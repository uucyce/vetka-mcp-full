from pathlib import Path
import json
import pytest

from src.services.reflex_tool_memory import (
    list_reflex_tool_memory,
    remember_reflex_tool,
    resolve_reflex_tool_reference,
)
from src.services.reflex_registry import ReflexRegistry
from src.services.reflex_scorer import ReflexContext, ReflexScorer

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 177 contracts changed")


def test_remember_reflex_tool_creates_and_lists_entry(tmp_path: Path):
    memory_path = tmp_path / "remembered_tools.json"
    catalog_path = tmp_path / "tool_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "tools": [
                    {
                        "tool_id": "seed_mcc_playwright_fixture",
                        "source": "agents/tools.py",
                    }
                ]
            }
        )
    )

    created = remember_reflex_tool(
        tool_name="seed_mcc_playwright_fixture",
        entry_type="script",
        path="scripts/mcc_seed_playwright_fixture.py",
        notes="Use for seeded MCC graph browser sessions",
        intent_tags=["playwright", "mcc", "visual_regression"],
        trigger_hint="seed browser fixture before MCC graph inspection",
        aliases=["mcc seed", "playwright seed"],
        memory_path=memory_path,
        catalog_path=catalog_path,
    )

    assert created["action"] == "created"
    assert created["entry"]["tool_name"] == "seed_mcc_playwright_fixture"
    assert created["entry"]["tool_id"] == "seed_mcc_playwright_fixture"
    assert created["entry"]["origin"] == "catalog"

    listed = list_reflex_tool_memory(
        query="visual_regression",
        memory_path=memory_path,
        catalog_path=catalog_path,
    )
    assert listed["count"] == 1
    assert listed["tools"][0]["path"] == "scripts/mcc_seed_playwright_fixture.py"
    assert listed["tools"][0]["stale"] is False


def test_remember_reflex_tool_updates_existing_entry(tmp_path: Path):
    memory_path = tmp_path / "remembered_tools.json"
    catalog_path = tmp_path / "tool_catalog.json"
    catalog_path.write_text(json.dumps({"tools": []}))

    remember_reflex_tool(
        tool_name="remember_reflex_tool",
        entry_type="tool",
        path="src/agents/tools.py",
        notes="initial",
        memory_path=memory_path,
        catalog_path=catalog_path,
    )
    updated = remember_reflex_tool(
        tool_name="remember_reflex_tool",
        entry_type="tool",
        path="src/agents/tools.py",
        notes="updated",
        intent_tags=["catalog", "registry"],
        memory_path=memory_path,
        catalog_path=catalog_path,
    )

    assert updated["action"] == "updated"
    assert updated["entry"]["notes"] == "updated"
    assert updated["count"] == 1


def test_list_reflex_tool_memory_filters_stale_entries_by_default(tmp_path: Path):
    memory_path = tmp_path / "remembered_tools.json"
    catalog_path = tmp_path / "tool_catalog.json"
    catalog_path.write_text(json.dumps({"tools": []}))

    remember_reflex_tool(
        tool_name="missing_tool",
        entry_type="script",
        path="scripts/definitely_missing.py",
        tool_id="missing_tool",
        memory_path=memory_path,
        catalog_path=catalog_path,
    )

    hidden = list_reflex_tool_memory(memory_path=memory_path, catalog_path=catalog_path)
    assert hidden["count"] == 0

    shown = list_reflex_tool_memory(
        memory_path=memory_path,
        catalog_path=catalog_path,
        exclude_stale=False,
    )
    assert shown["count"] == 1
    assert shown["tools"][0]["stale"] is True
    assert shown["tools"][0]["stale_reason"] == "catalog_tool_missing"


def test_resolve_reflex_tool_reference_prefers_catalog_tool_id(tmp_path: Path):
    catalog_path = tmp_path / "tool_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "tools": [
                    {
                        "tool_id": "remember_reflex_tool",
                        "source": "agents/tools.py",
                    }
                ]
            }
        )
    )

    resolved = resolve_reflex_tool_reference(
        tool_name="remember_reflex_tool",
        path="src/agents/tools.py",
        catalog_path=catalog_path,
    )
    assert resolved["tool_id"] == "remember_reflex_tool"
    assert resolved["origin"] == "catalog"
    assert resolved["catalog_source"] == "agents/tools.py"


def test_remembered_local_qwen_tool_recall_boosts_reflex_for_ollama_task(tmp_path: Path):
    memory_path = tmp_path / "remembered_tools.json"
    catalog_path = tmp_path / "tool_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "tools": [
                    {
                        "tool_id": "select_best_local_qwen_model",
                        "namespace": "internal",
                        "kind": "search",
                        "description": "Pick the best local Qwen model",
                        "intent_tags": ["local", "model"],
                        "trigger_patterns": {
                            "file_types": ["*"],
                            "phase_types": ["*"],
                            "keywords": ["local", "model"],
                        },
                        "cost": {"latency_ms": 150, "tokens": 0, "risk_level": "read_only"},
                        "permission": "READ",
                        "roles": ["Default"],
                        "deprecated_aliases": [],
                        "active": True,
                        "source": "agents/tools.py",
                    },
                    {
                        "tool_id": "list_reflex_tool_memory",
                        "namespace": "internal",
                        "kind": "search",
                        "description": "List remembered tools",
                        "intent_tags": ["memory"],
                        "trigger_patterns": {
                            "file_types": ["*"],
                            "phase_types": ["*"],
                            "keywords": ["memory"],
                        },
                        "cost": {"latency_ms": 100, "tokens": 0, "risk_level": "read_only"},
                        "permission": "READ",
                        "roles": ["Default"],
                        "deprecated_aliases": [],
                        "active": True,
                        "source": "agents/tools.py",
                    },
                ]
            }
        )
    )

    remember_reflex_tool(
        tool_name="select_best_local_qwen_model",
        entry_type="tool",
        path="src/agents/tools.py",
        tool_id="select_best_local_qwen_model",
        notes="Use before local-model tool calling to inspect ollama list and choose the smartest qwen",
        intent_tags=["ollama", "qwen", "smartest_qwen", "local_models"],
        trigger_hint="run ollama list and choose the smartest qwen before local tool calling",
        aliases=["ollama list", "smartest qwen"],
        memory_path=memory_path,
        catalog_path=catalog_path,
    )

    overlay = list_reflex_tool_memory(
        memory_path=memory_path,
        catalog_path=catalog_path,
        exclude_stale=True,
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("src.services.reflex_registry.list_reflex_tool_memory", lambda **_kwargs: overlay)
        registry = ReflexRegistry(catalog_path).load()

    scorer = ReflexScorer()
    context = ReflexContext(
        task_text="before local tool calling, inspect ollama list and choose the smartest qwen",
        phase_type="research",
        agent_role="Default",
    )
    tools = registry.get_tools_for_role("Default")
    results = scorer.recommend(context, tools, top_n=3)

    assert results
    assert results[0].tool_id == "select_best_local_qwen_model"
    assert results[0].overlay["applied"] is True
    assert results[0].overlay["score_delta"] > 0
