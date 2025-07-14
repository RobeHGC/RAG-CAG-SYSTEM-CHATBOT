"""
Comprehensive tests for the performance profiling system.
Tests profiling decorators, metrics collection, and performance analysis.
"""

import asyncio
import pytest
import time
import tracemalloc
from unittest.mock import Mock, patch, MagicMock
from collections import deque

from src.common.profiling import (
    ProfilerManager, PerformanceMetrics, CProfileWrapper, MemoryProfiler,
    profile_performance, profile_async_performance, profile_code_block,
    BottleneckAnalyzer, profiler_manager
)


class TestPerformanceMetrics:
    """Test cases for PerformanceMetrics class."""
    
    def test_performance_metrics_initialization(self):
        """Test performance metrics initialization."""
        metrics = PerformanceMetrics("test_function")
        
        assert metrics.name == "test_function"
        assert metrics.call_count == 0
        assert metrics.total_time == 0.0
        assert metrics.min_time == float('inf')
        assert metrics.max_time == 0.0
        assert metrics.avg_time == 0.0
        assert metrics.memory_usage == 0
        assert metrics.cpu_percent == 0.0
        assert isinstance(metrics.samples, deque)
        assert metrics.samples.maxlen == 1000
    
    def test_add_sample(self):
        """Test adding performance samples."""
        metrics = PerformanceMetrics("test_function")
        
        # Add first sample
        metrics.add_sample(0.5, memory_delta=1024, cpu_percent=10.0)
        
        assert metrics.call_count == 1
        assert metrics.total_time == 0.5
        assert metrics.min_time == 0.5
        assert metrics.max_time == 0.5
        assert metrics.avg_time == 0.5
        assert metrics.memory_usage == 1024
        assert metrics.cpu_percent == 10.0
        assert len(metrics.samples) == 1
        
        # Add second sample
        metrics.add_sample(1.0, memory_delta=512, cpu_percent=15.0)
        
        assert metrics.call_count == 2
        assert metrics.total_time == 1.5
        assert metrics.min_time == 0.5
        assert metrics.max_time == 1.0
        assert metrics.avg_time == 0.75
        assert metrics.memory_usage == 1024  # Max memory
        assert metrics.cpu_percent == 15.0  # Latest CPU
        assert len(metrics.samples) == 2
    
    def test_get_stats(self):
        """Test getting performance statistics."""
        metrics = PerformanceMetrics("test_function")
        
        # Add some samples
        metrics.add_sample(0.1)
        metrics.add_sample(0.5)
        metrics.add_sample(1.0)
        
        stats = metrics.get_stats()
        
        assert stats["name"] == "test_function"
        assert stats["call_count"] == 3
        assert stats["avg_time"] == 0.5333333333333333
        assert stats["min_time"] == 0.1
        assert stats["max_time"] == 1.0
        assert "percentiles" in stats
        assert "calls_per_second" in stats
    
    def test_percentile_calculation(self):
        """Test percentile calculation."""
        metrics = PerformanceMetrics("test_function")
        
        # Add samples for percentile calculation
        for i in range(100):
            metrics.add_sample(i / 100.0)  # 0.00 to 0.99
        
        stats = metrics.get_stats()
        percentiles = stats["percentiles"]
        
        assert "p50" in percentiles
        assert "p75" in percentiles
        assert "p90" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        
        # Basic sanity checks
        assert percentiles["p50"] < percentiles["p75"]
        assert percentiles["p75"] < percentiles["p90"]
        assert percentiles["p90"] < percentiles["p95"]
    
    def test_throughput_calculation(self):
        """Test throughput calculation."""
        metrics = PerformanceMetrics("test_function")
        
        # Mock time.time to control timestamps
        with patch('time.time') as mock_time:
            mock_time.side_effect = [1000.0, 1001.0, 1002.0, 1003.0]  # 1 second intervals
            
            metrics.add_sample(0.1)
            metrics.add_sample(0.1)
            metrics.add_sample(0.1)
            
            stats = metrics.get_stats()
            
            # Should calculate throughput based on time span
            assert stats["calls_per_second"] >= 0


class TestProfilerManager:
    """Test cases for ProfilerManager class."""
    
    @pytest.fixture
    def profiler(self):
        """Create a fresh profiler manager for each test."""
        return ProfilerManager()
    
    def test_profiler_initialization(self, profiler):
        """Test profiler manager initialization."""
        assert isinstance(profiler.metrics, dict)
        assert isinstance(profiler.active_profilers, dict)
        assert profiler.sampling_interval == 0.01
        assert profiler.profiling_enabled is True
        assert profiler.memory_tracking_enabled is False
        assert isinstance(profiler.cpu_samples, deque)
        assert isinstance(profiler.memory_samples, deque)
    
    def test_get_metrics(self, profiler):
        """Test getting or creating metrics."""
        metrics1 = profiler.get_metrics("test_function")
        metrics2 = profiler.get_metrics("test_function")
        
        assert metrics1 is metrics2  # Should return same instance
        assert metrics1.name == "test_function"
        assert "test_function" in profiler.metrics
    
    def test_record_performance(self, profiler):
        """Test recording performance metrics."""
        profiler.record_performance("test_op", 0.5, memory_delta=1024, cpu_percent=10.0)
        
        assert "test_op" in profiler.metrics
        metrics = profiler.metrics["test_op"]
        assert metrics.call_count == 1
        assert metrics.avg_time == 0.5
        assert metrics.memory_usage == 1024
    
    def test_get_all_stats(self, profiler):
        """Test getting all performance statistics."""
        profiler.record_performance("op1", 0.1)
        profiler.record_performance("op2", 0.2)
        profiler.record_performance("op1", 0.3)
        
        all_stats = profiler.get_all_stats()
        
        assert "op1" in all_stats
        assert "op2" in all_stats
        assert "_system" in all_stats
        
        assert all_stats["op1"]["call_count"] == 2
        assert all_stats["op2"]["call_count"] == 1
    
    def test_reset_metrics(self, profiler):
        """Test resetting metrics."""
        profiler.record_performance("test_op", 0.1)
        assert "test_op" in profiler.metrics
        
        # Reset specific metric
        profiler.reset_metrics("test_op")
        assert "test_op" not in profiler.metrics
        
        # Reset all metrics
        profiler.record_performance("op1", 0.1)
        profiler.record_performance("op2", 0.2)
        profiler.reset_metrics()
        assert len(profiler.metrics) == 0
    
    def test_memory_tracking_toggle(self, profiler):
        """Test memory tracking enable/disable."""
        assert profiler.memory_tracking_enabled is False
        
        profiler.enable_memory_tracking()
        assert profiler.memory_tracking_enabled is True
        
        profiler.disable_memory_tracking()
        assert profiler.memory_tracking_enabled is False
    
    def test_profiling_disabled(self, profiler):
        """Test behavior when profiling is disabled."""
        profiler.profiling_enabled = False
        profiler.record_performance("test_op", 0.1)
        
        # Should not record when disabled
        assert len(profiler.metrics) == 0


class TestProfilingDecorators:
    """Test cases for profiling decorators."""
    
    def test_profile_performance_decorator(self):
        """Test the profile_performance decorator."""
        @profile_performance("test_function")
        def test_function(x, y):
            time.sleep(0.01)  # Small delay for measurement
            return x + y
        
        result = test_function(2, 3)
        assert result == 5
        
        # Check if metrics were recorded
        # Note: This requires access to the global profiler_manager
        stats = profiler_manager.get_all_stats()
        assert "test_function" in stats
        assert stats["test_function"]["call_count"] >= 1
    
    def test_profile_performance_with_custom_name(self):
        """Test profile_performance decorator with custom name."""
        @profile_performance("custom_name")
        def another_function():
            return "result"
        
        result = another_function()
        assert result == "result"
        
        stats = profiler_manager.get_all_stats()
        assert "custom_name" in stats
    
    @pytest.mark.asyncio
    async def test_profile_async_performance_decorator(self):
        """Test the profile_async_performance decorator."""
        @profile_async_performance("async_function")
        async def async_test_function(delay):
            await asyncio.sleep(delay)
            return "async_result"
        
        result = await async_test_function(0.01)
        assert result == "async_result"
        
        stats = profiler_manager.get_all_stats()
        assert "async_function" in stats
    
    def test_profile_performance_with_exception(self):
        """Test profiling decorator when function raises exception."""
        @profile_performance("error_function")
        def error_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            error_function()
        
        # Should still record metrics for failed operations
        stats = profiler_manager.get_all_stats()
        assert "error_function" in stats
    
    def test_profile_code_block(self):
        """Test profile_code_block context manager."""
        with profile_code_block("code_block_test"):
            time.sleep(0.01)
            x = 1 + 1
        
        stats = profiler_manager.get_all_stats()
        assert "code_block_test" in stats
        assert stats["code_block_test"]["call_count"] == 1
    
    def test_profile_code_block_with_exception(self):
        """Test profile_code_block when exception occurs."""
        try:
            with profile_code_block("error_block"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should still record metrics
        stats = profiler_manager.get_all_stats()
        assert "error_block" in stats


class TestCProfileWrapper:
    """Test cases for CProfileWrapper class."""
    
    @pytest.fixture
    def cprofile_wrapper(self, tmp_path):
        """Create a CProfileWrapper with temporary output directory."""
        return CProfileWrapper(output_dir=str(tmp_path))
    
    def test_cprofile_wrapper_initialization(self, cprofile_wrapper, tmp_path):
        """Test CProfileWrapper initialization."""
        assert cprofile_wrapper.output_dir == str(tmp_path)
        assert isinstance(cprofile_wrapper.active_profilers, dict)
        assert tmp_path.exists()
    
    def test_start_stop_profiling(self, cprofile_wrapper):
        """Test starting and stopping profiling sessions."""
        # Start profiling
        session_name = cprofile_wrapper.start_profiling("test_session")
        assert session_name == "test_session"
        assert "test_session" in cprofile_wrapper.active_profilers
        
        # Do some work
        def test_work():
            for i in range(1000):
                x = i * i
        
        test_work()
        
        # Stop profiling
        report_path = cprofile_wrapper.stop_profiling("test_session")
        assert "test_session" not in cprofile_wrapper.active_profilers
        assert report_path.endswith("_report.txt")
    
    def test_profile_context_manager(self, cprofile_wrapper):
        """Test profiling context manager."""
        with cprofile_wrapper.profile_context("context_test") as session:
            assert session == "context_test"
            # Do some work
            sum([i for i in range(100)])
        
        # Session should be cleaned up
        assert "context_test" not in cprofile_wrapper.active_profilers
    
    def test_start_profiling_duplicate_name(self, cprofile_wrapper):
        """Test starting profiling with duplicate name."""
        cprofile_wrapper.start_profiling("duplicate")
        
        with pytest.raises(ValueError, match="already active"):
            cprofile_wrapper.start_profiling("duplicate")
    
    def test_stop_profiling_nonexistent(self, cprofile_wrapper):
        """Test stopping profiling for non-existent session."""
        with pytest.raises(ValueError, match="not active"):
            cprofile_wrapper.stop_profiling("nonexistent")


class TestMemoryProfiler:
    """Test cases for MemoryProfiler class."""
    
    @pytest.fixture
    def memory_profiler(self):
        """Create a MemoryProfiler for testing."""
        return MemoryProfiler()
    
    def test_memory_profiler_initialization(self, memory_profiler):
        """Test memory profiler initialization."""
        assert isinstance(memory_profiler.snapshots, dict)
        assert memory_profiler.baseline_snapshot is None
    
    def test_start_memory_profiling(self, memory_profiler):
        """Test starting memory profiling."""
        memory_profiler.start_memory_profiling()
        
        assert tracemalloc.is_tracing()
        assert memory_profiler.baseline_snapshot is not None
        
        # Cleanup
        tracemalloc.stop()
    
    def test_take_snapshot(self, memory_profiler):
        """Test taking memory snapshots."""
        memory_profiler.start_memory_profiling()
        
        # Allocate some memory
        data = [i for i in range(1000)]
        
        snapshot_info = memory_profiler.take_snapshot("test_snapshot")
        
        assert "test_snapshot" in memory_profiler.snapshots
        assert snapshot_info["name"] == "test_snapshot"
        assert "timestamp" in snapshot_info
        
        # Cleanup
        tracemalloc.stop()
    
    def test_analyze_memory_leaks(self, memory_profiler):
        """Test memory leak analysis."""
        memory_profiler.start_memory_profiling()
        
        # Take baseline
        memory_profiler.take_snapshot("baseline")
        
        # Allocate significant memory
        large_data = [i for i in range(100000)]
        
        # Take second snapshot
        memory_profiler.take_snapshot("after_allocation")
        
        leaks = memory_profiler.analyze_memory_leaks()
        
        # Should detect potential leaks
        assert isinstance(leaks, list)
        
        # Cleanup
        tracemalloc.stop()


class TestBottleneckAnalyzer:
    """Test cases for BottleneckAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a BottleneckAnalyzer with mock profiler."""
        mock_profiler = Mock()
        return BottleneckAnalyzer(mock_profiler)
    
    def test_analyze_bottlenecks_slow_operations(self, analyzer):
        """Test bottleneck analysis for slow operations."""
        # Mock stats with slow operation
        mock_stats = {
            "slow_operation": {
                "name": "slow_operation",
                "avg_time": 10.0,  # 10 seconds - very slow
                "call_count": 100,
                "memory_usage_mb": 50.0
            },
            "fast_operation": {
                "name": "fast_operation", 
                "avg_time": 0.1,  # 100ms - fast
                "call_count": 1000,
                "memory_usage_mb": 1.0
            }
        }
        
        analyzer.profiler_manager.get_all_stats.return_value = mock_stats
        
        analysis = analyzer.analyze_bottlenecks()
        
        assert len(analysis["bottlenecks"]) >= 1
        assert any(b["name"] == "slow_operation" for b in analysis["bottlenecks"])
        assert len(analysis["recommendations"]) >= 1
    
    def test_analyze_bottlenecks_memory_intensive(self, analyzer):
        """Test bottleneck analysis for memory-intensive operations."""
        mock_stats = {
            "memory_hog": {
                "name": "memory_hog",
                "avg_time": 1.0,
                "call_count": 10,
                "memory_usage_mb": 200.0  # 200MB - high memory
            }
        }
        
        analyzer.profiler_manager.get_all_stats.return_value = mock_stats
        
        analysis = analyzer.analyze_bottlenecks()
        
        memory_bottlenecks = [b for b in analysis["bottlenecks"] if b["type"] == "memory_intensive"]
        assert len(memory_bottlenecks) >= 1
    
    def test_analyze_bottlenecks_frequent_slow_calls(self, analyzer):
        """Test bottleneck analysis for frequent slow calls."""
        mock_stats = {
            "frequent_slow": {
                "name": "frequent_slow",
                "avg_time": 0.5,  # 500ms
                "call_count": 5000,  # Very frequent
                "memory_usage_mb": 5.0
            }
        }
        
        analyzer.profiler_manager.get_all_stats.return_value = mock_stats
        
        analysis = analyzer.analyze_bottlenecks()
        
        frequent_bottlenecks = [b for b in analysis["bottlenecks"] if b["type"] == "frequent_slow_calls"]
        assert len(frequent_bottlenecks) >= 1
    
    def test_generate_performance_report(self, analyzer):
        """Test performance report generation."""
        mock_stats = {
            "test_operation": {
                "name": "test_operation",
                "avg_time": 2.0,
                "call_count": 100,
                "memory_usage_mb": 10.0
            },
            "_system": {
                "avg_cpu_percent": 25.0,
                "avg_memory_percent": 60.0,
                "sample_count": 1000
            }
        }
        
        analyzer.profiler_manager.get_all_stats.return_value = mock_stats
        
        report = analyzer.generate_performance_report()
        
        assert "AI Companion Performance Analysis Report" in report
        assert "test_operation" in report
        assert "SYSTEM STATISTICS" in report
        assert "25.0%" in report  # CPU usage
        assert "60.0%" in report  # Memory usage


class TestProfilingIntegration:
    """Integration tests for profiling system."""
    
    def test_profiling_with_memory_tracking(self):
        """Test profiling with memory tracking enabled."""
        profiler = ProfilerManager()
        profiler.enable_memory_tracking()
        
        @profile_performance("memory_test", memory_tracking=True)
        def memory_intensive_function():
            # Allocate some memory
            data = [i for i in range(10000)]
            return len(data)
        
        result = memory_intensive_function()
        assert result == 10000
        
        stats = profiler.get_all_stats()
        assert "memory_test" in stats
        
        profiler.disable_memory_tracking()
    
    def test_profiling_disabled_performance(self):
        """Test performance when profiling is disabled."""
        profiler = ProfilerManager()
        profiler.profiling_enabled = False
        
        @profile_performance("disabled_test")
        def test_function():
            return "result"
        
        start_time = time.time()
        result = test_function()
        duration = time.time() - start_time
        
        assert result == "result"
        # Should have minimal overhead when disabled
        assert duration < 0.01
    
    def test_concurrent_profiling(self):
        """Test profiling with concurrent operations."""
        profiler = ProfilerManager()
        
        @profile_performance("concurrent_test")
        def worker_function(worker_id):
            time.sleep(0.01)
            return f"worker_{worker_id}"
        
        # Simulate concurrent calls
        import threading
        
        results = []
        threads = []
        
        def thread_worker(worker_id):
            result = worker_function(worker_id)
            results.append(result)
        
        for i in range(5):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 5
        
        stats = profiler.get_all_stats()
        assert "concurrent_test" in stats
        assert stats["concurrent_test"]["call_count"] == 5


class TestProfilingPerformance:
    """Performance tests for profiling system itself."""
    
    def test_profiler_overhead(self):
        """Test profiling system overhead."""
        profiler = ProfilerManager()
        
        # Measure baseline performance
        def baseline_function():
            return sum(range(1000))
        
        start_time = time.time()
        for _ in range(100):
            baseline_function()
        baseline_duration = time.time() - start_time
        
        # Measure with profiling
        @profile_performance("overhead_test")
        def profiled_function():
            return sum(range(1000))
        
        start_time = time.time()
        for _ in range(100):
            profiled_function()
        profiled_duration = time.time() - start_time
        
        # Overhead should be minimal (less than 50% increase)
        overhead_ratio = profiled_duration / baseline_duration
        assert overhead_ratio < 1.5  # Less than 50% overhead
    
    def test_memory_profiling_overhead(self):
        """Test memory profiling overhead."""
        profiler = ProfilerManager()
        profiler.enable_memory_tracking()
        
        @profile_performance("memory_overhead_test", memory_tracking=True)
        def memory_function():
            data = list(range(1000))
            return sum(data)
        
        start_time = time.time()
        for _ in range(50):  # Fewer iterations for memory tracking
            memory_function()
        duration = time.time() - start_time
        
        # Should complete reasonably quickly even with memory tracking
        assert duration < 1.0
        
        profiler.disable_memory_tracking()


if __name__ == "__main__":
    pytest.main([__file__])