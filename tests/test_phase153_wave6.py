"""
MARKER_153.6T: Phase 153 Wave 6 Tests — Rails UX + Keyboard Shortcuts + Toasts.

Tests for:
- RailsActionBar (max 3 actions per level, level-specific)
- useKeyboardShortcuts (per-level shortcut mapping)
- useToast (toast types, auto-dismiss timing, max toasts)
- ToastContainer (rendering, dismiss callback)
- MCC integration (imports, wiring, overlay placement)

@phase 153
@wave 6
"""

import os
import re
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 153 contracts changed")

# ── Paths ──
CLIENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'client', 'src')
MCC_DIR = os.path.join(CLIENT_DIR, 'components', 'mcc')
HOOKS_DIR = os.path.join(CLIENT_DIR, 'hooks')

RAILS_FILE = os.path.join(MCC_DIR, 'RailsActionBar.tsx')
TOAST_CONTAINER_FILE = os.path.join(MCC_DIR, 'ToastContainer.tsx')
KEYBOARD_FILE = os.path.join(HOOKS_DIR, 'useKeyboardShortcuts.ts')
TOAST_HOOK_FILE = os.path.join(HOOKS_DIR, 'useToast.ts')
MCC_FILE = os.path.join(MCC_DIR, 'MyceliumCommandCenter.tsx')


def _read(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


# ══════════════════════════════════════════════════════════════
# TestRailsActionBar
# ══════════════════════════════════════════════════════════════

class TestRailsActionBar:
    """Test MARKER_153.6A: RailsActionBar — context-aware action buttons."""

    def test_file_exists(self):
        assert os.path.isfile(RAILS_FILE)

    def test_exports_component(self):
        src = _read(RAILS_FILE)
        assert 'export function RailsActionBar' in src

    def test_exports_get_actions(self):
        src = _read(RAILS_FILE)
        assert 'export function getActionsForLevel' in src

    def test_max_3_actions_per_level(self):
        """Each navigation level should have at most 3 action buttons."""
        src = _read(RAILS_FILE)
        levels = ['roadmap', 'tasks', 'workflow', 'running', 'results']
        for level in levels:
            # Find the array for this level in LEVEL_ACTIONS
            pattern = rf"{level}:\s*\["
            match = re.search(pattern, src)
            assert match, f"Missing LEVEL_ACTIONS for {level}"
            # Count action objects (each has `action:`)
            start = match.end()
            bracket_depth = 1
            i = start
            while i < len(src) and bracket_depth > 0:
                if src[i] == '[':
                    bracket_depth += 1
                elif src[i] == ']':
                    bracket_depth -= 1
                i += 1
            block = src[start:i]
            action_count = block.count("action:")
            assert action_count <= 3, f"{level} has {action_count} actions (max 3)"
            assert action_count >= 1, f"{level} has no actions"

    def test_roadmap_has_drill_action(self):
        src = _read(RAILS_FILE)
        assert "'drillNode'" in src or '"drillNode"' in src

    def test_workflow_has_execute_action(self):
        src = _read(RAILS_FILE)
        # Check workflow level has execute
        workflow_section = src[src.index('workflow:'):src.index('running:')]
        assert 'execute' in workflow_section

    def test_running_has_stop_action(self):
        src = _read(RAILS_FILE)
        running_section = src[src.index('running:'):src.index('results:')]
        assert 'stop' in running_section

    def test_results_has_apply_reject(self):
        src = _read(RAILS_FILE)
        results_section = src[src.index('results:'):]
        assert 'apply' in results_section
        assert 'reject' in results_section

    def test_uses_nolan_palette(self):
        src = _read(RAILS_FILE)
        assert 'NOLAN_PALETTE' in src

    def test_handles_disabled_drill(self):
        """Drill button should be disabled when no node selected at roadmap."""
        src = _read(RAILS_FILE)
        assert 'drillDisabled' in src

    def test_shortcut_hints_displayed(self):
        """Action buttons should show keyboard shortcut hints."""
        src = _read(RAILS_FILE)
        assert 'shortcut' in src
        assert 'Enter' in src
        assert 'Esc' in src


# ══════════════════════════════════════════════════════════════
# TestUseKeyboardShortcuts
# ══════════════════════════════════════════════════════════════

class TestUseKeyboardShortcuts:
    """Test MARKER_153.6B: useKeyboardShortcuts hook."""

    def test_file_exists(self):
        assert os.path.isfile(KEYBOARD_FILE)

    def test_exports_hook(self):
        src = _read(KEYBOARD_FILE)
        assert 'export function useKeyboardShortcuts' in src

    def test_exports_get_shortcuts(self):
        src = _read(KEYBOARD_FILE)
        assert 'export function getShortcutsForLevel' in src

    def test_all_levels_have_shortcuts(self):
        """Every NavLevel should have at least one shortcut."""
        src = _read(KEYBOARD_FILE)
        for level in ['roadmap', 'tasks', 'workflow', 'running', 'results']:
            assert f"  {level}:" in src, f"Missing shortcuts for {level}"

    def test_escape_is_global(self):
        """Escape should be handled globally, not per-level."""
        src = _read(KEYBOARD_FILE)
        assert "e.key === 'Escape'" in src
        assert 'goBack()' in src

    def test_skips_form_elements(self):
        """Should not fire when typing in INPUT/TEXTAREA/SELECT."""
        src = _read(KEYBOARD_FILE)
        assert 'INPUT' in src
        assert 'TEXTAREA' in src
        assert 'SELECT' in src

    def test_skips_modifier_keys(self):
        """Should not fire when Ctrl/Meta/Alt held."""
        src = _read(KEYBOARD_FILE)
        assert 'metaKey' in src or 'ctrlKey' in src

    def test_roadmap_enter_drills(self):
        src = _read(KEYBOARD_FILE)
        # Find roadmap section
        roadmap_block = src[src.index('roadmap:'):src.index('tasks:')]
        assert 'Enter' in roadmap_block
        assert 'onDrillNode' in roadmap_block

    def test_workflow_enter_executes(self):
        src = _read(KEYBOARD_FILE)
        workflow_block = src[src.index('workflow:'):src.index('running:')]
        assert 'Enter' in workflow_block
        assert 'onExecute' in workflow_block

    def test_running_space_stops(self):
        src = _read(KEYBOARD_FILE)
        running_block = src[src.index('running:'):src.index('results:')]
        assert 'onStop' in running_block

    def test_handler_interface_complete(self):
        """ShortcutHandlers should cover all possible actions."""
        src = _read(KEYBOARD_FILE)
        required_handlers = [
            'onDrillNode', 'onDrillTask', 'onExecute', 'onStop',
            'onApply', 'onReject', 'onToggleEdit', 'onExpandStream',
        ]
        for handler in required_handlers:
            assert handler in src, f"Missing handler: {handler}"


# ══════════════════════════════════════════════════════════════
# TestUseToast
# ══════════════════════════════════════════════════════════════

class TestUseToast:
    """Test MARKER_153.6C: useToast hook."""

    def test_file_exists(self):
        assert os.path.isfile(TOAST_HOOK_FILE)

    def test_exports_hook(self):
        src = _read(TOAST_HOOK_FILE)
        assert 'export function useToast' in src

    def test_exports_toast_colors(self):
        src = _read(TOAST_HOOK_FILE)
        assert 'export const TOAST_COLORS' in src

    def test_toast_types_defined(self):
        """Should support info, success, warning, error types."""
        src = _read(TOAST_HOOK_FILE)
        assert "'info'" in src or '"info"' in src
        assert "'success'" in src or '"success"' in src
        assert "'warning'" in src or '"warning"' in src
        assert "'error'" in src or '"error"' in src

    def test_auto_dismiss_timings(self):
        """Info/success should auto-dismiss, errors should be sticky."""
        src = _read(TOAST_HOOK_FILE)
        # Check that there's a timing mechanism
        assert 'setTimeout' in src or 'AUTO_DISMISS' in src or 'duration' in src

    def test_max_toasts_limit(self):
        """Should enforce a maximum number of visible toasts."""
        src = _read(TOAST_HOOK_FILE)
        assert 'MAX_TOASTS' in src

    def test_returns_add_and_dismiss(self):
        """Hook should return addToast and dismissToast functions."""
        src = _read(TOAST_HOOK_FILE)
        assert 'addToast' in src
        assert 'dismissToast' in src

    def test_listens_for_pipeline_events(self):
        """Should auto-create toasts from pipeline-activity events."""
        src = _read(TOAST_HOOK_FILE)
        assert 'pipeline-activity' in src or 'pipeline_activity' in src

    def test_listens_for_task_board_events(self):
        """Should auto-create toasts from task-board-updated events."""
        src = _read(TOAST_HOOK_FILE)
        assert 'task-board-updated' in src or 'task_board_updated' in src

    def test_toast_interface_has_required_fields(self):
        """Toast type should have id, type, message fields."""
        src = _read(TOAST_HOOK_FILE)
        assert 'id:' in src or 'id:' in src
        assert 'type:' in src or 'ToastType' in src
        assert 'message:' in src or 'message' in src

    def test_nolan_dark_style_colors(self):
        """Toast colors should follow Nolan dark palette."""
        src = _read(TOAST_HOOK_FILE)
        # Should have dark backgrounds, not bright ones
        assert 'TOAST_COLORS' in src
        # Background should be dark (rgba with low brightness or dark hex)
        assert 'rgba' in src or '#1' in src or '#2' in src


# ══════════════════════════════════════════════════════════════
# TestToastContainer
# ══════════════════════════════════════════════════════════════

class TestToastContainer:
    """Test MARKER_153.6D: ToastContainer rendering component."""

    def test_file_exists(self):
        assert os.path.isfile(TOAST_CONTAINER_FILE)

    def test_exports_component(self):
        src = _read(TOAST_CONTAINER_FILE)
        assert 'export function ToastContainer' in src

    def test_positioned_absolute_top_right(self):
        src = _read(TOAST_CONTAINER_FILE)
        assert 'absolute' in src
        assert 'top' in src
        assert 'right' in src

    def test_renders_toast_type_icons(self):
        src = _read(TOAST_CONTAINER_FILE)
        assert 'TYPE_ICONS' in src
        # Should have icons for all 4 types
        assert 'info' in src
        assert 'success' in src
        assert 'warning' in src
        assert 'error' in src

    def test_has_dismiss_button(self):
        src = _read(TOAST_CONTAINER_FILE)
        assert 'onDismiss' in src
        # Should have a clickable dismiss control
        assert 'onClick' in src

    def test_uses_toast_colors(self):
        src = _read(TOAST_CONTAINER_FILE)
        assert 'TOAST_COLORS' in src

    def test_returns_null_when_empty(self):
        """Should return null when no toasts to display."""
        src = _read(TOAST_CONTAINER_FILE)
        assert 'return null' in src

    def test_has_z_index_overlay(self):
        """Should have high z-index to overlay other content."""
        src = _read(TOAST_CONTAINER_FILE)
        assert 'zIndex' in src

    def test_stacks_vertically(self):
        """Toasts should stack vertically (flex column)."""
        src = _read(TOAST_CONTAINER_FILE)
        assert 'column' in src

    def test_monospace_font(self):
        """Should use monospace font for consistency."""
        src = _read(TOAST_CONTAINER_FILE)
        assert 'monospace' in src


# ══════════════════════════════════════════════════════════════
# TestMCCWave6Integration
# ══════════════════════════════════════════════════════════════

class TestMCCWave6Integration:
    """Test Wave 6 components are properly integrated into MCC."""

    def test_mcc_imports_rails_action_bar(self):
        src = _read(MCC_FILE)
        assert "import { RailsActionBar }" in src

    def test_mcc_imports_toast_container(self):
        src = _read(MCC_FILE)
        assert "import { ToastContainer }" in src

    def test_mcc_imports_use_toast(self):
        src = _read(MCC_FILE)
        assert "import { useToast }" in src

    def test_mcc_imports_use_keyboard_shortcuts(self):
        src = _read(MCC_FILE)
        assert "import { useKeyboardShortcuts }" in src

    def test_mcc_initializes_toast_hook(self):
        src = _read(MCC_FILE)
        assert 'useToast()' in src
        assert 'toasts' in src
        assert 'addToast' in src
        assert 'dismissToast' in src

    def test_mcc_renders_toast_container(self):
        src = _read(MCC_FILE)
        assert '<ToastContainer' in src
        assert 'onDismiss={dismissToast}' in src

    def test_mcc_renders_rails_action_bar(self):
        src = _read(MCC_FILE)
        assert '<RailsActionBar' in src

    def test_mcc_calls_keyboard_shortcuts(self):
        src = _read(MCC_FILE)
        assert 'useKeyboardShortcuts({' in src or 'useKeyboardShortcuts(' in src

    def test_mcc_keyboard_wires_drill(self):
        src = _read(MCC_FILE)
        assert 'onDrillNode:' in src

    def test_mcc_keyboard_wires_execute(self):
        src = _read(MCC_FILE)
        assert 'onExecute: handleExecute' in src

    def test_mcc_keyboard_wires_toggle_edit(self):
        src = _read(MCC_FILE)
        assert 'onToggleEdit:' in src

    def test_mcc_toast_marker(self):
        src = _read(MCC_FILE)
        assert 'MARKER_153.6D' in src

    def test_mcc_rails_marker(self):
        src = _read(MCC_FILE)
        assert 'MARKER_153.6A' in src

    def test_mcc_keyboard_marker(self):
        src = _read(MCC_FILE)
        assert 'MARKER_153.6B' in src
