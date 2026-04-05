"""
MARKER_B40 — SocketIO handler for real-time audio scope updates.
MARKER_MIXER_STATE — mixer_levels_request: mixer-aware VU metering.

Mirrors scope_socket_handler.py pattern for audio: client pushes playhead
position, server computes RMS levels + optional waveform bins, emits back.

Events:
  Client → Server:
    "audio_scope_request" — { source_path, time, mode? }
      mode: "fast" (RMS only, for playback) | "full" (RMS + waveform bins)

    "mixer_levels_request" — { project_id, sources: [{source_path, lane_id, time}] }
      Computes per-lane RMS with mixer state (volume/mute/solo) applied.

  Server → Client:
    "audio_scope_data" — { success, source_path, time_sec,
                           rms_left, rms_right, peak_left, peak_right,
                           waveform_left?, waveform_right? }

    "mixer_levels_data" — { success, project_id,
                            lanes: {lane_id: {rms_left, rms_right, peak_left, peak_right,
                                              effective_rms_left, effective_rms_right, muted}},
                            master: {volume, pan} }

Server-side debounce: per-client lock prevents pileup (same pattern as video scopes).

@status: active
@phase: B40
@task: tb_1774241112_1
"""
from __future__ import annotations

import functools
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

    # MARKER_MIXER_STATE: Per-client debounce for mixer levels (separate lock from scope)
    _mixer_client_locks: dict[str, threading.Lock] = {}

    @sio.on("mixer_levels_request")
    async def handle_mixer_levels_request(sid: str, data: dict[str, Any]) -> None:
        """
        Client requests mixer-aware VU levels for all active lanes.

        Payload: { project_id, sources: [{source_path, lane_id, time}] }

        For each source: computes raw RMS via compute_audio_levels, then applies
        mixer state (volume, mute, solo) to get effective metering levels.

        Emits: mixer_levels_data → { success, project_id, lanes: {...}, master: {...} }
        """
        if not isinstance(data, dict):
            return
        sources = data.get("sources") or []
        if not sources:
            return
        project_id = str(data.get("project_id") or "project")

        lock = _mixer_client_locks.setdefault(sid, threading.Lock())
        if not lock.acquire(blocking=False):
            return  # Previous computation still running

        try:
            from src.services.cut_audio_engine import get_mixer_state, apply_mixer_levels
            from src.services.cut_ffmpeg_waveform import compute_audio_levels

            mixer = get_mixer_state(project_id)
            any_solo = any(ls.solo for ls in mixer.lanes.values())

            lane_results: dict[str, Any] = {}

            loop = asyncio.get_running_loop()

            async def _compute_one(entry: dict) -> None:
                source_path = str(entry.get("source_path") or "")
                lane_id = str(entry.get("lane_id") or "")
                time_sec = float(entry.get("time", 0))
                if not source_path or not lane_id:
                    return
                try:
                    raw = await loop.run_in_executor(
                        None,
                        functools.partial(
                            compute_audio_levels,
                            source_path,
                            time_sec,
                            waveform_bins=0,
                        ),
                    )
                except Exception:
                    raw = {}
                rms_l = float(raw.get("rms_left", 0.0))
                rms_r = float(raw.get("rms_right", 0.0))
                peak_l = float(raw.get("peak_left", 0.0))
                peak_r = float(raw.get("peak_right", 0.0))
                lane_state = mixer.lanes.get(lane_id)
                vol = lane_state.volume if lane_state else 1.0
                muted = lane_state.mute if lane_state else False
                solo = lane_state.solo if lane_state else False
                eff_l, eff_r = apply_mixer_levels(
                    rms_l, rms_r, vol, mixer.master_volume, muted, solo, any_solo
                )
                lane_results[lane_id] = {
                    "rms_left": round(rms_l, 4),
                    "rms_right": round(rms_r, 4),
                    "peak_left": round(peak_l, 4),
                    "peak_right": round(peak_r, 4),
                    "effective_rms_left": round(eff_l, 4),
                    "effective_rms_right": round(eff_r, 4),
                    "muted": muted or (any_solo and not solo),
                }

            # Compute all lanes concurrently
            await asyncio.gather(*[_compute_one(entry) for entry in sources])

            await sio.emit("mixer_levels_data", {
                "success": True,
                "project_id": project_id,
                "lanes": lane_results,
                "master": {
                    "volume": mixer.master_volume,
                    "pan": mixer.master_pan,
                },
            }, to=sid)

        except Exception as exc:
            logger.warning("mixer_levels_request failed for sid=%s: %s", sid, exc)
            await sio.emit("mixer_levels_data", {
                "success": False,
                "error": str(exc),
                "project_id": project_id,
            }, to=sid)
        finally:
            lock.release()

    @sio.on("disconnect")
    async def handle_audio_scope_disconnect(sid: str) -> None:
        """Cleanup client locks on disconnect."""
        _audio_client_locks.pop(sid, None)
        _mixer_client_locks.pop(sid, None)

    logger.info("MARKER_B40/MARKER_MIXER_STATE: Audio scope + mixer SocketIO handlers registered")
