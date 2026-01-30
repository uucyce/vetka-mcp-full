# ========================================
# MARKER: Phase 72.2 Test Fixture
# File: tests/scanners/fixtures/python/dynamic_imports.py
# Purpose: Test dynamic/runtime imports
# ========================================
"""
Test fixture: Dynamic imports.

From VETKA audit:
- 4 dynamic imports found
- Used for: graceful degradation, lazy loading, capability detection

Patterns:
1. __import__(name) - built-in dynamic import
2. importlib.import_module(name) - recommended for Python 3
"""

import importlib
import sys


def check_package_available(package_name: str) -> bool:
    """
    Check if a package is available without importing it fully.

    Pattern from src/agents/learner_initializer.py
    """
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def lazy_import(module_name: str):
    """
    Lazy import a module at runtime.

    Useful for heavy ML libraries that take time to load.
    """
    return importlib.import_module(module_name)


def dynamic_import_example():
    """
    Example of dynamic import pattern from VETKA.

    Pattern from src/initialization/dependency_check.py
    """
    # String-based import
    module_name = "json"
    module = __import__(module_name)

    # importlib usage (preferred)
    json_module = importlib.import_module("json")

    # Import submodule
    path_module = importlib.import_module("pathlib")

    return module, json_module, path_module


# List of dynamic import patterns for testing
DYNAMIC_IMPORT_PATTERNS = [
    "__import__('json')",
    "importlib.import_module('json')",
    "importlib.import_module('pathlib')",
    "__import__(package_name)",  # Variable-based
]


# Example: graceful degradation
def get_optional_dependency(name: str, fallback=None):
    """
    Try to import optional dependency, return fallback if unavailable.

    Example usage:
        umap = get_optional_dependency('umap')
        if umap:
            # Use umap
        else:
            # Use fallback algorithm
    """
    try:
        return importlib.import_module(name)
    except ImportError:
        return fallback
