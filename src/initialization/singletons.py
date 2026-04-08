"""VETKA Initialization Stubs.

This module provides stub implementations for MCP server initialization.
These stubs allow the MCP server to run without full VETKA backend.
"""

from typing import Optional, Any


class _MemoryManagerStub:
    """Stub for MemoryManager."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def search(self, query: str, **kwargs) -> list:
        return []


class _SocketIOStub:
    """Stub for Socket.IO instance."""

    def emit(self, event: str, data: Any = None, **kwargs):
        pass

    def on(self, event: str, handler):
        pass


class _ArcSolverStub:
    """Stub for ARC solver."""

    def solve(self, task: dict, **kwargs) -> dict:
        return {"status": "stub", "message": "ARC solver not available"}


_memory_manager: Optional[_MemoryManagerStub] = None
_socketio: Optional[_SocketIOStub] = None
_arc_solver: Optional[_ArcSolverStub] = None


def get_memory_manager() -> _MemoryManagerStub:
    """Get or create memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = _MemoryManagerStub()
    return _memory_manager


def get_socketio() -> Optional[_SocketIOStub]:
    """Get or create Socket.IO instance."""
    global _socketio
    if _socketio is None:
        _socketio = _SocketIOStub()
    return _socketio


def get_arc_solver() -> _ArcSolverStub:
    """Get or create ARC solver instance."""
    global _arc_solver
    if _arc_solver is None:
        _arc_solver = _ArcSolverStub()
    return _arc_solver
