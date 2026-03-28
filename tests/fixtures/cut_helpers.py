"""
Shared helper functions for CUT contract tests.

Extracted from 10+ test files where _read(), _find(), _strip_comments()
were independently defined with identical implementations.
"""

import re
from pathlib import Path

import pytest


def read_source(path: Path) -> str:
    """
    Read a source file, skipping test if file doesn't exist.

    Replaces the pattern duplicated in 10+ test files:
        def _read(path: Path) -> str:
            if not path.exists():
                pytest.skip(f"File not found: {path}")
            return path.read_text()
    """
    if not path.exists():
        pytest.skip(f"Source file not found: {path}")
    return path.read_text(errors="ignore")


def find_pattern(source: str, pattern: str) -> bool:
    """
    Check if a regex pattern exists in source text.

    Replaces the _find() helper duplicated in 5 test files.
    """
    return bool(re.search(pattern, source))


def find_all(source: str, pattern: str) -> list:
    """Return all regex matches in source text."""
    return re.findall(pattern, source)


# ── Comment stripping ─────────────────────────────────────────────────────

SINGLE_LINE_COMMENT_RE = re.compile(r"//.*$", re.MULTILINE)
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_comments(text: str) -> str:
    """
    Remove single-line (//) and block (/* */) comments from source text.

    Preserves line numbers by replacing block comments with equivalent
    newlines. Used by monochrome enforcement, static analysis, and
    dead import detection tests.
    """
    # Strip block comments first (they can span lines)
    text = BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group().count("\n"), text)
    # Strip single-line comments
    lines = text.splitlines()
    clean = []
    for line in lines:
        clean.append(SINGLE_LINE_COMMENT_RE.sub("", line))
    return "\n".join(clean)


def count_pattern(source: str, pattern: str) -> int:
    """Count occurrences of a regex pattern in source text."""
    return len(re.findall(pattern, source))


def assert_pattern_exists(source: str, pattern: str, msg: str = "") -> None:
    """Assert that a regex pattern exists in source. Gives clear error on failure."""
    assert find_pattern(source, pattern), (
        msg or f"Pattern not found: {pattern!r}"
    )


def assert_pattern_absent(source: str, pattern: str, msg: str = "") -> None:
    """Assert that a regex pattern does NOT exist in source."""
    assert not find_pattern(source, pattern), (
        msg or f"Unexpected pattern found: {pattern!r}"
    )
