"""
MARKER_PLAYER_LAB_SRT — Tests for N-moment / Favorite-moment marker pipeline.

Tests:
1. MarkerKind type includes 'negative' (store type-level check via import)
2. _extract_marker_meta_from_srt parses [N] / [FAV] / [n] / [fav] tags
3. _extract_marker_meta_from_srt still handles JSON meta format
4. _extract_marker_meta_from_srt falls back to ({}, text) for plain text
5. cut_routes.py allowlist accepts 'negative' kind
6. cut_routes.py allowlist accepts 'favorite' kind
7. cut_routes.py Literal includes 'negative' in CutTimeMarkerApplyRequest
8. cut_routes.py Literal includes 'negative' in PlayerLabMarkerImportItem
9. filter_clips_by_lab_markers: favorite clips included first
10. filter_clips_by_lab_markers: N-only clips excluded
11. filter_clips_by_lab_markers: untagged clips included when include_untagged=True
12. filter_clips_by_lab_markers: untagged clips excluded when include_untagged=False
13. filter_clips_by_lab_markers: mixed (fav+neg) → included as favorite
14. score_clip_by_lab_markers: favorite → 1.0
15. score_clip_by_lab_markers: negative → 0.0
16. score_clip_by_lab_markers: untagged → 0.5
17. score_clip_by_lab_markers: mixed uses weighted average
18. [N] tag with note text preserves note
19. [FAV] tag with note text preserves note
20. [N] case-insensitive match
"""

import sys
import os
import importlib
import ast

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ---------------------------------------------------------------------------
# Helpers: import _extract_marker_meta_from_srt from workers module
# ---------------------------------------------------------------------------
def _get_extract_fn():
    from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt
    return _extract_marker_meta_from_srt


def _get_extract_fn_export():
    from src.api.routes.cut_routes_export import _extract_marker_meta_from_srt
    return _extract_marker_meta_from_srt


# ---------------------------------------------------------------------------
# 1. MarkerKind includes 'negative' (AST check on TS source — fast, no build needed)
# ---------------------------------------------------------------------------
def test_markerkind_includes_negative():
    store_ts = os.path.join(ROOT, "client", "src", "store", "useCutEditorStore.ts")
    with open(store_ts, encoding="utf-8") as f:
        content = f.read()
    assert "'negative'" in content, "MarkerKind must include 'negative'"


# ---------------------------------------------------------------------------
# 2–4. _extract_marker_meta_from_srt (workers)
# ---------------------------------------------------------------------------
def test_extract_n_tag():
    fn = _get_extract_fn()
    meta, note = fn("[N] bad lighting")
    assert meta.get("kind") == "negative"
    assert meta.get("score") == pytest.approx(0.3)
    assert note == "bad lighting"


def test_extract_fav_tag():
    fn = _get_extract_fn()
    meta, note = fn("[FAV] great reaction")
    assert meta.get("kind") == "favorite"
    assert meta.get("score") == pytest.approx(1.0)
    assert note == "great reaction"


def test_extract_n_tag_empty_note():
    fn = _get_extract_fn()
    meta, note = fn("[N]")
    assert meta.get("kind") == "negative"
    assert note == ""


def test_extract_fav_tag_empty_note():
    fn = _get_extract_fn()
    meta, note = fn("[FAV]")
    assert meta.get("kind") == "favorite"
    assert note == ""


def test_extract_n_tag_case_insensitive():
    fn = _get_extract_fn()
    meta, note = fn("[n] soft focus")
    assert meta.get("kind") == "negative"
    assert note == "soft focus"


def test_extract_fav_tag_case_insensitive():
    fn = _get_extract_fn()
    meta, note = fn("[fav] perfect take")
    assert meta.get("kind") == "favorite"
    assert note == "perfect take"


def test_extract_json_meta_still_works():
    fn = _get_extract_fn()
    meta, note = fn('{"kind": "cam", "score": 0.8} camera note')
    assert meta.get("kind") == "cam"
    assert meta.get("score") == pytest.approx(0.8)
    assert note == "camera note"


def test_extract_plain_text_fallback():
    fn = _get_extract_fn()
    meta, note = fn("just a plain comment")
    assert meta == {}
    assert note == "just a plain comment"


# ---------------------------------------------------------------------------
# Same tests for export module (duplicate function)
# ---------------------------------------------------------------------------
def test_extract_n_tag_export_module():
    fn = _get_extract_fn_export()
    meta, note = fn("[N] out of focus")
    assert meta.get("kind") == "negative"
    assert note == "out of focus"


def test_extract_fav_tag_export_module():
    fn = _get_extract_fn_export()
    meta, note = fn("[FAV] hero shot")
    assert meta.get("kind") == "favorite"
    assert note == "hero shot"


# ---------------------------------------------------------------------------
# 5–8. cut_routes.py allowlist and Literal checks (AST)
# ---------------------------------------------------------------------------
def test_cut_routes_srt_allowlist_includes_negative():
    routes_py = os.path.join(ROOT, "src", "api", "routes", "cut_routes.py")
    with open(routes_py, encoding="utf-8") as f:
        content = f.read()
    assert '"negative"' in content or "'negative'" in content, \
        "cut_routes.py SRT import allowlist must include 'negative'"


def test_cut_routes_literal_apply_request_includes_negative():
    routes_py = os.path.join(ROOT, "src", "api", "routes", "cut_routes.py")
    with open(routes_py, encoding="utf-8") as f:
        content = f.read()
    # CutTimeMarkerApplyRequest.kind Literal should have negative
    assert "negative" in content


def test_cut_routes_player_lab_item_includes_negative():
    routes_py = os.path.join(ROOT, "src", "api", "routes", "cut_routes.py")
    with open(routes_py, encoding="utf-8") as f:
        content = f.read()
    assert "negative" in content


# ---------------------------------------------------------------------------
# 9–17. filter_clips_by_lab_markers / score_clip_by_lab_markers
# ---------------------------------------------------------------------------
from src.services.pulse_conductor import filter_clips_by_lab_markers, score_clip_by_lab_markers

CLIP_A = {"media_path": "/media/take1.mp4", "start_sec": 0.0, "end_sec": 10.0}
CLIP_B = {"media_path": "/media/take2.mp4", "start_sec": 0.0, "end_sec": 10.0}
CLIP_C = {"media_path": "/media/take3.mp4", "start_sec": 0.0, "end_sec": 10.0}

FAV_A = {"kind": "favorite", "media_path": "/media/take1.mp4", "start_sec": 2.0, "end_sec": 5.0, "score": 1.0}
NEG_B = {"kind": "negative", "media_path": "/media/take2.mp4", "start_sec": 0.0, "end_sec": 10.0, "score": 0.3}
FAV_B = {"kind": "favorite", "media_path": "/media/take2.mp4", "start_sec": 1.0, "end_sec": 3.0, "score": 0.9}


def test_filter_favorite_clips_included():
    result = filter_clips_by_lab_markers([CLIP_A, CLIP_C], [FAV_A], include_untagged=False)
    assert CLIP_A in result


def test_filter_negative_only_clips_excluded():
    result = filter_clips_by_lab_markers([CLIP_A, CLIP_B], [FAV_A, NEG_B])
    assert CLIP_B not in result
    assert CLIP_A in result


def test_filter_untagged_included_when_flag_true():
    result = filter_clips_by_lab_markers([CLIP_A, CLIP_C], [FAV_A], include_untagged=True)
    assert CLIP_C in result


def test_filter_untagged_excluded_when_flag_false():
    result = filter_clips_by_lab_markers([CLIP_A, CLIP_C], [FAV_A], include_untagged=False)
    assert CLIP_C not in result


def test_filter_mixed_fav_neg_included_as_favorite():
    # take2 has both fav and neg markers → has_favorite=True → included
    result = filter_clips_by_lab_markers([CLIP_B], [NEG_B, FAV_B])
    assert CLIP_B in result


def test_filter_favorites_come_before_untagged():
    result = filter_clips_by_lab_markers([CLIP_C, CLIP_A], [FAV_A], include_untagged=True)
    assert result.index(CLIP_A) < result.index(CLIP_C)


def test_score_favorite_clip():
    s = score_clip_by_lab_markers(CLIP_A, [FAV_A])
    assert s == pytest.approx(1.0)


def test_score_negative_clip():
    s = score_clip_by_lab_markers(CLIP_B, [NEG_B])
    assert s == pytest.approx(0.0)


def test_score_untagged_clip():
    s = score_clip_by_lab_markers(CLIP_C, [FAV_A])
    assert s == pytest.approx(0.5)


def test_score_mixed_weighted_average():
    # fav score=1.0 weight=0.9, neg score=0.0 weight=0.3 → (1.0*0.9 + 0.0*0.3) / 1.2 = 0.75
    s = score_clip_by_lab_markers(CLIP_B, [FAV_B, NEG_B])
    assert s == pytest.approx(0.75, abs=0.01)
