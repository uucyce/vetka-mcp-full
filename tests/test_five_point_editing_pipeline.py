"""
MARKER_EPSILON.5PT1: Five-point editing pipeline contract tests.

Verifies the 5 critical NLE paths exist and are correctly wired:
1. PLAYHEAD — Space → playPause → rAF shuttle loop
2. DRAG TO TIMELINE — drop handler → dropMediaOnTimeline → applyTimelineOps
3. SPLIT (Cmd+K) — splitClip → applyTimelineOps (split_at op)
4. INSERT/OVERWRITE — insertEdit/overwriteEdit → local-first + applyTimelineOps
5. UNDO (Cmd+Z) — /cut/undo → refreshProjectState

Strategy: Source-parsing contract tests verifying handler existence,
applyTimelineOps routing, and local-first patterns.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "client" / "src"
CUT_EDITOR = CLIENT / "components" / "cut" / "CutEditorLayoutV2.tsx"
STORE = CLIENT / "store" / "useCutEditorStore.ts"
HOTKEYS = CLIENT / "hooks" / "useCutHotkeys.ts"
TIMELINE_TV = CLIENT / "components" / "cut" / "TimelineTrackView.tsx"


def _read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"File not found: {path}")
    return path.read_text()


def _find(source: str, pattern: str) -> bool:
    return bool(re.search(pattern, source))


def _find_near(source: str, anchor: str, target: str, window: int = 60) -> bool:
    """Check if target appears within `window` lines of anchor."""
    lines = source.split("\n")
    for i, line in enumerate(lines):
        if re.search(anchor, line):
            block = "\n".join(lines[max(0, i - 5):i + window])
            if re.search(target, block):
                return True
    return False


@pytest.fixture(scope="module")
def editor_src():
    return _read(CUT_EDITOR)


@pytest.fixture(scope="module")
def store_src():
    return _read(STORE)


@pytest.fixture(scope="module")
def hotkeys_src():
    return _read(HOTKEYS)


@pytest.fixture(scope="module")
def timeline_src():
    return _read(TIMELINE_TV)


# ═══════════════════════════════════════════════════════════════════════
# PATH 1: PLAYHEAD — Space → playPause → rAF shuttle
# ═══════════════════════════════════════════════════════════════════════

class TestPlayheadPipeline:
    """Space key → playPause → currentTime updates via animation loop."""

    def test_play_pause_handler_exists(self, editor_src, store_src):
        combined = editor_src + store_src
        assert _find(combined, r"playPause"), \
            "playPause handler not found"

    def test_space_key_bound(self, hotkeys_src):
        assert _find(hotkeys_src, r"playPause:\s*['\"]Space['\"]"), \
            "playPause not bound to Space key"

    def test_shuttle_speed_state(self, store_src):
        """Store must track shuttleSpeed for JKL transport."""
        assert _find(store_src, r"shuttleSpeed"), \
            "shuttleSpeed not in store"

    def test_seek_function_exists(self, store_src):
        """seek() must exist to update currentTime."""
        assert _find(store_src, r"seek\s*[:(]"), \
            "seek function not in store"

    def test_current_time_state(self, store_src):
        """Store must track currentTime."""
        assert _find(store_src, r"currentTime"), \
            "currentTime not in store"

    def test_request_animation_frame_loop(self, editor_src, store_src):
        """Playback must use rAF for smooth animation."""
        combined = editor_src + store_src
        assert _find(combined, r"requestAnimationFrame|animationFrame|rAF|useAnimationFrame"), \
            "No rAF loop found for playback"


# ═══════════════════════════════════════════════════════════════════════
# PATH 2: DRAG TO TIMELINE — drop → addClip → applyTimelineOps
# ═══════════════════════════════════════════════════════════════════════

class TestDragToTimelinePipeline:
    """Drag clip from Project → drop on timeline → clip appears."""

    def test_drop_handler_exists(self, timeline_src, editor_src):
        """Drop handler must exist in TimelineTrackView or CutEditorLayoutV2."""
        combined = timeline_src + editor_src
        assert _find(combined, r"(handleDrop|onDrop|handleLaneDrop|dropMedia)"), \
            "No drop handler found"

    def test_drop_media_on_timeline_action(self, store_src):
        """Store must have dropMediaOnTimeline or equivalent action."""
        assert _find(store_src, r"(dropMediaOnTimeline|addClipToLane|addClip)"), \
            "No drop-to-timeline action in store"

    def test_drop_routes_to_apply_ops(self, store_src):
        """Drop handler must route through applyTimelineOps for undo."""
        assert _find_near(store_src, r"dropMediaOnTimeline|addClipToLane", r"applyTimelineOps"), \
            "Drop handler doesn't route through applyTimelineOps"

    def test_drag_data_transfer(self, timeline_src, editor_src):
        """Must read drag data from dataTransfer or DND store."""
        combined = timeline_src + editor_src
        assert _find(combined, r"(dataTransfer|dragData|DND_STORE|dndStore)"), \
            "No drag data reading mechanism found"


# ═══════════════════════════════════════════════════════════════════════
# PATH 3: SPLIT (Cmd+K) — splitClip → applyTimelineOps
# ═══════════════════════════════════════════════════════════════════════

class TestSplitPipeline:
    """Cmd+K → splitClip → split_at op → clip divides visually."""

    def test_split_handler_exists(self, editor_src, store_src):
        combined = editor_src + store_src
        assert _find(combined, r"splitClip"), \
            "splitClip handler not found"

    def test_split_hotkey_bound(self, hotkeys_src):
        """splitClip must be bound to Cmd+K (both presets)."""
        assert _find(hotkeys_src, r"splitClip:\s*['\"]Cmd\+k['\"]"), \
            "splitClip not bound to Cmd+K"

    def test_split_uses_apply_ops(self, editor_src, store_src):
        """splitClip must route through applyTimelineOps."""
        combined = editor_src + store_src
        assert _find_near(combined, r"splitClip|split_at", r"applyTimelineOps"), \
            "splitClip doesn't use applyTimelineOps"

    def test_split_op_type(self, editor_src, store_src):
        """Must use 'split_at' or 'split' operation type."""
        combined = editor_src + store_src
        assert _find(combined, r"['\"]split_at['\"]|['\"]split['\"]|op.*split"), \
            "No split_at op type found"


# ═══════════════════════════════════════════════════════════════════════
# PATH 4: INSERT/OVERWRITE — local-first + applyTimelineOps
# ═══════════════════════════════════════════════════════════════════════

class TestInsertOverwritePipeline:
    """Comma/Period → insertEdit/overwriteEdit → local-first + backend."""

    def test_insert_edit_handler(self, editor_src, store_src):
        combined = editor_src + store_src
        assert _find(combined, r"insertEdit"), \
            "insertEdit handler not found"

    def test_overwrite_edit_handler(self, editor_src, store_src):
        combined = editor_src + store_src
        assert _find(combined, r"overwriteEdit"), \
            "overwriteEdit handler not found"

    def test_insert_hotkey(self, hotkeys_src):
        assert _find(hotkeys_src, r"insertEdit:\s*['\"],"), \
            "insertEdit not bound to comma"

    def test_overwrite_hotkey(self, hotkeys_src):
        assert _find(hotkeys_src, r"overwriteEdit:\s*['\"]\."), \
            "overwriteEdit not bound to period"

    def test_insert_uses_apply_ops(self, editor_src, store_src):
        combined = editor_src + store_src
        assert _find_near(combined, r"insertEdit", r"applyTimelineOps"), \
            "insertEdit doesn't use applyTimelineOps"

    def test_overwrite_uses_apply_ops(self, editor_src, store_src):
        combined = editor_src + store_src
        assert _find_near(combined, r"overwriteEdit", r"applyTimelineOps"), \
            "overwriteEdit doesn't use applyTimelineOps"

    def test_local_first_set_lanes(self, editor_src):
        """INSERT/OVERWRITE should mutate lanes locally before backend."""
        assert _find_near(editor_src, r"insertEdit|overwriteEdit", r"setLanes|set\(\{.*lanes"), \
            "INSERT/OVERWRITE missing local-first setLanes pattern"

    def test_skip_refresh_flag(self, editor_src):
        """Local-first ops must pass skipRefresh: true."""
        assert _find(editor_src, r"skipRefresh:\s*true"), \
            "skipRefresh: true not found — backend may overwrite local mutations"

    def test_three_point_resolve(self, editor_src, store_src):
        """Must use resolveThreePointEdit or equivalent for mark resolution."""
        combined = editor_src + store_src
        assert _find(combined, r"resolveThreePointEdit|resolve.*[Tt]hreePoint|threePoint"), \
            "No three-point edit resolution found"


# ═══════════════════════════════════════════════════════════════════════
# PATH 5: UNDO (Cmd+Z) — /cut/undo → refreshProjectState
# ═══════════════════════════════════════════════════════════════════════

class TestUndoPipeline:
    """Cmd+Z → POST /cut/undo → refreshProjectState."""

    def test_undo_handler_exists(self, editor_src, store_src):
        combined = editor_src + store_src
        assert _find(combined, r"undo\b"), \
            "undo handler not found"

    def test_redo_handler_exists(self, editor_src, store_src):
        combined = editor_src + store_src
        assert _find(combined, r"redo\b"), \
            "redo handler not found"

    def test_undo_hotkey(self, hotkeys_src):
        assert _find(hotkeys_src, r"undo:\s*['\"]Cmd\+z['\"]"), \
            "undo not bound to Cmd+Z"

    def test_redo_hotkey(self, hotkeys_src):
        assert _find(hotkeys_src, r"redo:\s*['\"]Cmd\+Shift\+z['\"]"), \
            "redo not bound to Cmd+Shift+Z"

    def test_undo_calls_backend(self, editor_src, store_src):
        """Undo must POST to /cut/undo endpoint."""
        combined = editor_src + store_src
        assert _find(combined, r"/cut/undo"), \
            "/cut/undo endpoint not called"

    def test_redo_calls_backend(self, editor_src, store_src):
        """Redo must POST to /cut/redo endpoint."""
        combined = editor_src + store_src
        assert _find(combined, r"/cut/redo"), \
            "/cut/redo endpoint not called"

    def test_refresh_after_undo(self, editor_src, store_src):
        """Must refreshProjectState after undo/redo to sync UI."""
        combined = editor_src + store_src
        assert _find_near(combined, r"/cut/undo|undo\(\)", r"refreshProjectState|refreshProject"), \
            "No refreshProjectState after undo"


# ═══════════════════════════════════════════════════════════════════════
# CROSS-CUTTING: applyTimelineOps is the universal undo gate
# ═══════════════════════════════════════════════════════════════════════

class TestApplyTimelineOpsGate:
    """applyTimelineOps must be the single entry point for all backend ops."""

    def test_function_exists(self, store_src, editor_src):
        combined = store_src + editor_src
        assert _find(combined, r"applyTimelineOps"), \
            "applyTimelineOps function not found"

    def test_posts_to_backend(self, store_src, editor_src):
        """Must POST to /cut/timeline/apply or equivalent."""
        combined = store_src + editor_src
        assert _find_near(combined, r"applyTimelineOps", r"/cut/timeline/apply|/cut/apply|fetch.*timeline"), \
            "applyTimelineOps doesn't POST to backend"

    def test_accepts_ops_array(self, store_src, editor_src):
        """Must accept operations array (ops/operations parameter)."""
        combined = store_src + editor_src
        assert _find_near(combined, r"applyTimelineOps", r"ops|operations|op_type"), \
            "applyTimelineOps doesn't accept ops parameter"


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION: All 5 paths have hotkey bindings
# ═══════════════════════════════════════════════════════════════════════

class TestAllPathsHaveHotkeys:
    """Every editing path must have a keyboard shortcut."""

    @pytest.mark.parametrize("action,key_pattern", [
        ("playPause", r"Space"),
        ("splitClip", r"Cmd\+k"),
        ("insertEdit", r","),
        ("overwriteEdit", r"\."),
        ("undo", r"Cmd\+z"),
        ("redo", r"Cmd\+Shift\+z"),
    ])
    def test_hotkey_bound(self, hotkeys_src, action, key_pattern):
        assert _find(hotkeys_src, rf"{action}:\s*['\"].*{key_pattern}"), \
            f"{action} not bound to expected key"
