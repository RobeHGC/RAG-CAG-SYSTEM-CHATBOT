"""
Performance monitoring and metrics collection using Prometheus.
Provides comprehensive monitoring for database connections, caching, and application performance.
"""

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Optional

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, generate_latest, 
    CollectorRegistry, CONTENT_TYPE_LATEST, start_http_server
)

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Central performance monitoring system with Prometheus metrics."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize performance monitor.
        
        Args:
            registry: Optional custom registry, uses default if not provided
        """
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()
        
    def _setup_metrics(self):
        """Initialize all performance metrics."""
        
        # Request metrics
        self.request_count = Counter(
            'app_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'app_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_connections = Gauge(
            'db_connections_active',
            'Active database connections',
            ['database'],
            registry=self.registry
        )
        
        self.db_operations = Counter(
            'db_operations_total',
            'Total database operations',
            ['database', 'operation', 'status'],
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['database', 'operation'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_operations = Histogram(
            'cache_operation_duration_seconds',
            'Cache operation duration in seconds',
            ['operation', 'cache_type'],
            registry=self.registry
        )
        
        # Memory system metrics
        self.memory_operations = Counter(
            'memory_operations_total',
            'Total memory system operations',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.memory_consolidation_duration = Histogram(
            'memory_consolidation_duration_seconds',
            'Memory consolidation duration in seconds',
            registry=self.registry
        )
        
        self.active_memories = Gauge(
            'active_memories_count',
            'Number of active memories',
            ['user_id'],
            registry=self.registry
        )
        
        # System metrics
        self.memory_usage = Gauge(
            'app_memory_usage_bytes',
            'Application memory usage in bytes',
            registry=self.registry
        )
        
        self.response_time_percentile = Summary(
            'app_response_time_percentile',
            'Response time percentiles',
            registry=self.registry
        )
        
        # Rate limiting metrics
        self.rate_limit_hits = Counter(
            'rate_limit_hits_total',
            'Total rate limit hits',
            ['user_id', 'limit_type'],
            registry=self.registry
        )
        
        self.concurrent_users = Gauge(
            'concurrent_users_active',
            'Number of active concurrent users',
            registry=self.registry
        )
        
        # LLM metrics
        self.llm_requests = Counter(
            'llm_requests_total',
            'Total LLM requests',
            ['model', 'status'],
            registry=self.registry
        )
        
        self.llm_response_time = Histogram(
            'llm_response_duration_seconds',
            'LLM response duration in seconds',
            ['model'],
            registry=self.registry
        )
        
        self.token_usage = Counter(
            'llm_tokens_total',
            'Total tokens used',
            ['model', 'token_type'],
            registry=self.registry
        )
    
    @contextmanager
    def track_request(self, method: str, endpoint: str):
        """
        Track request duration and count.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
        """
        start_time = time.time()
        status = 'success'
        
        try:
            yield
        except Exception as e:
            status = 'error'
            logger.error(f"Request failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
            self.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
            self.response_time_percentile.observe(duration)
    
    @contextmanager
    def track_db_operation(self, database: str, operation: str):
        """
        Track database operation duration and count.
        
        Args:
            database: Database name (postgres, redis, neo4j)
            operation: Operation type (query, insert, update, delete)
        """
        start_time = time.time()
        status = 'success'
        
        try:
            yield
        except Exception as e:
            status = 'error'
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self.db_query_duration.labels(database=database, operation=operation).observe(duration)
            self.db_operations.labels(database=database, operation=operation, status=status).inc()
    
    @contextmanager
    def track_cache_operation(self, operation: str, cache_type: str):
        """
        Track cache operation duration.
        
        Args:
            operation: Cache operation (get, set, delete)
            cache_type: Type of cache (memory, embedding, llm)
        """
        start_time = time.time()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.cache_operations.labels(operation=operation, cache_type=cache_type).observe(duration)
    
    def record_cache_hit(self, cache_type: str):
        """Record a cache hit."""
        self.cache_hits.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record a cache miss."""
        self.cache_misses.labels(cache_type=cache_type).inc()
    
    def get_cache_hit_rate(self, cache_type: str) -> float:
        """
        Calculate cache hit rate.
        
        Args:
            cache_type: Type of cache
            
        Returns:
            Hit rate as percentage (0-100)
        """
        hits = self.cache_hits.labels(cache_type=cache_type)._value._value
        misses = self.cache_misses.labels(cache_type=cache_type)._value._value
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return (hits / total) * 100
    
    def update_active_connections(self, database: str, count: int):
        """Update active connection count for a database."""
        self.db_connections.labels(database=database).set(count)
    
    def update_memory_usage(self, bytes_used: int):
        """Update application memory usage."""
        self.memory_usage.set(bytes_used)
    
    def update_concurrent_users(self, count: int):
        """Update concurrent user count."""
        self.concurrent_users.set(count)
    
    def update_active_memories(self, user_id: str, count: int):
        """Update active memory count for a user."""
        self.active_memories.labels(user_id=user_id).set(count)
    
    def record_memory_operation(self, operation: str, status: str = 'success'):
        """Record a memory system operation."""
        self.memory_operations.labels(operation=operation, status=status).inc()
    
    @contextmanager
    def track_memory_consolidation(self):
        """Track memory consolidation duration."""
        start_time = time.time()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.memory_consolidation_duration.observe(duration)
    
    def record_rate_limit_hit(self, user_id: str, limit_type: str):
        """Record a rate limit hit."""
        self.rate_limit_hits.labels(user_id=user_id, limit_type=limit_type).inc()
    
    @contextmanager
    def track_llm_request(self, model: str):
        """Track LLM request duration and count."""
        start_time = time.time()
        status = 'success'
        
        try:
            yield
        except Exception as e:
            status = 'error'
            logger.error(f"LLM request failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self.llm_response_time.labels(model=model).observe(duration)
            self.llm_requests.labels(model=model, status=status).inc()
    
    def record_token_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Record LLM token usage."""
        self.token_usage.labels(model=model, token_type='input').inc(input_tokens)
        self.token_usage.labels(model=model, token_type='output').inc(output_tokens)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)
    
    def start_metrics_server(self, port: int = 8000):
        """Start HTTP server for metrics exposition."""
        start_http_server(port, registry=self.registry)
        logger.info(f"Metrics server started on port {port}")


def track_performance(operation: str, database: Optional[str] = None):
    """
    Decorator to track function performance.
    
    Args:
        operation: Name of the operation
        database: Optional database name for DB operations
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if database:
                with monitor.track_db_operation(database, operation):
                    return func(*args, **kwargs)
            else:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    monitor.record_memory_operation(operation, 'success')
                    return result
                except Exception as e:
                    monitor.record_memory_operation(operation, 'error')
                    raise
                finally:
                    duration = time.time() - start_time
                    monitor.response_time_percentile.observe(duration)
        
        return wrapper
    return decorator


# Global monitor instance
monitor = PerformanceMonitor()