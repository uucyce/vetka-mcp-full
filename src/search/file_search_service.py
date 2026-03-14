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
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".html", ".css", ".sql", ".go", ".rs", ".java", ".c", ".cpp",
}

logger = logging.getLogger("VETKA_FILE_SEARCH")
DESCRIPTIVE_MIN_WORDS = max(4, int(os.getenv("VETKA_DESCRIPTIVE_MIN_WORDS", "4")))

_RU_EN_HINTS = {
    "абревиат": ["abbreviation", "abbreviations", "acronym", "abbr"],
    "аббревиат": ["abbreviation", "abbreviations", "acronym", "abbr"],
    "памят": ["memory", "dag", "cam", "arc", "elision", "engram", "hope"],
    "матриц": ["matrix", "matrices", "capability_matrix", "input_matrix"],
    "инпут": ["input", "inputs", "scanner", "contract"],
    "ввод": ["input", "inputs"],
    "документ": ["docs", "marker"],
    "файл": [],
    "стрим": ["stream", "streaming"],
    "инструмент": ["tool", "tools"],
    "модел": ["model", "models"],
    "фаз": ["phase", "marker", "ph"],
    "контракт": ["contract", "spec"],
    "интеграц": ["integration"],
    "анализ": ["analysis"],
}

_STOP_TOKENS = {
    "и", "в", "во", "на", "по", "про", "где", "все", "это", "как", "что", "для",
    "не", "помню", "найди", "нужен", "нужна", "нужно", "или", "а", "но", "к",
    "the", "for", "with", "from", "that", "this", "find", "file", "doc",
}

_DOC_PREF_TOKENS = {
    "doc", "docs", "документ", "доки", "markdown", "readme", "md",
    "marker", "phase", "фаз", "отчет", "report", "runtime", "map",
}

_TEST_NOISE_MARKERS = (
    "/tests/",
    "/test/",
    "/testdata/",
    "/fixtures/",
    "/fixture/",
    "/mock/",
    "/mocks/",
    "/samples/",
    "/sample/",
    "/benchmarks/",
    "/benchmark/",
)


def _tokenize_query(query: str) -> List[str]:
    return [t for t in re.split(r"[^a-zA-Zа-яА-Я0-9_]+", (query or "").lower()) if len(t) >= 2]


def _is_descriptive_query(query: str) -> bool:
    q = (query or "").lower()
    words = _tokenize_query(q)
    markers = ["найди файл где", "не помню", "документ", "про ", "где ", "какой файл"]
    file_like = any(x in q for x in [".py", ".md", ".txt", "marker_", "/", "\\"])
    multiword_nl = (len(words) >= DESCRIPTIVE_MIN_WORDS and not file_like)
    return multiword_nl or any(m in q for m in markers)


def _expand_query_terms(query: str, max_terms: int = 14) -> List[str]:
    tokens = _tokenize_query(query)
    expanded: List[str] = []
    seen = set()
    for tok in tokens:
        if tok in _STOP_TOKENS:
            continue
        if tok not in seen:
            seen.add(tok)
            expanded.append(tok)
        for stem, adds in _RU_EN_HINTS.items():
            if stem in tok:
                for a in adds:
                    if a not in seen:
                        seen.add(a)
                        expanded.append(a)
    return expanded[:max_terms]


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
        # Prefer current workspace first, full FS only as far fallback.
        roots = [cwd, cwd.parent, home, Path("/")]
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


def _name_search_find(root: Path, query: str, limit: int) -> List[Tuple[str, str, float]]:
    """
    Non-indexed filename search using `find` with timeout.
    Useful fallback when Spotlight index is stale.
    """
    if not shutil.which("find"):
        return []
    q = str(query or "").strip()
    if len(q) < 2:
        return []
    # Escape minimal glob-sensitive chars for predictable matching.
    safe = q.replace("[", r"\[").replace("]", r"\]").replace("*", r"\*").replace("?", r"\?")
    pattern = f"*{safe}*"
    cmd = ["find", str(root), "-type", "f", "-iname", pattern]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=4, check=False)
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    out: List[Tuple[str, str, float]] = []
    ql = q.lower()
    for line in proc.stdout.splitlines():
        p = (line or "").strip()
        if not p or not os.path.isfile(p):
            continue
        name = Path(p).name
        score = _score_filename_match(name, ql)
        out.append((p, p, score))
        if len(out) >= limit:
            break
    return out


def _name_search_walk_terms(root: Path, terms: List[str], limit: int) -> List[Tuple[str, str, float]]:
    out: List[Tuple[str, str, float]] = []
    if not terms:
        return out
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = [d for d in dir_names if d not in SKIP_DIRS]
        for filename in file_names:
            name_l = filename.lower()
            path_l = str(Path(current_root) / filename).lower()
            hits = [t for t in terms if len(t) >= 3 and (t in name_l or t in path_l)]
            if not hits:
                continue
            p = str(Path(current_root) / filename)
            score = 0.75 + min(0.2, (len(hits) * 0.04))
            out.append((p, ",".join(hits[:4]), score))
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


def _content_search_rg_terms(root: Path, terms: List[str], limit: int) -> List[Tuple[str, str, float]]:
    if not shutil.which("rg") or not terms:
        return []
    pattern_terms = [re.escape(t) for t in terms if len(t) >= 3][:8]
    if not pattern_terms:
        return []
    pattern = "|".join(pattern_terms)
    cmd = [
        "rg",
        "--json",
        "--line-number",
        "--max-filesize",
        "8M",
        "--hidden",
        "-i",
        "-e",
        pattern,
        str(root),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
    except Exception:
        return []
    if proc.returncode not in (0, 1):
        return []
    out: List[Tuple[str, str, float]] = []
    for line in proc.stdout.splitlines():
        if '"type":"match"' not in line:
            continue
        pm = re.search(r'"path":\{"text":"([^"]+)"\}', line)
        lm = re.search(r'"text":"([^"]+)"', line)
        path = pm.group(1) if pm else ""
        snippet = lm.group(1) if lm else ""
        if not path:
            continue
        ext = Path(path).suffix.lower()
        if ext and ext not in TEXT_EXTENSIONS:
            continue
        out.append((path, snippet, 0.7))
        if len(out) >= limit:
            break
    return out


def _docs_catalog_candidates(cwd: Path, terms: List[str], limit: int) -> List[Tuple[str, str, float]]:
    docs_dir = cwd / "docs"
    if not docs_dir.exists():
        return []
    out: List[Tuple[str, str, float]] = []
    filtered_terms = [t for t in terms if len(t) >= 3 and t not in _STOP_TOKENS]
    min_hits = 2 if len(filtered_terms) >= 4 else 1
    for p in docs_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        p_l = p.as_posix().lower()
        hits = [t for t in filtered_terms if t in p_l]
        if len(hits) < min_hits:
            continue
        score = 0.45 + min(0.45, len(hits) * 0.08)
        out.append((str(p), ",".join(hits[:5]) or p.name, score))
    out.sort(key=lambda x: x[2], reverse=True)
    return out[:limit]


def _query_prefers_docs(query: str, terms: List[str]) -> bool:
    q = (query or "").lower()
    if any(t in q for t in ("док", "doc", "docs", "readme", "markdown", "marker", "phase", "фаз", "отчет", "report")):
        return True
    return any(t in _DOC_PREF_TOKENS for t in terms)


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(float(a[i]) * float(b[i]) for i in range(n))
    na = sum(float(a[i]) * float(a[i]) for i in range(n)) ** 0.5
    nb = sum(float(b[i]) * float(b[i]) for i in range(n)) ** 0.5
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(dot / (na * nb))


def _jepa_rescore_rows(rows: List[Dict[str, Any]], query: str, limit: int) -> List[Dict[str, Any]]:
    if not rows:
        return rows
    try:
        from src.services.mcc_jepa_adapter import embed_texts_for_overlay

        texts = [query]
        for r in rows[: max(limit * 4, 120)]:
            texts.append(f"{Path(str(r.get('path',''))).name} {r.get('path','')} {r.get('snippet','')[:180]}")
        jr = embed_texts_for_overlay(texts=texts, target_dim=128)
        vectors = getattr(jr, "vectors", []) or []
        if len(vectors) != len(texts):
            logger.info(
                "[MARKER_157.JEPA.FILE] skipped reason=vector_mismatch vectors=%d texts=%d",
                len(vectors),
                len(texts),
            )
            return rows
        qv = vectors[0]
        rescored: List[Dict[str, Any]] = []
        for idx, r in enumerate(rows[: max(limit * 4, 120)], start=1):
            js = max(0.0, _cosine(qv, vectors[idx]))
            nr = dict(r)
            nr["score"] = round(float(nr.get("score", 0.0)) + (0.35 * js), 4)
            nr["jepa_score"] = round(js, 6)
            rescored.append(nr)
        rescored.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
        logger.info(
            "[MARKER_157.JEPA.FILE] applied query='%s' rows=%d provider_mode=%s top_jepa=%.4f",
            query[:80],
            len(rescored),
            getattr(jr, "provider_mode", "unknown"),
            float(rescored[0].get("jepa_score", 0.0)) if rescored else 0.0,
        )
        return rescored + rows[max(limit * 4, 120):]
    except Exception as e:
        logger.warning("[MARKER_157.JEPA.FILE] failed error=%s", str(e)[:200])
        return rows


def _rerank_items(items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    cwd = Path.cwd().resolve().as_posix()
    parent = Path.cwd().resolve().parent.as_posix()
    home = Path.home().resolve().as_posix()
    docs = str(Path.home().resolve() / "Documents")
    ql = query.lower().strip()
    q_stem = Path(query).stem.lower().strip()
    terms = _expand_query_terms(query)
    descriptive = _is_descriptive_query(query)
    core_terms = [t for t in terms if t not in {"docs", "marker", "phase", "ph", "file", "doc"}]
    q_has_abbrev = any(
        t.startswith("аббрев") or t.startswith("абрев") or "abbreviat" in t or t == "abbr"
        for t in terms
    ) or ("аббрев" in ql or "абрев" in ql)
    q_has_memory = any("памят" in t or t in {"memory", "cam", "arc", "elision", "engram"} for t in terms) or ("памят" in ql)
    q_has_runtime = any(t in {"runtime", "map", "157", "phase", "marker"} or "фаз" in t for t in terms) or ("runtime" in ql)
    q_has_matrix = any("матриц" in t or t in {"matrix", "input", "inputs", "scanner", "contract"} for t in terms) or ("матриц" in ql or "инпут" in ql)
    q_has_stream = any("стрим" in t or t in {"stream", "streaming", "grok"} for t in terms) or ("стрим" in ql or "grok" in ql)
    q_targets_tests = any(t in ql for t in ("test", "tests", "pytest", "fixture", "mock", "тест"))

    ranked: List[Dict[str, Any]] = []
    for item in items:
        p = str(item.get("path", "")).replace("\\", "/")
        p_l = p.lower()
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
        else:
            term_hits = sum(1 for t in terms if len(t) >= 3 and (t in base or t in p.lower()))
            s += min(0.25, term_hits * 0.04)

        if descriptive:
            strong_hits = sum(1 for t in core_terms if len(t) >= 4 and t in p_l)
            s += min(1.0, strong_hits * 0.12)

            # High-value concept combos for descriptive doc retrieval.
            if q_has_abbrev and q_has_memory and "abbreviat" in p_l and "memory" in p_l:
                s += 1.2
            if q_has_abbrev and "abbreviat" in p_l:
                s += 0.8
            if q_has_matrix and "input" in p_l and "matrix" in p_l:
                s += 1.2
            if q_has_runtime and "runtime" in p_l and "map" in p_l and ("157" in p_l or "phase_157" in p_l):
                s += 1.2
            if q_has_memory and (not q_has_abbrev) and "memory" in p_l and ("integration" in p_l or "systems_summary" in p_l):
                s += 1.0
            if q_has_stream and "stream" in p_l and "grok" in p_l:
                s += 1.0

        # Prefer workspace/project locations.
        if p.startswith(cwd):
            s += 0.35
        elif p.startswith(parent):
            s += 0.22
        elif p.startswith(docs):
            s += 0.1
        elif p.startswith(home):
            s += 0.04
        if descriptive and not p.startswith(cwd):
            s -= 0.35

        # De-prioritize noisy system caches/config mirrors.
        if "/Library/" in p:
            s -= 0.4
        if "/.Trash/" in p:
            s -= 0.5
        if "/tests/" in p:
            s -= 0.25
        if not q_targets_tests and any(marker in p for marker in _TEST_NOISE_MARKERS):
            s -= 0.55 if descriptive else 0.3
        if "/docs/" in p:
            s += 0.25 if descriptive else 0.05

        item["score"] = round(s, 4)
        ranked.append(item)

    ranked.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    return ranked


def search_files(
    query: str,
    limit: int = 20,
    mode: str = "keyword",
    scope_roots: List[str] | None = None,
) -> Dict[str, Any]:
    started = time.time()
    q = (query or "").strip()
    if len(q) < 2:
        return {"success": False, "error": "Query too short (min 2 characters)", "results": [], "count": 0, "took_ms": 0}

    safe_limit = max(1, min(int(limit or 20), 100))
    provider = _detect_provider()
    if scope_roots:
        # MARKER_165.MCC.CONTEXT_SEARCH.SCOPE_GUARD.V1
        # MCC scoped search passes explicit roots to avoid global filesystem scans.
        roots = []
        seen = set()
        for raw in scope_roots:
            try:
                p = Path(str(raw)).expanduser().resolve()
            except Exception:
                continue
            key = p.as_posix()
            if key in seen:
                continue
            seen.add(key)
            if p.exists() and p.is_dir():
                roots.append(p)
    else:
        roots = _allowed_search_roots(provider)
    cwd = Path.cwd().resolve()
    walk_fallback_roots = {cwd.as_posix(), cwd.parent.as_posix()}

    merged: List[Tuple[str, str, float]] = []
    ql = q.lower()
    descriptive = _is_descriptive_query(q)
    expanded_terms = _expand_query_terms(q)
    prefer_docs = _query_prefers_docs(q, expanded_terms)
    if descriptive:
        focused = []
        for candidate in [cwd / "docs", cwd / "src", cwd / "data", cwd, cwd.parent]:
            if candidate.exists() and candidate.is_dir():
                focused.append(candidate)
        # Keep unique order
        seen_roots = set()
        narrowed = []
        for r in focused:
            key = r.as_posix()
            if key in seen_roots:
                continue
            seen_roots.add(key)
            narrowed.append(r)
        if narrowed:
            roots = narrowed
        # Add lightweight docs seed with term-filtering to recover key docs without flooding noise.
        docs_seed_limit = max(60, min(240, safe_limit * 8))
        merged.extend(_docs_catalog_candidates(cwd, expanded_terms, docs_seed_limit))
    for idx, root in enumerate(roots):
        # On macOS with Spotlight provider, keep full filesystem root as fallback.
        # If we already have enough hits from focused roots, skip expensive "/".
        if provider == "mdfind" and root == Path("/") and len(merged) >= safe_limit:
            continue
        if descriptive and provider == "mdfind" and root == Path("/"):
            continue

        if mode == "filename":
            if descriptive:
                merged.extend(_name_search_walk_terms(root, expanded_terms, safe_limit))
            else:
                if provider == "mdfind":
                    root_hits = _name_search_mdfind(root, q, safe_limit)
                    if not root_hits:
                        root_hits = _name_search_find(root, q, safe_limit)
                    if not root_hits and root.as_posix() in walk_fallback_roots:
                        root_hits = _name_search_walk(root, ql, safe_limit)
                    merged.extend(root_hits)
                else:
                    merged.extend(_name_search_walk(root, ql, safe_limit))
        else:
            # keyword mode: filename + content
            if descriptive:
                merged.extend(_name_search_walk_terms(root, expanded_terms, safe_limit))
            else:
                if provider == "mdfind":
                    root_hits = _name_search_mdfind(root, q, safe_limit)
                    if not root_hits:
                        root_hits = _name_search_find(root, q, safe_limit)
                    if not root_hits and root.as_posix() in walk_fallback_roots:
                        root_hits = _name_search_walk(root, ql, safe_limit)
                    merged.extend(root_hits)
                else:
                    merged.extend(_name_search_walk(root, ql, safe_limit))
            # Avoid worst-case scans over full filesystem for content search.
            if not (root == Path("/") and provider == "mdfind"):
                if descriptive:
                    merged.extend(_content_search_rg_terms(root, expanded_terms, safe_limit))
                else:
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

    rows = _rerank_items(list(by_path.values()), q)
    if descriptive:
        rows = _jepa_rescore_rows(rows, q, safe_limit)
    rows = rows[:safe_limit]
    return {
        "success": True,
        "results": rows,
        "count": len(rows),
        "mode": "filename" if mode == "filename" else "keyword",
        "intent": "descriptive" if descriptive else "name_like",
        "expanded_terms": expanded_terms[:10],
        "active_provider": provider,
        "roots_used": [r.as_posix() for r in roots],
        "took_ms": int((time.time() - started) * 1000),
    }
