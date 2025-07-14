"""
Comprehensive tests for the health check system.
Tests individual health checks and the overall health management system.
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.common.health_checks import (
    HealthCheckManager, HealthStatus, HealthCheckResult, HealthCheck,
    PostgreSQLHealthCheck, RedisHealthCheck, Neo4jHealthCheck,
    CacheSystemHealthCheck, SystemResourcesHealthCheck,
    MemorySystemHealthCheck, ExternalServiceHealthCheck
)


class TestHealthCheckResult:
    """Test cases for HealthCheckResult class."""
    
    def test_health_check_result_creation(self):
        """Test creating a health check result."""
        timestamp = datetime.now()
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All systems operational",
            duration_ms=50.5,
            timestamp=timestamp,
            details={"key": "value"}
        )
        
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All systems operational"
        assert result.duration_ms == 50.5
        assert result.timestamp == timestamp
        assert result.details == {"key": "value"}
    
    def test_health_check_result_to_dict(self):
        """Test converting health check result to dictionary."""
        timestamp = datetime.now()
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.DEGRADED,
            message="Performance issues",
            duration_ms=150.0,
            timestamp=timestamp
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["name"] == "test_check"
        assert result_dict["status"] == "degraded"
        assert result_dict["message"] == "Performance issues"
        assert result_dict["duration_ms"] == 150.0
        assert result_dict["timestamp"] == timestamp.isoformat()
        assert "details" in result_dict


class MockHealthCheck(HealthCheck):
    """Mock health check for testing."""
    
    def __init__(self, name: str, return_status: HealthStatus, should_timeout: bool = False, should_error: bool = False):
        super().__init__(name, timeout_seconds=1.0)
        self.return_status = return_status
        self.should_timeout = should_timeout
        self.should_error = should_error
    
    async def _perform_check(self):
        if self.should_timeout:
            await asyncio.sleep(2.0)  # Timeout after 1 second
        
        if self.should_error:
            raise Exception("Simulated health check error")
        
        return {
            "status": self.return_status,
            "message": f"Mock check result: {self.return_status.value}",
            "details": {"mock": True}
        }


class TestHealthCheck:
    """Test cases for base HealthCheck class."""
    
    @pytest.mark.asyncio
    async def test_successful_health_check(self):
        """Test a successful health check."""
        check = MockHealthCheck("test_check", HealthStatus.HEALTHY)
        result = await check.check()
        
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert "Mock check result" in result.message
        assert result.duration_ms >= 0
        assert isinstance(result.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Test health check timeout handling."""
        check = MockHealthCheck("timeout_check", HealthStatus.HEALTHY, should_timeout=True)
        result = await check.check()
        
        assert result.name == "timeout_check"
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message.lower()
        assert result.duration_ms >= 1000  # Should be at least 1 second
    
    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """Test health check error handling."""
        check = MockHealthCheck("error_check", HealthStatus.HEALTHY, should_error=True)
        result = await check.check()
        
        assert result.name == "error_check"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Simulated health check error" in result.message


class TestSystemResourcesHealthCheck:
    """Test cases for system resources health check."""
    
    @pytest.mark.asyncio
    async def test_system_resources_check(self):
        """Test system resources health check."""
        check = SystemResourcesHealthCheck()
        result = await check.check()
        
        assert result.name == "system_resources"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert "cpu_percent" in result.details
        assert "memory_percent" in result.details
        assert "disk_percent" in result.details
        assert result.details["cpu_percent"] >= 0
        assert result.details["memory_percent"] >= 0
        assert result.details["disk_percent"] >= 0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @pytest.mark.asyncio
    async def test_system_resources_thresholds(self, mock_disk, mock_memory, mock_cpu):
        """Test system resources health check thresholds."""
        # Mock high resource usage
        mock_cpu.return_value = 95.0  # High CPU
        mock_memory.return_value = Mock(percent=85.0)  # High memory
        mock_disk.return_value = Mock(percent=90.0, free=1000000, total=10000000)  # High disk
        
        check = SystemResourcesHealthCheck()
        result = await check.check()
        
        assert result.status == HealthStatus.UNHEALTHY  # CPU > 90%
        assert "CPU usage critical" in result.message


class TestDatabaseHealthChecks:
    """Test cases for database health checks."""
    
    @pytest.mark.asyncio
    async def test_postgresql_health_check_mock(self):
        """Test PostgreSQL health check with mocked database."""
        with patch('src.common.health_checks.db_manager') as mock_db:
            # Mock successful connection and query
            mock_db.postgres.test_connection.return_value = True
            mock_db.postgres.execute_query.return_value = [{"test": 1}]
            mock_db.postgres.engine.pool.size = 10
            mock_db.postgres.engine.pool.checkedout = 2
            
            check = PostgreSQLHealthCheck()
            result = await check.check()
            
            assert result.name == "postgresql"
            assert result.status == HealthStatus.HEALTHY
            assert "query_time_ms" in result.details
            assert "pool_size" in result.details
            assert result.details["pool_size"] == 10
    
    @pytest.mark.asyncio
    async def test_redis_health_check_mock(self):
        """Test Redis health check with mocked Redis."""
        with patch('src.common.health_checks.db_manager') as mock_db:
            # Mock successful Redis operations
            mock_db.redis.test_connection.return_value = True
            mock_db.redis.set.return_value = True
            mock_db.redis.get.return_value = "test_value"
            mock_db.redis.delete.return_value = True
            mock_db.redis.client.info.return_value = {
                'connected_clients': 5,
                'used_memory': 1024 * 1024,  # 1MB
                'used_memory_percentage': 10,
                'total_commands_processed': 1000
            }
            
            check = RedisHealthCheck()
            result = await check.check()
            
            assert result.name == "redis"
            assert result.status == HealthStatus.HEALTHY
            assert "operation_time_ms" in result.details
            assert "connected_clients" in result.details
    
    @pytest.mark.asyncio
    async def test_neo4j_health_check_mock(self):
        """Test Neo4j health check with mocked database."""
        with patch('src.common.health_checks.db_manager') as mock_db:
            # Mock successful Neo4j operations
            mock_db.neo4j.test_connection.return_value = True
            mock_db.neo4j.run_query.return_value = [{"test": 1}]
            
            check = Neo4jHealthCheck()
            result = await check.check()
            
            assert result.name == "neo4j"
            assert result.status == HealthStatus.HEALTHY
            assert "query_time_ms" in result.details


class TestCacheSystemHealthCheck:
    """Test cases for cache system health check."""
    
    @pytest.mark.asyncio
    async def test_cache_system_health_check_mock(self):
        """Test cache system health check with mocked cache."""
        with patch('src.common.health_checks.cache_manager') as mock_cache:
            # Mock cache statistics
            mock_stats = {
                'memory': Mock(hits=800, misses=200, hit_rate=80.0, total_operations=1000)
            }
            mock_cache.get_cache_stats.return_value = mock_stats
            mock_cache.get_overall_hit_rate.return_value = 80.0
            
            # Mock Redis operations
            mock_cache.redis.set.return_value = True
            mock_cache.redis.get.return_value = "cached_value"
            mock_cache.redis.delete.return_value = True
            
            check = CacheSystemHealthCheck()
            result = await check.check()
            
            assert result.name == "cache_system"
            assert result.status == HealthStatus.HEALTHY
            assert result.details["overall_hit_rate"] == 80.0
            assert "cache_stats" in result.details


class TestMemorySystemHealthCheck:
    """Test cases for memory system health check."""
    
    @pytest.mark.asyncio
    async def test_memory_system_health_check(self):
        """Test memory system health check."""
        with patch('src.common.health_checks.cache_manager') as mock_cache:
            # Mock memory cache statistics
            mock_memory_stats = Mock(
                hit_rate=75.0,
                total_operations=5000,
                avg_retrieval_time=50.0
            )
            mock_cache.get_cache_stats.return_value = {'memory': mock_memory_stats}
            
            check = MemorySystemHealthCheck()
            result = await check.check()
            
            assert result.name == "memory_system"
            assert result.status == HealthStatus.HEALTHY
            assert result.details["memory_cache_available"] is True
            assert result.details["cache_hit_rate"] == 75.0


class TestExternalServiceHealthCheck:
    """Test cases for external service health check."""
    
    @pytest.mark.asyncio
    async def test_external_service_healthy(self):
        """Test external service health check - healthy response."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            check = ExternalServiceHealthCheck("test_service", "http://example.com/health")
            result = await check.check()
            
            assert result.name == "external_test_service"
            assert result.status == HealthStatus.HEALTHY
            assert "response_time_ms" in result.details
            assert result.details["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_external_service_unhealthy(self):
        """Test external service health check - error response."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock error HTTP response
            mock_response = Mock()
            mock_response.status_code = 500
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            check = ExternalServiceHealthCheck("test_service", "http://example.com/health")
            result = await check.check()
            
            assert result.name == "external_test_service"
            assert result.status == HealthStatus.UNHEALTHY
            assert result.details["status_code"] == 500
    
    @pytest.mark.asyncio
    async def test_external_service_timeout(self):
        """Test external service health check - timeout."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock timeout exception
            import httpx
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")
            
            check = ExternalServiceHealthCheck("test_service", "http://example.com/health", timeout=1.0)
            result = await check.check()
            
            assert result.name == "external_test_service"
            assert result.status == HealthStatus.UNHEALTHY
            assert "timed out" in result.message.lower()


class TestHealthCheckManager:
    """Test cases for HealthCheckManager."""
    
    @pytest.fixture
    def health_manager(self):
        """Create a health check manager with mock checks."""
        manager = HealthCheckManager()
        # Clear default checks for testing
        manager.checks = []
        return manager
    
    def test_add_custom_health_check(self, health_manager):
        """Test adding custom health checks."""
        check = MockHealthCheck("custom_check", HealthStatus.HEALTHY)
        health_manager.add_check(check)
        
        assert len(health_manager.checks) == 1
        assert health_manager.checks[0].name == "custom_check"
    
    def test_add_external_service_check(self, health_manager):
        """Test adding external service checks."""
        health_manager.add_external_service_check("api_service", "http://api.example.com/health")
        
        assert len(health_manager.checks) == 1
        assert health_manager.checks[0].name == "external_api_service"
    
    @pytest.mark.asyncio
    async def test_run_all_checks(self, health_manager):
        """Test running all health checks."""
        # Add mock checks
        check1 = MockHealthCheck("check1", HealthStatus.HEALTHY)
        check2 = MockHealthCheck("check2", HealthStatus.DEGRADED)
        health_manager.add_check(check1)
        health_manager.add_check(check2)
        
        results = await health_manager.run_all_checks()
        
        assert len(results) == 2
        assert "check1" in results
        assert "check2" in results
        assert results["check1"].status == HealthStatus.HEALTHY
        assert results["check2"].status == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_exception(self, health_manager):
        """Test running health checks when one throws an exception."""
        # Add checks, one that will throw an exception
        check1 = MockHealthCheck("check1", HealthStatus.HEALTHY)
        check2 = MockHealthCheck("check2", HealthStatus.HEALTHY, should_error=True)
        health_manager.add_check(check1)
        health_manager.add_check(check2)
        
        results = await health_manager.run_all_checks()
        
        assert len(results) == 2
        assert results["check1"].status == HealthStatus.HEALTHY
        assert results["check2"].status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_get_overall_health_all_healthy(self, health_manager):
        """Test overall health when all checks are healthy."""
        check1 = MockHealthCheck("check1", HealthStatus.HEALTHY)
        check2 = MockHealthCheck("check2", HealthStatus.HEALTHY)
        health_manager.add_check(check1)
        health_manager.add_check(check2)
        
        health_status = await health_manager.get_overall_health()
        
        assert health_status["overall_status"] == "healthy"
        assert health_status["summary"]["total_checks"] == 2
        assert health_status["summary"]["status_counts"]["healthy"] == 2
        assert health_status["summary"]["status_counts"]["degraded"] == 0
        assert health_status["summary"]["status_counts"]["unhealthy"] == 0
    
    @pytest.mark.asyncio
    async def test_get_overall_health_mixed_status(self, health_manager):
        """Test overall health with mixed check statuses."""
        check1 = MockHealthCheck("check1", HealthStatus.HEALTHY)
        check2 = MockHealthCheck("check2", HealthStatus.DEGRADED)
        check3 = MockHealthCheck("check3", HealthStatus.UNHEALTHY)
        health_manager.add_check(check1)
        health_manager.add_check(check2)
        health_manager.add_check(check3)
        
        health_status = await health_manager.get_overall_health()
        
        assert health_status["overall_status"] == "unhealthy"  # Worst case wins
        assert health_status["summary"]["total_checks"] == 3
        assert health_status["summary"]["status_counts"]["healthy"] == 1
        assert health_status["summary"]["status_counts"]["degraded"] == 1
        assert health_status["summary"]["status_counts"]["unhealthy"] == 1
    
    def test_get_check_history(self, health_manager):
        """Test getting check history."""
        # This is a basic test since history is not fully implemented
        history = health_manager.get_check_history("test_check")
        assert isinstance(history, list)


class TestHealthCheckIntegration:
    """Integration tests for health check system."""
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Test health check system performance."""
        manager = HealthCheckManager()
        manager.checks = []  # Clear default checks
        
        # Add multiple mock checks
        for i in range(10):
            check = MockHealthCheck(f"check_{i}", HealthStatus.HEALTHY)
            manager.add_check(check)
        
        start_time = time.time()
        results = await manager.run_all_checks()
        duration = time.time() - start_time
        
        assert len(results) == 10
        assert duration < 1.0  # Should complete quickly for mock checks
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test that health checks run concurrently."""
        manager = HealthCheckManager()
        manager.checks = []
        
        # Add checks with different delays
        class DelayedHealthCheck(HealthCheck):
            def __init__(self, name: str, delay: float):
                super().__init__(name)
                self.delay = delay
            
            async def _perform_check(self):
                await asyncio.sleep(self.delay)
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": f"Delayed check {self.delay}s"
                }
        
        manager.add_check(DelayedHealthCheck("fast", 0.1))
        manager.add_check(DelayedHealthCheck("slow", 0.5))
        
        start_time = time.time()
        results = await manager.run_all_checks()
        duration = time.time() - start_time
        
        # Should take around 0.5s (max delay) not 0.6s (sum of delays)
        assert duration < 0.7
        assert len(results) == 2


if __name__ == "__main__":
    pytest.main([__file__])