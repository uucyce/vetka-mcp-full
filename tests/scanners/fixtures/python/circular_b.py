# ========================================
# MARKER: Phase 72.2 Test Fixture
# File: tests/scanners/fixtures/python/circular_b.py
# Purpose: Test circular dependency handling (file B)
# ========================================
"""
Test fixture: Circular dependencies (file B).

This file imports ClassA directly (no TYPE_CHECKING needed
because A doesn't import B at runtime).

At import time:
1. circular_b.py is imported
2. circular_b imports circular_a
3. circular_a does NOT import circular_b (TYPE_CHECKING=False at runtime)
4. circular_a loads successfully
5. circular_b loads successfully

No circular import error occurs!
"""

# Direct import - safe because circular_a.py uses TYPE_CHECKING
from .circular_a import ClassA


class ClassB:
    """Class B that imports Class A directly."""

    def __init__(self, name: str):
        self.name = name
        self._a_instance: ClassA | None = None

    def set_a_instance(self, a: ClassA) -> None:
        """Set reference to ClassA instance."""
        self._a_instance = a

    def use_a(self, a: ClassA) -> str:
        """Use ClassA instance directly."""
        return f"{self.name} using {a.get_info()}"

    def create_a(self, name: str) -> ClassA:
        """Create a new ClassA instance."""
        return ClassA(name)
