"""
Phase 150 file search service.

macOS-first local search with OS index + grep fallback.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".html", ".css", ".sql", ".go", ".rs", ".java", ".c", ".cpp",
}


def _detect_provider() -> str:
    if platform.system() == "Darwin" and shutil.which("mdfind"):
        return "mdfind"
    if shutil.which("fd"):
        return "fd"
    if shutil.which("rg"):
        return "rg"
    return "walk"


def _allowed_search_roots(provider: str) -> List[Path]:
    """
    MARKER_150.FILE_ROOT_POLICY_ALLOWED:
    file/ search is broader than VETKA indexed tree and may include parent workspace roots.
    """
    cwd = Path.cwd().resolve()
    home = Path.home().resolve()
    roots: List[Path]
    # MARKER_150.FILE_ROOT_POLICY_MAC_FULLFS:
    # macOS Finder-like mode uses Spotlight over full filesystem index.
    if platform.system() == "Darwin" and provider == "mdfind":
        # Fast-first order: user/workspace roots first, full FS fallback last.
        roots = [home, cwd.parent, cwd, Path("/")]
    else:
        # MARKER_150.FILE_ROOT_POLICY_XPLAT_PLACEHOLDER:
        # Linux/Windows remain scoped placeholders until dedicated OS adapters are implemented.
        roots = [home, cwd, cwd.parent]
    env_extra = os.getenv("VETKA_FILE_SEARCH_ROOTS", "").strip()
    if env_extra:
        for part in env_extra.split(":"):
            raw = part.strip()
            if not raw:
                continue
            try:
                p = Path(raw).expanduser().resolve()
            except Exception:
                continue
            roots.append(p)
    # Unique + existing dirs
    uniq: List[Path] = []
    seen: set[str] = set()
    for r in roots:
        key = r.as_posix()
        if key in seen:
            continue
        seen.add(key)
        if r.exists() and r.is_dir():
            uniq.append(r)
    return uniq


def get_file_search_capabilities() -> Dict[str, Any]:
    provider = _detect_provider()
    return {
        "success": True,
        "supported_modes": ["keyword", "filename"],
        "supports_name": True,
        "supports_content": bool(shutil.which("rg")),
        "supports_semantic": False,
        "supports_hybrid": False,
        "supports_fzf": bool(shutil.which("fzf")),
        "supports_duplicates_scan": bool(shutil.which("fdupes")),
        "active_provider": provider,
        "provider_health": {
            "mdfind": {"available": bool(shutil.which("mdfind"))},
            "rg": {"available": bool(shutil.which("rg"))},
            "fd": {"available": bool(shutil.which("fd"))},
            "fzf": {"available": bool(shutil.which("fzf"))},
            "fdupes": {"available": bool(shutil.which("fdupes"))},
        },
    }


def _normalize_item(path: str, snippet: str, score: float) -> Dict[str, Any]:
    abs_path = str(Path(path).expanduser().resolve())
    rel = abs_path
    try:
        rel = str(Path(abs_path).relative_to(Path.cwd().resolve()))
    except Exception:
        pass
    return {
        "source": "file",
        "title": rel,
        "snippet": (snippet or rel)[:500],
        "score": round(float(score), 4),
        "url": f"file://{abs_path}",
        "path": abs_path,
    }


def _score_filename_match(filename: str, query: str) -> float:
    ql = query.lower().strip()
    name_l = filename.lower().strip()
    stem_l = Path(filename).stem.lower().strip()
    q_stem = Path(query).stem.lower().strip()

    if name_l == ql:
        return 1.0
    if stem_l == ql or stem_l == q_stem:
        return 0.99
    if name_l.startswith(ql):
        return 0.97
    if ql in name_l:
        return 0.94
    if q_stem and q_stem in stem_l:
        return 0.92
    return 0.9


def _name_search_mdfind(root: Path, query: str, limit: int) -> List[Tuple[str, str, float]]:
    cmd = ["mdfind", "-name", query, "-onlyin", str(root)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=4, check=False)
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    out: List[Tuple[str, str, float]] = []
    ql = query.lower()
    for line in proc.stdout.splitlines():
        p = (line or "").strip()
        if not p:
            continue
        if not os.path.isfile(p):
            continue
        name = Path(p).name
        score = _score_filename_match(name, ql)
        out.append((p, p, score))
        if len(out) >= limit:
            break
    return out


def _name_search_walk(root: Path, query_l: str, limit: int) -> List[Tuple[str, str, float]]:
    out: List[Tuple[str, str, float]] = []
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = [d for d in dir_names if d not in SKIP_DIRS]
        for filename in file_names:
            if query_l not in filename.lower():
                continue
            p = str(Path(current_root) / filename)
            score = _score_filename_match(filename, query_l)
            out.append((p, filename, score))
            if len(out) >= limit:
                return out
    return out


def _content_search_rg(root: Path, query: str, limit: int) -> List[Tuple[str, str, float]]:
    if not shutil.which("rg"):
        return []
    cmd = [
        "rg",
        "--json",
        "--line-number",
        "--max-filesize",
        "8M",
        "--hidden",
        query,
        str(root),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
    except Exception:
        return []
    if proc.returncode not in (0, 1):
        return []
    out: List[Tuple[str, str, float]] = []
    for line in proc.stdout.splitlines():
        if '"type":"match"' not in line:
            continue
        try:
            # ultra-light parser without json import overhead in hot path
            pm = re.search(r'"path":\{"text":"([^"]+)"\}', line)
            lm = re.search(r'"text":"([^"]+)"', line)
            path = pm.group(1) if pm else ""
            snippet = lm.group(1) if lm else ""
            if not path:
                continue
            ext = Path(path).suffix.lower()
            if ext and ext not in TEXT_EXTENSIONS:
                continue
            out.append((path, snippet, 0.74))
            if len(out) >= limit:
                break
        except Exception:
            continue
    return out


def _rerank_items(items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    cwd = Path.cwd().resolve().as_posix()
    parent = Path.cwd().resolve().parent.as_posix()
    home = Path.home().resolve().as_posix()
    docs = str(Path.home().resolve() / "Documents")
    ql = query.lower().strip()
    q_stem = Path(query).stem.lower().strip()

    ranked: List[Dict[str, Any]] = []
    for item in items:
        p = str(item.get("path", "")).replace("\\", "/")
        base = Path(p).name.lower()
        stem = Path(p).stem.lower()
        s = float(item.get("score", 0.0))

        # Filename intent dominates in /file mode.
        if base == ql:
            s += 0.6
        elif stem == ql or (q_stem and stem == q_stem):
            s += 0.55
        elif base.startswith(ql):
            s += 0.35
        elif ql in base:
            s += 0.2

        # Prefer workspace/project locations.
        if p.startswith(cwd):
            s += 0.35
        elif p.startswith(parent):
            s += 0.22
        elif p.startswith(docs):
            s += 0.1
        elif p.startswith(home):
            s += 0.04

        # De-prioritize noisy system caches/config mirrors.
        if "/Library/" in p:
            s -= 0.4
        if "/.Trash/" in p:
            s -= 0.5

        item["score"] = round(s, 4)
        ranked.append(item)

    ranked.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    return ranked


def search_files(
    query: str,
    limit: int = 20,
    mode: str = "keyword",
) -> Dict[str, Any]:
    started = time.time()
    q = (query or "").strip()
    if len(q) < 2:
        return {"success": False, "error": "Query too short (min 2 characters)", "results": [], "count": 0, "took_ms": 0}

    safe_limit = max(1, min(int(limit or 20), 100))
    provider = _detect_provider()
    roots = _allowed_search_roots(provider)
    cwd = Path.cwd().resolve()
    walk_fallback_roots = {cwd.as_posix(), cwd.parent.as_posix()}

    merged: List[Tuple[str, str, float]] = []
    ql = q.lower()
    for idx, root in enumerate(roots):
        # On macOS with Spotlight provider, keep full filesystem root as fallback.
        # If we already have enough hits from focused roots, skip expensive "/".
        if provider == "mdfind" and root == Path("/") and len(merged) >= safe_limit:
            continue

        if mode == "filename":
            if provider == "mdfind":
                root_hits = _name_search_mdfind(root, q, safe_limit)
                if not root_hits and root.as_posix() in walk_fallback_roots:
                    root_hits = _name_search_walk(root, ql, safe_limit)
                merged.extend(root_hits)
            else:
                merged.extend(_name_search_walk(root, ql, safe_limit))
        else:
            # keyword mode: filename + content
            if provider == "mdfind":
                root_hits = _name_search_mdfind(root, q, safe_limit)
                if not root_hits and root.as_posix() in walk_fallback_roots:
                    root_hits = _name_search_walk(root, ql, safe_limit)
                merged.extend(root_hits)
            else:
                merged.extend(_name_search_walk(root, ql, safe_limit))
            # Avoid worst-case scans over full filesystem for content search.
            if not (root == Path("/") and provider == "mdfind"):
                merged.extend(_content_search_rg(root, q, safe_limit))
        if len(merged) >= safe_limit * 3:
            break

    by_path: Dict[str, Dict[str, Any]] = {}
    for path, snippet, score in merged:
        key = os.path.realpath(str(path))
        prev = by_path.get(key)
        item = _normalize_item(path, snippet, score)
        if prev is None or float(item["score"]) > float(prev["score"]):
            by_path[key] = item

    rows = _rerank_items(list(by_path.values()), q)[:safe_limit]
    return {
        "success": True,
        "results": rows,
        "count": len(rows),
        "mode": "filename" if mode == "filename" else "keyword",
        "active_provider": provider,
        "roots_used": [r.as_posix() for r in roots],
        "took_ms": int((time.time() - started) * 1000),
    }
