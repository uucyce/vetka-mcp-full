"""
Phase 157.1 - Context Packer (safe wrapper).

Provides a thin orchestration layer over existing context builders:
- build_pinned_context
- build_viewport_summary
- build_json_context

Adds:
- trace metadata for observability
- optional JEPA semantic-core fallback on overflow pressure
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    try:
        from src.utils.token_utils import estimate_tokens
    except Exception:
        estimate_tokens = lambda t: max(1, len(str(t)) // 4)
    return int(estimate_tokens(text or ""))


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(float(a[i]) * float(b[i]) for i in range(n))
    na = sum(float(a[i]) * float(a[i]) for i in range(n)) ** 0.5
    nb = sum(float(b[i]) * float(b[i]) for i in range(n)) ** 0.5
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(dot / (na * nb))


def _infer_context_window(model_name: str) -> int:
    model = (model_name or "").lower()
    # Safe heuristic for pressure scoring only (not provider limit authority).
    if "gpt-4" in model or "gpt-4o" in model or "claude" in model or "gemini" in model:
        return 128000
    if "grok" in model:
        return 128000
    if "qwen" in model or "llama" in model or "deepseek" in model:
        return 32768
    return 65536


@dataclass
class ContextPackResult:
    pinned_context: str
    viewport_summary: str
    json_context: str
    jepa_context: str
    trace: Dict[str, Any]


class ContextPacker:
    def __init__(self) -> None:
        self.enabled = os.getenv("VETKA_CONTEXT_PACKER_ENABLED", "true").lower() == "true"
        self.jepa_enabled = os.getenv("VETKA_CONTEXT_PACKER_JEPA_ENABLE", "true").lower() == "true"
        self.token_pressure_threshold = float(os.getenv("VETKA_CONTEXT_PACKER_TOKEN_PRESSURE", "0.80"))
        self.docs_threshold = int(os.getenv("VETKA_CONTEXT_PACKER_DOCS_THRESHOLD", "15"))
        self.entropy_threshold = float(os.getenv("VETKA_CONTEXT_PACKER_ENTROPY_THRESHOLD", "2.50"))
        self.modality_threshold = int(os.getenv("VETKA_CONTEXT_PACKER_MODALITY_THRESHOLD", "2"))
        self.hysteresis_on = int(os.getenv("VETKA_CONTEXT_PACKER_HYSTERESIS_ON", "3"))
        self.hysteresis_off = int(os.getenv("VETKA_CONTEXT_PACKER_HYSTERESIS_OFF", "2"))
        self.max_recent = int(os.getenv("VETKA_CONTEXT_PACKER_RECENT_MAX", "200"))
        self._hysteresis_state: Dict[str, Dict[str, int | bool]] = {}
        self._recent_traces: deque[Dict[str, Any]] = deque(maxlen=max(10, self.max_recent))

    def _estimate_entropy(self, chunks: List[str]) -> float:
        # Lightweight proxy entropy on chunk sizes and uniqueness.
        if not chunks:
            return 0.0
        lengths = [max(1, len(c.strip())) for c in chunks if c]
        if not lengths:
            return 0.0
        total = float(sum(lengths))
        probs = [x / total for x in lengths]
        import math
        return float(-sum(p * math.log(p + 1e-12) for p in probs))

    def _detect_modalities(self, pinned_files: List[Dict[str, Any]]) -> int:
        exts = set()
        for pf in pinned_files or []:
            path = str(pf.get("path", "")).lower()
            ext = path.rsplit(".", 1)[-1] if "." in path else ""
            if ext in {"py", "ts", "tsx", "js", "md", "txt", "json", "yaml", "yml", "toml", "rtf"}:
                exts.add("text")
            elif ext in {"mp3", "wav", "m4a", "flac", "ogg"}:
                exts.add("audio")
            elif ext in {"mp4", "mov", "avi", "mkv", "webm"}:
                exts.add("video")
            elif ext in {"png", "jpg", "jpeg", "gif", "webp"}:
                exts.add("image")
            elif ext:
                exts.add("other")
        return len(exts)

    def _should_trigger_jepa(
        self,
        *,
        overflow_risk: bool,
        docs_count: int,
        entropy: float,
        modality_mix: int,
    ) -> bool:
        return (
            overflow_risk
            or docs_count > self.docs_threshold
            or entropy > self.entropy_threshold
            or modality_mix > self.modality_threshold
        )

    def _maybe_build_jepa_context(
        self,
        *,
        trigger: bool,
        user_query: str,
        pinned_files: List[Dict[str, Any]],
        trace: Dict[str, Any],
    ) -> str:
        if not self.jepa_enabled or not trigger:
            return ""

        try:
            from src.services.mcc_jepa_adapter import embed_texts_for_overlay

            texts: List[str] = []
            if user_query:
                texts.append(user_query[:800])
            for pf in (pinned_files or [])[:40]:
                path = str(pf.get("path") or pf.get("name") or "").strip()
                if path:
                    texts.append(path)
            texts = [t for t in texts if t]
            if not texts:
                return ""

            result = embed_texts_for_overlay(texts=texts, target_dim=128)
            trace["jepa_mode"] = True
            trace["jepa_provider_mode"] = result.provider_mode
            trace["jepa_detail"] = result.detail
            trace["jepa_items"] = len(texts)
            return self._build_jepa_semantic_digest(
                texts=texts,
                vectors=getattr(result, "vectors", []) or [],
                provider_mode=result.provider_mode,
                detail=result.detail or "",
                user_query=user_query,
            )
        except Exception as e:
            trace["jepa_mode"] = False
            trace["jepa_error"] = str(e.__class__.__name__)
            logger.debug("[ContextPacker] JEPA fallback unavailable: %s", e)
            return ""

    def _build_jepa_semantic_digest(
        self,
        *,
        texts: List[str],
        vectors: List[List[float]],
        provider_mode: str,
        detail: str,
        user_query: str,
    ) -> str:
        if not texts:
            return ""

        # Fallback for providers that return no vectors.
        if not vectors or len(vectors) != len(texts):
            top_items = [t for t in texts[:6] if t and t != user_query]
            lines = "\n".join(f"  - {x}" for x in top_items)
            return (
                "## JEPA SEMANTIC CORE (overflow fallback)\n"
                f"- provider_mode: {provider_mode}\n"
                f"- items_embedded: {len(texts)}\n"
                "- semantic_focus: fallback(list-only)\n"
                "- representative_items:\n"
                f"{lines}\n\n"
            )

        # Build centroid and rank representative items by centroid similarity.
        n = len(vectors)
        d = len(vectors[0]) if vectors and vectors[0] else 0
        centroid = [0.0] * d
        for vec in vectors:
            for i in range(min(d, len(vec))):
                centroid[i] += float(vec[i])
        if n > 0:
            centroid = [x / n for x in centroid]

        scored = []
        for i, txt in enumerate(texts):
            if not txt:
                continue
            sim = _cosine(vectors[i], centroid)
            scored.append((txt, sim))
        scored.sort(key=lambda x: x[1], reverse=True)

        reps = []
        for txt, _ in scored:
            if txt == user_query:
                continue
            reps.append(txt)
            if len(reps) >= 6:
                break

        # Lightweight focus token extraction (path/word frequency).
        stop = {"the", "and", "for", "with", "from", "that", "this", "file", "docs", "src"}
        token_freq: Dict[str, int] = {}
        for txt in reps:
            raw = (
                txt.lower()
                .replace("\\", "/")
                .replace("_", " ")
                .replace("-", " ")
                .replace(".", " ")
                .replace("/", " ")
            )
            for tok in raw.split():
                if len(tok) < 3 or tok in stop:
                    continue
                token_freq[tok] = token_freq.get(tok, 0) + 1
        focus = [k for k, _ in sorted(token_freq.items(), key=lambda kv: kv[1], reverse=True)[:6]]
        focus_s = ", ".join(focus) if focus else "n/a"
        rep_lines = "\n".join(f"  - {x}" for x in reps) if reps else "  - n/a"

        detail_s = f" ({detail})" if detail else ""
        return (
            "## JEPA SEMANTIC CORE (overflow fallback)\n"
            f"- provider_mode: {provider_mode}{detail_s}\n"
            f"- items_embedded: {len(texts)}\n"
            f"- semantic_focus: {focus_s}\n"
            "- representative_items:\n"
            f"{rep_lines}\n"
            "- usage_hint: keep this core + top critical chunks when truncating long context\n\n"
        )

    def _apply_hysteresis(self, *, session_id: Optional[str], trigger_raw: bool) -> tuple[bool, Dict[str, Any]]:
        key = (session_id or "default").strip() or "default"
        state = self._hysteresis_state.setdefault(
            key,
            {"jepa_active": False, "on_streak": 0, "off_streak": 0},
        )

        if trigger_raw:
            state["on_streak"] = int(state["on_streak"]) + 1
            state["off_streak"] = 0
            if (not bool(state["jepa_active"])) and int(state["on_streak"]) >= max(1, self.hysteresis_on):
                state["jepa_active"] = True
        else:
            state["off_streak"] = int(state["off_streak"]) + 1
            state["on_streak"] = 0
            if bool(state["jepa_active"]) and int(state["off_streak"]) >= max(1, self.hysteresis_off):
                state["jepa_active"] = False

        return bool(state["jepa_active"]), {
            "hysteresis_session": key,
            "hysteresis_on_streak": int(state["on_streak"]),
            "hysteresis_off_streak": int(state["off_streak"]),
            "hysteresis_active": bool(state["jepa_active"]),
            "hysteresis_on_threshold": max(1, self.hysteresis_on),
            "hysteresis_off_threshold": max(1, self.hysteresis_off),
        }

    def get_recent_stats(self, limit: int = 50) -> Dict[str, Any]:
        rows = list(self._recent_traces)[-max(1, int(limit)) :]
        if not rows:
            return {"count": 0, "rows": []}

        pack_ms = [float(r.get("pack_latency_ms", 0.0)) for r in rows]
        jepa_ms = [float(r.get("jepa_latency_ms", 0.0)) for r in rows if float(r.get("jepa_latency_ms", 0.0)) > 0.0]
        jepa_mode = [r for r in rows if r.get("jepa_mode")]
        return {
            "count": len(rows),
            "jepa_mode_count": len(jepa_mode),
            "jepa_mode_ratio": round(len(jepa_mode) / max(1, len(rows)), 4),
            "pack_latency_ms_p50": sorted(pack_ms)[len(pack_ms) // 2],
            "pack_latency_ms_p95": sorted(pack_ms)[int(max(0, len(pack_ms) * 0.95 - 1))],
            "jepa_latency_ms_p50": (sorted(jepa_ms)[len(jepa_ms) // 2] if jepa_ms else 0.0),
            "jepa_latency_ms_p95": (sorted(jepa_ms)[int(max(0, len(jepa_ms) * 0.95 - 1))] if jepa_ms else 0.0),
            "rows": rows,
        }

    async def pack(
        self,
        *,
        user_query: str,
        pinned_files: Optional[List[Dict[str, Any]]],
        viewport_context: Optional[Dict[str, Any]],
        session_id: Optional[str],
        model_name: str,
        user_id: str = "default",
        zoom_level: float = 1.0,
    ) -> ContextPackResult:
        from src.api.handlers.message_utils import (
            build_json_context,
            build_pinned_context,
            build_viewport_summary,
        )

        pinned_files = pinned_files or []
        viewport_context = viewport_context or {}

        # Maintain backward-compatible behavior if disabled.
        if not self.enabled:
            pinned = build_pinned_context(pinned_files, user_query=user_query) if pinned_files else ""
            viewport = build_viewport_summary(viewport_context) if viewport_context else ""
            json_ctx = build_json_context(
                pinned_files,
                viewport_context,
                session_id=session_id,
                model_name=model_name,
            )
            return ContextPackResult(
                pinned_context=pinned,
                viewport_summary=viewport,
                json_context=json_ctx,
                jepa_context="",
                trace={"packing_path": "legacy", "packer_enabled": False},
            )

        t0 = time.perf_counter()
        pinned = (
            build_pinned_context(
                pinned_files,
                user_query=user_query,
                viewport_context=viewport_context,
                user_id=user_id,
                zoom_level=zoom_level,
                model_name=model_name,
            )
            if pinned_files
            else ""
        )
        viewport = build_viewport_summary(viewport_context) if viewport_context else ""
        json_ctx = build_json_context(
            pinned_files,
            viewport_context,
            session_id=session_id,
            model_name=model_name,
        )

        combined = f"{json_ctx}\n{pinned}\n{viewport}\n{user_query or ''}"
        raw_tokens = _estimate_tokens(combined)
        context_window = _infer_context_window(model_name)
        token_pressure = (raw_tokens / max(1, context_window))
        docs_count = len(pinned_files)
        modality_mix = self._detect_modalities(pinned_files)
        entropy = self._estimate_entropy([json_ctx, pinned, viewport, user_query or ""])
        overflow_risk = token_pressure > self.token_pressure_threshold

        trigger_raw = self._should_trigger_jepa(
            overflow_risk=overflow_risk,
            docs_count=docs_count,
            entropy=entropy,
            modality_mix=modality_mix,
        )
        trigger, hysteresis_trace = self._apply_hysteresis(session_id=session_id, trigger_raw=trigger_raw)

        trace: Dict[str, Any] = {
            "packing_path": "algorithmic",
            "packer_enabled": True,
            "memory_layers_used": ["CAM", "MGC", "ENGRAM", "HOPE", "ELISION", "ELISYA"],
            "raw_tokens_est": raw_tokens,
            "context_window_est": context_window,
            "token_pressure": round(token_pressure, 4),
            "overflow_risk": overflow_risk,
            "docs_count": docs_count,
            "modality_mix": modality_mix,
            "entropy": round(entropy, 4),
            "jepa_trigger_raw": trigger_raw,
            "jepa_trigger": trigger,
            "jepa_mode": False,
        }
        trace.update(hysteresis_trace)

        tj = time.perf_counter()
        jepa_ctx = self._maybe_build_jepa_context(
            trigger=trigger,
            user_query=user_query,
            pinned_files=pinned_files,
            trace=trace,
        )
        trace["jepa_latency_ms"] = round((time.perf_counter() - tj) * 1000.0, 2) if trigger else 0.0
        if jepa_ctx:
            trace["packing_path"] = "hybrid-jepa"
        trace["pack_latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        self._recent_traces.append(dict(trace))

        logger.info("[ContextPacker] %s", trace)
        return ContextPackResult(
            pinned_context=pinned,
            viewport_summary=viewport,
            json_context=json_ctx,
            jepa_context=jepa_ctx,
            trace=trace,
        )


_context_packer_singleton: Optional[ContextPacker] = None


def get_context_packer() -> ContextPacker:
    global _context_packer_singleton
    if _context_packer_singleton is None:
        _context_packer_singleton = ContextPacker()
    return _context_packer_singleton
