#!/usr/bin/env python3
"""
Test script for memory consolidation pipeline.
Tests the Celery tasks and consolidation logic.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memoria.consolidation import consolidate_user_memories
from src.common.celery_app import celery_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_direct_consolidation():
    """Test consolidation task directly (without Celery)."""
    logger.info("Testing direct consolidation...")
    
    # Create a mock task instance
    task = consolidate_user_memories
    task._embedding_generator = None
    task._llm_client = None
    task._neo4j_driver = None
    task._redis_client = None
    
    try:
        result = consolidate_user_memories('test_user_123')
        logger.info(f"Direct consolidation result: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"Direct consolidation failed: {e}")
        return False


def test_celery_task():
    """Test consolidation via Celery task."""
    logger.info("Testing Celery task submission...")
    
    try:
        # Submit task asynchronously
        result = consolidate_user_memories.delay('test_user_123')
        logger.info(f"Task submitted with ID: {result.id}")
        
        # Wait for result (with timeout)
        logger.info("Waiting for task completion...")
        task_result = result.get(timeout=60)
        
        logger.info(f"Celery task result: {json.dumps(task_result, indent=2)}")
        return True
        
    except Exception as e:
        logger.error(f"Celery task failed: {e}")
        return False


def test_health_check():
    """Test the health check task."""
    logger.info("Testing health check...")
    
    try:
        from src.memoria.consolidation import check_consolidation_health
        result = check_consolidation_health()
        logger.info(f"Health check result: {json.dumps(result, indent=2)}")
        return result.get('status') == 'healthy'
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


def test_schedule_task():
    """Test the scheduling task."""
    logger.info("Testing schedule consolidations...")
    
    try:
        from src.memoria.consolidation import schedule_consolidations
        result = schedule_consolidations()
        logger.info(f"Schedule result: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"Schedule task failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("Starting memory consolidation tests...")
    
    tests = [
        ("Health Check", test_health_check),
        ("Direct Consolidation", test_direct_consolidation),
        ("Schedule Task", test_schedule_task),
        ("Celery Task", test_celery_task),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            success = test_func()
            results.append((test_name, success))
            logger.info(f"Test {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            logger.error(f"Test {test_name} error: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)