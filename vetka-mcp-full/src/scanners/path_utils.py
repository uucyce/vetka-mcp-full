# ========================================
# MARKER: Phase 72.2 Python Import Resolution
# Date: 2026-01-19
# File: src/scanners/path_utils.py
# Purpose: Path utility functions for import resolution
# Research: IMPORT_PATTERNS_AUDIT.md (Haiku)
# ========================================
"""
Path utility functions for import resolution.

Provides helpers for:
- Finding Python files recursively
- Checking if directory is a package
- Converting file paths to module names

@status: active
@phase: 96
@depends: pathlib
@used_by: import_resolver, python_scanner
"""

from pathlib import Path
from typing import List, Optional


def get_python_files(root: Path, exclude_patterns: Optional[List[str]] = None) -> List[Path]:
    """
    Recursively find all Python files in directory.

    Args:
        root: Root directory to search
        exclude_patterns: Optional list of patterns to exclude (e.g., ['__pycache__', '.git'])

    Returns:
        List of absolute paths to .py files

    Example:
        >>> files = get_python_files(Path("/project"))
        >>> print(files[0])
        /project/src/main.py
    """
    if exclude_patterns is None:
        exclude_patterns = ['__pycache__', '.git', '.venv', 'venv', 'node_modules', '.pytest_cache']

    result = []
    for py_file in root.rglob('*.py'):
        # Check if any parent directory matches exclude patterns
        skip = False
        for part in py_file.parts:
            if part in exclude_patterns:
                skip = True
                break
        if not skip:
            result.append(py_file.resolve())

    return result


def is_package(path: Path) -> bool:
    """
    Check if path is a Python package (has __init__.py).

    Args:
        path: Directory path

    Returns:
        True if package, False otherwise

    Example:
        >>> is_package(Path("/project/src"))  # Has __init__.py
        True
        >>> is_package(Path("/project/docs"))  # No __init__.py
        False
    """
    if not path.is_dir():
        return False
    return (path / '__init__.py').exists()


def get_module_name(file_path: Path, root: Path) -> str:
    """
    Get dotted module name for file.

    Converts file system paths to Python's dotted module notation.

    Examples:
        /project/utils.py → "utils"
        /project/foo/bar.py → "foo.bar"
        /project/pkg/__init__.py → "pkg"
        /project/src/api/handlers.py → "src.api.handlers"

    Args:
        file_path: Path to Python file
        root: Project root

    Returns:
        Dotted module name

    Raises:
        ValueError: If file is not under root
    """
    file_path = Path(file_path).resolve()
    root = Path(root).resolve()

    try:
        rel_path = file_path.relative_to(root)
    except ValueError as e:
        raise ValueError(f"File {file_path} is not under root {root}") from e

    # Handle __init__.py - return package name
    if file_path.name == '__init__.py':
        parts = list(rel_path.parent.parts)
    else:
        # Regular module: include directory parts + stem (no .py)
        parts = list(rel_path.parent.parts) + [rel_path.stem]

    # Filter out empty parts (for root-level files)
    parts = [p for p in parts if p]

    return '.'.join(parts) if parts else ''


def path_to_module_candidates(import_name: str, project_root: Path) -> List[Path]:
    """
    Generate candidate file paths for an import name.

    Used for fuzzy matching when exact module isn't in index.

    Args:
        import_name: Dotted import name (e.g., "foo.bar.baz")
        project_root: Project root directory

    Returns:
        List of candidate paths to check (module file, package __init__)

    Example:
        >>> path_to_module_candidates("foo.bar", Path("/project"))
        [Path("/project/foo/bar.py"), Path("/project/foo/bar/__init__.py")]
    """
    # Convert dots to path separators
    path_str = import_name.replace('.', '/')

    candidates = [
        # Try as module file: foo/bar.py
        project_root / (path_str + '.py'),
        # Try as package: foo/bar/__init__.py
        project_root / path_str / '__init__.py',
    ]

    return candidates


def normalize_path(path: str, project_root: Path) -> str:
    """
    Normalize a path to be relative to project root if possible.

    Args:
        path: Absolute or relative path
        project_root: Project root directory

    Returns:
        Path string (absolute if outside project, relative if inside)
    """
    path_obj = Path(path)

    # Make absolute if relative
    if not path_obj.is_absolute():
        path_obj = (project_root / path_obj).resolve()
    else:
        path_obj = path_obj.resolve()

    return str(path_obj)
