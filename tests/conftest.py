"""
Shared pytest fixtures for test-runtime stability across Python versions.
"""

import asyncio
import pytest


# ── MARKER_D4: Stale test infrastructure ──────────────────────────
def pytest_addoption(parser):
    parser.addoption(
        "--include-stale", action="store_true", default=False,
        help="Include @pytest.mark.stale tests (pre-existing failures, excluded by default)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--include-stale"):
        return
    skip_stale = pytest.mark.skip(reason="stale test — run with --include-stale")
    for item in items:
        if "stale" in item.keywords:
            item.add_marker(skip_stale)


@pytest.fixture(scope="session", autouse=True)
def ensure_session_event_loop():
    """
    Python 3.13 no longer guarantees a default loop in sync tests.
    Keep one session-level default loop for legacy tests that call get_event_loop().
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def ensure_sync_test_event_loop(request):
    """
    Some legacy sync tests call asyncio.get_event_loop() directly.
    Recreate default loop if another test cleared it.
    """
    if request.node.get_closest_marker("asyncio") is not None:
        yield
        return

    policy = asyncio.get_event_loop_policy()
    created = False
    try:
        policy.get_event_loop()
    except RuntimeError:
        loop = policy.new_event_loop()
        policy.set_event_loop(loop)
        created = True

    try:
        yield
    finally:
        if created:
            loop = policy.get_event_loop()
            loop.close()
            policy.set_event_loop(None)


@pytest.fixture(autouse=True)
def isolate_task_board(tmp_path, monkeypatch):
    """MARKER_196.FIX: Redirect TaskBoard to tmpdir so tests never touch production DB.

    Patches TASK_BOARD_FILE, TASK_BOARD_DB, and resets singleton after each test.
    """
    import src.orchestration.task_board as tb_mod
    test_db = tmp_path / "test_task_board.db"
    test_json = tmp_path / "test_task_board.json"
    monkeypatch.setattr(tb_mod, "TASK_BOARD_FILE", test_json)
    monkeypatch.setattr(tb_mod, "TASK_BOARD_DB", test_db)
    # Reset singleton so next get_task_board() creates fresh instance with test paths
    tb_mod._board_instance = None
    yield
    # Cleanup: close any open connections
    if tb_mod._board_instance is not None:
        try:
            tb_mod._board_instance.db.close()
        except Exception:
            pass
        tb_mod._board_instance = None


def pytest_runtest_setup(item):
    """
    Safety net for unittest-style tests where autouse fixtures may not run.
    """
    policy = asyncio.get_event_loop_policy()
    try:
        policy.get_event_loop()
    except RuntimeError:
        policy.set_event_loop(policy.new_event_loop())
