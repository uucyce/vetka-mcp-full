"""
Voice storage routes for persistent chat voice messages.

Provides:
- POST /api/voice/storage        Upload voice sample, return storage_id
- GET  /api/voice/storage/{id}   Stream stored audio by id
"""

from __future__ import annotations

import asyncio
from datetime import datetime, UTC
import json
import threading
import uuid
import base64
import io
import wave
from pathlib import Path
from typing import Any, Dict, Optional
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
from src.voice.qwen_voice_catalog import normalize_qwen_voice_id


router = APIRouter(prefix="/api/voice", tags=["voice-storage"])
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_VOICE_STORAGE_DIR = _PROJECT_ROOT / "data" / "voice_storage"
_VOICE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
_INDEX_PATH = _VOICE_STORAGE_DIR / "index.json"
_INDEX_LOCK = threading.Lock()
_QWEN_SYNTH_LOCK = asyncio.Lock()


class TTSSynthesizeRequest(BaseModel):
    text: str
    speaker: Optional[str] = "ryan"
    language: Optional[str] = None
    speed: Optional[float] = None
    pitch: Optional[float] = None
    energy: Optional[float] = None
    pause_profile: Optional[str] = None


def _is_valid_wav(payload: bytes) -> bool:
    if not payload or len(payload) < 44:
        return False
    try:
        with wave.open(io.BytesIO(payload), "rb") as wav:
            return wav.getnchannels() >= 1 and wav.getframerate() > 0 and wav.getnframes() >= 1
    except Exception:
        return False


def _wrap_pcm16_as_wav(pcm_bytes: bytes, sample_rate: int = 24000) -> bytes:
    if not pcm_bytes:
        return pcm_bytes
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(int(sample_rate))
            wav.writeframes(pcm_bytes)
        return buffer.getvalue()


def normalize_qwen_audio_payload(audio_bytes: bytes) -> tuple[bytes, str, str]:
    """
    Ensure payload is playable WAV.
    Returns: (normalized_bytes, content_type, ext_hint)
    """
    if _is_valid_wav(audio_bytes):
        return audio_bytes, "audio/wav", "wav"
    # Qwen server may return raw PCM16 bytes on some runtime versions.
    return _wrap_pcm16_as_wav(audio_bytes, sample_rate=24000), "audio/wav", "wav"


def _load_index() -> Dict[str, Dict[str, Any]]:
    if not _INDEX_PATH.exists():
        return {}
    try:
        return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_index(index: Dict[str, Dict[str, Any]]) -> None:
    _INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _guess_extension(content_type: str, filename: str) -> str:
    ctype = (content_type or "").lower()
    if "webm" in ctype:
        return "webm"
    if "wav" in ctype:
        return "wav"
    if "mpeg" in ctype or "mp3" in ctype:
        return "mp3"
    if "mp4" in ctype or "m4a" in ctype:
        return "m4a"
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].strip().lower()
        if ext:
            return ext
    return "bin"


def _duration_ms_or_none(file_path: Path, content_type: str) -> Optional[int]:
    # Lightweight duration extraction for WAV only. Other formats return None.
    ctype = (content_type or "").lower()
    if "wav" not in ctype and file_path.suffix.lower() != ".wav":
        return None
    try:
        import wave

        with wave.open(str(file_path), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            if rate > 0:
                return int((frames / float(rate)) * 1000)
    except Exception:
        return None
    return None


def store_voice_audio_bytes(
    payload: bytes,
    *,
    content_type: str = "audio/wav",
    ext_hint: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Persist raw audio bytes to voice storage and return metadata contract.
    Shared by HTTP upload route and internal server-side TTS pipelines.
    """
    if not payload:
        raise ValueError("Empty audio payload")

    ext = (ext_hint or "").strip().lower()
    if not ext:
        ext = _guess_extension(content_type or "", "")
    if not ext:
        ext = "bin"

    storage_id = uuid.uuid4().hex
    out_name = f"{storage_id}.{ext}"
    out_path = _VOICE_STORAGE_DIR / out_name

    try:
        out_path.write_bytes(payload)
        effective_duration_ms = duration_ms
        if effective_duration_ms is None:
            effective_duration_ms = _duration_ms_or_none(out_path, content_type or "")

        with _INDEX_LOCK:
            index = _load_index()
            index[storage_id] = {
                "filename": out_name,
                "content_type": content_type or "application/octet-stream",
                "size_bytes": len(payload),
                "duration_ms": effective_duration_ms,
                "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
            _save_index(index)
    except Exception:
        if out_path.exists():
            try:
                out_path.unlink()
            except Exception:
                pass
        raise

    return {
        "storage_id": storage_id,
        "url": f"/api/voice/storage/{storage_id}",
        "format": ext,
        "duration_ms": effective_duration_ms,
        "size_bytes": len(payload),
    }


@router.post("/storage")
async def upload_voice_storage(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload voice sample and persist to local storage.
    Returns storage_id + playback URL for chat metadata.
    """
    try:
        payload = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read upload: {exc}") from exc

    if not payload:
        raise HTTPException(status_code=400, detail="Empty upload")

    try:
        stored = store_voice_audio_bytes(
            payload,
            content_type=file.content_type or "application/octet-stream",
            ext_hint=_guess_extension(file.content_type or "", file.filename or ""),
            duration_ms=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to store audio: {exc}") from exc

    return stored


@router.get("/storage/{storage_id}")
async def get_voice_storage(storage_id: str):
    """
    Stream stored voice file by storage_id.
    """
    with _INDEX_LOCK:
        index = _load_index()
        meta = index.get(storage_id)

    if not meta:
        raise HTTPException(status_code=404, detail="Voice storage not found")

    filename = str(meta.get("filename", "")).strip()
    if not filename:
        raise HTTPException(status_code=404, detail="Voice storage entry invalid")

    file_path = _VOICE_STORAGE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Voice file missing")

    media_type = str(meta.get("content_type") or "application/octet-stream")
    headers = {
        "Cache-Control": "public, max-age=3600",
        "ETag": storage_id,
    }
    return FileResponse(path=str(file_path), media_type=media_type, headers=headers)


@router.post("/tts/synthesize")
async def synthesize_qwen_tts(payload: TTSSynthesizeRequest) -> Dict[str, Any]:
    """
    On-demand strict local Qwen TTS for chat playback buttons.
    No browser TTS fallback.
    """
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    from src.voice.tts_server_manager import is_tts_running, start_tts_server
    if not is_tts_running():
        start_tts_server(wait_ready=True, timeout=20.0)

    language = payload.language or ("ru" if any("\u0400" <= ch <= "\u04FF" for ch in text) else "en")
    requested_speaker = (payload.speaker or "ryan").strip() or "ryan"
    speaker = normalize_qwen_voice_id(requested_speaker, default="ryan")

    try:
        # Qwen local model is heavy and unstable under burst parallel requests.
        async with _QWEN_SYNTH_LOCK:
            async with httpx.AsyncClient(timeout=90.0) as client:
                health = await client.get("http://127.0.0.1:5003/health", timeout=5.0)
                if health.status_code != 200:
                    raise HTTPException(status_code=503, detail="Qwen TTS server unavailable")

                resp = await client.post(
                    "http://127.0.0.1:5003/tts/generate",
                    json={
                        "text": text,
                        "language": language,
                        "speaker": speaker,
                        "speed": payload.speed,
                        "pitch": payload.pitch,
                        "energy": payload.energy,
                        "pause_profile": payload.pause_profile,
                    },
                    timeout=85.0,
                )
                if resp.status_code >= 400:
                    detail = (resp.text or "").strip().replace("\n", " ")
                    if len(detail) > 240:
                        detail = detail[:240] + "..."
                    logger.warning(
                        "[QWEN_TTS] /tts/generate failed status=%s speaker=%s requested=%s detail=%s",
                        resp.status_code,
                        speaker,
                        requested_speaker,
                        detail,
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=f"Qwen generate failed ({resp.status_code}) speaker={speaker}: {detail or 'no-details'}",
                    )

                body = resp.json() if resp.content else {}
                audio_b64 = body.get("audio") if isinstance(body, dict) else None
                if not audio_b64:
                    raise HTTPException(status_code=502, detail="Qwen TTS returned empty audio")

                audio_bytes = base64.b64decode(audio_b64)
                if not audio_bytes:
                    raise HTTPException(status_code=502, detail="Qwen TTS returned invalid audio")
                audio_bytes, normalized_content_type, normalized_ext = normalize_qwen_audio_payload(audio_bytes)

                # Reuse persistent storage so playback survives reload.
                stored = store_voice_audio_bytes(
                    audio_bytes,
                    content_type=normalized_content_type,
                    ext_hint=normalized_ext,
                    duration_ms=None,
                )
                return {
                    "ok": True,
                    "audio_b64": base64.b64encode(audio_bytes).decode("utf-8"),
                    "format": normalized_ext,
                    "speaker": speaker,
                    "storage_id": stored.get("storage_id"),
                    "url": stored.get("url"),
                    "duration_ms": stored.get("duration_ms"),
                }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[QWEN_TTS] synthesis route failed")
        raise HTTPException(status_code=500, detail=f"Qwen TTS synthesis failed: {repr(exc)}") from exc
