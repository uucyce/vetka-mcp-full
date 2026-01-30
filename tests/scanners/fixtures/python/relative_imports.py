# ========================================
# MARKER: Phase 72.2 Test Fixture
# File: tests/scanners/fixtures/python/relative_imports.py
# Purpose: Test relative imports (., .., ...)
# ========================================
"""
Test fixture: Relative imports.

From VETKA audit:
- 160 relative imports total (132 unique)
- Patterns: from . import X, from .. import X, from ...utils import X

This file simulates the pattern but won't actually import
(would need proper package structure).
"""

# NOTE: These imports won't work standalone - they're patterns for testing
# The actual import resolution tests use tmp_path fixtures

# Examples of relative import patterns found in VETKA:

# Single-level relative imports (from same package)
# from . import sibling_module
# from . import Action, ActionCategory
# from . import ReasoningSession
# from .approval import ApprovalManager, ApprovalStatus
# from .base_scanner import BaseScanner
# from .exceptions import ScannerError

# Multi-level relative imports (from parent packages)
# from .. import parent_module
# from ..api.handlers import chat_handler
# from ..utils import helper_function
# from ...utils import quiet_logger

# Triple-dot relative (grandparent)
# from ...root import config

RELATIVE_IMPORT_PATTERNS = [
    ".",              # from . import X
    ".sibling",       # from .sibling import X
    "..",             # from .. import X
    "..parent",       # from ..parent import X
    "..utils.helper", # from ..utils.helper import X
    "...",            # from ... import X
    "...config",      # from ...config import X
]
