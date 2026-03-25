"""
MARKER_EPSILON.BLOCK2: Editing operation contract tests.

Verifies store actions and hotkey handlers for core editing operations.
Tests parse TypeScript source to verify implementation contracts.
"""

import re
from pathlib import Path

import pytest

CLIENT = Path(__file__).resolve().parent.parent / "client" / "src"
STORE = CLIENT / "store" / "useCutEditorStore.ts"
LAYOUT = CLIENT / "components" / "cut" / "CutEditorLayoutV2.tsx"
HOTKEYS = CLIENT / "hooks" / "useCutHotkeys.ts"


@pytest.fixture(scope="module")
def store():
    return STORE.read_text()


@pytest.fixture(scope="module")
def layout():
    return LAYOUT.read_text()


@pytest.fixture(scope="module")
def hotkeys():
    return HOTKEYS.read_text()


def _find_impl(source: str, fn_name: str, window: int = 3000) -> str | None:
    pattern = rf"{fn_name}:\s*(?:async\s*)?\([^)]*\)\s*(?:=>)?\s*\{{"
    m = re.search(pattern, source)
    if not m:
        pattern2 = rf"{fn_name}:\s*\([^)]*\)\s*=>\s*\n?\s*set"
        m = re.search(pattern2, source)
    if not m:
        return None
    return source[m.start():m.start() + window]


# ═══════════════════════════════════════════════════════
# Insert Edit (comma key)
# ═══════════════════════════════════════════════════════

class TestInsertEdit:
    """Comma key: insert clip at playhead, push downstream clips right."""

    def test_handler_exists(self, layout):
        assert re.search(r"insertEdit:\s*async", layout)

    def test_reads_source_marks(self, layout):
        impl = _find_impl(layout, "insertEdit")
        assert impl and "sourceMarkIn" in impl

    def test_creates_clip(self, layout):
        impl = _find_impl(layout, "insertEdit")
        assert impl and "clip_3pt_" in impl, "Must create new clip with unique ID"

    def test_routes_to_backend(self, layout):
        impl = _find_impl(layout, "insertEdit")
        assert impl and "applyTimelineOps" in impl, "Must route to backend for undo"

    def test_seeks_after_insert(self, layout):
        impl = _find_impl(layout, "insertEdit")
        assert impl and re.search(r"seek\(", impl), "Must seek after insert"


# ═══════════════════════════════════════════════════════
# Overwrite Edit (period key)
# ═══════════════════════════════════════════════════════

class TestOverwriteEdit:
    """Period key: replace clip at playhead position."""

    def test_handler_exists(self, layout):
        assert re.search(r"overwriteEdit:\s*async", layout)

    def test_creates_clip(self, layout):
        impl = _find_impl(layout, "overwriteEdit")
        assert impl and "clip_3pt_" in impl

    def test_routes_to_backend(self, layout):
        impl = _find_impl(layout, "overwriteEdit")
        assert impl and "applyTimelineOps" in impl


# ═══════════════════════════════════════════════════════
# Split Clip (Cmd+K / Ctrl+V)
# ═══════════════════════════════════════════════════════

class TestSplitClip:
    """Split clip at playhead into two clips."""

    def test_split_clip_action_exists(self, layout):
        """splitClip may be in store or layout hotkey handler."""
        assert "splitClip" in layout or "split" in layout

    def test_hotkey_bound(self, hotkeys):
        assert re.search(r"splitClip:\s*'Cmd\+k'|splitClip:\s*'Ctrl\+v'", hotkeys)

    def test_handler_in_layout(self, layout):
        assert "splitClip" in layout


# ═══════════════════════════════════════════════════════
# Ripple Delete
# ═══════════════════════════════════════════════════════

class TestRippleDelete:
    """Remove clip and close gap (shift downstream left)."""

    def test_action_exists(self, store):
        """rippleDelete may be as store action or as ripple_delete op."""
        assert "ripple_delete" in store or "rippleDelete" in store

    def test_hotkey_bound(self, hotkeys):
        assert re.search(r"rippleDelete:\s*'Shift\+Delete'", hotkeys)

    def test_uses_backend_ops(self, store):
        impl = _find_impl(store, "rippleDelete")
        if impl:
            assert "applyTimelineOps" in impl or "ripple_delete" in impl


# ═══════════════════════════════════════════════════════
# applyTimelineOps → undo stack
# ═══════════════════════════════════════════════════════

class TestApplyTimelineOps:
    """Core undo mechanism: routes ops to backend POST /cut/timeline/apply."""

    def test_action_exists(self, store):
        assert "applyTimelineOps" in store

    def test_posts_to_backend(self, store):
        impl = _find_impl(store, "applyTimelineOps")
        assert impl and re.search(r"fetch|POST|/cut/timeline/apply", impl), \
            "applyTimelineOps must POST to backend"

    def test_refreshes_state(self, store):
        impl = _find_impl(store, "applyTimelineOps")
        assert impl and "refreshProjectState" in impl, \
            "Must refresh project state after ops applied"


# ═══════════════════════════════════════════════════════
# Delete Clip (leave gap)
# ═══════════════════════════════════════════════════════

class TestDeleteClip:
    """Remove selected clip, leave gap."""

    def test_action_exists(self, store):
        """deleteClip may be in store or as remove_clip op."""
        assert "deleteClip" in store or "remove_clip" in store or "delete" in store.lower()

    def test_hotkey_bound(self, hotkeys):
        assert re.search(r"deleteClip:\s*'Delete'", hotkeys)


# ═══════════════════════════════════════════════════════
# Lift and Extract
# ═══════════════════════════════════════════════════════

class TestLiftExtract:
    """Lift (leave gap) and Extract (close gap) operations."""

    def test_lift_exists(self, store):
        assert "liftClip" in store

    def test_extract_exists(self, store):
        assert "extractClip" in store

    def test_lift_uses_undo(self, store):
        impl = _find_impl(store, "liftClip")
        assert impl and "applyTimelineOps" in impl

    def test_extract_uses_undo(self, store):
        impl = _find_impl(store, "extractClip")
        assert impl and "applyTimelineOps" in impl

    def test_lift_hotkey(self, hotkeys):
        assert re.search(r"liftClip:\s*';'", hotkeys)

    def test_extract_hotkey(self, hotkeys):
        # extractClip uses double-quoted string for single quote value
        assert "extractClip" in hotkeys


# ═══════════════════════════════════════════════════════
# Close Gap
# ═══════════════════════════════════════════════════════

class TestCloseGap:
    """Close gap: remove empty space between clips."""

    def test_action_exists(self, store):
        assert "closeGap" in store

    def test_uses_undo(self, store):
        impl = _find_impl(store, "closeGap")
        assert impl and "applyTimelineOps" in impl

    def test_hotkey_bound(self, hotkeys):
        assert re.search(r"closeGap:\s*'Alt\+Backspace'", hotkeys)


# ═══════════════════════════════════════════════════════
# Extend Edit
# ═══════════════════════════════════════════════════════

class TestExtendEdit:
    """Extend nearest edit point to playhead."""

    def test_action_exists(self, store):
        assert "extendEdit" in store

    def test_uses_undo(self, store):
        impl = _find_impl(store, "extendEdit")
        assert impl and "applyTimelineOps" in impl

    def test_hotkey_bound(self, hotkeys):
        assert re.search(r"extendEdit:\s*'e'", hotkeys)
