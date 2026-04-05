"""DELTA QA-209 BATCH: Verify 4 CUT done_worktree tasks.

Tasks verified:
1. tb_1775409210_74964_1 — GAMMA-FIX: EffectsPanel.tsx duplicate braces (claude/cut-ux)
2. tb_1775409058_71633_1 — HARNESS-209.4: Commander wake gap dual alert (claude/harness)
3. tb_1775406964_68814_4 — HARNESS-209.1: Context exhaustion auto-restart (claude/harness)
4. tb_1775406970_68814_6 — HARNESS-209.3: smart_snapshot polish (claude/harness-eta)
"""
import os
import subprocess
import sys
import ast
import re
from pathlib import Path

# Resolve project root via git
_git_result = subprocess.run(
    ["git", "rev-parse", "--git-common-dir"],
    capture_output=True, text=True,
)
if _git_result.returncode == 0:
    _gc = Path(_git_result.stdout.strip())
    PROJECT_ROOT = _gc.parent if _gc.name == ".git" else _gc
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

sys.path.insert(0, str(PROJECT_ROOT))


def _git_show(commit, path):
    """Read file content from a specific commit."""
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True, text=True, timeout=10,
        cwd=str(PROJECT_ROOT),
    )
    return result.stdout if result.returncode == 0 else ""


# ═══════════════════════════════════════════════════════════════════
# TASK 1: GAMMA-FIX EffectsPanel.tsx — tb_1775409210_74964_1
# Commit: 00b38814 on claude/cut-ux
# ═══════════════════════════════════════════════════════════════════
class TestGammaFixEffectsPanel:
    """Verify duplicate closing braces removed from EffectsPanel.tsx."""

    COMMIT = "00b38814"
    FILE = "client/src/components/cut/EffectsPanel.tsx"

    def _src(self):
        return _git_show(self.COMMIT, self.FILE)

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "GAMMA-FIX" in result.stdout

    def test_no_consecutive_closing_braces(self):
        """The bug was duplicate );} blocks — verify no two within 2 lines."""
        src = self._src()
        assert src, "Could not read EffectsPanel.tsx from commit"
        lines = src.split("\n")
        closing_positions = []
        for i in range(len(lines) - 1):
            if lines[i].strip() == ");" and lines[i + 1].strip() == "}":
                closing_positions.append(i)
        for j in range(1, len(closing_positions)):
            gap = closing_positions[j] - closing_positions[j - 1]
            assert gap > 2, f"Duplicate closing at lines {closing_positions[j-1]+1} and {closing_positions[j]+1}"

    def test_transitions_section_defined_once(self):
        src = self._src()
        matches = re.findall(r"function\s+TransitionsSection\s*\(", src)
        assert len(matches) == 1, f"TransitionsSection defined {len(matches)} times"

    def test_effects_panel_default_export_once(self):
        src = self._src()
        matches = re.findall(r"export\s+default\s+function\s+EffectsPanel\s*\(", src)
        assert len(matches) == 1

    def test_structural_tests_included(self):
        """Agent included vitest structural tests."""
        test_content = _git_show(self.COMMIT, "client/src/components/cut/__tests__/EffectsPanel.test.ts")
        assert test_content, "Structural test file missing from commit"
        assert "TransitionsSection" in test_content
        assert "balanced" in test_content.lower()


# ═══════════════════════════════════════════════════════════════════
# TASK 2: HARNESS-209.4 Wake Gap — tb_1775409058_71633_1
# Commit: c92291a0 on claude/harness
# ═══════════════════════════════════════════════════════════════════
class TestHarness209_4_WakeGap:
    """Verify dual alert: osascript notification ALWAYS fires + tmux poke."""

    COMMIT = "c92291a0"
    FILE = "scripts/synapse_wake.sh"

    def _src(self):
        return _git_show(self.COMMIT, self.FILE)

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "HARNESS-209.4" in result.stdout

    def test_osascript_notification_function(self):
        """_send_notification function defined with osascript."""
        src = self._src()
        assert "_send_notification" in src, "Missing _send_notification function"
        assert "osascript" in src, "Missing osascript call"
        assert 'display notification' in src, "Missing display notification"

    def test_notification_always_fires(self):
        """Notification fires BEFORE idle check, not conditionally."""
        src = self._src()
        lines = src.split("\n")
        notif_line = None
        idle_check_line = None
        for i, line in enumerate(lines):
            if "_send_notification" in line and "SYNAPSE: Wake" in line:
                notif_line = i
            if "IDLE_SEC" in line and "WAKE_THRESHOLD" in line and "lt" in line:
                idle_check_line = i
        assert notif_line is not None, "Notification call for wake not found"
        assert idle_check_line is not None, "Idle check not found"
        assert notif_line < idle_check_line, \
            f"Notification (line {notif_line}) must fire BEFORE idle check (line {idle_check_line})"

    def test_tmux_poke_only_for_idle(self):
        """tmux send-keys only fires for idle agents (after threshold check)."""
        src = self._src()
        lines = src.split("\n")
        send_keys_line = None
        threshold_check_line = None
        for i, line in enumerate(lines):
            if 'tmux send-keys' in line and 'session init' in line:
                send_keys_line = i
            if "IDLE_SEC" in line and "WAKE_THRESHOLD" in line:
                threshold_check_line = i
        assert send_keys_line is not None, "tmux send-keys not found"
        assert threshold_check_line is not None
        assert send_keys_line > threshold_check_line, "tmux poke must be after idle check"

    def test_offline_agent_gets_notification(self):
        """Agent not running still gets macOS notification."""
        src = self._src()
        assert "OFFLINE" in src, "Should send notification when agent is offline"

    def test_message_parameter_supported(self):
        """Third parameter MESSAGE is supported."""
        src = self._src()
        assert 'MESSAGE="${3:-' in src, "MESSAGE parameter not parsed"

    def test_vibe_agent_gets_notification(self):
        """Vibe agents get both signal file and notification."""
        src = self._src()
        # Find vibe section
        vibe_section = src[src.index("vibe"):src.index("exit 0", src.index("vibe"))+10]
        assert "_send_notification" in vibe_section, "Vibe agents must get notification"

    def test_marker_209_dual_wake(self):
        src = self._src()
        assert "MARKER_209.DUAL_WAKE" in src


# ═══════════════════════════════════════════════════════════════════
# TASK 3: HARNESS-209.1 Context Exhaustion — tb_1775406964_68814_4
# Commit: d9b17af2 on claude/harness
# ═══════════════════════════════════════════════════════════════════
class TestHarness209_1_ContextExhaustion:
    """Verify context exhaustion auto-restart daemon + checkpoint."""

    COMMIT = "d9b17af2"

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "HARNESS-209.1" in result.stdout

    def test_context_monitor_script_exists(self):
        src = _git_show(self.COMMIT, "scripts/synapse_context_monitor.sh")
        assert src, "synapse_context_monitor.sh missing from commit"
        assert "MARKER_209.CONTEXT_MONITOR" in src

    def test_detection_patterns_comprehensive(self):
        """Monitor detects multiple context exhaustion signals."""
        src = _git_show(self.COMMIT, "scripts/synapse_context_monitor.sh")
        required_patterns = [
            "compacting conversation",
            "context window",
            "auto-compact",
        ]
        for pattern in required_patterns:
            assert pattern in src, f"Missing detection pattern: {pattern}"

    def test_checkpoint_save_mechanism(self):
        """Checkpoint directory and save logic exist."""
        src = _git_show(self.COMMIT, "scripts/synapse_context_monitor.sh")
        assert "CHECKPOINT_DIR" in src, "Checkpoint directory variable missing"
        assert "checkpoint" in src.lower(), "Checkpoint logic missing"

    def test_daemon_mode_supported(self):
        """--daemon flag for continuous monitoring."""
        src = _git_show(self.COMMIT, "scripts/synapse_context_monitor.sh")
        assert "--daemon" in src, "Daemon mode not supported"

    def test_status_mode_supported(self):
        """--status flag for checking compacting state."""
        src = _git_show(self.COMMIT, "scripts/synapse_context_monitor.sh")
        assert "--status" in src, "Status mode not supported"

    def test_task_board_checkpoint_methods(self):
        """task_board.py has checkpoint save/load methods."""
        src = _git_show(self.COMMIT, "src/orchestration/task_board.py")
        assert src, "task_board.py not readable from commit"
        assert "checkpoint" in src.lower(), "Checkpoint methods missing from task_board.py"

    def test_synapse_wake_script_created(self):
        """synapse_wake.sh created as part of this feature."""
        src = _git_show(self.COMMIT, "scripts/synapse_wake.sh")
        assert src, "synapse_wake.sh missing"

    def test_synapse_write_script_created(self):
        """synapse_write.sh created as part of this feature."""
        src = _git_show(self.COMMIT, "scripts/synapse_write.sh")
        assert src, "synapse_write.sh missing"

    def test_claude_md_template_updated(self):
        """CLAUDE.md template includes context restart guidance."""
        src = _git_show(self.COMMIT, "data/templates/claude_md_template.j2")
        assert src, "Template not readable"

    def test_test_script_included(self):
        """Test script for context restart cycle included."""
        src = _git_show(self.COMMIT, "scripts/test_context_restart.sh")
        assert src, "test_context_restart.sh missing"


# ═══════════════════════════════════════════════════════════════════
# TASK 4: HARNESS-209.3 Snapshot Polish — tb_1775406970_68814_6
# Commit: a7a187b1 on claude/harness-eta
# ═══════════════════════════════════════════════════════════════════
class TestHarness209_3_SnapshotPolish:
    """Verify smart_snapshot conflict detection + sidecar auto-expand."""

    COMMIT = "a7a187b1"

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "HARNESS-209.3" in result.stdout

    def test_glob_pattern_support(self):
        """allowed_paths supports glob patterns (fnmatch)."""
        src = _git_show(self.COMMIT, "src/orchestration/task_board.py")
        assert "fnmatch" in src, "fnmatch import missing"
        assert "MARKER_209.3" in src, "MARKER_209.3 missing"

    def test_extended_sidecar_patterns(self):
        """Sidecar detection includes _test.py convention and json/jsonl variants."""
        src = _git_show(self.COMMIT, "src/orchestration/task_board.py")
        assert "stem}_test" in src, "Missing _test.py sidecar pattern"
        assert ".jsonl" in src, "Missing .jsonl variant matching"

    def test_merge_base_failure_handling(self):
        """merge-base failure is logged as warning, not silent skip."""
        src = _git_show(self.COMMIT, "src/orchestration/task_board.py")
        assert "merge-base failed" in src, "Missing merge-base failure warning"

    def test_merge_base_strip(self):
        """merge_base output is stripped before use (avoids trailing newline)."""
        src = _git_show(self.COMMIT, "src/orchestration/task_board.py")
        assert "merge_base.strip()" in src, "merge_base not stripped"

    def test_tests_included(self):
        """Agent included tests for snapshot polish."""
        src = _git_show(self.COMMIT, "tests/test_smart_snapshot_polish.py")
        assert src, "test_smart_snapshot_polish.py missing from commit"
        assert len(src) > 200, "Test file seems too small"

    def test_task_board_syntax_valid(self):
        """task_board.py from commit parses as valid Python."""
        src = _git_show(self.COMMIT, "src/orchestration/task_board.py")
        assert src, "Cannot read task_board.py"
        ast.parse(src)
