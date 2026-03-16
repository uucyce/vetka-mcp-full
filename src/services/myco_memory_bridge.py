"""
MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1
MARKER_162.P3.MYCO.README_SCAN_PIPELINE.V1
MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1
MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1
MARKER_162.P3.MYCO.NO_UI_MEMORY_SURFACE.V1

Hidden MYCO memory bridge:
- internal docs/readme indexing via triple-write
- AURA user payload extraction
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
import re

from src.memory.aura_store import get_aura_store

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
GLOSSARY_PATH = PROJECT_ROOT / "docs" / "besedii_google_drive_docs" / "VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md"


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


def _extract_glossary_aliases() -> Dict[str, List[str]]:
    """
    MARKER_162.P3.P4.MYCO.GLOSSARY_ALIAS_EXPANSION.V1
    Build bounded alias map from canonical memory glossary.
    """
    raw = _read_text(GLOSSARY_PATH)
    aliases: Dict[str, List[str]] = {}
    if not raw.strip():
        return aliases
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue
        left, right = line[2:].split(":", 1)
        key = left.strip()
        val = right.strip()
        if not key:
            continue
        norm_key = key.lower()
        bucket = aliases.setdefault(norm_key, [])
        long_name = val.split("(")[0].strip()
        if long_name and long_name.lower() != norm_key:
            bucket.append(long_name)
        if val:
            # Keep one short phrase variant for lexical fallback.
            bucket.append(val[:96].strip())
    for k, vals in list(aliases.items()):
        dedup: List[str] = []
        seen = set()
        for v in vals:
            t = str(v or "").strip()
            if not t:
                continue
            lk = t.lower()
            if lk in seen:
                continue
            seen.add(lk)
            dedup.append(t)
        aliases[k] = dedup[:4]
    return aliases


def expand_myco_query_aliases(query: str) -> Dict[str, Any]:
    """
    MARKER_162.P3.P4.MYCO.GLOSSARY_ALIAS_EXPANSION.V1
    Expand query with glossary aliases for hidden retrieval.
    """
    base = str(query or "").strip()
    if not base:
        return {"query": "", "expanded_queries": [], "aliases_used": []}
    aliases = _extract_glossary_aliases()
    expanded = [base]
    aliases_used: List[str] = []
    lower = base.lower()
    for key, variants in aliases.items():
        trigger = re.compile(rf"\b{re.escape(key)}\b", re.IGNORECASE)
        if trigger.search(lower):
            aliases_used.append(key)
            for variant in variants:
                candidate = trigger.sub(variant, base)
                candidate = candidate.strip()
                if candidate and candidate not in expanded:
                    expanded.append(candidate)
    return {
        "query": base,
        "expanded_queries": expanded[:5],
        "aliases_used": aliases_used[:8],
    }


def _lexical_hidden_fallback(
    query_terms: List[str],
    *,
    top_k: int,
    source_files: List[Path],
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    term_set = {t for t in query_terms if t}
    if not term_set:
        return []
    for path in source_files[:220]:
        raw = _read_text(path)
        if not raw:
            continue
        lower = raw.lower()
        matched = [t for t in term_set if t in lower]
        if not matched:
            continue
        score = float(len(matched)) / float(max(1, len(term_set)))
        first_term = matched[0]
        idx = lower.find(first_term)
        start = max(0, idx - 80)
        end = min(len(raw), idx + 220)
        snippet = " ".join(raw[start:end].split())
        hits.append(
            {
                "source_path": str(path.relative_to(PROJECT_ROOT)),
                "score": round(score, 3),
                "snippet": snippet[:220],
                "method": "lexical_fallback",
            }
        )
    hits.sort(key=lambda h: float(h.get("score", 0.0)), reverse=True)
    return hits[: max(1, int(top_k))]


def retrieve_myco_hidden_context(
    *,
    query: str,
    focus: Optional[Dict[str, Any]] = None,
    top_k: int = 3,
    min_score: float = 0.22,
) -> Dict[str, Any]:
    """
    MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1
    MARKER_162.P3.P4.MYCO.RETRIEVAL_QUALITY_GATE.V1
    Retrieve compact hidden instruction snippets for MYCO quick path.
    """
    alias_pack = expand_myco_query_aliases(query)
    expanded_queries = list(alias_pack.get("expanded_queries") or [])
    q = str(alias_pack.get("query") or "").strip()
    if not q:
        return {
            "query": q,
            "items": [],
            "method": "none",
            "aliases_used": [],
            "marker": "MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1",
        }

    # Add focused label as optional retrieval hint.
    focus_obj = dict(focus or {})
    focus_label = str(
        focus_obj.get("label")
        or focus_obj.get("task_id")
        or focus_obj.get("taskId")
        or focus_obj.get("node_id")
        or focus_obj.get("nodeId")
        or ""
    ).strip()
    if focus_label and focus_label not in expanded_queries:
        expanded_queries.append(f"{q} {focus_label}")

    collected: List[Dict[str, Any]] = []
    try:
        from src.orchestration.triple_write_manager import get_triple_write_manager
        tw = get_triple_write_manager()
        if tw and getattr(tw, "qdrant_client", None):
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            query_filter = Filter(
                must=[
                    FieldCondition(key="hidden_index", match=MatchValue(value=True)),
                    FieldCondition(key="index_scope", match=MatchValue(value="myco_instructions")),
                ]
            )
            for eq in expanded_queries[:4]:
                emb = tw.get_embedding(eq[:2000])
                if not emb:
                    continue
                limit = max(4, int(top_k) * 2)
                if hasattr(tw.qdrant_client, "query_points"):
                    qp = tw.qdrant_client.query_points(
                        collection_name="vetka_elisya",
                        query=emb,
                        query_filter=query_filter,
                        limit=limit,
                        with_payload=True,
                        with_vectors=False,
                    )
                    rows = list(getattr(qp, "points", None) or [])
                else:
                    rows = tw.qdrant_client.search(
                        collection_name="vetka_elisya",
                        query_vector=emb,
                        query_filter=query_filter,
                        limit=limit,
                        with_payload=True,
                        with_vectors=False,
                    )
                for row in rows or []:
                    payload = getattr(row, "payload", {}) or {}
                    score = float(getattr(row, "score", 0.0) or 0.0)
                    if score < float(min_score):
                        continue
                    source_path = str(payload.get("source_path") or payload.get("file_path") or "").strip()
                    snippet = str(payload.get("content") or payload.get("text") or "").strip()
                    if not snippet:
                        snippet = str(payload.get("file_name") or source_path or "")
                    collected.append(
                        {
                            "source_path": source_path,
                            "score": round(score, 3),
                            "snippet": " ".join(snippet.split())[:220],
                            "method": "qdrant_semantic",
                        }
                    )
    except Exception:
        collected = []

    if collected:
        dedup: List[Dict[str, Any]] = []
        seen = set()
        for row in sorted(collected, key=lambda r: float(r.get("score", 0.0)), reverse=True):
            key = (str(row.get("source_path") or ""), str(row.get("snippet") or "")[:80])
            if key in seen:
                continue
            seen.add(key)
            dedup.append(row)
            if len(dedup) >= max(1, int(top_k)):
                break
        return {
            "query": q,
            "items": dedup,
            "method": "qdrant_semantic",
            "aliases_used": list(alias_pack.get("aliases_used") or []),
            "marker": "MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1",
        }

    # Deterministic lexical fallback (quality-gated via normalized overlap score).
    source_files = list(_iter_source_files(PROJECT_ROOT))
    query_terms = re.findall(r"[a-zA-Z0-9_]{3,}", " ".join(expanded_queries).lower())
    lexical = _lexical_hidden_fallback(query_terms, top_k=max(1, int(top_k)), source_files=source_files)
    return {
        "query": q,
        "items": lexical,
        "method": "lexical_fallback" if lexical else "none",
        "aliases_used": list(alias_pack.get("aliases_used") or []),
        "marker": "MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1",
    }


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
        ((preferences.get("tool_usage_patterns") or {}).get("shortcuts", {}).get("user_name") if isinstance(preferences.get("tool_usage_patterns"), dict) else None),
        ((preferences.get("tool_usage_patterns") or {}).get("patterns", {}).get("user_name") if isinstance(preferences.get("tool_usage_patterns"), dict) else None),
    )
    for c in candidates:
        s = str(c or "").strip()
        if s:
            return s
    return fallback_user_id


def _load_task_board() -> Dict[str, Any]:
    return _load_json(DATA_DIR / "task_board.json")


def _load_project_digest() -> Dict[str, Any]:
    return _load_json(DATA_DIR / "project_digest.json")


def _digest_snapshot(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # MARKER_171.P1.MYCO.DIGEST_NORMALIZE.V1
    # Keep digest compact but structured so MYCO/MCC don't receive stringified dict blobs.
    data = dict(payload or _load_project_digest())
    summary_raw = data.get("summary")
    phase_raw = data.get("current_phase") or data.get("phase")
    status_raw = data.get("status")
    system_status = data.get("system_status") if isinstance(data.get("system_status"), dict) else {}

    if isinstance(summary_raw, dict):
        summary = str(
            summary_raw.get("headline")
            or ((summary_raw.get("key_achievements") or [""])[0])
            or ""
        ).strip()
    else:
        summary = str(summary_raw or system_status.get("summary") or "").strip()

    phase_number = ""
    phase_subphase = ""
    phase_name = ""
    phase_status = ""
    if isinstance(phase_raw, dict):
        phase_number = str(phase_raw.get("number") or "").strip()
        phase_subphase = str(phase_raw.get("subphase") or "").strip()
        phase_name = str(phase_raw.get("name") or "").strip()
        phase_status = str(phase_raw.get("status") or "").strip()
        phase = ".".join(x for x in (phase_number, phase_subphase) if x)
        if phase_status:
            phase = f"{phase} {phase_status}".strip() if phase else phase_status
    else:
        phase = str(phase_raw or ((data.get("meta") or {}).get("phase") if isinstance(data.get("meta"), dict) else "") or "").strip()

    if isinstance(status_raw, dict):
        status = str(status_raw.get("summary") or "").strip()
    else:
        status = str(status_raw or system_status.get("health") or "").strip()

    return {
        "updated_at": str(data.get("last_updated") or data.get("updated_at") or ""),
        "phase": phase,
        "phase_number": phase_number,
        "phase_subphase": phase_subphase,
        "phase_name": phase_name,
        "phase_status": phase_status,
        "status": status,
        "summary": summary,
    }


def _multitask_stats() -> Dict[str, Any]:
    # MARKER_162.P3.P3.MYCO.MULTITASK_CFG_SNAPSHOT.V1
    # MARKER_171.P1.MYCO.MULTITASK_STATUS_SPLIT.V1
    # Separate failed/cancelled from queued to keep orchestration signal clean.
    payload = _load_task_board()
    tasks = payload.get("tasks") if isinstance(payload.get("tasks"), dict) else {}
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
    total = len(tasks)
    done = 0
    active = 0
    queued = 0
    failed = 0
    protocol_required = 0
    history_entries = 0
    lanes: Dict[str, int] = {}
    latest_closed: Dict[str, str] = {}
    for task in tasks.values():
        if not isinstance(task, dict):
            continue
        status = str(task.get("status") or "").strip().lower()
        if task.get("require_closure_proof"):
            protocol_required += 1
        history = task.get("status_history")
        if isinstance(history, list):
            history_entries += len(history)
        lane = str(task.get("project_lane") or task.get("project_id") or "").strip()
        if lane:
            lanes[lane] = lanes.get(lane, 0) + 1
        if status == "done":
            done += 1
            completed_at = str(task.get("completed_at") or "")
            if completed_at and completed_at >= str(latest_closed.get("completed_at") or ""):
                latest_closed = {
                    "task_id": str(task.get("id") or ""),
                    "closed_by": str(task.get("closed_by") or task.get("assigned_to") or ""),
                    "project_lane": lane,
                    "completed_at": completed_at,
                }
        elif status in {"running", "active", "in_progress", "claimed"}:
            active += 1
        elif status in {"failed", "cancelled"}:
            failed += 1
        else:
            queued += 1
    return {
        "total": total,
        "done": done,
        "active": active,
        "queued": queued,
        "failed": failed,
        "phase": str(meta.get("phase") or ""),
        "max_concurrent": int(settings.get("max_concurrent") or 0),
        "auto_dispatch": bool(settings.get("auto_dispatch", False)),
        "protocol_required": protocol_required,
        "history_entries": history_entries,
        "last_closed_by": str(latest_closed.get("closed_by") or ""),
        "last_closed_task_id": str(latest_closed.get("task_id") or ""),
        "last_closed_lane": str(latest_closed.get("project_lane") or ""),
        "lanes": lanes,
    }


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
            lane = str(t.get("project_id") or t.get("project_lane") or "").strip()
            if not tid or lane != project_id or any(str(x.get("task_id")) == tid for x in picked):
                continue
            picked.append(
                {
                    "task_id": tid,
                    "title": str(t.get("title") or ""),
                    "status": str(t.get("status") or ""),
                }
            )

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
    aura = get_aura_store()
    prefs = aura.get_all_preferences(user_id) or {}
    manifest = _load_json(MANIFEST_PATH)
    recent = _recent_tasks_by_project(limit_per_project=3)
    digest = _load_project_digest()
    multitask = _multitask_stats()
    digest_snapshot = _digest_snapshot(digest)

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
        "orchestration": {
            "multitask": multitask,
            "digest": digest_snapshot,
            "marker": "MARKER_162.P3.P2.MYCO.ORCHESTRATION_SNAPSHOT.V1",
        },
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


def persist_myco_runtime_facts(
    *,
    user_id: str = "danila",
    user_name: str = "",
    active_project_id: str = "",
    focus: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    MARKER_162.P3.P2.MYCO.ENGRAM_PERSIST_RUNTIME_FACTS.V1
    Persist lightweight MYCO runtime facts in AURA-safe fields.
    """
    aura = get_aura_store()
    prefs = aura.get_all_preferences(user_id) or {}
    focus_obj = dict(focus or {})
    recent = _recent_tasks_by_project(limit_per_project=3)
    multi = _multitask_stats()
    digest = _digest_snapshot()

    current_project = str(active_project_id or "")
    focus_label = str(
        focus_obj.get("label")
        or focus_obj.get("task_id")
        or focus_obj.get("taskId")
        or focus_obj.get("node_id")
        or focus_obj.get("nodeId")
        or ""
    ).strip()

    proj = dict(prefs.get("project_highlights") or {})
    tool = dict(prefs.get("tool_usage_patterns") or {})
    temporal = dict(prefs.get("temporal_patterns") or {})

    priorities = list(proj.get("priorities") or [])
    if focus_label and focus_label not in priorities:
        priorities = [focus_label, *priorities][:6]
    if current_project and current_project not in priorities:
        priorities = [current_project, *priorities][:6]
    if not priorities:
        priorities = ["myco", "context"]

    highlights = dict(proj.get("highlights") or {})
    project_tasks = recent.get(current_project) if current_project else []
    project_tasks = project_tasks if isinstance(project_tasks, list) else []
    task_titles = [str(t.get("title") or "").strip() for t in project_tasks if isinstance(t, dict)]
    task_titles = [t for t in task_titles if t]
    if current_project:
        highlights[current_project] = task_titles[:8]

    tool_shortcuts = dict(tool.get("shortcuts") or {})
    tool_patterns = dict(tool.get("patterns") or {})
    if user_name:
        tool_shortcuts["user_name"] = str(user_name).strip()
        tool_patterns["user_name"] = str(user_name).strip()
    if current_project:
        tool_patterns["myco_last_project"] = current_project
    if focus_label:
        tool_patterns["myco_last_focus"] = focus_label
    if digest.get("phase"):
        tool_patterns["myco_last_phase"] = str(digest.get("phase"))

    time_of_day = dict(temporal.get("time_of_day") or {})
    if current_project:
        time_of_day["myco_last_project"] = current_project
    if focus_label:
        time_of_day["myco_last_focus"] = focus_label

    if current_project:
        aura.set_preference(
            user_id,
            "project_highlights",
            "current_project",
            current_project,
            confidence=0.9,
        )
    aura.set_preference(
        user_id,
        "project_highlights",
        "priorities",
        priorities,
        confidence=0.75,
    )
    aura.set_preference(
        user_id,
        "project_highlights",
        "highlights",
        highlights,
        confidence=0.75,
    )
    aura.set_preference(
        user_id,
        "tool_usage_patterns",
        "shortcuts",
        tool_shortcuts,
        confidence=0.7,
    )
    aura.set_preference(
        user_id,
        "tool_usage_patterns",
        "patterns",
        tool_patterns,
        confidence=0.7,
    )
    aura.set_preference(
        user_id,
        "temporal_patterns",
        "time_of_day",
        time_of_day,
        confidence=0.65,
    )
    if multi.get("active", 0) > 0:
        tool_patterns["myco_multitask_active"] = str(int(multi.get("active", 0)))
        aura.set_preference(
            user_id,
            "tool_usage_patterns",
            "patterns",
            tool_patterns,
            confidence=0.72,
        )
    return {
        "ok": True,
        "user_id": str(user_id),
        "project_id": current_project,
        "focus": focus_label,
        "marker": "MARKER_162.P3.P2.MYCO.ENGRAM_PERSIST_RUNTIME_FACTS.V1",
    }
