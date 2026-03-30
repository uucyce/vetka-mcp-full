"""
MARKER_KF-CONTRACT: Contract tests for keyframe timeline ops.

Covers add_keyframe, remove_keyframe, and set_prop dotted path (keyframes.*).
Implementation: _apply_timeline_ops, MARKER_B71 + KF-DICTFORMAT + KF-SETPROP-DOT.

keyframes are stored as dict[property → list[{time_sec, value, easing?}]].
"property" key is NOT stored inside each kf entry — it's the dict key.

Tests written by Epsilon [task:tb_1774786638_19262_1]
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_state(clips_data: list[dict]) -> dict:
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
                "clips": sorted(clips_data, key=lambda c: c["start_sec"]),
            }
        ],
        "selection": {"clip_ids": [], "scene_ids": []},
        "view": {"zoom": 60, "scroll_sec": 0},
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _get_clip(state: dict, clip_id: str) -> dict | None:
    for lane in state["lanes"]:
        for clip in lane["clips"]:
            if clip["clip_id"] == clip_id:
                return clip
    return None


@pytest.fixture(autouse=True)
def _import_ops():
    from src.api.routes.cut_routes import _apply_timeline_ops
    global apply_ops
    apply_ops = _apply_timeline_ops


# ─── add_keyframe ─────────────────────────────────────────────────────────────

class TestAddKeyframe:
    def test_basic_add_creates_dict_keyed_by_property(self):
        """add_keyframe stores clip['keyframes']['opacity'] as a list."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        new_state, applied = apply_ops(state, [{
            "op": "add_keyframe", "clip_id": "A",
            "property": "opacity", "time_sec": 1.0, "value": 0.5,
        }])
        clip = _get_clip(new_state, "A")
        assert isinstance(clip.get("keyframes"), dict)
        prop_list = clip["keyframes"]["opacity"]
        assert len(prop_list) == 1
        assert prop_list[0]["time_sec"] == 1.0
        assert prop_list[0]["value"] == 0.5
        # property key must NOT be stored inside the kf entry (KF-DICTFORMAT)
        assert "property" not in prop_list[0]

    def test_multiple_properties_stored_as_separate_keys(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 10},
        ])
        new_state, _ = apply_ops(state, [
            {"op": "add_keyframe", "clip_id": "A", "property": "opacity", "time_sec": 1.0, "value": 0.2},
            {"op": "add_keyframe", "clip_id": "A", "property": "scale",   "time_sec": 0.5, "value": 1.5},
        ])
        kfs = _get_clip(new_state, "A")["keyframes"]
        assert "opacity" in kfs
        assert "scale" in kfs
        assert kfs["opacity"][0]["time_sec"] == 1.0
        assert kfs["scale"][0]["time_sec"] == 0.5

    def test_sorted_by_time_within_property(self):
        """Multiple kfs on same property are sorted by time_sec."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 10},
        ])
        new_state, _ = apply_ops(state, [
            {"op": "add_keyframe", "clip_id": "A", "property": "opacity", "time_sec": 3.0, "value": 0.8},
            {"op": "add_keyframe", "clip_id": "A", "property": "opacity", "time_sec": 1.0, "value": 0.2},
        ])
        prop_list = _get_clip(new_state, "A")["keyframes"]["opacity"]
        assert len(prop_list) == 2
        assert prop_list[0]["time_sec"] == 1.0
        assert prop_list[1]["time_sec"] == 3.0

    def test_duplicate_time_replaces_existing(self):
        """Adding kf at same time_sec (within 0.001s) replaces old one."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        new_state, _ = apply_ops(state, [
            {"op": "add_keyframe", "clip_id": "A", "property": "opacity", "time_sec": 2.0, "value": 0.5},
            {"op": "add_keyframe", "clip_id": "A", "property": "opacity", "time_sec": 2.0, "value": 0.9},
        ])
        prop_list = _get_clip(new_state, "A")["keyframes"]["opacity"]
        assert len(prop_list) == 1
        assert prop_list[0]["value"] == 0.9

    def test_easing_stored_when_provided(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        new_state, _ = apply_ops(state, [{
            "op": "add_keyframe", "clip_id": "A",
            "property": "opacity", "time_sec": 2.0, "value": 1.0, "easing": "ease_in",
        }])
        kf = _get_clip(new_state, "A")["keyframes"]["opacity"][0]
        assert kf["easing"] == "ease_in"

    def test_no_easing_field_when_not_provided(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        new_state, _ = apply_ops(state, [{
            "op": "add_keyframe", "clip_id": "A",
            "property": "opacity", "time_sec": 2.0, "value": 1.0,
        }])
        kf = _get_clip(new_state, "A")["keyframes"]["opacity"][0]
        assert "easing" not in kf

    def test_applied_ops_records_correct_fields(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        _, applied = apply_ops(state, [{
            "op": "add_keyframe", "clip_id": "A",
            "property": "scale", "time_sec": 0.0, "value": 1.2,
        }])
        assert applied[0]["op"] == "add_keyframe"
        assert applied[0]["clip_id"] == "A"
        assert applied[0]["property"] == "scale"
        assert applied[0]["time_sec"] == 0.0

    def test_raises_on_missing_clip_id(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="clip_id"):
            apply_ops(state, [{"op": "add_keyframe", "property": "opacity", "time_sec": 0.0, "value": 1.0}])

    def test_raises_on_missing_property(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="property"):
            apply_ops(state, [{"op": "add_keyframe", "clip_id": "A", "time_sec": 0.0, "value": 1.0}])

    def test_raises_on_negative_time(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="time_sec"):
            apply_ops(state, [{"op": "add_keyframe", "clip_id": "A",
                               "property": "opacity", "time_sec": -1.0, "value": 0.5}])

    def test_raises_on_unknown_clip(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="not found"):
            apply_ops(state, [{"op": "add_keyframe", "clip_id": "MISSING",
                               "property": "opacity", "time_sec": 0.0, "value": 1.0}])

    def test_migrates_legacy_flat_list_on_add(self):
        """If clip has legacy flat-list keyframes, add_keyframe migrates to dict format."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5,
             "keyframes": [{"property": "opacity", "time_sec": 0.5, "value": 0.3}]},
        ])
        new_state, _ = apply_ops(state, [{
            "op": "add_keyframe", "clip_id": "A",
            "property": "scale", "time_sec": 1.0, "value": 1.5,
        }])
        kfs = _get_clip(new_state, "A")["keyframes"]
        assert isinstance(kfs, dict)
        assert "opacity" in kfs
        assert "scale" in kfs


# ─── remove_keyframe ──────────────────────────────────────────────────────────

class TestRemoveKeyframe:
    def _clip_with_kfs(self, *entries):
        """Build clip fixture with dict-format keyframes."""
        kf_dict = {}
        for prop, time_sec, value in entries:
            kf_dict.setdefault(prop, []).append({"time_sec": time_sec, "value": value})
        return {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5,
                "keyframes": kf_dict}

    def test_removes_matching_keyframe(self):
        state = _make_state([self._clip_with_kfs(("opacity", 1.0, 0.5), ("opacity", 2.0, 0.8))])
        new_state, applied = apply_ops(state, [{
            "op": "remove_keyframe", "clip_id": "A", "property": "opacity", "time_sec": 1.0,
        }])
        prop_list = _get_clip(new_state, "A")["keyframes"]["opacity"]
        assert len(prop_list) == 1
        assert prop_list[0]["time_sec"] == 2.0
        assert applied[0]["removed"] == 1

    def test_no_crash_on_missing_keyframe(self):
        state = _make_state([self._clip_with_kfs(("opacity", 1.0, 0.5))])
        new_state, applied = apply_ops(state, [{
            "op": "remove_keyframe", "clip_id": "A", "property": "opacity", "time_sec": 9.9,
        }])
        assert len(_get_clip(new_state, "A")["keyframes"]["opacity"]) == 1
        assert applied[0]["removed"] == 0

    def test_time_tolerance_removes_near_match(self):
        """kf at time 2.0001 is removed when request specifies time 2.0 (diff < 0.001)."""
        state = _make_state([self._clip_with_kfs(("scale", 2.0001, 1.0))])
        new_state, applied = apply_ops(state, [{
            "op": "remove_keyframe", "clip_id": "A", "property": "scale", "time_sec": 2.0,
        }])
        assert len(_get_clip(new_state, "A")["keyframes"]["scale"]) == 0
        assert applied[0]["removed"] == 1

    def test_time_outside_tolerance_not_removed(self):
        """kf at time 2.005 is NOT removed when request specifies 2.0 (diff >= 0.001)."""
        state = _make_state([self._clip_with_kfs(("scale", 2.005, 1.0))])
        new_state, applied = apply_ops(state, [{
            "op": "remove_keyframe", "clip_id": "A", "property": "scale", "time_sec": 2.0,
        }])
        assert len(_get_clip(new_state, "A")["keyframes"]["scale"]) == 1
        assert applied[0]["removed"] == 0

    def test_no_crash_on_clip_without_keyframes(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        new_state, applied = apply_ops(state, [{
            "op": "remove_keyframe", "clip_id": "A", "property": "opacity", "time_sec": 1.0,
        }])
        assert applied[0]["removed"] == 0

    def test_no_crash_on_missing_property_key(self):
        """Removing from a property not in keyframes dict returns removed=0."""
        state = _make_state([self._clip_with_kfs(("opacity", 1.0, 0.5))])
        new_state, applied = apply_ops(state, [{
            "op": "remove_keyframe", "clip_id": "A", "property": "scale", "time_sec": 1.0,
        }])
        assert applied[0]["removed"] == 0

    def test_raises_on_missing_clip_id(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="clip_id"):
            apply_ops(state, [{"op": "remove_keyframe", "property": "opacity", "time_sec": 1.0}])

    def test_raises_on_missing_property(self):
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="property"):
            apply_ops(state, [{"op": "remove_keyframe", "clip_id": "A", "time_sec": 1.0}])


# ─── set_prop dotted path (KF-SETPROP-DOT) ───────────────────────────────────

class TestSetPropDottedKeyframes:
    def test_set_prop_keyframes_opacity_creates_nested_dict(self):
        """keyframes.opacity → clip['keyframes']['opacity'] without ValueError."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        kf_list = [{"time_sec": 0.0, "value": 1.0, "easing": "linear"}]
        new_state, applied = apply_ops(state, [{
            "op": "set_prop", "clip_id": "A",
            "key": "keyframes.opacity", "value": kf_list,
        }])
        clip = _get_clip(new_state, "A")
        assert isinstance(clip.get("keyframes"), dict)
        assert clip["keyframes"]["opacity"] == kf_list
        assert applied[0]["key"] == "keyframes.opacity"

    def test_set_prop_dotted_merges_not_replaces(self):
        """Existing sub-keys survive when sibling key is set via dotted path."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5,
             "keyframes": {"scale": [{"time_sec": 0, "value": 1.0, "easing": "linear"}]}},
        ])
        new_kfs = [{"time_sec": 0.5, "value": 0.0, "easing": "ease_out"}]
        new_state, _ = apply_ops(state, [{
            "op": "set_prop", "clip_id": "A",
            "key": "keyframes.opacity", "value": new_kfs,
        }])
        clip = _get_clip(new_state, "A")
        assert "scale" in clip["keyframes"], "existing scale key must survive"
        assert clip["keyframes"]["opacity"] == new_kfs

    def test_set_prop_dotted_none_removes_subkey(self):
        """value=None on dotted path removes the sub-key."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5,
             "keyframes": {"opacity": [{"time_sec": 0, "value": 1.0}]}},
        ])
        new_state, _ = apply_ops(state, [{
            "op": "set_prop", "clip_id": "A", "key": "keyframes.opacity", "value": None,
        }])
        clip = _get_clip(new_state, "A")
        assert "opacity" not in clip.get("keyframes", {})

    def test_set_prop_dotted_disallowed_root_raises(self):
        """Root key not in whitelist raises ValueError even with dotted path."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5},
        ])
        with pytest.raises(ValueError, match="not in paste-safe whitelist"):
            apply_ops(state, [{
                "op": "set_prop", "clip_id": "A", "key": "start_sec.foo", "value": 99,
            }])

    def test_update_keyframe_easing_via_set_prop(self):
        """Typical updateKeyframeEasing call: replace opacity list with updated easing."""
        state = _make_state([
            {"clip_id": "A", "source_path": "/a.mp4", "start_sec": 0, "duration_sec": 5,
             "keyframes": {"opacity": [
                 {"time_sec": 0.0, "value": 1.0, "easing": "linear"},
                 {"time_sec": 2.0, "value": 0.5, "easing": "linear"},
             ]}},
        ])
        updated = [
            {"time_sec": 0.0, "value": 1.0, "easing": "ease_in"},
            {"time_sec": 2.0, "value": 0.5, "easing": "ease_out"},
        ]
        new_state, _ = apply_ops(state, [{
            "op": "set_prop", "clip_id": "A",
            "key": "keyframes.opacity", "value": updated,
        }])
        clip = _get_clip(new_state, "A")
        assert clip["keyframes"]["opacity"][0]["easing"] == "ease_in"
        assert clip["keyframes"]["opacity"][1]["easing"] == "ease_out"
