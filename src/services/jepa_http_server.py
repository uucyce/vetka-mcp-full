"""
MARKER_155.P3_1.JEPA_HTTP_SERVER.V1

Local JEPA runtime server (FastAPI, separate process).

Endpoints:
- GET  /health
- POST /embed_texts
- POST /embed_media

Run:
  python -m src.services.jepa_http_server
or
  uvicorn src.services.jepa_http_server:app --host 127.0.0.1 --port 8099
"""

from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

from src.utils.embedding_service import get_embedding_service


APP_HOST = os.environ.get("MCC_JEPA_HTTP_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("MCC_JEPA_HTTP_PORT", "8099"))


class EmbedTextsRequest(BaseModel):
    texts: List[str]
    dim: int = 128


class EmbedMediaRequest(BaseModel):
    media_type: str  # video|audio
    path: str
    dim: int = 512
    max_frames: int = 32
    transcript: str = ""


app = FastAPI(title="VETKA JEPA Runtime", version="1.0.0")


def _normalize(vec: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(vec))
    if n <= 1e-12:
        return vec
    return vec / n


def _hash_vec(text: str, dim: int) -> np.ndarray:
    clean = (text or "").strip().lower()
    if not clean:
        return np.zeros(dim, dtype=np.float32)
    out = np.zeros(dim, dtype=np.float32)
    toks = [t for t in clean.replace("\\", "/").replace("_", "/").replace("-", "/").split("/") if t]
    if not toks:
        toks = [clean]
    for tok in toks:
        h = hashlib.sha1(tok.encode("utf-8")).hexdigest()
        for i in range(0, min(len(h), dim * 2), 2):
            out[(i // 2) % dim] += (int(h[i : i + 2], 16) / 255.0) - 0.5
    return _normalize(out).astype(np.float32)


def _whiten(vectors: List[np.ndarray]) -> List[np.ndarray]:
    if len(vectors) < 3:
        return vectors
    X = np.stack(vectors).astype(np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    X = np.clip(X, -10.0, 10.0)
    Xc = X - X.mean(axis=0, keepdims=True)
    Xc = np.nan_to_num(Xc, nan=0.0, posinf=0.0, neginf=0.0)
    Xc = np.clip(Xc, -10.0, 10.0)
    try:
        with np.errstate(all="ignore"):
            cov = (Xc.T @ Xc) / max(1, Xc.shape[0] - 1)
        cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
        cov = np.clip(cov, -1e6, 1e6)
        vals, vecs = np.linalg.eigh(cov)
        order = np.argsort(vals)[::-1]
        vals = np.maximum(vals[order], 1e-9)
        vecs = vecs[:, order]
        cumulative = np.cumsum(vals) / float(vals.sum())
        keep = int(np.searchsorted(cumulative, 0.95) + 1)
        keep = max(8, min(keep, min(X.shape[1], 128)))
        proj = vecs[:, :keep]
        scaled = np.diag(1.0 / np.sqrt(vals[:keep] + 1e-6))
        with np.errstate(all="ignore"):
            Xw = Xc @ proj @ scaled
        Xw = np.nan_to_num(Xw, nan=0.0, posinf=0.0, neginf=0.0)
        Xw = np.clip(Xw, -50.0, 50.0)
        return [_normalize(row.astype(np.float32)) for row in Xw]
    except Exception:
        return vectors


def _embed_texts_internal(texts: List[str], dim: int) -> List[np.ndarray]:
    use_embedding_backend = os.environ.get("MCC_JEPA_HTTP_USE_EMBEDDING_BACKEND", "").strip().lower() in {
        "1", "true", "yes", "on"
    }
    vectors: List[np.ndarray] = []

    # Safety-first default:
    # keep JEPA HTTP runtime process stable even when local embedding backend is flaky
    # (e.g., crashes in native ML stacks). Enable backend explicitly via env flag.
    if not use_embedding_backend:
        vectors = [_hash_vec(t, dim) for t in texts]
        vectors = _whiten(vectors)
        return vectors

    svc = get_embedding_service()
    raw = svc.get_embedding_batch(texts)
    for i, row in enumerate(raw):
        if isinstance(row, list) and row:
            arr = np.array(row[:dim], dtype=np.float32)
            if arr.size < dim:
                arr = np.pad(arr, (0, dim - arr.size))
            vectors.append(_normalize(arr))
        else:
            vectors.append(_hash_vec(texts[i], dim))
    vectors = _whiten(vectors)
    return vectors


def _embed_video(path: str, dim: int, max_frames: int) -> np.ndarray:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if cv2 is None:
        return _hash_vec(f"video:{path}", dim)

    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        return _hash_vec(f"video:{path}", dim)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total // max(1, max_frames))
    means: List[np.ndarray] = []
    for i in range(0, max(1, total), step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.resize(frame, (224, 224))
        means.append(frame.mean(axis=(0, 1)).astype(np.float32))
        if len(means) >= max_frames:
            break
    cap.release()
    if not means:
        return _hash_vec(f"video:{path}", dim)
    arr = np.concatenate(means, axis=0)
    if arr.size < dim:
        arr = np.pad(arr, (0, dim - arr.size))
    else:
        arr = arr[:dim]
    return _normalize(arr.astype(np.float32))


def _embed_audio(path: str, transcript: str, dim: int) -> np.ndarray:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    basis = f"audio:{path}|{(transcript or '')[:3000]}"
    return _hash_vec(basis, dim)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "vetka_jepa_runtime",
        "mode": "local_fastapi_runtime",
        "host": APP_HOST,
        "port": APP_PORT,
    }


@app.post("/embed_texts")
async def embed_texts(req: EmbedTextsRequest) -> Dict[str, Any]:
    if not req.texts:
        return {"vectors": [], "model": "empty"}
    dim = max(16, min(int(req.dim), 512))
    vectors = _embed_texts_internal(req.texts, dim=dim)
    return {
        "vectors": [v.tolist() for v in vectors],
        "model": "vetka_jepa_runtime_texts_v1",
        "dim": dim,
    }


@app.post("/embed_media")
async def embed_media(req: EmbedMediaRequest) -> Dict[str, Any]:
    media_type = str(req.media_type or "").strip().lower()
    dim = max(64, min(int(req.dim), 2048))
    path = str(req.path or "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    try:
        if media_type == "video":
            vec = _embed_video(path, dim=dim, max_frames=max(4, min(int(req.max_frames), 128)))
        elif media_type == "audio":
            vec = _embed_audio(path, req.transcript or "", dim=dim)
        else:
            raise HTTPException(status_code=400, detail="media_type must be video|audio")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"media file not found: {path}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"embed_media failed: {e}")

    return {
        "vector": vec.tolist(),
        "model": "vetka_jepa_runtime_media_v1",
        "dim": dim,
        "media_type": media_type,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.services.jepa_http_server:app", host=APP_HOST, port=APP_PORT, reload=False)
