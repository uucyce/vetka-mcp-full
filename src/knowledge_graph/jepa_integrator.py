"""
MARKER_2026_JEPA_INTEGRATION_FULL

Pragmatic JEPA integration layer for VETKA:
- video/audio embedding extraction contract
- runtime HTTP bridge to external JEPA service
- robust local fallback path (no hard dependency on JEPA runtime)

Notes:
- This module is production-safe in mixed environments (with/without JEPA runtime).
- Real JEPA/V-JEPA backend is expected to be served behind HTTP endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class JepaRuntimeConfig:
    media_url: str = os.environ.get("MCC_JEPA_HTTP_MEDIA_URL", "http://127.0.0.1:8099/embed_media")
    timeout_sec: float = float(os.environ.get("MCC_JEPA_HTTP_TIMEOUT_SEC", "3.0"))
    enabled: bool = os.environ.get("MCC_JEPA_HTTP_ENABLE", "").strip().lower() in {"1", "true", "yes"}


def _normalize(vec: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(vec))
    if n <= 1e-12:
        return vec
    return vec / n


def _stable_hash_embedding(text: str, dim: int = 512) -> np.ndarray:
    import hashlib

    clean = (text or "").strip().lower()
    if not clean:
        return np.zeros(dim, dtype=np.float32)

    vec = np.zeros(dim, dtype=np.float32)
    tokens = [t for t in clean.replace("\\", "/").replace("_", "/").replace("-", "/").split("/") if t]
    if not tokens:
        tokens = [clean]
    for tok in tokens:
        h = hashlib.sha1(tok.encode("utf-8")).hexdigest()
        for i in range(0, min(len(h), dim * 2), 2):
            idx = (i // 2) % dim
            vec[idx] += (int(h[i : i + 2], 16) / 255.0) - 0.5
    return _normalize(vec).astype(np.float32)


class JepaIntegrator:
    def __init__(self, model_path: str = "./models/v-jepa-base-mlx", max_frames: int = 32, embedding_dim: int = 512):
        self.model_path = model_path
        self.max_frames = int(max(4, min(max_frames, 128)))
        self.embedding_dim = int(max(64, min(embedding_dim, 2048)))
        self.runtime = JepaRuntimeConfig()

    def extract_video_frames(self, video_path: str) -> List[np.ndarray]:
        """Extract representative frames from video (OpenCV optional)."""
        try:
            import cv2  # type: ignore
        except Exception:
            logger.warning("[JEPA] OpenCV unavailable, frame extraction skipped")
            return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, frame_count // max(1, self.max_frames))
        frames: List[np.ndarray] = []
        for i in range(0, max(1, frame_count), step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.resize(frame, (224, 224))
            frames.append(frame.astype(np.uint8))
            if len(frames) >= self.max_frames:
                break
        cap.release()
        return frames

    def _http_embed_media(self, media_type: str, path: str, transcript: str = "") -> Optional[np.ndarray]:
        if not self.runtime.enabled:
            return None
        payload = {
            "media_type": media_type,
            "path": path,
            "dim": self.embedding_dim,
            "max_frames": self.max_frames,
            "transcript": transcript or "",
        }
        req = urllib.request.Request(
            self.runtime.media_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.runtime.timeout_sec) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body) if body else {}
            vector = data.get("vector")
            if not isinstance(vector, list) or not vector:
                return None
            arr = np.array(vector[: self.embedding_dim], dtype=np.float32)
            if arr.size < self.embedding_dim:
                arr = np.pad(arr, (0, self.embedding_dim - arr.size))
            return _normalize(arr).astype(np.float32)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as e:
            logger.warning("[JEPA] HTTP media runtime unavailable: %s", e.__class__.__name__)
            return None

    async def transcribe_audio(self, audio_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Whisper transcription path.
        Uses local whisper CLI-compatible path if available in environment.
        """
        try:
            from src.voice.stt_engine import WhisperSTT
            stt = WhisperSTT(model_name="base")
            result = await asyncio.to_thread(stt.transcribe, audio_path)
            text = str(result.get("text") or "").strip()
            segments = result.get("segments") or []
            if not isinstance(segments, list):
                segments = []
            return text, segments
        except Exception as e:
            logger.warning("[JEPA] Audio transcription unavailable: %s", e.__class__.__name__)
            return "", []

    async def get_video_embedding(self, video_path: str) -> np.ndarray:
        video_path = str(video_path)
        if not Path(video_path).exists():
            raise FileNotFoundError(video_path)

        http_vec = self._http_embed_media("video", video_path)
        if http_vec is not None:
            return http_vec

        frames = self.extract_video_frames(video_path)
        if frames:
            # Lightweight fallback: frame statistics projection.
            arr = np.concatenate([f.mean(axis=(0, 1)).astype(np.float32) for f in frames], axis=0)
            if arr.size < self.embedding_dim:
                arr = np.pad(arr, (0, self.embedding_dim - arr.size))
            else:
                arr = arr[: self.embedding_dim]
            return _normalize(arr).astype(np.float32)

        return _stable_hash_embedding(f"video:{video_path}", dim=self.embedding_dim)

    async def get_audio_embedding(self, audio_path: str) -> Tuple[np.ndarray, Dict[str, Any]]:
        audio_path = str(audio_path)
        if not Path(audio_path).exists():
            raise FileNotFoundError(audio_path)

        transcript, segments = await self.transcribe_audio(audio_path)
        http_vec = self._http_embed_media("audio", audio_path, transcript=transcript)
        if http_vec is not None:
            return http_vec, {"transcript": transcript, "segments": segments, "jepa_mode": "http_runtime"}

        text_basis = f"audio:{audio_path}|{transcript[:2000]}"
        emb = _stable_hash_embedding(text_basis, dim=self.embedding_dim)
        return emb, {"transcript": transcript, "segments": segments, "jepa_mode": "fallback_hash"}

    async def predict_new_links(
        self,
        existing_embeddings: List[np.ndarray],
        threshold: float = 0.85,
    ) -> List[Dict[str, Any]]:
        """Predict candidate links by cosine threshold."""
        links: List[Dict[str, Any]] = []
        if not existing_embeddings:
            return links

        for i, emb1 in enumerate(existing_embeddings):
            n1 = float(np.linalg.norm(emb1))
            if n1 <= 1e-12:
                continue
            for j, emb2 in enumerate(existing_embeddings):
                if i == j:
                    continue
                n2 = float(np.linalg.norm(emb2))
                if n2 <= 1e-12:
                    continue
                sim = float(np.dot(emb1, emb2) / (n1 * n2))
                if sim >= threshold:
                    links.append(
                        {
                            "source_id": f"node_{i}",
                            "target_id": f"node_{j}",
                            "type": "predicted",
                            "strength": sim,
                        }
                    )
        return links


# Global runtime singleton
jepa = JepaIntegrator()
