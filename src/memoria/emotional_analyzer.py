"""
VAD (Valence-Arousal-Dominance) Emotional Analysis System for Nadia AI Companion.

This module implements the core emotional analysis using RoBERTa emotion classification
and VAD mapping for emotionally-weighted memory operations.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)


@dataclass
class EmotionalState:
    """Represents the emotional state with VAD values and confidence scores."""
    
    valence: float  # Positive/negative sentiment (-1 to 1)
    arousal: float  # Emotional intensity (0 to 1)
    dominance: float  # Control/submission (-1 to 1)
    confidence: float  # Overall confidence score (0 to 1)
    primary_emotion: str  # Detected primary emotion
    emotion_scores: Dict[str, float] = field(default_factory=dict)  # All emotion scores
    processing_time: float = 0.0  # Time taken for analysis (ms)


class VADEmotionalAnalyzer:
    """
    VAD Emotional Analysis System using RoBERTa emotion classification.
    
    Maps detected emotions to Valence-Arousal-Dominance space for memory weighting.
    """
    
    # Emotion to VAD mapping based on psychological research
    VAD_MAPPING = {
        'joy': {'valence': 0.76, 'arousal': 0.48, 'dominance': 0.35},
        'sadness': {'valence': -0.63, 'arousal': 0.27, 'dominance': -0.33},
        'anger': {'valence': -0.43, 'arousal': 0.67, 'dominance': 0.65},
        'fear': {'valence': -0.64, 'arousal': 0.60, 'dominance': -0.43},
        'surprise': {'valence': 0.40, 'arousal': 0.67, 'dominance': -0.13},
        'disgust': {'valence': -0.60, 'arousal': 0.35, 'dominance': 0.11},
        'neutral': {'valence': 0.0, 'arousal': 0.0, 'dominance': 0.0}
    }
    
    def __init__(self, model_name: str = "j-hartmann/emotion-english-distilroberta-base"):
        """
        Initialize the VAD emotional analyzer.
        
        Args:
            model_name: HuggingFace model name for emotion classification
        """
        self.model_name = model_name
        self.pipeline = None
        self.tokenizer = None
        self.model = None
        self._is_initialized = False
        
    def initialize(self) -> None:
        """Initialize the emotion classification pipeline."""
        if self._is_initialized:
            return
            
        try:
            logger.info(f"Initializing emotion analysis model: {self.model_name}")
            
            # Initialize tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            # Create classification pipeline
            self.pipeline = pipeline(
                "text-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                top_k=None,
                device=0 if torch.cuda.is_available() else -1
            )
            
            self._is_initialized = True
            logger.info("Emotion analysis model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize emotion analysis model: {e}")
            raise
    
    def analyze_emotion(self, text: str) -> EmotionalState:
        """
        Analyze the emotional content of text and return VAD values.
        
        Args:
            text: Input text to analyze
            
        Returns:
            EmotionalState with VAD values and confidence scores
        """
        if not self._is_initialized:
            self.initialize()
            
        start_time = time.time()
        
        try:
            # Get emotion predictions
            emotion_results = self.pipeline(text)
            
            # Process results - handle both single and batch results
            if isinstance(emotion_results, list) and len(emotion_results) > 0:
                if isinstance(emotion_results[0], list):
                    # Multiple texts, take first
                    emotion_data = emotion_results[0]
                else:
                    # Single text result
                    emotion_data = emotion_results
            else:
                emotion_data = emotion_results
            
            emotion_scores = {result['label'].lower(): result['score'] for result in emotion_data}
            
            # Find primary emotion
            primary_emotion = max(emotion_scores, key=emotion_scores.get)
            primary_confidence = emotion_scores[primary_emotion]
            
            # Calculate VAD values
            vad_values = self._calculate_vad(emotion_scores)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(emotion_scores, primary_confidence)
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return EmotionalState(
                valence=vad_values['valence'],
                arousal=vad_values['arousal'],
                dominance=vad_values['dominance'],
                confidence=confidence,
                primary_emotion=primary_emotion,
                emotion_scores=emotion_scores,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error analyzing emotion: {e}")
            # Return neutral state on error
            return EmotionalState(
                valence=0.0,
                arousal=0.0,
                dominance=0.0,
                confidence=0.0,
                primary_emotion='neutral',
                emotion_scores={'neutral': 1.0},
                processing_time=(time.time() - start_time) * 1000
            )
    
    def _calculate_vad(self, emotion_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate VAD values from emotion scores using weighted averaging.
        
        Args:
            emotion_scores: Dictionary of emotion labels and their scores
            
        Returns:
            Dictionary with valence, arousal, and dominance values
        """
        valence = 0.0
        arousal = 0.0
        dominance = 0.0
        total_weight = 0.0
        
        for emotion, score in emotion_scores.items():
            if emotion in self.VAD_MAPPING:
                vad = self.VAD_MAPPING[emotion]
                valence += vad['valence'] * score
                arousal += vad['arousal'] * score
                dominance += vad['dominance'] * score
                total_weight += score
        
        # Normalize by total weight
        if total_weight > 0:
            valence /= total_weight
            arousal /= total_weight
            dominance /= total_weight
        
        return {
            'valence': np.clip(valence, -1.0, 1.0),
            'arousal': np.clip(arousal, 0.0, 1.0),
            'dominance': np.clip(dominance, -1.0, 1.0)
        }
    
    def _calculate_confidence(self, emotion_scores: Dict[str, float], primary_confidence: float) -> float:
        """
        Calculate overall confidence score based on emotion prediction scores.
        
        Args:
            emotion_scores: Dictionary of emotion labels and their scores
            primary_confidence: Confidence score of the primary emotion
            
        Returns:
            Overall confidence score (0 to 1)
        """
        # Use entropy-based confidence calculation
        scores = list(emotion_scores.values())
        entropy = -sum(s * np.log(s + 1e-10) for s in scores)
        max_entropy = np.log(len(scores))
        
        # Normalize entropy to 0-1 range (lower entropy = higher confidence)
        normalized_entropy = entropy / max_entropy
        entropy_confidence = 1.0 - normalized_entropy
        
        # Combine with primary emotion confidence
        confidence = (primary_confidence * 0.7) + (entropy_confidence * 0.3)
        
        return np.clip(confidence, 0.0, 1.0)
    
    def get_emotion_intensity(self, emotional_state: EmotionalState) -> float:
        """
        Calculate emotional intensity for memory weighting.
        
        Args:
            emotional_state: The emotional state to analyze
            
        Returns:
            Emotional intensity value (0 to 1)
        """
        # Intensity based on arousal and absolute valence
        valence_intensity = abs(emotional_state.valence)
        arousal_intensity = emotional_state.arousal
        
        # Weighted combination
        intensity = (valence_intensity * 0.4) + (arousal_intensity * 0.6)
        
        # Scale by confidence
        intensity *= emotional_state.confidence
        
        return np.clip(intensity, 0.0, 1.0)
    
    def is_positive_emotion(self, emotional_state: EmotionalState) -> bool:
        """Check if the emotional state is positive."""
        return emotional_state.valence > 0.1
    
    def is_negative_emotion(self, emotional_state: EmotionalState) -> bool:
        """Check if the emotional state is negative."""
        return emotional_state.valence < -0.1
    
    def is_high_arousal(self, emotional_state: EmotionalState) -> bool:
        """Check if the emotional state has high arousal."""
        return emotional_state.arousal > 0.6
    
    def is_dominant_emotion(self, emotional_state: EmotionalState) -> bool:
        """Check if the emotional state is dominant."""
        return emotional_state.dominance > 0.1


def create_emotional_analyzer() -> VADEmotionalAnalyzer:
    """Factory function to create and initialize the emotional analyzer."""
    analyzer = VADEmotionalAnalyzer()
    analyzer.initialize()
    return analyzer


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create analyzer
    analyzer = create_emotional_analyzer()
    
    # Test messages
    test_messages = [
        "I'm so happy about this amazing news!",
        "I feel really sad and disappointed.",
        "This makes me so angry!",
        "I'm scared about what might happen.",
        "What a surprising turn of events!",
        "This is disgusting and terrible.",
        "The weather is nice today."
    ]
    
    print("VAD Emotional Analysis Test Results:")
    print("=" * 50)
    
    for message in test_messages:
        result = analyzer.analyze_emotion(message)
        print(f"\nText: {message}")
        print(f"Primary Emotion: {result.primary_emotion}")
        print(f"VAD: V={result.valence:.3f}, A={result.arousal:.3f}, D={result.dominance:.3f}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Intensity: {analyzer.get_emotion_intensity(result):.3f}")
        print(f"Processing Time: {result.processing_time:.1f}ms")