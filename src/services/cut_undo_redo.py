"""
MARKER_173.1.UNDO_REDO_SERVICE

Undo/Redo service for CUT timeline editing.

Architecture:
- Each undoable action = entry with (label, prev_state_snapshot, ops_applied)
- Undo: restore prev_state snapshot
- Redo: re-apply ops from stored entry
- Pointer model: `pointer` = count of applied entries (0..len(entries))
  - pointer == len(entries) → at head (no redo available)
  - pointer == 0 → all undone
- Persistence: undo_stack.json in cut_runtime/state/
- Max depth: configurable (default 100)
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("cut.undo_redo")

DEFAULT_MAX_DEPTH = 100


@dataclass
class UndoStack:
    """
    Full undo/redo state.

    Pointer model:
      entries = [E0, E1, E2, E3]
      pointer = 4  → all applied, undo_depth=4, redo_depth=0
      pointer = 2  → E0,E1 applied; E2,E3 are redo-able
      pointer = 0  → nothing applied, redo_depth=4
    """

    project_id: str
    timeline_id: str
    max_depth: int = DEFAULT_MAX_DEPTH
    entries: list[dict[str, Any]] = field(default_factory=list)
    pointer: int = 0  # count of applied entries

    @property
    def undo_depth(self) -> int:
        return self.pointer

    @property
    def redo_depth(self) -> int:
        return len(self.entries) - self.pointer

    @property
    def can_undo(self) -> bool:
        return self.pointer > 0

    @property
    def can_redo(self) -> bool:
        return self.pointer < len(self.entries)

    def labels(self, last_n: int = 10) -> list[dict[str, Any]]:
        """Return last N applied entries' labels for UI display."""
        result = []
        start = max(0, self.pointer - last_n)
        for i in range(self.pointer - 1, start - 1, -1):
            e = self.entries[i]
            result.append({
                "index": i,
                "label": e.get("label", ""),
                "timestamp": e.get("timestamp", ""),
            })
        return result


class CutUndoRedoService:
    """
    Manages undo/redo for a CUT project timeline.

    Usage:
        service = CutUndoRedoService(sandbox_root, project_id, timeline_id)
        service.push(label, prev_state, applied_ops, rev_before, rev_after)
        result = service.undo()   # returns state to restore
        result = service.redo()   # returns ops to re-apply
    """

    def __init__(
        self,
        sandbox_root: str,
        project_id: str,
        timeline_id: str,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ):
        self.sandbox_root = Path(sandbox_root)
        self.project_id = project_id
        self.timeline_id = timeline_id
        self.max_depth = max_depth
        self._stack: UndoStack | None = None

    @property
    def _stack_path(self) -> Path:
        return self.sandbox_root / "cut_runtime" / "state" / "undo_stack.json"

    def _load_stack(self) -> UndoStack:
        if self._stack is not None:
            return self._stack

        path = self._stack_path
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                self._stack = UndoStack(
                    project_id=raw.get("project_id", self.project_id),
                    timeline_id=raw.get("timeline_id", self.timeline_id),
                    max_depth=raw.get("max_depth", self.max_depth),
                    entries=raw.get("entries", []),
                    pointer=raw.get("pointer", 0),
                )
                if (
                    self._stack.project_id != self.project_id
                    or self._stack.timeline_id != self.timeline_id
                ):
                    logger.warning("Undo stack project/timeline mismatch, resetting")
                    self._stack = self._empty_stack()
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning("Failed to load undo stack, resetting: %s", exc)
                self._stack = self._empty_stack()
        else:
            self._stack = self._empty_stack()
        return self._stack

    def _empty_stack(self) -> UndoStack:
        return UndoStack(
            project_id=self.project_id,
            timeline_id=self.timeline_id,
            max_depth=self.max_depth,
        )

    def _save_stack(self) -> None:
        stack = self._load_stack()
        path = self._stack_path
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "schema_version": "cut_undo_stack_v1",
            "project_id": stack.project_id,
            "timeline_id": stack.timeline_id,
            "max_depth": stack.max_depth,
            "pointer": stack.pointer,
            "entry_count": len(stack.entries),
            "entries": stack.entries,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)

    # ── Core operations ─────────────────────────────────────

    def push(
        self,
        label: str,
        prev_state: dict[str, Any],
        applied_ops: list[dict[str, Any]],
        revision_before: int,
        revision_after: int,
        entry_id: str = "",
    ) -> dict[str, Any]:
        """Push a new undo entry after a successful timeline edit."""
        stack = self._load_stack()

        # Truncate redo tail (entries beyond pointer)
        if stack.pointer < len(stack.entries):
            stack.entries = stack.entries[: stack.pointer]

        entry = {
            "entry_id": entry_id or f"undo_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{len(stack.entries)}",
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prev_state": prev_state,
            "applied_ops": applied_ops,
            "revision_before": revision_before,
            "revision_after": revision_after,
        }
        stack.entries.append(entry)

        # Enforce max depth — drop oldest
        while len(stack.entries) > stack.max_depth:
            stack.entries.pop(0)

        # Pointer at head
        stack.pointer = len(stack.entries)

        self._save_stack()
        return {
            "pushed": True,
            "undo_depth": stack.undo_depth,
            "redo_depth": stack.redo_depth,
        }

    def undo(self) -> dict[str, Any] | None:
        """Undo last applied action. Returns prev_state to restore, or None."""
        stack = self._load_stack()
        if not stack.can_undo:
            return None

        # The entry to undo is at pointer-1
        undo_idx = stack.pointer - 1
        entry = stack.entries[undo_idx]
        restore_state = deepcopy(entry.get("prev_state", {}))

        stack.pointer -= 1
        self._save_stack()

        return {
            "entry": {
                "entry_id": entry.get("entry_id", ""),
                "label": entry.get("label", ""),
                "timestamp": entry.get("timestamp", ""),
                "revision_before": entry.get("revision_before", 0),
                "revision_after": entry.get("revision_after", 0),
            },
            "restore_state": restore_state,
            "undo_depth": stack.pointer,
            "redo_depth": len(stack.entries) - stack.pointer,
        }

    def redo(self) -> dict[str, Any] | None:
        """Redo next undone action. Returns ops to re-apply, or None."""
        stack = self._load_stack()
        if not stack.can_redo:
            return None

        # The entry to redo is at pointer
        redo_idx = stack.pointer
        entry = stack.entries[redo_idx]

        stack.pointer += 1
        self._save_stack()

        return {
            "entry": {
                "entry_id": entry.get("entry_id", ""),
                "label": entry.get("label", ""),
                "timestamp": entry.get("timestamp", ""),
                "revision_before": entry.get("revision_before", 0),
                "revision_after": entry.get("revision_after", 0),
            },
            "reapply_ops": deepcopy(entry.get("applied_ops", [])),
            "undo_depth": stack.pointer,
            "redo_depth": len(stack.entries) - stack.pointer,
        }

    def get_stack_info(self) -> dict[str, Any]:
        """Return stack metadata for UI (no heavy state payloads)."""
        stack = self._load_stack()
        return {
            "schema_version": "cut_undo_stack_v1",
            "project_id": stack.project_id,
            "timeline_id": stack.timeline_id,
            "undo_depth": stack.undo_depth,
            "redo_depth": stack.redo_depth,
            "can_undo": stack.can_undo,
            "can_redo": stack.can_redo,
            "max_depth": stack.max_depth,
            "labels": stack.labels(last_n=20),
        }

    def clear(self) -> dict[str, Any]:
        """Clear the entire undo stack."""
        self._stack = self._empty_stack()
        self._save_stack()
        return {"cleared": True, "undo_depth": 0, "redo_depth": 0}


def build_op_label(ops: list[dict[str, Any]]) -> str:
    """Generate a human-readable label from a list of timeline ops."""
    if not ops:
        return "Empty edit"
    if len(ops) == 1:
        op = ops[0]
        op_type = op.get("op", "unknown")
        clip_id = op.get("clip_id", "")
        short_id = clip_id[-8:] if clip_id else ""
        labels = {
            "move_clip": f"Move clip {short_id}",
            "trim_clip": f"Trim clip {short_id}",
            "add_clip": f"Add clip {short_id}",
            "remove_clip": f"Remove clip {short_id}",
            "split_at": f"Split clip {short_id}",
            "ripple_delete": f"Ripple delete {short_id}",
            "insert_at": f"Insert clip {short_id}",
            "overwrite_at": f"Overwrite at {op.get('start_sec', '?')}s",
            "set_selection": "Change selection",
            "set_view": "Change view",
            "apply_sync_offset": f"Sync clip {short_id}",
        }
        return labels.get(op_type, f"{op_type} {short_id}".strip())

    op_types = set(op.get("op", "") for op in ops)
    return f"{len(ops)} edits ({', '.join(sorted(op_types))})"
