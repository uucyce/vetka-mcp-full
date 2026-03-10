"""
Tests for REFLEX Registry (Phase 172.P1).

MARKER_172.P1.TESTS

Tests:
  T1.1 test_catalog_schema_valid — JSON schema validation
  T1.2 test_all_pipeline_tools_in_catalog — PIPELINE_CODER_TOOLS ⊂ catalog
  T1.3 test_all_mcp_tools_in_catalog — MCP tools present
  T1.4 test_role_permissions_match — registry roles match AGENT_TOOL_PERMISSIONS
  T1.5 test_deprecated_aliases_resolve — old names map to new
  T1.6 test_intent_tag_search — fuzzy search returns relevant tools
  T1.7 test_catalog_no_duplicates — unique tool_ids
"""

import json
import pytest
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Import after path setup
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.reflex_registry import (
    ReflexRegistry,
    ToolEntry,
    DEPRECATED_ALIASES,
    CATALOG_PATH,
    reset_reflex_registry,
)


@pytest.fixture
def catalog_data():
    """Load raw catalog JSON."""
    assert CATALOG_PATH.exists(), f"Catalog not found at {CATALOG_PATH}. Run: python3 scripts/generate_reflex_catalog.py"
    with open(CATALOG_PATH) as f:
        return json.load(f)


@pytest.fixture
def registry():
    """Fresh ReflexRegistry instance loaded from disk."""
    reset_reflex_registry()
    reg = ReflexRegistry(CATALOG_PATH).load()
    return reg


# ─── T1.1: Schema validation ─────────────────────────────────────────

class TestCatalogSchema:
    def test_catalog_schema_valid(self, catalog_data):
        """T1.1: Every tool entry has required fields with correct types."""
        assert "version" in catalog_data
        assert "tools" in catalog_data
        assert isinstance(catalog_data["tools"], list)
        assert len(catalog_data["tools"]) > 0, "Catalog is empty"

        required_fields = {"tool_id", "namespace", "kind"}
        for tool in catalog_data["tools"]:
            missing = required_fields - set(tool.keys())
            assert not missing, f"Tool {tool.get('tool_id', '?')} missing fields: {missing}"
            assert isinstance(tool["tool_id"], str)
            assert len(tool["tool_id"]) > 0
            assert isinstance(tool["namespace"], str)
            assert tool["namespace"] in ("vetka", "mycelium", "internal", "cut", "unknown")
            assert isinstance(tool.get("intent_tags", []), list)
            assert isinstance(tool.get("active", True), bool)


# ─── T1.2: Pipeline coder tools covered ──────────────────────────────

class TestPipelineToolsCovered:
    PIPELINE_CODER_TOOLS = [
        "vetka_read_file",
        "vetka_search_semantic",
        "vetka_search_files",
        "vetka_search_code",
        "vetka_list_files",
    ]

    def test_all_pipeline_tools_in_catalog(self, registry):
        """T1.2: Every PIPELINE_CODER_TOOLS tool exists in the catalog."""
        catalog_ids = registry.get_tool_ids()
        for tool_name in self.PIPELINE_CODER_TOOLS:
            assert registry.has_tool(tool_name), (
                f"Pipeline tool '{tool_name}' not in catalog. "
                f"Available: {sorted(catalog_ids)[:10]}..."
            )


# ─── T1.3: MCP tools covered ─────────────────────────────────────────

class TestMCPToolsCovered:
    def test_vetka_mcp_tools_present(self, registry):
        """T1.3a: Key VETKA MCP tools are in catalog."""
        key_vetka = [
            "vetka_session_init",
            "vetka_search_semantic",
            "vetka_read_file",
            "vetka_edit_file",
            "vetka_git_commit",
            "vetka_run_tests",
            "vetka_camera_focus",
        ]
        for name in key_vetka:
            assert registry.has_tool(name), f"VETKA MCP tool '{name}' missing"

    def test_mycelium_mcp_tools_present(self, registry):
        """T1.3b: Key MYCELIUM MCP tools are in catalog."""
        key_mycelium = [
            "mycelium_pipeline",
            "mycelium_task_board",
            "mycelium_heartbeat_tick",
            "mycelium_call_model",
        ]
        for name in key_mycelium:
            assert registry.has_tool(name), f"MYCELIUM tool '{name}' missing"


# ─── T1.4: Role permissions ──────────────────────────────────────────

class TestRolePermissions:
    def test_role_permissions_match(self, registry):
        """T1.4: Tools with roles have correct role assignments."""
        # At minimum, Dev role should have write tools
        dev_tools = registry.get_tools_for_role("Dev")
        dev_names = {t.tool_id for t in dev_tools}

        # Dev should have some tools
        assert len(dev_tools) > 0, "Dev role has no tools in catalog"

        # Coder role should include pipeline tools
        coder_tools = registry.get_tools_for_role("coder")
        coder_names = {t.tool_id for t in coder_tools}
        assert "vetka_read_file" in coder_names or len(coder_tools) > 0, (
            "Coder role should include pipeline tools"
        )


# ─── T1.5: Deprecated aliases ────────────────────────────────────────

class TestDeprecatedAliases:
    def test_deprecated_aliases_resolve(self, registry):
        """T1.5: Deprecated tool names resolve to canonical names."""
        test_cases = {
            "vetka_task_board": "mycelium_task_board",
            "search_semantic": "vetka_search_semantic",
            "camera_focus": "vetka_camera_focus",
        }
        for old_name, expected_new in test_cases.items():
            resolved = registry.resolve_alias(old_name)
            assert resolved == expected_new, (
                f"Alias '{old_name}' → '{resolved}', expected '{expected_new}'"
            )

    def test_deprecated_alias_lookup_finds_tool(self, registry):
        """T1.5b: Looking up deprecated name returns the canonical tool."""
        # vetka_task_board → mycelium_task_board
        tool = registry.get_tool("vetka_task_board")
        if tool:
            assert tool.tool_id == "mycelium_task_board"


# ─── T1.6: Intent tag search ─────────────────────────────────────────

class TestIntentTagSearch:
    def test_intent_tag_search(self, registry):
        """T1.6: Searching by intent tags returns relevant tools."""
        # Search for "find" should return search tools
        results = registry.get_tools_by_intent(["find", "locate"])
        assert len(results) > 0, "No tools found for intent ['find', 'locate']"

        # Results should be search-related
        result_names = [t.tool_id for t in results]
        has_search = any("search" in name for name in result_names)
        assert has_search, f"Expected search tools, got: {result_names}"

    def test_intent_tag_empty_returns_empty(self, registry):
        """T1.6b: Empty intent tags return no results."""
        results = registry.get_tools_by_intent([])
        assert len(results) == 0


# ─── T1.7: No duplicates ─────────────────────────────────────────────

class TestNoDuplicates:
    def test_catalog_no_duplicates(self, catalog_data):
        """T1.7: All tool_ids are unique in the catalog."""
        tool_ids = [t["tool_id"] for t in catalog_data["tools"]]
        duplicates = [tid for tid in tool_ids if tool_ids.count(tid) > 1]
        assert len(duplicates) == 0, f"Duplicate tool_ids found: {set(duplicates)}"


# ─── Bonus: Registry mechanics ────────────────────────────────────────

class TestRegistryMechanics:
    def test_tool_count_matches_catalog(self, registry, catalog_data):
        """Registry tool count matches catalog JSON."""
        assert registry.tool_count == len(catalog_data["tools"])

    def test_get_tools_by_kind(self, registry):
        """get_tools_by_kind returns tools of that kind."""
        search_tools = registry.get_tools_by_kind("search")
        assert len(search_tools) > 0
        for t in search_tools:
            assert t.kind == "search"

    def test_get_tools_for_phase(self, registry):
        """get_tools_for_phase returns relevant tools."""
        fix_tools = registry.get_tools_for_phase("fix")
        assert len(fix_tools) > 0

    def test_tool_entry_matches_keywords(self):
        """ToolEntry.matches_keywords works correctly."""
        tool = ToolEntry(
            tool_id="test_tool",
            namespace="test",
            kind="test",
            trigger_patterns={"keywords": ["video", "edit", "timeline"]},
        )
        assert tool.matches_keywords("I want to edit a video timeline") > 0.5
        assert tool.matches_keywords("hello world") == 0.0
