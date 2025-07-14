"""
Memory Management System for Nadia AI Companion.

This module implements the dual-memory architecture:
- Short-term memory: Context window management with Redis
- Long-term memory: Semantic storage with Neo4j and embeddings
"""

import asyncio
import json
import logging
import time
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import redis.asyncio as redis
from neo4j import AsyncGraphDatabase
import numpy as np

from .embeddings import EmbeddingManager
from .emotional_analyzer import VADEmotionalAnalyzer, EmotionalState
from .forgetting_curves import AdaptiveForgettingCurve, create_forgetting_curve_system
from ..common.cache import cache_manager, CacheKeyGenerator
from ..common.monitoring import monitor, track_performance
from ..common.rate_limiter import rate_limiter, LimitType
from ..common.enhanced_logging import enhanced_logger, log_memory_operation, log_performance
from ..common.sentry_config import SentryContextManager, track_memory_performance
from ..common.profiling import profile_performance, profile_async_performance, profile_code_block

logger = enhanced_logger.get_logger(__name__)


@dataclass
class MemoryMessage:
    """Represents a message in memory with metadata."""
    
    id: str
    user_id: str
    content: str
    timestamp: datetime
    message_type: str  # 'user' or 'assistant'
    emotional_state: Optional[EmotionalState] = None
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        if self.emotional_state:
            data['emotional_state'] = asdict(self.emotional_state)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryMessage':
        """Create from dictionary."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if 'emotional_state' in data and data['emotional_state']:
            data['emotional_state'] = EmotionalState(**data['emotional_state'])
        return cls(**data)


@dataclass
class MemoryRetrievalResult:
    """Result of memory retrieval operation."""
    
    messages: List[MemoryMessage]
    similarity_scores: List[float]
    total_retrieved: int
    retrieval_time_ms: float


class ContextWindowManager:
    """Manages short-term context window using Redis."""
    
    def __init__(self, redis_client: redis.Redis, window_size: int = 50):
        """
        Initialize context window manager.
        
        Args:
            redis_client: Redis async client
            window_size: Maximum number of messages to keep in context (20-100)
        """
        self.redis = redis_client
        self.window_size = max(20, min(100, window_size))  # Enforce 20-100 range
        
    async def add_message(self, user_id: str, message: MemoryMessage) -> None:
        """Add message to context window."""
        context_key = f"context:{user_id}"
        
        # Add message to list
        await self.redis.lpush(context_key, json.dumps(message.to_dict()))
        
        # Trim to window size
        await self.redis.ltrim(context_key, 0, self.window_size - 1)
        
        # Set TTL for context (24 hours)
        await self.redis.expire(context_key, 86400)
        
    async def get_context(self, user_id: str, limit: Optional[int] = None) -> List[MemoryMessage]:
        """Retrieve context window for user."""
        context_key = f"context:{user_id}"
        limit = limit or self.window_size
        
        # Get messages from Redis
        raw_messages = await self.redis.lrange(context_key, 0, limit - 1)
        
        messages = []
        for raw_msg in raw_messages:
            try:
                msg_data = json.loads(raw_msg)
                messages.append(MemoryMessage.from_dict(msg_data))
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to decode message: {e}")
                
        return messages
    
    async def clear_context(self, user_id: str) -> None:
        """Clear context window for user."""
        context_key = f"context:{user_id}"
        await self.redis.delete(context_key)
    
    async def get_context_size(self, user_id: str) -> int:
        """Get current context window size."""
        context_key = f"context:{user_id}"
        return await self.redis.llen(context_key)


class LongTermMemoryManager:
    """Manages long-term semantic memory using Neo4j."""
    
    def __init__(self, neo4j_driver, embedding_manager: EmbeddingManager):
        """
        Initialize long-term memory manager.
        
        Args:
            neo4j_driver: Neo4j async driver
            embedding_manager: Embedding manager for similarity search
        """
        self.driver = neo4j_driver
        self.embedding_manager = embedding_manager
        
    async def store_memory(self, message: MemoryMessage) -> str:
        """Store message as long-term memory node."""
        
        # Check rate limit for memory operations
        rate_result = rate_limiter.check_rate_limit(message.user_id, LimitType.MEMORY_OPERATIONS_PER_MINUTE)
        if not rate_result.allowed:
            logger.warning(f"Memory storage rate limited for user {message.user_id}")
            raise Exception(f"Rate limit exceeded for memory operations")
        
        with monitor.track_db_operation('neo4j', 'memory_storage'):
            # Generate embedding if not present
            if not message.embedding:
                message.embedding = await self.embedding_manager.get_embedding(message.content)
        
        memory_id = f"memory_{message.user_id}_{int(time.time())}"
        
        async with self.driver.session() as session:
            query = """
            CREATE (m:Memory {
                id: $memory_id,
                user_id: $user_id,
                content: $content,
                timestamp: datetime($timestamp),
                message_type: $message_type,
                embedding: $embedding,
                valence: $valence,
                arousal: $arousal,
                dominance: $dominance,
                emotional_intensity: $emotional_intensity,
                primary_emotion: $primary_emotion,
                confidence: $confidence,
                metadata: $metadata
            })
            RETURN m.id as memory_id
            """
            
            result = await session.run(query, {
                'memory_id': memory_id,
                'user_id': message.user_id,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'message_type': message.message_type,
                'embedding': message.embedding,
                'valence': message.emotional_state.valence if message.emotional_state else 0.0,
                'arousal': message.emotional_state.arousal if message.emotional_state else 0.0,
                'dominance': message.emotional_state.dominance if message.emotional_state else 0.0,
                'emotional_intensity': message.emotional_state.confidence if message.emotional_state else 0.0,
                'primary_emotion': message.emotional_state.primary_emotion if message.emotional_state else 'neutral',
                'confidence': message.emotional_state.confidence if message.emotional_state else 0.0,
                'metadata': json.dumps(message.metadata or {})
            })
            
            # Invalidate related caches since we added new memory
            cache_manager.invalidate_user_cache(message.user_id, ['memory'])
            
            monitor.record_memory_operation('store_memory', 'success')
            
            return memory_id
    
    async def retrieve_similar_memories(
        self, 
        query_text: str, 
        user_id: str, 
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> MemoryRetrievalResult:
        """Retrieve memories similar to query text."""
        
        start_time = time.time()
        
        # Check rate limit for memory operations
        rate_result = rate_limiter.check_rate_limit(user_id, LimitType.MEMORY_OPERATIONS_PER_MINUTE)
        if not rate_result.allowed:
            logger.warning(f"Memory retrieval rate limited for user {user_id}")
            return MemoryRetrievalResult([], [], 0, 0.0)
        
        # Generate cache key for this query
        query_hash = hashlib.md5(f"{query_text}:{limit}:{similarity_threshold}".encode()).hexdigest()
        
        # Try to get from cache first
        cached_result = cache_manager.get_memory_query_cache(user_id, query_hash)
        if cached_result:
            retrieval_time = (time.time() - start_time) * 1000
            monitor.record_memory_operation('retrieve_similar', 'cache_hit')
            
            # Convert cached data back to MemoryRetrievalResult
            messages = [MemoryMessage.from_dict(msg_data) for msg_data in cached_result['messages']]
            return MemoryRetrievalResult(
                messages=messages,
                similarity_scores=cached_result['similarity_scores'],
                total_retrieved=cached_result['total_retrieved'],
                retrieval_time_ms=retrieval_time
            )
        
        with monitor.track_db_operation('neo4j', 'memory_retrieval'):
            # Get query embedding
            query_embedding = await self.embedding_manager.get_embedding(query_text)
        
        async with self.driver.session() as session:
            # Use cosine similarity for retrieval
            cypher_query = """
            MATCH (m:Memory {user_id: $user_id})
            WHERE m.embedding IS NOT NULL
            WITH m, 
                 reduce(dot = 0, i IN range(0, size($query_embedding)-1) | 
                   dot + ($query_embedding[i] * m.embedding[i])) as dot_product,
                 sqrt(reduce(norm_a = 0, i IN range(0, size($query_embedding)-1) | 
                   norm_a + ($query_embedding[i] * $query_embedding[i]))) as norm_a,
                 sqrt(reduce(norm_b = 0, i IN range(0, size(m.embedding)-1) | 
                   norm_b + (m.embedding[i] * m.embedding[i]))) as norm_b
            WITH m, dot_product / (norm_a * norm_b) as similarity
            WHERE similarity >= $similarity_threshold
            RETURN m, similarity
            ORDER BY similarity DESC
            LIMIT $limit
            """
            
            result = await session.run(cypher_query, {
                'user_id': user_id,
                'query_embedding': query_embedding,
                'similarity_threshold': similarity_threshold,
                'limit': limit
            })
            
            records = await result.data()
            
            messages = []
            similarities = []
            
            for record in records:
                memory_data = record['m']
                similarity = record['similarity']
                
                # Reconstruct MemoryMessage
                emotional_state = EmotionalState(
                    valence=memory_data.get('valence', 0.0),
                    arousal=memory_data.get('arousal', 0.0),
                    dominance=memory_data.get('dominance', 0.0),
                    confidence=memory_data.get('confidence', 0.0),
                    primary_emotion=memory_data.get('primary_emotion', 'neutral'),
                    emotion_scores={},
                    processing_time=0.0
                )
                
                memory_message = MemoryMessage(
                    id=memory_data['id'],
                    user_id=memory_data['user_id'],
                    content=memory_data['content'],
                    timestamp=datetime.fromisoformat(memory_data['timestamp']),
                    message_type=memory_data['message_type'],
                    emotional_state=emotional_state,
                    embedding=memory_data.get('embedding'),
                    metadata=json.loads(memory_data.get('metadata', '{}'))
                )
                
                messages.append(memory_message)
                similarities.append(similarity)
            
            retrieval_time = (time.time() - start_time) * 1000
            
            # Cache the result for future queries
            cache_data = {
                'messages': [msg.to_dict() for msg in messages],
                'similarity_scores': similarities,
                'total_retrieved': len(messages)
            }
            cache_manager.set_memory_query_cache(user_id, query_hash, cache_data, ttl=1800)  # 30 minutes
            
            monitor.record_memory_operation('retrieve_similar', 'success')
            
            return MemoryRetrievalResult(
                messages=messages,
                similarity_scores=similarities,
                total_retrieved=len(messages),
                retrieval_time_ms=retrieval_time
            )
    
    async def cleanup_old_memories(self, user_id: str, days_to_keep: int = 30) -> int:
        """Remove memories older than specified days."""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        async with self.driver.session() as session:
            query = """
            MATCH (m:Memory {user_id: $user_id})
            WHERE m.timestamp < datetime($cutoff_date)
            DELETE m
            RETURN count(m) as deleted_count
            """
            
            result = await session.run(query, {
                'user_id': user_id,
                'cutoff_date': cutoff_date.isoformat()
            })
            
            record = await result.single()
            return record['deleted_count'] if record else 0


class MemoryManager:
    """Main memory management system coordinating short and long-term memory."""
    
    def __init__(
        self, 
        redis_url: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        context_window_size: int = 50
    ):
        """
        Initialize the memory management system.
        
        Args:
            redis_url: Redis connection URL
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            context_window_size: Size of context window (20-100)
        """
        self.redis_url = redis_url
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.context_window_size = context_window_size
        
        # Initialize components
        self.redis_client = None
        self.neo4j_driver = None
        self.context_manager = None
        self.longterm_manager = None
        self.embedding_manager = EmbeddingManager()
        self.emotional_analyzer = VADEmotionalAnalyzer()
        self.forgetting_curve = None
        
        self._initialized = False
    
    @profile_async_performance("memory_system_initialize")
    @log_performance("memory_system_initialize", threshold_ms=5000.0)
    async def initialize(self) -> None:
        """Initialize all memory components."""
        if self._initialized:
            return
            
        correlation_id = enhanced_logger.generate_correlation_id()
        enhanced_logger.set_correlation_id(correlation_id)
        SentryContextManager.add_breadcrumb("Memory system initialization started", "memory_init")
        
        try:
            with profile_code_block("memory_redis_init"):
                # Initialize Redis
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Redis connection established for memory system")
            
            with profile_code_block("memory_neo4j_init"):
                # Initialize Neo4j
                self.neo4j_driver = AsyncGraphDatabase.driver(
                    self.neo4j_uri, 
                    auth=(self.neo4j_user, self.neo4j_password)
                )
                logger.info("Neo4j connection established for memory system")
            
            with profile_code_block("memory_managers_init"):
                # Initialize managers
                self.context_manager = ContextWindowManager(
                    self.redis_client, 
                    self.context_window_size
                )
                self.longterm_manager = LongTermMemoryManager(
                    self.neo4j_driver, 
                    self.embedding_manager
                )
            
            with profile_code_block("memory_ml_init"):
                # Initialize ML components
                await self.embedding_manager.initialize()
                self.emotional_analyzer.initialize()
                logger.info("ML components initialized for memory system")
            
            with profile_code_block("memory_forgetting_init"):
                # Initialize forgetting curve system
                self.forgetting_curve = create_forgetting_curve_system(
                    redis_client=self.redis_client,
                    neo4j_driver=self.neo4j_driver,
                    emotional_analyzer=self.emotional_analyzer
                )
            
            self._initialized = True
            
            # Record initialization metrics
            monitor.increment_counter('memory_system_initializations_total')
            logger.info("Memory management system initialized successfully")
            SentryContextManager.add_breadcrumb("Memory system initialization completed", "memory_init", level="info")
            
        except Exception as e:
            monitor.increment_counter('memory_system_initialization_errors_total')
            logger.error(f"Failed to initialize memory system: {e}")
            SentryContextManager.add_breadcrumb(f"Memory init failed: {e}", "memory_init", level="error")
            raise
    
    @track_performance('store_message')
    @profile_async_performance("memory_store_message", memory_tracking=True)
    @log_memory_operation("store_message")
    @track_memory_performance
    async def store_message(
        self, 
        user_id: str, 
        content: str, 
        message_type: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryMessage:
        """Store a message in both short and long-term memory."""
        
        correlation_id = enhanced_logger.generate_correlation_id()
        enhanced_logger.set_correlation_id(correlation_id)
        enhanced_logger.set_user_context(user_id)
        SentryContextManager.set_memory_context("store_message", 1, user_id)
        
        if not self._initialized:
            await self.initialize()
        
        # Check rate limit for message storage
        rate_result = rate_limiter.check_rate_limit(user_id, LimitType.REQUESTS_PER_MINUTE)
        if not rate_result.allowed:
            monitor.increment_counter('memory_rate_limit_exceeded_total', {'user_id': user_id, 'operation': 'store_message'})
            logger.warning(f"Message storage rate limited for user {user_id}")
            raise Exception(f"Rate limit exceeded for message storage")
        
        start_time = time.time()
        
        try:
            # Analyze emotions
            with profile_code_block("emotion_analysis", memory_tracking=True):
                emotional_state = self.emotional_analyzer.analyze_emotion(content)
                SentryContextManager.add_breadcrumb(f"Emotion analyzed: {emotional_state.primary_emotion if emotional_state else 'none'}", "memory")
            
            # Create memory message
            message = MemoryMessage(
                id=f"msg_{user_id}_{int(time.time() * 1000)}",
                user_id=user_id,
                content=content,
                timestamp=datetime.now(),
                message_type=message_type,
                emotional_state=emotional_state,
                metadata=metadata or {}
            )
            
            # Store in context window (short-term)
            with profile_code_block("short_term_storage"):
                await self.context_manager.add_message(user_id, message)
                logger.debug(f"Message added to short-term memory for user {user_id}")
            
            # Store in long-term memory (for important messages)
            should_store_longterm = self._should_store_longterm(message)
            if should_store_longterm:
                with profile_code_block("long_term_storage"):
                    await self.longterm_manager.store_memory(message)
                    logger.debug(f"Message stored in long-term memory for user {user_id}")
                    monitor.increment_counter('memory_longterm_stores_total', {'user_id': user_id})
            
            # Update monitoring metrics
            processing_time = (time.time() - start_time) * 1000
            context_size = await self.context_manager.get_context_size(user_id)
            monitor.update_active_memories(user_id, context_size)
            monitor.record_custom_metric('memory_processing_time_ms', processing_time, {'operation': 'store_message'})
            monitor.increment_counter('memory_messages_stored_total', {'user_id': user_id, 'message_type': message_type})
            
            logger.info(f"Stored message for user {user_id} in {processing_time:.2f}ms (context_size: {context_size}, longterm: {should_store_longterm})")
            SentryContextManager.add_breadcrumb(f"Message stored successfully in {processing_time:.2f}ms", "memory", level="info")
            
            return message
            
        except Exception as e:
            monitor.record_memory_operation('store_message', 'error')
            monitor.increment_counter('memory_store_errors_total', {'user_id': user_id})
            logger.error(f"Error storing message: {e}")
            SentryContextManager.add_breadcrumb(f"Message storage failed: {e}", "memory", level="error")
            raise
    
    async def get_context(self, user_id: str) -> List[MemoryMessage]:
        """Get current context window."""
        if not self._initialized:
            await self.initialize()
            
        return await self.context_manager.get_context(user_id)
    
    @track_performance('retrieve_memories')
    async def retrieve_memories(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 5
    ) -> MemoryRetrievalResult:
        """Retrieve relevant memories using semantic search."""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            result = await self.longterm_manager.retrieve_similar_memories(
                query, user_id, limit
            )
            
            # Update access count for retrieved memories
            for message in result.messages:
                await self.forgetting_curve.update_memory_access(message.id, user_id)
            
            processing_time = (time.time() - start_time) * 1000
            logger.debug(f"Retrieved {len(result.messages)} memories for user {user_id} in {processing_time:.2f}ms")
            
            return result
            
        except Exception as e:
            monitor.record_memory_operation('retrieve_memories', 'error')
            logger.error(f"Error retrieving memories: {e}")
            raise
    
    async def cleanup_old_data(self, user_id: str) -> Dict[str, int]:
        """Clean up old data from both memory systems."""
        if not self._initialized:
            await self.initialize()
        
        # Cleanup long-term memories older than 30 days
        deleted_longterm = await self.longterm_manager.cleanup_old_memories(user_id, 30)
        
        return {
            'deleted_longterm_memories': deleted_longterm
        }
    
    async def get_memory_retention_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive memory retention analysis for a user."""
        if not self._initialized:
            await self.initialize()
        
        # Get memory metrics from forgetting curve system
        metrics = await self.forgetting_curve.get_memory_metrics(user_id, limit=500)
        
        if not metrics:
            return {
                'user_id': user_id,
                'total_memories': 0,
                'error': 'No memories found'
            }
        
        # Calculate retention statistics
        active_memories = sum(1 for m in metrics if m.retention_state.value == 'active')
        fading_memories = sum(1 for m in metrics if m.retention_state.value == 'fading')
        forgotten_memories = sum(1 for m in metrics if m.retention_state.value == 'forgotten')
        
        avg_retention = sum(m.current_retention for m in metrics) / len(metrics)
        emotional_memories = sum(1 for m in metrics if m.emotional_modifier > 1.5)
        accessed_memories = sum(1 for m in metrics if m.access_count > 0)
        
        return {
            'user_id': user_id,
            'total_memories': len(metrics),
            'active_memories': active_memories,
            'fading_memories': fading_memories,
            'forgotten_memories': forgotten_memories,
            'average_retention': avg_retention,
            'retention_distribution': {
                'active_percentage': (active_memories / len(metrics)) * 100,
                'fading_percentage': (fading_memories / len(metrics)) * 100,
                'forgotten_percentage': (forgotten_memories / len(metrics)) * 100
            },
            'emotional_impact': {
                'emotional_memory_count': emotional_memories,
                'emotional_memory_percentage': (emotional_memories / len(metrics)) * 100
            },
            'access_patterns': {
                'accessed_memory_count': accessed_memories,
                'accessed_memory_percentage': (accessed_memories / len(metrics)) * 100,
                'avg_access_count': sum(m.access_count for m in metrics) / len(metrics)
            }
        }
    
    async def cleanup_forgotten_memories(
        self, 
        user_id: str, 
        retention_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """Clean up forgotten memories based on retention analysis."""
        if not self._initialized:
            await self.initialize()
        
        return await self.forgetting_curve.cleanup_forgotten_memories(
            user_id=user_id,
            retention_threshold=retention_threshold,
            dry_run=False
        )
    
    def _should_store_longterm(self, message: MemoryMessage) -> bool:
        """Determine if message should be stored in long-term memory."""
        
        # Store if high emotional intensity
        if message.emotional_state:
            intensity = self.emotional_analyzer.get_emotion_intensity(message.emotional_state)
            if intensity > 0.6:  # High emotional importance
                return True
        
        # Store if message is longer (more content)
        if len(message.content) > 50:
            return True
            
        # Store assistant messages (responses)
        if message.message_type == "assistant":
            return True
        
        # Store important keywords (can be customized)
        important_keywords = ['remember', 'important', 'never forget', 'always']
        if any(keyword in message.content.lower() for keyword in important_keywords):
            return True
        
        return False
    
    async def close(self) -> None:
        """Close all connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self.neo4j_driver:
            await self.neo4j_driver.close()


# Factory function
async def create_memory_manager(
    redis_url: str = "redis://localhost:6379",
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password",
    context_window_size: int = 50
) -> MemoryManager:
    """Create and initialize memory manager."""
    manager = MemoryManager(
        redis_url=redis_url,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        context_window_size=context_window_size
    )
    await manager.initialize()
    return manager