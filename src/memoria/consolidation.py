"""
Memory Consolidation Pipeline with Celery.
Transforms episodic memories into semantic knowledge using pattern detection and LLM extraction.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from celery import Task
from celery.exceptions import Retry, SoftTimeLimitExceeded
from neo4j import AsyncGraphDatabase

from src.common.celery_app import celery_app
from src.common.config import settings
from src.common.database import get_neo4j_driver, get_redis_client
from src.memoria.embeddings import EmbeddingGenerator
from src.orquestador.llm_client import LLMClient

logger = logging.getLogger(__name__)


class MemoryConsolidationTask(Task):
    """Base task class for memory consolidation with shared resources."""
    
    _embedding_generator = None
    _llm_client = None
    _neo4j_driver = None
    _redis_client = None
    
    @property
    def embedding_generator(self):
        if self._embedding_generator is None:
            self._embedding_generator = EmbeddingGenerator()
        return self._embedding_generator
    
    @property
    def llm_client(self):
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client
    
    async def get_neo4j_driver(self):
        if self._neo4j_driver is None:
            self._neo4j_driver = await get_neo4j_driver()
        return self._neo4j_driver
    
    async def get_redis_client(self):
        if self._redis_client is None:
            self._redis_client = await get_redis_client()
        return self._redis_client


@celery_app.task(
    base=MemoryConsolidationTask,
    bind=True,
    name='consolidate_user_memories',
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def consolidate_user_memories(self, user_id: str):
    """
    Main consolidation task for a user's memories.
    
    Args:
        user_id: User identifier
    
    Returns:
        Dict with consolidation results
    """
    try:
        logger.info(f"Starting memory consolidation for user {user_id}")
        
        # Run async consolidation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            _async_consolidate_memories(self, user_id)
        )
        
        loop.close()
        
        logger.info(f"Completed consolidation for user {user_id}: {result}")
        return result
        
    except SoftTimeLimitExceeded:
        logger.error(f"Consolidation timeout for user {user_id}")
        raise
    except Exception as exc:
        logger.error(f"Consolidation failed for user {user_id}: {exc}")
        raise self.retry(exc=exc)


async def _async_consolidate_memories(task: MemoryConsolidationTask, user_id: str) -> Dict:
    """
    Async implementation of memory consolidation.
    
    Returns:
        Dict with:
        - patterns_found: Number of patterns detected
        - semantic_memories_created: Number of new semantic memories
        - episodic_memories_processed: Number of episodic memories analyzed
        - errors: List of any errors encountered
    """
    driver = await task.get_neo4j_driver()
    redis_client = await task.get_redis_client()
    
    result = {
        'patterns_found': 0,
        'semantic_memories_created': 0,
        'episodic_memories_processed': 0,
        'errors': []
    }
    
    try:
        # 1. Find consolidation candidates
        candidates = await _find_consolidation_candidates(driver, user_id)
        result['episodic_memories_processed'] = len(candidates)
        
        if not candidates:
            logger.info(f"No consolidation candidates found for user {user_id}")
            return result
        
        # 2. Detect patterns with repetition threshold
        patterns = await _detect_patterns(candidates, threshold=3)
        result['patterns_found'] = len(patterns)
        
        if not patterns:
            logger.info(f"No patterns above threshold for user {user_id}")
            return result
        
        # 3. Extract semantic knowledge using LLM
        for pattern in patterns:
            try:
                semantic_memory = await _extract_semantic_knowledge(
                    task.llm_client,
                    pattern,
                    task.embedding_generator
                )
                
                if semantic_memory:
                    # 4. Create semantic memory node
                    created = await _create_semantic_memory(
                        driver,
                        user_id,
                        semantic_memory,
                        pattern['episode_ids']
                    )
                    
                    if created:
                        result['semantic_memories_created'] += 1
                        
                        # 5. Update consolidation tracking
                        await _update_consolidation_tracking(
                            redis_client,
                            user_id,
                            pattern['episode_ids']
                        )
                        
            except Exception as e:
                logger.error(f"Error processing pattern: {e}")
                result['errors'].append(str(e))
                
        # 6. Apply forgetting curves to old episodic memories
        await _apply_forgetting_curves(driver, user_id)
        
    except Exception as e:
        logger.error(f"Consolidation error for user {user_id}: {e}")
        result['errors'].append(str(e))
        raise
    
    return result


async def _find_consolidation_candidates(driver, user_id: str) -> List[Dict]:
    """Find episodic memories eligible for consolidation."""
    async with driver.session() as session:
        # Get recent episodic memories not yet consolidated
        query = """
        MATCH (m:Memory {user_id: $user_id, type: 'episodic'})
        WHERE m.consolidated IS NULL OR m.consolidated = false
        AND m.timestamp > datetime() - duration('P7D')  // Last 7 days
        RETURN m
        ORDER BY m.timestamp DESC
        LIMIT 1000
        """
        
        result = await session.run(query, user_id=user_id)
        memories = []
        
        async for record in result:
            memory = dict(record['m'])
            memories.append(memory)
        
        return memories


async def _detect_patterns(memories: List[Dict], threshold: int = 3) -> List[Dict]:
    """
    Detect repeated patterns in episodic memories.
    
    Args:
        memories: List of episodic memories
        threshold: Minimum repetitions for pattern detection
        
    Returns:
        List of detected patterns with episode IDs
    """
    patterns = []
    
    # Group memories by emotional patterns
    emotional_groups = defaultdict(list)
    for memory in memories:
        if memory.get('emotional_state'):
            # Create emotional signature
            emotions = memory['emotional_state']
            dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0] if emotions else 'neutral'
            emotional_groups[dominant_emotion].append(memory)
    
    # Group by semantic similarity using embeddings
    semantic_groups = []
    processed = set()
    
    for i, memory in enumerate(memories):
        if memory['id'] in processed:
            continue
            
        if not memory.get('embedding'):
            continue
            
        group = [memory]
        processed.add(memory['id'])
        embedding1 = np.array(memory['embedding'])
        
        # Find similar memories
        for j, other in enumerate(memories[i+1:], i+1):
            if other['id'] in processed or not other.get('embedding'):
                continue
                
            embedding2 = np.array(other['embedding'])
            similarity = 1 - np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            if similarity > 0.7:  # High similarity threshold
                group.append(other)
                processed.add(other['id'])
        
        if len(group) >= threshold:
            semantic_groups.append(group)
    
    # Combine emotional and semantic patterns
    for emotion, emotion_memories in emotional_groups.items():
        if len(emotion_memories) >= threshold:
            patterns.append({
                'type': 'emotional',
                'emotion': emotion,
                'memories': emotion_memories,
                'episode_ids': [m['id'] for m in emotion_memories],
                'count': len(emotion_memories)
            })
    
    for group in semantic_groups:
        # Extract common themes
        contents = [m.get('content', '') for m in group]
        patterns.append({
            'type': 'semantic',
            'memories': group,
            'episode_ids': [m['id'] for m in group],
            'contents': contents,
            'count': len(group)
        })
    
    return patterns


async def _extract_semantic_knowledge(
    llm_client: LLMClient,
    pattern: Dict,
    embedding_generator: EmbeddingGenerator
) -> Optional[Dict]:
    """
    Extract semantic knowledge from pattern using LLM.
    
    Returns:
        Dict with semantic memory data or None
    """
    try:
        # Prepare context for LLM
        if pattern['type'] == 'emotional':
            prompt = f"""
            Analyze these {pattern['count']} memories with dominant emotion '{pattern['emotion']}':
            
            {json.dumps([m.get('content', '') for m in pattern['memories'][:10]], indent=2)}
            
            Extract the semantic pattern or life lesson. What does this pattern reveal about the person's 
            emotional responses, values, or behavioral patterns? Provide a concise semantic memory.
            
            Response format:
            {{
                "title": "Brief title for the semantic memory",
                "content": "The extracted semantic knowledge or pattern",
                "category": "behavioral_pattern|life_lesson|preference|skill|relationship",
                "confidence": 0.0-1.0
            }}
            """
        else:  # semantic type
            prompt = f"""
            Analyze these {pattern['count']} semantically similar memories:
            
            {json.dumps(pattern['contents'][:10], indent=2)}
            
            Extract the common theme, pattern, or knowledge. What general principle, preference, 
            or understanding emerges from these repeated experiences?
            
            Response format:
            {{
                "title": "Brief title for the semantic memory",
                "content": "The extracted semantic knowledge or pattern",
                "category": "behavioral_pattern|life_lesson|preference|skill|relationship",
                "confidence": 0.0-1.0
            }}
            """
        
        # Get LLM response
        response = await llm_client.generate_response(
            prompt,
            temperature=0.3,  # Low temperature for consistency
            response_format="json"
        )
        
        semantic_data = json.loads(response)
        
        # Validate response
        if not all(k in semantic_data for k in ['title', 'content', 'category', 'confidence']):
            logger.warning("Invalid semantic extraction response")
            return None
        
        # Generate embedding for semantic memory
        embedding = await embedding_generator.generate_embedding(
            f"{semantic_data['title']}: {semantic_data['content']}"
        )
        
        semantic_data['embedding'] = embedding.tolist()
        semantic_data['created_at'] = datetime.now().isoformat()
        semantic_data['pattern_type'] = pattern['type']
        semantic_data['source_count'] = pattern['count']
        
        return semantic_data
        
    except Exception as e:
        logger.error(f"Error extracting semantic knowledge: {e}")
        return None


async def _create_semantic_memory(
    driver,
    user_id: str,
    semantic_memory: Dict,
    episode_ids: List[str]
) -> bool:
    """Create semantic memory node and link to source episodes."""
    async with driver.session() as session:
        try:
            # Create semantic memory node
            create_query = """
            CREATE (s:Memory:Semantic {
                id: randomUUID(),
                user_id: $user_id,
                type: 'semantic',
                title: $title,
                content: $content,
                category: $category,
                confidence: $confidence,
                embedding: $embedding,
                created_at: datetime($created_at),
                pattern_type: $pattern_type,
                source_count: $source_count
            })
            RETURN s.id as semantic_id
            """
            
            result = await session.run(
                create_query,
                user_id=user_id,
                **semantic_memory
            )
            
            record = await result.single()
            if not record:
                return False
                
            semantic_id = record['semantic_id']
            
            # Link to source episodes
            link_query = """
            MATCH (s:Memory {id: $semantic_id})
            MATCH (e:Memory {id: $episode_id})
            CREATE (e)-[:CONSOLIDATED_TO {
                timestamp: datetime(),
                confidence: $confidence
            }]->(s)
            """
            
            for episode_id in episode_ids:
                await session.run(
                    link_query,
                    semantic_id=semantic_id,
                    episode_id=episode_id,
                    confidence=semantic_memory['confidence']
                )
            
            # Mark episodes as consolidated
            mark_query = """
            MATCH (m:Memory)
            WHERE m.id IN $episode_ids
            SET m.consolidated = true,
                m.consolidated_at = datetime()
            """
            
            await session.run(mark_query, episode_ids=episode_ids)
            
            logger.info(f"Created semantic memory {semantic_id} from {len(episode_ids)} episodes")
            return True
            
        except Exception as e:
            logger.error(f"Error creating semantic memory: {e}")
            return False


async def _update_consolidation_tracking(
    redis_client,
    user_id: str,
    episode_ids: List[str]
):
    """Update Redis tracking for consolidation progress."""
    key = f"consolidation:{user_id}:progress"
    
    # Track consolidated episodes
    data = {
        'last_consolidation': datetime.now().isoformat(),
        'episodes_consolidated': len(episode_ids),
        'episode_ids': episode_ids
    }
    
    await redis_client.setex(
        key,
        86400,  # 24 hour TTL
        json.dumps(data)
    )


async def _apply_forgetting_curves(driver, user_id: str):
    """Apply forgetting curves to reduce old episodic memory weights."""
    async with driver.session() as session:
        # Exponential decay for memories older than 30 days
        query = """
        MATCH (m:Memory {user_id: $user_id, type: 'episodic'})
        WHERE m.timestamp < datetime() - duration('P30D')
        AND (m.retention_weight IS NULL OR m.retention_weight > 0.1)
        SET m.retention_weight = 
            CASE 
                WHEN m.consolidated = true THEN 0.5
                ELSE 0.1
            END
        RETURN count(m) as updated_count
        """
        
        result = await session.run(query, user_id=user_id)
        record = await result.single()
        
        if record and record['updated_count'] > 0:
            logger.info(f"Applied forgetting curves to {record['updated_count']} memories")


# Scheduled task for periodic consolidation
@celery_app.task(name='schedule_consolidations')
def schedule_consolidations():
    """Schedule consolidation tasks for all active users."""
    try:
        # In production, this would query active users
        # For now, we'll use a placeholder
        active_users = ['user123', 'user456']  # TODO: Get from database
        
        for user_id in active_users:
            consolidate_user_memories.delay(user_id)
            
        logger.info(f"Scheduled consolidation for {len(active_users)} users")
        return {'users_scheduled': len(active_users)}
        
    except Exception as e:
        logger.error(f"Error scheduling consolidations: {e}")
        raise


# Monitoring task
@celery_app.task(name='check_consolidation_health')
def check_consolidation_health():
    """Health check for consolidation pipeline."""
    try:
        # Check Redis connection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _check():
            redis = await get_redis_client()
            await redis.ping()
            
            driver = await get_neo4j_driver()
            async with driver.session() as session:
                result = await session.run("RETURN 1")
                await result.single()
                
            return True
        
        healthy = loop.run_until_complete(_check())
        loop.close()
        
        return {
            'status': 'healthy' if healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }