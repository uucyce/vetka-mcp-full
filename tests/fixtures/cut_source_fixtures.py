"""
Session-scoped pytest fixtures for CUT TypeScript source files.

Replaces the module-scoped fixtures duplicated in 6+ contract test files:
    @pytest.fixture(scope="module")
    def store():
        if not STORE_FILE.exists():
            pytest.skip("Store not found")
        return STORE_FILE.read_text()

Register these in conftest.py or import directly in test files.

Usage in conftest.py:
    from tests.fixtures.cut_source_fixtures import *  # noqa: F401,F403

Usage in individual test file:
    from tests.fixtures.cut_source_fixtures import store_source  # as function
    # or rely on conftest auto-registration
"""

import pytest

from tests.fixtures.cut_paths import (
    STORE_FILE,
    LAYOUT_FILE,
    HOTKEYS_FILE,
    TIMELINE_FILE,
    VIDEO_PREVIEW_FILE,
    AUTOSAVE_FILE,
    DOCKVIEW_STORE_FILE,
    WORKSPACE_PRESETS_FILE,
    MENU_BAR_FILE,
)


def _read_or_skip(path) -> str:
    """Read a file or skip the test if not found."""
    if not path.exists():
        pytest.skip(f"Source file not found: {path}")
    return path.read_text(errors="ignore")


# ── Session-scoped fixtures ──────────────────────────────────────────────
# Session scope because source files don't change during a test run.
# This is faster than module scope (read once, share across all tests).


@pytest.fixture(scope="session")
def store_source():
    """useCutEditorStore.ts source text — used by 6+ contract tests."""
    return _read_or_skip(STORE_FILE)


@pytest.fixture(scope="session")
def layout_source():
    """CutEditorLayoutV2.tsx source text."""
    return _read_or_skip(LAYOUT_FILE)


@pytest.fixture(scope="session")
def hotkeys_source():
    """useCutHotkeys.ts source text."""
    return _read_or_skip(HOTKEYS_FILE)


@pytest.fixture(scope="session")
def timeline_source():
    """TimelineTrackView.tsx source text."""
    return _read_or_skip(TIMELINE_FILE)


@pytest.fixture(scope="session")
def video_preview_source():
    """VideoPreview.tsx source text."""
    return _read_or_skip(VIDEO_PREVIEW_FILE)


@pytest.fixture(scope="session")
def autosave_source():
    """useCutAutosave.ts source text."""
    return _read_or_skip(AUTOSAVE_FILE)


@pytest.fixture(scope="session")
def dockview_store_source():
    """useDockviewStore.ts source text."""
    return _read_or_skip(DOCKVIEW_STORE_FILE)


@pytest.fixture(scope="session")
def workspace_presets_source():
    """WorkspacePresets.tsx source text."""
    return _read_or_skip(WORKSPACE_PRESETS_FILE)


@pytest.fixture(scope="session")
def menu_bar_source():
    """MenuBar.tsx source text."""
    return _read_or_skip(MENU_BAR_FILE)
