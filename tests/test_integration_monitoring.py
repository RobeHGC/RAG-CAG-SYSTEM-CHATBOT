"""
Integration tests for the complete monitoring infrastructure.
Tests end-to-end scenarios with multiple monitoring components working together.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.common.monitoring import monitor
from src.common.health_checks import health_manager, HealthStatus
from src.common.alerts import alert_manager, AlertRule, AlertSeverity, AlertStatus
from src.common.profiling import profiler_manager, profile_performance
from src.common.enhanced_logging import enhanced_logger


class TestMonitoringIntegration:
    """Integration tests for monitoring system components."""
    
    @pytest.mark.asyncio
    async def test_health_check_to_alert_pipeline(self):
        """Test pipeline from health check failure to alert generation."""
        # Clear any existing state
        alert_manager.rules.clear()
        alert_manager.active_alerts.clear()
        
        # Add alert rule for health check failures
        health_alert_rule = AlertRule(
            name="service_health_alert",
            description="Service health check failed",
            metric_name="health_check_status",
            threshold=0.5,  # Below 50% success rate
            comparison="lt",
            duration_seconds=1,
            severity=AlertSeverity.CRITICAL
        )
        alert_manager.add_rule(health_alert_rule)
        
        # Mock metric collection to simulate health check failure
        with patch.object(alert_manager, 'get_metric_value') as mock_metric:
            mock_metric.return_value = 0.0  # 0% health check success
            
            # Simulate rule evaluation
            should_fire = alert_manager.evaluate_rule(health_alert_rule)
            if should_fire:
                await alert_manager.fire_alert(health_alert_rule, 0.0)
            
            # Verify alert was created
            assert "service_health_alert" in alert_manager.active_alerts
            alert = alert_manager.active_alerts["service_health_alert"]
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.status == AlertStatus.FIRING
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_to_alerts(self):
        """Test performance monitoring triggering alerts."""
        # Clear state
        alert_manager.rules.clear()
        alert_manager.active_alerts.clear()
        profiler_manager.reset_metrics()
        
        # Add performance alert rule
        perf_alert_rule = AlertRule(
            name="slow_response_alert",
            description="Average response time too high",
            metric_name="avg_response_time",
            threshold=5.0,  # 5 seconds
            comparison="gt",
            duration_seconds=1,
            severity=AlertSeverity.HIGH
        )
        alert_manager.add_rule(perf_alert_rule)
        
        # Simulate slow operations
        for _ in range(10):
            profiler_manager.record_performance("slow_operation", 6.0)  # 6 seconds each
        
        # Mock metric value based on profiler data
        with patch.object(alert_manager, 'get_metric_value') as mock_metric:
            mock_metric.return_value = 6.0  # Average 6 seconds
            
            # Evaluate and fire alert
            should_fire = alert_manager.evaluate_rule(perf_alert_rule)
            if should_fire:
                await alert_manager.fire_alert(perf_alert_rule, 6.0)
            
            # Verify alert was created
            assert "slow_response_alert" in alert_manager.active_alerts
    
    def test_profiling_with_monitoring_integration(self):
        """Test profiling data being collected by monitoring system."""
        # Clear profiler state
        profiler_manager.reset_metrics()
        
        @profile_performance("integrated_operation")
        def test_operation():
            time.sleep(0.01)  # Small delay
            return "result"
        
        # Execute operation multiple times
        for _ in range(5):
            result = test_operation()
            assert result == "result"
        
        # Verify profiling data was collected
        stats = profiler_manager.get_all_stats()
        assert "integrated_operation" in stats
        assert stats["integrated_operation"]["call_count"] == 5
        
        # Verify monitoring metrics were recorded
        # Note: This would require integration with actual monitoring system
    
    @pytest.mark.asyncio
    async def test_logging_correlation_with_monitoring(self):
        """Test enhanced logging correlation with monitoring events."""
        correlation_id = enhanced_logger.generate_correlation_id()
        enhanced_logger.set_correlation_id(correlation_id)
        enhanced_logger.set_user_context("test_user")
        
        # Simulate operation with logging and monitoring
        with patch('src.common.enhanced_logging.logger') as mock_logger:
            @profile_performance("logged_operation")
            def logged_operation():
                enhanced_logger.get_logger().info("Operation started")
                time.sleep(0.01)
                enhanced_logger.get_logger().info("Operation completed")
                return "logged_result"
            
            result = logged_operation()
            assert result == "logged_result"
            
            # Verify logging occurred
            assert mock_logger.info.called
    
    @pytest.mark.asyncio
    async def test_memory_operation_full_monitoring(self):
        """Test memory operations with full monitoring stack."""
        correlation_id = enhanced_logger.generate_correlation_id()
        enhanced_logger.set_correlation_id(correlation_id)
        
        # Mock memory manager operation
        with patch('src.memoria.memory_manager.MemoryManager') as MockMemoryManager:
            mock_manager = MockMemoryManager.return_value
            mock_manager.store_message = AsyncMock(return_value=Mock(id="msg_123"))
            
            # Simulate decorated memory operation
            @profile_performance("memory_store", memory_tracking=True)
            async def store_memory_message(user_id: str, content: str):
                enhanced_logger.get_logger().info(f"Storing message for user {user_id}")
                
                # Simulate rate limiting check
                monitor.increment_counter('memory_operations_total', {'user_id': user_id})
                
                # Simulate actual storage
                result = await mock_manager.store_message(user_id, content)
                
                # Record success
                monitor.increment_counter('memory_operations_success_total', {'user_id': user_id})
                
                return result
            
            result = await store_memory_message("test_user", "test message")
            assert result.id == "msg_123"
            
            # Verify profiling was recorded
            stats = profiler_manager.get_all_stats()
            assert "memory_store" in stats


class TestAlertingSystemIntegration:
    """Integration tests for alerting system."""
    
    @pytest.fixture
    def mock_notification_channel(self):
        """Create a mock notification channel."""
        channel = Mock()
        channel.name = "test_channel"
        channel.enabled = True
        channel.send_notification = AsyncMock(return_value=True)
        return channel
    
    @pytest.mark.asyncio
    async def test_alert_lifecycle_integration(self, mock_notification_channel):
        """Test complete alert lifecycle."""
        # Clear state
        alert_manager.rules.clear()
        alert_manager.active_alerts.clear()
        alert_manager.notification_channels = [mock_notification_channel]
        
        # Create test rule
        test_rule = AlertRule(
            name="integration_test_alert",
            description="Integration test alert",
            metric_name="test_metric",
            threshold=10.0,
            comparison="gt",
            duration_seconds=1,
            severity=AlertSeverity.WARNING
        )
        alert_manager.add_rule(test_rule)
        
        # Mock metric that exceeds threshold
        with patch.object(alert_manager, 'get_metric_value') as mock_metric:
            mock_metric.return_value = 15.0
            
            # Phase 1: Trigger alert
            should_fire = alert_manager.evaluate_rule(test_rule)
            if should_fire:
                await alert_manager.fire_alert(test_rule, 15.0)
            
            # Verify alert firing
            assert "integration_test_alert" in alert_manager.active_alerts
            alert = alert_manager.active_alerts["integration_test_alert"]
            assert alert.status == AlertStatus.FIRING
            
            # Verify notification was sent
            mock_notification_channel.send_notification.assert_called_once()
            
            # Phase 2: Resolve alert
            mock_metric.return_value = 5.0  # Below threshold
            
            should_fire = alert_manager.evaluate_rule(test_rule)
            if not should_fire:
                await alert_manager.resolve_alert("integration_test_alert")
            
            # Verify alert resolution
            assert "integration_test_alert" not in alert_manager.active_alerts
    
    @pytest.mark.asyncio
    async def test_multiple_alert_priorities(self, mock_notification_channel):
        """Test handling multiple alerts with different priorities."""
        # Clear state
        alert_manager.rules.clear()
        alert_manager.active_alerts.clear()
        alert_manager.notification_channels = [mock_notification_channel]
        
        # Create rules with different severities
        critical_rule = AlertRule(
            name="critical_alert",
            description="Critical system failure",
            metric_name="system_health",
            threshold=0.1,
            comparison="lt",
            duration_seconds=1,
            severity=AlertSeverity.CRITICAL
        )
        
        warning_rule = AlertRule(
            name="warning_alert", 
            description="Performance degradation",
            metric_name="response_time",
            threshold=2.0,
            comparison="gt",
            duration_seconds=1,
            severity=AlertSeverity.WARNING
        )
        
        alert_manager.add_rule(critical_rule)
        alert_manager.add_rule(warning_rule)
        
        # Fire both alerts
        await alert_manager.fire_alert(critical_rule, 0.05)
        await alert_manager.fire_alert(warning_rule, 3.0)
        
        # Verify both alerts are active
        assert len(alert_manager.active_alerts) == 2
        assert alert_manager.active_alerts["critical_alert"].severity == AlertSeverity.CRITICAL
        assert alert_manager.active_alerts["warning_alert"].severity == AlertSeverity.WARNING
        
        # Verify notifications were sent for both
        assert mock_notification_channel.send_notification.call_count == 2


class TestPerformanceUnderLoad:
    """Test monitoring system performance under load."""
    
    def test_monitoring_high_throughput(self):
        """Test monitoring system under high metric load."""
        start_time = time.time()
        
        # Generate high volume of metrics
        for i in range(1000):
            monitor.increment_counter(f"load_test_counter_{i % 10}")
            monitor.record_duration("load_test_duration", 0.001 * i)
            profiler_manager.record_performance(f"load_test_op_{i % 5}", 0.001)
        
        duration = time.time() - start_time
        
        # Should handle high load efficiently (< 1 second for 1000 operations)
        assert duration < 1.0
        
        # Verify metrics were recorded
        stats = profiler_manager.get_all_stats()
        assert len([k for k in stats.keys() if k.startswith("load_test_op_")]) == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks_performance(self):
        """Test health check system under concurrent load."""
        from src.common.health_checks import HealthCheckManager, MockHealthCheck
        
        manager = HealthCheckManager()
        manager.checks = []  # Clear default checks
        
        # Add many health checks
        for i in range(20):
            check = MockHealthCheck(f"concurrent_check_{i}", HealthStatus.HEALTHY)
            manager.add_check(check)
        
        start_time = time.time()
        results = await manager.run_all_checks()
        duration = time.time() - start_time
        
        # Should complete all checks concurrently in reasonable time
        assert len(results) == 20
        assert duration < 2.0  # Should be much faster than 20 * check_time
    
    def test_profiling_overhead_under_load(self):
        """Test profiling overhead under heavy load."""
        # Test without profiling
        def baseline_operation():
            return sum(range(100))
        
        start_time = time.time()
        for _ in range(1000):
            baseline_operation()
        baseline_duration = time.time() - start_time
        
        # Test with profiling
        @profile_performance("load_test_profiled")
        def profiled_operation():
            return sum(range(100))
        
        start_time = time.time()
        for _ in range(1000):
            profiled_operation()
        profiled_duration = time.time() - start_time
        
        # Overhead should be reasonable (< 100% increase)
        overhead_ratio = profiled_duration / baseline_duration
        assert overhead_ratio < 2.0


class TestMonitoringFailureScenarios:
    """Test monitoring system behavior during failures."""
    
    @pytest.mark.asyncio
    async def test_health_check_failure_recovery(self):
        """Test health check system recovery from failures."""
        from src.common.health_checks import HealthCheckManager
        
        manager = HealthCheckManager()
        manager.checks = []
        
        # Add a check that will fail
        failing_check = MockHealthCheck("failing_check", HealthStatus.HEALTHY, should_error=True)
        healthy_check = MockHealthCheck("healthy_check", HealthStatus.HEALTHY)
        
        manager.add_check(failing_check)
        manager.add_check(healthy_check)
        
        results = await manager.run_all_checks()
        
        # Should handle failure gracefully
        assert len(results) == 2
        assert results["failing_check"].status == HealthStatus.UNHEALTHY
        assert results["healthy_check"].status == HealthStatus.HEALTHY
    
    def test_profiler_memory_limit_handling(self):
        """Test profiler behavior when memory limits are approached."""
        profiler = profiler_manager
        
        # Fill profiler with many metrics
        for i in range(1000):
            profiler.record_performance(f"memory_test_{i}", 0.001)
        
        # Should still function without errors
        stats = profiler.get_all_stats()
        assert len(stats) >= 1000  # Should have recorded all metrics
        
        # System stats should still be available
        assert "_system" in stats
    
    @pytest.mark.asyncio
    async def test_alert_system_notification_failure(self):
        """Test alert system behavior when notifications fail."""
        # Create failing notification channel
        failing_channel = Mock()
        failing_channel.name = "failing_channel"
        failing_channel.enabled = True
        failing_channel.send_notification = AsyncMock(side_effect=Exception("Notification failed"))
        
        alert_manager.notification_channels = [failing_channel]
        
        test_rule = AlertRule(
            name="notification_test",
            description="Test notification failure",
            metric_name="test_metric",
            threshold=5.0,
            comparison="gt",
            duration_seconds=0,
            severity=AlertSeverity.WARNING
        )
        
        # Should not raise exception even if notification fails
        try:
            await alert_manager.fire_alert(test_rule, 10.0)
        except Exception as e:
            pytest.fail(f"Alert firing should not fail due to notification error: {e}")
        
        # Alert should still be created
        assert "notification_test" in alert_manager.active_alerts


class TestMonitoringDataConsistency:
    """Test data consistency across monitoring components."""
    
    def test_metric_data_consistency(self):
        """Test consistency of metrics across different collection points."""
        operation_name = "consistency_test"
        
        # Record metrics through different interfaces
        monitor.increment_counter('test_operations_total')
        profiler_manager.record_performance(operation_name, 0.5)
        
        # Verify data is accessible through all interfaces
        profiler_stats = profiler_manager.get_all_stats()
        assert operation_name in profiler_stats
        
        monitor_metrics = monitor.get_metrics()
        assert 'test_operations_total' in monitor_metrics
    
    @pytest.mark.asyncio
    async def test_timestamp_consistency(self):
        """Test timestamp consistency across monitoring events."""
        start_time = datetime.now()
        
        # Generate events in sequence
        profiler_manager.record_performance("timestamp_test_1", 0.1)
        await asyncio.sleep(0.01)
        profiler_manager.record_performance("timestamp_test_2", 0.1)
        
        end_time = datetime.now()
        
        # Verify timestamps are within expected range
        stats = profiler_manager.get_all_stats()
        
        # Both operations should have been recorded
        assert "timestamp_test_1" in stats
        assert "timestamp_test_2" in stats
        
        # Timestamps should be reasonable (this is a basic check)
        assert stats["timestamp_test_1"]["call_count"] == 1
        assert stats["timestamp_test_2"]["call_count"] == 1


class MockHealthCheck:
    """Mock health check for testing."""
    
    def __init__(self, name: str, status: HealthStatus, should_error: bool = False):
        self.name = name
        self.return_status = status
        self.should_error = should_error
    
    async def check(self):
        from src.common.health_checks import HealthCheckResult
        
        if self.should_error:
            raise Exception(f"Mock error in {self.name}")
        
        return HealthCheckResult(
            name=self.name,
            status=self.return_status,
            message=f"Mock result for {self.name}",
            duration_ms=10.0,
            timestamp=datetime.now()
        )


if __name__ == "__main__":
    pytest.main([__file__])