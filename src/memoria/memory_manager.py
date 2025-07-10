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
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import redis.asyncio as redis
from neo4j import AsyncGraphDatabase
import numpy as np

from .embeddings import EmbeddingManager
from .emotional_analyzer import VADEmotionalAnalyzer, EmotionalState

logger = logging.getLogger(__name__)


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
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all memory components."""
        if self._initialized:
            return
            
        try:
            # Initialize Redis
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # Initialize Neo4j
            self.neo4j_driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Initialize managers
            self.context_manager = ContextWindowManager(
                self.redis_client, 
                self.context_window_size
            )
            self.longterm_manager = LongTermMemoryManager(
                self.neo4j_driver, 
                self.embedding_manager
            )
            
            # Initialize ML components
            await self.embedding_manager.initialize()
            self.emotional_analyzer.initialize()
            
            self._initialized = True
            logger.info("Memory management system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory system: {e}")
            raise
    
    async def store_message(
        self, 
        user_id: str, 
        content: str, 
        message_type: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryMessage:
        """Store a message in both short and long-term memory."""
        
        if not self._initialized:
            await self.initialize()
        
        # Analyze emotions
        emotional_state = self.emotional_analyzer.analyze_emotion(content)
        
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
        await self.context_manager.add_message(user_id, message)
        
        # Store in long-term memory (for important messages)
        if self._should_store_longterm(message):
            await self.longterm_manager.store_memory(message)
        
        return message
    
    async def get_context(self, user_id: str) -> List[MemoryMessage]:
        """Get current context window."""
        if not self._initialized:
            await self.initialize()
            
        return await self.context_manager.get_context(user_id)
    
    async def retrieve_memories(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 5
    ) -> MemoryRetrievalResult:
        """Retrieve relevant memories using semantic search."""
        if not self._initialized:
            await self.initialize()
            
        return await self.longterm_manager.retrieve_similar_memories(
            query, user_id, limit
        )
    
    async def cleanup_old_data(self, user_id: str) -> Dict[str, int]:
        """Clean up old data from both memory systems."""
        if not self._initialized:
            await self.initialize()
        
        # Cleanup long-term memories older than 30 days
        deleted_longterm = await self.longterm_manager.cleanup_old_memories(user_id, 30)
        
        return {
            'deleted_longterm_memories': deleted_longterm
        }
    
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