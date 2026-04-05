"""
DELTA-QA: 204.4 — E2E signal delivery test
Task: tb_1775252937_23835_1

Full cycle: Commander notify → signal file created → hook reads → file deleted → append verified.

Depends on:
  204.1 (Zeta): notify() writes ~/.claude/signals/<role>.json
  204.2 (Zeta): UDS daemon (not tested directly — daemon is infra)
  204.3 (Eta): check_notifications.sh reads + deletes signal file

Acceptance contract (5 checks):
  1. signal file created after notify()
  2. JSON array format with required fields (id, from, message, ts)
  3. check_notifications.sh outputs message text + deletes file
  4. multiple notifies append (not overwrite)
  5. total runtime < 5 sec
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Project root resolution (worktree-safe)
# ---------------------------------------------------------------------------
_r = subprocess.run(
    ["git", "rev-parse", "--git-common-dir"],
    capture_output=True, text=True,
)
if _r.returncode == 0:
    _git_common = Path(_r.stdout.strip())
    PROJECT_ROOT = _git_common.parent if _git_common.name == ".git" else _git_common
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[4]

# 204.1 signal writing may be in harness worktree (pre-merge).
# Prefer the branch that has MARKER_204.FILE_SIGNAL in task_board.py.
def _find_task_board_with_signal() -> Path:
    """Return the project root whose task_board.py contains 204 signal writing."""
    candidates = [
        PROJECT_ROOT,
        PROJECT_ROOT / ".claude" / "worktrees" / "harness",
        PROJECT_ROOT / ".claude" / "worktrees" / "harness-eta",
    ]
    for root in candidates:
        tb_path = root / "src" / "orchestration" / "task_board.py"
        if tb_path.exists() and "MARKER_204.FILE_SIGNAL" in tb_path.read_text():
            return root
    return PROJECT_ROOT  # fallback — test will fail with clear error

_TB_ROOT = _find_task_board_with_signal()
sys.path.insert(0, str(_TB_ROOT))

# ---------------------------------------------------------------------------
# Locate check_notifications.sh (may be in harness-eta worktree pre-merge)
# ---------------------------------------------------------------------------
_SCRIPT_CANDIDATES = [
    PROJECT_ROOT / "scripts" / "check_notifications.sh",
    PROJECT_ROOT / ".claude" / "worktrees" / "harness-eta" / "scripts" / "check_notifications.sh",
    PROJECT_ROOT / ".claude" / "worktrees" / "harness" / "scripts" / "check_notifications.sh",
]
CHECK_SCRIPT = next((p for p in _SCRIPT_CANDIDATES if p.exists()), None)

# Test role — unique, won't collide with real agents
TEST_ROLE = "_DeltaTest204"
SIGNAL_DIR = Path.home() / ".claude" / "signals"
SIGNAL_FILE = SIGNAL_DIR / f"{TEST_ROLE}.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def cleanup_signal():
    """Remove test signal file before and after each test."""
    SIGNAL_FILE.unlink(missing_ok=True)
    yield
    SIGNAL_FILE.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def task_board(tmp_path_factory):
    """Instantiate TaskBoard from the branch that has MARKER_204.FILE_SIGNAL.

    Uses importlib to load directly from the harness worktree file,
    bypassing sys.modules cache which may hold a stale copy from main.
    """
    import importlib.util

    tb_py = _TB_ROOT / "src" / "orchestration" / "task_board.py"
    spec = importlib.util.spec_from_file_location("task_board_204", tb_py)
    mod = importlib.util.module_from_spec(spec)
    # Inject the harness root into sys.path for sub-imports within task_board.py
    if str(_TB_ROOT) not in sys.path:
        sys.path.insert(0, str(_TB_ROOT))
    spec.loader.exec_module(mod)

    TaskBoard = mod.TaskBoard
    db_file = tmp_path_factory.mktemp("tb") / "test_signal.db"
    tb = TaskBoard(board_file=db_file)
    return tb


# ---------------------------------------------------------------------------
# Check 1 — signal file created after notify()
# ---------------------------------------------------------------------------
class TestSignalFileCreation:
    def test_signal_file_created(self, task_board):
        """notify() must create ~/.claude/signals/<role>.json"""
        t0 = time.time()

        result = task_board.notify(
            target_role=TEST_ROLE,
            message="Hello from Commander",
            source_role="Commander",
        )

        assert result.get("success"), f"notify() failed: {result}"
        assert SIGNAL_FILE.exists(), f"Signal file not created: {SIGNAL_FILE}"

        elapsed = time.time() - t0
        assert elapsed < 5.0, f"Total time exceeded 5s: {elapsed:.2f}s"

    # Check 2 — JSON array format with required fields
    def test_signal_json_format(self, task_board):
        """Signal file must be a JSON array with required fields."""
        task_board.notify(
            target_role=TEST_ROLE,
            message="Format check",
            source_role="Commander",
        )

        raw = SIGNAL_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)

        assert isinstance(data, list), "Signal file must be a JSON array"
        assert len(data) >= 1, "Signal array must have at least 1 entry"

        entry = data[0]
        assert "id" in entry, "Missing field: id"
        assert "from" in entry, "Missing field: from"
        assert "message" in entry, "Missing field: message"
        assert "ts" in entry, "Missing field: ts"
        assert entry["from"] == "Commander"
        assert "Format check" in entry["message"]


# ---------------------------------------------------------------------------
# Check 3 — check_notifications.sh outputs message + deletes file
# ---------------------------------------------------------------------------
@pytest.mark.skipif(CHECK_SCRIPT is None, reason="check_notifications.sh not found on this branch (pre-merge)")
class TestHookScript:
    def test_hook_reads_and_deletes(self, task_board):
        """check_notifications.sh must output notification text and delete the signal file."""
        task_board.notify(
            target_role=TEST_ROLE,
            message="HookTestMessage",
            source_role="Zeta",
        )
        assert SIGNAL_FILE.exists(), "Signal file must exist before hook runs"

        env = {**os.environ, "VETKA_AGENT_ROLE": TEST_ROLE}
        result = subprocess.run(
            ["bash", str(CHECK_SCRIPT), TEST_ROLE],
            capture_output=True, text=True, env=env, timeout=5,
        )

        assert result.returncode == 0, f"Script exited {result.returncode}: {result.stderr}"
        assert "HookTestMessage" in result.stdout, (
            f"Message not in output.\nstdout: {result.stdout!r}"
        )
        assert not SIGNAL_FILE.exists(), "Signal file must be deleted after hook reads it"

    def test_hook_noop_when_no_signal(self):
        """Hook must exit 0 silently when no signal file exists."""
        assert not SIGNAL_FILE.exists()

        result = subprocess.run(
            ["bash", str(CHECK_SCRIPT), TEST_ROLE],
            capture_output=True, text=True, timeout=2,
        )
        assert result.returncode == 0
        assert result.stdout == ""

    def test_hook_speed(self, task_board):
        """Hook must complete in < 1 second (both with and without signal)."""
        # Without signal
        t0 = time.time()
        subprocess.run(["bash", str(CHECK_SCRIPT), TEST_ROLE], capture_output=True, timeout=2)
        assert time.time() - t0 < 1.0, "No-signal hook took >= 1s"

        # With signal
        task_board.notify(target_role=TEST_ROLE, message="speed test", source_role="Commander")
        t1 = time.time()
        subprocess.run(["bash", str(CHECK_SCRIPT), TEST_ROLE], capture_output=True, timeout=2)
        assert time.time() - t1 < 1.0, "Signal hook took >= 1s"


# ---------------------------------------------------------------------------
# Check 4 — multiple notifies append (not overwrite)
# ---------------------------------------------------------------------------
class TestSignalAppend:
    def test_multiple_notifies_append(self, task_board):
        """Three notify() calls must produce an array of 3 entries, not overwrite."""
        messages = ["First", "Second", "Third"]
        for msg in messages:
            task_board.notify(target_role=TEST_ROLE, message=msg, source_role="Commander")

        data = json.loads(SIGNAL_FILE.read_text(encoding="utf-8"))
        assert isinstance(data, list), "Must be a JSON array"
        assert len(data) == 3, f"Expected 3 entries, got {len(data)}"

        found_messages = [e["message"] for e in data]
        for msg in messages:
            assert any(msg in m for m in found_messages), f"Missing message: {msg}"

    def test_append_preserves_existing(self, task_board):
        """Manual pre-write + notify() must preserve the pre-existing entry."""
        pre_existing = [{"id": "manual_1", "from": "Test", "message": "pre", "ts": "2026-01-01", "ntype": "custom", "task_id": ""}]
        SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        SIGNAL_FILE.write_text(json.dumps(pre_existing), encoding="utf-8")

        task_board.notify(target_role=TEST_ROLE, message="appended", source_role="Commander")

        data = json.loads(SIGNAL_FILE.read_text(encoding="utf-8"))
        assert len(data) == 2, f"Expected 2 entries after append, got {len(data)}"
        assert data[0]["id"] == "manual_1", "Pre-existing entry must be preserved at index 0"
        assert "appended" in data[1]["message"]


# ---------------------------------------------------------------------------
# Check 5 — full cycle timing < 5s
# ---------------------------------------------------------------------------
class TestFullCycleTiming:
    def test_full_cycle_under_5s(self, task_board):
        """Complete cycle (notify + verify + cleanup) must finish in < 5 seconds."""
        t0 = time.time()

        # notify
        result = task_board.notify(target_role=TEST_ROLE, message="timing test", source_role="Commander")
        assert result.get("success")

        # verify file
        assert SIGNAL_FILE.exists()
        data = json.loads(SIGNAL_FILE.read_text(encoding="utf-8"))
        assert len(data) == 1

        # cleanup
        SIGNAL_FILE.unlink()
        assert not SIGNAL_FILE.exists()

        elapsed = time.time() - t0
        assert elapsed < 5.0, f"Full cycle took {elapsed:.2f}s (limit: 5s)"
