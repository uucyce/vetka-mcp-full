"""
MARKER_EPSILON.T3: Insert/Overwrite three-point editing contract tests.

FCP7 Ch.36: Comma (,) = Insert Edit, Period (.) = Overwrite Edit.
Verifies the local-first implementation in CutEditorLayoutV2.tsx:

1. insertEdit uses source marks (sourceMarkIn/Out) to compute duration
2. overwriteEdit replaces clips at sequence mark position
3. Both create new clip with correct source_path, start_sec, duration_sec
4. Both call applyTimelineOps for backend undo/redo
5. Both seek playhead to end of inserted clip

Source: client/src/components/cut/CutEditorLayoutV2.tsx (MARKER_3PT_LOCAL_FIRST)
Hotkey: client/src/hooks/useCutHotkeys.ts (insertEdit: ',', overwriteEdit: '.')
"""

import re
from pathlib import Path

import pytest

LAYOUT_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "components" / "cut" / "CutEditorLayoutV2.tsx"
HOTKEYS_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "hooks" / "useCutHotkeys.ts"
STORE_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "store" / "useCutEditorStore.ts"


@pytest.fixture(scope="module")
def layout_source():
    if not LAYOUT_FILE.exists():
        pytest.skip(f"Layout not found: {LAYOUT_FILE}")
    return LAYOUT_FILE.read_text()


@pytest.fixture(scope="module")
def hotkeys_source():
    if not HOTKEYS_FILE.exists():
        pytest.skip(f"Hotkeys not found: {HOTKEYS_FILE}")
    return HOTKEYS_FILE.read_text()


@pytest.fixture(scope="module")
def store_source():
    if not STORE_FILE.exists():
        pytest.skip(f"Store not found: {STORE_FILE}")
    return STORE_FILE.read_text()


class TestInsertEditContract:
    """Comma key: Insert edit (FCP7 Ch.36) — ripple insert at sequence mark."""

    def test_insert_edit_handler_exists(self, layout_source):
        """insertEdit handler must be defined in hotkey handlers."""
        # After MARKER_3PT_DEDUP refactor: insertEdit delegates to performInsert (useCallback)
        assert re.search(r"insertEdit:\s*(async\s*\(\)|performInsert)", layout_source)

    def test_reads_source_marks(self, layout_source):
        """Must read sourceMarkIn/sourceMarkOut for clip duration."""
        assert "sourceMarkIn" in layout_source
        assert "sourceMarkOut" in layout_source

    def test_computes_duration(self, layout_source):
        """Duration = sourceMarkOut - sourceMarkIn."""
        # The pattern: srcOut - srcIn or similar
        assert re.search(r"srcOut\s*-\s*srcIn|sourceMarkOut.*sourceMarkIn", layout_source)

    def test_gets_insert_targets(self, layout_source):
        """Must call getInsertTargets() to find target lane."""
        assert "getInsertTargets()" in layout_source

    def test_creates_new_clip_id(self, layout_source):
        """Must generate unique clip ID."""
        assert re.search(r"clip_3pt_", layout_source)

    def test_calls_apply_timeline_ops(self, layout_source):
        """Must route through applyTimelineOps for undo support."""
        # MARKER_3PT_LOCAL_FIRST: local-first + async backend
        # After dedup refactor, applyTimelineOps and insert_at may be on separate lines
        assert "applyTimelineOps" in layout_source and "insert_at" in layout_source

    def test_seeks_after_insert(self, layout_source):
        """Must seek playhead to end of inserted clip."""
        assert re.search(r"seek\(seqIn\s*\+\s*dur\)", layout_source)

    def test_local_first_pattern(self, layout_source):
        """Must do local-first insert, not await backend first."""
        # MARKER_3PT_LOCAL_FIRST: setLanes before applyTimelineOps
        assert re.search(r"setLanes.*\n.*applyTimelineOps", layout_source, re.DOTALL)


class TestOverwriteEditContract:
    """Period key: Overwrite edit — replace at sequence mark position."""

    def test_overwrite_edit_handler_exists(self, layout_source):
        # After MARKER_3PT_DEDUP refactor: overwriteEdit delegates to performOverwrite (useCallback)
        assert re.search(r"overwriteEdit:\s*(async\s*\(\)|performOverwrite)", layout_source)

    def test_overwrite_uses_source_marks(self, layout_source):
        """Overwrite also reads source marks for duration."""
        # Both insert and overwrite use srcIn/srcOut
        count = len(re.findall(r"srcOut\s*-\s*srcIn", layout_source))
        assert count >= 2, "Both insert and overwrite should compute duration"

    def test_overwrite_creates_clip(self, layout_source):
        """Must create a new clip object with source_path."""
        assert re.search(r"source_path:\s*srcPath", layout_source)


class TestSourcePathResolution:
    """MARKER_3PT_SRC_FIX: Source media resolution chain."""

    def test_tries_source_media_path_first(self, layout_source):
        """First try: sourceMediaPath from store."""
        assert "sourceMediaPath" in layout_source

    def test_fallback_to_clip_under_playhead(self, layout_source):
        """Second try: find clip at current time."""
        assert re.search(r"clip.*start_sec.*currentTime|currentTime.*clip", layout_source, re.DOTALL)

    def test_fallback_to_any_clip(self, layout_source):
        """Third try (MARKER_3PT_SRC_FIX): use first clip from any lane."""
        assert re.search(r"lane\.clips\.length\s*>\s*0", layout_source)


class TestHotkeyBindings:
    """Verify insert/overwrite are bound to correct keys."""

    def test_insert_bound_to_comma(self, hotkeys_source):
        assert re.search(r"insertEdit:\s*['\"],", hotkeys_source)

    def test_overwrite_bound_to_period(self, hotkeys_source):
        assert re.search(r"overwriteEdit:\s*['\"]\.", hotkeys_source)


class TestStoreSupport:
    """Verify store provides required fields for 3PT editing."""

    def test_source_mark_in_exists(self, store_source):
        assert "sourceMarkIn" in store_source

    def test_source_mark_out_exists(self, store_source):
        assert "sourceMarkOut" in store_source

    def test_sequence_mark_in_exists(self, store_source):
        assert "sequenceMarkIn" in store_source

    def test_get_insert_targets_exists(self, store_source):
        assert "getInsertTargets" in store_source

    def test_source_media_path_exists(self, store_source):
        assert "sourceMediaPath" in store_source
