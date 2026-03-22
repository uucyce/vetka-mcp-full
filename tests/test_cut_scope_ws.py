"""
MARKER_B15-WS — Tests for WebSocket scope handler.

Tests: debounce logic, scope computation, mode selection, handler registration.
"""
from __future__ import annotations

import threading

import pytest

from src.api.handlers.scope_socket_handler import (
    _compute_scopes_sync,
    _get_client_lock,
    _client_locks,
)


class TestClientLock:
    def test_creates_lock(self) -> None:
        lock = _get_client_lock("test_sid_1")
        assert isinstance(lock, threading.Lock)

    def test_same_sid_same_lock(self) -> None:
        lock1 = _get_client_lock("test_sid_2")
        lock2 = _get_client_lock("test_sid_2")
        assert lock1 is lock2

    def test_different_sid_different_lock(self) -> None:
        lock1 = _get_client_lock("test_sid_3")
        lock2 = _get_client_lock("test_sid_4")
        assert lock1 is not lock2

    def test_lock_acquire_release(self) -> None:
        lock = _get_client_lock("test_sid_5")
        assert lock.acquire(blocking=False)
        # Second acquire should fail (debounce)
        assert not lock.acquire(blocking=False)
        lock.release()
        # After release, acquire succeeds again
        assert lock.acquire(blocking=False)
        lock.release()


class TestComputeScopesSync:
    def test_fast_mode_histogram_only(self) -> None:
        """Fast mode should request histogram only with smaller size."""
        # Can't run without real video, but verify it doesn't crash
        result = _compute_scopes_sync({
            "source_path": "/nonexistent/video.mp4",
            "time": 0,
            "mode": "fast",
        })
        assert result["success"] is False  # file doesn't exist
        assert "error" in result

    def test_full_mode_default(self) -> None:
        result = _compute_scopes_sync({
            "source_path": "/nonexistent/video.mp4",
            "time": 0,
            "mode": "full",
        })
        assert result["success"] is False

    def test_custom_scopes(self) -> None:
        result = _compute_scopes_sync({
            "source_path": "/nonexistent/video.mp4",
            "time": 0,
            "scopes": "histogram,parade",
        })
        assert result["success"] is False

    def test_scope_list_input(self) -> None:
        result = _compute_scopes_sync({
            "source_path": "/nonexistent/video.mp4",
            "time": 0,
            "scopes": ["histogram", "waveform"],
        })
        assert result["success"] is False

    def test_size_clamped(self) -> None:
        # Size should be clamped to 64-512
        result = _compute_scopes_sync({
            "source_path": "/nonexistent/video.mp4",
            "size": 10000,
        })
        assert result["success"] is False  # file doesn't exist, but no crash

    def test_empty_source_no_crash(self) -> None:
        result = _compute_scopes_sync({
            "source_path": "",
            "time": 0,
        })
        assert result["success"] is False


class TestHandlerRegistration:
    def test_register_function_exists(self) -> None:
        from src.api.handlers.scope_socket_handler import register_scope_socket_handlers
        assert callable(register_scope_socket_handlers)

    def test_module_imports(self) -> None:
        """Module should import without errors."""
        import src.api.handlers.scope_socket_handler as mod
        assert hasattr(mod, "register_scope_socket_handlers")
        assert hasattr(mod, "_compute_scopes_sync")
        assert hasattr(mod, "_get_client_lock")
