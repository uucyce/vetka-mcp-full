"""
Shared pytest fixtures for test-runtime stability across Python versions.
"""

import asyncio
import pytest


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


def pytest_runtest_setup(item):
    """
    Safety net for unittest-style tests where autouse fixtures may not run.
    """
    policy = asyncio.get_event_loop_policy()
    try:
        policy.get_event_loop()
    except RuntimeError:
        policy.set_event_loop(policy.new_event_loop())
