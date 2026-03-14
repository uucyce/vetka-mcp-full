"""
VETKA MYCO_HELP lightweight retrieval for voice path.

MARKER_163.P3.VETKA_MYCO_HELP_RAG_RETRIEVAL.V1
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

_ROOT = Path(__file__).resolve().parents[2]
_DOCS_DIR = _ROOT / "docs" / "163_ph_myco_VETKA_help"
_RAG_DIR = _DOCS_DIR / "rag"

_ALLOWED_PREFIXES = (
    "MYCO_VETKA_",
    "VETKA_HELP_",
    "PHASE_163_",
)
_EXCLUDED_PARTS = (
    "_RAW_",
    "BUTTON_HINT_CATALOG",
)
_MAX_FILES = 24
_MAX_CHARS_PER_FILE = 24000
_MAX_LINES_PER_FILE = 260

_cache: Dict[str, Any] = {
    "version": None,
    "chunks": [],
}


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9_]{3,}", (text or "").lower())
    return tokens[:256]


def _current_version(files: List[Path]) -> Tuple[Tuple[str, int], ...]:
    out: List[Tuple[str, int]] = []
    for fp in files:
        try:
            out.append((str(fp), int(fp.stat().st_mtime_ns)))
        except Exception:
            out.append((str(fp), 0))
    return tuple(out)


def _iter_help_files() -> List[Path]:
    scan_roots: List[Path] = []
    if _DOCS_DIR.exists():
        scan_roots.append(_DOCS_DIR)
    if _RAG_DIR.exists():
        scan_roots.append(_RAG_DIR)
    if not scan_roots:
        return []

    files: List[Path] = []
    seen: set[str] = set()
    for root in scan_roots:
        for fp in sorted(root.glob("*.md")):
            path_key = str(fp.resolve())
            if path_key in seen:
                continue
            seen.add(path_key)
            name = fp.name
            if not any(name.startswith(p) for p in _ALLOWED_PREFIXES):
                continue
            if any(ex in name for ex in _EXCLUDED_PARTS):
                continue
            files.append(fp)
            if len(files) >= _MAX_FILES:
                return files
    return files


def _load_chunks() -> List[Dict[str, Any]]:
    files = _iter_help_files()
    version = _current_version(files)
    if _cache.get("version") == version and _cache.get("chunks"):
        return _cache["chunks"]

    chunks: List[Dict[str, Any]] = []
    for fp in files:
        try:
            raw = fp.read_text(encoding="utf-8", errors="ignore")[:_MAX_CHARS_PER_FILE]
        except Exception:
            continue
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()][:_MAX_LINES_PER_FILE]
        if not lines:
            continue
        # Build short semantic chunks around headings/bullets.
        buf: List[str] = []
        for ln in lines:
            if ln.startswith("#") and buf:
                txt = " ".join(buf).strip()
                if txt:
                    chunks.append(
                        {
                            "source_path": str(fp.relative_to(_ROOT)),
                            "snippet": txt[:280],
                            "tokens": set(_tokenize(txt)),
                        }
                    )
                buf = [ln.lstrip("# ").strip()]
                continue
            buf.append(ln)
            if len(buf) >= 6:
                txt = " ".join(buf).strip()
                if txt:
                    chunks.append(
                        {
                            "source_path": str(fp.relative_to(_ROOT)),
                            "snippet": txt[:280],
                            "tokens": set(_tokenize(txt)),
                        }
                    )
                buf = []
        if buf:
            txt = " ".join(buf).strip()
            if txt:
                chunks.append(
                    {
                        "source_path": str(fp.relative_to(_ROOT)),
                        "snippet": txt[:280],
                        "tokens": set(_tokenize(txt)),
                    }
                )

    _cache["version"] = version
    _cache["chunks"] = chunks
    return chunks


def retrieve_vetka_myco_help_context(
    *,
    query: str,
    focus: Dict[str, Any] | None = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Lightweight lexical retrieval over Phase-163 MYCO docs.
    Returns structure compatible with existing hidden_retrieval payload.
    """
    chunks = _load_chunks()
    if not chunks:
        return {"items": [], "source": "phase163_docs", "marker": "MARKER_163.P3.VETKA_MYCO_HELP_RAG_RETRIEVAL.V1"}

    q_tokens = set(_tokenize(query))
    if focus:
        for key in ("node_kind", "role", "label", "nav_level", "task_drill_state"):
            val = str(focus.get(key) or focus.get(key.title()) or "").strip()
            if val:
                q_tokens.update(_tokenize(val))
    if not q_tokens:
        return {"items": [], "source": "phase163_docs", "marker": "MARKER_163.P3.VETKA_MYCO_HELP_RAG_RETRIEVAL.V1"}

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for ch in chunks:
        overlap = len(q_tokens & ch["tokens"])
        if overlap <= 0:
            continue
        # mild preference for direct action hints
        snippet = ch.get("snippet", "").lower()
        action_bonus = 0.35 if any(k in snippet for k in ("следующ", "next", "action", "клик", "pin", "artifact")) else 0.0
        source = str(ch.get("source_path", ""))
        source_bonus = 0.0
        if "/rag/" in source or source.startswith("docs/163_ph_myco_VETKA_help/rag/"):
            source_bonus += 0.45
        if "VETKA_HELP_" in source:
            source_bonus += 0.25
        score = float(overlap) + action_bonus + source_bonus
        scored.append((score, ch))

    if not scored:
        return {"items": [], "source": "phase163_docs", "marker": "MARKER_163.P3.VETKA_MYCO_HELP_RAG_RETRIEVAL.V1"}

    scored.sort(key=lambda x: x[0], reverse=True)
    items: List[Dict[str, Any]] = []
    for score, ch in scored[: max(1, int(top_k))]:
        items.append(
            {
                "source_path": ch["source_path"],
                "snippet": ch["snippet"],
                "score": round(float(score), 3),
            }
        )

    return {
        "items": items,
        "source": "phase163_docs",
        "marker": "MARKER_163.P3.VETKA_MYCO_HELP_RAG_RETRIEVAL.V1",
    }
