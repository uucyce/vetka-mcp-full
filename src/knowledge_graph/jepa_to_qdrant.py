"""
MARKER_2026_VIDEO_AUDIO_EMBEDDING_QDRANT

JEPA -> Qdrant media embedding bridge for VETKA.

Stores:
- vector embedding
- media metadata
- optional transcript segments (audio)
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from src.knowledge_graph.jepa_integrator import jepa

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, PointStruct, VectorParams
except Exception:  # pragma: no cover
    QdrantClient = None  # type: ignore
    Distance = None  # type: ignore
    PointStruct = None  # type: ignore
    VectorParams = None  # type: ignore


@dataclass
class MediaMetadata:
    path: str
    media_type: str
    created_at: str
    file_size_mb: float
    duration_sec: float = 0.0
    source: str = "user_upload"
    transcript: str = ""
    transcript_segments: Optional[List[Dict[str, Any]]] = None


class JepaToQdrant:
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "vetka_media_embeddings",
        embedding_dim: int = 512,
    ):
        if QdrantClient is None:
            raise RuntimeError("qdrant-client is not installed")
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        self.embedding_dim = int(max(64, min(embedding_dim, 4096)))
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE),
        )

    @staticmethod
    def _safe_size_mb(path: str) -> float:
        try:
            return float(os.path.getsize(path) / (1024 * 1024))
        except Exception:
            return 0.0

    @staticmethod
    def _safe_duration_sec(path: str) -> float:
        # best-effort probe for video duration
        try:
            import cv2  # type: ignore

            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                return 0.0
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            total = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
            cap.release()
            if fps > 0.0 and total > 0.0:
                return total / fps
        except Exception:
            pass
        return 0.0

    def _run(self, coro):
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # sync wrapper called from running loop: spawn dedicated loop
                new_loop = asyncio.new_event_loop()
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
        except RuntimeError:
            pass
        return asyncio.run(coro)

    def upsert_video(self, video_path: str, payload_extra: Optional[Dict[str, Any]] = None) -> str:
        p = Path(video_path)
        if not p.exists():
            raise FileNotFoundError(video_path)

        emb: np.ndarray = self._run(jepa.get_video_embedding(str(p)))
        emb = emb.astype(np.float32)
        if emb.size < self.embedding_dim:
            emb = np.pad(emb, (0, self.embedding_dim - emb.size))
        else:
            emb = emb[: self.embedding_dim]

        meta = MediaMetadata(
            path=str(p),
            media_type="video",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            file_size_mb=self._safe_size_mb(str(p)),
            duration_sec=self._safe_duration_sec(str(p)),
        )

        point_id = str(uuid.uuid4())
        payload = {
            "type": "media",
            "media_type": "video",
            **meta.__dict__,
            **(payload_extra or {}),
        }

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=emb.tolist(),
                    payload=payload,
                )
            ],
        )
        return point_id

    def upsert_audio(self, audio_path: str, payload_extra: Optional[Dict[str, Any]] = None) -> str:
        p = Path(audio_path)
        if not p.exists():
            raise FileNotFoundError(audio_path)

        emb, audio_meta = self._run(jepa.get_audio_embedding(str(p)))
        emb = emb.astype(np.float32)
        if emb.size < self.embedding_dim:
            emb = np.pad(emb, (0, self.embedding_dim - emb.size))
        else:
            emb = emb[: self.embedding_dim]

        meta = MediaMetadata(
            path=str(p),
            media_type="audio",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            file_size_mb=self._safe_size_mb(str(p)),
            duration_sec=float(audio_meta.get("duration_sec") or 0.0),
            transcript=str(audio_meta.get("transcript") or ""),
            transcript_segments=audio_meta.get("segments") if isinstance(audio_meta.get("segments"), list) else [],
        )

        point_id = str(uuid.uuid4())
        payload = {
            "type": "media",
            "media_type": "audio",
            **meta.__dict__,
            **(payload_extra or {}),
        }

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=emb.tolist(),
                    payload=payload,
                )
            ],
        )
        return point_id

    def search_similar(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        if not query_vector:
            return []
        vector = [float(x) for x in query_vector[: self.embedding_dim]]
        if len(vector) < self.embedding_dim:
            vector += [0.0] * (self.embedding_dim - len(vector))

        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=max(1, min(limit, 50)),
            with_payload=True,
        )
        out: List[Dict[str, Any]] = []
        for hit in hits:
            out.append({"id": str(hit.id), "score": float(hit.score), "payload": hit.payload or {}})
        return out
