"""
VETKA Tool Source Watch — Auto-detect tool code changes for CORTEX freshness.

MARKER_195.2.WATCH

Maps each MCP tool to its source file(s), tracks git commit hashes,
and generates FreshnessEvents when tool code changes. This allows
CORTEX to discount pre-update failures and boost recently-fixed tools.

Storage: data/reflex/tool_freshness.json (epoch log)
         data/reflex/tool_source_map.json (auto-discovered mapping)

NO LLM calls. File-based persistence. Runs on session_init.

Part of VETKA OS:
  VETKA > REFLEX > Tool Freshness (this file)

@status: active
@phase: 195.2
@depends: reflex_feedback (reads epochs), reflex_guard (clears warnings)
@used_by: session_tools.session_init(), reflex_feedback._aggregate_entries()
"""

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent.parent
REFLEX_DATA_DIR = PROJECT_ROOT / "data" / "reflex"
TOOL_FRESHNESS_PATH = REFLEX_DATA_DIR / "tool_freshness.json"
TOOL_SOURCE_MAP_PATH = REFLEX_DATA_DIR / "tool_source_map.json"
TOOL_SOURCE_OVERRIDES_PATH = REFLEX_DATA_DIR / "tool_source_overrides.json"
TOOL_CATALOG_PATH = REFLEX_DATA_DIR / "tool_catalog.json"
MCP_TOOLS_DIR = PROJECT_ROOT / "src" / "mcp" / "tools"

# --- Config ---
MAX_EPOCH_HISTORY = 100  # Cap epoch history per tool
FRESHNESS_WINDOW_HOURS = 48.0  # How long a tool is considered "fresh"


@dataclass
class FreshnessEvent:
    """Emitted when a tool's source code has changed.

    MARKER_195.2.EVENT
    """
    tool_id: str
    source_files: List[str]
    old_commit: str
    new_commit: str
    old_epoch: int
    new_epoch: int
    updated_at: str = ""

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolFreshnessEntry:
    """Per-tool freshness state in tool_freshness.json.

    MARKER_195.2.EPOCH
    """
    source_files: List[str]
    current_epoch: int = 0
    last_commit: str = ""
    last_mtime: float = 0.0
    updated_at: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)

    def is_recently_updated(self, hours: float = FRESHNESS_WINDOW_HOURS) -> bool:
        """Check if tool was updated within the freshness window."""
        if not self.updated_at:
            return False
        try:
            ts = datetime.fromisoformat(self.updated_at)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
            return age_hours < hours
        except (ValueError, TypeError):
            return False

    def hours_since_update(self) -> float:
        """Hours elapsed since last update."""
        if not self.updated_at:
            return float("inf")
        try:
            ts = datetime.fromisoformat(self.updated_at)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
        except (ValueError, TypeError):
            return float("inf")

    def epoch_for_timestamp(self, ts_iso: str) -> int:
        """Determine which epoch a given timestamp belongs to.

        Used by reflex_feedback._aggregate_entries() to discount pre-update entries.
        """
        try:
            ts = datetime.fromisoformat(ts_iso)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return 0

        # Walk history in reverse to find the epoch active at ts
        for h in reversed(self.history):
            try:
                h_ts = datetime.fromisoformat(h["ts"])
                if h_ts.tzinfo is None:
                    h_ts = h_ts.replace(tzinfo=timezone.utc)
                if ts >= h_ts:
                    return h["epoch"]
            except (ValueError, TypeError, KeyError):
                continue
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_files": self.source_files,
            "current_epoch": self.current_epoch,
            "last_commit": self.last_commit,
            "last_mtime": self.last_mtime,
            "updated_at": self.updated_at,
            "history": self.history[-MAX_EPOCH_HISTORY:],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ToolFreshnessEntry":
        return ToolFreshnessEntry(
            source_files=d.get("source_files", []),
            current_epoch=d.get("current_epoch", 0),
            last_commit=d.get("last_commit", ""),
            last_mtime=d.get("last_mtime", 0.0),
            updated_at=d.get("updated_at", ""),
            history=d.get("history", []),
        )


class ToolSourceWatch:
    """
    MARKER_195.2.WATCH

    Maps MCP tools to source files and detects code changes via git commit hashes.
    Generates FreshnessEvents when tool code is updated.

    Usage:
        watch = get_tool_source_watch()
        events = watch.scan_all()  # Returns list of FreshnessEvent
        entry = watch.get(tool_id)  # Get freshness state for a tool
    """

    def __init__(self):
        self._source_map: Optional[Dict[str, List[str]]] = None
        self._freshness: Optional[Dict[str, ToolFreshnessEntry]] = None

    def scan_all(self) -> List[FreshnessEvent]:
        """Scan all mapped tools for source code changes.

        Returns list of FreshnessEvents for tools whose source files changed.
        Designed to run once per session_init (budget: <500ms).
        """
        source_map = self._get_source_map()
        freshness = self._load_freshness()
        events: List[FreshnessEvent] = []

        # Group by unique source files to minimize git calls
        file_to_tools: Dict[str, List[str]] = {}
        for tool_id, files in source_map.items():
            for f in files:
                file_to_tools.setdefault(f, []).append(tool_id)

        # Batch git log for all unique files
        file_commits = self._batch_git_commits(list(file_to_tools.keys()))

        # Check each tool
        for tool_id, files in source_map.items():
            # Get the newest commit across all source files for this tool
            newest_commit = ""
            for f in files:
                commit = file_commits.get(f, "")
                if commit and (not newest_commit or commit > newest_commit):
                    newest_commit = commit

            if not newest_commit:
                continue

            entry = freshness.get(tool_id)
            if entry is None:
                # First time seeing this tool — initialize epoch 0
                entry = ToolFreshnessEntry(
                    source_files=files,
                    current_epoch=0,
                    last_commit=newest_commit,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                    history=[{
                        "epoch": 0,
                        "commit": newest_commit,
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }],
                )
                freshness[tool_id] = entry
                continue

            # Compare commit hash
            if newest_commit != entry.last_commit:
                old_epoch = entry.current_epoch
                new_epoch = old_epoch + 1
                now_iso = datetime.now(timezone.utc).isoformat()

                entry.current_epoch = new_epoch
                entry.last_commit = newest_commit
                entry.updated_at = now_iso
                entry.source_files = files
                entry.history.append({
                    "epoch": new_epoch,
                    "commit": newest_commit,
                    "ts": now_iso,
                })
                # Compact history
                if len(entry.history) > MAX_EPOCH_HISTORY:
                    entry.history = entry.history[-MAX_EPOCH_HISTORY:]

                event = FreshnessEvent(
                    tool_id=tool_id,
                    source_files=files,
                    old_commit=entry.last_commit if old_epoch > 0 else "",
                    new_commit=newest_commit,
                    old_epoch=old_epoch,
                    new_epoch=new_epoch,
                    updated_at=now_iso,
                )
                events.append(event)
                logger.info(
                    "[FRESHNESS] Tool %s updated: epoch %d→%d (commit %s)",
                    tool_id, old_epoch, new_epoch, newest_commit[:8],
                )

        # Persist
        self._save_freshness(freshness)
        self._freshness = freshness

        if events:
            logger.info("[FRESHNESS] %d tool(s) freshened: %s",
                        len(events), ", ".join(e.tool_id for e in events))

        return events

    def get(self, tool_id: str) -> Optional[ToolFreshnessEntry]:
        """Get freshness state for a specific tool."""
        freshness = self._load_freshness()
        return freshness.get(tool_id)

    def get_all(self) -> Dict[str, ToolFreshnessEntry]:
        """Get all freshness entries."""
        return self._load_freshness()

    def get_recently_updated(self, hours: float = FRESHNESS_WINDOW_HOURS) -> List[str]:
        """Get tool_ids updated within the freshness window."""
        freshness = self._load_freshness()
        return [
            tool_id for tool_id, entry in freshness.items()
            if entry.is_recently_updated(hours)
        ]

    # --- Source Map ---

    def _get_source_map(self) -> Dict[str, List[str]]:
        """Get tool→source file mapping. Auto-discovers if not cached."""
        if self._source_map is not None:
            return self._source_map

        # Try loading saved map
        source_map = self._load_source_map()

        # Apply manual overrides
        overrides = self._load_overrides()
        source_map.update(overrides)

        # If empty, auto-discover
        if not source_map:
            source_map = self._auto_discover()
            overrides = self._load_overrides()
            source_map.update(overrides)
            self._save_source_map(source_map)

        self._source_map = source_map
        return source_map

    def rebuild_source_map(self) -> Dict[str, List[str]]:
        """Force re-discover tool→source mapping."""
        source_map = self._auto_discover()
        overrides = self._load_overrides()
        source_map.update(overrides)
        self._save_source_map(source_map)
        self._source_map = source_map
        return source_map

    def _auto_discover(self) -> Dict[str, List[str]]:
        """Auto-discover tool→source file mapping.

        Strategy:
        1. Scan src/mcp/tools/*.py for tool name declarations (class-based pattern)
        2. Also scan for register_* functions (list-based pattern)
        3. Include vetka_mcp_bridge.py handler dispatch as secondary source

        MARKER_195.2.DISCOVER
        """
        source_map: Dict[str, List[str]] = {}

        if not MCP_TOOLS_DIR.exists():
            logger.warning("[FRESHNESS] MCP tools dir not found: %s", MCP_TOOLS_DIR)
            return source_map

        # Pattern: return "vetka_xxx" or return 'vetka_xxx' in @property name
        name_pattern = re.compile(
            r'return\s+["\']'
            r'(vetka_\w+|mycelium_\w+|cut_\w+|internal_\w+)'
            r'["\']'
        )

        # Scan all .py files in tools directory
        for py_file in MCP_TOOLS_DIR.glob("*.py"):
            if py_file.name.startswith("__") or py_file.name.startswith("base_"):
                continue

            rel_path = str(py_file.relative_to(PROJECT_ROOT))
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            # Find all tool name declarations
            for match in name_pattern.finditer(content):
                tool_id = match.group(1)
                if tool_id not in source_map:
                    source_map[tool_id] = []
                if rel_path not in source_map[tool_id]:
                    source_map[tool_id].append(rel_path)

        # Also add bridge as secondary source for tools dispatched via REST
        bridge_path = "src/mcp/vetka_mcp_bridge.py"
        bridge_full = PROJECT_ROOT / bridge_path
        if bridge_full.exists():
            try:
                content = bridge_full.read_text(encoding="utf-8", errors="ignore")
                bridge_pattern = re.compile(
                    r'name\s*==\s*["\']'
                    r'(vetka_\w+|mycelium_\w+|cut_\w+)'
                    r'["\']'
                )
                for match in bridge_pattern.finditer(content):
                    tool_id = match.group(1)
                    # Only add bridge if tool doesn't have a primary source
                    if tool_id not in source_map:
                        source_map[tool_id] = [bridge_path]
            except OSError:
                pass

        # Also map tools from task_board_tools.py (mycelium namespace)
        tb_path = MCP_TOOLS_DIR / "task_board_tools.py"
        if tb_path.exists():
            rel = str(tb_path.relative_to(PROJECT_ROOT))
            try:
                content = tb_path.read_text(encoding="utf-8", errors="ignore")
                for match in name_pattern.finditer(content):
                    tool_id = match.group(1)
                    if tool_id not in source_map:
                        source_map[tool_id] = []
                    if rel not in source_map[tool_id]:
                        source_map[tool_id].append(rel)
            except OSError:
                pass

        logger.info("[FRESHNESS] Auto-discovered %d tool→file mappings", len(source_map))
        return source_map

    # --- Git Operations ---

    def _batch_git_commits(self, files: List[str]) -> Dict[str, str]:
        """Get latest commit hash for multiple files efficiently.

        Uses a single `git log` call with --diff-filter to get the latest
        commit that touched each file. Falls back to per-file calls if needed.

        Returns dict of {relative_path: commit_hash}.
        """
        result: Dict[str, str] = {}
        if not files:
            return result

        unique_files = list(set(files))

        # Strategy: one git log per file, but run them all via a single
        # shell command using a for-loop to minimize process overhead
        try:
            # Build a script that outputs "FILE\tHASH" for each file
            file_args = " ".join(
                f'"{f}"' for f in unique_files
                if (PROJECT_ROOT / f).exists()
            )
            if not file_args:
                return result

            script = (
                f'cd "{PROJECT_ROOT}" && '
                f'for f in {file_args}; do '
                f'h=$(git log -1 --format=%H -- "$f" 2>/dev/null); '
                f'[ -n "$h" ] && printf "%s\\t%s\\n" "$f" "$h"; '
                f'done'
            )
            proc = subprocess.run(
                ["sh", "-c", script],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(PROJECT_ROOT),
            )
            if proc.returncode == 0:
                for line in proc.stdout.strip().split("\n"):
                    if "\t" in line:
                        rel_path, commit = line.split("\t", 1)
                        result[rel_path] = commit.strip()
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning("[FRESHNESS] Batch git failed: %s, falling back", e)
            # Fallback: per-file calls
            for rel_path in unique_files:
                if not (PROJECT_ROOT / rel_path).exists():
                    continue
                try:
                    proc = subprocess.run(
                        ["git", "log", "-1", "--format=%H", "--", rel_path],
                        capture_output=True, text=True, timeout=5,
                        cwd=str(PROJECT_ROOT),
                    )
                    if proc.returncode == 0 and proc.stdout.strip():
                        result[rel_path] = proc.stdout.strip()
                except (subprocess.TimeoutExpired, OSError):
                    continue

        return result

    # --- Persistence ---

    def _load_freshness(self) -> Dict[str, ToolFreshnessEntry]:
        """Load tool freshness data from JSON."""
        if self._freshness is not None:
            return self._freshness

        freshness: Dict[str, ToolFreshnessEntry] = {}
        if not TOOL_FRESHNESS_PATH.exists():
            self._freshness = freshness
            return freshness

        try:
            with open(TOOL_FRESHNESS_PATH, "r") as f:
                data = json.load(f)
            for tool_id, entry_data in data.items():
                freshness[tool_id] = ToolFreshnessEntry.from_dict(entry_data)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("[FRESHNESS] Failed to load freshness data: %s", e)

        self._freshness = freshness
        return freshness

    def _save_freshness(self, freshness: Dict[str, ToolFreshnessEntry]) -> None:
        """Persist tool freshness data to JSON."""
        REFLEX_DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {tool_id: entry.to_dict() for tool_id, entry in freshness.items()}
        try:
            with open(TOOL_FRESHNESS_PATH, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("[FRESHNESS] Failed to save freshness data: %s", e)

    def _load_source_map(self) -> Dict[str, List[str]]:
        """Load saved tool→source file mapping."""
        if not TOOL_SOURCE_MAP_PATH.exists():
            return {}
        try:
            with open(TOOL_SOURCE_MAP_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_source_map(self, source_map: Dict[str, List[str]]) -> None:
        """Save tool→source file mapping."""
        REFLEX_DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(TOOL_SOURCE_MAP_PATH, "w") as f:
                json.dump(source_map, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("[FRESHNESS] Failed to save source map: %s", e)

    def _load_overrides(self) -> Dict[str, List[str]]:
        """Load manual tool→source file overrides."""
        if not TOOL_SOURCE_OVERRIDES_PATH.exists():
            return {}
        try:
            with open(TOOL_SOURCE_OVERRIDES_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}


# --- Singleton ---

_watch_instance: Optional[ToolSourceWatch] = None


def get_tool_source_watch() -> ToolSourceWatch:
    """Get or create singleton ToolSourceWatch."""
    global _watch_instance
    if _watch_instance is None:
        _watch_instance = ToolSourceWatch()
    return _watch_instance


def reset_tool_source_watch() -> None:
    """Reset singleton (for testing)."""
    global _watch_instance
    _watch_instance = None
