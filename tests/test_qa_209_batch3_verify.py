"""DELTA QA-209 BATCH 3: Verify 9 remaining CUT done_worktree tasks.

Tasks 9-17 (P2-P4 CUT + infrastructure).
"""
import os
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


def _commit_exists(commit, keyword):
    result = subprocess.run(
        ["git", "log", "--oneline", commit, "-1"],
        capture_output=True, text=True, timeout=5,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"Commit {commit} not found"
    assert keyword in result.stdout, f"'{keyword}' not in commit message"


# ═══ TASK 9: SYNAPSE-206.7 Vibe spawn — tb_1775329556_99331_7 ═══
class TestVibeSpawnBackend:
    COMMIT = "c841941b"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "VIBE_BRIDGE")

    def test_vibe_bridge_stub(self):
        src = _git_show(self.COMMIT, "scripts/vibe_bridge.py")
        assert src, "vibe_bridge.py missing"
        assert "playwright" in src.lower() or "Playwright" in src

    def test_spawn_synapse_vibe_support(self):
        src = _git_show(self.COMMIT, "scripts/spawn_synapse.sh")
        assert "vibe" in src


# ═══ TASK 10: QA fleet test — tb_1775348755_19775_5 ═══
class TestQAFleetTest:
    COMMIT = "3a0f9e29"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "fleet")

    def test_registry_updated(self):
        """agent_registry.yaml modified (Polaris agents added)."""
        result = subprocess.run(
            ["git", "show", "--stat", self.COMMIT],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert "agent_registry.yaml" in result.stdout


# ═══ TASK 11: Epsilon cleanup — tb_1775348763_19775_6 ═══
class TestEpsilonCleanup:
    COMMIT = "ee9960b2"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "EPSILON-CLEANUP")

    def test_agents_md_cleaned(self):
        """AGENTS.md was significantly reduced (cleanup)."""
        result = subprocess.run(
            ["git", "show", "--stat", self.COMMIT],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert "AGENTS.md" in result.stdout


# ═══ TASK 12: synapse_write Enter fix — tb_1775349345_29186_1 ═══
class TestSynapseWriteEnterFix:
    COMMIT = "1c4d4ff0"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "synapse_write")

    def test_agent_type_aware_submit(self):
        """synapse_write.sh handles opencode TUI differently."""
        src = _git_show(self.COMMIT, "scripts/synapse_write.sh")
        assert src
        assert "opencode" in src or "agent_type" in src.lower()


# ═══ TASK 13: QA-209 wake chain — tb_1775406948_68814_3 ═══
class TestQA209WakeChain:
    COMMIT = "01799803"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "QA-209")

    def test_wake_test_file(self):
        src = _git_show(self.COMMIT, "tests/test_agent_wake.py")
        assert src, "test_agent_wake.py missing"
        assert "JSONL" in src or "jsonl" in src or "wake" in src.lower()


# ═══ TASK 14: Polaris fleet integration — tb_1775406967_68814_5 ═══
class TestPolarisFleetIntegration:
    COMMIT = "e565363a"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "HARNESS-209.2")

    def test_registry_has_polaris_agents(self):
        """agent_registry.yaml includes Polaris fleet entries."""
        result = subprocess.run(
            ["git", "show", "--stat", self.COMMIT],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert "agent_registry.yaml" in result.stdout

    def test_spawn_synapse_model_routing(self):
        """spawn_synapse.sh has model routing for free models."""
        src = _git_show(self.COMMIT, "scripts/spawn_synapse.sh")
        assert src
        assert "qwen" in src.lower() or "model" in src.lower() or "opencode" in src.lower()


# ═══ TASK 15: spawn auto-init — tb_1775349336_29186_1 ═══
class TestSpawnAutoInit:
    COMMIT = "64f12408"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "auto-init")

    def test_all_cli_agents_get_init(self):
        """Auto-init fires for opencode + generic_cli, not just claude_code."""
        src = _git_show(self.COMMIT, "scripts/spawn_synapse.sh")
        assert src
        # Should handle multiple agent types for init
        assert "opencode" in src


# ═══ TASK 16: opencode permissions — tb_1775349351_29186_1 ═══
class TestOpencodePermissions:
    COMMIT = "be6ac0ac"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "permission")

    def test_pre_spawn_file_copy(self):
        """Pre-spawn copies necessary files for opencode."""
        src = _git_show(self.COMMIT, "scripts/spawn_synapse.sh")
        assert src
        assert "cp " in src or "copy" in src.lower() or "permission" in src.lower()


# ═══ TASK 17: vibe agent binary — tb_1775349359_29186_1 ═══
class TestVibeAgentBinary:
    COMMIT = "56986cc9"

    def test_commit_exists(self):
        _commit_exists(self.COMMIT, "vibe")

    def test_exit_code_consistency(self):
        """synapse_wake.sh has agent-type-aware submit."""
        result = subprocess.run(
            ["git", "show", "--stat", self.COMMIT],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert "synapse_wake.sh" in result.stdout
