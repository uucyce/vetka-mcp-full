"""
MARKER_155.P3_1.JEPA_RUNTIME_PROVIDER.V1

Runtime JEPA-style embedding provider for MCC predictive overlay.

Current runtime path:
- prefers batch embeddings from EmbeddingService (Ollama-backed when available)
- applies Tao-inspired whitening / dominant-direction suppression
- returns normalized vectors for overlay predictor

This module is loaded dynamically by `mcc_jepa_adapter`.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

from src.utils.embedding_service import get_embedding_service


_RUNTIME_CACHE: Dict[str, List[List[float]]] = {}
_RUNTIME_STATUS: Dict[str, Any] = {
    "backend": "uninitialized",
    "detail": "",
}
_HTTP_HEALTH_CACHE: Dict[str, Any] = {
    "url": "",
    "ok": False,
    "detail": "",
    "ts": 0.0,
}
_HTTP_RUNTIME_PROC: subprocess.Popen | None = None


def _normalize(vec: List[float]) -> List[float]:
    n = math.sqrt(sum(x * x for x in vec))
    if n <= 1e-12:
        return vec
    return [x / n for x in vec]


def _stable_text_vector(text: str, dim: int = 128) -> List[float]:
    clean = (text or "").strip().lower()
    if not clean:
        return [0.0] * dim
    v = [0.0] * dim
    toks = [t for t in clean.replace("\\", "/").replace("_", "/").replace("-", "/").split("/") if t]
    if not toks:
        toks = [clean]
    for tok in toks:
        h = hashlib.sha1(tok.encode("utf-8")).hexdigest()
        for i in range(0, min(len(h), dim * 2), 2):
            idx = (i // 2) % dim
            v[idx] += (int(h[i : i + 2], 16) / 255.0) - 0.5
    return _normalize(v)


def _cache_key(texts: List[str], dim: int) -> str:
    digest = hashlib.md5(("\n".join(texts) + f"|{dim}").encode("utf-8")).hexdigest()
    return f"{len(texts)}:{dim}:{digest}"


def _set_runtime_status(backend: str, detail: str = "") -> None:
    _RUNTIME_STATUS["backend"] = backend
    _RUNTIME_STATUS["detail"] = detail


def get_runtime_status() -> Dict[str, Any]:
    return dict(_RUNTIME_STATUS)


def _runtime_urls() -> Tuple[str, str, bool]:
    url = (os.environ.get("MCC_JEPA_HTTP_URL") or "").strip()
    enabled = (os.environ.get("MCC_JEPA_HTTP_ENABLE") or "").strip().lower() in {"1", "true", "yes"}
    if not url and enabled:
        url = "http://127.0.0.1:8099/embed_texts"
    health_url = url.rsplit("/", 1)[0] + "/health" if url else ""
    return url, health_url, enabled


def _parse_host_port_from_url(url: str) -> Tuple[str, int] | None:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = int(parsed.port or 8099)
        return host, port
    except Exception:
        return None


def _ensure_http_runtime_started(url: str) -> None:
    global _HTTP_RUNTIME_PROC
    if _HTTP_RUNTIME_PROC is not None and _HTTP_RUNTIME_PROC.poll() is None:
        return
    host_port = _parse_host_port_from_url(url)
    if not host_port:
        return
    host, port = host_port
    if host not in {"127.0.0.1", "localhost"}:
        return
    env = os.environ.copy()
    env.setdefault("MCC_JEPA_HTTP_ENABLE", "1")
    env.setdefault("MCC_JEPA_HTTP_HOST", host)
    env.setdefault("MCC_JEPA_HTTP_PORT", str(port))
    env.setdefault("MCC_JEPA_HTTP_URL", url)
    # Safety-first default for runtime stability.
    env.setdefault("MCC_JEPA_HTTP_USE_EMBEDDING_BACKEND", "0")
    try:
        _HTTP_RUNTIME_PROC = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.services.jepa_http_server:app",
                "--host",
                host,
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
    except Exception:
        _HTTP_RUNTIME_PROC = None


def _probe_http_runtime_health(force: bool = False) -> Tuple[bool, str]:
    """
    Lightweight health probe for JEPA HTTP runtime.
    Trigger-based only (no periodic polling).
    """
    url, health_url, enabled = _runtime_urls()
    if not url:
        return False, "http_url_not_configured"

    now = time.monotonic()
    ttl_sec = 2.0
    if (
        not force
        and _HTTP_HEALTH_CACHE.get("url") == health_url
        and (now - float(_HTTP_HEALTH_CACHE.get("ts", 0.0))) <= ttl_sec
    ):
        return bool(_HTTP_HEALTH_CACHE.get("ok")), str(_HTTP_HEALTH_CACHE.get("detail") or "")

    timeout = float(os.environ.get("MCC_JEPA_HTTP_TIMEOUT_SEC") or "2.5")
    try:
        req = urllib.request.Request(url=health_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body) if body else {}
        ok = bool(data.get("ok") is True)
        mode = str(data.get("mode") or "")
        detail = f"{health_url}|{mode}" if mode else health_url
    except Exception as e:
        ok = False
        detail = f"{health_url}|{e.__class__.__name__}"

    _HTTP_HEALTH_CACHE["url"] = health_url
    _HTTP_HEALTH_CACHE["ok"] = ok
    _HTTP_HEALTH_CACHE["detail"] = detail
    _HTTP_HEALTH_CACHE["ts"] = now
    if not enabled and ok:
        detail = f"{detail}|enable_flag_off"
    if enabled and not ok:
        _ensure_http_runtime_started(url)
        # one short retry after local runtime autostart attempt
        try:
            time.sleep(0.25)
            req = urllib.request.Request(url=health_url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body) if body else {}
            ok = bool(data.get("ok") is True)
            mode = str(data.get("mode") or "")
            detail = f"{health_url}|{mode}" if mode else health_url
            _HTTP_HEALTH_CACHE["ok"] = ok
            _HTTP_HEALTH_CACHE["detail"] = detail
            _HTTP_HEALTH_CACHE["ts"] = time.monotonic()
        except Exception:
            pass
    return ok, detail


def runtime_health(force: bool = False) -> Dict[str, Any]:
    """
    Runtime health contract for diagnostics and strict-mode smoke tests.
    """
    url, health_url, enabled = _runtime_urls()
    ok, detail = _probe_http_runtime_health(force=force)
    return {
        "ok": ok,
        "enabled": enabled,
        "embed_url": url,
        "health_url": health_url,
        "detail": detail,
        "backend": str(_RUNTIME_STATUS.get("backend") or "uninitialized"),
        "backend_detail": str(_RUNTIME_STATUS.get("detail") or ""),
    }


def _validate_vectors(raw: Any, rows: int, dim: int) -> List[List[float]]:
    if not isinstance(raw, list):
        raise ValueError("vectors must be list")
    out: List[List[float]] = []
    for row in raw[:rows]:
        if not isinstance(row, list):
            raise ValueError("vector row must be list")
        vec = [float(x) for x in row[:dim]]
        if len(vec) < dim:
            vec += [0.0] * (dim - len(vec))
        out.append(_normalize(vec))
    if len(out) != rows:
        raise ValueError("vector rows mismatch")
    return out


def _try_http_jepa(texts: List[str], dim: int) -> List[List[float]] | None:
    """
    Real JEPA runtime bridge.

    Expected endpoint contract:
    POST {MCC_JEPA_HTTP_URL}
    Body: {"texts":[...], "dim":128}
    Response: {"vectors":[[...], ...], "model":"..."}
    """
    url, _health_url, enabled = _runtime_urls()
    if not url:
        return None

    health_ok, health_detail = _probe_http_runtime_health(force=False)
    if not health_ok:
        _set_runtime_status("jepa_http_unavailable", health_detail or url)
        return None

    timeout = float(os.environ.get("MCC_JEPA_HTTP_TIMEOUT_SEC") or "2.5")
    payload = json.dumps({"texts": texts, "dim": dim}).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body) if body else {}
        vectors = _validate_vectors(data.get("vectors"), rows=len(texts), dim=dim)
        model = str(data.get("model") or "unknown_model")
        _set_runtime_status("jepa_http_runtime", f"{url}|{model}|{health_detail}")
        return vectors
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as e:
        _set_runtime_status("jepa_http_unavailable", f"{url}|{e.__class__.__name__}")
        return None


def _fit_whitening(vectors: List[List[float]]) -> Tuple[List[List[float]], Dict[str, float]]:
    """
    Lightweight whitening + component clipping for runtime robustness.
    """
    if np is None or not vectors:
        return vectors, {"enabled": 0.0}

    X = np.array(vectors, dtype=float)
    if X.ndim != 2 or X.shape[0] < 3 or X.shape[1] < 4:
        return vectors, {"enabled": 0.0}

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
        vals = vals[order]
        vecs = vecs[:, order]
        vals = np.maximum(vals, 1e-9)

        # Keep enough components to preserve ~95% variance, cap for runtime speed.
        total = float(vals.sum())
        if total <= 1e-12:
            return vectors, {"enabled": 0.0}
        cumulative = np.cumsum(vals) / total
        keep = int(np.searchsorted(cumulative, 0.95) + 1)
        keep = max(8, min(keep, min(X.shape[1], 128)))

        proj = vecs[:, :keep]
        scaled = np.diag(1.0 / np.sqrt(vals[:keep] + 1e-6))
        with np.errstate(all="ignore"):
            Xw = Xc @ proj @ scaled
        Xw = np.nan_to_num(Xw, nan=0.0, posinf=0.0, neginf=0.0)
        Xw = np.clip(Xw, -50.0, 50.0)

        out: List[List[float]] = []
        for row in Xw.tolist():
            out.append(_normalize([float(x) for x in row]))
        return out, {"enabled": 1.0, "components": float(keep), "var95": float(cumulative[keep - 1])}
    except Exception:
        return vectors, {"enabled": 0.0}


def embed_texts(texts: List[str], dim: int = 128) -> List[List[float]]:
    """
    Runtime contract for `mcc_jepa_adapter`.
    """
    if not texts:
        return []

    dim = max(16, min(int(dim or 128), 256))
    key = _cache_key(texts, dim)
    cached = _RUNTIME_CACHE.get(key)
    if cached is not None:
        if _RUNTIME_STATUS.get("backend") == "uninitialized":
            _set_runtime_status("cache", "warm")
        return cached

    # 1) Real JEPA runtime (HTTP bridge)
    http_vectors = _try_http_jepa(texts, dim=dim)
    if http_vectors is not None:
        whitened, _stats = _fit_whitening(http_vectors)
        vectors = whitened if whitened and len(whitened) == len(http_vectors) else http_vectors
        _RUNTIME_CACHE[key] = vectors
        return vectors

    # 2) Local embedding service path
    svc = get_embedding_service()
    raw = svc.get_embedding_batch(texts)

    vectors: List[List[float]] = []
    for i, row in enumerate(raw):
        if isinstance(row, list) and row:
            vec = [float(x) for x in row[:dim]]
            if len(vec) < dim:
                vec += [0.0] * (dim - len(vec))
            vectors.append(_normalize(vec))
        else:
            vectors.append(_stable_text_vector(texts[i], dim=dim))

    # Whitening is applied only on sufficiently rich batches.
    whitened, _stats = _fit_whitening(vectors)
    if whitened and len(whitened) == len(vectors):
        vectors = whitened

    _set_runtime_status("local_embedding_runtime", "EmbeddingService batch + whitening")
    _RUNTIME_CACHE[key] = vectors
    if len(_RUNTIME_CACHE) > 64:
        # Simple bounded cache eviction.
        first_key = next(iter(_RUNTIME_CACHE.keys()))
        _RUNTIME_CACHE.pop(first_key, None)
    return vectors


def get_embedding(text: str) -> List[float]:
    rows = embed_texts([text], dim=128)
    return rows[0] if rows else [0.0] * 128
