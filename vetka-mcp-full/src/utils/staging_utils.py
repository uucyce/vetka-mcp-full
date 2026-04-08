"""VETKA Staging Utils Stubs.

This module provides stub implementations for staging utilities.
These stubs allow the MCP server to run without full staging system.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List


class StagingArea:
    """Stub for staging area management."""

    def __init__(self, root: Optional[Path] = None):
        self._root = root or Path(tempfile.mkdtemp(prefix="vetka_staging_"))
        self._files: List[Path] = []

    def add(self, path: Path) -> Path:
        """Add file to staging area."""
        dest = self._root / path.name
        if path.exists():
            shutil.copy2(path, dest)
        self._files.append(dest)
        return dest

    def get_path(self, filename: str) -> Optional[Path]:
        """Get path for staged file."""
        for f in self._files:
            if f.name == filename:
                return f
        return self._root / filename

    def list_files(self) -> List[str]:
        """List all staged files."""
        return [f.name for f in self._files]

    def clear(self) -> None:
        """Clear staging area."""
        shutil.rmtree(self._root, ignore_errors=True)
        self._root = Path(tempfile.mkdtemp(prefix="vetka_staging_"))
        self._files = []


_staging_areas: dict = {}


def get_staging_area(name: str = "default") -> StagingArea:
    """Get or create staging area by name."""
    if name not in _staging_areas:
        _staging_areas[name] = StagingArea()
    return _staging_areas[name]


def stage_file(path: Path, area: str = "default") -> Path:
    """Stage a file for review."""
    staging = get_staging_area(area)
    return staging.add(path)


def unstage_file(filename: str, area: str = "default") -> bool:
    """Remove file from staging area."""
    staging = get_staging_area(area)
    for f in staging._files:
        if f.name == filename:
            staging._files.remove(f)
            return True
    return False
