"""
Phase 192: SQLite Migration Tests
MARKER_192.2 (Wave 1) + MARKER_192.4 (Wave 2)

Wave 1 tests:
- test_create_schema — schema creation on empty DB
- test_task_roundtrip — dict → row → dict preserves all fields
- test_save_load_task — write + read single task
- test_concurrent_writes — two connections write simultaneously, no data loss
- test_migration_json_to_sqlite — migrate real-format JSON, verify count
- test_migration_preserves_all_fields — check 5 random tasks, all fields match
- test_project_id_filter — query by project_id works
- test_status_filter — query by status works
- test_get_queue_ordering — priority + created_at sort
- test_settings_persistence — save/load settings
- test_wal_mode — verify WAL is active

Wave 2 tests:
- test_concurrent_add_no_data_loss — 3 threads × 10 tasks, all 30 exist
- test_export_sqlite_to_json — roundtrip: JSON → SQLite → JSON
- test_verify_migration — verification passes on good migration
- test_delete_task — delete single task
- test_get_task_count — count with/without status filter
- test_get_status_counts — GROUP BY status
"""

import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

import sys
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.task_board_migrate import (
    INDEXED_COLUMNS,
    connect_db,
    delete_task,
    ensure_schema,
    export_sqlite_to_json,
    get_status_counts,
    get_task_count,
    load_all_tasks,
    load_settings,
    load_task,
    migrate_json_to_sqlite,
    query_tasks,
    row_to_task,
    save_settings,
    save_task,
    task_to_row,
    verify_migration,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_tasks.db"


@pytest.fixture
def db_conn(db_path):
    conn = connect_db(db_path)
    ensure_schema(conn)
    yield conn
    conn.close()


def _make_task(
    task_id: str = "tb_test_1",
    title: str = "Test task",
    **overrides,
) -> dict:
    """Create a minimal task dict for testing."""
    task = {
        "id": task_id,
        "title": title,
        "description": "Test description",
        "priority": 3,
        "status": "pending",
        "phase_type": "build",
        "complexity": "medium",
        "project_id": "",
        "assigned_to": None,
        "agent_type": None,
        "assigned_at": None,
        "created_by": "test",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "closed_at": None,
        "commit_hash": None,
        "commit_message": None,
        "updated_at": "",
        # Extra fields (go into JSON blob)
        "tags": ["test"],
        "dependencies": [],
        "source": "manual",
        "module": "tests",
        "status_history": [{"event": "created", "ts": datetime.now().isoformat()}],
        "closure_proof": None,
        "execution_mode": "pipeline",
    }
    task.update(overrides)
    return task


def _make_json_board(json_path: Path, num_tasks: int = 10, **task_overrides) -> dict:
    """Create a JSON task board file with N tasks. Returns the data dict."""
    tasks = {}
    for i in range(num_tasks):
        tid = f"tb_{int(time.time())}_{i+1}"
        t = _make_task(task_id=tid, title=f"Task {i+1}", priority=(i % 5) + 1, **task_overrides)
        tasks[tid] = t
    data = {
        "tasks": tasks,
        "settings": {
            "max_concurrent": 2,
            "auto_dispatch": True,
            "default_preset": "dragon_silver",
        },
    }
    json_path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    return data


# ============================================================
# Wave 1: Core SQLite tests (MARKER_192.2)
# ============================================================

class TestCreateSchema:
    """test_create_schema — schema creation on empty DB."""

    def test_tables_exist(self, db_conn):
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        assert "tasks" in tables
        assert "settings" in tables
        assert "meta" in tables

    def test_indexes_exist(self, db_conn):
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = {row["name"] for row in cursor.fetchall()}
        assert "idx_tasks_status" in indexes
        assert "idx_tasks_priority" in indexes
        assert "idx_tasks_project" in indexes
        assert "idx_tasks_assigned" in indexes

    def test_idempotent_schema(self, db_conn):
        """Running ensure_schema twice doesn't error."""
        ensure_schema(db_conn)
        ensure_schema(db_conn)
        count = get_task_count(db_conn)
        assert count == 0


class TestTaskRoundtrip:
    """test_task_roundtrip — dict → row → dict preserves all fields."""

    def test_indexed_fields_preserved(self):
        task = _make_task(priority=2, status="running", project_id="cut")
        row = task_to_row(task)
        # Simulate DB row → task
        # Build a fake sqlite3.Row-like dict
        assert row["priority"] == 2
        assert row["status"] == "running"
        assert row["project_id"] == "cut"

    def test_extra_fields_in_json_blob(self):
        task = _make_task(tags=["alpha", "beta"], execution_mode="manual")
        row = task_to_row(task)
        extra = json.loads(row["extra"])
        assert extra["tags"] == ["alpha", "beta"]
        assert extra["execution_mode"] == "manual"

    def test_full_roundtrip_via_db(self, db_conn):
        task = _make_task(
            task_id="tb_roundtrip",
            priority=1,
            status="claimed",
            project_id="test_proj",
            tags=["x", "y"],
            dependencies=["tb_dep_1"],
            closure_proof={"commit_hash": "abc"},
            execution_mode="manual",
        )
        save_task(db_conn, task)
        loaded = load_task(db_conn, "tb_roundtrip")
        assert loaded is not None
        assert loaded["id"] == "tb_roundtrip"
        assert loaded["priority"] == 1
        assert loaded["status"] == "claimed"
        assert loaded["project_id"] == "test_proj"
        assert loaded["tags"] == ["x", "y"]
        assert loaded["dependencies"] == ["tb_dep_1"]
        assert loaded["closure_proof"] == {"commit_hash": "abc"}
        assert loaded["execution_mode"] == "manual"

    def test_none_fields_survive_roundtrip(self, db_conn):
        task = _make_task(task_id="tb_none", assigned_to=None, commit_hash=None)
        save_task(db_conn, task)
        loaded = load_task(db_conn, "tb_none")
        assert loaded["assigned_to"] is None
        assert loaded["commit_hash"] is None


class TestSaveLoadTask:
    """test_save_load_task — write + read single task."""

    def test_save_and_load(self, db_conn):
        task = _make_task(task_id="tb_save_1", title="Save me")
        save_task(db_conn, task)
        loaded = load_task(db_conn, "tb_save_1")
        assert loaded is not None
        assert loaded["title"] == "Save me"

    def test_load_nonexistent(self, db_conn):
        assert load_task(db_conn, "tb_nonexistent") is None

    def test_upsert_overwrites(self, db_conn):
        task = _make_task(task_id="tb_upsert", title="Version 1")
        save_task(db_conn, task)
        task["title"] = "Version 2"
        save_task(db_conn, task)
        loaded = load_task(db_conn, "tb_upsert")
        assert loaded["title"] == "Version 2"
        assert get_task_count(db_conn) == 1


class TestConcurrentWrites:
    """test_concurrent_writes — two connections write simultaneously, no data loss."""

    def test_two_connections_no_conflict(self, db_path):
        conn1 = connect_db(db_path)
        ensure_schema(conn1)
        conn2 = connect_db(db_path)

        task1 = _make_task(task_id="tb_c1", title="From conn 1")
        task2 = _make_task(task_id="tb_c2", title="From conn 2")

        save_task(conn1, task1)
        save_task(conn2, task2)

        # Both tasks should exist when read from either connection
        assert load_task(conn1, "tb_c1") is not None
        assert load_task(conn1, "tb_c2") is not None
        assert load_task(conn2, "tb_c1") is not None
        assert load_task(conn2, "tb_c2") is not None

        conn1.close()
        conn2.close()


class TestMigrationJsonToSqlite:
    """test_migration_json_to_sqlite — migrate JSON, verify count."""

    def test_migrate_basic(self, tmp_path):
        json_path = tmp_path / "board.json"
        db_path = tmp_path / "board.db"
        data = _make_json_board(json_path, num_tasks=15)

        result = migrate_json_to_sqlite(json_path, db_path)

        assert result["success"] is True
        assert result["migrated"] == 15
        assert result["total_in_json"] == 15
        assert len(result["errors"]) == 0

        conn = connect_db(db_path)
        assert get_task_count(conn) == 15
        conn.close()

    def test_migrate_nonexistent_json(self, tmp_path):
        result = migrate_json_to_sqlite(tmp_path / "nope.json", tmp_path / "board.db")
        assert result["success"] is False

    def test_migrate_empty_board(self, tmp_path):
        json_path = tmp_path / "empty.json"
        json_path.write_text('{"tasks": {}, "settings": {}}')
        db_path = tmp_path / "empty.db"

        result = migrate_json_to_sqlite(json_path, db_path)

        assert result["success"] is True
        assert result["migrated"] == 0

    def test_migrate_settings(self, tmp_path):
        json_path = tmp_path / "board.json"
        db_path = tmp_path / "board.db"
        _make_json_board(json_path, num_tasks=1)

        migrate_json_to_sqlite(json_path, db_path)

        conn = connect_db(db_path)
        settings = load_settings(conn)
        assert settings["max_concurrent"] == 2
        assert settings["auto_dispatch"] is True
        conn.close()


class TestMigrationPreservesAllFields:
    """test_migration_preserves_all_fields — check tasks, all fields match."""

    def test_fields_preserved(self, tmp_path):
        json_path = tmp_path / "board.json"
        db_path = tmp_path / "board.db"

        # Create tasks with many fields
        tasks = {}
        for i in range(5):
            tid = f"tb_field_{i}"
            tasks[tid] = _make_task(
                task_id=tid,
                title=f"Field test {i}",
                priority=i + 1,
                status="pending",
                tags=["alpha", f"tag_{i}"],
                dependencies=[f"tb_dep_{i}"] if i > 0 else [],
                execution_mode="manual" if i % 2 == 0 else "pipeline",
                project_id=f"proj_{i}",
                module=f"mod_{i}",
            )
        data = {"tasks": tasks, "settings": {"max_concurrent": 3}}
        json_path.write_text(json.dumps(data, indent=2, default=str))

        migrate_json_to_sqlite(json_path, db_path)

        conn = connect_db(db_path)
        for tid, original in tasks.items():
            loaded = load_task(conn, tid)
            assert loaded is not None, f"Task {tid} missing from DB"
            assert loaded["title"] == original["title"]
            assert loaded["priority"] == original["priority"]
            assert loaded["tags"] == original["tags"]
            assert loaded["execution_mode"] == original["execution_mode"]
            assert loaded["project_id"] == original["project_id"]
        conn.close()


class TestProjectIdFilter:
    """test_project_id_filter — query by project_id works."""

    def test_filter_by_project(self, db_conn):
        save_task(db_conn, _make_task(task_id="tb_p1", project_id="cut"))
        save_task(db_conn, _make_task(task_id="tb_p2", project_id="cut"))
        save_task(db_conn, _make_task(task_id="tb_p3", project_id="vetka"))

        cut_tasks = query_tasks(db_conn, project_id="cut")
        assert len(cut_tasks) == 2
        assert all(t["project_id"] == "cut" for t in cut_tasks)

        vetka_tasks = query_tasks(db_conn, project_id="vetka")
        assert len(vetka_tasks) == 1


class TestStatusFilter:
    """test_status_filter — query by status works."""

    def test_filter_by_status(self, db_conn):
        save_task(db_conn, _make_task(task_id="tb_s1", status="pending"))
        save_task(db_conn, _make_task(task_id="tb_s2", status="pending"))
        save_task(db_conn, _make_task(task_id="tb_s3", status="done"))
        save_task(db_conn, _make_task(task_id="tb_s4", status="running"))

        pending = query_tasks(db_conn, status="pending")
        assert len(pending) == 2

        done = query_tasks(db_conn, status="done")
        assert len(done) == 1


class TestGetQueueOrdering:
    """test_get_queue_ordering — priority + created_at sort."""

    def test_priority_then_created_at(self, db_conn):
        # Insert with explicit created_at to control ordering
        save_task(db_conn, _make_task(
            task_id="tb_q1", title="Low", priority=4, status="pending",
            created_at="2026-03-19T10:00:00",
        ))
        save_task(db_conn, _make_task(
            task_id="tb_q2", title="Critical", priority=1, status="pending",
            created_at="2026-03-19T12:00:00",
        ))
        save_task(db_conn, _make_task(
            task_id="tb_q3", title="Critical older", priority=1, status="pending",
            created_at="2026-03-19T08:00:00",
        ))

        queue = query_tasks(db_conn, status="pending")
        # P1 tasks first, older P1 before newer P1, then P4
        assert queue[0]["id"] == "tb_q3"  # P1, 08:00
        assert queue[1]["id"] == "tb_q2"  # P1, 12:00
        assert queue[2]["id"] == "tb_q1"  # P4, 10:00


class TestSettingsPersistence:
    """test_settings_persistence — save/load settings."""

    def test_save_and_load(self, db_conn):
        settings = {
            "max_concurrent": 4,
            "auto_dispatch": False,
            "default_preset": "dragon_gold",
        }
        save_settings(db_conn, settings)
        loaded = load_settings(db_conn)
        assert loaded["max_concurrent"] == 4
        assert loaded["auto_dispatch"] is False
        assert loaded["default_preset"] == "dragon_gold"

    def test_update_setting(self, db_conn):
        save_settings(db_conn, {"max_concurrent": 2})
        save_settings(db_conn, {"max_concurrent": 5})
        loaded = load_settings(db_conn)
        assert loaded["max_concurrent"] == 5

    def test_skips_private_keys(self, db_conn):
        save_settings(db_conn, {"max_concurrent": 2, "_integrity_warning": "mismatch"})
        loaded = load_settings(db_conn)
        assert "max_concurrent" in loaded
        assert "_integrity_warning" not in loaded


class TestWalMode:
    """test_wal_mode — verify WAL is active."""

    def test_wal_active(self, db_path):
        conn = connect_db(db_path)
        ensure_schema(conn)
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal"
        conn.close()


# ============================================================
# Wave 2: Concurrent + integration tests (MARKER_192.4)
# ============================================================

class TestConcurrentAddNoDataLoss:
    """THE critical test: 3 threads × 10 tasks, all 30 exist."""

    def test_30_tasks_from_3_threads(self, db_path):
        conn = connect_db(db_path)
        ensure_schema(conn)
        conn.close()

        errors = []

        def writer(thread_id: int):
            try:
                c = connect_db(db_path)
                for i in range(10):
                    tid = f"tb_thread{thread_id}_{i}"
                    task = _make_task(task_id=tid, title=f"Thread {thread_id} task {i}")
                    save_task(c, task)
                c.close()
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Thread errors: {errors}"

        conn = connect_db(db_path)
        total = get_task_count(conn)
        assert total == 30, f"Expected 30 tasks, got {total}"

        # Verify each task exists
        for thread_id in range(3):
            for i in range(10):
                tid = f"tb_thread{thread_id}_{i}"
                task = load_task(conn, tid)
                assert task is not None, f"Missing: {tid}"
        conn.close()


class TestExportSqliteToJson:
    """Roundtrip: JSON → SQLite → JSON."""

    def test_roundtrip_export(self, tmp_path):
        json_src = tmp_path / "source.json"
        db_path = tmp_path / "board.db"
        json_dst = tmp_path / "exported.json"

        data = _make_json_board(json_src, num_tasks=8)
        migrate_json_to_sqlite(json_src, db_path)
        result = export_sqlite_to_json(db_path, json_dst)

        assert result["success"] is True
        assert result["exported"] == 8

        exported = json.loads(json_dst.read_text())
        assert len(exported["tasks"]) == 8
        assert exported["settings"]["max_concurrent"] == 2

    def test_export_nonexistent_db(self, tmp_path):
        result = export_sqlite_to_json(tmp_path / "nope.db", tmp_path / "out.json")
        assert result["success"] is False


class TestVerifyMigration:
    """Verification passes on good migration."""

    def test_verify_good_migration(self, tmp_path):
        json_path = tmp_path / "board.json"
        db_path = tmp_path / "board.db"
        _make_json_board(json_path, num_tasks=20)

        migrate_json_to_sqlite(json_path, db_path)
        result = verify_migration(json_path, db_path)

        assert result["success"] is True
        assert result["count_match"] is True
        assert result["json_count"] == 20
        assert result["db_count"] == 20
        assert len(result["spot_checks"]) == 5  # min(5, 20)
        assert all(c["match"] for c in result["spot_checks"])

    def test_verify_missing_json(self, tmp_path):
        result = verify_migration(tmp_path / "nope.json", tmp_path / "board.db")
        assert result["success"] is False

    def test_verify_missing_db(self, tmp_path):
        json_path = tmp_path / "board.json"
        _make_json_board(json_path, num_tasks=1)
        result = verify_migration(json_path, tmp_path / "nope.db")
        assert result["success"] is False


class TestDeleteTask:
    """delete_task removes single task."""

    def test_delete_existing(self, db_conn):
        save_task(db_conn, _make_task(task_id="tb_del_1"))
        assert load_task(db_conn, "tb_del_1") is not None
        assert delete_task(db_conn, "tb_del_1") is True
        assert load_task(db_conn, "tb_del_1") is None

    def test_delete_nonexistent(self, db_conn):
        assert delete_task(db_conn, "tb_nope") is False


class TestGetTaskCount:
    """Count with/without status filter."""

    def test_total_count(self, db_conn):
        save_task(db_conn, _make_task(task_id="tb_cnt_1", status="pending"))
        save_task(db_conn, _make_task(task_id="tb_cnt_2", status="done"))
        assert get_task_count(db_conn) == 2

    def test_filtered_count(self, db_conn):
        save_task(db_conn, _make_task(task_id="tb_cnt_3", status="pending"))
        save_task(db_conn, _make_task(task_id="tb_cnt_4", status="pending"))
        save_task(db_conn, _make_task(task_id="tb_cnt_5", status="done"))
        assert get_task_count(db_conn, status="pending") == 2
        assert get_task_count(db_conn, status="done") == 1
        assert get_task_count(db_conn, status="running") == 0


class TestGetStatusCounts:
    """GROUP BY status."""

    def test_status_groups(self, db_conn):
        save_task(db_conn, _make_task(task_id="tb_g1", status="pending"))
        save_task(db_conn, _make_task(task_id="tb_g2", status="pending"))
        save_task(db_conn, _make_task(task_id="tb_g3", status="done"))
        save_task(db_conn, _make_task(task_id="tb_g4", status="failed"))

        counts = get_status_counts(db_conn)
        assert counts["pending"] == 2
        assert counts["done"] == 1
        assert counts["failed"] == 1


class TestMigrateRealJsonFormat:
    """Test migration with a JSON file matching the real task_board.json format."""

    def test_real_format_with_meta(self, tmp_path):
        """JSON with _meta, settings, and realistic task structure."""
        json_path = tmp_path / "real.json"
        data = {
            "_meta": {
                "version": "1.0",
                "phase": "121",
                "updated": "2026-03-19T00:00:00",
                "integrity_sig": "abc123",
                "last_writer": "task_board_runtime",
            },
            "tasks": {
                "tb_1710000000_1": {
                    "id": "tb_1710000000_1",
                    "title": "Fix broken import",
                    "description": "Fix file positioning",
                    "priority": 2,
                    "status": "done",
                    "phase_type": "fix",
                    "complexity": "medium",
                    "preset": None,
                    "assigned_tier": None,
                    "source": "manual",
                    "tags": ["urgent", "import"],
                    "dependencies": [],
                    "created_at": "2026-03-19T10:00:00",
                    "started_at": "2026-03-19T10:05:00",
                    "completed_at": "2026-03-19T11:00:00",
                    "pipeline_task_id": None,
                    "result_summary": "Fixed",
                    "stats": {"duration_s": 3300},
                    "assigned_to": "opus",
                    "assigned_at": "2026-03-19T10:05:00",
                    "agent_type": "claude_code",
                    "commit_hash": "abc123def",
                    "commit_message": "fix: broken import",
                    "created_by": "claude-code",
                    "module": "backend_api",
                    "project_id": "vetka",
                    "execution_mode": "manual",
                    "status_history": [
                        {"event": "created", "ts": "2026-03-19T10:00:00"},
                        {"event": "claimed", "ts": "2026-03-19T10:05:00"},
                        {"event": "closed", "ts": "2026-03-19T11:00:00"},
                    ],
                    "closure_proof": {"commit_hash": "abc123def"},
                    "closed_by": "opus",
                    "closed_at": "2026-03-19T11:00:00",
                },
            },
            "settings": {
                "max_concurrent": 2,
                "auto_dispatch": True,
                "default_preset": "dragon_silver",
            },
        }
        json_path.write_text(json.dumps(data, indent=2))

        db_path = tmp_path / "real.db"
        result = migrate_json_to_sqlite(json_path, db_path)
        assert result["success"] is True
        assert result["migrated"] == 1

        conn = connect_db(db_path)
        task = load_task(conn, "tb_1710000000_1")
        assert task is not None
        assert task["title"] == "Fix broken import"
        assert task["status"] == "done"
        assert task["commit_hash"] == "abc123def"
        assert task["tags"] == ["urgent", "import"]
        assert task["execution_mode"] == "manual"
        assert task["closure_proof"] == {"commit_hash": "abc123def"}
        assert len(task["status_history"]) == 3
        conn.close()
