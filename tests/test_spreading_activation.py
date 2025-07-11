"""
Tests for Spreading Activation Algorithm.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from src.memoria.spreading_activation import SpreadingActivation


class TestSpreadingActivation:
    """Test cases for spreading activation algorithm."""
    
    @pytest.fixture
    def spreading_activation(self):
        """Create SpreadingActivation instance."""
        return SpreadingActivation()
    
    @pytest.fixture
    def mock_embedding(self):
        """Create a mock embedding vector."""
        return np.random.rand(384)  # all-MiniLM-L6-v2 dimension
    
    @pytest.fixture
    def mock_emotional_state(self):
        """Create a mock emotional state."""
        return {
            'joy': 0.7,
            'curiosity': 0.5,
            'surprise': 0.3,
            'sadness': 0.1
        }
    
    @pytest.fixture
    def mock_memories(self):
        """Create mock memory nodes."""
        base_time = datetime.now()
        return [
            {
                'id': 'mem1',
                'user_id': 'user123',
                'content': 'Happy birthday celebration',
                'embedding': np.random.rand(384).tolist(),
                'emotional_state': {'joy': 0.9, 'surprise': 0.6},
                'timestamp': base_time.isoformat()
            },
            {
                'id': 'mem2',
                'user_id': 'user123',
                'content': 'Learning something new',
                'embedding': np.random.rand(384).tolist(),
                'emotional_state': {'curiosity': 0.8, 'joy': 0.4},
                'timestamp': (base_time - timedelta(hours=24)).isoformat()
            },
            {
                'id': 'mem3',
                'user_id': 'user123',
                'content': 'Challenging problem solved',
                'embedding': np.random.rand(384).tolist(),
                'emotional_state': {'satisfaction': 0.7, 'curiosity': 0.5},
                'timestamp': (base_time - timedelta(hours=72)).isoformat()
            }
        ]
    
    @pytest.mark.asyncio
    async def test_initialization(self, spreading_activation):
        """Test SpreadingActivation initialization."""
        assert spreading_activation.decay_factor == 0.6
        assert spreading_activation.activation_threshold == 0.3
        assert spreading_activation.max_depth == 5
        assert spreading_activation.emotional_weight_factor == 0.5
        assert spreading_activation.driver is None
    
    @pytest.mark.asyncio
    async def test_find_seed_nodes(self, spreading_activation, mock_embedding):
        """Test finding seed nodes by similarity."""
        # Mock Neo4j driver and session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {'node_id': 'mem1', 'embedding': np.random.rand(384).tolist()},
            {'node_id': 'mem2', 'embedding': np.random.rand(384).tolist()},
            {'node_id': 'mem3', 'embedding': np.random.rand(384).tolist()}
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        
        mock_driver = AsyncMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        spreading_activation.driver = mock_driver
        
        # Test finding seed nodes
        seed_nodes = await spreading_activation._find_seed_nodes(
            mock_embedding, 'user123', limit=2
        )
        
        assert len(seed_nodes) <= 2
        assert all(isinstance(node, tuple) for node in seed_nodes)
        assert all(len(node) == 2 for node in seed_nodes)
        assert all(0 <= node[1] <= 1 for node in seed_nodes)  # Similarity scores
    
    @pytest.mark.asyncio
    async def test_calculate_emotional_weight(self, spreading_activation):
        """Test emotional weight calculation."""
        memory_emotions = {'joy': 0.8, 'surprise': 0.6, 'curiosity': 0.3}
        current_emotions = {'joy': 0.7, 'surprise': 0.4, 'sadness': 0.2}
        
        weight = spreading_activation._calculate_emotional_weight(
            memory_emotions, current_emotions
        )
        
        assert 0 <= weight <= 1
        assert weight > 0  # Should have some similarity
        
        # Test with no common emotions
        weight_no_common = spreading_activation._calculate_emotional_weight(
            {'anger': 0.5}, {'joy': 0.8}
        )
        assert weight_no_common == 0.0
        
        # Test with empty emotions
        weight_empty = spreading_activation._calculate_emotional_weight({}, {})
        assert weight_empty == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_temporal_weight(self, spreading_activation):
        """Test temporal weight calculation."""
        # Recent timestamp
        recent_time = datetime.now() - timedelta(hours=1)
        recent_weight = spreading_activation._calculate_temporal_weight(recent_time)
        assert 0.9 <= recent_weight <= 1.0
        
        # Week old timestamp
        week_old = datetime.now() - timedelta(days=7)
        week_weight = spreading_activation._calculate_temporal_weight(week_old)
        assert 0.3 <= week_weight <= 0.5
        
        # Very old timestamp
        old_time = datetime.now() - timedelta(days=30)
        old_weight = spreading_activation._calculate_temporal_weight(old_time)
        assert old_weight == 0.1  # Minimum weight
        
        # Test with None
        none_weight = spreading_activation._calculate_temporal_weight(None)
        assert none_weight == 0.5  # Default weight
    
    @pytest.mark.asyncio
    async def test_get_neighbors(self, spreading_activation):
        """Test getting neighbor nodes."""
        # Mock Neo4j session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {
                'neighbor_id': 'mem2',
                'emotional_state': {'joy': 0.5},
                'timestamp': datetime.now().isoformat(),
                'edge_weight': 0.7,
                'relationship_type': 'EMOTIONALLY_CONNECTED'
            },
            {
                'neighbor_id': 'mem3',
                'emotional_state': {'curiosity': 0.8},
                'timestamp': (datetime.now() - timedelta(hours=24)).isoformat(),
                'edge_weight': 0.5,
                'relationship_type': 'SEMANTICALLY_SIMILAR'
            }
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        
        mock_driver = AsyncMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        spreading_activation.driver = mock_driver
        
        neighbors = await spreading_activation._get_neighbors('mem1', 'user123')
        
        assert len(neighbors) == 2
        assert all(len(n) == 3 for n in neighbors)  # (id, weight, data)
        
        # Check weight boosting for emotional connection
        emotional_neighbor = next(n for n in neighbors if n[0] == 'mem2')
        assert emotional_neighbor[1] > 0.7  # Should be boosted
    
    @pytest.mark.asyncio
    async def test_spread_activation(self, spreading_activation, mock_emotional_state):
        """Test the spreading activation process."""
        seed_nodes = [('mem1', 0.9), ('mem2', 0.7)]
        
        # Mock get_neighbors to return a simple graph
        async def mock_get_neighbors(node_id, user_id):
            if node_id == 'mem1':
                return [
                    ('mem2', 0.8, {'emotional_state': {'joy': 0.6}, 'timestamp': datetime.now()}),
                    ('mem3', 0.6, {'emotional_state': {'curiosity': 0.7}, 'timestamp': datetime.now()})
                ]
            elif node_id == 'mem2':
                return [
                    ('mem1', 0.8, {'emotional_state': {'joy': 0.9}, 'timestamp': datetime.now()}),
                    ('mem4', 0.5, {'emotional_state': {'surprise': 0.5}, 'timestamp': datetime.now()})
                ]
            else:
                return []
        
        spreading_activation._get_neighbors = mock_get_neighbors
        
        activated = await spreading_activation._spread_activation(
            seed_nodes, 'user123', mock_emotional_state
        )
        
        # Check that seed nodes are activated
        assert 'mem1' in activated
        assert 'mem2' in activated
        
        # Check activation values
        assert activated['mem1']['activation'] == 0.9
        assert activated['mem1']['depth'] == 0
        
        # Check that activation spreads
        assert len(activated) > 2
        
        # Check decay
        for node_id, data in activated.items():
            if data['depth'] > 0:
                assert data['activation'] < 0.9  # Should be less than seed activation
    
    @pytest.mark.asyncio
    async def test_activate_memories_full_flow(
        self, 
        spreading_activation, 
        mock_embedding, 
        mock_emotional_state
    ):
        """Test the full activation flow."""
        # Mock all dependencies
        spreading_activation._find_seed_nodes = AsyncMock(
            return_value=[('mem1', 0.85), ('mem2', 0.75)]
        )
        
        spreading_activation._spread_activation = AsyncMock(
            return_value={
                'mem1': {'activation': 0.85, 'depth': 0, 'path': ['mem1']},
                'mem2': {'activation': 0.75, 'depth': 0, 'path': ['mem2']},
                'mem3': {'activation': 0.45, 'depth': 1, 'path': ['mem1', 'mem3']},
                'mem4': {'activation': 0.35, 'depth': 2, 'path': ['mem1', 'mem3', 'mem4']}
            }
        )
        
        spreading_activation._enrich_memories = AsyncMock(
            return_value=[
                {
                    'id': 'mem1',
                    'content': 'Memory 1',
                    'activation_strength': 0.85,
                    'activation_depth': 0
                },
                {
                    'id': 'mem2',
                    'content': 'Memory 2',
                    'activation_strength': 0.75,
                    'activation_depth': 0
                }
            ]
        )
        
        spreading_activation.driver = AsyncMock()
        
        # Run activation
        results = await spreading_activation.activate_memories(
            mock_embedding,
            'user123',
            mock_emotional_state,
            max_results=10
        )
        
        assert len(results) == 2
        assert results[0]['activation_strength'] > results[1]['activation_strength']
        
        # Verify methods were called
        spreading_activation._find_seed_nodes.assert_called_once()
        spreading_activation._spread_activation.assert_called_once()
        spreading_activation._enrich_memories.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_limits(self, spreading_activation):
        """Test performance optimization limits."""
        # Test max activated nodes limit
        assert spreading_activation.max_activated_nodes == 500
        
        # Test batch size
        assert spreading_activation.batch_size == 100
        
        # Create large number of mock nodes
        large_seed = [(f'mem{i}', 0.9 - i*0.01) for i in range(10)]
        
        # Mock get_neighbors to create a dense graph
        async def mock_dense_neighbors(node_id, user_id):
            # Each node connects to 20 others
            neighbors = []
            node_num = int(node_id.replace('mem', ''))
            for i in range(20):
                neighbor_id = f'mem{(node_num + i + 1) % 1000}'
                neighbors.append((
                    neighbor_id,
                    0.7,
                    {'emotional_state': {'joy': 0.5}, 'timestamp': datetime.now()}
                ))
            return neighbors
        
        spreading_activation._get_neighbors = mock_dense_neighbors
        
        activated = await spreading_activation._spread_activation(
            large_seed, 'user123', {'joy': 0.5}
        )
        
        # Should respect max activated nodes limit
        assert len(activated) <= spreading_activation.max_activated_nodes
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, spreading_activation, mock_embedding):
        """Test edge cases and error handling."""
        # Test with no seed nodes found
        spreading_activation._find_seed_nodes = AsyncMock(return_value=[])
        spreading_activation.driver = AsyncMock()
        
        results = await spreading_activation.activate_memories(
            mock_embedding, 'user123', {}, max_results=10
        )
        
        assert results == []
        
        # Test with activation below threshold
        seed_nodes = [('mem1', 0.2)]  # Below threshold
        spreading_activation._get_neighbors = AsyncMock(return_value=[])
        
        activated = await spreading_activation._spread_activation(
            seed_nodes, 'user123', {}
        )
        
        # Should still include seed node even if below threshold initially
        assert 'mem1' in activated
    
    @pytest.mark.asyncio
    async def test_close_connection(self, spreading_activation):
        """Test closing Neo4j connection."""
        mock_driver = AsyncMock()
        spreading_activation.driver = mock_driver
        
        await spreading_activation.close()
        
        mock_driver.close.assert_called_once()