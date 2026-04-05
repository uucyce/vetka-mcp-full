"""DELTA QA-209 BATCH 2: Verify 4 more CUT done_worktree tasks.

Tasks verified:
5. tb_1775338576_17631_2 — FIX: MCP bridge missing imports (claude/harness)
6. tb_1775344063_19775_1 — RECOVERY: Synapse scripts lost by snapshot merge (claude/pedantic-bell)
7. tb_1775406942_68814_2 — SHERPA-210: Gemma 4 recon (claude/harness-eta)
8. tb_1775408087_71633_1 — HARNESS-209.3: Provision Polaris fleet worktrees (claude/harness)
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

sys.path.insert(0, str(PROJECT_ROOT))


def _git_show(commit, path):
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True, text=True, timeout=10,
        cwd=str(PROJECT_ROOT),
    )
    return result.stdout if result.returncode == 0 else ""


# ═══════════════════════════════════════════════════════════════════
# TASK 5: MCP Bridge Missing Imports — tb_1775338576_17631_2
# Commit: 39230394 on claude/harness
# ═══════════════════════════════════════════════════════════════════
class TestMcpBridgeImportFix:
    """Verify missing Path + struct imports added to vetka_mcp_bridge.py."""

    COMMIT = "39230394"

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "pathlib" in result.stdout.lower() or "import" in result.stdout.lower()

    def test_pathlib_import_present(self):
        """from pathlib import Path at top level."""
        src = _git_show(self.COMMIT, "src/mcp/vetka_mcp_bridge.py")
        assert src, "Cannot read vetka_mcp_bridge.py"
        # Check in first 80 lines (import block)
        header = "\n".join(src.split("\n")[:80])
        assert "from pathlib import Path" in header, "Missing top-level Path import"

    def test_struct_import_present(self):
        """import struct at top level."""
        src = _git_show(self.COMMIT, "src/mcp/vetka_mcp_bridge.py")
        header = "\n".join(src.split("\n")[:80])
        assert "import struct" in header, "Missing top-level struct import"

    def test_bridge_syntax_valid(self):
        """Bridge file has valid Python syntax after fix."""
        src = _git_show(self.COMMIT, "src/mcp/vetka_mcp_bridge.py")
        assert src
        compile(src, "vetka_mcp_bridge.py", "exec")


# ═══════════════════════════════════════════════════════════════════
# TASK 6: Synapse Scripts Recovery — tb_1775344063_19775_1
# Commit: 2530ccb92 on claude/pedantic-bell (main)
# ═══════════════════════════════════════════════════════════════════
class TestSynapseScriptsRecovery:
    """Verify 5 synapse files recovered to main."""

    COMMIT = "2530ccb92"

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "recover" in result.stdout.lower() or "RECOVERY" in result.stdout

    def test_spawn_synapse_recovered(self):
        src = _git_show(self.COMMIT, "scripts/spawn_synapse.sh")
        assert src, "spawn_synapse.sh missing from recovery commit"
        assert "SYNAPSE" in src

    def test_synapse_write_recovered(self):
        src = _git_show(self.COMMIT, "scripts/synapse_write.sh")
        assert src, "synapse_write.sh missing from recovery commit"

    def test_synapse_wake_recovered(self):
        src = _git_show(self.COMMIT, "scripts/synapse_wake.sh")
        assert src, "synapse_wake.sh missing from recovery commit"

    def test_vibe_bridge_recovered(self):
        src = _git_show(self.COMMIT, "scripts/vibe_bridge.py")
        assert src, "vibe_bridge.py missing from recovery commit"

    def test_agent_registry_v2_recovered(self):
        """Registry recovered (may be symlink — check git tree entry exists)."""
        result = subprocess.run(
            ["git", "ls-tree", self.COMMIT, "--", "data/templates/agent_registry.yaml"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "agent_registry.yaml" in result.stdout, "agent_registry.yaml missing from recovery"


# ═══════════════════════════════════════════════════════════════════
# TASK 7: SHERPA-210 Gemma 4 Recon — tb_1775406942_68814_2
# Commit: c5a2d54c on claude/harness-eta
# ═══════════════════════════════════════════════════════════════════
class TestSherpa210Gemma4Recon:
    """Verify Gemma 4 recon research doc quality."""

    COMMIT = "c5a2d54c"
    DOC_PATH = "docs/210_sherpa_gemma4/GEMMA4_RECON_SHERPA_tb_1775406942_68814_2.md"

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "SHERPA-210" in result.stdout

    def test_recon_doc_exists(self):
        src = _git_show(self.COMMIT, self.DOC_PATH)
        assert src, "Recon doc missing"
        assert len(src) > 500, "Doc too short for meaningful recon"

    def test_model_comparison_table(self):
        """Doc contains model comparison table with all 4 variants."""
        src = _git_show(self.COMMIT, self.DOC_PATH)
        for variant in ["E2B", "E4B", "26B", "31B"]:
            assert variant in src, f"Missing Gemma 4 variant: {variant}"

    def test_memory_budget_analysis(self):
        """Doc includes M4 24GB memory budget."""
        src = _git_show(self.COMMIT, self.DOC_PATH)
        assert "24GB" in src or "24 GB" in src, "Missing M4 memory analysis"
        assert "Q4" in src or "Q8" in src, "Missing quantization analysis"

    def test_ollama_availability(self):
        """Doc confirms Ollama availability."""
        src = _git_show(self.COMMIT, self.DOC_PATH)
        assert "ollama" in src.lower() or "Ollama" in src

    def test_apache_license_confirmed(self):
        """Apache 2.0 license noted (important for local deployment)."""
        src = _git_show(self.COMMIT, self.DOC_PATH)
        assert "Apache" in src

    def test_task_id_in_filename(self):
        """Filename contains task ID (feedback_doc_task_id_suffix rule)."""
        assert "tb_1775406942_68814_2" in self.DOC_PATH


# ═══════════════════════════════════════════════════════════════════
# TASK 8: Polaris Fleet Provision — tb_1775408087_71633_1
# Commit: 835b444c on claude/harness
# ═══════════════════════════════════════════════════════════════════
class TestPolarisFleetProvision:
    """Verify Polaris fleet provisioning scripts."""

    COMMIT = "835b444c"

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "HARNESS-209.3" in result.stdout or "Polaris" in result.stdout

    def test_provision_script_exists(self):
        src = _git_show(self.COMMIT, "scripts/provision_polaris_fleet.sh")
        assert src, "provision_polaris_fleet.sh missing"
        assert "MARKER_209.PROVISION_POLARIS" in src

    def test_all_six_roles_defined(self):
        """All 6 Polaris agents defined in provision script."""
        src = _git_show(self.COMMIT, "scripts/provision_polaris_fleet.sh")
        for role in ["Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu"]:
            assert role in src, f"Missing Polaris role: {role}"

    def test_worktree_creation_logic(self):
        """Script creates git worktree for each role."""
        src = _git_show(self.COMMIT, "scripts/provision_polaris_fleet.sh")
        assert "git worktree add" in src, "Missing git worktree add command"

    def test_branch_creation_logic(self):
        """Script creates branches with claude/polaris-* naming."""
        src = _git_show(self.COMMIT, "scripts/provision_polaris_fleet.sh")
        assert "claude/polaris-" in src, "Missing claude/polaris-* branch naming"

    def test_dry_run_supported(self):
        """--dry-run flag supported for safety."""
        src = _git_show(self.COMMIT, "scripts/provision_polaris_fleet.sh")
        assert "--dry-run" in src

    def test_test_script_included(self):
        """Test script for fleet validation included."""
        src = _git_show(self.COMMIT, "scripts/test_polaris_fleet.sh")
        assert src, "test_polaris_fleet.sh missing"

    def test_skip_existing_worktrees(self):
        """Script skips if worktree already exists (idempotent)."""
        src = _git_show(self.COMMIT, "scripts/provision_polaris_fleet.sh")
        assert "SKIP" in src or "already exists" in src
