"""
MARKER_173.5 — Montage Decision Ranking Engine.

Scores cues from all sources (transcript, pause, music, scene, manual)
using weighted signal fusion. Pure math — no LLM, <5ms execution.

Architecture mirrors ReflexScorer (Phase 172.P2):
- Multiple input signals → weighted fusion → ranked output
- Each signal produces 0.0–1.0 score
- Final score = weighted sum × recency_decay × user_boost

Signals:
  1. transcript_confidence (0.30) — pause detection from transcript
  2. energy_confidence   (0.25) — energy-based pause detection
  3. sync_confidence     (0.20) — audio sync quality
  4. marker_score        (0.15) — user-assigned or auto-scored marker
  5. intent_weight       (0.10) — editorial intent importance

Usage:
    from src.services.cut_montage_ranker import MontageRanker

    ranker = MontageRanker()
    suggestions = ranker.rank_clips(markers, decisions, now=time.time())
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


# ── Signal weights ────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "transcript_confidence": 0.30,
    "energy_confidence": 0.25,
    "sync_confidence": 0.20,
    "marker_score": 0.15,
    "intent_weight": 0.10,
}

# ── Editorial intent importance (higher = more important) ─

INTENT_WEIGHTS: dict[str, float] = {
    "dialogue_anchor": 1.0,
    "accent_cut": 0.9,
    "insight_emphasis": 0.85,
    "camera_emphasis": 0.75,
    "commentary_hold": 0.7,
    "music_sync": 0.65,
    "auto_scene": 0.5,
    "unknown": 0.4,
}

# ── Recency decay: half-life in seconds (24 hours) ──────

RECENCY_HALF_LIFE_SEC = 86400.0  # 24h


@dataclass
class MontageSignals:
    """Input signals for scoring a single clip/cue."""
    transcript_confidence: float = 0.0  # 0.0–1.0
    energy_confidence: float = 0.0      # 0.0–1.0
    sync_confidence: float = 0.0        # 0.0–1.0
    marker_score: float = 0.0           # 0.0–1.0
    editorial_intent: str = "unknown"
    created_at: float = 0.0             # epoch seconds
    is_pinned: bool = False             # user pinned this cue


@dataclass
class ScoredClip:
    """Ranked output for a single montage suggestion."""
    clip_id: str = ""
    source_path: str = ""
    start_sec: float = 0.0
    end_sec: float = 0.0
    duration_sec: float = 0.0
    score: float = 0.0           # final composite 0.0–1.0
    confidence: float = 0.0      # weighted confidence (before decay)
    editorial_intent: str = ""
    reasoning: str = ""          # human-readable breakdown
    source_signals: dict[str, float] = field(default_factory=dict)
    marker_id: str = ""          # source marker/decision id


class MontageRanker:
    """
    Weighted signal fusion ranker for montage clip suggestions.

    Pure math, no LLM. Mirrors ReflexScorer architecture.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        intent_weights: dict[str, float] | None = None,
        recency_half_life: float = RECENCY_HALF_LIFE_SEC,
        min_score: float = 0.05,
    ) -> None:
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.intent_weights = intent_weights or dict(INTENT_WEIGHTS)
        self.recency_half_life = recency_half_life
        self.min_score = min_score

    def _compute_recency_decay(self, created_at: float, now: float) -> float:
        """Exponential decay based on age. Returns 0.0–1.0."""
        if created_at <= 0 or now <= 0:
            return 1.0  # no time info → no penalty
        age_sec = max(0.0, now - created_at)
        if self.recency_half_life <= 0:
            return 1.0
        # Exponential decay: 0.5^(age / half_life)
        return math.pow(0.5, age_sec / self.recency_half_life)

    def _compute_intent_weight(self, intent: str) -> float:
        """Map editorial intent to 0.0–1.0 importance score."""
        return self.intent_weights.get(intent, self.intent_weights.get("unknown", 0.4))

    def score_clip(self, signals: MontageSignals, now: float = 0.0) -> ScoredClip:
        """Score a single clip from its signals. Returns ScoredClip."""
        if now <= 0:
            now = time.time()

        # Clamp all signals to [0, 1]
        tc = max(0.0, min(1.0, signals.transcript_confidence))
        ec = max(0.0, min(1.0, signals.energy_confidence))
        sc = max(0.0, min(1.0, signals.sync_confidence))
        ms = max(0.0, min(1.0, signals.marker_score))
        iw = self._compute_intent_weight(signals.editorial_intent)

        # Weighted confidence (before decay)
        w = self.weights
        confidence = (
            w.get("transcript_confidence", 0.30) * tc
            + w.get("energy_confidence", 0.25) * ec
            + w.get("sync_confidence", 0.20) * sc
            + w.get("marker_score", 0.15) * ms
            + w.get("intent_weight", 0.10) * iw
        )

        # Recency decay
        recency = self._compute_recency_decay(signals.created_at, now)

        # User boost for pinned cues
        user_boost = 1.2 if signals.is_pinned else 1.0

        # Final score
        final = min(1.0, confidence * recency * user_boost)

        # Reasoning string
        parts = []
        if tc > 0:
            parts.append(f"transcript:{tc:.2f}")
        if ec > 0:
            parts.append(f"energy:{ec:.2f}")
        if sc > 0:
            parts.append(f"sync:{sc:.2f}")
        if ms > 0:
            parts.append(f"marker:{ms:.2f}")
        parts.append(f"intent({signals.editorial_intent}):{iw:.2f}")
        if recency < 0.99:
            parts.append(f"recency:{recency:.2f}")
        if signals.is_pinned:
            parts.append("pinned:+20%")
        reasoning = ", ".join(parts)

        return ScoredClip(
            score=round(final, 4),
            confidence=round(confidence, 4),
            editorial_intent=signals.editorial_intent,
            reasoning=reasoning,
            source_signals={
                "transcript_confidence": round(tc, 4),
                "energy_confidence": round(ec, 4),
                "sync_confidence": round(sc, 4),
                "marker_score": round(ms, 4),
                "intent_weight": round(iw, 4),
                "recency_decay": round(recency, 4),
            },
        )

    def rank_clips(
        self,
        markers: list[dict[str, Any]],
        decisions: list[dict[str, Any]] | None = None,
        *,
        now: float = 0.0,
        limit: int = 10,
    ) -> list[ScoredClip]:
        """
        Rank all clips/cues from markers and existing decisions.

        Args:
            markers: Time marker bundle entries with score, confidence, kind
            decisions: Existing montage decisions (optional, for re-ranking)
            now: Current time (epoch), defaults to time.time()
            limit: Max results to return

        Returns:
            Sorted list of ScoredClip (descending by score)
        """
        if now <= 0:
            now = time.time()

        scored: list[ScoredClip] = []

        # ── Score markers ────────────────────────────────
        for marker in markers:
            signals = self._signals_from_marker(marker)
            clip = self.score_clip(signals, now=now)
            clip.clip_id = str(marker.get("clip_id") or marker.get("marker_id") or "")
            clip.marker_id = str(marker.get("marker_id") or marker.get("id") or "")
            clip.source_path = str(marker.get("source_path") or marker.get("media_path") or "")
            clip.start_sec = float(marker.get("start_sec") or marker.get("anchor_sec") or 0)
            clip.end_sec = float(marker.get("end_sec") or (clip.start_sec + float(marker.get("duration_sec") or 0)))
            clip.duration_sec = clip.end_sec - clip.start_sec
            if clip.score >= self.min_score:
                scored.append(clip)

        # ── Score existing decisions ─────────────────────
        for dec in (decisions or []):
            signals = self._signals_from_decision(dec)
            clip = self.score_clip(signals, now=now)
            clip.clip_id = str(dec.get("clip_id") or dec.get("decision_id") or "")
            clip.source_path = str(dec.get("source_path") or "")
            clip.start_sec = float(dec.get("start_sec") or dec.get("anchor_sec") or 0)
            clip.end_sec = float(dec.get("end_sec") or 0)
            clip.duration_sec = clip.end_sec - clip.start_sec
            if clip.score >= self.min_score:
                scored.append(clip)

        # Sort descending by score
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:limit]

    def _signals_from_marker(self, marker: dict[str, Any]) -> MontageSignals:
        """Extract MontageSignals from a time marker dict."""
        score = float(marker.get("score") or 0.0)
        confidence = float(marker.get("confidence") or 0.0)
        kind = str(marker.get("kind") or "unknown")

        # Map marker kind → editorial intent
        intent_map = {
            "favorite": "accent_cut",
            "comment": "commentary_hold",
            "cam": "camera_emphasis",
            "insight": "insight_emphasis",
            "chat": "dialogue_anchor",
            "music_sync": "music_sync",
            "scene": "auto_scene",
        }
        editorial_intent = intent_map.get(kind, "unknown")

        # Extract source-specific confidences from context_slice
        ctx = marker.get("context_slice") or {}
        tc = float(ctx.get("transcript_confidence") or 0.0)
        ec = float(ctx.get("energy_confidence") or 0.0)
        sc = float(ctx.get("sync_confidence") or 0.0)

        # Fall back: use marker.confidence as transcript conf if not specified
        if tc == 0 and confidence > 0:
            tc = confidence

        created_at = 0.0
        if marker.get("created_at"):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(str(marker["created_at"]).replace("Z", "+00:00"))
                created_at = dt.timestamp()
            except (ValueError, TypeError):
                pass

        return MontageSignals(
            transcript_confidence=tc,
            energy_confidence=ec,
            sync_confidence=sc,
            marker_score=score,
            editorial_intent=editorial_intent,
            created_at=created_at,
            is_pinned=bool(marker.get("is_pinned") or marker.get("pinned")),
        )

    def _signals_from_decision(self, dec: dict[str, Any]) -> MontageSignals:
        """Extract MontageSignals from an existing montage decision dict."""
        return MontageSignals(
            transcript_confidence=float(dec.get("transcript_confidence") or dec.get("confidence") or 0.0),
            energy_confidence=float(dec.get("energy_confidence") or 0.0),
            sync_confidence=float(dec.get("sync_confidence") or 0.0),
            marker_score=float(dec.get("score") or 0.0),
            editorial_intent=str(dec.get("editorial_intent") or "unknown"),
            created_at=float(dec.get("created_at_epoch") or 0.0),
            is_pinned=bool(dec.get("is_pinned")),
        )
