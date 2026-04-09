# MARKER_136.FILE_CONNECTIONS_API
"""Build file connections for knowledge-mode file graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from src.scanners.python_scanner import PythonScanner


def _collect_python_files(base_dir: Path) -> List[Path]:
    return sorted(
        p for p in base_dir.glob("*.py")
        if p.is_file()
    )


def build_file_connections(
    target_file: str,
    project_root: str,
    max_connections: int = 50,
) -> Dict[str, Any]:
    """
    Build import/reverse-import connections for a file.

    Current implementation is deterministic and local:
    - Scans Python files in the same folder
    - Uses PythonScanner AST import extraction + resolver
    """
    target_path = Path(target_file).resolve()
    root_path = Path(project_root).resolve()

    if not target_path.exists() or not target_path.is_file():
        return {"file": str(target_path), "connections": [], "error": "File not found"}

    folder = target_path.parent
    files = _collect_python_files(folder)
    if target_path.suffix == ".py" and target_path not in files:
        files.append(target_path)

    scanned_files = [str(p) for p in files]
    scanner = PythonScanner(
        project_root=root_path,
        scanned_files=scanned_files,
        src_roots=["src"],
        include_external=False,
    )

    connections: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    def add_connection(target: str, score: float, relation_type: str, via: str) -> None:
        key = (target, relation_type)
        if key in seen:
            return
        seen.add(key)
        connections.append(
            {
                "target": target,
                "score": round(float(score), 3),
                "relation_type": relation_type,
                "via": via,
            }
        )

    # Outbound imports: target_file -> imported local file
    if target_path.suffix == ".py":
        content = target_path.read_text(encoding="utf-8", errors="replace")
        try:
            deps = scanner.extract_dependencies(str(target_path), content)
        except Exception:
            deps = []
        for dep in deps:
            dep_target = getattr(dep, "source", None)
            dep_conf = getattr(dep, "confidence", 0.0)
            dep_ctx = getattr(dep, "context", "") or "import"
            if not dep_target:
                continue
            if Path(dep_target).resolve().parent != folder:
                continue
            add_connection(str(Path(dep_target).resolve()), dep_conf, "imports", str(dep_ctx))

    # Inbound imports: other file in folder imports target_file
    for candidate in files:
        if candidate == target_path:
            continue
        try:
            candidate_content = candidate.read_text(encoding="utf-8", errors="replace")
            deps = scanner.extract_dependencies(str(candidate), candidate_content)
        except Exception:
            continue
        for dep in deps:
            dep_target = getattr(dep, "source", None)
            dep_conf = getattr(dep, "confidence", 0.0)
            dep_ctx = getattr(dep, "context", "") or "import"
            if not dep_target:
                continue
            if Path(dep_target).resolve() == target_path:
                add_connection(str(candidate.resolve()), dep_conf, "referenced_by", str(dep_ctx))

    connections.sort(key=lambda x: (-x["score"], x["relation_type"], x["target"]))
    return {
        "file": str(target_path),
        "connections": connections[:max_connections],
    }
