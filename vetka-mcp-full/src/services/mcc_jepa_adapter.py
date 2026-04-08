"""
MARKER_155.P3_1.JEPA_ADAPTER.V1

Runtime adapter layer for MCC predictive overlay.

Provider policy:
1) runtime module provider (if configured and available)
2) embedding_service provider
3) deterministic fallback provider
"""

from __future__ import annotations

import hashlib
import importlib
import math
import os
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


class JepaRuntimeUnavailableError(RuntimeError):
    """Raised when strict JEPA runtime mode is requested but not available."""


@dataclass
class JepaAdapterResult:
    vectors: List[List[float]]
    provider_mode: str
    detail: str = ""


def _normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 1e-12:
        return vec
    return [x / norm for x in vec]


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


def _build_deterministic_vectors(texts: List[str], dim: int = 128) -> List[List[float]]:
    return [_stable_text_vector(t, dim=dim) for t in texts]


def _is_strict_true_runtime(result: JepaAdapterResult) -> bool:
    """
    Strict runtime requires real JEPA runtime backend, not local surrogate.
    """
    if result.provider_mode != "jepa_runtime_module":
        return False
    detail = (result.detail or "").lower()
    return "|jepa_http_runtime" in detail


def _try_runtime_module(
    module_path: str,
    texts: List[str],
    target_dim: int = 128,
) -> Optional[JepaAdapterResult]:
    """
    Runtime module contract (soft):
    - embed_texts(texts: List[str], dim: int) -> List[List[float]]
      OR
    - get_embedding(text: str) -> List[float]
    """
    try:
        mod = importlib.import_module(module_path)
    except Exception:
        return None

    vectors: List[List[float]] = []
    embed_texts: Optional[Callable[..., List[List[float]]]] = getattr(mod, "embed_texts", None)
    get_embedding: Optional[Callable[..., List[float]]] = getattr(mod, "get_embedding", None)

    if callable(embed_texts):
        try:
            raw = embed_texts(texts, target_dim)  # type: ignore[misc]
            if isinstance(raw, list) and raw:
                for row in raw[: len(texts)]:
                    if isinstance(row, list) and row:
                        vec = [float(x) for x in row[:target_dim]]
                        if len(vec) < target_dim:
                            vec += [0.0] * (target_dim - len(vec))
                        vectors.append(_normalize(vec))
            if len(vectors) == len(texts):
                detail = module_path
                get_status = getattr(mod, "get_runtime_status", None)
                if callable(get_status):
                    try:
                        status = get_status()  # type: ignore[misc]
                        if isinstance(status, dict):
                            backend = str(status.get("backend") or "").strip()
                            extra = str(status.get("detail") or "").strip()
                            detail = f"{module_path}|{backend}" + (f"|{extra}" if extra else "")
                    except Exception:
                        pass
                return JepaAdapterResult(vectors=vectors, provider_mode="jepa_runtime_module", detail=detail)
        except Exception:
            vectors = []

    if callable(get_embedding):
        try:
            for t in texts:
                row = get_embedding(t)  # type: ignore[misc]
                vec = [float(x) for x in (row or [])[:target_dim]]
                if len(vec) < target_dim:
                    vec += [0.0] * (target_dim - len(vec))
                vectors.append(_normalize(vec))
            if len(vectors) == len(texts):
                detail = f"{module_path}.get_embedding"
                get_status = getattr(mod, "get_runtime_status", None)
                if callable(get_status):
                    try:
                        status = get_status()  # type: ignore[misc]
                        if isinstance(status, dict):
                            backend = str(status.get("backend") or "").strip()
                            extra = str(status.get("detail") or "").strip()
                            detail = f"{module_path}|{backend}" + (f"|{extra}" if extra else "")
                    except Exception:
                        pass
                return JepaAdapterResult(vectors=vectors, provider_mode="jepa_runtime_module", detail=detail)
        except Exception:
            return None
    return None


def _try_embedding_service(texts: List[str], target_dim: int = 128) -> Optional[JepaAdapterResult]:
    try:
        from src.utils.embedding_service import get_embedding  # type: ignore
    except Exception:
        return None

    vectors: List[List[float]] = []
    try:
        for t in texts:
            row = get_embedding(t)
            if not isinstance(row, list) or not row:
                return None
            vec = [float(x) for x in row[:target_dim]]
            if len(vec) < target_dim:
                vec += [0.0] * (target_dim - len(vec))
            vectors.append(_normalize(vec))
    except Exception:
        return None
    return JepaAdapterResult(vectors=vectors, provider_mode="embedding_service")


def embed_texts_for_overlay(
    texts: List[str],
    target_dim: int = 128,
    provider_override: str | None = None,
    runtime_module_override: str | None = None,
    strict_runtime: bool = False,
) -> JepaAdapterResult:
    """
    Resolve JEPA provider for overlay.

    Env flags:
    - MCC_JEPA_PROVIDER: auto | runtime | embedding | deterministic
    - MCC_JEPA_RUNTIME_MODULE: python module path for runtime provider
    """
    provider = (provider_override or os.environ.get("MCC_JEPA_PROVIDER") or "auto").strip().lower()
    runtime_module = (
        runtime_module_override
        or os.environ.get("MCC_JEPA_RUNTIME_MODULE")
        or "src.services.jepa_runtime"
    ).strip()

    if provider in ("runtime", "auto"):
        runtime_result = _try_runtime_module(runtime_module, texts, target_dim=target_dim)
        if runtime_result is not None:
            if strict_runtime and provider == "runtime" and not _is_strict_true_runtime(runtime_result):
                backend_detail = runtime_result.detail or runtime_module
                raise JepaRuntimeUnavailableError(
                    f"strict runtime requested but true JEPA runtime backend is unavailable: {backend_detail}"
                )
            return runtime_result
        if strict_runtime and provider == "runtime":
            raise JepaRuntimeUnavailableError(
                f"strict runtime requested but runtime module unavailable: {runtime_module}"
            )
        if provider == "runtime":
            return JepaAdapterResult(
                vectors=_build_deterministic_vectors(texts, dim=target_dim),
                provider_mode="deterministic_fallback",
                detail=f"runtime module unavailable: {runtime_module}",
            )

    if provider in ("embedding", "auto"):
        emb_result = _try_embedding_service(texts, target_dim=target_dim)
        if emb_result is not None:
            return emb_result
        if provider == "embedding":
            return JepaAdapterResult(
                vectors=_build_deterministic_vectors(texts, dim=target_dim),
                provider_mode="deterministic_fallback",
                detail="embedding_service unavailable",
            )

    return JepaAdapterResult(
        vectors=_build_deterministic_vectors(texts, dim=target_dim),
        provider_mode="deterministic_fallback",
        detail="explicit deterministic mode or all providers unavailable",
    )
