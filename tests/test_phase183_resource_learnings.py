"""
Phase 183.2 — Resource Learnings Store Tests

Tests:
1. ResourceLearningStore fallback (no Qdrant) — store + search
2. extract_and_store_learnings generates correct learnings
3. get_learnings_for_architect formats output
4. Fallback keyword search works
5. Category filtering
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock


# ── Test 1: Fallback store and search (no Qdrant) ─────────────────────

def test_fallback_store(tmp_path):
    """Store learning in fallback JSON when Qdrant unavailable."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.resource_learnings import ResourceLearningStore, _FALLBACK_FILE

    store = ResourceLearningStore()
    store._initialized = True  # Skip Qdrant init
    store._qdrant = None

    # Override fallback file
    import src.orchestration.resource_learnings as rl_module
    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"

    try:
        point_id = store._store_fallback("test_001", {
            "text": "Always validate inputs before pipeline",
            "category": "pitfall",
            "run_id": "run_123",
        })

        assert point_id == "test_001"
        data = json.loads((tmp_path / "learnings.json").read_text())
        assert len(data) == 1
        assert data[0]["text"] == "Always validate inputs before pipeline"
    finally:
        rl_module._FALLBACK_FILE = original_fallback


# ── Test 2: Fallback keyword search ───────────────────────────────────

def test_fallback_search(tmp_path):
    """Search learnings by keyword overlap."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.orchestration.resource_learnings import ResourceLearningStore
    import src.orchestration.resource_learnings as rl_module

    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"

    try:
        store = ResourceLearningStore()
        store._initialized = True
        store._qdrant = None

        # Populate fallback
        entries = [
            {"text": "Pipeline timeout on large file embeddings", "category": "pitfall"},
            {"text": "Co-change pattern: heartbeat and task_board", "category": "pattern"},
            {"text": "Use chunked embeddings for large files", "category": "optimization"},
        ]
        (tmp_path / "learnings.json").write_text(json.dumps(entries))

        results = store._search_fallback("embeddings large files", limit=3)
        assert len(results) >= 1
        # "large file embeddings" and "chunked embeddings for large files" should match
        texts = [r["text"] for r in results]
        assert any("embeddings" in t for t in texts)
    finally:
        rl_module._FALLBACK_FILE = original_fallback


# ── Test 3: extract_and_store_learnings generates learnings ────────────

@pytest.mark.asyncio
async def test_extract_and_store_learnings(tmp_path):
    """Extract learnings from a completed pipeline run."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    import src.orchestration.resource_learnings as rl_module

    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"

    # Reset singleton
    rl_module._store_instance = None

    try:
        with patch.object(rl_module.ResourceLearningStore, '_ensure_init', return_value=False):
            from src.orchestration.resource_learnings import extract_and_store_learnings

            ids = await extract_and_store_learnings(
                run_id="run_test_001",
                task_id="tb_123",
                session_id="sess_999_abcd1234",
                files_committed=[
                    "src/orchestration/heartbeat.py",
                    "src/orchestration/task_board.py",
                    "tests/test_heartbeat.py",
                ],
                task_title="Add session_id to heartbeat flow",
                task_description="Wire session_id through heartbeat → TaskBoard → pipeline",
            )

            # Should generate at least 2 learnings (co-change + completion)
            assert len(ids) >= 2

            # Check fallback file was written
            data = json.loads((tmp_path / "learnings.json").read_text())
            assert len(data) >= 2

            # Verify categories
            categories = {d.get("category") for d in data}
            assert "pattern" in categories  # co-change
            assert "optimization" in categories  # completion
    finally:
        rl_module._FALLBACK_FILE = original_fallback
        rl_module._store_instance = None


# ── Test 4: extract with verifier issues → pitfall learning ───────────

@pytest.mark.asyncio
async def test_extract_with_verifier_issues(tmp_path):
    """Verifier issues generate 'pitfall' learnings."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    import src.orchestration.resource_learnings as rl_module

    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"
    rl_module._store_instance = None

    try:
        with patch.object(rl_module.ResourceLearningStore, '_ensure_init', return_value=False):
            from src.orchestration.resource_learnings import extract_and_store_learnings

            verifier_results = [
                {"issues": ["Missing error handling in API route", "No type validation"], "retry_count": 1},
                {"issues": ["Import not found"], "retry_count": 0},
            ]

            ids = await extract_and_store_learnings(
                run_id="run_test_002",
                task_id="tb_456",
                files_committed=["src/api/routes.py"],
                verifier_results=verifier_results,
                task_title="Fix API routes",
            )

            data = json.loads((tmp_path / "learnings.json").read_text())
            pitfalls = [d for d in data if d.get("category") == "pitfall"]
            assert len(pitfalls) == 1
            assert "retries" in pitfalls[0]["text"].lower() or "retry" in pitfalls[0]["text"].lower()
    finally:
        rl_module._FALLBACK_FILE = original_fallback
        rl_module._store_instance = None


# ── Test 5: get_learnings_for_architect returns formatted string ───────

@pytest.mark.asyncio
async def test_get_learnings_for_architect(tmp_path):
    """Architect injection formats learnings correctly."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    import src.orchestration.resource_learnings as rl_module

    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"
    rl_module._store_instance = None

    try:
        # Populate with searchable data
        entries = [
            {"text": "Session ID must flow through heartbeat to pipeline", "category": "pattern",
             "run_id": "run_1", "task_id": "tb_1", "files": [], "timestamp_iso": "2026-03-15 12:00:00"},
        ]
        (tmp_path / "learnings.json").write_text(json.dumps(entries))

        with patch.object(rl_module.ResourceLearningStore, '_ensure_init', return_value=False):
            from src.orchestration.resource_learnings import get_learnings_for_architect

            result = await get_learnings_for_architect("heartbeat session flow")

            assert "[Past Learnings]" in result
            assert "pattern" in result.lower()
            assert "session" in result.lower()
    finally:
        rl_module._FALLBACK_FILE = original_fallback
        rl_module._store_instance = None


# ── Test 6: Empty results → empty string ──────────────────────────────

@pytest.mark.asyncio
async def test_get_learnings_empty(tmp_path):
    """No learnings → empty string (no injection)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    import src.orchestration.resource_learnings as rl_module

    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"
    rl_module._store_instance = None

    try:
        with patch.object(rl_module.ResourceLearningStore, '_ensure_init', return_value=False):
            from src.orchestration.resource_learnings import get_learnings_for_architect

            result = await get_learnings_for_architect("completely unrelated query xyz123")
            assert result == ""
    finally:
        rl_module._FALLBACK_FILE = original_fallback
        rl_module._store_instance = None


# ── Test 7: store_learning_sync (MARKER_198.P1.7) ────────────────────

def test_store_learning_sync_fallback(tmp_path):
    """MARKER_198.P1.7: Sync store falls back to JSON when Qdrant unavailable."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    import src.orchestration.resource_learnings as rl_module

    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"
    rl_module._store_instance = None

    try:
        store = rl_module.ResourceLearningStore()
        store._initialized = True
        store._qdrant = None

        # Store a bug report via sync path
        pid = store.store_learning_sync(
            text="[BUG] MCP bridge doesn't hot-reload",
            category="pitfall",
            task_id="tb_test_sync",
            session_id="sess_test",
            files=["src/mcp/vetka_mcp_bridge.py"],
            metadata={"source": "debrief_q1", "agent": "Zeta"},
        )

        assert pid is not None

        data = json.loads((tmp_path / "learnings.json").read_text())
        assert len(data) == 1
        assert data[0]["text"] == "[BUG] MCP bridge doesn't hot-reload"
        assert data[0]["category"] == "pitfall"
        assert data[0]["task_id"] == "tb_test_sync"
        assert data[0]["agent"] == "Zeta"
    finally:
        rl_module._FALLBACK_FILE = original_fallback
        rl_module._store_instance = None


def test_store_learning_sync_multiple_categories(tmp_path):
    """MARKER_198.P1.7: Sync store handles all debrief categories (q1/q2/q3)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    import src.orchestration.resource_learnings as rl_module

    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"
    rl_module._store_instance = None

    try:
        store = rl_module.ResourceLearningStore()
        store._initialized = True
        store._qdrant = None

        ids = []
        ids.append(store.store_learning_sync(
            text="[BUG] ENGRAM writes fail silently", category="pitfall",
            task_id="tb_198", metadata={"source": "debrief_q1"},
        ))
        ids.append(store.store_learning_sync(
            text="[WORKED] Direct routing bypasses regex", category="pattern",
            task_id="tb_198", metadata={"source": "debrief_q2"},
        ))
        ids.append(store.store_learning_sync(
            text="[IDEA] Auto-generate MCP wrappers from schema", category="architecture",
            task_id="tb_198", metadata={"source": "debrief_q3"},
        ))

        assert all(pid is not None for pid in ids)
        assert len(set(ids)) == 3  # All unique IDs

        data = json.loads((tmp_path / "learnings.json").read_text())
        assert len(data) == 3
        categories = {d["category"] for d in data}
        assert categories == {"pitfall", "pattern", "architecture"}
    finally:
        rl_module._FALLBACK_FILE = original_fallback
        rl_module._store_instance = None


# ── Test 8: get_stats fallback ────────────────────────────────────────

def test_get_stats_fallback(tmp_path):
    """Stats work in fallback mode."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    import src.orchestration.resource_learnings as rl_module

    original_fallback = rl_module._FALLBACK_FILE
    rl_module._FALLBACK_FILE = tmp_path / "learnings.json"

    try:
        store = rl_module.ResourceLearningStore()
        store._initialized = True
        store._qdrant = None

        entries = [{"text": "test1"}, {"text": "test2"}]
        (tmp_path / "learnings.json").write_text(json.dumps(entries))

        stats = store.get_stats()
        assert stats["source"] == "fallback"
        assert stats["count"] == 2
    finally:
        rl_module._FALLBACK_FILE = original_fallback
