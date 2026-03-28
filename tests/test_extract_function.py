"""
Tests for AST function extraction utility.

Verifies completion contract:
1. extract_function works for _apply_timeline_ops
2. extract_function works for _decode_vlog (pure numpy, replaces _kelvin_to_rgb_adjustment)
3. No fastapi/pydantic import needed
4. Demonstrates usage pattern for existing test files
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np

from tests.test_utils.extract_function import extract_function, extract_functions


# ---------------------------------------------------------------------------
# Contract 1: _apply_timeline_ops from cut_routes.py
# ---------------------------------------------------------------------------

class TestApplyTimelineOps:
    @pytest.fixture
    def apply_ops(self):
        return extract_function(
            "src/api/routes/cut_routes.py",
            "_apply_timeline_ops",
        )

    @pytest.fixture
    def state(self):
        return {
            "schema_version": "cut_timeline_state_v1",
            "project_id": "test",
            "timeline_id": "main",
            "revision": 1,
            "fps": 25,
            "lanes": [
                {
                    "lane_id": "v1",
                    "lane_type": "video_main",
                    "clips": [
                        {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
                        {"clip_id": "B", "source_path": "/b.mp4", "start_sec": 5, "duration_sec": 5},
                    ],
                }
            ],
            "selection": {"clip_ids": [], "scene_ids": []},
            "view": {"zoom": 60, "scroll_sec": 0},
        }

    def test_set_selection(self, apply_ops, state):
        new_state, applied = apply_ops(state, [
            {"op": "set_selection", "clip_ids": ["A"], "scene_ids": []}
        ])
        assert new_state["selection"]["clip_ids"] == ["A"]
        assert applied[0]["op"] == "set_selection"

    def test_set_view_zoom(self, apply_ops, state):
        new_state, applied = apply_ops(state, [
            {"op": "set_view", "zoom": 120}
        ])
        assert new_state["view"]["zoom"] == 120
        assert applied[0]["zoom"] == 120

    def test_move_clip(self, apply_ops, state):
        new_state, applied = apply_ops(state, [
            {"op": "move_clip", "clip_id": "A", "lane_id": "v1", "start_sec": 20}
        ])
        clips = new_state["lanes"][0]["clips"]
        moved = [c for c in clips if c["clip_id"] == "A"][0]
        assert moved["start_sec"] == 20

    def test_does_not_mutate_original(self, apply_ops, state):
        import copy
        original = copy.deepcopy(state)
        apply_ops(state, [{"op": "set_selection", "clip_ids": ["B"], "scene_ids": []}])
        assert state == original

    def test_invalid_zoom_raises(self, apply_ops, state):
        with pytest.raises(ValueError, match="zoom must be > 0"):
            apply_ops(state, [{"op": "set_view", "zoom": -1}])


# ---------------------------------------------------------------------------
# Contract 2: _decode_vlog from cut_color_pipeline.py (pure numpy)
# ---------------------------------------------------------------------------

class TestDecodeVlog:
    @pytest.fixture
    def decode_vlog(self):
        return extract_function(
            "src/services/cut_color_pipeline.py",
            "_decode_vlog",
        )

    def test_mid_gray_range(self, decode_vlog):
        """V-Log encodes 18% gray at ~0.433."""
        x = np.array([0.433], dtype=np.float32)
        result = decode_vlog(x)
        assert result.shape == x.shape
        # Should decode to roughly 0.18 (18% gray)
        assert 0.05 < float(result[0]) < 0.35

    def test_zero_input(self, decode_vlog):
        x = np.zeros(10, dtype=np.float32)
        result = decode_vlog(x)
        assert result.shape == (10,)

    def test_output_clipped_0_1(self, decode_vlog):
        x = np.array([0.0, 0.5, 1.0], dtype=np.float32)
        result = decode_vlog(x)
        assert np.all(result >= 0.0)
        assert np.all(result <= 1.0)


# ---------------------------------------------------------------------------
# Contract 3: No fastapi/pydantic import
# ---------------------------------------------------------------------------

class TestNoHeavyImports:
    def test_fastapi_not_imported(self):
        """Extraction must not trigger fastapi import."""
        modules_before = set(sys.modules.keys())
        extract_function("src/api/routes/cut_routes.py", "_apply_timeline_ops")
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        heavy = {"fastapi", "pydantic", "uvicorn", "starlette", "qdrant_client"}
        imported_heavy = heavy & new_modules
        assert not imported_heavy, f"Heavy modules imported: {imported_heavy}"

    def test_numpy_only_for_color(self):
        """Color pipeline extraction needs only numpy."""
        modules_before = set(sys.modules.keys())
        extract_function("src/services/cut_color_pipeline.py", "_decode_slog3")
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        heavy = {"fastapi", "pydantic", "colour"}
        imported_heavy = heavy & new_modules
        assert not imported_heavy, f"Heavy modules imported: {imported_heavy}"


# ---------------------------------------------------------------------------
# Contract 4: extract_functions (multi) with shared namespace
# ---------------------------------------------------------------------------

class TestMultiExtract:
    def test_extract_multiple_log_decoders(self):
        fns = extract_functions(
            "src/services/cut_color_pipeline.py",
            ["_decode_vlog", "_decode_slog3", "_decode_logc3"],
        )
        assert len(fns) == 3
        x = np.array([0.5], dtype=np.float32)
        for name, fn in fns.items():
            result = fn(x)
            assert result.shape == x.shape, f"{name} changed shape"

    def test_sibling_deps_auto_resolved(self):
        """_apply_timeline_ops calls _find_lane/_find_clip — they must be auto-included."""
        apply_ops = extract_function(
            "src/api/routes/cut_routes.py",
            "_apply_timeline_ops",
        )
        state = {
            "lanes": [{"lane_id": "v1", "lane_type": "video", "clips": [
                {"clip_id": "X", "start_sec": 0, "duration_sec": 3}
            ]}],
            "selection": {},
            "view": {},
        }
        # This calls _find_lane and _find_clip internally
        new_state, applied = apply_ops(state, [
            {"op": "move_clip", "clip_id": "X", "lane_id": "v1", "start_sec": 10}
        ])
        assert new_state["lanes"][0]["clips"][0]["start_sec"] == 10


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_missing_function_raises_key_error(self):
        with pytest.raises(KeyError, match="not_a_real_function"):
            extract_function("src/api/routes/cut_routes.py", "not_a_real_function")

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_function("src/nonexistent_module.py", "foo")

    def test_extra_namespace(self):
        """extra_ns injects custom dependencies."""
        custom_flag = {"MY_FLAG": True}
        fns = extract_functions(
            "src/services/cut_color_pipeline.py",
            ["_decode_vlog"],
            extra_ns=custom_flag,
        )
        assert "_decode_vlog" in fns
