"""
Rate limiting and request throttling system for AI Companion.
Provides protection against overload and ensures fair usage across users.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from functools import wraps

from .database import RedisConnection, RedisClusterConnection
from .monitoring import monitor

logger = logging.getLogger(__name__)


class LimitType(Enum):
    """Types of rate limits."""
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"
    LLM_REQUESTS_PER_MINUTE = "llm_requests_per_minute"
    MEMORY_OPERATIONS_PER_MINUTE = "memory_ops_per_minute"
    WEBHOOK_REQUESTS_PER_SECOND = "webhook_per_second"


@dataclass
class RateLimitConfig:
    """Configuration for a specific rate limit."""
    limit: int
    window_seconds: int
    burst_limit: Optional[int] = None  # Allow burst up to this many requests
    penalty_seconds: Optional[int] = None  # Penalty time when limit exceeded


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None
    limit_type: Optional[str] = None


@dataclass
class UserLimitState:
    """Current rate limit state for a user."""
    request_count: int = 0
    first_request_time: float = field(default_factory=time.time)
    last_request_time: float = field(default_factory=time.time)
    penalty_until: Optional[float] = None
    burst_count: int = 0


class RateLimiter:
    """High-performance rate limiter with Redis backend."""
    
    def __init__(self, redis_connection: Optional[Union[RedisConnection, RedisClusterConnection]] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_connection: Redis connection for distributed rate limiting
        """
        self.redis = redis_connection or RedisConnection()
        
        # Default rate limit configurations
        self.default_limits = {
            LimitType.REQUESTS_PER_MINUTE: RateLimitConfig(
                limit=60, 
                window_seconds=60, 
                burst_limit=10,
                penalty_seconds=60
            ),
            LimitType.REQUESTS_PER_HOUR: RateLimitConfig(
                limit=1000, 
                window_seconds=3600,
                burst_limit=50,
                penalty_seconds=300
            ),
            LimitType.REQUESTS_PER_DAY: RateLimitConfig(
                limit=10000, 
                window_seconds=86400,
                penalty_seconds=3600
            ),
            LimitType.LLM_REQUESTS_PER_MINUTE: RateLimitConfig(
                limit=20, 
                window_seconds=60,
                burst_limit=5,
                penalty_seconds=120
            ),
            LimitType.MEMORY_OPERATIONS_PER_MINUTE: RateLimitConfig(
                limit=100, 
                window_seconds=60,
                burst_limit=20,
                penalty_seconds=60
            ),
            LimitType.WEBHOOK_REQUESTS_PER_SECOND: RateLimitConfig(
                limit=10, 
                window_seconds=1,
                burst_limit=3,
                penalty_seconds=5
            )
        }
        
        # Custom limits per user
        self.custom_limits: Dict[str, Dict[LimitType, RateLimitConfig]] = {}
        
        # In-memory state for very high-frequency operations
        self.local_state: Dict[str, UserLimitState] = {}
        
    def _get_redis_key(self, user_id: str, limit_type: LimitType, window_start: int) -> str:
        """Generate Redis key for rate limit tracking."""
        return f"rate_limit:{user_id}:{limit_type.value}:{window_start}"
    
    def _get_penalty_key(self, user_id: str, limit_type: LimitType) -> str:
        """Generate Redis key for penalty tracking."""
        return f"rate_limit:penalty:{user_id}:{limit_type.value}"
    
    def _get_current_window(self, window_seconds: int) -> int:
        """Get current time window."""
        return int(time.time() // window_seconds)
    
    def set_custom_limit(self, user_id: str, limit_type: LimitType, 
                        config: RateLimitConfig):
        """
        Set custom rate limit for a specific user.
        
        Args:
            user_id: User identifier
            limit_type: Type of rate limit
            config: Rate limit configuration
        """
        if user_id not in self.custom_limits:
            self.custom_limits[user_id] = {}
        self.custom_limits[user_id][limit_type] = config
        logger.info(f"Set custom rate limit for {user_id}: {limit_type.value} = {config.limit}")
    
    def _get_limit_config(self, user_id: str, limit_type: LimitType) -> RateLimitConfig:
        """Get rate limit configuration for user and limit type."""
        if (user_id in self.custom_limits and 
            limit_type in self.custom_limits[user_id]):
            return self.custom_limits[user_id][limit_type]
        return self.default_limits[limit_type]
    
    def check_rate_limit(self, user_id: str, limit_type: LimitType, 
                        increment: int = 1) -> RateLimitResult:
        """
        Check if request is within rate limit and optionally increment counter.
        
        Args:
            user_id: User identifier
            limit_type: Type of rate limit to check
            increment: Amount to increment counter (0 for check-only)
            
        Returns:
            RateLimitResult with decision and metadata
        """
        config = self._get_limit_config(user_id, limit_type)
        current_time = time.time()
        window_start = self._get_current_window(config.window_seconds)
        
        # Check for active penalty
        penalty_key = self._get_penalty_key(user_id, limit_type)
        try:
            penalty_until = self.redis.get(penalty_key)
            if penalty_until and float(penalty_until) > current_time:
                retry_after = int(float(penalty_until) - current_time)
                monitor.record_rate_limit_hit(user_id, limit_type.value)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=float(penalty_until),
                    retry_after=retry_after,
                    limit_type=limit_type.value
                )
        except Exception as e:
            logger.warning(f"Error checking penalty: {e}")
        
        # Get current count from Redis
        redis_key = self._get_redis_key(user_id, limit_type, window_start)
        
        try:
            current_count = self.redis.get(redis_key)
            current_count = int(current_count) if current_count else 0
        except Exception as e:
            logger.error(f"Error getting rate limit count: {e}")
            current_count = 0
        
        # Calculate remaining requests
        remaining = max(0, config.limit - current_count)
        reset_time = (window_start + 1) * config.window_seconds
        
        # Check if request would exceed limit
        if current_count + increment > config.limit:
            # Check burst allowance
            if config.burst_limit and current_count + increment <= config.limit + config.burst_limit:
                logger.warning(f"User {user_id} using burst allowance for {limit_type.value}")
            else:
                # Apply penalty if configured
                if config.penalty_seconds:
                    penalty_until_time = current_time + config.penalty_seconds
                    try:
                        self.redis.set(penalty_key, str(penalty_until_time), ex=config.penalty_seconds)
                    except Exception as e:
                        logger.error(f"Error setting penalty: {e}")
                
                monitor.record_rate_limit_hit(user_id, limit_type.value)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=int(reset_time - current_time),
                    limit_type=limit_type.value
                )
        
        # Increment counter if requested
        if increment > 0:
            try:
                # Use pipeline for atomic operations
                pipe = self.redis.client.pipeline()
                pipe.incr(redis_key, increment)
                pipe.expire(redis_key, config.window_seconds)
                pipe.execute()
                
                current_count += increment
                remaining = max(0, config.limit - current_count)
                
            except Exception as e:
                logger.error(f"Error incrementing rate limit counter: {e}")
        
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_time=reset_time,
            limit_type=limit_type.value
        )
    
    def increment_counter(self, user_id: str, limit_type: LimitType, 
                         increment: int = 1) -> RateLimitResult:
        """
        Increment rate limit counter and check if within limits.
        
        Args:
            user_id: User identifier
            limit_type: Type of rate limit
            increment: Amount to increment
            
        Returns:
            RateLimitResult with decision and metadata
        """
        return self.check_rate_limit(user_id, limit_type, increment)
    
    def reset_user_limits(self, user_id: str, limit_types: Optional[List[LimitType]] = None):
        """
        Reset rate limits for a user.
        
        Args:
            user_id: User identifier
            limit_types: Specific limit types to reset (all if None)
        """
        limit_types = limit_types or list(LimitType)
        
        try:
            keys_to_delete = []
            
            for limit_type in limit_types:
                # Delete penalty keys
                penalty_key = self._get_penalty_key(user_id, limit_type)
                keys_to_delete.append(penalty_key)
                
                # Delete current window keys (approximate)
                config = self._get_limit_config(user_id, limit_type)
                current_window = self._get_current_window(config.window_seconds)
                redis_key = self._get_redis_key(user_id, limit_type, current_window)
                keys_to_delete.append(redis_key)
            
            if keys_to_delete:
                self.redis.delete(*keys_to_delete)
                logger.info(f"Reset rate limits for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error resetting rate limits: {e}")
    
    def get_user_status(self, user_id: str) -> Dict[str, Dict[str, Union[int, float]]]:
        """
        Get current rate limit status for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with status for each limit type
        """
        status = {}
        current_time = time.time()
        
        for limit_type in LimitType:
            try:
                result = self.check_rate_limit(user_id, limit_type, increment=0)
                config = self._get_limit_config(user_id, limit_type)
                
                status[limit_type.value] = {
                    'limit': config.limit,
                    'remaining': result.remaining,
                    'reset_time': result.reset_time,
                    'window_seconds': config.window_seconds,
                    'is_penalty_active': result.retry_after is not None,
                    'retry_after': result.retry_after
                }
                
            except Exception as e:
                logger.error(f"Error getting status for {limit_type.value}: {e}")
                status[limit_type.value] = {'error': str(e)}
        
        return status
    
    def cleanup_expired_data(self):
        """Clean up expired rate limit data (run periodically)."""
        try:
            current_time = time.time()
            
            # Clean up local state
            expired_keys = []
            for key, state in self.local_state.items():
                if (state.penalty_until and state.penalty_until < current_time):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.local_state[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired local rate limit entries")
                
        except Exception as e:
            logger.error(f"Error during rate limit cleanup: {e}")
    
    def get_global_stats(self) -> Dict[str, int]:
        """Get global rate limiting statistics."""
        try:
            # This is a simplified implementation
            # In production, you'd want more sophisticated monitoring
            stats = {
                'total_rate_limited_requests': 0,
                'active_penalties': 0,
                'unique_users_tracked': 0
            }
            
            # Count penalty keys (approximate)
            try:
                if hasattr(self.redis.client, 'keys'):
                    penalty_keys = self.redis.client.keys("rate_limit:penalty:*")
                    stats['active_penalties'] = len(penalty_keys) if penalty_keys else 0
            except Exception as e:
                logger.warning(f"Error counting penalty keys: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return {}


def rate_limit(limit_type: LimitType, user_id_func: Optional[callable] = None):
    """
    Decorator to apply rate limiting to functions.
    
    Args:
        limit_type: Type of rate limit to apply
        user_id_func: Function to extract user_id from function arguments
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user_id
            if user_id_func:
                user_id = user_id_func(*args, **kwargs)
            else:
                # Try to find user_id in kwargs or first argument
                user_id = kwargs.get('user_id') or (args[0] if args else 'global')
            
            # Check rate limit
            result = rate_limiter.increment_counter(user_id, limit_type)
            
            if not result.allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit_type": result.limit_type,
                        "retry_after": result.retry_after,
                        "reset_time": result.reset_time
                    }
                )
            
            # Add rate limit headers to response if possible
            if hasattr(func, '__annotations__') and 'Response' in str(func.__annotations__):
                # This would be handled in the actual response
                pass
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts limits based on system load."""
    
    def __init__(self, base_limiter: RateLimiter):
        """
        Initialize adaptive rate limiter.
        
        Args:
            base_limiter: Base rate limiter instance
        """
        self.base_limiter = base_limiter
        self.system_load_threshold = 0.8  # Reduce limits when load > 80%
        self.load_factor = 0.5  # Reduce limits to 50% under high load
        
    def get_current_load(self) -> float:
        """Get current system load (0.0 to 1.0)."""
        # This would integrate with monitoring system
        # For now, return a placeholder
        try:
            # Could check CPU, memory, response times, etc.
            return 0.3  # Placeholder: 30% load
        except Exception:
            return 0.5  # Conservative default
    
    def check_adaptive_rate_limit(self, user_id: str, limit_type: LimitType, 
                                 increment: int = 1) -> RateLimitResult:
        """
        Check rate limit with adaptive adjustment based on system load.
        
        Args:
            user_id: User identifier
            limit_type: Type of rate limit
            increment: Amount to increment
            
        Returns:
            RateLimitResult with adaptive decision
        """
        current_load = self.get_current_load()
        
        # Adjust limits based on system load
        if current_load > self.system_load_threshold:
            # Temporarily reduce limits under high load
            original_config = self.base_limiter._get_limit_config(user_id, limit_type)
            
            # Create temporary reduced config
            adaptive_config = RateLimitConfig(
                limit=int(original_config.limit * self.load_factor),
                window_seconds=original_config.window_seconds,
                burst_limit=int(original_config.burst_limit * self.load_factor) if original_config.burst_limit else None,
                penalty_seconds=original_config.penalty_seconds
            )
            
            # Temporarily override the config
            self.base_limiter.custom_limits.setdefault(user_id, {})[limit_type] = adaptive_config
            
            try:
                result = self.base_limiter.check_rate_limit(user_id, limit_type, increment)
                logger.debug(f"Applied adaptive rate limiting for {user_id} due to high load ({current_load:.2f})")
                return result
            finally:
                # Restore original config
                if user_id in self.base_limiter.custom_limits:
                    if limit_type in self.base_limiter.custom_limits[user_id]:
                        del self.base_limiter.custom_limits[user_id][limit_type]
        else:
            # Normal operation
            return self.base_limiter.check_rate_limit(user_id, limit_type, increment)


# Global rate limiter instances
rate_limiter = RateLimiter()
adaptive_rate_limiter = AdaptiveRateLimiter(rate_limiter)