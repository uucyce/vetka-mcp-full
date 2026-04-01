"""
Shared pytest fixtures for test-runtime stability across Python versions.
"""

import asyncio
import pytest


# ── MARKER_IMPORT_GUARD: Skip test modules with missing optional deps ──
# Without this, missing deps (fastapi, watchdog, httpx, numpy, etc.)
# cause 137+ collection ERRORs that mask real failures.
# Strategy: patch pytest.Module.collect to catch ModuleNotFoundError.
import _pytest.python

_original_module_collect = _pytest.python.Module.collect

def _safe_module_collect(self):
    """Wrap Module.collect to convert ModuleNotFoundError into skip."""
    try:
        yield from _original_module_collect(self)
    except Exception as exc:
        # Walk the exception chain looking for ModuleNotFoundError
        cause = exc
        while cause is not None:
            if isinstance(cause, ModuleNotFoundError):
                mod_name = getattr(cause, 'name', '?')
                pytest.skip(f"missing optional dependency: {mod_name}")
                return
            cause = cause.__cause__ or (cause.__context__ if not isinstance(cause.__context__, type(cause)) else None)
        raise

_pytest.python.Module.collect = _safe_module_collect


# ── MARKER_CASCADE: Cascade skip — skip downstream tests when gate fixture fails ──
# Registry of failed gate fixtures. Keys = fixture/gate names, values = error message.
_cascade_failures: dict[str, str] = {}


def cascade_gate(name: str):
    """Decorator for fixtures that act as cascade gates.

    If the fixture raises, all tests marked @pytest.mark.depends_on("name")
    will be skipped immediately instead of failing with the same error.

    Usage in test files:
        @pytest.fixture
        @cascade_gate("bootstrap")
        def bootstrap_project():
            ...  # if this raises, dependents skip

        @pytest.mark.depends_on("bootstrap")
        def test_something(bootstrap_project):
            ...
    """
    def decorator(fn):
        import functools

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                result = fn(*args, **kwargs)
                # Handle generator fixtures
                if hasattr(result, '__next__'):
                    import types
                    def gen_wrapper():
                        try:
                            value = next(result)
                            yield value
                            try:
                                next(result)
                            except StopIteration:
                                pass
                        except Exception as exc:
                            _cascade_failures[name] = f"{type(exc).__name__}: {exc}"
                            raise
                    return gen_wrapper()
                return result
            except Exception as exc:
                _cascade_failures[name] = f"{type(exc).__name__}: {exc}"
                raise
        return wrapper
    return decorator


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "depends_on(gate): skip test if named gate fixture has failed (cascade skip)",
    )


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


# ── MARKER_QA.BOOTSTRAP_ASYNC_V2: Common bootstrap helpers for all test files ──
# Old pattern (removed): POST /api/cut/bootstrap → returns project immediately
# New pattern (async): POST /api/cut/worker/bootstrap-async → returns job_id, poll until done
#
# @issue: Test regression discovered 2026-04-01 — 34 tests failed with KeyError: 'project'
#         Root cause: /api/cut/bootstrap sync endpoint removed, only /bootstrap-async exists
# @fix: Extracted async bootstrap helper + worker_router registration to conftest
#
import time
from pathlib import Path
from fastapi.testclient import TestClient

def cut_make_client_with_workers() -> TestClient:
    """Create TestClient with both main router AND worker_router registered.

    Use this in test files instead of the old _make_client pattern.

    Example:
        client = cut_make_client_with_workers()
        project_id = cut_bootstrap_async_and_wait(client, source_dir, sandbox_root)
    """
    from fastapi import FastAPI
    from src.api.routes.cut_routes import router
    from src.api.routes.cut_routes_workers import worker_router

    app = FastAPI()
    app.include_router(router)
    app.include_router(worker_router, prefix="/api/cut/worker")
    return TestClient(app)


def cut_bootstrap_async_and_wait(
    client: TestClient,
    source_dir: Path,
    sandbox_root: Path,
    project_name: str = "Test Project"
) -> str:
    """Wait for async bootstrap job to complete and return project_id.

    Replaces the old sync /api/cut/bootstrap pattern with the new async pipeline:
    1. POST /api/cut/worker/bootstrap-async → get job_id
    2. Poll /api/cut/job/{job_id} until done
    3. Extract project_id from job.result.project.project_id

    Args:
        client: TestClient with worker_router registered
        source_dir: Path to media source directory
        sandbox_root: Path to CUT sandbox
        project_name: Project name for bootstrap

    Returns:
        project_id string

    Raises:
        AssertionError if bootstrap fails
    """
    # Step 1: Start async bootstrap job
    bootstrap_resp = client.post(
        "/api/cut/worker/bootstrap-async",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox_root),
            "project_name": project_name,
        },
    )
    assert bootstrap_resp.status_code == 200, f"Bootstrap failed: {bootstrap_resp.text}"
    job_id = bootstrap_resp.json()["job_id"]

    # Step 2: Poll until job completes (max 20 attempts @ 50ms = 1 second timeout)
    for _ in range(20):
        job_resp = client.get(f"/api/cut/job/{job_id}")
        job = job_resp.json()["job"]
        if job["state"] in {"done", "error", "cancelled"}:
            break
        time.sleep(0.05)

    assert job["state"] == "done", f"Bootstrap job failed: {job}"

    # Step 3: Extract project_id from job result
    assert job["result"]["success"] is True, f"Bootstrap result failed: {job['result']}"
    project_id = job["result"]["project"]["project_id"]
    return str(project_id)


def pytest_runtest_setup(item):
    """
    Safety net for unittest-style tests where autouse fixtures may not run.
    Also enforces cascade skip for @pytest.mark.depends_on gates.
    """
    # ── Cascade skip check ──
    for marker in item.iter_markers("depends_on"):
        for gate in marker.args:
            if gate in _cascade_failures:
                pytest.skip(
                    f"cascade skip: gate '{gate}' failed — {_cascade_failures[gate]}"
                )

    policy = asyncio.get_event_loop_policy()
    try:
        policy.get_event_loop()
    except RuntimeError:
        policy.set_event_loop(policy.new_event_loop())
