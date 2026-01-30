# ========================================
# MARKER: Phase 72.2 Test Fixture
# File: tests/scanners/fixtures/python/circular_a.py
# Purpose: Test circular dependency handling (file A)
# ========================================
"""
Test fixture: Circular dependencies (file A).

From VETKA audit:
- 2 circular dependency cycles detected
- Both resolved via TYPE_CHECKING pattern

Cycle 1: langgraph_builder.py <-> orchestrator_with_elisya.py
Cycle 2: middleware.py <-> memory_manager.py

This file simulates the TYPE_CHECKING pattern used to break cycles.
"""

from typing import TYPE_CHECKING

# This import only happens during type checking (mypy, pyright)
# At runtime, TYPE_CHECKING is False, so no actual import
if TYPE_CHECKING:
    from .circular_b import ClassB


class ClassA:
    """Class A that references Class B for type hints only."""

    def __init__(self, name: str):
        self.name = name
        self._b_reference: 'ClassB | None' = None

    def set_b_reference(self, b: 'ClassB') -> None:
        """Set reference to ClassB instance (type hint uses forward ref)."""
        self._b_reference = b

    def use_b(self, b: 'ClassB') -> str:
        """Use ClassB instance (breaks cycle via TYPE_CHECKING)."""
        return f"{self.name} using {b.name}"

    def get_info(self) -> str:
        """Get info about this instance."""
        return f"ClassA({self.name})"
