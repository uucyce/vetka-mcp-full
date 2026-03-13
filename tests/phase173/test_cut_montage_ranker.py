"""
MARKER_173.5 — Montage Decision Ranking Engine tests.

Tests:
- Signal weighting correctness
- Recency decay function
- Intent weight mapping
- Marker → signals extraction
- Decision → signals extraction
- Ranking order (descending by score)
- Edge cases: empty markers, all low confidence, pinned boost
- GET /montage/suggestions endpoint
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.cut_montage_ranker import (
    MontageRanker,
    MontageSignals,
    ScoredClip,
    DEFAULT_WEIGHTS,
    INTENT_WEIGHTS,
)


class TestMontageSignals:
    def test_default_values(self):
        s = MontageSignals()
        assert s.transcript_confidence == 0.0
        assert s.energy_confidence == 0.0
        assert s.editorial_intent == "unknown"
        assert s.is_pinned is False


class TestRecencyDecay:
    def test_no_age_no_penalty(self):
        ranker = MontageRanker()
        now = time.time()
        decay = ranker._compute_recency_decay(now, now)
        assert abs(decay - 1.0) < 0.01

    def test_half_life_halves_score(self):
        ranker = MontageRanker(recency_half_life=3600)  # 1 hour
        now = time.time()
        decay = ranker._compute_recency_decay(now - 3600, now)
        assert abs(decay - 0.5) < 0.01

    def test_double_half_life(self):
        ranker = MontageRanker(recency_half_life=3600)
        now = time.time()
        decay = ranker._compute_recency_decay(now - 7200, now)
        assert abs(decay - 0.25) < 0.01

    def test_zero_created_at_no_penalty(self):
        ranker = MontageRanker()
        assert ranker._compute_recency_decay(0, time.time()) == 1.0

    def test_zero_half_life_no_penalty(self):
        ranker = MontageRanker(recency_half_life=0)
        assert ranker._compute_recency_decay(1000, 2000) == 1.0


class TestIntentWeighting:
    def test_known_intents(self):
        ranker = MontageRanker()
        assert ranker._compute_intent_weight("dialogue_anchor") == 1.0
        assert ranker._compute_intent_weight("accent_cut") == 0.9
        assert ranker._compute_intent_weight("auto_scene") == 0.5

    def test_unknown_intent(self):
        ranker = MontageRanker()
        assert ranker._compute_intent_weight("totally_unknown") == 0.4


class TestScoreClip:
    def test_all_zeros(self):
        ranker = MontageRanker()
        signals = MontageSignals()
        result = ranker.score_clip(signals)
        # Only intent weight contributes (0.10 * 0.4 = 0.04)
        assert result.score < 0.1
        assert result.confidence < 0.1

    def test_perfect_signals(self):
        ranker = MontageRanker()
        signals = MontageSignals(
            transcript_confidence=1.0,
            energy_confidence=1.0,
            sync_confidence=1.0,
            marker_score=1.0,
            editorial_intent="dialogue_anchor",
            created_at=time.time(),
        )
        result = ranker.score_clip(signals)
        assert result.score > 0.9
        assert result.confidence > 0.9

    def test_pinned_boost(self):
        ranker = MontageRanker()
        signals_normal = MontageSignals(
            transcript_confidence=0.5,
            marker_score=0.5,
            created_at=time.time(),
        )
        signals_pinned = MontageSignals(
            transcript_confidence=0.5,
            marker_score=0.5,
            created_at=time.time(),
            is_pinned=True,
        )
        normal = ranker.score_clip(signals_normal)
        pinned = ranker.score_clip(signals_pinned)
        assert pinned.score > normal.score
        assert "pinned" in pinned.reasoning

    def test_score_clamped_to_1(self):
        ranker = MontageRanker()
        signals = MontageSignals(
            transcript_confidence=1.0,
            energy_confidence=1.0,
            sync_confidence=1.0,
            marker_score=1.0,
            editorial_intent="dialogue_anchor",
            created_at=time.time(),
            is_pinned=True,
        )
        result = ranker.score_clip(signals)
        assert result.score <= 1.0

    def test_reasoning_string(self):
        ranker = MontageRanker()
        signals = MontageSignals(
            transcript_confidence=0.88,
            energy_confidence=0.82,
            editorial_intent="accent_cut",
        )
        result = ranker.score_clip(signals)
        assert "transcript:0.88" in result.reasoning
        assert "energy:0.82" in result.reasoning
        assert "intent(accent_cut)" in result.reasoning


class TestRankClips:
    def test_empty_markers(self):
        ranker = MontageRanker()
        assert ranker.rank_clips([]) == []

    def test_single_marker(self):
        ranker = MontageRanker()
        markers = [{"marker_id": "m1", "score": 0.8, "kind": "favorite", "start_sec": 5.0, "end_sec": 8.0}]
        results = ranker.rank_clips(markers)
        assert len(results) == 1
        assert results[0].marker_id == "m1"
        assert results[0].score > 0

    def test_ranking_order_descending(self):
        ranker = MontageRanker()
        markers = [
            {"marker_id": "low", "score": 0.2, "kind": "comment", "start_sec": 0, "end_sec": 1},
            {"marker_id": "high", "score": 0.9, "kind": "favorite", "start_sec": 5, "end_sec": 8},
            {"marker_id": "mid", "score": 0.5, "kind": "cam", "start_sec": 10, "end_sec": 12},
        ]
        results = ranker.rank_clips(markers)
        assert results[0].marker_id == "high"
        assert results[-1].marker_id == "low"
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_limit_respected(self):
        ranker = MontageRanker()
        markers = [{"marker_id": f"m{i}", "score": 0.5, "kind": "cam"} for i in range(20)]
        results = ranker.rank_clips(markers, limit=5)
        assert len(results) <= 5

    def test_min_score_filter(self):
        ranker = MontageRanker(min_score=0.1)
        markers = [
            {"marker_id": "high", "score": 0.9, "kind": "favorite",
             "context_slice": {"transcript_confidence": 0.9, "energy_confidence": 0.8}},
            {"marker_id": "low", "score": 0.0, "kind": "unknown"},
        ]
        results = ranker.rank_clips(markers)
        # "high" has strong signals → should pass; "low" has weak → may be filtered
        ids = [r.marker_id for r in results]
        assert "high" in ids
        # "low" gets only intent(unknown)=0.04, should be below 0.1
        assert "low" not in ids

    def test_decisions_included(self):
        ranker = MontageRanker()
        markers = [{"marker_id": "m1", "score": 0.5, "kind": "favorite"}]
        decisions = [{"decision_id": "d1", "score": 0.7, "editorial_intent": "dialogue_anchor", "start_sec": 3.0, "end_sec": 6.0}]
        results = ranker.rank_clips(markers, decisions)
        ids = [r.clip_id for r in results]
        assert "d1" in ids

    def test_context_slice_extraction(self):
        ranker = MontageRanker()
        markers = [{
            "marker_id": "m1",
            "score": 0.7,
            "kind": "chat",
            "context_slice": {
                "transcript_confidence": 0.88,
                "energy_confidence": 0.82,
                "sync_confidence": 0.75,
            },
        }]
        results = ranker.rank_clips(markers)
        assert len(results) == 1
        signals = results[0].source_signals
        assert signals["transcript_confidence"] == 0.88
        assert signals["energy_confidence"] == 0.82
        assert signals["sync_confidence"] == 0.75


class TestMontageEndpoint:
    """Test GET /montage/suggestions via TestClient."""

    def _get_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.routes.cut_routes import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @patch("src.api.routes.cut_routes.CutProjectStore")
    def test_suggestions_basic(self, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = {"project_id": "proj_1"}
        instance.load_time_marker_bundle.return_value = {
            "markers": [
                {"marker_id": "m1", "score": 0.8, "kind": "favorite", "start_sec": 5.0, "end_sec": 8.0},
                {"marker_id": "m2", "score": 0.3, "kind": "comment", "start_sec": 10.0, "end_sec": 12.0},
            ]
        }
        instance.load_montage_state.return_value = None
        MockStore.return_value = instance

        client = self._get_client()
        resp = client.get("/api/cut/montage/suggestions", params={
            "sandbox_root": "/tmp/test",
            "project_id": "proj_1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["total"] == 2
        assert data["marker_count"] == 2
        # Higher score first
        assert data["suggestions"][0]["score"] >= data["suggestions"][1]["score"]

    @patch("src.api.routes.cut_routes.CutProjectStore")
    def test_suggestions_empty(self, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = {"project_id": "proj_1"}
        instance.load_time_marker_bundle.return_value = {"markers": []}
        instance.load_montage_state.return_value = None
        MockStore.return_value = instance

        client = self._get_client()
        resp = client.get("/api/cut/montage/suggestions", params={
            "sandbox_root": "/tmp/test",
            "project_id": "proj_1",
        })
        data = resp.json()
        assert data["success"] is True
        assert data["total"] == 0

    @patch("src.api.routes.cut_routes.CutProjectStore")
    def test_project_not_found(self, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = None
        MockStore.return_value = instance

        client = self._get_client()
        resp = client.get("/api/cut/montage/suggestions", params={
            "sandbox_root": "/tmp/test",
            "project_id": "proj_1",
        })
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "project_not_found"

    @patch("src.api.routes.cut_routes.CutProjectStore")
    def test_limit_param(self, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = {"project_id": "proj_1"}
        instance.load_time_marker_bundle.return_value = {
            "markers": [{"marker_id": f"m{i}", "score": 0.5, "kind": "cam"} for i in range(20)]
        }
        instance.load_montage_state.return_value = None
        MockStore.return_value = instance

        client = self._get_client()
        resp = client.get("/api/cut/montage/suggestions", params={
            "sandbox_root": "/tmp/test",
            "project_id": "proj_1",
            "limit": 3,
        })
        data = resp.json()
        assert data["total"] <= 3
