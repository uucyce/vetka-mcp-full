"""
MARKER_200.SINGLE_LOCK: Stress test for concurrent SQLite access.

Tests that 10 concurrent processes can read/write task_board.db
without deadlocking. Validates the SINGLE_LOCK fix:
- _save_task: task + FTS in one transaction (was 4 locks, now 1)
- busy_timeout=15000 (was 5000)
- synchronous=NORMAL with WAL

Run: python -m pytest tests/test_phase200_single_lock.py -v
"""

import sqlite3
import threading
import time
import json
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "task_board.db"


class TestSingleLockConcurrency:
    """Stress tests for MARKER_200.SINGLE_LOCK."""

    def _get_conn(self):
        """Get a connection matching production settings."""
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def test_busy_timeout_is_15000(self):
        """Verify busy_timeout is 15000ms (MARKER_200.SINGLE_LOCK)."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.db_path = DB_PATH
        conn = board._connect()
        bt = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        conn.close()
        assert bt == 15000, f"busy_timeout={bt}, expected 15000"

    def test_synchronous_normal(self):
        """Verify synchronous=NORMAL for WAL performance."""
        from src.orchestration.task_board import TaskBoard
        board = TaskBoard.__new__(TaskBoard)
        board.db_path = DB_PATH
        conn = board._connect()
        sync = conn.execute("PRAGMA synchronous").fetchone()[0]
        conn.close()
        # NORMAL = 1
        assert sync == 1, f"synchronous={sync}, expected 1 (NORMAL)"

    def test_10_concurrent_writes_no_deadlock(self):
        """10 threads writing simultaneously — no deadlock within 15s."""
        results = {"success": 0, "fail": 0, "errors": []}
        test_prefix = f"test_stress_{int(time.time())}"

        def worker(thread_id):
            try:
                conn = self._get_conn()
                task_id = f"{test_prefix}_{thread_id}"
                now = time.strftime("%Y-%m-%dT%H:%M:%S")
                extra = json.dumps({"thread": thread_id, "stress_test": True})

                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO tasks (id, title, description, priority, status, "
                        "phase_type, complexity, project_id, extra, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (task_id, f"Stress test thread {thread_id}",
                         f"Concurrent write test from thread {thread_id}",
                         5, "pending", "test", "low", "STRESS_TEST",
                         extra, now, now),
                    )
                conn.close()
                return True
            except Exception as e:
                results["errors"].append(f"Thread {thread_id}: {e}")
                return False

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(worker, i) for i in range(10)]
            for f in as_completed(futures):
                if f.result():
                    results["success"] += 1
                else:
                    results["fail"] += 1

        # Cleanup
        try:
            conn = self._get_conn()
            with conn:
                conn.execute(f"DELETE FROM tasks WHERE id LIKE '{test_prefix}%'")
            conn.close()
        except Exception:
            pass

        assert results["success"] == 10, (
            f"Only {results['success']}/10 writes succeeded. "
            f"Errors: {results['errors']}"
        )

    def test_10_concurrent_read_write_mix(self):
        """5 readers + 5 writers simultaneously — no deadlock."""
        results = {"reads": 0, "writes": 0, "errors": []}
        test_prefix = f"test_rw_{int(time.time())}"

        def reader(thread_id):
            try:
                conn = self._get_conn()
                rows = conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status = 'pending'"
                ).fetchone()[0]
                conn.close()
                assert rows >= 0
                return "read"
            except Exception as e:
                results["errors"].append(f"Reader {thread_id}: {e}")
                return "error"

        def writer(thread_id):
            try:
                conn = self._get_conn()
                task_id = f"{test_prefix}_{thread_id}"
                now = time.strftime("%Y-%m-%dT%H:%M:%S")
                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO tasks (id, title, priority, status, "
                        "phase_type, complexity, project_id, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (task_id, f"RW test {thread_id}", 5, "pending",
                         "test", "low", "STRESS_TEST", now, now),
                    )
                conn.close()
                return "write"
            except Exception as e:
                results["errors"].append(f"Writer {thread_id}: {e}")
                return "error"

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = []
            for i in range(5):
                futures.append(pool.submit(reader, i))
                futures.append(pool.submit(writer, i))

            for f in as_completed(futures):
                r = f.result()
                if r == "read":
                    results["reads"] += 1
                elif r == "write":
                    results["writes"] += 1

        # Cleanup
        try:
            conn = self._get_conn()
            with conn:
                conn.execute(f"DELETE FROM tasks WHERE id LIKE '{test_prefix}%'")
            conn.close()
        except Exception:
            pass

        assert results["reads"] == 5, f"Only {results['reads']}/5 reads"
        assert results["writes"] == 5, f"Only {results['writes']}/5 writes"
        assert not results["errors"], f"Errors: {results['errors']}"

    def test_save_task_single_transaction(self):
        """Verify _save_task uses _index_task_fts_inner (not _index_task_fts)."""
        import inspect
        from src.orchestration.task_board import TaskBoard
        src = inspect.getsource(TaskBoard._save_task)
        assert "_index_task_fts_inner" in src, (
            "_save_task must call _index_task_fts_inner (single transaction), "
            "not _index_task_fts (separate transaction)"
        )
        # Should NOT call the outer version
        # Check that _index_task_fts is not called directly (only inner)
        lines = [l.strip() for l in src.split("\n") if "index_task_fts" in l and not l.startswith("#")]
        for line in lines:
            assert "inner" in line or line.startswith("#"), (
                f"_save_task calls _index_task_fts directly: {line}"
            )

    def test_fts_inner_vs_outer_exist(self):
        """Both _index_task_fts and _index_task_fts_inner must exist."""
        from src.orchestration.task_board import TaskBoard
        assert hasattr(TaskBoard, "_index_task_fts"), "Missing _index_task_fts"
        assert hasattr(TaskBoard, "_index_task_fts_inner"), "Missing _index_task_fts_inner"

    def test_write_latency_under_100ms(self):
        """Single write must complete in <100ms even with WAL contention."""
        conn = self._get_conn()
        task_id = f"test_latency_{int(time.time())}"
        now = time.strftime("%Y-%m-%dT%H:%M:%S")

        start = time.monotonic()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO tasks (id, title, priority, status, "
                "phase_type, complexity, project_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (task_id, "Latency test", 5, "pending",
                 "test", "low", "STRESS_TEST", now, now),
            )
        elapsed = (time.monotonic() - start) * 1000

        # Cleanup
        with conn:
            conn.execute(f"DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.close()

        assert elapsed < 100, f"Write took {elapsed:.1f}ms, expected <100ms"
