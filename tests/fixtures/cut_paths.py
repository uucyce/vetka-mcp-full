"""
Canonical path constants for CUT test suite.

Previously duplicated in 15+ test files as:
    ROOT = Path(__file__).resolve().parent.parent
    CLIENT_SRC = ROOT / "client" / "src"
    CUT_COMPONENTS = ROOT / "client" / "src" / "components" / "cut"
"""

from pathlib import Path

# Repository root (two levels up from tests/fixtures/)
ROOT = Path(__file__).resolve().parent.parent.parent

# Client source tree
CLIENT_DIR = ROOT / "client"
CLIENT_SRC = CLIENT_DIR / "src"

# CUT component tree (76 .tsx files, 16 panels)
CUT_COMPONENTS = CLIENT_SRC / "components" / "cut"

# Commonly referenced source files (each used in 3-8 contract tests)
STORE_FILE = CLIENT_SRC / "store" / "useCutEditorStore.ts"
LAYOUT_FILE = CUT_COMPONENTS / "CutEditorLayoutV2.tsx"
HOTKEYS_FILE = CLIENT_SRC / "hooks" / "useCutHotkeys.ts"
TIMELINE_FILE = CUT_COMPONENTS / "TimelineTrackView.tsx"
VIDEO_PREVIEW_FILE = CUT_COMPONENTS / "VideoPreview.tsx"
AUTOSAVE_FILE = CLIENT_SRC / "hooks" / "useCutAutosave.ts"
DOCKVIEW_STORE_FILE = CLIENT_SRC / "store" / "useDockviewStore.ts"
WORKSPACE_PRESETS_FILE = CUT_COMPONENTS / "WorkspacePresets.tsx"
MENU_BAR_FILE = CUT_COMPONENTS / "MenuBar.tsx"

# E2E test directory
E2E_DIR = CLIENT_DIR / "e2e"
