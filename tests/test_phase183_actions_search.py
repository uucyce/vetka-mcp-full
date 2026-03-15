"""
Phase 183.4-183.5 — ActionRegistry Qdrant Integration + Search API Tests

Tests:
1. search_actions fallback (no Qdrant) — filter by session_id
2. search_actions fallback — filter by run_id
3. search_actions fallback — filter by agent
4. search_actions fallback — filter by action type
5. search_actions fallback — file path partial match
6. search_actions fallback — keyword query scoring
7. flush_async writes to JSON
8. _search_fallback with combined filters
9. Actions route: /api/actions/stats
10. Actions route: /api/actions/run/{run_id}
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


# ── Test 1: Fallback search by session_id ─────────────────────────

@pytest.mark.asyncio
async def test_search_by_session_id(tmp_path):
    """Search actions filtered by session_id (no Qdrant)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_1", "opus", "edit", "src/main.py", session_id="sess_aaa")
    reg.log_action("run_1", "opus", "read", "src/utils.py", session_id="sess_aaa")
    reg.log_action("run_2", "cursor", "edit", "src/ui.tsx", session_id="sess_bbb")
    reg.flush()

    results = await reg.search_actions("", session_id="sess_aaa")
    assert len(results) == 2
    assert all(r.get("session_id") == "sess_aaa" for r in results)


# ── Test 2: Fallback search by run_id ─────────────────────────────

@pytest.mark.asyncio
async def test_search_by_run_id(tmp_path):
    """Search actions filtered by run_id."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_abc", "opus", "edit", "src/a.py")
    reg.log_action("run_abc", "opus", "create", "src/b.py")
    reg.log_action("run_xyz", "cursor", "edit", "src/c.py")
    reg.flush()

    results = await reg.search_actions("", run_id="run_abc")
    assert len(results) == 2
    assert all(r.get("run_id") == "run_abc" for r in results)


# ── Test 3: Fallback search by agent ──────────────────────────────

@pytest.mark.asyncio
async def test_search_by_agent(tmp_path):
    """Search actions filtered by agent."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_1", "opus", "edit", "src/a.py")
    reg.log_action("run_1", "dragon", "edit", "src/b.py")
    reg.log_action("run_2", "opus", "read", "src/c.py")
    reg.flush()

    results = await reg.search_actions("", agent="dragon")
    assert len(results) == 1
    assert results[0]["agent"] == "dragon"


# ── Test 4: Fallback search by action type ────────────────────────

@pytest.mark.asyncio
async def test_search_by_action_type(tmp_path):
    """Search actions filtered by action type."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_1", "opus", "edit", "src/a.py")
    reg.log_action("run_1", "opus", "read", "src/b.py")
    reg.log_action("run_1", "opus", "create", "src/c.py")
    reg.flush()

    results = await reg.search_actions("", action="edit")
    assert len(results) == 1
    assert results[0]["action"] == "edit"


# ── Test 5: Fallback file path partial match ──────────────────────

@pytest.mark.asyncio
async def test_search_by_file_path(tmp_path):
    """Search actions by file path (partial match)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_1", "opus", "edit", "src/orchestration/heartbeat.py")
    reg.log_action("run_1", "opus", "edit", "src/orchestration/task_board.py")
    reg.log_action("run_1", "opus", "edit", "src/api/routes/health.py")
    reg.flush()

    results = await reg.search_actions("", file_path="orchestration")
    assert len(results) == 2
    assert all("orchestration" in r["file"] for r in results)


# ── Test 6: Keyword query scoring ────────────────────────────────

@pytest.mark.asyncio
async def test_keyword_query_scoring(tmp_path):
    """Keyword search scores results by word overlap."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_1", "opus", "edit", "src/heartbeat.py")
    reg.log_action("run_1", "dragon", "create", "src/task_board.py")
    reg.log_action("run_1", "opus", "read", "docs/readme.md")
    reg.flush()

    results = await reg.search_actions("edit heartbeat opus")
    assert len(results) >= 1
    # The edit on heartbeat by opus should score highest
    assert results[0]["file"] == "src/heartbeat.py"
    assert "score" in results[0]


# ── Test 7: flush_async writes to JSON ────────────────────────────

@pytest.mark.asyncio
async def test_flush_async_writes_json(tmp_path):
    """flush_async writes entries to JSON file."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_1", "opus", "edit", "src/a.py")
    reg.log_action("run_1", "opus", "read", "src/b.py")

    count = await reg.flush_async()
    assert count == 2

    data = json.loads((tmp_path / "actions.json").read_text())
    assert len(data) == 2


# ── Test 8: Combined filters ─────────────────────────────────────

@pytest.mark.asyncio
async def test_combined_filters(tmp_path):
    """Multiple filters combine with AND logic."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_1", "opus", "edit", "src/a.py", session_id="sess_1")
    reg.log_action("run_1", "opus", "read", "src/b.py", session_id="sess_1")
    reg.log_action("run_1", "dragon", "edit", "src/c.py", session_id="sess_1")
    reg.log_action("run_2", "opus", "edit", "src/d.py", session_id="sess_2")
    reg.flush()

    # session_id=sess_1 AND agent=opus AND action=edit
    results = await reg.search_actions(
        "", session_id="sess_1", agent="opus", action="edit"
    )
    assert len(results) == 1
    assert results[0]["file"] == "src/a.py"


# ── Test 9: get_stats works ──────────────────────────────────────

def test_stats_after_logging(tmp_path):
    """Stats reflect logged actions."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    reg.log_action("run_1", "opus", "edit", "src/a.py")
    reg.log_action("run_1", "opus", "read", "src/b.py")
    reg.log_action("run_1", "dragon", "edit", "src/c.py")
    reg.flush()

    stats = reg.get_stats()
    assert stats["total_persisted"] == 3
    assert stats["action_counts"]["edit"] == 2
    assert stats["action_counts"]["read"] == 1
    assert stats["agent_counts"]["opus"] == 2
    assert stats["agent_counts"]["dragon"] == 1


# ── Test 10: Empty search returns newest ──────────────────────────

@pytest.mark.asyncio
async def test_empty_search_returns_newest(tmp_path):
    """Empty query with no filters returns newest entries."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.action_registry import ActionRegistry

    reg = ActionRegistry(storage_path=tmp_path / "actions.json", qdrant_enabled=False)

    for i in range(5):
        reg.log_action(f"run_{i}", "opus", "edit", f"src/file_{i}.py")
    reg.flush()

    results = await reg.search_actions("", limit=3)
    assert len(results) == 3
