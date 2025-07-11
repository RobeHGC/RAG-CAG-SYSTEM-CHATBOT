"""
Spreading Activation Algorithm for Neo4j Memory Graph.
Retrieves emotionally-weighted memories using graph traversal with decay.
"""

import asyncio
import heapq
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from neo4j import AsyncGraphDatabase, AsyncSession
from scipy.spatial.distance import cosine

from src.common.config import settings
from src.common.database import get_neo4j_driver
from src.memoria.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class SpreadingActivation:
    """Implements spreading activation algorithm for memory retrieval."""
    
    def __init__(self):
        self.driver = None
        self.embedding_generator = EmbeddingGenerator()
        
        # Algorithm parameters
        self.decay_factor = 0.6  # 60% reduction per hop
        self.activation_threshold = 0.3  # Minimum activation for inclusion
        self.max_depth = 5  # Maximum traversal depth
        self.emotional_weight_factor = 0.5  # Influence of emotional similarity
        self.temporal_decay_hours = 168  # 1 week temporal decay
        
        # Performance optimization
        self.batch_size = 100  # Process nodes in batches
        self.max_activated_nodes = 500  # Limit total activated nodes
        
    async def initialize(self):
        """Initialize Neo4j connection."""
        if not self.driver:
            self.driver = await get_neo4j_driver()
            logger.info("SpreadingActivation initialized with Neo4j driver")
    
    async def activate_memories(
        self, 
        seed_embedding: np.ndarray,
        user_id: str,
        emotional_state: Dict[str, float],
        max_results: int = 20
    ) -> List[Dict]:
        """
        Activate memories using spreading activation from seed.
        
        Args:
            seed_embedding: Initial embedding vector to start activation
            user_id: User identifier for filtering memories
            emotional_state: Current emotional state for weighting
            max_results: Maximum number of memories to return
            
        Returns:
            List of activated memories sorted by activation strength
        """
        await self.initialize()
        
        start_time = time.time()
        
        # Find initial seed nodes by similarity
        seed_nodes = await self._find_seed_nodes(seed_embedding, user_id)
        
        if not seed_nodes:
            logger.warning(f"No seed nodes found for user {user_id}")
            return []
        
        # Run spreading activation
        activated_nodes = await self._spread_activation(
            seed_nodes,
            user_id,
            emotional_state
        )
        
        # Sort by activation strength and get top results
        sorted_memories = sorted(
            activated_nodes.items(),
            key=lambda x: x[1]['activation'],
            reverse=True
        )[:max_results]
        
        # Enrich memories with full data
        result_memories = await self._enrich_memories(
            [node_id for node_id, _ in sorted_memories],
            {node_id: data for node_id, data in sorted_memories}
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Spreading activation completed in {elapsed_time:.2f}s, "
                   f"returned {len(result_memories)} memories")
        
        return result_memories
    
    async def _find_seed_nodes(
        self, 
        seed_embedding: np.ndarray, 
        user_id: str,
        limit: int = 5
    ) -> List[Tuple[str, float]]:
        """Find initial nodes by embedding similarity."""
        async with self.driver.session() as session:
            query = """
            MATCH (m:Memory {user_id: $user_id})
            WHERE m.embedding IS NOT NULL
            RETURN m.id as node_id, m.embedding as embedding
            LIMIT 1000
            """
            
            result = await session.run(query, user_id=user_id)
            nodes = await result.data()
            
            if not nodes:
                return []
            
            # Calculate similarities
            similarities = []
            for node in nodes:
                node_embedding = np.array(node['embedding'])
                similarity = 1 - cosine(seed_embedding, node_embedding)
                if similarity > 0.5:  # Only consider reasonably similar nodes
                    similarities.append((node['node_id'], similarity))
            
            # Return top similar nodes
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]
    
    async def _spread_activation(
        self,
        seed_nodes: List[Tuple[str, float]],
        user_id: str,
        emotional_state: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        Perform spreading activation from seed nodes.
        
        Returns dict of activated nodes with their activation values.
        """
        # Initialize activation values
        activated = {}
        visited = set()
        
        # Priority queue: (-activation, depth, node_id)
        queue = []
        
        # Add seed nodes to queue
        for node_id, similarity in seed_nodes:
            initial_activation = similarity
            heapq.heappush(queue, (-initial_activation, 0, node_id))
            activated[node_id] = {
                'activation': initial_activation,
                'depth': 0,
                'path': [node_id]
            }
        
        # Process queue
        while queue and len(activated) < self.max_activated_nodes:
            neg_activation, depth, current_id = heapq.heappop(queue)
            activation = -neg_activation
            
            if current_id in visited or depth >= self.max_depth:
                continue
            
            visited.add(current_id)
            
            # Get neighbors
            neighbors = await self._get_neighbors(current_id, user_id)
            
            for neighbor_id, edge_weight, neighbor_data in neighbors:
                if neighbor_id in visited:
                    continue
                
                # Calculate propagated activation
                propagated_activation = activation * self.decay_factor * edge_weight
                
                # Apply emotional weighting
                emotional_weight = self._calculate_emotional_weight(
                    neighbor_data.get('emotional_state', {}),
                    emotional_state
                )
                propagated_activation *= (1 + emotional_weight * self.emotional_weight_factor)
                
                # Apply temporal decay
                temporal_weight = self._calculate_temporal_weight(
                    neighbor_data.get('timestamp')
                )
                propagated_activation *= temporal_weight
                
                # Check threshold
                if propagated_activation < self.activation_threshold:
                    continue
                
                # Update or add to activated nodes
                if neighbor_id not in activated or propagated_activation > activated[neighbor_id]['activation']:
                    activated[neighbor_id] = {
                        'activation': propagated_activation,
                        'depth': depth + 1,
                        'path': activated[current_id]['path'] + [neighbor_id]
                    }
                    heapq.heappush(queue, (-propagated_activation, depth + 1, neighbor_id))
        
        return activated
    
    async def _get_neighbors(
        self, 
        node_id: str, 
        user_id: str
    ) -> List[Tuple[str, float, Dict]]:
        """Get neighboring nodes with edge weights."""
        async with self.driver.session() as session:
            query = """
            MATCH (m:Memory {id: $node_id, user_id: $user_id})
            MATCH (m)-[r]-(n:Memory {user_id: $user_id})
            WHERE type(r) IN ['TEMPORALLY_RELATED', 'SEMANTICALLY_SIMILAR', 'EMOTIONALLY_CONNECTED']
            RETURN n.id as neighbor_id,
                   n.emotional_state as emotional_state,
                   n.timestamp as timestamp,
                   r.weight as edge_weight,
                   type(r) as relationship_type
            """
            
            result = await session.run(query, node_id=node_id, user_id=user_id)
            neighbors = await result.data()
            
            processed_neighbors = []
            for n in neighbors:
                # Default edge weight if not specified
                edge_weight = n.get('edge_weight', 0.5)
                
                # Boost weight based on relationship type
                if n['relationship_type'] == 'EMOTIONALLY_CONNECTED':
                    edge_weight *= 1.3
                elif n['relationship_type'] == 'SEMANTICALLY_SIMILAR':
                    edge_weight *= 1.1
                
                neighbor_data = {
                    'emotional_state': n.get('emotional_state', {}),
                    'timestamp': n.get('timestamp')
                }
                
                processed_neighbors.append((
                    n['neighbor_id'],
                    min(edge_weight, 1.0),  # Cap at 1.0
                    neighbor_data
                ))
            
            return processed_neighbors
    
    def _calculate_emotional_weight(
        self,
        memory_emotions: Dict[str, float],
        current_emotions: Dict[str, float]
    ) -> float:
        """Calculate emotional similarity weight."""
        if not memory_emotions or not current_emotions:
            return 0.0
        
        # Get common emotions
        common_emotions = set(memory_emotions.keys()) & set(current_emotions.keys())
        if not common_emotions:
            return 0.0
        
        # Calculate cosine similarity between emotion vectors
        memory_vec = np.array([memory_emotions.get(e, 0) for e in common_emotions])
        current_vec = np.array([current_emotions.get(e, 0) for e in common_emotions])
        
        if np.all(memory_vec == 0) or np.all(current_vec == 0):
            return 0.0
        
        similarity = 1 - cosine(memory_vec, current_vec)
        return max(0, similarity)
    
    def _calculate_temporal_weight(self, timestamp: Optional[datetime]) -> float:
        """Calculate temporal decay weight."""
        if not timestamp:
            return 0.5  # Default weight for missing timestamps
        
        # Parse timestamp if string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return 0.5
        
        # Calculate hours elapsed
        hours_elapsed = (datetime.now() - timestamp).total_seconds() / 3600
        
        # Exponential decay
        decay_rate = 1 / self.temporal_decay_hours
        weight = np.exp(-decay_rate * hours_elapsed)
        
        return max(0.1, weight)  # Minimum weight of 0.1
    
    async def _enrich_memories(
        self,
        node_ids: List[str],
        activation_data: Dict[str, Dict]
    ) -> List[Dict]:
        """Enrich memory nodes with full data."""
        if not node_ids:
            return []
        
        async with self.driver.session() as session:
            query = """
            MATCH (m:Memory)
            WHERE m.id IN $node_ids
            RETURN m
            """
            
            result = await session.run(query, node_ids=node_ids)
            memories = await result.data()
            
            # Combine memory data with activation data
            enriched_memories = []
            for record in memories:
                memory = dict(record['m'])
                node_id = memory['id']
                
                # Add activation data
                memory['activation_strength'] = activation_data[node_id]['activation']
                memory['activation_depth'] = activation_data[node_id]['depth']
                memory['activation_path'] = activation_data[node_id]['path']
                
                enriched_memories.append(memory)
            
            # Sort by activation strength
            enriched_memories.sort(
                key=lambda x: x['activation_strength'],
                reverse=True
            )
            
            return enriched_memories
    
    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            logger.info("SpreadingActivation Neo4j connection closed")