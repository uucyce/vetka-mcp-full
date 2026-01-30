# MARKER_102.5_START
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech

logger = logging.getLogger(__name__)

@dataclass
class VoiceConfig:
    """Configuration for voice pipeline"""
    stt_model: str = "whisper-base"
    tts_voice: str = "default"
    silence_threshold: float = 0.5
    max_listen_duration: int = 30

class VoicePipeline:
    """Main voice processing pipeline"""
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.stt = SpeechToText(model=self.config.stt_model)
        self.tts = TextToSpeech(voice=self.config.tts_voice)
        self._is_listening = False
        
    async def listen(self, timeout: Optional[int] = None) -> Optional[str]:
        """
        Listen for audio input and convert to text
        
        Args:
            timeout: Maximum time to listen in seconds
            
        Returns:
            Transcribed text or None if no speech detected
        """
        try:
            self._is_listening = True
            timeout = timeout or self.config.max_listen_duration
            
            logger.info("Starting to listen for audio input")
            audio_data = await self.stt.capture_audio(
                timeout=timeout,
                silence_threshold=self.config.silence_threshold
            )
            
            if audio_data is None:
                logger.warning("No audio captured")
                return None
                
            text = await self.stt.transcribe(audio_data)
            logger.info(f"Transcribed: {text}")
            return text
            
        except Exception as e:
            logger.error(f"Error during listening: {e}")
            return None
        finally:
            self._is_listening = False
    
    async def speak(self, text: str) -> bool:
        """
        Convert text to speech and play audio
        
        Args:
            text: Text to convert to speech
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for speech")
                return False
                
            logger.info(f"Speaking: {text}")
            audio_data = await self.tts.synthesize(text)
            
            if audio_data is None:
                logger.error("Failed to synthesize speech")
                return False
                
            success = await self.tts.play_audio(audio_data)
            return success
            
        except Exception as e:
            logger.error(f"Error during speech: {e}")
            return False
    
    async def conversation_turn(self, 
                              process_callback,
                              listen_timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a complete conversation turn: listen -> process -> speak
        
        Args:
            process_callback: Async function to process the input text
            listen_timeout: Maximum time to listen
            
        Returns:
            Dictionary with turn results
        """
        result = {
            "input_text": None,
            "output_text": None,
            "success": False,
            "error": None
        }
        
        try:
            # Listen phase
            logger.info("Starting conversation turn - listening")
            input_text = await self.listen(timeout=listen_timeout)
            
            if not input_text:
                result["error"] = "No input detected"
                return result
                
            result["input_text"] = input_text
            
            # Process phase
            logger.info("Processing input")
            output_text = await process_callback(input_text)
            
            if not output_text:
                result["error"] = "No response generated"
                return result
                
            result["output_text"] = output_text
            
            # Speak phase
            logger.info("Speaking response")
            speak_success = await self.speak(output_text)
            
            if not speak_success:
                result["error"] = "Failed to speak response"
                return result
                
            result["success"] = True
            logger.info("Conversation turn completed successfully")
            
        except Exception as e:
            logger.error(f"Error during conversation turn: {e}")
            result["error"] = str(e)
            
        return result
    
    def stop_listening(self):
        """Stop current listening operation"""
        self._is_listening = False
        self.stt.stop_capture()
        
    def is_listening(self) -> bool:
        """Check if currently listening"""
        return self._is_listening
        
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.stt.cleanup()
            await self.tts.cleanup()
            logger.info("Voice pipeline cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
# MARKER_102.5_END