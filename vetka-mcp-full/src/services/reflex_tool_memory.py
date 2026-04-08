"""
REFLEX tool memory helpers.

Stores lightweight reminders about scripts, tools, and skills that should be
remembered by REFLEX and surfaced later when relevant.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_PATH = PROJECT_ROOT / "data" / "reflex" / "remembered_tools.json"
CATALOG_PATH = PROJECT_ROOT / "data" / "reflex" / "tool_catalog.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RememberedToolEntry:
    tool_name: str
    entry_type: str
    path: str
    tool_id: str
    catalog_source: str
    origin: str
    notes: str
    intent_tags: List[str]
    trigger_hint: str
    aliases: List[str]
    active: bool
    created_at: str
    updated_at: str


def load_reflex_tool_memory(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = Path(path or MEMORY_PATH)
    if not target.exists():
        return []
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("tools", []) if isinstance(data, dict) else []
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    except Exception:
        return []
    return []


def save_reflex_tool_memory(rows: List[Dict[str, Any]], path: Optional[Path] = None) -> Path:
    target = Path(path or MEMORY_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "updated_at": _utc_now_iso(),
        "tools": rows,
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return target


def _resolve_path_exists(path_value: str) -> bool:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate.exists()
    return (PROJECT_ROOT / candidate).exists()


def _load_catalog_rows(catalog_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = Path(catalog_path or CATALOG_PATH)
    if not target.exists():
        return []
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("tools", []) if isinstance(data, dict) else []
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    except Exception:
        return []
    return []


def resolve_reflex_tool_reference(
    *,
    tool_name: str = "",
    path: str = "",
    tool_id: str = "",
    catalog_path: Optional[Path] = None,
) -> Dict[str, Any]:
    tool_name_value = str(tool_name or "").strip()
    path_value = str(path or "").strip()
    tool_id_value = str(tool_id or "").strip()
    catalog_rows = _load_catalog_rows(catalog_path)

    matched = None
    canonical_id = tool_id_value
    if tool_id_value:
        matched = next(
            (row for row in catalog_rows if str(row.get("tool_id", "")).strip() == tool_id_value),
            None,
        )
    if matched is None and tool_name_value:
        matched = next(
            (
                row
                for row in catalog_rows
                if str(row.get("tool_id", "")).strip() == tool_name_value
            ),
            None,
        )
    if matched is not None:
        canonical_id = str(matched.get("tool_id", "")).strip()

    path_exists = _resolve_path_exists(path_value) if path_value else False
    stale_reason = ""
    if canonical_id and matched is None:
        stale_reason = "catalog_tool_missing"
    elif path_value and not path_exists:
        stale_reason = "path_missing"

    return {
        "tool_id": canonical_id,
        "catalog_source": str((matched or {}).get("source", "")).strip(),
        "origin": "catalog" if matched is not None else "overlay_only",
        "path_exists": path_exists,
        "stale": bool(stale_reason),
        "stale_reason": stale_reason,
        "matched_catalog_entry": matched,
    }


def remember_reflex_tool(
    *,
    tool_name: str,
    entry_type: str,
    path: str,
    tool_id: str = "",
    notes: str = "",
    intent_tags: Optional[List[str]] = None,
    trigger_hint: str = "",
    aliases: Optional[List[str]] = None,
    active: bool = True,
    memory_path: Optional[Path] = None,
    catalog_path: Optional[Path] = None,
) -> Dict[str, Any]:
    target = Path(memory_path or MEMORY_PATH)
    tool_name = str(tool_name or "").strip()
    entry_type = str(entry_type or "").strip()
    path_value = str(path or "").strip()
    if not tool_name:
      raise ValueError("tool_name is required")
    if not entry_type:
      raise ValueError("entry_type is required")
    if not path_value:
      raise ValueError("path is required")

    tags = [str(tag).strip() for tag in (intent_tags or []) if str(tag).strip()]
    aliases_value = [str(alias).strip() for alias in (aliases or []) if str(alias).strip()]
    resolved = resolve_reflex_tool_reference(
        tool_name=tool_name,
        path=path_value,
        tool_id=tool_id,
        catalog_path=catalog_path,
    )

    rows = load_reflex_tool_memory(target)
    now = _utc_now_iso()
    matched_index = None
    for idx, row in enumerate(rows):
        if (
            str(row.get("tool_name", "")).strip() == tool_name
            or str(row.get("path", "")).strip() == path_value
            or (
                resolved["tool_id"]
                and str(row.get("tool_id", "")).strip() == resolved["tool_id"]
            )
        ):
            matched_index = idx
            break

    if matched_index is None:
        entry = RememberedToolEntry(
            tool_name=tool_name,
            entry_type=entry_type,
            path=path_value,
            tool_id=resolved["tool_id"],
            catalog_source=resolved["catalog_source"],
            origin=resolved["origin"],
            notes=str(notes or "").strip(),
            intent_tags=tags,
            trigger_hint=str(trigger_hint or "").strip(),
            aliases=aliases_value,
            active=bool(active),
            created_at=now,
            updated_at=now,
        )
        rows.append(asdict(entry))
        action = "created"
        result_row = rows[-1]
    else:
        row = dict(rows[matched_index])
        row.update(
            {
                "tool_name": tool_name,
                "entry_type": entry_type,
                "path": path_value,
                "tool_id": resolved["tool_id"],
                "catalog_source": resolved["catalog_source"],
                "origin": resolved["origin"],
                "notes": str(notes or row.get("notes", "")).strip(),
                "intent_tags": tags or list(row.get("intent_tags", []) or []),
                "trigger_hint": str(trigger_hint or row.get("trigger_hint", "")).strip(),
                "aliases": aliases_value or list(row.get("aliases", []) or []),
                "active": bool(active),
                "updated_at": now,
            }
        )
        rows[matched_index] = row
        action = "updated"
        result_row = row

    save_reflex_tool_memory(rows, target)
    return {
        "action": action,
        "entry": result_row,
        "count": len(rows),
        "memory_path": str(target),
        "resolved": resolved,
    }


def list_reflex_tool_memory(
    *,
    entry_type: str = "",
    query: str = "",
    only_active: bool = True,
    exclude_stale: bool = True,
    memory_path: Optional[Path] = None,
    catalog_path: Optional[Path] = None,
) -> Dict[str, Any]:
    rows = load_reflex_tool_memory(memory_path)
    entry_type_value = str(entry_type or "").strip().lower()
    query_value = str(query or "").strip().lower()
    filtered = []
    for row in rows:
        if only_active and not bool(row.get("active", True)):
            continue
        if entry_type_value and str(row.get("entry_type", "")).strip().lower() != entry_type_value:
            continue
        resolved = resolve_reflex_tool_reference(
            tool_name=str(row.get("tool_name", "")),
            path=str(row.get("path", "")),
            tool_id=str(row.get("tool_id", "")),
            catalog_path=catalog_path,
        )
        if exclude_stale and resolved["stale"]:
            continue
        haystack = " ".join(
            [
                str(row.get("tool_name", "")),
                str(row.get("tool_id", "")),
                str(row.get("path", "")),
                str(row.get("notes", "")),
                " ".join(row.get("intent_tags", []) or []),
                " ".join(row.get("aliases", []) or []),
                str(row.get("trigger_hint", "")),
            ]
        ).lower()
        if query_value and query_value not in haystack:
            continue
        merged = dict(row)
        merged.update(
            {
                "tool_id": resolved["tool_id"] or str(row.get("tool_id", "")),
                "catalog_source": resolved["catalog_source"] or str(row.get("catalog_source", "")),
                "origin": resolved["origin"] or str(row.get("origin", "overlay_only")),
                "path_exists": resolved["path_exists"],
                "stale": resolved["stale"],
                "stale_reason": resolved["stale_reason"],
            }
        )
        filtered.append(merged)
    return {
        "count": len(filtered),
        "tools": filtered,
        "memory_path": str(memory_path or MEMORY_PATH),
    }
