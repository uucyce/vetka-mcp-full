"""
Tool: vetka_voice_to_text
Speech-to-text transcription using whisper.cpp.

@status: active
@phase: 110
@depends: base_tool, whisper.cpp
@used_by: mcp_server, agents needing voice input

Transcribes audio files (WAV, MP3, etc.) to text using whisper.cpp.
Optionally records from microphone if recording tools are available.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .base_tool import BaseMCPTool


# Path to whisper.cpp CLI
WHISPER_CLI = "/Users/uucyce/VETKA-FULL/vetka-chat-host/stt/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/Users/uucyce/VETKA-FULL/vetka-chat-host/stt/models/ggml-base.bin"

# Path to static ffmpeg for microphone recording (avfoundation backend)
FFMPEG_BIN = "/Users/uucyce/VETKA-FULL/vetka-chat-host/stt/ffmpeg"

# Supported audio formats
SUPPORTED_FORMATS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}


class VoiceToTextTool(BaseMCPTool):
    """Speech-to-text tool using whisper.cpp"""
    
    @property
    def name(self) -> str:
        return "vetka_voice_to_text"
    
    @property
    def description(self) -> str:
        return (
            "Transcribe audio to text using whisper.cpp. "
            "Accepts audio file paths (WAV, MP3, FLAC, OGG, M4A, AAC). "
            "Optionally record from microphone with duration parameter."
        )
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "audio_file": {
                    "type": "string",
                    "description": "Path to audio file to transcribe"
                },
                "record_seconds": {
                    "type": "integer",
                    "description": "Record from microphone for N seconds before transcribing (optional, requires sox/ffmpeg)"
                },
                "language": {
                    "type": "string",
                    "description": "Language code (e.g., 'ru', 'en', 'auto'). Default: auto-detect",
                    "default": "auto"
                },
                "translate": {
                    "type": "boolean",
                    "description": "Translate to English if True, otherwise transcribe in original language",
                    "default": False
                }
            },
            "required": []
        }
    
    def _check_whisper(self) -> bool:
        """Check if whisper-cli exists and is executable"""
        return os.path.exists(WHISPER_CLI) and os.access(WHISPER_CLI, os.X_OK)
    
    def _check_model(self) -> bool:
        """Check if whisper model exists"""
        return os.path.exists(WHISPER_MODEL)
    
    def _record_audio(self, duration: int, output_path: str) -> bool:
        """Record audio from microphone
        
        Tries multiple recording methods:
        1. project static ffmpeg (avfoundation on macOS) - preferred
        2. sox (rec command)
        3. system ffmpeg
        4. macOS afrecord
        
        Returns True if recording succeeded
        """
        # Try project static ffmpeg (avfoundation) first - known to work on macOS
        for ffmpeg_candidate in (FFMPEG_BIN if os.path.exists(FFMPEG_BIN) else None, "ffmpeg"):
            if ffmpeg_candidate is None:
                continue
            try:
                cmd = [
                    ffmpeg_candidate, "-f", "avfoundation", "-i", ":0",
                    "-t", str(duration), "-ar", "16000", "-ac", "1",
                    "-c:a", "pcm_s16le", "-y", output_path
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=duration + 10)
                if result.returncode == 0 and os.path.exists(output_path):
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # Try sox
        try:
            cmd = ["rec", "-r", "16000", "-c", "1", "-b", "16", output_path, "trim", "0", str(duration)]
            result = subprocess.run(cmd, capture_output=True, timeout=duration + 5)
            if result.returncode == 0 and os.path.exists(output_path):
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Try macOS afrecord
        try:
            cmd = [
                "afrecord", "-f", "WAVE", "-d", str(duration),
                "-c", "1", "-r", "16000", output_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=duration + 5)
            if result.returncode == 0 and os.path.exists(output_path):
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return False
    
    def _transcribe(self, audio_file: str, language: str = "auto", translate: bool = False) -> Dict[str, Any]:
        """Transcribe audio file using whisper.cpp
        
        Returns:
            {'success': bool, 'text': str, 'error': Optional[str]}
        """
        if not self._check_whisper():
            return {
                'success': False,
                'text': '',
                'error': f'whisper-cli not found at {WHISPER_CLI}'
            }
        
        if not self._check_model():
            return {
                'success': False,
                'text': '',
                'error': f'whisper model not found at {WHISPER_MODEL}'
            }
        
        if not os.path.exists(audio_file):
            return {
                'success': False,
                'text': '',
                'error': f'Audio file not found: {audio_file}'
            }
        
        # Build whisper command
        cmd = [
            WHISPER_CLI,
            "-m", WHISPER_MODEL,
            "-f", audio_file,
            "-nt",  # No timestamps
            "--no-prints",  # Suppress progress output
            "--no-gpu",  # Use CPU backend (Metal crashes in headless env)
        ]
        
        # Language option
        if language and language != "auto":
            cmd.extend(["-l", language])
        
        # Translate option
        if translate:
            cmd.append("--translate")
        
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120  # 2 minute timeout
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='replace').strip()
                return {
                    'success': False,
                    'text': '',
                    'error': f'Whisper failed: {error_msg}'
                }
            
            # Parse output
            text = result.stdout.decode('utf-8', errors='replace').strip()
            
            # Clean up common whisper artifacts
            text = text.replace('[BLANK_AUDIO]', '').strip()
            text = text.replace('[MUSIC]', '').strip()
            
            if not text:
                return {
                    'success': True,
                    'text': '',
                    'error': None,
                    'warning': 'No speech detected in audio'
                }
            
            return {
                'success': True,
                'text': text,
                'duration_ms': round(duration_ms, 1),
                'error': None
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'text': '',
                'error': 'Transcription timed out (>120s)'
            }
        except Exception as e:
            return {
                'success': False,
                'text': '',
                'error': f'Transcription error: {str(e)}'
            }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute voice-to-text transcription"""
        audio_file = arguments.get('audio_file', '')
        record_seconds = arguments.get('record_seconds')
        language = arguments.get('language', 'auto')
        translate = arguments.get('translate', False)
        
        # Validate input
        if not audio_file and not record_seconds:
            return {
                'success': False,
                'error': 'Either audio_file or record_seconds is required',
                'result': None
            }
        
        # Recording mode
        if record_seconds and record_seconds > 0:
            if record_seconds > 300:
                return {
                    'success': False,
                    'error': 'Maximum recording duration is 300 seconds (5 minutes)',
                    'result': None
                }
            
            # Create temp file for recording
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_path = tmp.name
            
            try:
                print(f"[VOICE] Recording {record_seconds}s from microphone...", file=sys.stderr)
                if not self._record_audio(record_seconds, temp_path):
                    return {
                        'success': False,
                        'error': 'Microphone recording failed. Install sox, ffmpeg, or use macOS built-in tools.',
                        'result': None
                    }
                
                audio_file = temp_path
                print(f"[VOICE] Recording complete: {temp_path}", file=sys.stderr)
                
            except Exception as e:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return {
                    'success': False,
                    'error': f'Recording failed: {str(e)}',
                    'result': None
                }
        
        # Transcribe
        try:
            result = self._transcribe(audio_file, language, translate)
            
            # Clean up temp file if we recorded
            if record_seconds and audio_file and os.path.exists(audio_file):
                os.unlink(audio_file)
            
            if result['success']:
                return {
                    'success': True,
                    'result': {
                        'text': result['text'],
                        'language': language,
                        'translate': translate,
                        'duration_ms': result.get('duration_ms'),
                        'warning': result.get('warning')
                    },
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'error': result['error'],
                    'result': None
                }
                
        except Exception as e:
            # Clean up temp file on error
            if record_seconds and audio_file and os.path.exists(audio_file):
                os.unlink(audio_file)
            return {
                'success': False,
                'error': f'Execution failed: {str(e)}',
                'result': None
            }


# Singleton instance
_voice_to_text_tool = None


def get_voice_to_text_tool() -> VoiceToTextTool:
    """Get singleton voice-to-text tool instance"""
    global _voice_to_text_tool
    if _voice_to_text_tool is None:
        _voice_to_text_tool = VoiceToTextTool()
    return _voice_to_text_tool


# Convenience function for direct MCP bridge calls
def vetka_voice_to_text(**kwargs) -> Dict[str, Any]:
    """Direct call to voice-to-text tool"""
    tool = get_voice_to_text_tool()
    return tool.safe_execute(kwargs)


def register_voice_to_text_tool(mcp_server):
    """Register voice-to-text tool with MCP server"""
    tool = get_voice_to_text_tool()
    mcp_server.register_tool(tool)
    print(f"[MCP] Voice-to-text tool registered: {tool.name}")
    return tool
