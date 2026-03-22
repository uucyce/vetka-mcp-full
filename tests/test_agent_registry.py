"""
MARKER_ZETA.D1: Unit tests for AgentRegistry.

Tests:
- YAML loading and parsing
- Lookup by callsign, branch, worktree, domain
- File ownership validation (owned, blocked, shared zones)
- Domain match validation
- Edge cases (unknown callsign, empty paths, case insensitivity)
"""

import pytest
from pathlib import Path

from src.services.agent_registry import (
    AgentRegistry,
    AgentRole,
    OwnershipResult,
    SharedZone,
    reset_agent_registry,
    get_agent_registry,
)

# Use real registry YAML from project
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "templates" / "agent_registry.yaml"


@pytest.fixture
def registry():
    """Load real agent_registry.yaml."""
    reset_agent_registry()
    return AgentRegistry(REGISTRY_PATH)


# ── Loading Tests ───────────────────────────────────────────


class TestRegistryLoading:
    def test_loads_all_five_roles(self, registry):
        assert len(registry.roles) == 5

    def test_version_and_project(self, registry):
        assert registry.version == "1.0"
        assert registry.project_id == "CUT"

    def test_all_callsigns_present(self, registry):
        callsigns = {r.callsign for r in registry.roles}
        assert callsigns == {"Alpha", "Beta", "Gamma", "Delta", "Commander"}

    def test_all_domains_present(self, registry):
        domains = {r.domain for r in registry.roles}
        assert domains == {"engine", "media", "ux", "qa", "architect"}

    def test_roles_are_frozen(self, registry):
        role = registry.get_by_callsign("Alpha")
        with pytest.raises(AttributeError):
            role.callsign = "Omega"

    def test_shared_zones_loaded(self, registry):
        zones = registry.shared_zones
        assert len(zones) >= 3  # useCutHotkeys, DockviewLayout, useCutEditorStore
        file_names = [z.file for z in zones]
        assert any("useCutHotkeys" in f for f in file_names)

    def test_each_role_has_owned_paths(self, registry):
        for role in registry.roles:
            assert len(role.owned_paths) > 0, f"{role.callsign} has no owned_paths"

    def test_each_role_has_branch(self, registry):
        for role in registry.roles:
            assert role.branch, f"{role.callsign} has no branch"

    def test_each_role_has_worktree(self, registry):
        for role in registry.roles:
            assert role.worktree, f"{role.callsign} has no worktree"


# ── Lookup Tests ────────────────────────────────────────────


class TestLookups:
    def test_get_by_callsign(self, registry):
        role = registry.get_by_callsign("Alpha")
        assert role is not None
        assert role.domain == "engine"
        assert role.worktree == "cut-engine"

    def test_get_by_callsign_case_insensitive(self, registry):
        role = registry.get_by_callsign("alpha")
        assert role is not None
        assert role.callsign == "Alpha"

    def test_get_by_callsign_unknown(self, registry):
        assert registry.get_by_callsign("Omega") is None

    def test_get_by_branch(self, registry):
        role = registry.get_by_branch("claude/cut-media")
        assert role is not None
        assert role.callsign == "Beta"

    def test_get_by_branch_unknown(self, registry):
        assert registry.get_by_branch("claude/unknown") is None

    def test_get_by_worktree(self, registry):
        role = registry.get_by_worktree("cut-qa")
        assert role is not None
        assert role.callsign == "Delta"

    def test_get_by_domain(self, registry):
        role = registry.get_by_domain("ux")
        assert role is not None
        assert role.callsign == "Gamma"

    def test_get_by_domain_case_insensitive(self, registry):
        role = registry.get_by_domain("ENGINE")
        assert role is not None
        assert role.callsign == "Alpha"

    def test_all_branches_unique(self, registry):
        branches = [r.branch for r in registry.roles]
        assert len(branches) == len(set(branches))

    def test_delta_branch_legacy(self, registry):
        """Delta uses legacy branch naming (worktree-cut-qa, not claude/cut-qa)."""
        role = registry.get_by_callsign("Delta")
        assert role.branch == "worktree-cut-qa"


# ── Ownership Validation Tests ──────────────────────────────


class TestOwnershipValidation:
    def test_alpha_owns_timeline_store(self, registry):
        result = registry.validate_file_ownership(
            "Alpha", "client/src/store/useTimelineInstanceStore.ts"
        )
        assert result.is_owned is True
        assert result.is_blocked is False

    def test_alpha_blocked_from_menubar(self, registry):
        result = registry.validate_file_ownership(
            "Alpha", "client/src/components/cut/MenuBar.tsx"
        )
        assert result.is_blocked is True

    def test_alpha_blocked_from_e2e(self, registry):
        result = registry.validate_file_ownership(
            "Alpha", "e2e/cut_smoke.spec.cjs"
        )
        assert result.is_blocked is True

    def test_beta_owns_codec_probe(self, registry):
        result = registry.validate_file_ownership(
            "Beta", "src/services/cut_codec_probe.py"
        )
        assert result.is_owned is True

    def test_beta_blocked_from_hotkeys(self, registry):
        result = registry.validate_file_ownership(
            "Beta", "client/src/hooks/useCutHotkeys.ts"
        )
        assert result.is_blocked is True

    def test_gamma_owns_menubar(self, registry):
        result = registry.validate_file_ownership(
            "Gamma", "client/src/components/cut/MenuBar.tsx"
        )
        assert result.is_owned is True

    def test_gamma_owns_panel_glob(self, registry):
        result = registry.validate_file_ownership(
            "Gamma", "client/src/components/cut/panels/SourceBrowserPanel.tsx"
        )
        assert result.is_owned is True

    def test_gamma_blocked_from_timeline_store(self, registry):
        result = registry.validate_file_ownership(
            "Gamma", "client/src/store/useTimelineInstanceStore.ts"
        )
        assert result.is_blocked is True

    def test_delta_owns_e2e_spec(self, registry):
        result = registry.validate_file_ownership(
            "Delta", "e2e/cut_smoke.spec.cjs"
        )
        assert result.is_owned is True

    def test_delta_blocked_from_components(self, registry):
        result = registry.validate_file_ownership(
            "Delta", "client/src/components/cut/TimelineTrackView.tsx"
        )
        assert result.is_blocked is True

    def test_commander_owns_docs(self, registry):
        result = registry.validate_file_ownership(
            "Commander", "docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP.md"
        )
        assert result.is_owned is True

    def test_unknown_callsign_returns_neutral(self, registry):
        result = registry.validate_file_ownership(
            "Omega", "any/file.ts"
        )
        assert result.is_owned is False
        assert result.is_blocked is False

    def test_alpha_tauri_directory_ownership(self, registry):
        result = registry.validate_file_ownership(
            "Alpha", "client/src-tauri/tauri.conf.json"
        )
        assert result.is_owned is True

    def test_shared_zone_detected(self, registry):
        result = registry.validate_file_ownership(
            "Alpha", "client/src/hooks/useCutHotkeys.ts"
        )
        assert result.shared_zone is not None
        assert "Alpha" in result.shared_zone.owners
        assert "Gamma" in result.shared_zone.owners


# ── Domain Match Tests ──────────────────────────────────────


class TestDomainMatch:
    def test_alpha_matches_engine(self, registry):
        matches, msg = registry.validate_domain_match("Alpha", "engine")
        assert matches is True

    def test_alpha_mismatches_qa(self, registry):
        matches, msg = registry.validate_domain_match("Alpha", "qa")
        assert matches is False
        assert "mismatch" in msg.lower()

    def test_unknown_callsign_passes(self, registry):
        matches, msg = registry.validate_domain_match("Omega", "engine")
        assert matches is True  # permissive for unknown

    def test_empty_domain_passes(self, registry):
        matches, msg = registry.validate_domain_match("Alpha", "")
        assert matches is True

    def test_domain_case_insensitive(self, registry):
        matches, _ = registry.validate_domain_match("Beta", "MEDIA")
        assert matches is True


# ── Singleton Tests ─────────────────────────────────────────


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        reset_agent_registry()
        r1 = get_agent_registry(REGISTRY_PATH)
        r2 = get_agent_registry()
        assert r1 is r2

    def test_reset_clears_singleton(self):
        reset_agent_registry()
        r1 = get_agent_registry(REGISTRY_PATH)
        reset_agent_registry()
        r2 = get_agent_registry(REGISTRY_PATH)
        assert r1 is not r2
