from pathlib import Path

from src.services.reflex_tool_memory import (
    list_reflex_tool_memory,
    remember_reflex_tool,
)


def test_remember_reflex_tool_creates_and_lists_entry(tmp_path: Path):
    memory_path = tmp_path / "remembered_tools.json"

    created = remember_reflex_tool(
        tool_name="seed_mcc_playwright_fixture",
        entry_type="script",
        path="scripts/mcc_seed_playwright_fixture.py",
        notes="Use for seeded MCC graph browser sessions",
        intent_tags=["playwright", "mcc", "visual_regression"],
        trigger_hint="seed browser fixture before MCC graph inspection",
        aliases=["mcc seed", "playwright seed"],
        memory_path=memory_path,
    )

    assert created["action"] == "created"
    assert created["entry"]["tool_name"] == "seed_mcc_playwright_fixture"

    listed = list_reflex_tool_memory(query="visual_regression", memory_path=memory_path)
    assert listed["count"] == 1
    assert listed["tools"][0]["path"] == "scripts/mcc_seed_playwright_fixture.py"


def test_remember_reflex_tool_updates_existing_entry(tmp_path: Path):
    memory_path = tmp_path / "remembered_tools.json"

    remember_reflex_tool(
        tool_name="remember_reflex_tool",
        entry_type="tool",
        path="src/agents/tools.py",
        notes="initial",
        memory_path=memory_path,
    )
    updated = remember_reflex_tool(
        tool_name="remember_reflex_tool",
        entry_type="tool",
        path="src/agents/tools.py",
        notes="updated",
        intent_tags=["catalog", "registry"],
        memory_path=memory_path,
    )

    assert updated["action"] == "updated"
    assert updated["entry"]["notes"] == "updated"
    assert updated["count"] == 1
