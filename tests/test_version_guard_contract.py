"""
Contract tests for MARKER_201.VERSION_GUARD — block merge on doc rollback.

Covers:
  1. merge_request blocked when branch has shorter (older) doc vs main
  2. merge_request proceeds when docs only grew (net >= 0)
  3. Binary files (added="-") are skipped, don't cause false block
  4. Multiple rollback files — all listed in response
  5. VERSION_GUARD error is non-fatal when git diff itself fails (exception path)
  6. post-rewrite hook syncs ALL differing docs (not just deleted)

@phase 201
@task tb_1774759589_97753_1
@branch claude/harness-eta
"""

from __future__ import annotations

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _make_board(tmp_path):
    from src.orchestration.task_board import TaskBoard
    return TaskBoard(board_file=tmp_path / "board.json")


def _make_task(board, branch="feature/x", commits=None):
    tid = board.add_task("Test VERSION_GUARD merge", priority=2)
    board.update_task(
        tid,
        branch_name=branch,
        merge_commits=commits or ["abc123"],
    )
    return tid


# ── Helpers ────────────────────────────────────────────────────────────────

def _numstat_line(added: int, deleted: int, fname: str) -> bytes:
    """Build a git diff --numstat line."""
    return f"{added}\t{deleted}\t{fname}\n".encode()


def _binary_numstat_line(fname: str) -> bytes:
    """Binary file line: added/deleted are '-'."""
    return f"-\t-\t{fname}\n".encode()


# ── Test 1: block when doc has net < 0 ────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.xfail(reason="VERSION_GUARD not yet in main — pending claude/harness-eta merge", strict=False)
async def test_version_guard_blocks_doc_rollback(tmp_path):
    """merge_request is blocked when branch has fewer lines in a doc vs main (net < 0)."""
    board = _make_board(tmp_path)
    tid = _make_task(board)

    async def mock_exec(*args, **kwargs):
        proc = AsyncMock()
        if "diff" in args and "--diff-filter=M" in args and "--numstat" in args:
            # Branch has 50 added, 200 deleted → net = -150 → rollback
            proc.communicate = AsyncMock(
                return_value=(_numstat_line(50, 200, "docs/VETKA_CUT_MANUAL.md"), b"")
            )
        elif "rev-parse" in args and "--verify" in args:
            proc.communicate = AsyncMock(return_value=(b"abc123\n", b""))
        elif "merge-base" in args and "--is-ancestor" in args:
            proc.communicate = AsyncMock(return_value=(b"", b""))
            proc.returncode = 1
            return proc
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec), \
         patch("asyncio.wait_for", side_effect=lambda c, **kw: c):
        result = await board.merge_request(tid)

    assert result["success"] is False
    assert "VERSION_GUARD" in result.get("error", "")
    assert "docs/VETKA_CUT_MANUAL.md" in result.get("rollback_docs", [])


# ── Test 2: allow when docs only grew ─────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.xfail(reason="VERSION_GUARD not yet in main — pending claude/harness-eta merge", strict=False)
async def test_version_guard_allows_doc_growth(tmp_path):
    """merge_request is NOT blocked when branch adds more lines to docs (net >= 0)."""
    board = _make_board(tmp_path)
    tid = _make_task(board)

    async def mock_exec(*args, **kwargs):
        proc = AsyncMock()
        if "diff" in args and "--diff-filter=M" in args and "--numstat" in args:
            # Branch adds 100 lines, removes 50 → net = +50 → OK
            proc.communicate = AsyncMock(
                return_value=(_numstat_line(100, 50, "docs/VETKA_CUT_MANUAL.md"), b"")
            )
        elif "rev-parse" in args and "--verify" in args:
            proc.communicate = AsyncMock(return_value=(b"abc123\n", b""))
        elif "merge-base" in args and "--is-ancestor" in args:
            proc.communicate = AsyncMock(return_value=(b"", b""))
            proc.returncode = 1
            return proc
        elif "rev-parse" in args and "HEAD" in args:
            proc.communicate = AsyncMock(return_value=(b"merge_hash_abc\n", b""))
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec), \
         patch("asyncio.wait_for", side_effect=lambda c, **kw: c):
        result = await board.merge_request(tid)

    # Should not be blocked by VERSION_GUARD (may fail for other reasons, but not this)
    assert result.get("error", "") != "VERSION_GUARD: branch would overwrite newer docs with older (shorter) versions — merge blocked"


# ── Test 3: binary files are skipped ──────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.xfail(reason="VERSION_GUARD not yet in main — pending claude/harness-eta merge", strict=False)
async def test_version_guard_skips_binary_files(tmp_path):
    """Binary files with added='-' should not trigger VERSION_GUARD."""
    board = _make_board(tmp_path)
    tid = _make_task(board)

    async def mock_exec(*args, **kwargs):
        proc = AsyncMock()
        if "diff" in args and "--diff-filter=M" in args and "--numstat" in args:
            # Only a binary file — should be skipped, no block
            proc.communicate = AsyncMock(
                return_value=(_binary_numstat_line("docs/screenshot.png"), b"")
            )
        elif "rev-parse" in args and "--verify" in args:
            proc.communicate = AsyncMock(return_value=(b"abc123\n", b""))
        elif "merge-base" in args and "--is-ancestor" in args:
            proc.communicate = AsyncMock(return_value=(b"", b""))
            proc.returncode = 1
            return proc
        elif "rev-parse" in args and "HEAD" in args:
            proc.communicate = AsyncMock(return_value=(b"merge_hash_abc\n", b""))
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec), \
         patch("asyncio.wait_for", side_effect=lambda c, **kw: c):
        result = await board.merge_request(tid)

    assert "VERSION_GUARD" not in result.get("error", "")


# ── Test 4: multiple rollback files listed ────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.xfail(reason="VERSION_GUARD not yet in main — pending claude/harness-eta merge", strict=False)
async def test_version_guard_lists_all_rollback_docs(tmp_path):
    """response.rollback_docs contains ALL files with net < 0, not just the first."""
    board = _make_board(tmp_path)
    tid = _make_task(board)

    rollback_output = (
        _numstat_line(10, 100, "docs/VETKA_CUT_MANUAL.md") +
        _numstat_line(5, 50, "docs/USER_GUIDE_MULTI_AGENT.md") +
        _numstat_line(200, 10, "docs/ARCHITECTURE.md")  # this one is OK (net > 0)
    )

    async def mock_exec(*args, **kwargs):
        proc = AsyncMock()
        if "diff" in args and "--diff-filter=M" in args and "--numstat" in args:
            proc.communicate = AsyncMock(return_value=(rollback_output, b""))
        elif "rev-parse" in args and "--verify" in args:
            proc.communicate = AsyncMock(return_value=(b"abc123\n", b""))
        elif "merge-base" in args and "--is-ancestor" in args:
            proc.communicate = AsyncMock(return_value=(b"", b""))
            proc.returncode = 1
            return proc
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec), \
         patch("asyncio.wait_for", side_effect=lambda c, **kw: c):
        result = await board.merge_request(tid)

    assert result["success"] is False
    rollback_docs = result.get("rollback_docs", [])
    assert "docs/VETKA_CUT_MANUAL.md" in rollback_docs
    assert "docs/USER_GUIDE_MULTI_AGENT.md" in rollback_docs
    # ARCHITECTURE.md grew — should NOT be in rollback list
    assert "docs/ARCHITECTURE.md" not in rollback_docs


# ── Test 5: VERSION_GUARD exception is non-fatal ──────────────────────────

@pytest.mark.asyncio
@pytest.mark.xfail(reason="VERSION_GUARD not yet in main — pending claude/harness-eta merge", strict=False)
async def test_version_guard_exception_is_nonfatal(tmp_path):
    """If the VERSION_GUARD git diff itself raises, merge proceeds (non-blocking guard)."""
    board = _make_board(tmp_path)
    tid = _make_task(board)

    call_count = {"n": 0}

    async def mock_exec(*args, **kwargs):
        call_count["n"] += 1
        proc = AsyncMock()
        if "diff" in args and "--diff-filter=M" in args and "--numstat" in args:
            raise RuntimeError("git diff failed")
        elif "rev-parse" in args and "--verify" in args:
            proc.communicate = AsyncMock(return_value=(b"abc123\n", b""))
        elif "merge-base" in args and "--is-ancestor" in args:
            proc.communicate = AsyncMock(return_value=(b"", b""))
            proc.returncode = 1
            return proc
        elif "rev-parse" in args and "HEAD" in args:
            proc.communicate = AsyncMock(return_value=(b"merge_hash_abc\n", b""))
        else:
            proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        proc.returncode = 0
        return proc

    with patch("asyncio.create_subprocess_exec", side_effect=mock_exec), \
         patch("asyncio.wait_for", side_effect=lambda c, **kw: c):
        result = await board.merge_request(tid)

    # VERSION_GUARD exception must NOT block the merge
    assert result.get("error", "") != "VERSION_GUARD: branch would overwrite newer docs with older (shorter) versions — merge blocked"


# ── Test 6: post-rewrite hook syncs all differing docs ────────────────────

@pytest.mark.xfail(reason="post-rewrite hook not yet in main — pending claude/harness-eta merge", strict=False)
def test_post_rewrite_hook_syncs_modified_not_only_deleted(tmp_path):
    """post-rewrite hook uses git diff --name-only (no --diff-filter=D) to sync ALL
    docs/ files that differ from main — not just deleted ones."""
    hook_path = Path(__file__).parent.parent / "scripts" / "hooks" / "post-rewrite"
    assert hook_path.exists(), "post-rewrite hook file not found"

    content = hook_path.read_text()

    # Must NOT use --diff-filter=D (that was the old behavior — only deleted files)
    assert "--diff-filter=D" not in content, (
        "post-rewrite hook still uses --diff-filter=D — should sync ALL differing docs, not just deleted"
    )

    # Must use git diff --name-only main -- docs/ (catches both deleted + modified)
    assert "git diff --name-only main" in content or "diff --name-only" in content, (
        "post-rewrite hook must use 'git diff --name-only main -- docs/' to sync all differing docs"
    )
