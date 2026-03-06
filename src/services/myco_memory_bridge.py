"""
MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1
MARKER_162.P3.MYCO.README_SCAN_PIPELINE.V1
MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1
MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1
MARKER_162.P3.MYCO.NO_UI_MEMORY_SURFACE.V1

Hidden MYCO memory bridge:
- internal docs/readme indexing via triple-write
- ENGRAM user payload extraction
- recent task snapshot across MCC projects
- lightweight local fastpath metadata for MYCO quick answers
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.memory.engram_user_memory import get_engram_user_memory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "myco_hidden_index_manifest.json"

HIDDEN_SOURCE_PATHS = (
    "README.md",
    "src/memory/README.md",
    "src/orchestration/README.md",
    "client/src/components/mcc/README.md",
    "docs/162_ph_MCC_MYCO_HELPER",
    "docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md",
    "docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md",
)


@dataclass
class HiddenIndexStats:
    indexed_files: int = 0
    indexed_chunks: int = 0
    errors: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "indexed_files": int(self.indexed_files),
            "indexed_chunks": int(self.indexed_chunks),
            "errors": int(self.errors),
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iter_source_files(project_root: Path) -> Iterable[Path]:
    seen: set[str] = set()
    for rel in HIDDEN_SOURCE_PATHS:
        target = (project_root / rel).resolve()
        if not str(target).startswith(str(project_root.resolve())):
            continue
        if target.is_file():
            key = str(target)
            if key not in seen:
                seen.add(key)
                yield target
            continue
        if target.is_dir():
            for path in sorted(target.rglob("*.md")):
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                yield path.resolve()


def _chunk_text(text: str, max_chars: int = 1400) -> List[str]:
    raw = str(text or "").replace("\r\n", "\n")
    if not raw.strip():
        return []
    parts = [p.strip() for p in raw.split("\n\n") if p.strip()]
    chunks: List[str] = []
    buf = ""
    for p in parts:
        candidate = p if not buf else f"{buf}\n\n{p}"
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
            buf = ""
        if len(p) <= max_chars:
            buf = p
            continue
        start = 0
        while start < len(p):
            chunk = p[start : start + max_chars].strip()
            if chunk:
                chunks.append(chunk)
            start += max_chars
    if buf:
        chunks.append(buf)
    return chunks


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def reindex_hidden_instruction_memory(
    *,
    project_root: Optional[str] = None,
    max_files: int = 240,
    max_chunks: int = 2400,
) -> Dict[str, Any]:
    """
    Hidden index ingest for MYCO instruction corpus.
    """
    root = Path(project_root).resolve() if project_root else PROJECT_ROOT
    stats = HiddenIndexStats()
    chunk_budget = max(1, int(max_chunks))
    file_budget = max(1, int(max_files))

    source_files = list(_iter_source_files(root))[:file_budget]
    manifest_sources: List[Dict[str, Any]] = []
    try:
        from src.orchestration.triple_write_manager import get_triple_write_manager

        tw = get_triple_write_manager()
    except Exception:
        tw = None

    for src in source_files:
        rel = str(src.relative_to(root))
        raw = _read_text(src)
        chunks = _chunk_text(raw)
        if not chunks:
            continue
        stats.indexed_files += 1
        mtime = 0.0
        try:
            mtime = src.stat().st_mtime
        except Exception:
            mtime = 0.0

        indexed_here = 0
        for idx, chunk in enumerate(chunks):
            if stats.indexed_chunks >= chunk_budget:
                break
            chunk_path = f"internal/myco_hidden/{rel}#chunk-{idx+1:04d}"
            if tw is not None:
                try:
                    emb = tw.get_embedding(chunk[:2000])
                    result = tw.write_file(
                        file_path=chunk_path,
                        content=chunk,
                        embedding=emb,
                        metadata={
                            "hidden_index": True,
                            "index_scope": "myco_instructions",
                            "source_path": rel,
                            "chunk_index": idx + 1,
                            "chunk_count": len(chunks),
                            "mtime": mtime,
                            "marker": "MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1",
                        },
                    )
                    if not any(bool(v) for v in (result or {}).values()):
                        stats.errors += 1
                except Exception:
                    stats.errors += 1
            indexed_here += 1
            stats.indexed_chunks += 1
        manifest_sources.append(
            {
                "path": rel,
                "mtime": mtime,
                "chunks_indexed": indexed_here,
            }
        )
        if stats.indexed_chunks >= chunk_budget:
            break

    manifest = {
        "marker": "MARKER_162.P3.MYCO.README_SCAN_PIPELINE.V1",
        "updated_at": _utc_now_iso(),
        "project_root": str(root),
        "source_count": len(manifest_sources),
        "sources": manifest_sources,
        "stats": stats.to_dict(),
        "hidden": True,
        "ui_surface": "none",
    }
    _save_json(MANIFEST_PATH, manifest)
    return manifest


def _extract_user_name(preferences: Dict[str, Any], fallback_user_id: str) -> str:
    if not isinstance(preferences, dict):
        return fallback_user_id
    candidates = (
        preferences.get("user_name"),
        preferences.get("name"),
        ((preferences.get("communication_style") or {}).get("user_name") if isinstance(preferences.get("communication_style"), dict) else None),
        ((preferences.get("project_highlights") or {}).get("user_name") if isinstance(preferences.get("project_highlights"), dict) else None),
    )
    for c in candidates:
        s = str(c or "").strip()
        if s:
            return s
    return fallback_user_id


def _load_task_board() -> Dict[str, Any]:
    return _load_json(DATA_DIR / "task_board.json")


def _task_sort_key(task: Dict[str, Any]) -> Tuple[str, str]:
    return (
        str(task.get("completed_at") or task.get("started_at") or task.get("created_at") or ""),
        str(task.get("id") or ""),
    )


def _recent_tasks_by_project(limit_per_project: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    from src.services.mcc_project_registry import list_projects, load_session_for_project

    tasks_payload = _load_task_board()
    tasks_map = dict((tasks_payload.get("tasks") or {})) if isinstance(tasks_payload.get("tasks"), dict) else {}
    rows = list_projects().get("projects") or []
    out: Dict[str, List[Dict[str, Any]]] = {}

    global_pool: List[Dict[str, Any]] = []
    for t in tasks_map.values():
        if isinstance(t, dict):
            global_pool.append(t)
    global_pool.sort(key=_task_sort_key, reverse=True)

    for row in rows:
        project_id = str((row or {}).get("project_id") or "").strip()
        if not project_id:
            continue
        picked: List[Dict[str, Any]] = []
        try:
            state = load_session_for_project(project_id)
            current_task = str(getattr(state, "task_id", "") or "").strip()
            if current_task and current_task in tasks_map and isinstance(tasks_map[current_task], dict):
                t = tasks_map[current_task]
                picked.append(
                    {
                        "task_id": str(t.get("id") or current_task),
                        "title": str(t.get("title") or ""),
                        "status": str(t.get("status") or ""),
                    }
                )
        except Exception:
            pass

        for t in global_pool:
            if len(picked) >= max(1, int(limit_per_project)):
                break
            tid = str(t.get("id") or "").strip()
            if not tid or any(str(x.get("task_id")) == tid for x in picked):
                continue
            picked.append(
                {
                    "task_id": tid,
                    "title": str(t.get("title") or ""),
                    "status": str(t.get("status") or ""),
                }
            )
        out[project_id] = picked
    return out


def build_myco_memory_payload(
    *,
    user_id: str = "danila",
    active_project_id: str = "",
    focus: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build MYCO hidden memory payload (backend/runtime only).
    """
    engram = get_engram_user_memory()
    prefs = engram.get_all_preferences(user_id) or {}
    manifest = _load_json(MANIFEST_PATH)
    recent = _recent_tasks_by_project(limit_per_project=3)

    jepa_enabled = os.getenv("VETKA_CONTEXT_PACKER_JEPA_ENABLE", "true").lower() == "true"
    fastpath = {
        "mode": "local_jepa_gemma_first",
        "jepa_enabled": bool(jepa_enabled),
        "gemma_hint": "local",
        "api_escalation": "low_confidence_only",
        "marker": "MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1",
    }

    return {
        "user_id": str(user_id or "danila"),
        "user_name": _extract_user_name(prefs, str(user_id or "danila")),
        "active_project_id": str(active_project_id or ""),
        "focus": dict(focus or {}),
        "recent_tasks_by_project": recent,
        "engram_preferences": prefs,
        "hidden_index": {
            "updated_at": str(manifest.get("updated_at") or ""),
            "source_count": int(manifest.get("source_count") or 0),
            "stats": dict(manifest.get("stats") or {}),
            "hidden": True,
            "ui_surface": "none",
            "marker": "MARKER_162.P3.MYCO.NO_UI_MEMORY_SURFACE.V1",
        },
        "fastpath": fastpath,
        "marker": "MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1",
    }

