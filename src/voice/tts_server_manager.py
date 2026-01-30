"""
TTS Server Manager - Phase 104

Manages the MLX Qwen3-TTS microservice lifecycle.
Handles startup, health checks, and graceful shutdown.
"""

import subprocess
import logging
import os
import time
import httpx
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Module-level process reference
_tts_process: Optional[subprocess.Popen] = None

# Configuration
TTS_PORT = 5003
TTS_HEALTH_URL = f"http://127.0.0.1:{TTS_PORT}/health"
PROJECT_ROOT = Path(__file__).parent.parent.parent


def start_tts_server(port: int = TTS_PORT, wait_ready: bool = True, timeout: float = 30.0) -> Optional[subprocess.Popen]:
    """
    Start the TTS server subprocess.

    Args:
        port: Port to run the server on (default 5003)
        wait_ready: Whether to wait for server to be ready
        timeout: Max seconds to wait for ready

    Returns:
        subprocess.Popen instance if started, None if failed
    """
    global _tts_process

    # Check if already running
    if is_tts_running():
        logger.info(f"[TTS] Server already running on port {port}")
        return _tts_process

    # Find paths
    venv_python = PROJECT_ROOT / "venv_voice" / "bin" / "python"
    server_script = PROJECT_ROOT / "scripts" / "voice_tts_server.py"

    if not venv_python.exists():
        logger.warning(f"[TTS] venv_voice not found at {venv_python}")
        return None

    if not server_script.exists():
        logger.warning(f"[TTS] Server script not found at {server_script}")
        return None

    try:
        # Start subprocess
        _tts_process = subprocess.Popen(
            [str(venv_python), str(server_script), str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,  # Detach from parent process group
            cwd=str(PROJECT_ROOT)
        )

        logger.info(f"[TTS] Server process started (PID: {_tts_process.pid}) on port {port}")

        if wait_ready:
            if _wait_for_ready(timeout):
                logger.info(f"[TTS] Server ready on port {port}")
            else:
                logger.warning(f"[TTS] Server not ready after {timeout}s (may still be loading model)")

        return _tts_process

    except Exception as e:
        logger.error(f"[TTS] Failed to start server: {e}")
        return None


def stop_tts_server(timeout: float = 5.0) -> bool:
    """
    Stop the TTS server gracefully.

    Args:
        timeout: Max seconds to wait for graceful shutdown

    Returns:
        True if stopped successfully
    """
    global _tts_process

    if _tts_process is None:
        logger.info("[TTS] No server process to stop")
        return True

    try:
        # Try graceful terminate first
        _tts_process.terminate()

        try:
            _tts_process.wait(timeout=timeout)
            logger.info("[TTS] Server stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if still running
            _tts_process.kill()
            _tts_process.wait(timeout=2)
            logger.warning("[TTS] Server killed forcefully")

        _tts_process = None
        return True

    except Exception as e:
        logger.error(f"[TTS] Error stopping server: {e}")
        _tts_process = None
        return False


def is_tts_running() -> bool:
    """Check if TTS server is responding to health checks."""
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(TTS_HEALTH_URL)
            return response.status_code == 200
    except Exception:
        return False


def get_tts_status() -> dict:
    """Get detailed TTS server status."""
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(TTS_HEALTH_URL)
            if response.status_code == 200:
                return {
                    "running": True,
                    "port": TTS_PORT,
                    "pid": _tts_process.pid if _tts_process else None,
                    **response.json()
                }
    except Exception as e:
        pass

    return {
        "running": False,
        "port": TTS_PORT,
        "pid": _tts_process.pid if _tts_process else None,
        "error": "Not responding"
    }


def _wait_for_ready(timeout: float) -> bool:
    """Wait for TTS server to respond to health check."""
    start = time.time()
    while time.time() - start < timeout:
        if is_tts_running():
            return True
        time.sleep(0.5)
    return False


# Cleanup handler for atexit
def _cleanup():
    """Cleanup handler called on program exit."""
    if _tts_process:
        stop_tts_server(timeout=2.0)


# Register cleanup
import atexit
atexit.register(_cleanup)
