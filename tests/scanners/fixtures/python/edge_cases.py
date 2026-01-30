# ========================================
# MARKER: Phase 72.2 Test Fixture
# File: tests/scanners/fixtures/python/edge_cases.py
# Purpose: Test edge cases (aliases, out of bounds, syntax)
# ========================================
"""
Test fixture: Edge cases.

Edge cases that import resolver must handle:
1. Import aliases (import X as Y)
2. Out-of-bounds relative imports (too many ..)
3. Multiple imports from same module
4. Star imports (from X import *)
5. Submodule imports (import foo.bar.baz)
6. Name collisions (module and package with same name)
"""

# Pattern 1: Import aliases
# The resolver should track the MODULE, not the alias
import json as j
from pathlib import Path as P
from typing import Optional as Opt, List as L
from collections import defaultdict as dd

# Pattern 2: Multiple imports from same module
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Tuple,
    Union,
    Callable,
)

# Pattern 3: Star imports (generally discouraged but exist)
# from os.path import *  # Would import everything - bad practice

# Pattern 4: Submodule imports
import os.path
import urllib.parse
import email.mime.text

# Pattern 5: Relative import edge cases
# These would fail if file is at project root:
# from .... import something  # Too many dots - out of bounds

# Pattern 6: Mixed import styles in same statement
from dataclasses import dataclass, field as f, asdict

# Pattern 7: __future__ imports (must be first)
# from __future__ import annotations  # Would need to be at file top

# Pattern 8: Name collision example
# If both utils.py and utils/__init__.py exist:
# import utils  # Which one gets imported?
# Answer: utils/__init__.py (package takes precedence)


# Edge case patterns for testing
EDGE_CASE_PATTERNS = {
    'alias_simple': 'import json as j',
    'alias_from': 'from pathlib import Path as P',
    'alias_multiple': 'from typing import Optional as Opt, List as L',
    'multi_from_same': 'from typing import Dict, List, Optional',
    'submodule': 'import os.path',
    'deep_submodule': 'import email.mime.text',
    'mixed_styles': 'from dataclasses import dataclass, field as f',
}


# Out of bounds relative import examples (would fail)
OUT_OF_BOUNDS_EXAMPLES = [
    '.....',          # 5 dots from shallow file
    '...........',    # 10 dots - definitely out of bounds
    '..nonexistent',  # Parent doesn't have this module
]


# Usage to suppress linter warnings
_ = (j, P, Opt, L, dd, Dict, List, Optional, Any, Tuple, Union, Callable,
     os.path, urllib.parse, email.mime.text, dataclass, f, asdict)
