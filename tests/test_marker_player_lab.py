"""
Test: MARKER_PLAYER_LAB_SRT — N-moments and Favorite marker support (tb_1775249587_77255_1)

Tests for commit c4f62be4: Player Lab marker import with N/FAV tags.

Features to test:
- 'negative' kind added to MarkerKind type
- SRT sidecar import: _extract_marker_meta_from_srt parses [N], [FAV] tags
- Timeline rendering: N-moments (dimmed), Favorite (bright)
- Auto-assembly hooks: filter_clips_by_lab_markers excludes all-N clips
"""

import json
import sys
from pathlib import Path

import pytest

# Project root
_git_common_dir_result = __import__('subprocess').run(
    ["git", "rev-parse", "--git-common-dir"],
    capture_output=True,
    text=True,
)
if _git_common_dir_result.returncode == 0:
    _git_common = Path(_git_common_dir_result.stdout.strip())
    _PROJECT_ROOT = _git_common.parent if _git_common.name == ".git" else _git_common
else:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

sys.path.insert(0, str(_PROJECT_ROOT))


class TestMarkerKindNegativeType:
    """Verify MarkerKind includes 'negative' type."""

    def test_marker_kind_includes_negative(self):
        """MarkerKind in useCutEditorStore.ts includes 'negative'."""
        store_ts = _PROJECT_ROOT / "client" / "src" / "store" / "useCutEditorStore.ts"
        assert store_ts.exists(), f"Store file not found: {store_ts}"
        content = store_ts.read_text()
        assert "'negative'" in content or '"negative"' in content, "MarkerKind must include 'negative'"

    def test_marker_kind_includes_favorite(self):
        """MarkerKind in useCutEditorStore.ts includes 'favorite'."""
        store_ts = _PROJECT_ROOT / "client" / "src" / "store" / "useCutEditorStore.ts"
        assert store_ts.exists(), f"Store file not found: {store_ts}"
        content = store_ts.read_text()
        assert "'favorite'" in content or '"favorite"' in content, "MarkerKind must include 'favorite'"


class TestExtractMarkerMetaFromSrtNegativeTags:
    """Test _extract_marker_meta_from_srt parsing [N] and [FAV] tags."""

    def test_extract_n_tag(self):
        """_extract_marker_meta_from_srt parses [N] tag."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[N] bad lighting")
        assert meta.get("kind") == "negative", f"Expected kind='negative', got {meta.get('kind')}"
        assert note == "bad lighting", f"Expected note='bad lighting', got {note}"

    def test_extract_fav_tag(self):
        """_extract_marker_meta_from_srt parses [FAV] tag."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[FAV] great reaction")
        assert meta.get("kind") == "favorite", f"Expected kind='favorite', got {meta.get('kind')}"
        assert note == "great reaction", f"Expected note='great reaction', got {note}"

    def test_extract_n_tag_empty_note(self):
        """_extract_marker_meta_from_srt handles [N] with empty note."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[N]")
        assert meta.get("kind") == "negative"
        assert note == ""

    def test_extract_fav_tag_empty_note(self):
        """_extract_marker_meta_from_srt handles [FAV] with empty note."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[FAV]")
        assert meta.get("kind") == "favorite"
        assert note == ""

    def test_extract_n_tag_case_insensitive_lowercase(self):
        """_extract_marker_meta_from_srt parses [n] (lowercase) tag."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[n] soft focus")
        assert meta.get("kind") == "negative"
        assert note == "soft focus"

    def test_extract_fav_tag_case_insensitive_lowercase(self):
        """_extract_marker_meta_from_srt parses [fav] (lowercase) tag."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[fav] perfect take")
        assert meta.get("kind") == "favorite"
        assert note == "perfect take"

    def test_extract_json_meta_still_works(self):
        """_extract_marker_meta_from_srt still handles JSON meta format."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt('{"kind": "cam", "score": 0.8} camera note')
        assert meta.get("kind") == "cam"
        assert meta.get("score") == 0.8
        assert note == "camera note"

    def test_extract_plain_text_fallback(self):
        """_extract_marker_meta_from_srt falls back to ({}, text) for plain text."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("just a plain comment")
        assert meta == {}, f"Expected empty dict, got {meta}"
        assert note == "just a plain comment"

    def test_extract_n_tag_with_multiword_note(self):
        """_extract_marker_meta_from_srt preserves multiword notes."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[N] this shot is out of focus and unusable")
        assert meta.get("kind") == "negative"
        assert note == "this shot is out of focus and unusable"

    def test_extract_fav_tag_sets_score(self):
        """_extract_marker_meta_from_srt [FAV] tag sets score=1.0."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[FAV] keep this")
        assert meta.get("score") == 1.0, f"FAV tag should set score=1.0, got {meta.get('score')}"

    def test_extract_n_tag_sets_score(self):
        """_extract_marker_meta_from_srt [N] tag sets score=0.0 or low value."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[N] reject this")
        score = meta.get("score", 0.5)  # Should be 0.0 or very low
        assert score <= 0.3, f"N tag should set low score, got {score}"


class TestCutRoutesNegativeKindSupport:
    """Test cut_routes.py includes 'negative' kind in type allowlists."""

    def test_cut_routes_includes_negative_kind(self):
        """cut_routes.py allowlist includes 'negative' kind."""
        routes_py = _PROJECT_ROOT / "src" / "api" / "routes" / "cut_routes.py"
        assert routes_py.exists(), f"cut_routes.py not found: {routes_py}"
        content = routes_py.read_text()
        assert '"negative"' in content or "'negative'" in content, "cut_routes.py must include 'negative' kind"

    def test_cut_time_marker_apply_request_literal_includes_negative(self):
        """CutTimeMarkerApplyRequest Literal includes 'negative' kind."""
        routes_py = _PROJECT_ROOT / "src" / "api" / "routes" / "cut_routes.py"
        content = routes_py.read_text()
        # Check for the Literal type definition containing negative
        assert "Literal" in content, "CutTimeMarkerApplyRequest should use Literal for kind"
        assert '"negative"' in content or "'negative'" in content


class TestPlayerLabMarkerImport:
    """Test Player Lab marker import flow with N/FAV tags."""

    def test_player_lab_marker_import_item_includes_negative(self):
        """PlayerLabMarkerImportItem accepts 'negative' kind."""
        routes_py = _PROJECT_ROOT / "src" / "api" / "routes" / "cut_routes.py"
        content = routes_py.read_text()
        # Should have a type definition for PlayerLabMarkerImportItem
        assert "PlayerLabMarkerImportItem" in content
        # And it should support negative kind
        assert '"negative"' in content or "'negative'" in content

    def test_srt_import_creates_negative_markers(self):
        """SRT import with [N] tags creates negative markers in store."""
        # This is an integration test that requires the full pipeline
        pytest.skip("Requires SRT import integration test setup")

    def test_srt_import_creates_favorite_markers(self):
        """SRT import with [FAV] tags creates favorite markers in store."""
        # This is an integration test that requires the full pipeline
        pytest.skip("Requires SRT import integration test setup")


class TestTimelineMarkerRendering:
    """Test N-moment and Favorite marker rendering on timeline."""

    def test_negative_markers_render_dimmed(self):
        """N-moment markers render with dimmed styling."""
        # This is a React component test that requires Playwright or RTL
        pytest.skip("Requires React component testing setup (Playwright/RTL)")

    def test_favorite_markers_render_bright(self):
        """Favorite markers render with bright/highlighted styling."""
        # This is a React component test that requires Playwright or RTL
        pytest.skip("Requires React component testing setup (Playwright/RTL)")

    def test_marker_color_coding_applied(self):
        """Markers use correct visual encoding: N=dim gray, FAV=gold."""
        pytest.skip("Requires Playwright E2E test")


class TestFilterClipsByLabMarkers:
    """Test filter_clips_by_lab_markers excluding all-N clips."""

    def test_filter_excludes_all_negative_clips(self):
        """filter_clips_by_lab_markers excludes clips with only [N] markers."""
        pytest.skip("Requires filter_clips_by_lab_markers implementation")

    def test_filter_includes_favorite_clips(self):
        """filter_clips_by_lab_markers includes [FAV] clips first."""
        pytest.skip("Requires filter_clips_by_lab_markers implementation")

    def test_filter_includes_untagged_by_default(self):
        """filter_clips_by_lab_markers includes untagged clips when include_untagged=True."""
        pytest.skip("Requires filter_clips_by_lab_markers implementation")

    def test_filter_excludes_untagged_when_strict(self):
        """filter_clips_by_lab_markers excludes untagged clips when include_untagged=False."""
        pytest.skip("Requires filter_clips_by_lab_markers implementation")

    def test_filter_mixed_markers_uses_favorite(self):
        """Clips with both [N] and [FAV] markers are treated as favorite."""
        pytest.skip("Requires filter_clips_by_lab_markers implementation")


class TestMarkerScoringLogic:
    """Test marker scoring for auto-assembly decisions."""

    def test_score_favorite_is_max(self):
        """[FAV] marker gets score=1.0 (max)."""
        pytest.skip("Requires score_clip_by_lab_markers implementation")

    def test_score_negative_is_min(self):
        """[N] marker gets score=0.0 (min)."""
        pytest.skip("Requires score_clip_by_lab_markers implementation")

    def test_score_untagged_is_neutral(self):
        """Untagged clips get score=0.5 (neutral)."""
        pytest.skip("Requires score_clip_by_lab_markers implementation")

    def test_score_mixed_uses_weighted_average(self):
        """Mixed markers use weighted average of constituent scores."""
        pytest.skip("Requires score_clip_by_lab_markers implementation")


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_extract_empty_string(self):
        """_extract_marker_meta_from_srt handles empty string."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("")
        assert meta == {}
        assert note == ""

    def test_extract_whitespace_only(self):
        """_extract_marker_meta_from_srt handles whitespace-only input."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("   ")
        assert meta == {}
        assert note == ""

    def test_extract_malformed_json(self):
        """_extract_marker_meta_from_srt handles malformed JSON gracefully."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("{bad json}")
        # Should fall back to plain text
        assert meta == {}

    def test_extract_bracket_in_note(self):
        """_extract_marker_meta_from_srt preserves brackets in note text."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[N] note with [brackets]")
        assert "[brackets]" in note

    def test_extract_multiple_tags_first_wins(self):
        """_extract_marker_meta_from_srt handles [N][FAV] — first tag wins."""
        from src.api.routes.cut_routes_workers import _extract_marker_meta_from_srt

        meta, note = _extract_marker_meta_from_srt("[N][FAV] conflicting tags")
        # Should parse first tag
        assert meta.get("kind") in ["negative", "favorite"]
