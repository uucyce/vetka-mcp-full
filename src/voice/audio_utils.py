# MARKER_102.3_START
import subprocess
import os
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def convert_to_webm(input_path: str, output_path: str = None) -> str:
    """
    Convert audio file to WebM format using FFmpeg.
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output WebM file (optional)
    
    Returns:
        Path to converted WebM file
    """
    if output_path is None:
        output_path = str(Path(input_path).with_suffix('.webm'))
    
    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:a', 'libopus',
            '-b:a', '64k',
            '-y',  # Overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Successfully converted {input_path} to {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed: {e.stderr}")
        raise RuntimeError(f"Audio conversion failed: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found. Please install FFmpeg.")

def get_audio_duration(file_path: str) -> float:
    """
    Get duration of audio file in seconds using FFprobe.
    
    Args:
        file_path: Path to audio file
    
    Returns:
        Duration in seconds
    """
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
        
    except (subprocess.CalledProcessError, ValueError) as e:
        logger.error(f"Failed to get audio duration: {e}")
        raise RuntimeError(f"Could not determine audio duration: {e}")
    except FileNotFoundError:
        raise RuntimeError("FFprobe not found. Please install FFmpeg.")

def validate_audio_file(file_path: str) -> bool:
    """
    Validate if file is a supported audio format.
    
    Args:
        file_path: Path to audio file
    
    Returns:
        True if valid audio file
    """
    if not os.path.exists(file_path):
        return False
    
    try:
        # Try to get duration - if successful, it's likely a valid audio file
        get_audio_duration(file_path)
        return True
    except RuntimeError:
        return False

def create_temp_webm(input_path: str) -> str:
    """
    Create temporary WebM file from input audio.
    
    Args:
        input_path: Path to input audio file
    
    Returns:
        Path to temporary WebM file
    """
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp_file:
        temp_path = tmp_file.name
    
    return convert_to_webm(input_path, temp_path)

def cleanup_temp_file(file_path: str) -> None:
    """
    Safely remove temporary file.
    
    Args:
        file_path: Path to file to remove
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")
    except OSError as e:
        logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")
# MARKER_102.3_END