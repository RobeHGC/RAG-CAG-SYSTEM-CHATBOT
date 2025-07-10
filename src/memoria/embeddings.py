"""
Embedding Management System for Nadia AI Companion.

This module handles text embeddings using sentence-transformers for semantic similarity
and memory retrieval operations.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Manages text embeddings using sentence-transformers.
    
    Optimized for fast embedding generation (<100ms) using the all-MiniLM-L6-v2 model.
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the embedding manager.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._initialized = False
        self._embedding_cache = {}  # Simple LRU cache for embeddings
        self._cache_max_size = 1000
        
    async def initialize(self) -> None:
        """Initialize the sentence transformer model."""
        if self._initialized:
            return
            
        try:
            logger.info(f"Initializing embedding model: {self.model_name}")
            start_time = time.time()
            
            # Load model in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                lambda: SentenceTransformer(self.model_name, device=self.device)
            )
            
            # Warm up the model with a test embedding
            await self._warmup_model()
            
            self._initialized = True
            init_time = (time.time() - start_time) * 1000
            logger.info(f"Embedding model initialized in {init_time:.1f}ms on device: {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    async def _warmup_model(self) -> None:
        """Warm up the model with a test embedding."""
        try:
            test_text = "This is a test message for model warmup."
            _ = await self.get_embedding(test_text)
            logger.info("Model warmup completed successfully")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    
    async def get_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            use_cache: Whether to use/store in cache
            
        Returns:
            List of embedding values
        """
        if not self._initialized:
            await self.initialize()
        
        # Check cache first
        if use_cache and text in self._embedding_cache:
            return self._embedding_cache[text]
        
        start_time = time.time()
        
        try:
            # Generate embedding in thread to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode([text], convert_to_numpy=True)[0]
            )
            
            # Convert to list for JSON serialization
            embedding_list = embedding.tolist()
            
            # Cache the result
            if use_cache:
                self._cache_embedding(text, embedding_list)
            
            generation_time = (time.time() - start_time) * 1000
            
            if generation_time > 100:  # Log if slower than target
                logger.warning(f"Embedding generation took {generation_time:.1f}ms (target: <100ms)")
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 384  # all-MiniLM-L6-v2 has 384 dimensions
    
    async def get_embeddings_batch(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of input texts
            use_cache: Whether to use/store in cache
            
        Returns:
            List of embedding lists
        """
        if not self._initialized:
            await self.initialize()
        
        if not texts:
            return []
        
        # Check which texts need embeddings
        cached_embeddings = {}
        texts_to_embed = []
        
        if use_cache:
            for text in texts:
                if text in self._embedding_cache:
                    cached_embeddings[text] = self._embedding_cache[text]
                else:
                    texts_to_embed.append(text)
        else:
            texts_to_embed = texts
        
        start_time = time.time()
        new_embeddings = {}
        
        if texts_to_embed:
            try:
                # Generate embeddings in batch
                loop = asyncio.get_event_loop()
                embeddings_array = await loop.run_in_executor(
                    None,
                    lambda: self.model.encode(texts_to_embed, convert_to_numpy=True)
                )
                
                # Convert to lists and cache
                for i, text in enumerate(texts_to_embed):
                    embedding_list = embeddings_array[i].tolist()
                    new_embeddings[text] = embedding_list
                    
                    if use_cache:
                        self._cache_embedding(text, embedding_list)
                        
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                # Return zero vectors as fallback
                for text in texts_to_embed:
                    new_embeddings[text] = [0.0] * 384
        
        # Combine cached and new embeddings in original order
        result = []
        for text in texts:
            if text in cached_embeddings:
                result.append(cached_embeddings[text])
            else:
                result.append(new_embeddings[text])
        
        generation_time = (time.time() - start_time) * 1000
        avg_time_per_text = generation_time / len(texts_to_embed) if texts_to_embed else 0
        
        logger.info(f"Generated {len(texts_to_embed)} embeddings in {generation_time:.1f}ms "
                   f"(avg: {avg_time_per_text:.1f}ms per text)")
        
        return result
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Clamp to [0, 1] range
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def find_most_similar(
        self, 
        query_embedding: List[float], 
        candidate_embeddings: List[List[float]], 
        threshold: float = 0.7
    ) -> List[tuple]:
        """
        Find most similar embeddings to query.
        
        Args:
            query_embedding: Query embedding to match against
            candidate_embeddings: List of candidate embeddings
            threshold: Minimum similarity threshold
            
        Returns:
            List of (index, similarity_score) tuples sorted by similarity
        """
        similarities = []
        
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.calculate_similarity(query_embedding, candidate)
            if similarity >= threshold:
                similarities.append((i, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities
    
    def _cache_embedding(self, text: str, embedding: List[float]) -> None:
        """Cache an embedding with LRU eviction."""
        # Simple LRU: remove oldest if cache is full
        if len(self._embedding_cache) >= self._cache_max_size:
            # Remove oldest entry (first in dict)
            oldest_key = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest_key]
        
        self._embedding_cache[text] = embedding
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cache_size': len(self._embedding_cache),
            'cache_max_size': self._cache_max_size,
            'cache_usage_percent': (len(self._embedding_cache) / self._cache_max_size) * 100
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self._initialized:
            return {'status': 'not_initialized'}
        
        return {
            'model_name': self.model_name,
            'device': self.device,
            'embedding_dimension': 384,  # all-MiniLM-L6-v2 dimension
            'max_sequence_length': 256,  # all-MiniLM-L6-v2 max length
            'initialized': self._initialized
        }


# Utility functions for semantic caching and retrieval
class SemanticCache:
    """
    Implements semantic caching using embeddings for query-response pairs.
    """
    
    def __init__(self, embedding_manager: EmbeddingManager, similarity_threshold: float = 0.85):
        """
        Initialize semantic cache.
        
        Args:
            embedding_manager: Embedding manager instance
            similarity_threshold: Minimum similarity for cache hit
        """
        self.embedding_manager = embedding_manager
        self.similarity_threshold = similarity_threshold
        self.cache_entries = []  # List of (query, embedding, response) tuples
        self.max_cache_size = 500
    
    async def get_cached_response(self, query: str) -> Optional[str]:
        """
        Check if query has a cached response.
        
        Args:
            query: Input query to check
            
        Returns:
            Cached response if found, None otherwise
        """
        if not self.cache_entries:
            return None
        
        # Get query embedding
        query_embedding = await self.embedding_manager.get_embedding(query)
        
        # Find most similar cached query
        best_similarity = 0.0
        best_response = None
        
        for cached_query, cached_embedding, cached_response in self.cache_entries:
            similarity = self.embedding_manager.calculate_similarity(
                query_embedding, cached_embedding
            )
            
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_response = cached_response
        
        if best_response:
            logger.info(f"Cache hit with similarity: {best_similarity:.3f}")
            return best_response
        
        return None
    
    async def cache_response(self, query: str, response: str) -> None:
        """
        Cache a query-response pair.
        
        Args:
            query: Input query
            response: Generated response
        """
        # Get query embedding
        query_embedding = await self.embedding_manager.get_embedding(query)
        
        # Add to cache
        self.cache_entries.append((query, query_embedding, response))
        
        # Maintain cache size
        if len(self.cache_entries) > self.max_cache_size:
            self.cache_entries.pop(0)  # Remove oldest entry
    
    def clear_cache(self) -> None:
        """Clear the semantic cache."""
        self.cache_entries.clear()
        logger.info("Semantic cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cache_size': len(self.cache_entries),
            'max_cache_size': self.max_cache_size,
            'similarity_threshold': self.similarity_threshold
        }


# Factory function
async def create_embedding_manager(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> EmbeddingManager:
    """Create and initialize embedding manager."""
    manager = EmbeddingManager(model_name)
    await manager.initialize()
    return manager