"""
Celery application configuration for Bot Provisional.
Handles async task processing.
"""

import logging
from celery import Celery

from src.common.config import settings

# Setup logger
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'bot_provisional',
    broker=f'redis://{settings.redis_host}:{settings.redis_port}/1',
    backend=f'redis://{settings.redis_host}:{settings.redis_port}/2',
    include=['src.common.tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

logger.info("Celery app configured successfully")


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    logger.info(f'Request: {self.request!r}')
    return 'Debug task completed'


if __name__ == '__main__':
    celery_app.start()