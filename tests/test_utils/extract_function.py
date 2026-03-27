"""
AST-based function extraction for testing pure Python functions
without importing their parent modules (avoids fastapi/qdrant/pydantic).

Usage:
    from tests.test_utils.extract_function import extract_function, extract_functions

    apply_ops = extract_function("src/api/routes/cut_routes.py", "_apply_timeline_ops")
    result = apply_ops(state, ops)

    fns = extract_functions("src/services/cut_color_pipeline.py",
                            ["_decode_vlog", "_decode_slog3"])
    fns["_decode_vlog"](np.array([0.5]))
"""
from __future__ import annotations

import ast
import textwrap
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np


_DEFAULT_NAMESPACE: dict[str, Any] = {
    "deepcopy": deepcopy,
    "uuid4": uuid4,
    "datetime": datetime,
    "timezone": timezone,
    "np": np,
    "Any": Any,
    "__builtins__": __builtins__,
}


def _resolve_path(filepath: str | Path) -> Path:
    """Resolve filepath relative to project root (parent of tests/)."""
    p = Path(filepath)
    if p.is_absolute():
        return p
    # Walk up from this file to find project root
    root = Path(__file__).resolve().parent.parent.parent
    return root / p


def _read_source(filepath: str | Path) -> str:
    path = _resolve_path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    return path.read_text(encoding="utf-8")


def _collect_function_nodes(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    """Collect all top-level function definitions from AST."""
    funcs: dict[str, ast.FunctionDef] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
    return funcs


def _find_dependencies(node: ast.FunctionDef, available: dict[str, ast.FunctionDef]) -> list[str]:
    """Find which sibling functions this function calls."""
    deps: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in available and child.id != node.name:
            if child.id not in deps:
                deps.append(child.id)
    return deps


def _topo_sort(names: list[str], all_funcs: dict[str, ast.FunctionDef]) -> list[str]:
    """Topological sort: dependencies first, then the requested functions."""
    visited: set[str] = set()
    order: list[str] = []

    def _visit(name: str) -> None:
        if name in visited or name not in all_funcs:
            return
        visited.add(name)
        for dep in _find_dependencies(all_funcs[name], all_funcs):
            _visit(dep)
        order.append(name)

    for name in names:
        _visit(name)
    return order


def extract_function(
    filepath: str | Path,
    function_name: str,
    extra_ns: dict[str, Any] | None = None,
) -> Any:
    """Extract a single function from a Python source file via AST.

    Automatically resolves sibling function dependencies (e.g. _find_lane
    called by _apply_timeline_ops) and includes them in the namespace.

    Returns:
        The extracted callable.

    Raises:
        FileNotFoundError: Source file not found.
        KeyError: Function not found in source.
    """
    fns = extract_functions(filepath, [function_name], extra_ns)
    return fns[function_name]


def extract_functions(
    filepath: str | Path,
    names: list[str],
    extra_ns: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract multiple functions from a Python source file via AST.

    All extracted functions share a namespace so they can call each other.
    Dependencies are auto-resolved via AST analysis.

    Returns:
        Dict mapping function name to callable.

    Raises:
        FileNotFoundError: Source file not found.
        KeyError: Any requested function not found in source.
    """
    source = _read_source(filepath)
    tree = ast.parse(source)
    all_funcs = _collect_function_nodes(tree)

    missing = [n for n in names if n not in all_funcs]
    if missing:
        available = sorted(all_funcs.keys())[:20]
        raise KeyError(
            f"Functions not found in {filepath}: {missing}. "
            f"Available (first 20): {available}"
        )

    # Topo-sort with auto-resolved dependencies
    ordered = _topo_sort(names, all_funcs)

    # Build shared namespace
    ns: dict[str, Any] = dict(_DEFAULT_NAMESPACE)
    if extra_ns:
        ns.update(extra_ns)

    # Compile and exec each function in order
    for fname in ordered:
        node = all_funcs[fname]
        # Create a module with just this function
        mod = ast.Module(body=[node], type_ignores=[])
        ast.fix_missing_locations(mod)
        code = compile(mod, filename=str(_resolve_path(filepath)), mode="exec")
        exec(code, ns)

    return {name: ns[name] for name in names}
