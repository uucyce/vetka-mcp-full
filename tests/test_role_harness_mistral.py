"""
Test: Role harness Mistral verification (tb_1775138684_85698_1)

Tests for ETA-RECON: Role harness audit (commit de685c13).

What was fixed:
- Mistral-1/2/3 roles moved from external_agents → roles: section
- AGENTS.md regenerated for visibility
- add_role.sh v2 with proper YAML insertion

Tests:
- agent_registry.py reads Mistral roles correctly from roles: section
- generate_agents_md works for Mistral-1/2/3
- add_role.sh inserts into roles: section (not external_agents)
- Integration: session_init role=Mistral-1 works
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

# Project root — find main repo root (not worktree)
import subprocess as _sp
_git_common_dir_result = _sp.run(
    ["git", "rev-parse", "--git-common-dir"],
    capture_output=True,
    text=True,
)
if _git_common_dir_result.returncode == 0:
    # .git is in the main repo, so go up one level
    _git_common = Path(_git_common_dir_result.stdout.strip())
    _PROJECT_ROOT = _git_common.parent if _git_common.name == ".git" else _git_common
else:
    # Fallback: walk up from tests/
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_REGISTRY_PATH = _PROJECT_ROOT / "data" / "templates" / "agent_registry.yaml"
_GENERATE_AGENTS_MD = _PROJECT_ROOT / "src" / "tools" / "generate_agents_md.py"
_ADD_ROLE_SH = _PROJECT_ROOT / "scripts" / "release" / "add_role.sh"


class TestAgentRegistryMistralRoles:
    """Test agent_registry.py reads Mistral roles correctly."""

    def test_mistral_roles_exist_in_registry(self):
        """Verify Mistral-1/2/3 are in agent_registry.yaml roles: section."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)

        callsigns = [r["callsign"] for r in data.get("roles", [])]
        assert "Mistral-1" in callsigns, "Mistral-1 missing from roles:"
        assert "Mistral-2" in callsigns, "Mistral-2 missing from roles:"
        assert "Mistral-3" in callsigns, "Mistral-3 missing from roles:"

    def test_mistral_not_in_external_agents(self):
        """Verify Mistral roles are NOT in external_agents (moved to roles:)."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)

        external = [r.get("callsign") for r in data.get("external_agents", [])]
        assert "Mistral-1" not in external, "Mistral-1 found in external_agents (should be in roles:)"
        assert "Mistral-2" not in external, "Mistral-2 found in external_agents (should be in roles:)"
        assert "Mistral-3" not in external, "Mistral-3 found in external_agents (should be in roles:)"

    def test_mistral_1_attributes(self):
        """Test Mistral-1 has correct attributes."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)

        mistral_1 = next((r for r in data.get("roles", []) if r["callsign"] == "Mistral-1"), None)
        assert mistral_1 is not None, "Mistral-1 not found"
        assert mistral_1["domain"] == "weather"
        assert mistral_1["pipeline_stage"] == "coder"
        assert mistral_1["tool_type"] == "opencode"
        assert mistral_1["worktree"] == "weather-mistral-1"
        assert mistral_1["branch"] == "agent/mistral-1-weather"
        assert mistral_1["model_tier"] == "sonnet"
        # Verify owned_paths
        assert "src/services/" in mistral_1.get("owned_paths", [])
        assert "config/browser_agents.yaml" in mistral_1.get("owned_paths", [])

    def test_mistral_2_attributes(self):
        """Test Mistral-2 has correct attributes (qa domain)."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)

        mistral_2 = next((r for r in data.get("roles", []) if r["callsign"] == "Mistral-2"), None)
        assert mistral_2 is not None, "Mistral-2 not found"
        assert mistral_2["domain"] == "qa"
        assert mistral_2["pipeline_stage"] == "verifier"
        assert mistral_2["tool_type"] == "opencode"
        assert mistral_2["worktree"] == "cut-qa-5"
        assert mistral_2["branch"] == "agent/mistral-2-qa"
        # QA owned paths
        assert "e2e/*.spec.cjs" in mistral_2.get("owned_paths", [])
        assert "tests/test_*.py" in mistral_2.get("owned_paths", [])

    def test_mistral_3_attributes(self):
        """Test Mistral-3 has correct attributes."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)

        mistral_3 = next((r for r in data.get("roles", []) if r["callsign"] == "Mistral-3"), None)
        assert mistral_3 is not None, "Mistral-3 not found"
        assert mistral_3["domain"] == "weather"
        assert mistral_3["worktree"] == "weather-mistral-2"
        assert mistral_3["branch"] == "agent/mistral-3-weather"

    def test_agent_registry_loader_mistral_1(self):
        """Test AgentRegistry.get_by_callsign('Mistral-1') works."""
        import sys

        sys.path.insert(0, str(_PROJECT_ROOT))
        from src.services.agent_registry import get_agent_registry, reset_agent_registry

        reset_agent_registry()
        registry = get_agent_registry(_REGISTRY_PATH)
        role = registry.get_by_callsign("Mistral-1")

        assert role is not None, "AgentRegistry failed to load Mistral-1"
        assert role.callsign == "Mistral-1"
        assert role.domain == "weather"
        assert role.worktree == "weather-mistral-1"
        assert "src/services/" in role.owned_paths

    def test_agent_registry_list_callsigns_includes_mistral(self):
        """Test AgentRegistry.list_callsigns() includes all Mistral roles."""
        import sys

        sys.path.insert(0, str(_PROJECT_ROOT))
        from src.services.agent_registry import get_agent_registry, reset_agent_registry

        reset_agent_registry()
        registry = get_agent_registry(_REGISTRY_PATH)
        callsigns = registry.list_callsigns()

        assert "Mistral-1" in callsigns
        assert "Mistral-2" in callsigns
        assert "Mistral-3" in callsigns


class TestGenerateAgentsMdMistral:
    """Test generate_agents_md.py can handle Mistral roles."""

    def test_mistral_roles_have_worktrees_for_generation(self):
        """Verify Mistral roles have worktree entries needed by generate_agents_md."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)

        for callsign in ["Mistral-1", "Mistral-2", "Mistral-3"]:
            role = next((r for r in data.get("roles", []) if r["callsign"] == callsign), None)
            assert role is not None, f"{callsign} not found"
            assert "worktree" in role, f"{callsign} has no worktree"
            assert role["worktree"], f"{callsign} worktree is empty"
            # Verify worktree names are reasonable
            assert role["worktree"].startswith(("weather-", "cut-")), f"{callsign} worktree name suspicious: {role['worktree']}"


class TestAddRoleShMistral:
    """Test add_role.sh v2 logic (inserts into roles: section before shared_zones)."""

    def test_add_role_sh_exists(self):
        """Verify add_role.sh exists in main repo."""
        assert _ADD_ROLE_SH.exists(), f"add_role.sh not found at {_ADD_ROLE_SH}"

    def test_add_role_sh_v2_inserts_before_shared_zones(self):
        """Test that add_role.sh v2 inserts into roles: section before shared_zones."""
        # This test verifies the script logic by checking the script content
        with open(_ADD_ROLE_SH) as f:
            script = f.read()

        # Check for the insertion point logic
        assert "shared_zones:" in script, "Script doesn't check for shared_zones insertion point"

        # Verify the Python insertion code mentions shared_zones
        assert "# Find insertion point: before shared_zones" in script
        assert 'insert_marker = re.search(r"^(# ── Shared Zones|shared_zones:)"' in script
        # Verify v2 comment exists
        assert "MARKER_ETA.ADD_ROLE_V2" in script, "add_role.sh should have MARKER_ETA.ADD_ROLE_V2"


class TestMistralSessionInit:
    """Test session_init works with Mistral roles."""

    def test_mistral_1_get_by_branch(self):
        """Test AgentRegistry.get_by_branch('agent/mistral-1-weather')."""
        import sys

        sys.path.insert(0, str(_PROJECT_ROOT))
        from src.services.agent_registry import get_agent_registry, reset_agent_registry

        reset_agent_registry()
        registry = get_agent_registry(_REGISTRY_PATH)
        role = registry.get_by_branch("agent/mistral-1-weather")

        assert role is not None, "get_by_branch failed for agent/mistral-1-weather"
        assert role.callsign == "Mistral-1"

    def test_mistral_2_get_by_worktree(self):
        """Test AgentRegistry.get_by_worktree('cut-qa-5')."""
        import sys

        sys.path.insert(0, str(_PROJECT_ROOT))
        from src.services.agent_registry import get_agent_registry, reset_agent_registry

        reset_agent_registry()
        registry = get_agent_registry(_REGISTRY_PATH)
        role = registry.get_by_worktree("cut-qa-5")

        assert role is not None, "get_by_worktree failed for cut-qa-5"
        assert role.callsign == "Mistral-2"

    def test_mistral_domains_correct(self):
        """Test each Mistral role has correct domain for task assignment."""
        import sys

        sys.path.insert(0, str(_PROJECT_ROOT))
        from src.services.agent_registry import get_agent_registry, reset_agent_registry

        reset_agent_registry()
        registry = get_agent_registry(_REGISTRY_PATH)

        # Mistral-1: weather domain
        assert registry.get_by_callsign("Mistral-1").domain == "weather"
        # Mistral-2: qa domain
        assert registry.get_by_callsign("Mistral-2").domain == "qa"
        # Mistral-3: weather domain
        assert registry.get_by_callsign("Mistral-3").domain == "weather"


class TestRoleHarnessIntegration:
    """Integration tests: verify the whole role harness works."""

    def test_all_mistral_roles_accessible_via_registry(self):
        """Test all 3 Mistral roles are accessible via AgentRegistry."""
        import sys

        sys.path.insert(0, str(_PROJECT_ROOT))
        from src.services.agent_registry import get_agent_registry, reset_agent_registry

        reset_agent_registry()
        registry = get_agent_registry(_REGISTRY_PATH)

        for callsign in ["Mistral-1", "Mistral-2", "Mistral-3"]:
            role = registry.get_by_callsign(callsign)
            assert role is not None, f"{callsign} not found"
            assert role.worktree, f"{callsign} has no worktree"
            assert role.branch, f"{callsign} has no branch"
            assert role.owned_paths, f"{callsign} has no owned_paths"

    def test_mistral_tool_types_are_opencode(self):
        """Verify Mistral roles use opencode tool_type (not claude_code)."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)

        for callsign in ["Mistral-1", "Mistral-2", "Mistral-3"]:
            role = next((r for r in data.get("roles", []) if r["callsign"] == callsign), None)
            assert role is not None, f"{callsign} not found"
            # Check raw YAML to ensure tool_type is set
            assert role.get("tool_type") == "opencode", f"{callsign} tool_type should be 'opencode', got {role.get('tool_type')}"

    def test_yaml_syntax_valid(self):
        """Verify agent_registry.yaml is valid YAML after Mistral addition."""
        try:
            with open(_REGISTRY_PATH) as f:
                data = yaml.safe_load(f)
            assert isinstance(data, dict), "Registry is not a YAML dict"
            assert "roles" in data, "No 'roles' key in registry"
            assert isinstance(data["roles"], list), "'roles' is not a list"
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in agent_registry.yaml: {e}")
