"""
Comprehensive health check system for AI Companion services.
Provides detailed health monitoring for all system components.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import psutil
import httpx

from .database import db_manager
from .cache import cache_manager
from .monitoring import monitor

import logging
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


class HealthCheck:
    """Base health check class."""
    
    def __init__(self, name: str, timeout_seconds: float = 30.0):
        self.name = name
        self.timeout_seconds = timeout_seconds
    
    async def check(self) -> HealthCheckResult:
        """
        Perform the health check.
        
        Returns:
            HealthCheckResult with status and details
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            result = await asyncio.wait_for(
                self._perform_check(),
                timeout=self.timeout_seconds
            )
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=self.name,
                status=result["status"],
                message=result["message"],
                duration_ms=duration_ms,
                timestamp=timestamp,
                details=result.get("details", {})
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                duration_ms=duration_ms,
                timestamp=timestamp
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=timestamp
            )
    
    async def _perform_check(self) -> Dict[str, Any]:
        """
        Perform the actual health check logic.
        Must be implemented by subclasses.
        
        Returns:
            Dictionary with status, message, and optional details
        """
        raise NotImplementedError


class PostgreSQLHealthCheck(HealthCheck):
    """PostgreSQL database health check."""
    
    def __init__(self):
        super().__init__("postgresql", timeout_seconds=10.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check PostgreSQL connection and performance."""
        try:
            # Test basic connection
            if not db_manager.postgres.test_connection():
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Cannot connect to PostgreSQL database"
                }
            
            # Test query performance
            start_time = time.time()
            result = db_manager.postgres.execute_query("SELECT 1 as test")
            query_time = (time.time() - start_time) * 1000
            
            if not result or result[0]["test"] != 1:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "PostgreSQL query returned unexpected result"
                }
            
            # Check connection pool status (simplified)
            pool_size = getattr(db_manager.postgres.engine.pool, 'size', 0)
            checked_out = getattr(db_manager.postgres.engine.pool, 'checkedout', 0)
            
            status = HealthStatus.HEALTHY
            message = "PostgreSQL is healthy"
            
            # Check for performance degradation
            if query_time > 1000:  # 1 second
                status = HealthStatus.DEGRADED
                message = f"PostgreSQL query slow: {query_time:.2f}ms"
            
            # Check for pool exhaustion
            if pool_size > 0 and (checked_out / pool_size) > 0.8:
                status = HealthStatus.DEGRADED
                message = "PostgreSQL connection pool nearly exhausted"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "query_time_ms": query_time,
                    "pool_size": pool_size,
                    "connections_checked_out": checked_out,
                    "pool_utilization": (checked_out / pool_size) if pool_size > 0 else 0
                }
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"PostgreSQL health check failed: {str(e)}"
            }


class RedisHealthCheck(HealthCheck):
    """Redis cache health check."""
    
    def __init__(self):
        super().__init__("redis", timeout_seconds=5.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check Redis connection and performance."""
        try:
            # Test basic connection
            if not db_manager.redis.test_connection():
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Cannot connect to Redis"
                }
            
            # Test read/write performance
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"
            
            start_time = time.time()
            db_manager.redis.set(test_key, test_value, ex=60)
            retrieved_value = db_manager.redis.get(test_key)
            operation_time = (time.time() - start_time) * 1000
            
            # Clean up
            db_manager.redis.delete(test_key)
            
            if retrieved_value != test_value:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Redis read/write test failed"
                }
            
            # Get Redis info
            redis_info = {}
            try:
                redis_info = db_manager.redis.client.info()
            except Exception:
                pass
            
            status = HealthStatus.HEALTHY
            message = "Redis is healthy"
            
            # Check for performance degradation
            if operation_time > 100:  # 100ms
                status = HealthStatus.DEGRADED
                message = f"Redis operations slow: {operation_time:.2f}ms"
            
            # Check memory usage
            if redis_info.get('used_memory_percentage', 0) > 80:
                status = HealthStatus.DEGRADED
                message = "Redis memory usage high"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "operation_time_ms": operation_time,
                    "connected_clients": redis_info.get('connected_clients', 0),
                    "used_memory_mb": redis_info.get('used_memory', 0) / (1024 * 1024),
                    "used_memory_percentage": redis_info.get('used_memory_percentage', 0),
                    "total_commands_processed": redis_info.get('total_commands_processed', 0)
                }
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Redis health check failed: {str(e)}"
            }


class Neo4jHealthCheck(HealthCheck):
    """Neo4j graph database health check."""
    
    def __init__(self):
        super().__init__("neo4j", timeout_seconds=10.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check Neo4j connection and performance."""
        try:
            # Test basic connection
            if not db_manager.neo4j.test_connection():
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Cannot connect to Neo4j database"
                }
            
            # Test query performance
            start_time = time.time()
            result = db_manager.neo4j.run_query("RETURN 1 as test")
            query_time = (time.time() - start_time) * 1000
            
            if not result or result[0]["test"] != 1:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Neo4j query returned unexpected result"
                }
            
            # Get database statistics
            stats_query = """
            CALL apoc.monitor.store() YIELD heapUsed, heapMax
            RETURN heapUsed, heapMax
            """
            
            heap_info = {}
            try:
                heap_result = db_manager.neo4j.run_query(stats_query)
                if heap_result:
                    heap_info = heap_result[0]
            except Exception:
                # APOC might not be available
                pass
            
            status = HealthStatus.HEALTHY
            message = "Neo4j is healthy"
            
            # Check for performance degradation
            if query_time > 2000:  # 2 seconds
                status = HealthStatus.DEGRADED
                message = f"Neo4j query slow: {query_time:.2f}ms"
            
            # Check heap usage if available
            if heap_info and heap_info.get('heapMax', 0) > 0:
                heap_usage = heap_info['heapUsed'] / heap_info['heapMax']
                if heap_usage > 0.8:
                    status = HealthStatus.DEGRADED
                    message = "Neo4j heap usage high"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "query_time_ms": query_time,
                    "heap_used_mb": heap_info.get('heapUsed', 0) / (1024 * 1024),
                    "heap_max_mb": heap_info.get('heapMax', 0) / (1024 * 1024),
                    "heap_utilization": heap_info.get('heapUsed', 0) / heap_info.get('heapMax', 1) if heap_info.get('heapMax', 0) > 0 else 0
                }
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Neo4j health check failed: {str(e)}"
            }


class CacheSystemHealthCheck(HealthCheck):
    """Cache system health check."""
    
    def __init__(self):
        super().__init__("cache_system", timeout_seconds=5.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check cache system performance."""
        try:
            # Get cache statistics
            cache_stats = cache_manager.get_cache_stats()
            overall_hit_rate = cache_manager.get_overall_hit_rate()
            
            status = HealthStatus.HEALTHY
            message = "Cache system is healthy"
            
            # Check cache hit rates
            if overall_hit_rate < 50:  # Less than 50% hit rate
                status = HealthStatus.DEGRADED
                message = f"Cache hit rate low: {overall_hit_rate:.1f}%"
            elif overall_hit_rate < 30:  # Very low hit rate
                status = HealthStatus.UNHEALTHY
                message = f"Cache hit rate critical: {overall_hit_rate:.1f}%"
            
            # Test cache operations
            test_key = "health_check_cache_test"
            test_data = {"timestamp": time.time(), "test": True}
            
            start_time = time.time()
            cache_manager.redis.set(test_key, str(test_data), ex=60)
            retrieved = cache_manager.redis.get(test_key)
            operation_time = (time.time() - start_time) * 1000
            
            # Clean up
            cache_manager.redis.delete(test_key)
            
            if not retrieved:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Cache read/write test failed"
                }
            
            if operation_time > 50:  # 50ms threshold
                status = HealthStatus.DEGRADED
                message = f"Cache operations slow: {operation_time:.2f}ms"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "overall_hit_rate": overall_hit_rate,
                    "operation_time_ms": operation_time,
                    "cache_stats": {k: {
                        "hits": v.hits,
                        "misses": v.misses,
                        "hit_rate": v.hit_rate,
                        "total_operations": v.total_operations
                    } for k, v in cache_stats.items()}
                }
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Cache system health check failed: {str(e)}"
            }


class SystemResourcesHealthCheck(HealthCheck):
    """System resources health check."""
    
    def __init__(self):
        super().__init__("system_resources", timeout_seconds=5.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = HealthStatus.HEALTHY
            messages = []
            
            # Check CPU usage
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                messages.append(f"CPU usage critical: {cpu_percent:.1f}%")
            elif cpu_percent > 80:
                status = HealthStatus.DEGRADED
                messages.append(f"CPU usage high: {cpu_percent:.1f}%")
            
            # Check memory usage
            memory_percent = memory.percent
            if memory_percent > 90:
                status = HealthStatus.UNHEALTHY
                messages.append(f"Memory usage critical: {memory_percent:.1f}%")
            elif memory_percent > 80:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                messages.append(f"Memory usage high: {memory_percent:.1f}%")
            
            # Check disk usage
            disk_percent = disk.percent
            if disk_percent > 95:
                status = HealthStatus.UNHEALTHY
                messages.append(f"Disk usage critical: {disk_percent:.1f}%")
            elif disk_percent > 85:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                messages.append(f"Disk usage high: {disk_percent:.1f}%")
            
            message = "System resources healthy" if not messages else "; ".join(messages)
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "memory_total_gb": memory.total / (1024**3),
                    "disk_percent": disk_percent,
                    "disk_free_gb": disk.free / (1024**3),
                    "disk_total_gb": disk.total / (1024**3)
                }
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"System resources health check failed: {str(e)}"
            }


class MemorySystemHealthCheck(HealthCheck):
    """Memory system health check."""
    
    def __init__(self):
        super().__init__("memory_system", timeout_seconds=10.0)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check memory system health."""
        try:
            # This would integrate with the actual memory manager
            # For now, we'll check basic functionality
            
            status = HealthStatus.HEALTHY
            message = "Memory system is healthy"
            
            # Get memory-related cache statistics
            memory_cache_stats = cache_manager.get_cache_stats().get('memory', None)
            
            details = {
                "memory_cache_available": memory_cache_stats is not None
            }
            
            if memory_cache_stats:
                hit_rate = memory_cache_stats.hit_rate
                if hit_rate < 60:  # Memory cache hit rate below 60%
                    status = HealthStatus.DEGRADED
                    message = f"Memory cache hit rate low: {hit_rate:.1f}%"
                
                details.update({
                    "cache_hit_rate": hit_rate,
                    "cache_operations": memory_cache_stats.total_operations,
                    "cache_avg_retrieval_time": memory_cache_stats.avg_retrieval_time
                })
            
            # You could add more memory system specific checks here
            # - Check for consolidation backlog
            # - Check embedding generation performance
            # - Check forgetting curve processing
            
            return {
                "status": status,
                "message": message,
                "details": details
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Memory system health check failed: {str(e)}"
            }


class ExternalServiceHealthCheck(HealthCheck):
    """External service health check (e.g., LLM APIs)."""
    
    def __init__(self, service_name: str, url: str, timeout: float = 10.0):
        super().__init__(f"external_{service_name}", timeout_seconds=timeout)
        self.service_name = service_name
        self.url = url
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check external service availability."""
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, timeout=self.timeout_seconds)
                
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY
            message = f"{self.service_name} is healthy"
            
            if response.status_code != 200:
                status = HealthStatus.UNHEALTHY
                message = f"{self.service_name} returned status {response.status_code}"
            elif response_time > 5000:  # 5 seconds
                status = HealthStatus.DEGRADED
                message = f"{self.service_name} response slow: {response_time:.2f}ms"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "response_time_ms": response_time,
                    "status_code": response.status_code,
                    "url": self.url
                }
            }
            
        except httpx.TimeoutException:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"{self.service_name} request timed out"
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"{self.service_name} health check failed: {str(e)}"
            }


class HealthCheckManager:
    """Manages all health checks for the system."""
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.last_results: Dict[str, HealthCheckResult] = {}
        self._setup_default_checks()
    
    def _setup_default_checks(self):
        """Set up default health checks."""
        self.checks = [
            PostgreSQLHealthCheck(),
            RedisHealthCheck(),
            Neo4jHealthCheck(),
            CacheSystemHealthCheck(),
            SystemResourcesHealthCheck(),
            MemorySystemHealthCheck()
        ]
    
    def add_check(self, check: HealthCheck):
        """Add a custom health check."""
        self.checks.append(check)
    
    def add_external_service_check(self, service_name: str, url: str, timeout: float = 10.0):
        """Add an external service health check."""
        check = ExternalServiceHealthCheck(service_name, url, timeout)
        self.add_check(check)
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks concurrently."""
        tasks = [check.check() for check in self.checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_results = {}
        for i, result in enumerate(results):
            check_name = self.checks[i].name
            
            if isinstance(result, Exception):
                # Handle exceptions from health checks
                health_results[check_name] = HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(result)}",
                    duration_ms=0.0,
                    timestamp=datetime.now()
                )
            else:
                health_results[check_name] = result
        
        self.last_results = health_results
        return health_results
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        results = await self.run_all_checks()
        
        # Determine overall status
        statuses = [result.status for result in results.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Count statuses
        status_counts = {
            "healthy": sum(1 for s in statuses if s == HealthStatus.HEALTHY),
            "degraded": sum(1 for s in statuses if s == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for s in statuses if s == HealthStatus.UNHEALTHY),
            "unknown": sum(1 for s in statuses if s == HealthStatus.UNKNOWN)
        }
        
        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {name: result.to_dict() for name, result in results.items()},
            "summary": {
                "total_checks": len(results),
                "status_counts": status_counts
            }
        }
    
    def get_check_history(self, check_name: str, hours: int = 24) -> List[HealthCheckResult]:
        """Get historical results for a specific check."""
        # This would typically be stored in a database
        # For now, return the last result if available
        if check_name in self.last_results:
            return [self.last_results[check_name]]
        return []


# Global health check manager
health_manager = HealthCheckManager()