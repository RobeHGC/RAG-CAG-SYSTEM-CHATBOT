"""
Distributed caching system for AI Companion.
Provides high-performance caching for memory queries, embeddings, and LLM responses.
"""

import asyncio
import json
import logging
import pickle
import time
from typing import Any, Dict, List, Optional, Union, Tuple
from functools import wraps
from dataclasses import dataclass

import numpy as np
import redis

from .database import RedisConnection, RedisClusterConnection, AsyncRedisConnection
from .monitoring import monitor

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""
    hits: int = 0
    misses: int = 0
    total_operations: int = 0
    hit_rate: float = 0.0
    avg_retrieval_time: float = 0.0


class CacheKeyGenerator:
    """Generates consistent cache keys for different data types."""
    
    @staticmethod
    def memory_query_key(user_id: str, query_hash: str) -> str:
        """Generate key for memory query results."""
        return f"memory:query:{user_id}:{query_hash}"
    
    @staticmethod
    def embedding_key(text_hash: str, model: str) -> str:
        """Generate key for text embeddings."""
        return f"embedding:{model}:{text_hash}"
    
    @staticmethod
    def llm_response_key(prompt_hash: str, model: str, temperature: float) -> str:
        """Generate key for LLM responses."""
        return f"llm:response:{model}:{temperature}:{prompt_hash}"
    
    @staticmethod
    def memory_consolidation_key(user_id: str, time_window: str) -> str:
        """Generate key for memory consolidation results."""
        return f"memory:consolidation:{user_id}:{time_window}"
    
    @staticmethod
    def spreading_activation_key(user_id: str, memory_id: str) -> str:
        """Generate key for spreading activation results."""
        return f"memory:spreading:{user_id}:{memory_id}"
    
    @staticmethod
    def emotional_state_key(user_id: str) -> str:
        """Generate key for user emotional state."""
        return f"emotional:state:{user_id}"
    
    @staticmethod
    def user_session_key(user_id: str) -> str:
        """Generate key for user session data."""
        return f"session:{user_id}"


class CacheSerializer:
    """Handles serialization and deserialization of cached data."""
    
    @staticmethod
    def serialize_json(data: Any) -> str:
        """Serialize data as JSON."""
        return json.dumps(data, default=str)
    
    @staticmethod
    def deserialize_json(data: str) -> Any:
        """Deserialize JSON data."""
        return json.loads(data)
    
    @staticmethod
    def serialize_pickle(data: Any) -> bytes:
        """Serialize data as pickle (for complex objects)."""
        return pickle.dumps(data)
    
    @staticmethod
    def deserialize_pickle(data: bytes) -> Any:
        """Deserialize pickle data."""
        return pickle.loads(data)
    
    @staticmethod
    def serialize_numpy(array: np.ndarray) -> bytes:
        """Serialize numpy array."""
        return array.tobytes()
    
    @staticmethod
    def deserialize_numpy(data: bytes, dtype: np.dtype, shape: Tuple[int, ...]) -> np.ndarray:
        """Deserialize numpy array."""
        return np.frombuffer(data, dtype=dtype).reshape(shape)


class CacheManager:
    """High-performance distributed cache manager."""
    
    def __init__(self, redis_connection: Optional[Union[RedisConnection, RedisClusterConnection]] = None,
                 default_ttl: int = 3600, max_memory_mb: int = 1024):
        """
        Initialize cache manager.
        
        Args:
            redis_connection: Redis connection instance
            default_ttl: Default time-to-live in seconds
            max_memory_mb: Maximum memory usage in MB
        """
        self.redis = redis_connection or RedisConnection()
        self.default_ttl = default_ttl
        self.max_memory_mb = max_memory_mb
        self.stats = {
            'memory': CacheStats(),
            'embedding': CacheStats(),
            'llm': CacheStats(),
            'consolidation': CacheStats(),
            'spreading': CacheStats()
        }
        
    def _track_operation(self, cache_type: str, hit: bool, retrieval_time: float):
        """Track cache operation statistics."""
        stats = self.stats[cache_type]
        stats.total_operations += 1
        
        if hit:
            stats.hits += 1
            monitor.record_cache_hit(cache_type)
        else:
            stats.misses += 1
            monitor.record_cache_miss(cache_type)
            
        stats.hit_rate = (stats.hits / stats.total_operations) * 100
        stats.avg_retrieval_time = (
            (stats.avg_retrieval_time * (stats.total_operations - 1) + retrieval_time) 
            / stats.total_operations
        )
    
    def get_memory_query_cache(self, user_id: str, query_hash: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached memory query results.
        
        Args:
            user_id: User identifier
            query_hash: Hash of the query
            
        Returns:
            Cached query results or None
        """
        start_time = time.time()
        
        try:
            with monitor.track_cache_operation('get', 'memory'):
                key = CacheKeyGenerator.memory_query_key(user_id, query_hash)
                cached_data = self.redis.get(key)
                
                retrieval_time = time.time() - start_time
                
                if cached_data:
                    self._track_operation('memory', True, retrieval_time)
                    return CacheSerializer.deserialize_json(cached_data)
                else:
                    self._track_operation('memory', False, retrieval_time)
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving memory query cache: {e}")
            self._track_operation('memory', False, time.time() - start_time)
            return None
    
    def set_memory_query_cache(self, user_id: str, query_hash: str, 
                              results: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """
        Cache memory query results.
        
        Args:
            user_id: User identifier
            query_hash: Hash of the query
            results: Query results to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if cached successfully
        """
        try:
            with monitor.track_cache_operation('set', 'memory'):
                key = CacheKeyGenerator.memory_query_key(user_id, query_hash)
                data = CacheSerializer.serialize_json(results)
                ttl = ttl or self.default_ttl
                
                return self.redis.set(key, data, ex=ttl)
                
        except Exception as e:
            logger.error(f"Error setting memory query cache: {e}")
            return False
    
    def get_embedding_cache(self, text_hash: str, model: str) -> Optional[np.ndarray]:
        """
        Get cached text embedding.
        
        Args:
            text_hash: Hash of the text
            model: Embedding model name
            
        Returns:
            Cached embedding or None
        """
        start_time = time.time()
        
        try:
            with monitor.track_cache_operation('get', 'embedding'):
                key = CacheKeyGenerator.embedding_key(text_hash, model)
                cached_data = self.redis.get(key)
                
                retrieval_time = time.time() - start_time
                
                if cached_data:
                    self._track_operation('embedding', True, retrieval_time)
                    # Embeddings are stored as JSON with metadata
                    embedding_data = CacheSerializer.deserialize_json(cached_data)
                    return np.array(embedding_data['vector'])
                else:
                    self._track_operation('embedding', False, retrieval_time)
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving embedding cache: {e}")
            self._track_operation('embedding', False, time.time() - start_time)
            return None
    
    def set_embedding_cache(self, text_hash: str, model: str, 
                           embedding: np.ndarray, ttl: Optional[int] = None) -> bool:
        """
        Cache text embedding.
        
        Args:
            text_hash: Hash of the text
            model: Embedding model name
            embedding: Embedding vector
            ttl: Time-to-live in seconds
            
        Returns:
            True if cached successfully
        """
        try:
            with monitor.track_cache_operation('set', 'embedding'):
                key = CacheKeyGenerator.embedding_key(text_hash, model)
                
                # Store embedding with metadata
                embedding_data = {
                    'vector': embedding.tolist(),
                    'shape': embedding.shape,
                    'dtype': str(embedding.dtype),
                    'model': model,
                    'timestamp': time.time()
                }
                
                data = CacheSerializer.serialize_json(embedding_data)
                ttl = ttl or self.default_ttl * 2  # Embeddings live longer
                
                return self.redis.set(key, data, ex=ttl)
                
        except Exception as e:
            logger.error(f"Error setting embedding cache: {e}")
            return False
    
    def get_llm_response_cache(self, prompt_hash: str, model: str, 
                              temperature: float) -> Optional[str]:
        """
        Get cached LLM response.
        
        Args:
            prompt_hash: Hash of the prompt
            model: LLM model name
            temperature: Model temperature
            
        Returns:
            Cached response or None
        """
        start_time = time.time()
        
        try:
            with monitor.track_cache_operation('get', 'llm'):
                key = CacheKeyGenerator.llm_response_key(prompt_hash, model, temperature)
                cached_data = self.redis.get(key)
                
                retrieval_time = time.time() - start_time
                
                if cached_data:
                    self._track_operation('llm', True, retrieval_time)
                    response_data = CacheSerializer.deserialize_json(cached_data)
                    return response_data['response']
                else:
                    self._track_operation('llm', False, retrieval_time)
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving LLM response cache: {e}")
            self._track_operation('llm', False, time.time() - start_time)
            return None
    
    def set_llm_response_cache(self, prompt_hash: str, model: str, temperature: float,
                              response: str, ttl: Optional[int] = None) -> bool:
        """
        Cache LLM response.
        
        Args:
            prompt_hash: Hash of the prompt
            model: LLM model name
            temperature: Model temperature
            response: LLM response to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if cached successfully
        """
        try:
            with monitor.track_cache_operation('set', 'llm'):
                key = CacheKeyGenerator.llm_response_key(prompt_hash, model, temperature)
                
                response_data = {
                    'response': response,
                    'model': model,
                    'temperature': temperature,
                    'timestamp': time.time()
                }
                
                data = CacheSerializer.serialize_json(response_data)
                ttl = ttl or self.default_ttl // 2  # LLM responses don't live as long
                
                return self.redis.set(key, data, ex=ttl)
                
        except Exception as e:
            logger.error(f"Error setting LLM response cache: {e}")
            return False
    
    def get_memory_consolidation_cache(self, user_id: str, 
                                     time_window: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached memory consolidation results."""
        start_time = time.time()
        
        try:
            with monitor.track_cache_operation('get', 'consolidation'):
                key = CacheKeyGenerator.memory_consolidation_key(user_id, time_window)
                cached_data = self.redis.get(key)
                
                retrieval_time = time.time() - start_time
                
                if cached_data:
                    self._track_operation('consolidation', True, retrieval_time)
                    return CacheSerializer.deserialize_json(cached_data)
                else:
                    self._track_operation('consolidation', False, retrieval_time)
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving consolidation cache: {e}")
            self._track_operation('consolidation', False, time.time() - start_time)
            return None
    
    def set_memory_consolidation_cache(self, user_id: str, time_window: str,
                                     results: List[Dict[str, Any]], 
                                     ttl: Optional[int] = None) -> bool:
        """Cache memory consolidation results."""
        try:
            with monitor.track_cache_operation('set', 'consolidation'):
                key = CacheKeyGenerator.memory_consolidation_key(user_id, time_window)
                data = CacheSerializer.serialize_json(results)
                ttl = ttl or self.default_ttl * 3  # Consolidation results live longer
                
                return self.redis.set(key, data, ex=ttl)
                
        except Exception as e:
            logger.error(f"Error setting consolidation cache: {e}")
            return False
    
    def get_spreading_activation_cache(self, user_id: str, 
                                     memory_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached spreading activation results."""
        start_time = time.time()
        
        try:
            with monitor.track_cache_operation('get', 'spreading'):
                key = CacheKeyGenerator.spreading_activation_key(user_id, memory_id)
                cached_data = self.redis.get(key)
                
                retrieval_time = time.time() - start_time
                
                if cached_data:
                    self._track_operation('spreading', True, retrieval_time)
                    return CacheSerializer.deserialize_json(cached_data)
                else:
                    self._track_operation('spreading', False, retrieval_time)
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving spreading activation cache: {e}")
            self._track_operation('spreading', False, time.time() - start_time)
            return None
    
    def set_spreading_activation_cache(self, user_id: str, memory_id: str,
                                     results: List[Dict[str, Any]], 
                                     ttl: Optional[int] = None) -> bool:
        """Cache spreading activation results."""
        try:
            with monitor.track_cache_operation('set', 'spreading'):
                key = CacheKeyGenerator.spreading_activation_key(user_id, memory_id)
                data = CacheSerializer.serialize_json(results)
                ttl = ttl or self.default_ttl
                
                return self.redis.set(key, data, ex=ttl)
                
        except Exception as e:
            logger.error(f"Error setting spreading activation cache: {e}")
            return False
    
    def invalidate_user_cache(self, user_id: str, cache_types: Optional[List[str]] = None):
        """
        Invalidate all cache entries for a user.
        
        Args:
            user_id: User identifier
            cache_types: Specific cache types to invalidate (optional)
        """
        cache_types = cache_types or ['memory', 'consolidation', 'spreading', 'emotional', 'session']
        
        try:
            patterns = []
            for cache_type in cache_types:
                if cache_type == 'memory':
                    patterns.append(f"memory:*:{user_id}:*")
                elif cache_type == 'consolidation':
                    patterns.append(f"memory:consolidation:{user_id}:*")
                elif cache_type == 'spreading':
                    patterns.append(f"memory:spreading:{user_id}:*")
                elif cache_type == 'emotional':
                    patterns.append(f"emotional:state:{user_id}")
                elif cache_type == 'session':
                    patterns.append(f"session:{user_id}")
            
            # Note: This is a simplified implementation
            # In production, you'd want to use SCAN for large datasets
            for pattern in patterns:
                try:
                    # For Redis cluster, this would need different handling
                    if hasattr(self.redis.client, 'keys'):
                        keys = self.redis.client.keys(pattern)
                        if keys:
                            self.redis.delete(*keys)
                except Exception as e:
                    logger.warning(f"Error invalidating cache pattern {pattern}: {e}")
                    
        except Exception as e:
            logger.error(f"Error invalidating user cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, CacheStats]:
        """Get cache statistics for all cache types."""
        return self.stats.copy()
    
    def get_overall_hit_rate(self) -> float:
        """Get overall cache hit rate across all cache types."""
        total_hits = sum(stats.hits for stats in self.stats.values())
        total_operations = sum(stats.total_operations for stats in self.stats.values())
        
        if total_operations == 0:
            return 0.0
            
        return (total_hits / total_operations) * 100
    
    def clear_all_cache(self):
        """Clear all cache entries (use with caution)."""
        try:
            if hasattr(self.redis.client, 'flushall'):
                self.redis.client.flushall()
                logger.warning("All cache entries cleared")
            else:
                logger.warning("Cache clear not available for this Redis configuration")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


def cache_result(cache_type: str, key_func: callable, ttl: Optional[int] = None):
    """
    Decorator to automatically cache function results.
    
    Args:
        cache_type: Type of cache (memory, embedding, llm, etc.)
        key_func: Function to generate cache key from function arguments
        ttl: Time-to-live in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)
            
            # Try to get from cache first
            cached_result = cache_manager.redis.get(cache_key)
            if cached_result:
                monitor.record_cache_hit(cache_type)
                return CacheSerializer.deserialize_json(cached_result)
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            monitor.record_cache_miss(cache_type)
            
            # Cache the result
            try:
                data = CacheSerializer.serialize_json(result)
                cache_manager.redis.set(cache_key, data, ex=ttl or cache_manager.default_ttl)
            except Exception as e:
                logger.error(f"Error caching result: {e}")
            
            return result
        
        return wrapper
    return decorator


# Global cache manager instance
cache_manager = CacheManager()