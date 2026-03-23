"""
MARKER_B40 — SocketIO handler for real-time audio scope updates.

Mirrors scope_socket_handler.py pattern for audio: client pushes playhead
position, server computes RMS levels + optional waveform bins, emits back.

Events:
  Client → Server:
    "audio_scope_request" — { source_path, time, mode? }
      mode: "fast" (RMS only, for playback) | "full" (RMS + waveform bins)

  Server → Client:
    "audio_scope_data" — { success, source_path, time_sec,
                           rms_left, rms_right, peak_left, peak_right,
                           waveform_left?, waveform_right? }

Server-side debounce: per-client lock prevents pileup (same pattern as video scopes).

@status: active
@phase: B40
@task: tb_1774241112_1
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger("cut.audio_scope_ws")

# Per-client debounce locks (shared pattern with scope_socket_handler)
_audio_client_locks: dict[str, threading.Lock] = {}
_LOCK_CLEANUP_INTERVAL = 300
_last_cleanup = 0.0


def _get_audio_client_lock(sid: str) -> threading.Lock:
    """Get or create a per-client lock for debounce."""
    global _last_cleanup
    now = time.monotonic()
    if now - _last_cleanup > _LOCK_CLEANUP_INTERVAL:
        _last_cleanup = now
        stale = [k for k, v in _audio_client_locks.items() if not v.locked()]
        for k in stale[:50]:
            _audio_client_locks.pop(k, None)
    if sid not in _audio_client_locks:
        _audio_client_locks[sid] = threading.Lock()
    return _audio_client_locks[sid]


def _compute_audio_levels_sync(data: dict[str, Any]) -> dict[str, Any]:
    """Synchronous audio level computation — runs in thread pool."""
    from src.services.cut_ffmpeg_waveform import compute_audio_levels

    source_path = data.get("source_path", "")
    time_sec = float(data.get("time", 0))
    mode = data.get("mode", "fast")

    # Fast mode: RMS only (~2ms). Full mode: RMS + waveform bins (~5ms).
    waveform_bins = 0 if mode == "fast" else int(data.get("waveform_bins", 32))

    return compute_audio_levels(
        media_path=source_path,
        time_sec=time_sec,
        waveform_bins=waveform_bins,
    )


def register_audio_scope_socket_handlers(sio: Any) -> None:
    """Register SocketIO handlers for real-time audio level metering."""
    import asyncio

    @sio.on("audio_scope_request")
    async def handle_audio_scope_request(sid: str, data: dict[str, Any]) -> None:
        """Client requests audio levels at current playhead."""
        if not isinstance(data, dict):
            return

        source_path = data.get("source_path", "")
        if not source_path:
            return

        lock = _get_audio_client_lock(sid)
        if not lock.acquire(blocking=False):
            return  # Previous computation still running — skip

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _compute_audio_levels_sync, data)
            await sio.emit("audio_scope_data", result, to=sid)
        except Exception as exc:
            logger.warning("Audio scope computation failed for %s: %s", sid, exc)
            await sio.emit("audio_scope_data", {
                "success": False,
                "error": str(exc),
                "source_path": source_path,
            }, to=sid)
        finally:
            lock.release()

    @sio.on("disconnect")
    async def handle_audio_scope_disconnect(sid: str) -> None:
        """Cleanup client lock on disconnect."""
        _audio_client_locks.pop(sid, None)

    logger.info("MARKER_B40: Audio scope SocketIO handlers registered")
