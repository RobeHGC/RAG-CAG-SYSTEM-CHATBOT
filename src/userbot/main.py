"""
Telegram Userbot for Bot Provisional.
Handles message reception and user interaction with debouncing, typing simulation, and batch processing.
"""

import asyncio
import json
import logging
import random
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import Message, SendMessageTypingAction

from src.common.config import settings
from src.common.database import get_redis_client

# Setup logger
logger = logging.getLogger(__name__)


class MessageBatch:
    """Represents a batch of messages from a user."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.messages: List[Dict] = []
        self.last_message_time = time.time()
        self.emotional_trajectory = {}
        self.priority = 0.5
    
    def add_message(self, message: Message):
        """Add a message to the batch."""
        self.messages.append({
            'text': message.text,
            'timestamp': message.date,
            'has_image': message.photo is not None,
            'message_id': message.id,
            'emotional_preview': {}  # To be filled by emotional analyzer
        })
        self.last_message_time = time.time()
    
    def to_dict(self) -> Dict:
        """Convert batch to dictionary for processing."""
        return {
            'user_id': str(self.user_id),
            'messages': self.messages,
            'emotional_trajectory': self.emotional_trajectory,
            'priority': self.priority
        }


class UserBot:
    """Telegram userbot implementation with advanced features."""
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.is_running = False
        self.redis_client = None
        
        # Message batching and debouncing
        self.message_batches: Dict[int, MessageBatch] = defaultdict(lambda: None)
        self.debounce_tasks: Dict[int, asyncio.Task] = {}
        
        # Configuration
        self.debounce_time = 120  # seconds
        self.batch_delay = 6  # seconds between batches
        self.max_words_per_bubble = 20
        self.typing_speed_factor = 1.0
        self.emotional_priority_threshold = 0.7
        self.max_parallel_users = 10
        self.message_age_limit = 12  # hours
        
        # Session management
        self.session_path = settings.data_dir / "sessions"
        self.session_path.mkdir(exist_ok=True)
        
        logger.info("UserBot initialized")
    
    async def setup_client(self):
        """Initialize Telethon client with authentication."""
        session_file = self.session_path / f"{settings.telegram_session_name}.session"
        
        self.client = TelegramClient(
            str(session_file),
            settings.telegram_api_id,
            settings.telegram_api_hash
        )
        
        await self.client.start()
        
        # Verify authentication
        if not await self.client.is_user_authorized():
            logger.error("User not authorized. Please run authentication script first.")
            raise RuntimeError("Telegram authentication required")
        
        # Setup event handlers
        self.client.add_event_handler(
            self.handle_new_message,
            events.NewMessage(incoming=True, forwards=False)
        )
        
        logger.info(f"Telegram client connected as {(await self.client.get_me()).username}")
    
    async def setup_redis(self):
        """Initialize Redis connection."""
        self.redis_client = await get_redis_client()
        logger.info("Redis client connected")
    
    async def handle_new_message(self, event: events.NewMessage.Event):
        """Handle incoming messages with debouncing."""
        message = event.message
        user_id = message.sender_id
        
        # Skip if from self
        if user_id == (await self.client.get_me()).id:
            return
        
        logger.info(f"New message from user {user_id}: {message.text[:50]}...")
        
        # Create or update message batch
        if self.message_batches[user_id] is None:
            self.message_batches[user_id] = MessageBatch(user_id)
        
        batch = self.message_batches[user_id]
        batch.add_message(message)
        
        # Cancel existing debounce task if any
        if user_id in self.debounce_tasks:
            self.debounce_tasks[user_id].cancel()
        
        # Create new debounce task
        self.debounce_tasks[user_id] = asyncio.create_task(
            self.debounce_and_process(user_id)
        )
    
    async def debounce_and_process(self, user_id: int):
        """Debounce messages and process batch after timeout."""
        try:
            # Wait for debounce time
            await asyncio.sleep(self.debounce_time)
            
            # Process the batch
            batch = self.message_batches[user_id]
            if batch and batch.messages:
                await self.process_message_batch(batch)
                
                # Clear the batch
                self.message_batches[user_id] = None
                
        except asyncio.CancelledError:
            logger.debug(f"Debounce cancelled for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Error in debounce_and_process for user {user_id}: {e}")
        finally:
            # Remove task reference
            self.debounce_tasks.pop(user_id, None)
    
    async def process_message_batch(self, batch: MessageBatch):
        """Process a batch of messages."""
        logger.info(f"Processing batch of {len(batch.messages)} messages from user {batch.user_id}")
        
        try:
            # Store batch in Redis for processing
            batch_key = f"batch:{batch.user_id}:{int(time.time())}"
            await self.redis_client.setex(
                batch_key,
                300,  # 5 minute TTL
                json.dumps(batch.to_dict(), default=str)
            )
            
            # Send to supervisor (placeholder - would use actual message queue)
            await self.send_to_supervisor(batch)
            
            # Simulate processing delay
            await asyncio.sleep(self.batch_delay)
            
            # Get response (placeholder - would come from supervisor)
            response = await self.get_supervisor_response(batch)
            
            if response:
                await self.send_response(batch.user_id, response)
                
        except Exception as e:
            logger.error(f"Error processing batch for user {batch.user_id}: {e}")
    
    async def send_to_supervisor(self, batch: MessageBatch):
        """Send batch to supervisor for processing."""
        # TODO: Implement actual supervisor communication
        logger.info(f"Sending batch to supervisor for user {batch.user_id}")
    
    async def get_supervisor_response(self, batch: MessageBatch) -> Optional[str]:
        """Get response from supervisor."""
        # TODO: Implement actual supervisor communication
        # Placeholder response
        return "I understand you've sent multiple messages. Let me process them and respond appropriately."
    
    async def send_response(self, user_id: int, response: str):
        """Send response with typing simulation and message splitting."""
        try:
            # Calculate typing duration
            typing_duration = await self.calculate_typing_duration(response)
            
            # Simulate typing
            await self.simulate_typing(user_id, typing_duration)
            
            # Split response into bubbles
            bubbles = self.split_into_bubbles(response)
            
            # Send each bubble
            for i, bubble in enumerate(bubbles):
                if i > 0:
                    # Small delay between bubbles
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
                await self.client.send_message(user_id, bubble)
                logger.info(f"Sent bubble {i+1}/{len(bubbles)} to user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending response to user {user_id}: {e}")
    
    async def calculate_typing_duration(self, text: str) -> float:
        """Calculate realistic typing duration based on text length."""
        base_time = 2.0
        char_time = len(text) * 0.05
        emotional_adjustment = random.uniform(0, 2)  # Placeholder
        
        duration = (base_time + char_time + emotional_adjustment) * self.typing_speed_factor
        
        # Add some randomness
        duration *= random.uniform(0.8, 1.2)
        
        return min(duration, 30)  # Cap at 30 seconds
    
    async def simulate_typing(self, user_id: int, duration: float):
        """Simulate typing with realistic patterns."""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Send typing action
            await self.client(SetTypingRequest(
                peer=user_id,
                action=SendMessageTypingAction()
            ))
            
            # Wait with variation
            wait_time = random.uniform(0.5, 1.5)
            await asyncio.sleep(wait_time)
    
    def split_into_bubbles(self, text: str) -> List[str]:
        """Split text into natural message bubbles."""
        # Split by sentences first
        sentences = text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')
        
        bubbles = []
        current_bubble = []
        current_words = 0
        
        for sentence in sentences:
            words = sentence.split()
            
            # Check if adding this sentence would exceed limit
            if current_words + len(words) > self.max_words_per_bubble and current_bubble:
                bubbles.append(' '.join(current_bubble))
                current_bubble = []
                current_words = 0
            
            current_bubble.extend(words)
            current_words += len(words)
            
            # Force split on punctuation
            if sentence.strip().endswith(('.', '!', '?')):
                bubbles.append(' '.join(current_bubble))
                current_bubble = []
                current_words = 0
        
        # Add remaining words
        if current_bubble:
            bubbles.append(' '.join(current_bubble))
        
        return [b.strip() for b in bubbles if b.strip()]
    
    async def recover_missed_messages(self):
        """Recover messages that were missed during downtime."""
        try:
            # Get last processed message ID from Redis
            last_message_key = "userbot:last_processed_message"
            last_message_id = await self.redis_client.get(last_message_key)
            
            if last_message_id:
                last_message_id = int(last_message_id)
                logger.info(f"Recovering messages after ID {last_message_id}")
                
                # Get recent dialogs
                async for dialog in self.client.iter_dialogs(limit=20):
                    if dialog.is_user:
                        # Get messages since last processed
                        messages = []
                        async for message in self.client.iter_messages(
                            dialog.entity,
                            min_id=last_message_id,
                            limit=50
                        ):
                            # Check age limit
                            if datetime.now() - message.date > timedelta(hours=self.message_age_limit):
                                continue
                            
                            if message.sender_id != (await self.client.get_me()).id:
                                messages.append(message)
                        
                        if messages:
                            logger.info(f"Found {len(messages)} missed messages from {dialog.name}")
                            # Process in chronological order
                            for msg in reversed(messages):
                                event = events.NewMessage.Event(msg)
                                await self.handle_new_message(event)
                                
        except Exception as e:
            logger.error(f"Error recovering missed messages: {e}")
    
    async def start(self):
        """Start the userbot."""
        logger.info("Starting UserBot...")
        self.is_running = True
        
        try:
            # Setup components
            await self.setup_client()
            await self.setup_redis()
            
            # Recover missed messages
            await self.recover_missed_messages()
            
            logger.info("UserBot started successfully")
            
            # Run client
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting userbot: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the userbot."""
        logger.info("Stopping UserBot...")
        self.is_running = False
        
        # Cancel all debounce tasks
        for task in self.debounce_tasks.values():
            task.cancel()
        
        # Disconnect client
        if self.client:
            await self.client.disconnect()
        
        # Close Redis
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("UserBot stopped")


async def main():
    """Main function to run the userbot."""
    bot = UserBot()
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        bot.is_running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.start()
    except Exception as e:
        logger.error(f"Error running userbot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())