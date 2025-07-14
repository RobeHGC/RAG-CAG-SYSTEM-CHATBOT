#!/usr/bin/env python3
"""
Load testing script for AI Companion performance validation.
Tests concurrent users, memory system, and database performance under load.
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
import argparse

import aiohttp
import numpy as np
from prometheus_client import CollectorRegistry, Gauge, Histogram, Counter, push_to_gateway

# Import project modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.common.performance_config import performance_config, LoadTestingConfig
from src.common.monitoring import PerformanceMonitor
from src.memoria.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    """Results from a load test scenario."""
    
    scenario_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    requests_per_second: float
    errors_per_second: float
    error_rate_percent: float
    memory_usage_mb: float
    cache_hit_rate: float
    database_errors: int
    timeout_errors: int
    duration_seconds: float
    timestamp: datetime


@dataclass
class UserSession:
    """Represents a simulated user session."""
    
    user_id: str
    session_start: datetime
    messages_sent: int = 0
    memories_queried: int = 0
    errors_encountered: int = 0
    total_response_time: float = 0.0
    active: bool = True


class LoadTestMetrics:
    """Collects and manages load test metrics."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Response time metrics
        self.response_time = Histogram(
            'load_test_response_time_seconds',
            'Response time for load test requests',
            ['endpoint', 'user_id'],
            registry=self.registry
        )
        
        # Request counters
        self.request_count = Counter(
            'load_test_requests_total',
            'Total load test requests',
            ['endpoint', 'status', 'user_id'],
            registry=self.registry
        )
        
        # System metrics
        self.concurrent_users = Gauge(
            'load_test_concurrent_users',
            'Number of concurrent users',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'load_test_memory_usage_mb',
            'Memory usage during load test',
            registry=self.registry
        )
        
        self.cache_hit_rate = Gauge(
            'load_test_cache_hit_rate',
            'Cache hit rate during load test',
            registry=self.registry
        )
    
    def record_request(self, endpoint: str, user_id: str, response_time: float, success: bool):
        """Record a request metric."""
        status = 'success' if success else 'error'
        self.response_time.labels(endpoint=endpoint, user_id=user_id).observe(response_time)
        self.request_count.labels(endpoint=endpoint, status=status, user_id=user_id).inc()
    
    def update_system_metrics(self, concurrent_users: int, memory_mb: float, cache_hit_rate: float):
        """Update system-level metrics."""
        self.concurrent_users.set(concurrent_users)
        self.memory_usage.set(memory_mb)
        self.cache_hit_rate.set(cache_hit_rate)


class AICompanionLoadTester:
    """Main load testing class for AI Companion."""
    
    def __init__(self, config: LoadTestingConfig):
        """
        Initialize load tester.
        
        Args:
            config: Load testing configuration
        """
        self.config = config
        self.metrics = LoadTestMetrics()
        self.monitor = PerformanceMonitor()
        self.memory_manager = None
        
        # Test data
        self.test_messages = self._generate_test_messages()
        self.test_queries = self._generate_test_queries()
        
        # Results tracking
        self.results: List[Tuple[str, float, bool, str]] = []
        self.user_sessions: Dict[str, UserSession] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def _generate_test_messages(self) -> List[str]:
        """Generate realistic test messages."""
        templates = [
            "Hello, how are you today?",
            "I'm feeling {emotion} about {topic}.",
            "Can you help me with {task}?",
            "I remember we talked about {memory_topic} before.",
            "What do you think about {opinion_topic}?",
            "I'm worried about {concern}.",
            "That's interesting! Tell me more about {topic}.",
            "I disagree with {statement}.",
            "How can I improve my {skill}?",
            "I'm excited about {event}!",
        ]
        
        emotions = ["happy", "sad", "anxious", "excited", "confused", "frustrated"]
        topics = ["work", "family", "hobbies", "travel", "technology", "health"]
        tasks = ["planning", "learning", "organizing", "deciding", "understanding"]
        
        messages = []
        for template in templates:
            for _ in range(10):  # Generate 10 variations per template
                message = template.format(
                    emotion=random.choice(emotions),
                    topic=random.choice(topics),
                    task=random.choice(tasks),
                    memory_topic=random.choice(topics),
                    opinion_topic=random.choice(topics),
                    concern=random.choice(topics + ["the future", "my decisions"]),
                    statement=random.choice(["that idea", "the proposal", "the plan"]),
                    skill=random.choice(["communication", "productivity", "focus"]),
                    event=random.choice(["the weekend", "my vacation", "the project"])
                )
                messages.append(message)
        
        return messages
    
    def _generate_test_queries(self) -> List[str]:
        """Generate test queries for memory retrieval."""
        return [
            "What did we discuss about work?",
            "Tell me about my family conversations",
            "What are my hobbies?",
            "Recall our travel discussions",
            "What technology topics interest me?",
            "Health-related conversations",
            "Times I felt happy",
            "When was I worried?",
            "What are my goals?",
            "Past learning experiences"
        ]
    
    async def initialize(self):
        """Initialize load testing components."""
        try:
            # Initialize memory manager (if testing memory operations)
            self.memory_manager = MemoryManager(
                redis_url="redis://localhost:6379",
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password"
            )
            await self.memory_manager.initialize()
            
            logger.info("Load tester initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize load tester: {e}")
            raise
    
    async def simulate_user_session(self, user_id: str, session_duration: int) -> UserSession:
        """
        Simulate a single user session.
        
        Args:
            user_id: Unique user identifier
            session_duration: Session duration in seconds
            
        Returns:
            UserSession with results
        """
        session = UserSession(
            user_id=user_id,
            session_start=datetime.now()
        )
        
        self.user_sessions[user_id] = session
        session_end = time.time() + session_duration
        
        try:
            while time.time() < session_end and session.active:
                # Choose action type
                if random.random() < self.config.test_memory_queries_ratio:
                    # Memory query
                    await self._simulate_memory_query(session)
                else:
                    # Regular message
                    await self._simulate_message_send(session)
                
                # Random delay between actions (0.5-3 seconds)
                await asyncio.sleep(random.uniform(0.5, 3.0))
                
        except Exception as e:
            logger.error(f"Error in user session {user_id}: {e}")
            session.errors_encountered += 1
            session.active = False
        
        return session
    
    async def _simulate_message_send(self, session: UserSession):
        """Simulate sending a message."""
        start_time = time.time()
        success = False
        
        try:
            # Select random message
            message = random.choice(self.test_messages)
            
            # Store message in memory system
            if self.memory_manager:
                await self.memory_manager.store_message(
                    user_id=session.user_id,
                    content=message,
                    message_type="user"
                )
            
            response_time = (time.time() - start_time) * 1000
            session.messages_sent += 1
            session.total_response_time += response_time
            success = True
            
            # Record metrics
            self.metrics.record_request("store_message", session.user_id, response_time / 1000, success)
            self.results.append((session.user_id, response_time, success, "store_message"))
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            session.errors_encountered += 1
            logger.warning(f"Message send failed for {session.user_id}: {e}")
            
            self.metrics.record_request("store_message", session.user_id, response_time / 1000, False)
            self.results.append((session.user_id, response_time, False, "store_message"))
    
    async def _simulate_memory_query(self, session: UserSession):
        """Simulate querying memory."""
        start_time = time.time()
        success = False
        
        try:
            # Select random query
            query = random.choice(self.test_queries)
            
            # Query memory system
            if self.memory_manager:
                result = await self.memory_manager.retrieve_memories(
                    user_id=session.user_id,
                    query=query,
                    limit=5
                )
            
            response_time = (time.time() - start_time) * 1000
            session.memories_queried += 1
            session.total_response_time += response_time
            success = True
            
            # Record metrics
            self.metrics.record_request("retrieve_memories", session.user_id, response_time / 1000, success)
            self.results.append((session.user_id, response_time, success, "retrieve_memories"))
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            session.errors_encountered += 1
            logger.warning(f"Memory query failed for {session.user_id}: {e}")
            
            self.metrics.record_request("retrieve_memories", session.user_id, response_time / 1000, False)
            self.results.append((session.user_id, response_time, False, "retrieve_memories"))
    
    async def run_load_test(self, concurrent_users: int, duration_seconds: int) -> LoadTestResult:
        """
        Run load test with specified parameters.
        
        Args:
            concurrent_users: Number of concurrent users to simulate
            duration_seconds: Test duration in seconds
            
        Returns:
            LoadTestResult with performance metrics
        """
        logger.info(f"Starting load test: {concurrent_users} users for {duration_seconds}s")
        
        self.start_time = datetime.now()
        start_timestamp = time.time()
        
        # Create user sessions
        user_tasks = []
        for i in range(concurrent_users):
            user_id = f"load_test_user_{i:04d}"
            task = asyncio.create_task(
                self.simulate_user_session(user_id, duration_seconds)
            )
            user_tasks.append(task)
        
        # Update concurrent users metric
        self.metrics.update_system_metrics(concurrent_users, 0.0, 0.0)
        
        # Wait for all sessions to complete
        sessions = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        self.end_time = datetime.now()
        actual_duration = time.time() - start_timestamp
        
        # Calculate results
        result = self._calculate_results("load_test", actual_duration)
        
        logger.info(f"Load test completed: {result.successful_requests}/{result.total_requests} requests successful")
        logger.info(f"Average response time: {result.avg_response_time_ms:.2f}ms")
        logger.info(f"P95 response time: {result.p95_response_time_ms:.2f}ms")
        logger.info(f"Error rate: {result.error_rate_percent:.2f}%")
        
        return result
    
    def _calculate_results(self, scenario_name: str, duration: float) -> LoadTestResult:
        """Calculate load test results from collected data."""
        
        if not self.results:
            return LoadTestResult(
                scenario_name=scenario_name,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0.0,
                p50_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                max_response_time_ms=0.0,
                requests_per_second=0.0,
                errors_per_second=0.0,
                error_rate_percent=0.0,
                memory_usage_mb=0.0,
                cache_hit_rate=0.0,
                database_errors=0,
                timeout_errors=0,
                duration_seconds=duration,
                timestamp=datetime.now()
            )
        
        # Extract response times and success flags
        response_times = [result[1] for result in self.results]
        successes = [result[2] for result in self.results]
        
        total_requests = len(self.results)
        successful_requests = sum(successes)
        failed_requests = total_requests - successful_requests
        
        # Calculate percentiles
        response_times_sorted = sorted(response_times)
        avg_response_time = statistics.mean(response_times)
        
        def percentile(data, p):
            if not data:
                return 0.0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = k - f
            if f == len(data) - 1:
                return data[f]
            return data[f] * (1 - c) + data[f + 1] * c
        
        p50 = percentile(response_times_sorted, 50)
        p95 = percentile(response_times_sorted, 95)
        p99 = percentile(response_times_sorted, 99)
        max_response_time = max(response_times) if response_times else 0.0
        
        # Calculate rates
        requests_per_second = total_requests / duration if duration > 0 else 0.0
        errors_per_second = failed_requests / duration if duration > 0 else 0.0
        error_rate_percent = (failed_requests / total_requests * 100) if total_requests > 0 else 0.0
        
        # Get cache hit rate (if available)
        cache_hit_rate = 0.0
        try:
            from src.common.cache import cache_manager
            cache_hit_rate = cache_manager.get_overall_hit_rate()
        except Exception:
            pass
        
        return LoadTestResult(
            scenario_name=scenario_name,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_response_time,
            p50_response_time_ms=p50,
            p95_response_time_ms=p95,
            p99_response_time_ms=p99,
            max_response_time_ms=max_response_time,
            requests_per_second=requests_per_second,
            errors_per_second=errors_per_second,
            error_rate_percent=error_rate_percent,
            memory_usage_mb=0.0,  # Would need system monitoring integration
            cache_hit_rate=cache_hit_rate,
            database_errors=0,  # Would need to parse error types
            timeout_errors=0,
            duration_seconds=duration,
            timestamp=datetime.now()
        )
    
    async def run_ramp_up_test(self) -> List[LoadTestResult]:
        """Run a ramp-up test with increasing user load."""
        results = []
        
        user_steps = [
            self.config.concurrent_users_min,
            self.config.concurrent_users_min * 2,
            self.config.concurrent_users_min * 5,
            self.config.concurrent_users_min * 10,
            self.config.concurrent_users_max
        ]
        
        for users in user_steps:
            if users > self.config.concurrent_users_max:
                users = self.config.concurrent_users_max
            
            logger.info(f"Running ramp-up test with {users} users")
            
            # Clear previous results
            self.results.clear()
            self.user_sessions.clear()
            
            # Run test
            result = await self.run_load_test(users, 60)  # 1 minute per step
            result.scenario_name = f"ramp_up_{users}_users"
            results.append(result)
            
            # Brief pause between tests
            await asyncio.sleep(10)
        
        return results
    
    def save_results(self, results: List[LoadTestResult], filename: str):
        """Save load test results to JSON file."""
        results_data = [asdict(result) for result in results]
        
        # Convert datetime objects to strings
        for result_data in results_data:
            if 'timestamp' in result_data:
                result_data['timestamp'] = result_data['timestamp'].isoformat()
        
        with open(filename, 'w') as f:
            json.dump({
                'test_config': asdict(self.config),
                'results': results_data,
                'summary': self._generate_summary(results)
            }, f, indent=2)
        
        logger.info(f"Results saved to {filename}")
    
    def _generate_summary(self, results: List[LoadTestResult]) -> Dict:
        """Generate summary statistics from results."""
        if not results:
            return {}
        
        return {
            'total_tests': len(results),
            'avg_requests_per_second': statistics.mean([r.requests_per_second for r in results]),
            'avg_response_time_ms': statistics.mean([r.avg_response_time_ms for r in results]),
            'max_p95_response_time_ms': max([r.p95_response_time_ms for r in results]),
            'avg_error_rate_percent': statistics.mean([r.error_rate_percent for r in results]),
            'total_requests': sum([r.total_requests for r in results]),
            'total_successful_requests': sum([r.successful_requests for r in results]),
            'total_failed_requests': sum([r.failed_requests for r in results])
        }


async def main():
    """Main load testing function."""
    parser = argparse.ArgumentParser(description='AI Companion Load Tester')
    parser.add_argument('--users', type=int, default=50, help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds')
    parser.add_argument('--scenario', choices=['load', 'ramp', 'stress'], default='load', 
                       help='Test scenario to run')
    parser.add_argument('--output', type=str, default='load_test_results.json', 
                       help='Output file for results')
    
    args = parser.parse_args()
    
    # Get configuration
    config = performance_config.get_load_testing_config()
    config.concurrent_users_max = args.users
    config.test_duration_seconds = args.duration
    
    # Initialize load tester
    tester = AICompanionLoadTester(config)
    
    try:
        await tester.initialize()
        
        if args.scenario == 'load':
            # Single load test
            result = await tester.run_load_test(args.users, args.duration)
            results = [result]
        elif args.scenario == 'ramp':
            # Ramp-up test
            results = await tester.run_ramp_up_test()
        elif args.scenario == 'stress':
            # Stress test with maximum users
            result = await tester.run_load_test(config.concurrent_users_max, args.duration)
            results = [result]
        
        # Save results
        tester.save_results(results, args.output)
        
        # Print summary
        print("\n" + "="*50)
        print("LOAD TEST SUMMARY")
        print("="*50)
        
        for result in results:
            print(f"\nScenario: {result.scenario_name}")
            print(f"Total Requests: {result.total_requests}")
            print(f"Success Rate: {(result.successful_requests/result.total_requests)*100:.1f}%")
            print(f"Avg Response Time: {result.avg_response_time_ms:.2f}ms")
            print(f"P95 Response Time: {result.p95_response_time_ms:.2f}ms")
            print(f"Requests/sec: {result.requests_per_second:.1f}")
            print(f"Error Rate: {result.error_rate_percent:.2f}%")
        
        print(f"\nResults saved to: {args.output}")
        
    except Exception as e:
        logger.error(f"Load test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    asyncio.run(main())