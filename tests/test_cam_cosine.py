"""
MARKER_200.CAM_COSINE: Test CAM surprise cosine path in ReflexContext.from_session().

Verifies:
1. Cosine path fires when stored embedding exists + embed succeeds -> cam_surprise != 0
2. Embedding is persisted to cam_last_task.json after session
3. Jaccard fallback works when embedding raises an exception
4. Jaccard fallback works when no stored embedding exists
"""

import json
import math
import pytest
from dataclasses import dataclass
from typing import List


@dataclass
class MockJepaResult:
    """Mock JepaAdapterResult."""
    vectors: List[List[float]]
    provider_mode: str
    detail: str = ""


_VEC_A = [0.1] * 128
_VEC_B = [0.9] * 64 + [-0.9] * 64  # very different from _VEC_A


def _cosine_distance(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - dot / (norm_a * norm_b)))


def _minimal_session_data(task_text="Fix the task board"):
    return {
        "current_phase": {"number": 200, "subphase": "10"},
        "task_board_summary": {"top_pending": [{"title": task_text}]},
        "user_preferences": {"has_preferences": False},
    }


def _call_from_session(tmp_path, monkeypatch, task_text, mock_embed_fn=None):
    """Helper: call ReflexContext.from_session with cam path redirected to tmp_path."""
    import src.services.reflex_scorer as scorer_mod

    if mock_embed_fn is not None:
        monkeypatch.setattr(
            "src.services.mcc_jepa_adapter.embed_texts_for_overlay",
            mock_embed_fn,
        )

    # Redirect _cam_project_root by patching __file__
    (tmp_path / "src" / "services").mkdir(parents=True, exist_ok=True)
    fake_file = str(tmp_path / "src" / "services" / "reflex_scorer.py")
    original_file = scorer_mod.__file__
    scorer_mod.__file__ = fake_file
    try:
        ctx = scorer_mod.ReflexContext.from_session(
            _minimal_session_data(task_text),
            task_text=task_text,
        )
    finally:
        scorer_mod.__file__ = original_file
    return ctx


class TestCAMCosine:

    def test_cosine_path_produces_nonzero_surprise(self, tmp_path, monkeypatch):
        """Stored embedding + successful embed -> cosine-based cam_surprise."""
        cam_file = tmp_path / "data" / "cam_last_task.json"
        cam_file.parent.mkdir(parents=True, exist_ok=True)
        cam_file.write_text(json.dumps({
            "task_text": "Deploy the multicam sync pipeline",
            "embedding": _VEC_B,
        }))

        def mock_embed(texts, target_dim=128, **kwargs):
            return MockJepaResult(vectors=[_VEC_A], provider_mode="test")

        ctx = _call_from_session(
            tmp_path, monkeypatch,
            task_text="Fix the task board deduplication bug",
            mock_embed_fn=mock_embed,
        )

        expected = round(_cosine_distance(_VEC_A, _VEC_B), 4)
        assert ctx.cam_surprise > 0, f"Expected nonzero cam_surprise, got {ctx.cam_surprise}"
        assert ctx.cam_surprise == expected, (
            f"Expected cosine distance {expected}, got {ctx.cam_surprise}"
        )

    def test_embedding_persisted_after_session(self, tmp_path, monkeypatch):
        """After from_session, cam_last_task.json contains 'embedding' key."""
        cam_file = tmp_path / "data" / "cam_last_task.json"
        # No previous file

        def mock_embed(texts, target_dim=128, **kwargs):
            return MockJepaResult(vectors=[_VEC_A], provider_mode="test")

        _call_from_session(
            tmp_path, monkeypatch,
            task_text="Audit the parallax pipeline",
            mock_embed_fn=mock_embed,
        )

        assert cam_file.exists(), "cam_last_task.json should be created"
        saved = json.loads(cam_file.read_text())
        assert "embedding" in saved, "Expected 'embedding' key in persisted data"
        assert saved["embedding"] == _VEC_A
        assert saved["task_text"] == "Audit the parallax pipeline"

    def test_jaccard_fallback_on_embed_failure(self, tmp_path, monkeypatch):
        """embed raises -> falls back to Jaccard word overlap."""
        cam_file = tmp_path / "data" / "cam_last_task.json"
        cam_file.parent.mkdir(parents=True, exist_ok=True)
        cam_file.write_text(json.dumps({
            "task_text": "alpha beta gamma delta epsilon",
            "embedding": _VEC_B,  # has embedding but embed will fail
        }))

        def mock_embed_raises(texts, target_dim=128, **kwargs):
            raise RuntimeError("Ollama unavailable")

        ctx = _call_from_session(
            tmp_path, monkeypatch,
            task_text="zeta theta iota kappa lambda",
            mock_embed_fn=mock_embed_raises,
        )

        # Disjoint words -> Jaccard surprise = 1.0
        assert ctx.cam_surprise > 0.5, (
            f"Jaccard fallback should give high surprise, got {ctx.cam_surprise}"
        )

    def test_jaccard_when_no_stored_embedding(self, tmp_path, monkeypatch):
        """No embedding in cam_last_task.json -> Jaccard path directly."""
        cam_file = tmp_path / "data" / "cam_last_task.json"
        cam_file.parent.mkdir(parents=True, exist_ok=True)
        cam_file.write_text(json.dumps({
            "task_text": "fix render pipeline audio sync",
            # No 'embedding' key
        }))

        call_count = {"n": 0}

        def mock_embed(texts, target_dim=128, **kwargs):
            call_count["n"] += 1
            return MockJepaResult(vectors=[_VEC_A], provider_mode="test")

        ctx = _call_from_session(
            tmp_path, monkeypatch,
            task_text="deploy multicam sync to production",
            mock_embed_fn=mock_embed,
        )

        assert ctx.cam_surprise > 0, "Jaccard should give nonzero for different text"
        # embed IS called for the persist step (saving embedding for next session)
        assert call_count["n"] >= 1, "embed called for persist step"
