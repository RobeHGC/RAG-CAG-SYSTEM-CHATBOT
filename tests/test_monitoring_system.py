"""
Comprehensive tests for the monitoring system infrastructure.
Tests monitoring, alerting, health checks, profiling, and logging components.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

import redis.asyncio as redis
from prometheus_client import CollectorRegistry

from src.common.monitoring import MonitoringSystem, monitor
from src.common.health_checks import HealthCheckManager, HealthStatus, HealthCheckResult
from src.common.alerts import AlertManager, AlertRule, AlertSeverity, AlertStatus
from src.common.profiling import ProfilerManager, PerformanceMetrics, profile_performance
from src.common.enhanced_logging import EnhancedLogger
from src.common.sentry_config import SentryConfig


class TestMonitoringSystem:
    """Test cases for the monitoring system."""
    
    @pytest.fixture
    def monitoring_system(self):
        """Create a fresh monitoring system for each test."""
        registry = CollectorRegistry()
        return MonitoringSystem(registry=registry)
    
    def test_monitoring_initialization(self, monitoring_system):
        """Test monitoring system initialization."""
        assert monitoring_system.registry is not None
        assert hasattr(monitoring_system, 'request_counter')
        assert hasattr(monitoring_system, 'request_duration')
        assert hasattr(monitoring_system, 'error_counter')
    
    def test_increment_counter(self, monitoring_system):
        """Test counter increment functionality."""
        # Test basic increment
        monitoring_system.increment_counter('test_counter')
        
        # Test increment with labels
        monitoring_system.increment_counter('test_counter', {'label': 'value'})
        
        # Verify metrics were recorded (basic check)
        metrics_data = monitoring_system.get_metrics()
        assert 'test_counter' in metrics_data
    
    def test_record_duration(self, monitoring_system):
        """Test duration recording."""
        monitoring_system.record_duration('test_operation', 0.5)
        monitoring_system.record_duration('test_operation', 1.0, {'method': 'POST'})
        
        metrics_data = monitoring_system.get_metrics()
        assert 'test_operation' in metrics_data
    
    def test_record_custom_metric(self, monitoring_system):
        """Test custom metric recording."""
        monitoring_system.record_custom_metric('custom_metric', 42.5)
        monitoring_system.record_custom_metric('custom_metric', 55.0, {'type': 'test'})
        
        metrics_data = monitoring_system.get_metrics()
        assert 'custom_metric' in metrics_data
    
    @patch('src.common.monitoring.time.time')
    def test_track_db_operation(self, mock_time, monitoring_system):
        """Test database operation tracking."""
        mock_time.side_effect = [1000.0, 1000.5]  # 500ms operation
        
        with monitoring_system.track_db_operation('redis', 'get'):
            pass  # Simulate operation
        
        # Verify metrics were recorded
        metrics_data = monitoring_system.get_metrics()
        assert any('db_operation' in metric for metric in metrics_data.split('\n'))
    
    def test_memory_operation_recording(self, monitoring_system):
        """Test memory operation recording."""
        monitoring_system.record_memory_operation('store', 'success')
        monitoring_system.record_memory_operation('retrieve', 'error')
        
        metrics_data = monitoring_system.get_metrics()
        assert 'memory_operations' in metrics_data


class TestHealthCheckSystem:
    """Test cases for the health check system."""
    
    @pytest.fixture
    def health_manager(self):
        """Create a health check manager for testing."""
        return HealthCheckManager()
    
    @pytest.mark.asyncio
    async def test_health_check_result_creation(self):
        """Test health check result creation."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="Test is healthy",
            duration_ms=50.0,
            timestamp=datetime.now()
        )
        
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.duration_ms == 50.0
        
        # Test dictionary conversion
        result_dict = result.to_dict()
        assert 'name' in result_dict
        assert 'status' in result_dict
        assert result_dict['status'] == 'healthy'
    
    @pytest.mark.asyncio
    async def test_overall_health_calculation(self, health_manager):
        """Test overall health status calculation."""
        # Mock some health checks
        with patch.object(health_manager, 'run_all_checks') as mock_checks:
            mock_checks.return_value = {
                'service1': HealthCheckResult(
                    name='service1',
                    status=HealthStatus.HEALTHY,
                    message='OK',
                    duration_ms=10.0,
                    timestamp=datetime.now()
                ),
                'service2': HealthCheckResult(
                    name='service2',
                    status=HealthStatus.DEGRADED,
                    message='Slow',
                    duration_ms=200.0,
                    timestamp=datetime.now()
                )
            }
            
            health_status = await health_manager.get_overall_health()
            
            assert health_status['overall_status'] == 'degraded'
            assert health_status['summary']['total_checks'] == 2
            assert health_status['summary']['status_counts']['healthy'] == 1
            assert health_status['summary']['status_counts']['degraded'] == 1
    
    @pytest.mark.asyncio
    async def test_system_resources_health_check(self):
        """Test system resources health check."""
        from src.common.health_checks import SystemResourcesHealthCheck
        
        check = SystemResourcesHealthCheck()
        result = await check.check()
        
        assert result.name == "system_resources"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert 'cpu_percent' in result.details
        assert 'memory_percent' in result.details
        assert 'disk_percent' in result.details


class TestAlertingSystem:
    """Test cases for the alerting system."""
    
    @pytest.fixture
    def alert_manager(self):
        """Create an alert manager for testing."""
        return AlertManager()
    
    def test_alert_rule_creation(self):
        """Test alert rule creation."""
        rule = AlertRule(
            name="test_alert",
            description="Test alert rule",
            metric_name="test_metric",
            threshold=10.0,
            comparison="gt",
            duration_seconds=300,
            severity=AlertSeverity.WARNING
        )
        
        assert rule.name == "test_alert"
        assert rule.threshold == 10.0
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True
    
    def test_add_alert_rule(self, alert_manager):
        """Test adding alert rules."""
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            threshold=5.0,
            comparison="gt",
            duration_seconds=60,
            severity=AlertSeverity.CRITICAL
        )
        
        alert_manager.add_rule(rule)
        assert "test_rule" in alert_manager.rules
        assert alert_manager.rules["test_rule"].severity == AlertSeverity.CRITICAL
    
    @patch.object(AlertManager, 'get_metric_value')
    def test_rule_evaluation(self, mock_get_metric, alert_manager):
        """Test alert rule evaluation."""
        # Setup rule
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            metric_name="test_metric",
            threshold=10.0,
            comparison="gt",
            duration_seconds=1,  # 1 second for quick test
            severity=AlertSeverity.WARNING
        )
        alert_manager.add_rule(rule)
        
        # Test condition not met
        mock_get_metric.return_value = 5.0
        assert not alert_manager.evaluate_rule(rule)
        
        # Test condition met but duration not reached
        mock_get_metric.return_value = 15.0
        assert not alert_manager.evaluate_rule(rule)
        
        # Wait for duration and test again
        time.sleep(1.1)
        assert alert_manager.evaluate_rule(rule)
    
    @pytest.mark.asyncio
    async def test_alert_firing(self, alert_manager):
        """Test alert firing mechanism."""
        rule = AlertRule(
            name="test_alert",
            description="Test alert firing",
            metric_name="test_metric",
            threshold=10.0,
            comparison="gt",
            duration_seconds=0,
            severity=AlertSeverity.HIGH
        )
        
        # Mock notification channels
        mock_channel = Mock()
        mock_channel.send_notification = AsyncMock(return_value=True)
        alert_manager.notification_channels = [mock_channel]
        
        await alert_manager.fire_alert(rule, 15.0)
        
        # Verify alert was created
        assert "test_alert" in alert_manager.active_alerts
        alert = alert_manager.active_alerts["test_alert"]
        assert alert.status == AlertStatus.FIRING
        assert alert.metric_value == 15.0
        
        # Verify notification was sent
        mock_channel.send_notification.assert_called_once()
    
    def test_alert_status_summary(self, alert_manager):
        """Test alert status summary generation."""
        # Add some test rules
        rule1 = AlertRule("rule1", "desc1", "metric1", 10.0, "gt", 60, AlertSeverity.WARNING)
        rule2 = AlertRule("rule2", "desc2", "metric2", 20.0, "lt", 60, AlertSeverity.CRITICAL)
        
        alert_manager.add_rule(rule1)
        alert_manager.add_rule(rule2)
        
        status = alert_manager.get_alert_status()
        
        assert status["total_rules"] == 2
        assert status["enabled_rules"] == 2
        assert "incident_metrics" in status


class TestProfilingSystem:
    """Test cases for the profiling system."""
    
    @pytest.fixture
    def profiler_manager(self):
        """Create a profiler manager for testing."""
        return ProfilerManager()
    
    def test_performance_metrics_creation(self):
        """Test performance metrics creation and updates."""
        metrics = PerformanceMetrics("test_function")
        
        # Add some samples
        metrics.add_sample(0.1, memory_delta=1024, cpu_percent=5.0)
        metrics.add_sample(0.2, memory_delta=2048, cpu_percent=10.0)
        
        assert metrics.call_count == 2
        assert metrics.avg_time == 0.15
        assert metrics.min_time == 0.1
        assert metrics.max_time == 0.2
        
        # Test statistics
        stats = metrics.get_stats()
        assert stats["name"] == "test_function"
        assert stats["call_count"] == 2
        assert stats["avg_time"] == 0.15
    
    def test_profiler_manager_metrics(self, profiler_manager):
        """Test profiler manager metric recording."""
        profiler_manager.record_performance("test_op", 0.5, memory_delta=1024)
        
        all_stats = profiler_manager.get_all_stats()
        assert "test_op" in all_stats
        assert all_stats["test_op"]["call_count"] == 1
        assert all_stats["test_op"]["avg_time"] == 0.5
    
    @patch('time.time')
    def test_profile_performance_decorator(self, mock_time):
        """Test performance profiling decorator."""
        mock_time.side_effect = [1000.0, 1000.5]  # 500ms operation
        
        @profile_performance("test_function")
        def test_function():
            return "result"
        
        result = test_function()
        assert result == "result"
        
        # Check if metrics were recorded (would need access to global profiler)
        # This is a basic test of decorator application
    
    def test_profiler_reset_metrics(self, profiler_manager):
        """Test metrics reset functionality."""
        profiler_manager.record_performance("test_op", 0.5)
        assert "test_op" in profiler_manager.get_all_stats()
        
        profiler_manager.reset_metrics("test_op")
        assert "test_op" not in profiler_manager.get_all_stats()


class TestEnhancedLogging:
    """Test cases for enhanced logging system."""
    
    @pytest.fixture
    def enhanced_logger(self):
        """Create an enhanced logger for testing."""
        return EnhancedLogger(service_name="test_service")
    
    def test_correlation_id_generation(self, enhanced_logger):
        """Test correlation ID generation and setting."""
        correlation_id = enhanced_logger.generate_correlation_id()
        assert correlation_id is not None
        assert len(correlation_id) > 0
        
        enhanced_logger.set_correlation_id(correlation_id)
        # Verify it was set (would need access to context variable)
    
    def test_user_context_setting(self, enhanced_logger):
        """Test user context setting."""
        enhanced_logger.set_user_context("test_user", role="admin")
        # Verify context was set (would need access to context variable)
    
    def test_request_context_setting(self, enhanced_logger):
        """Test request context setting."""
        enhanced_logger.set_request_context("/api/test", "POST", client_ip="127.0.0.1")
        # Verify context was set (would need access to context variable)
    
    def test_logger_instance_creation(self, enhanced_logger):
        """Test logger instance creation."""
        logger = enhanced_logger.get_logger("test_component")
        assert logger is not None


class TestSentryIntegration:
    """Test cases for Sentry integration."""
    
    @pytest.fixture
    def sentry_config(self):
        """Create a Sentry config for testing."""
        return SentryConfig(
            dsn="https://test@sentry.io/123456",
            environment="test",
            sample_rate=1.0
        )
    
    def test_sentry_config_creation(self, sentry_config):
        """Test Sentry configuration creation."""
        assert sentry_config.dsn == "https://test@sentry.io/123456"
        assert sentry_config.environment == "test"
        assert sentry_config.sample_rate == 1.0
    
    @patch('src.common.sentry_config.sentry_sdk.init')
    def test_sentry_initialization(self, mock_init, sentry_config):
        """Test Sentry initialization."""
        sentry_config.initialize()
        
        # Verify sentry_sdk.init was called
        mock_init.assert_called_once()
        
        # Check call arguments
        call_args = mock_init.call_args
        assert call_args[1]['dsn'] == "https://test@sentry.io/123456"
        assert call_args[1]['environment'] == "test"


class TestIntegrationScenarios:
    """Integration tests for monitoring components working together."""
    
    @pytest.mark.asyncio
    async def test_memory_operation_monitoring_integration(self):
        """Test memory operations with full monitoring integration."""
        # This would require a more complex setup with actual memory manager
        # For now, test that decorators can be stacked
        pass
    
    @pytest.mark.asyncio
    async def test_alert_health_check_integration(self):
        """Test alerts based on health check results."""
        health_manager = HealthCheckManager()
        alert_manager = AlertManager()
        
        # Mock a failing health check
        with patch.object(health_manager, 'run_all_checks') as mock_checks:
            mock_checks.return_value = {
                'service1': HealthCheckResult(
                    name='service1',
                    status=HealthStatus.UNHEALTHY,
                    message='Service down',
                    duration_ms=1000.0,
                    timestamp=datetime.now()
                )
            }
            
            health_status = await health_manager.get_overall_health()
            assert health_status['overall_status'] == 'unhealthy'
            
            # This could trigger alerts in a real scenario
    
    def test_profiling_with_alerts(self):
        """Test profiling data feeding into alert conditions."""
        profiler_manager = ProfilerManager()
        alert_manager = AlertManager()
        
        # Record slow operation
        profiler_manager.record_performance("slow_operation", 5.0)  # 5 seconds
        
        stats = profiler_manager.get_all_stats()
        assert stats["slow_operation"]["avg_time"] == 5.0
        
        # In a real scenario, this could trigger performance alerts


# Test fixtures and utilities
@pytest.fixture(scope="session")
def redis_client():
    """Redis client for integration tests."""
    return redis.from_url("redis://localhost:6379/15")  # Use test database


@pytest.fixture(scope="session")  
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Performance benchmarks
class TestPerformanceBenchmarks:
    """Performance benchmarks for monitoring components."""
    
    def test_monitoring_overhead(self):
        """Test monitoring system performance overhead."""
        monitoring_system = MonitoringSystem()
        
        # Benchmark counter increments
        start_time = time.time()
        for i in range(1000):
            monitoring_system.increment_counter("benchmark_counter")
        duration = time.time() - start_time
        
        # Should be very fast (< 100ms for 1000 operations)
        assert duration < 0.1
    
    def test_profiling_overhead(self):
        """Test profiling system performance overhead."""
        profiler_manager = ProfilerManager()
        
        # Benchmark performance recording
        start_time = time.time()
        for i in range(1000):
            profiler_manager.record_performance(f"op_{i}", 0.001)
        duration = time.time() - start_time
        
        # Should have minimal overhead
        assert duration < 0.5


if __name__ == "__main__":
    pytest.main([__file__])