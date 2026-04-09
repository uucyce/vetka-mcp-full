"""
MARKER_B15-WS — SocketIO handler for real-time video scope updates.

Replaces HTTP polling (GET /scopes/analyze, debounced 500ms) with event-driven
scope computation. Client pushes playhead position, server computes scopes
and emits results back.

Events:
  Client → Server:
    "scope_request" — { source_path, time, scopes?, size?, log_profile?, lut_path?, mode? }
      mode: "full" (all scopes, default) | "fast" (histogram only, for playback)

  Server → Client:
    "scope_data" — { success, source_path, time_sec, histogram?, waveform?, ... }

Server-side debounce: if computation is in progress, skip incoming requests
(don't queue — next request will have fresher data anyway).

@status: active
@phase: B15-WS
@task: tb_1774159765_11
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger("cut.scope_ws")

# Server-side debounce: per-client lock to prevent pileup
_client_locks: dict[str, threading.Lock] = {}
_LOCK_CLEANUP_INTERVAL = 300  # cleanup stale locks every 5 min
_last_cleanup = 0.0


def _get_client_lock(sid: str) -> threading.Lock:
    """Get or create a per-client lock for debounce."""
    global _last_cleanup
    now = time.monotonic()
    if now - _last_cleanup > _LOCK_CLEANUP_INTERVAL:
        # Cleanup locks for disconnected clients (best-effort)
        _last_cleanup = now
        stale = [k for k, v in _client_locks.items() if not v.locked()]
        for k in stale[:50]:  # limit cleanup batch
            _client_locks.pop(k, None)
    if sid not in _client_locks:
        _client_locks[sid] = threading.Lock()
    return _client_locks[sid]


def _compute_scopes_sync(data: dict[str, Any]) -> dict[str, Any]:
    """Synchronous scope computation — runs in thread pool."""
    from src.services.cut_scope_renderer import analyze_frame_scopes

    source_path = data.get("source_path", "")
    time_sec = float(data.get("time", 0))
    mode = data.get("mode", "full")

    # Fast mode: histogram only (for live playback, ~2ms)
    if mode == "fast":
        scopes = ["histogram"]
        size = 128  # smaller for speed
    else:
        scopes_raw = data.get("scopes", "histogram,waveform,vectorscope")
        if isinstance(scopes_raw, list):
            scopes = scopes_raw
        else:
            scopes = [s.strip() for s in str(scopes_raw).split(",") if s.strip()]
        size = int(data.get("size", 256))

    size = max(64, min(512, size))
    valid = {"histogram", "waveform", "vectorscope", "parade", "broadcast_safe"}
    scopes = [s for s in scopes if s in valid] or ["histogram"]

    return analyze_frame_scopes(
        source_path=source_path,
        time_sec=time_sec,
        scopes=scopes,
        scope_size=size,
        log_profile=data.get("log_profile"),
        lut_path=data.get("lut_path"),
    )


def register_scope_socket_handlers(sio: Any) -> None:
    """
    Register SocketIO handlers for real-time scope updates.

    Args:
        sio: python-socketio AsyncServer instance
    """
    import asyncio

    @sio.on("scope_request")
    async def handle_scope_request(sid: str, data: dict[str, Any]) -> None:
        """
        Client requests scope computation at current playhead.

        Debounced: if previous computation for this client is still running,
        skip this request (next one will have fresher data).
        """
        if not isinstance(data, dict):
            return

        source_path = data.get("source_path", "")
        if not source_path:
            return

        lock = _get_client_lock(sid)
        if not lock.acquire(blocking=False):
            # Previous computation still running — skip (debounce)
            return

        try:
            # Run scope computation in thread pool (CPU-bound numpy)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _compute_scopes_sync, data)
            await sio.emit("scope_data", result, to=sid)
        except Exception as exc:
            logger.warning("Scope computation failed for %s: %s", sid, exc)
            await sio.emit("scope_data", {
                "success": False,
                "error": str(exc),
                "source_path": source_path,
            }, to=sid)
        finally:
            lock.release()

    @sio.on("disconnect")
    async def handle_scope_disconnect(sid: str) -> None:
        """Cleanup client lock on disconnect."""
        _client_locks.pop(sid, None)

    logger.info("MARKER_B15-WS: Scope SocketIO handlers registered")
