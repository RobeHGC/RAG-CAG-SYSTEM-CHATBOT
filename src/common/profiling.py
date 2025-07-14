"""
Performance profiling system for AI Companion application.
Provides comprehensive profiling tools for CPU, memory, and operation analysis.
"""

import asyncio
import cProfile
import functools
import gc
import linecache
import os
import pstats
import sys
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import psutil

from .monitoring import monitor
from .enhanced_logging import enhanced_logger

import logging
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a function or operation."""
    
    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    memory_usage: int = 0  # Peak memory usage in bytes
    cpu_percent: float = 0.0
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_sample(self, duration: float, memory_delta: int = 0, cpu_percent: float = 0.0):
        """Add a performance sample."""
        self.call_count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.avg_time = self.total_time / self.call_count
        
        if memory_delta > self.memory_usage:
            self.memory_usage = memory_delta
        
        self.cpu_percent = cpu_percent
        
        self.samples.append({
            'timestamp': time.time(),
            'duration': duration,
            'memory_delta': memory_delta,
            'cpu_percent': cpu_percent
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        percentiles = self._calculate_percentiles()
        
        return {
            'name': self.name,
            'call_count': self.call_count,
            'total_time': self.total_time,
            'avg_time': self.avg_time,
            'min_time': self.min_time if self.min_time != float('inf') else 0.0,
            'max_time': self.max_time,
            'memory_usage_mb': self.memory_usage / (1024 * 1024),
            'cpu_percent': self.cpu_percent,
            'percentiles': percentiles,
            'calls_per_second': self._calculate_throughput()
        }
    
    def _calculate_percentiles(self) -> Dict[str, float]:
        """Calculate duration percentiles."""
        if not self.samples:
            return {}
        
        durations = sorted([s['duration'] for s in self.samples])
        length = len(durations)
        
        if length == 0:
            return {}
        
        return {
            'p50': durations[int(length * 0.5)],
            'p75': durations[int(length * 0.75)],
            'p90': durations[int(length * 0.9)],
            'p95': durations[int(length * 0.95)],
            'p99': durations[int(length * 0.99)]
        }
    
    def _calculate_throughput(self) -> float:
        """Calculate calls per second over recent samples."""
        if len(self.samples) < 2:
            return 0.0
        
        recent_samples = list(self.samples)[-100:]  # Last 100 samples
        if len(recent_samples) < 2:
            return 0.0
        
        time_span = recent_samples[-1]['timestamp'] - recent_samples[0]['timestamp']
        if time_span <= 0:
            return 0.0
        
        return len(recent_samples) / time_span


class ProfilerManager:
    """Central profiler management system."""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.active_profilers: Dict[str, Any] = {}
        self.sampling_interval = 0.01  # 10ms sampling
        self.profiling_enabled = True
        self.memory_tracking_enabled = False
        self._lock = threading.Lock()
        
        # CPU monitoring
        self.cpu_samples = deque(maxlen=1000)
        self.memory_samples = deque(maxlen=1000)
        
        # Start background monitoring
        self._start_system_monitoring()
    
    def _start_system_monitoring(self):
        """Start background system monitoring."""
        def monitor_system():
            while True:
                if self.profiling_enabled:
                    try:
                        # Sample CPU and memory
                        cpu_percent = psutil.cpu_percent()
                        memory_info = psutil.virtual_memory()
                        
                        timestamp = time.time()
                        self.cpu_samples.append({
                            'timestamp': timestamp,
                            'cpu_percent': cpu_percent
                        })
                        
                        self.memory_samples.append({
                            'timestamp': timestamp,
                            'memory_percent': memory_info.percent,
                            'memory_available': memory_info.available,
                            'memory_used': memory_info.used
                        })
                        
                    except Exception as e:
                        logger.warning(f"System monitoring error: {e}")
                
                time.sleep(self.sampling_interval * 100)  # Sample every second
        
        thread = threading.Thread(target=monitor_system, daemon=True)
        thread.start()
    
    def get_metrics(self, name: str) -> PerformanceMetrics:
        """Get or create metrics for a function."""
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = PerformanceMetrics(name)
            return self.metrics[name]
    
    def record_performance(self, name: str, duration: float, 
                         memory_delta: int = 0, cpu_percent: float = 0.0):
        """Record performance metrics."""
        if not self.profiling_enabled:
            return
        
        metrics = self.get_metrics(name)
        metrics.add_sample(duration, memory_delta, cpu_percent)
        
        # Send to monitoring system
        monitor.record_custom_metric(f"profiler_{name}_duration", duration)
        monitor.record_custom_metric(f"profiler_{name}_calls", metrics.call_count)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all tracked functions."""
        with self._lock:
            stats = {}
            for name, metrics in self.metrics.items():
                stats[name] = metrics.get_stats()
            
            # Add system stats
            stats['_system'] = self._get_system_stats()
            
            return stats
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics."""
        if not self.cpu_samples or not self.memory_samples:
            return {}
        
        recent_cpu = list(self.cpu_samples)[-100:]
        recent_memory = list(self.memory_samples)[-100:]
        
        avg_cpu = sum(s['cpu_percent'] for s in recent_cpu) / len(recent_cpu)
        avg_memory = sum(s['memory_percent'] for s in recent_memory) / len(recent_memory)
        
        return {
            'avg_cpu_percent': avg_cpu,
            'avg_memory_percent': avg_memory,
            'sample_count': len(self.cpu_samples),
            'monitoring_enabled': self.profiling_enabled
        }
    
    def reset_metrics(self, name: str = None):
        """Reset metrics for a specific function or all functions."""
        with self._lock:
            if name:
                if name in self.metrics:
                    del self.metrics[name]
            else:
                self.metrics.clear()
    
    def enable_memory_tracking(self):
        """Enable memory tracking using tracemalloc."""
        if not self.memory_tracking_enabled:
            tracemalloc.start()
            self.memory_tracking_enabled = True
            logger.info("Memory tracking enabled")
    
    def disable_memory_tracking(self):
        """Disable memory tracking."""
        if self.memory_tracking_enabled:
            tracemalloc.stop()
            self.memory_tracking_enabled = False
            logger.info("Memory tracking disabled")


class CProfileWrapper:
    """Wrapper for cProfile with enhanced reporting."""
    
    def __init__(self, output_dir: str = "profiling_results"):
        self.output_dir = output_dir
        self.active_profilers: Dict[str, cProfile.Profile] = {}
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def start_profiling(self, name: str) -> str:
        """Start cProfile profiling session."""
        if name in self.active_profilers:
            raise ValueError(f"Profiler '{name}' is already active")
        
        profiler = cProfile.Profile()
        profiler.enable()
        self.active_profilers[name] = profiler
        
        logger.info(f"Started cProfile session: {name}")
        return name
    
    def stop_profiling(self, name: str) -> str:
        """Stop profiling and save results."""
        if name not in self.active_profilers:
            raise ValueError(f"Profiler '{name}' is not active")
        
        profiler = self.active_profilers.pop(name)
        profiler.disable()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.prof"
        filepath = os.path.join(self.output_dir, filename)
        
        # Save profile data
        profiler.dump_stats(filepath)
        
        # Generate text report
        report_path = self._generate_text_report(filepath, name)
        
        logger.info(f"Profiling results saved: {filepath}")
        return report_path
    
    def _generate_text_report(self, profile_path: str, name: str) -> str:
        """Generate human-readable text report."""
        stats = pstats.Stats(profile_path)
        
        # Create text report
        text_output = StringIO()
        stats.sort_stats('cumulative')
        stats.print_stats(30, file=text_output)  # Top 30 functions
        
        # Save to file
        report_filename = profile_path.replace('.prof', '_report.txt')
        with open(report_filename, 'w') as f:
            f.write(f"Profile Report for: {name}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            f.write(text_output.getvalue())
        
        return report_filename
    
    @contextmanager
    def profile_context(self, name: str):
        """Context manager for profiling code blocks."""
        session_name = self.start_profiling(name)
        try:
            yield session_name
        finally:
            self.stop_profiling(session_name)


class MemoryProfiler:
    """Memory profiling using tracemalloc and custom tracking."""
    
    def __init__(self):
        self.snapshots: Dict[str, Any] = {}
        self.baseline_snapshot = None
        
    def start_memory_profiling(self):
        """Start memory profiling."""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        
        self.baseline_snapshot = tracemalloc.take_snapshot()
        logger.info("Memory profiling started")
    
    def take_snapshot(self, name: str) -> Dict[str, Any]:
        """Take a memory snapshot."""
        if not tracemalloc.is_tracing():
            raise RuntimeError("Memory profiling not started")
        
        snapshot = tracemalloc.take_snapshot()
        self.snapshots[name] = snapshot
        
        # Calculate memory usage
        if self.baseline_snapshot:
            stats = snapshot.compare_to(self.baseline_snapshot, 'lineno')
            total_size = sum(stat.size for stat in stats)
            
            return {
                'name': name,
                'timestamp': datetime.now().isoformat(),
                'total_size_mb': total_size / (1024 * 1024),
                'top_files': [
                    {
                        'filename': stat.traceback.format()[0] if stat.traceback else 'unknown',
                        'size_mb': stat.size / (1024 * 1024),
                        'count': stat.count
                    }
                    for stat in stats[:10]  # Top 10 allocations
                ]
            }
        
        return {'name': name, 'timestamp': datetime.now().isoformat()}
    
    def analyze_memory_leaks(self) -> List[Dict[str, Any]]:
        """Analyze potential memory leaks."""
        if len(self.snapshots) < 2:
            return []
        
        # Compare latest snapshot with baseline
        snapshot_names = list(self.snapshots.keys())
        latest_snapshot = self.snapshots[snapshot_names[-1]]
        
        if self.baseline_snapshot:
            stats = latest_snapshot.compare_to(self.baseline_snapshot, 'traceback')
            
            # Look for significant growth
            potential_leaks = []
            for stat in stats:
                if stat.size > 1024 * 1024:  # > 1MB growth
                    potential_leaks.append({
                        'size_mb': stat.size / (1024 * 1024),
                        'count': stat.count,
                        'traceback': stat.traceback.format() if stat.traceback else []
                    })
            
            return sorted(potential_leaks, key=lambda x: x['size_mb'], reverse=True)
        
        return []


def profile_performance(name: str = None, memory_tracking: bool = False, 
                       cpu_profiling: bool = False):
    """
    Decorator for performance profiling.
    
    Args:
        name: Custom name for the profiled function
        memory_tracking: Enable memory usage tracking
        cpu_profiling: Enable CPU profiling
    """
    def decorator(func: Callable) -> Callable:
        profile_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not profiler_manager.profiling_enabled:
                return func(*args, **kwargs)
            
            # Setup profiling
            start_time = time.time()
            start_memory = 0
            start_cpu = psutil.cpu_percent()
            
            if memory_tracking and profiler_manager.memory_tracking_enabled:
                current_memory = tracemalloc.get_traced_memory()[0]
                start_memory = current_memory
            
            cpu_profiler = None
            if cpu_profiling:
                cpu_profiler = cProfile.Profile()
                cpu_profiler.enable()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate metrics
                duration = time.time() - start_time
                memory_delta = 0
                
                if memory_tracking and profiler_manager.memory_tracking_enabled:
                    end_memory = tracemalloc.get_traced_memory()[0]
                    memory_delta = end_memory - start_memory
                
                end_cpu = psutil.cpu_percent()
                cpu_delta = end_cpu - start_cpu
                
                # Record performance
                profiler_manager.record_performance(
                    profile_name, duration, memory_delta, cpu_delta
                )
                
                # Log performance if significant
                if duration > 1.0:  # > 1 second
                    enhanced_logger.get_logger().warning(
                        f"Slow operation detected: {profile_name} took {duration:.2f}s",
                        extra={
                            'operation': profile_name,
                            'duration': duration,
                            'memory_delta_mb': memory_delta / (1024 * 1024) if memory_delta else 0
                        }
                    )
                
                return result
                
            except Exception as e:
                # Record failed operation
                duration = time.time() - start_time
                profiler_manager.record_performance(profile_name, duration, 0, 0)
                
                enhanced_logger.get_logger().error(
                    f"Operation failed: {profile_name} after {duration:.2f}s",
                    extra={'operation': profile_name, 'duration': duration, 'error': str(e)}
                )
                raise
            
            finally:
                if cpu_profiler:
                    cpu_profiler.disable()
                    # Save CPU profile if needed
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"cpu_profile_{profile_name}_{timestamp}.prof"
                    cpu_profiler.dump_stats(f"profiling_results/{filename}")
        
        return wrapper
    return decorator


async def profile_async_performance(name: str = None, memory_tracking: bool = False):
    """
    Decorator for async function performance profiling.
    """
    def decorator(func: Callable) -> Callable:
        profile_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not profiler_manager.profiling_enabled:
                return await func(*args, **kwargs)
            
            start_time = time.time()
            start_memory = 0
            start_cpu = psutil.cpu_percent()
            
            if memory_tracking and profiler_manager.memory_tracking_enabled:
                start_memory = tracemalloc.get_traced_memory()[0]
            
            try:
                result = await func(*args, **kwargs)
                
                duration = time.time() - start_time
                memory_delta = 0
                
                if memory_tracking and profiler_manager.memory_tracking_enabled:
                    end_memory = tracemalloc.get_traced_memory()[0]
                    memory_delta = end_memory - start_memory
                
                cpu_delta = psutil.cpu_percent() - start_cpu
                
                profiler_manager.record_performance(
                    profile_name, duration, memory_delta, cpu_delta
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                profiler_manager.record_performance(profile_name, duration, 0, 0)
                
                enhanced_logger.get_logger().error(
                    f"Async operation failed: {profile_name} after {duration:.2f}s",
                    extra={'operation': profile_name, 'duration': duration, 'error': str(e)}
                )
                raise
        
        return wrapper
    return decorator


@contextmanager
def profile_code_block(name: str, memory_tracking: bool = False):
    """Context manager for profiling code blocks."""
    start_time = time.time()
    start_memory = 0
    start_cpu = psutil.cpu_percent()
    
    if memory_tracking and profiler_manager.memory_tracking_enabled:
        start_memory = tracemalloc.get_traced_memory()[0]
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        memory_delta = 0
        
        if memory_tracking and profiler_manager.memory_tracking_enabled:
            end_memory = tracemalloc.get_traced_memory()[0]
            memory_delta = end_memory - start_memory
        
        cpu_delta = psutil.cpu_percent() - start_cpu
        
        profiler_manager.record_performance(name, duration, memory_delta, cpu_delta)


class BottleneckAnalyzer:
    """Analyze performance bottlenecks and provide recommendations."""
    
    def __init__(self, profiler_manager: ProfilerManager):
        self.profiler_manager = profiler_manager
    
    def analyze_bottlenecks(self) -> Dict[str, Any]:
        """Analyze current performance data for bottlenecks."""
        stats = self.profiler_manager.get_all_stats()
        
        bottlenecks = []
        recommendations = []
        
        for name, metrics in stats.items():
            if name == '_system':
                continue
            
            # Check for slow operations
            if metrics['avg_time'] > 5.0:  # > 5 seconds average
                bottlenecks.append({
                    'type': 'slow_operation',
                    'name': name,
                    'avg_time': metrics['avg_time'],
                    'call_count': metrics['call_count'],
                    'severity': 'high'
                })
                
                recommendations.append({
                    'operation': name,
                    'issue': 'High average execution time',
                    'suggestion': 'Consider optimization, caching, or async processing'
                })
            
            # Check for high memory usage
            if metrics['memory_usage_mb'] > 100:  # > 100MB
                bottlenecks.append({
                    'type': 'memory_intensive',
                    'name': name,
                    'memory_usage_mb': metrics['memory_usage_mb'],
                    'severity': 'medium'
                })
                
                recommendations.append({
                    'operation': name,
                    'issue': 'High memory usage',
                    'suggestion': 'Review memory allocation and consider memory pooling'
                })
            
            # Check for high call frequency with slow performance
            if metrics['call_count'] > 1000 and metrics['avg_time'] > 0.1:
                bottlenecks.append({
                    'type': 'frequent_slow_calls',
                    'name': name,
                    'call_count': metrics['call_count'],
                    'avg_time': metrics['avg_time'],
                    'severity': 'high'
                })
                
                recommendations.append({
                    'operation': name,
                    'issue': 'Frequent slow calls',
                    'suggestion': 'Implement caching or batch processing'
                })
        
        return {
            'bottlenecks': sorted(bottlenecks, key=lambda x: x.get('avg_time', 0), reverse=True),
            'recommendations': recommendations,
            'total_operations': len([k for k in stats.keys() if k != '_system']),
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def generate_performance_report(self) -> str:
        """Generate a comprehensive performance report."""
        stats = self.profiler_manager.get_all_stats()
        analysis = self.analyze_bottlenecks()
        
        report_lines = [
            "AI Companion Performance Analysis Report",
            "=" * 50,
            f"Generated: {datetime.now().isoformat()}",
            f"Total Operations Tracked: {analysis['total_operations']}",
            "",
            "TOP PERFORMANCE BOTTLENECKS:",
            "-" * 30
        ]
        
        for bottleneck in analysis['bottlenecks'][:10]:  # Top 10
            report_lines.append(
                f"• {bottleneck['name']} ({bottleneck['type']})"
            )
            if 'avg_time' in bottleneck:
                report_lines.append(f"  Average Time: {bottleneck['avg_time']:.2f}s")
            if 'memory_usage_mb' in bottleneck:
                report_lines.append(f"  Memory Usage: {bottleneck['memory_usage_mb']:.2f}MB")
            if 'call_count' in bottleneck:
                report_lines.append(f"  Call Count: {bottleneck['call_count']}")
            report_lines.append("")
        
        report_lines.extend([
            "RECOMMENDATIONS:",
            "-" * 15
        ])
        
        for rec in analysis['recommendations'][:10]:
            report_lines.append(f"• {rec['operation']}")
            report_lines.append(f"  Issue: {rec['issue']}")
            report_lines.append(f"  Suggestion: {rec['suggestion']}")
            report_lines.append("")
        
        # Add system statistics
        if '_system' in stats:
            system_stats = stats['_system']
            report_lines.extend([
                "SYSTEM STATISTICS:",
                "-" * 18,
                f"Average CPU Usage: {system_stats.get('avg_cpu_percent', 0):.1f}%",
                f"Average Memory Usage: {system_stats.get('avg_memory_percent', 0):.1f}%",
                f"Monitoring Samples: {system_stats.get('sample_count', 0)}",
                ""
            ])
        
        return "\n".join(report_lines)


# Global instances
profiler_manager = ProfilerManager()
cprofile_wrapper = CProfileWrapper()
memory_profiler = MemoryProfiler()
bottleneck_analyzer = BottleneckAnalyzer(profiler_manager)

# Convenience functions
enable_profiling = lambda: setattr(profiler_manager, 'profiling_enabled', True)
disable_profiling = lambda: setattr(profiler_manager, 'profiling_enabled', False)
get_performance_stats = profiler_manager.get_all_stats
reset_performance_stats = profiler_manager.reset_metrics