# MARKER_102.4_START
import logging
from typing import Optional, Dict, Any
import mlx_whisper
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

class WhisperSTT:
    """Speech-to-Text engine using MLX Whisper for Apple Silicon optimization."""
    
    def __init__(self, model_name: str = "base", language: Optional[str] = None):
        """
        Initialize Whisper STT engine.
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            language: Target language code (e.g., 'en', 'es', 'fr')
        """
        self.model_name = model_name
        self.language = language
        self.model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the Whisper model."""
        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = mlx_whisper.load_model(self.model_name)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            **kwargs: Additional transcription options
        
        Returns:
            Dictionary containing transcription results
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            audio_file = Path(audio_path)
            if not audio_file.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Set transcription options
            options = {
                "language": self.language,
                "task": "transcribe",
                **kwargs
            }
            
            logger.info(f"Transcribing audio: {audio_path}")
            result = mlx_whisper.transcribe(
                str(audio_file),
                model=self.model,
                **options
            )
            
            return {
                "text": result["text"].strip(),
                "segments": result.get("segments", []),
                "language": result.get("language", self.language),
                "confidence": self._calculate_confidence(result)
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int = 16000, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio data directly.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of audio data
            **kwargs: Additional transcription options
        
        Returns:
            Dictionary containing transcription results
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        try:
            # Set transcription options
            options = {
                "language": self.language,
                "task": "transcribe",
                **kwargs
            }
            
            logger.info("Transcribing audio data")
            result = mlx_whisper.transcribe(
                audio_data,
                model=self.model,
                **options
            )
            
            return {
                "text": result["text"].strip(),
                "segments": result.get("segments", []),
                "language": result.get("language", self.language),
                "confidence": self._calculate_confidence(result)
            }
            
        except Exception as e:
            logger.error(f"Audio data transcription failed: {e}")
            raise
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """
        Calculate average confidence score from segments.
        
        Args:
            result: Whisper transcription result
        
        Returns:
            Average confidence score (0.0 to 1.0)
        """
        segments = result.get("segments", [])
        if not segments:
            return 0.0
        
        # Calculate average confidence from segments
        total_confidence = sum(
            segment.get("avg_logprob", 0.0) for segment in segments
        )
        avg_confidence = total_confidence / len(segments)
        
        # Convert log probability to confidence score (approximate)
        confidence = max(0.0, min(1.0, (avg_confidence + 1.0)))
        return confidence
    
    def set_language(self, language: str) -> None:
        """
        Set the target language for transcription.
        
        Args:
            language: Language code (e.g., 'en', 'es', 'fr')
        """
        self.language = language
        logger.info(f"Language set to: {language}")
    
    def get_supported_languages(self) -> list:
        """
        Get list of supported languages.
        
        Returns:
            List of supported language codes
        """
        # Common Whisper supported languages
        return [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
            "ar", "tr", "pl", "nl", "sv", "da", "no", "fi", "hu", "cs",
            "sk", "sl", "hr", "bg", "ro", "uk", "he", "hi", "th", "vi"
        ]
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.model:
            logger.info("Cleaning up Whisper model")
            self.model = None
# MARKER_102.4_END