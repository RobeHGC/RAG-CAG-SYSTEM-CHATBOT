"""
Performance configuration module for production deployment.
Provides optimized settings for database connections, caching, rate limiting, and memory systems.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

from .rate_limiter import RateLimitConfig, LimitType


class DeploymentMode(Enum):
    """Deployment mode for different environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabasePerformanceConfig:
    """Database connection and performance configuration."""
    
    # PostgreSQL settings
    postgres_pool_size: int = 50
    postgres_max_overflow: int = 100
    postgres_pool_pre_ping: bool = True
    postgres_pool_recycle: int = 3600
    postgres_query_timeout: int = 30
    
    # Async PostgreSQL settings
    postgres_async_min_size: int = 10
    postgres_async_max_size: int = 100
    postgres_async_command_timeout: int = 30
    
    # Redis settings
    redis_max_connections: int = 200
    redis_retry_on_timeout: bool = True
    redis_socket_keepalive: bool = True
    redis_socket_keepalive_options: Dict[int, int] = None
    
    # Redis cluster settings
    redis_cluster_max_connections_per_node: int = 100
    redis_cluster_skip_full_coverage_check: bool = True
    
    # Neo4j settings
    neo4j_max_connection_pool_size: int = 100
    neo4j_connection_acquisition_timeout: int = 60
    neo4j_max_connection_lifetime: int = 3600
    neo4j_max_transaction_retry_time: int = 30
    
    def __post_init__(self):
        if self.redis_socket_keepalive_options is None:
            self.redis_socket_keepalive_options = {
                1: 1,   # TCP_KEEPIDLE
                2: 2,   # TCP_KEEPINTVL
                3: 3,   # TCP_KEEPCNT
            }


@dataclass
class CachePerformanceConfig:
    """Caching system performance configuration."""
    
    # Cache TTL settings (in seconds)
    memory_query_ttl: int = 1800  # 30 minutes
    embedding_ttl: int = 7200     # 2 hours
    llm_response_ttl: int = 900   # 15 minutes
    consolidation_ttl: int = 5400 # 1.5 hours
    spreading_activation_ttl: int = 1800  # 30 minutes
    
    # Cache size limits
    max_memory_cache_mb: int = 1024  # 1GB
    max_embedding_cache_mb: int = 2048  # 2GB
    max_llm_cache_mb: int = 512  # 512MB
    
    # Cache cleanup settings
    cleanup_interval_seconds: int = 3600  # 1 hour
    cache_hit_rate_threshold: float = 0.8  # Target 80% hit rate
    
    # Serialization settings
    use_compression: bool = True
    compression_level: int = 6


@dataclass
class RateLimitPerformanceConfig:
    """Rate limiting performance configuration."""
    
    # Development limits (relaxed)
    development_limits: Dict[LimitType, RateLimitConfig] = None
    
    # Staging limits (moderate)
    staging_limits: Dict[LimitType, RateLimitConfig] = None
    
    # Production limits (strict)
    production_limits: Dict[LimitType, RateLimitConfig] = None
    
    # Adaptive rate limiting settings
    enable_adaptive_limiting: bool = True
    load_threshold: float = 0.8
    load_reduction_factor: float = 0.5
    
    def __post_init__(self):
        if self.development_limits is None:
            self.development_limits = {
                LimitType.REQUESTS_PER_MINUTE: RateLimitConfig(
                    limit=120, window_seconds=60, burst_limit=20, penalty_seconds=30
                ),
                LimitType.REQUESTS_PER_HOUR: RateLimitConfig(
                    limit=2000, window_seconds=3600, burst_limit=100, penalty_seconds=300
                ),
                LimitType.LLM_REQUESTS_PER_MINUTE: RateLimitConfig(
                    limit=30, window_seconds=60, burst_limit=10, penalty_seconds=60
                ),
                LimitType.MEMORY_OPERATIONS_PER_MINUTE: RateLimitConfig(
                    limit=200, window_seconds=60, burst_limit=40, penalty_seconds=30
                ),
                LimitType.WEBHOOK_REQUESTS_PER_SECOND: RateLimitConfig(
                    limit=20, window_seconds=1, burst_limit=5, penalty_seconds=2
                )
            }
        
        if self.staging_limits is None:
            self.staging_limits = {
                LimitType.REQUESTS_PER_MINUTE: RateLimitConfig(
                    limit=80, window_seconds=60, burst_limit=15, penalty_seconds=60
                ),
                LimitType.REQUESTS_PER_HOUR: RateLimitConfig(
                    limit=1500, window_seconds=3600, burst_limit=75, penalty_seconds=300
                ),
                LimitType.LLM_REQUESTS_PER_MINUTE: RateLimitConfig(
                    limit=25, window_seconds=60, burst_limit=8, penalty_seconds=90
                ),
                LimitType.MEMORY_OPERATIONS_PER_MINUTE: RateLimitConfig(
                    limit=150, window_seconds=60, burst_limit=30, penalty_seconds=60
                ),
                LimitType.WEBHOOK_REQUESTS_PER_SECOND: RateLimitConfig(
                    limit=15, window_seconds=1, burst_limit=4, penalty_seconds=3
                )
            }
        
        if self.production_limits is None:
            self.production_limits = {
                LimitType.REQUESTS_PER_MINUTE: RateLimitConfig(
                    limit=60, window_seconds=60, burst_limit=10, penalty_seconds=60
                ),
                LimitType.REQUESTS_PER_HOUR: RateLimitConfig(
                    limit=1000, window_seconds=3600, burst_limit=50, penalty_seconds=300
                ),
                LimitType.LLM_REQUESTS_PER_MINUTE: RateLimitConfig(
                    limit=20, window_seconds=60, burst_limit=5, penalty_seconds=120
                ),
                LimitType.MEMORY_OPERATIONS_PER_MINUTE: RateLimitConfig(
                    limit=100, window_seconds=60, burst_limit=20, penalty_seconds=60
                ),
                LimitType.WEBHOOK_REQUESTS_PER_SECOND: RateLimitConfig(
                    limit=10, window_seconds=1, burst_limit=3, penalty_seconds=5
                )
            }


@dataclass
class MemorySystemPerformanceConfig:
    """Memory system performance configuration."""
    
    # Context window settings
    context_window_size: int = 100  # Messages
    context_ttl_seconds: int = 86400  # 24 hours
    
    # Memory consolidation settings
    consolidation_batch_size: int = 50
    consolidation_threshold: int = 3  # Minimum frequency
    consolidation_interval_seconds: int = 3600  # 1 hour
    
    # Embedding settings
    embedding_batch_size: int = 64
    embedding_cache_enabled: bool = True
    embedding_dimension: int = 768
    
    # Similarity search settings
    similarity_threshold: float = 0.7
    max_memories_per_query: int = 10
    similarity_search_timeout: int = 30
    
    # Forgetting curve settings
    forgetting_check_interval: int = 3600  # 1 hour
    max_memories_per_user: int = 1000
    memory_retention_days: int = 30
    
    # Emotional analysis settings
    emotional_weight_threshold: float = 0.6
    emotional_cache_enabled: bool = True


@dataclass
class MonitoringPerformanceConfig:
    """Monitoring and observability configuration."""
    
    # Metrics collection settings
    metrics_collection_enabled: bool = True
    metrics_export_interval: int = 60  # seconds
    metrics_retention_days: int = 30
    
    # Performance thresholds
    response_time_threshold_ms: float = 2000  # 2 seconds
    memory_usage_threshold_gb: float = 2.0
    cache_hit_rate_threshold: float = 0.8  # 80%
    error_rate_threshold: float = 0.05  # 5%
    
    # Alerting settings
    enable_alerts: bool = True
    alert_cooldown_seconds: int = 300  # 5 minutes
    alert_webhook_url: Optional[str] = None
    
    # Logging settings
    log_level: str = "INFO"
    log_structured: bool = True
    log_performance_traces: bool = True


@dataclass
class LoadTestingConfig:
    """Load testing configuration."""
    
    # Test scenarios
    concurrent_users_min: int = 10
    concurrent_users_max: int = 1000
    test_duration_seconds: int = 300  # 5 minutes
    ramp_up_seconds: int = 60
    
    # Performance targets
    target_response_time_p95_ms: float = 2000
    target_throughput_rps: float = 100
    target_error_rate_max: float = 0.01  # 1%
    target_memory_usage_max_gb: float = 2.0
    
    # Test data
    test_messages_per_user: int = 50
    test_memory_queries_ratio: float = 0.3  # 30% of requests are memory queries
    test_llm_requests_ratio: float = 0.7   # 70% are LLM requests


class PerformanceConfigManager:
    """Manager for performance configuration across different environments."""
    
    def __init__(self, deployment_mode: Optional[DeploymentMode] = None):
        """
        Initialize performance configuration manager.
        
        Args:
            deployment_mode: Target deployment environment
        """
        self.deployment_mode = deployment_mode or self._detect_deployment_mode()
        self._config_cache = {}
    
    def _detect_deployment_mode(self) -> DeploymentMode:
        """Auto-detect deployment mode from environment variables."""
        env_mode = os.getenv('DEPLOYMENT_MODE', 'development').lower()
        
        if env_mode in ['prod', 'production']:
            return DeploymentMode.PRODUCTION
        elif env_mode in ['stage', 'staging']:
            return DeploymentMode.STAGING
        else:
            return DeploymentMode.DEVELOPMENT
    
    def get_database_config(self) -> DatabasePerformanceConfig:
        """Get database performance configuration for current environment."""
        if 'database' not in self._config_cache:
            config = DatabasePerformanceConfig()
            
            # Adjust for environment
            if self.deployment_mode == DeploymentMode.PRODUCTION:
                config.postgres_pool_size = 100
                config.postgres_max_overflow = 200
                config.postgres_async_max_size = 200
                config.redis_max_connections = 500
                config.neo4j_max_connection_pool_size = 150
            elif self.deployment_mode == DeploymentMode.STAGING:
                config.postgres_pool_size = 75
                config.postgres_max_overflow = 150
                config.postgres_async_max_size = 150
                config.redis_max_connections = 300
                config.neo4j_max_connection_pool_size = 100
            
            self._config_cache['database'] = config
        
        return self._config_cache['database']
    
    def get_cache_config(self) -> CachePerformanceConfig:
        """Get cache performance configuration for current environment."""
        if 'cache' not in self._config_cache:
            config = CachePerformanceConfig()
            
            # Adjust for environment
            if self.deployment_mode == DeploymentMode.PRODUCTION:
                config.max_memory_cache_mb = 2048  # 2GB
                config.max_embedding_cache_mb = 4096  # 4GB
                config.max_llm_cache_mb = 1024  # 1GB
                config.memory_query_ttl = 3600  # 1 hour
            elif self.deployment_mode == DeploymentMode.STAGING:
                config.max_memory_cache_mb = 1024  # 1GB
                config.max_embedding_cache_mb = 2048  # 2GB
                config.max_llm_cache_mb = 512  # 512MB
            
            self._config_cache['cache'] = config
        
        return self._config_cache['cache']
    
    def get_rate_limit_config(self) -> RateLimitPerformanceConfig:
        """Get rate limiting configuration for current environment."""
        if 'rate_limit' not in self._config_cache:
            config = RateLimitPerformanceConfig()
            
            # Environment-specific adjustments are in the dataclass defaults
            self._config_cache['rate_limit'] = config
        
        return self._config_cache['rate_limit']
    
    def get_memory_config(self) -> MemorySystemPerformanceConfig:
        """Get memory system configuration for current environment."""
        if 'memory' not in self._config_cache:
            config = MemorySystemPerformanceConfig()
            
            # Adjust for environment
            if self.deployment_mode == DeploymentMode.PRODUCTION:
                config.context_window_size = 200
                config.consolidation_batch_size = 100
                config.max_memories_per_user = 2000
                config.embedding_batch_size = 128
            elif self.deployment_mode == DeploymentMode.STAGING:
                config.context_window_size = 150
                config.consolidation_batch_size = 75
                config.max_memories_per_user = 1500
                config.embedding_batch_size = 96
            
            self._config_cache['memory'] = config
        
        return self._config_cache['memory']
    
    def get_monitoring_config(self) -> MonitoringPerformanceConfig:
        """Get monitoring configuration for current environment."""
        if 'monitoring' not in self._config_cache:
            config = MonitoringPerformanceConfig()
            
            # Adjust for environment
            if self.deployment_mode == DeploymentMode.PRODUCTION:
                config.log_level = "WARNING"
                config.log_performance_traces = False  # Reduce overhead
                config.metrics_retention_days = 90
            elif self.deployment_mode == DeploymentMode.STAGING:
                config.log_level = "INFO"
                config.metrics_retention_days = 60
            else:  # Development
                config.log_level = "DEBUG"
                config.metrics_retention_days = 7
            
            self._config_cache['monitoring'] = config
        
        return self._config_cache['monitoring']
    
    def get_load_testing_config(self) -> LoadTestingConfig:
        """Get load testing configuration."""
        if 'load_testing' not in self._config_cache:
            config = LoadTestingConfig()
            
            # Adjust targets based on environment
            if self.deployment_mode == DeploymentMode.PRODUCTION:
                config.target_throughput_rps = 200
                config.target_memory_usage_max_gb = 4.0
                config.concurrent_users_max = 2000
            elif self.deployment_mode == DeploymentMode.STAGING:
                config.target_throughput_rps = 150
                config.target_memory_usage_max_gb = 3.0
                config.concurrent_users_max = 1500
            
            self._config_cache['load_testing'] = config
        
        return self._config_cache['load_testing']
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all performance configurations."""
        return {
            'database': self.get_database_config(),
            'cache': self.get_cache_config(),
            'rate_limit': self.get_rate_limit_config(),
            'memory': self.get_memory_config(),
            'monitoring': self.get_monitoring_config(),
            'load_testing': self.get_load_testing_config(),
            'deployment_mode': self.deployment_mode.value
        }
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate all configurations."""
        validation_results = {}
        
        try:
            db_config = self.get_database_config()
            validation_results['database'] = (
                db_config.postgres_pool_size > 0 and
                db_config.redis_max_connections > 0 and
                db_config.neo4j_max_connection_pool_size > 0
            )
        except Exception:
            validation_results['database'] = False
        
        try:
            cache_config = self.get_cache_config()
            validation_results['cache'] = (
                cache_config.memory_query_ttl > 0 and
                cache_config.max_memory_cache_mb > 0
            )
        except Exception:
            validation_results['cache'] = False
        
        try:
            memory_config = self.get_memory_config()
            validation_results['memory'] = (
                memory_config.context_window_size > 0 and
                memory_config.similarity_threshold > 0
            )
        except Exception:
            validation_results['memory'] = False
        
        return validation_results


# Global configuration manager instance
performance_config = PerformanceConfigManager()