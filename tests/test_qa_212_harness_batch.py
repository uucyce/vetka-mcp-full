"""DELTA QA-212: Verify HARNESS-212.1/212.2/212.3 batch.

1. tb_1775438863_68814_11 — HARNESS-212.1: Free agent heartbeat (232cebf1)
2. tb_1775438872_68814_12 — HARNESS-212.2: Polaris Captain role (84d96b80)
3. tb_1775438878_68814_13 — HARNESS-212.3: Synapse polish (c38d8eda)
"""
import subprocess
import sys
from pathlib import Path

_git_result = subprocess.run(
    ["git", "rev-parse", "--git-common-dir"],
    capture_output=True, text=True,
)
if _git_result.returncode == 0:
    _gc = Path(_git_result.stdout.strip())
    PROJECT_ROOT = _gc.parent if _gc.name == ".git" else _gc
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


def _git_show(commit, path):
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True, text=True, timeout=10,
        cwd=str(PROJECT_ROOT),
    )
    return result.stdout if result.returncode == 0 else ""


def _commit_ok(commit, keyword):
    result = subprocess.run(
        ["git", "log", "--oneline", commit, "-1"],
        capture_output=True, text=True, timeout=5,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"Commit {commit} not found"
    assert keyword in result.stdout, f"'{keyword}' not in: {result.stdout}"


# ═══ TASK 1: HARNESS-212.1 Heartbeat ═══
class TestHeartbeat212_1:
    COMMIT = "232cebf1"

    def test_commit_exists(self):
        _commit_ok(self.COMMIT, "HARNESS-212.1")

    def test_heartbeat_script_exists(self):
        src = _git_show(self.COMMIT, "scripts/synapse_heartbeat.sh")
        assert src, "synapse_heartbeat.sh missing"
        assert "MARKER_212.HEARTBEAT" in src

    def test_stall_detection(self):
        src = _git_show(self.COMMIT, "scripts/synapse_heartbeat.sh")
        assert "STALL_THRESHOLD" in src

    def test_commander_notification(self):
        src = _git_show(self.COMMIT, "scripts/synapse_heartbeat.sh")
        assert "osascript" in src or "notification" in src.lower()

    def test_auto_nudge(self):
        src = _git_show(self.COMMIT, "scripts/synapse_heartbeat.sh")
        assert "AUTO_NUDGE" in src
        assert "continue" in src.lower()

    def test_daemon_mode(self):
        src = _git_show(self.COMMIT, "scripts/synapse_heartbeat.sh")
        assert "--daemon" in src

    def test_agent_filter(self):
        """Monitors opencode and vibe agents."""
        src = _git_show(self.COMMIT, "scripts/synapse_heartbeat.sh")
        assert "opencode" in src
        assert "vibe" in src


# ═══ TASK 2: HARNESS-212.2 Polaris Captain ═══
class TestPolarisCaptain212_2:
    COMMIT = "84d96b80"

    def test_commit_exists(self):
        _commit_ok(self.COMMIT, "HARNESS-212.2")

    def test_registry_updated(self):
        """agent_registry.yaml has Polaris fleet entries."""
        result = subprocess.run(
            ["git", "show", "--stat", self.COMMIT],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert "agent_registry.yaml" in result.stdout

    def test_polaris_captain_in_registry(self):
        """Polaris Captain role present."""
        src = _git_show(self.COMMIT, "data/templates/agent_registry.yaml")
        assert "Polaris" in src or "polaris" in src


# ═══ TASK 3: HARNESS-212.3 Synapse Polish ═══
class TestSynapsePolish212_3:
    COMMIT = "c38d8eda"

    def test_commit_exists(self):
        _commit_ok(self.COMMIT, "HARNESS-212.3")

    def test_tmux_color_from_registry(self):
        """spawn_synapse.sh reads tmux_color from registry."""
        src = _git_show(self.COMMIT, "scripts/spawn_synapse.sh")
        assert "tmux_color" in src
        assert "MARKER_212.TMUX_COLOR" in src

    def test_opencode_submit_key(self):
        """synapse_write.sh has per-agent-type submit key routing."""
        src = _git_show(self.COMMIT, "scripts/synapse_write.sh")
        assert "SUBMIT_KEY" in src
        assert "MARKER_212.SUBMIT_KEY" in src

    def test_registry_read_json(self):
        """spawn_synapse.sh reads both model_id and tmux_color from registry."""
        src = _git_show(self.COMMIT, "scripts/spawn_synapse.sh")
        assert "model_id" in src
        assert "tmux_color" in src

    def test_multi_line_uses_submit_key(self):
        """Multi-line prompt uses SUBMIT_KEY variable, not hardcoded Enter."""
        src = _git_show(self.COMMIT, "scripts/synapse_write.sh")
        assert '"$SUBMIT_KEY"' in src
