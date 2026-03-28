"""
VETKA ENGRAM L1 — Deterministic O(1) Cache for Learned Patterns.

True Engram inspired by DeepSeek: deterministic dict-based cache
sitting between RAM hot preferences (L0/AURA) and Qdrant semantic search (L2).

4-key lookup format: agent_type::filename::action_type::phase_type
Compound keys for multi-file patterns: pair::file1::file2::action

Auto-promoted from L2 (VetkaResourceLearnings) when match_count >= 3.

@file engram_cache.py
@status active
@phase 187.8 MARKER_187.8
@depends json, pathlib, logging, time
@used_by session_tools.py, reflex/scorer.py
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_PATH = PROJECT_ROOT / "data" / "engram_cache.json"

MAX_ENTRIES = 200

# Per-category TTL in days (0 = permanent)
CATEGORY_TTL = {
    "danger": 0,
    "architecture": 0,
    "pattern": 60,
    "optimization": 60,
    "tool_select": 30,
    "default": 90,
}


@dataclass
class EngramEntry:
    """Single L1 cache entry."""
    key: str
    value: str
    category: str = "default"
    hit_count: int = 0
    match_count: int = 0  # L2 matches that triggered promotion
    created_at: float = field(default_factory=time.time)
    last_hit: float = field(default_factory=time.time)
    source_learning_id: Optional[str] = None
    # MARKER_187.10: Demotion tracking
    was_presented: bool = False
    presented_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EngramEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class EngramCache:
    """
    ENGRAM L1 — O(1) deterministic cache.

    Key format: agent_type::filename::action_type::phase_type
    Compound:   pair::file1::file2::action

    Lookup priority:
    1. Exact match
    2. Agent wildcard: *::filename::action::phase
    3. Full wildcard:  *::filename::action::*
    """

    def __init__(self, cache_path: Path = CACHE_PATH):
        self._cache: Dict[str, EngramEntry] = {}
        self._path = cache_path
        self._load()

    def _load(self):
        """Load cache from disk."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                for key, entry_dict in data.items():
                    self._cache[key] = EngramEntry.from_dict(entry_dict)
                logger.info(f"[ENGRAM L1] Loaded {len(self._cache)} entries")
            except Exception as e:
                logger.warning(f"[ENGRAM L1] Load failed: {e}")
        else:
            logger.info("[ENGRAM L1] No cache file, starting empty")

    def _save(self):
        """Persist cache to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._cache.items()}
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @staticmethod
    def make_key(agent: str, filename: str, action: str, phase_type: str) -> str:
        """Build 4-component key."""
        return f"{agent}::{filename}::{action}::{phase_type}"

    @staticmethod
    def make_pair_key(file1: str, file2: str, action: str) -> str:
        """Build compound key for file pairs."""
        f1, f2 = sorted([file1, file2])
        return f"pair::{f1}::{f2}::{action}"

    def put(self, key: str, value: str, category: str = "default",
            source_learning_id: Optional[str] = None, match_count: int = 0) -> bool:
        """Insert or update an entry. Returns True if new entry."""
        is_new = key not in self._cache
        if is_new and len(self._cache) >= MAX_ENTRIES:
            self._evict()

        self._cache[key] = EngramEntry(
            key=key, value=value, category=category,
            match_count=match_count,
            source_learning_id=source_learning_id,
        )
        self._save()
        return is_new

    def get(self, agent: str, filename: str, action: str, phase_type: str) -> Optional[EngramEntry]:
        """
        Lookup with fallback chain:
        1. exact match
        2. *::filename::action::phase_type
        3. *::filename::action::*
        """
        candidates = [
            self.make_key(agent, filename, action, phase_type),
            self.make_key("*", filename, action, phase_type),
            self.make_key("*", filename, action, "*"),
        ]
        for key in candidates:
            entry = self._cache.get(key)
            if entry and not self._is_expired(entry):
                entry.hit_count += 1
                entry.last_hit = time.time()
                return entry
        return None

    def get_pair(self, file1: str, file2: str, action: str) -> Optional[EngramEntry]:
        """Lookup compound key for file pair."""
        key = self.make_pair_key(file1, file2, action)
        entry = self._cache.get(key)
        if entry and not self._is_expired(entry):
            entry.hit_count += 1
            entry.last_hit = time.time()
            return entry
        return None

    # ============ MARKER_187.10: Demotion ============

    def mark_presented(self, key: str) -> bool:
        """Mark entry as presented to agent during session."""
        entry = self._cache.get(key)
        if entry:
            entry.was_presented = True
            entry.presented_at = time.time()
            self._save()
            return True
        return False

    def get_presented(self) -> List[EngramEntry]:
        """Get all entries presented in current session (was_presented=True)."""
        return [e for e in self._cache.values() if e.was_presented]

    def demote_if_ignored(self, key: str, task_succeeded: bool) -> bool:
        """
        Demote entry from L1 if agent ignored the advice AND task succeeded.

        Logic:
        - Entry was presented but agent didn't follow it
        - Task succeeded anyway → lesson may be stale → demote
        - Task failed → lesson was correct → keep it
        - category="danger" → NEVER demote

        Returns True if demoted.
        """
        entry = self._cache.get(key)
        if not entry:
            return False
        if not entry.was_presented:
            return False
        if entry.category == "danger":
            logger.debug(f"[ENGRAM L1] Skipping demotion for danger entry: {key}")
            return False
        if task_succeeded:
            del self._cache[key]
            self._save()
            logger.info(f"[ENGRAM L1] Demoted (ignored + succeeded): {key}")
            return True
        # Task failed → lesson was right, boost it
        entry.hit_count += 1
        entry.was_presented = False
        self._save()
        return False

    def reset_presented(self):
        """Reset all was_presented flags (call at session end)."""
        for entry in self._cache.values():
            entry.was_presented = False
            entry.presented_at = None
        self._save()

    def find_pair_warnings(self, filename: str) -> List[EngramEntry]:
        """Find all pair entries involving this file. Returns partner warnings."""
        results = []
        for key, entry in self._cache.items():
            if key.startswith("pair::") and filename in key and not self._is_expired(entry):
                results.append(entry)
        return results

    def remove(self, key: str) -> bool:
        """Remove entry (demotion from L1)."""
        if key in self._cache:
            del self._cache[key]
            self._save()
            return True
        return False

    def _is_expired(self, entry: EngramEntry) -> bool:
        """Check if entry exceeded its category TTL."""
        ttl_days = CATEGORY_TTL.get(entry.category, CATEGORY_TTL["default"])
        if ttl_days == 0:
            return False
        age_days = (time.time() - entry.created_at) / 86400
        return age_days > ttl_days

    def _evict(self):
        """Evict: remove expired first, then LFU (lowest hit_count + oldest last_hit)."""
        # Phase 1: remove expired
        expired = [k for k, v in self._cache.items() if self._is_expired(v)]
        for k in expired:
            del self._cache[k]

        if len(self._cache) < MAX_ENTRIES:
            return

        # Phase 2: LFU+LRU — evict lowest hit_count, break ties by oldest last_hit
        victim = min(self._cache.keys(),
                     key=lambda k: (self._cache[k].hit_count, self._cache[k].last_hit))
        del self._cache[victim]
        logger.debug(f"[ENGRAM L1] Evicted: {victim}")

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Return all non-expired entries as dicts."""
        return {k: v.to_dict() for k, v in self._cache.items()
                if not self._is_expired(v)}

    # ============ MARKER_193.2: Category accessors ============

    def get_danger_entries(self, role: Optional[str] = None) -> List[EngramEntry]:
        """Return all non-expired entries with category='danger'.

        Args:
            role: Optional callsign filter. If provided, returns only entries
                  whose key starts with the role prefix (e.g. 'Zeta::') or
                  universal entries ('*::', 'feedback::', 'pair::').
        """
        entries = [e for e in self._cache.values()
                   if e.category == "danger" and not self._is_expired(e)]
        if role:
            entries = [e for e in entries if self._matches_role(e.key, role)]
        return entries

    def get_all_by_category(self, category: str, role: Optional[str] = None) -> List[EngramEntry]:
        """Return all non-expired entries matching the given category.

        Args:
            role: Optional callsign filter (same logic as get_danger_entries).
        """
        entries = [e for e in self._cache.values()
                   if e.category == category and not self._is_expired(e)]
        if role:
            entries = [e for e in entries if self._matches_role(e.key, role)]
        return entries

    @staticmethod
    def _matches_role(key: str, role: str) -> bool:
        """Check if an engram key is relevant to a given role.

        Universal prefixes (*, feedback::, pair::) match all roles.
        Role-specific entries match only if key starts with the role callsign.
        """
        prefix = key.split("::")[0] if "::" in key else key
        if prefix in ("*", "feedback", "pair"):
            return True
        return prefix.lower() == role.lower()

    def stats(self) -> Dict[str, Any]:
        """Cache statistics."""
        total = len(self._cache)
        expired = sum(1 for v in self._cache.values() if self._is_expired(v))
        categories = {}
        for v in self._cache.values():
            categories[v.category] = categories.get(v.category, 0) + 1
        return {
            "total": total,
            "active": total - expired,
            "expired": expired,
            "max": MAX_ENTRIES,
            "categories": categories,
        }

    def __len__(self) -> int:
        return len(self._cache)


# ============ SINGLETON ============

_instance: Optional[EngramCache] = None


def get_engram_cache() -> EngramCache:
    """Get singleton EngramCache instance."""
    global _instance
    if _instance is None:
        _instance = EngramCache(cache_path=CACHE_PATH)
    return _instance


def reset_engram_cache():
    """Reset singleton (for tests)."""
    global _instance
    _instance = None


# ============ MARKER_200.FEEDBACK_BRIDGE ============

def ingest_feedback_memories(memory_dir: Optional[Path] = None) -> int:
    """Scan Claude Code feedback_*.md files and ingest into ENGRAM L1 as danger entries.

    Parses YAML frontmatter (name, description) from each file and creates
    permanent danger entries so REFLEX Guard can see user corrections.

    Key format: feedback::{name}::rule
    Category: danger (TTL=0, permanent, never demoted)

    Args:
        memory_dir: Path to Claude Code memory directory. If None, auto-detects
                    from PROJECT_ROOT via the standard Claude Code projects path.

    Returns:
        Number of new entries ingested (skips already-existing keys).
    """
    if memory_dir is None:
        memory_dir = _detect_claude_memory_dir()
    if memory_dir is None or not memory_dir.is_dir():
        return 0

    cache = get_engram_cache()
    ingested = 0

    for md_file in sorted(memory_dir.glob("feedback_*.md")):
        try:
            name, description = _parse_feedback_frontmatter(md_file)
            if not name or not description:
                continue

            key = f"feedback::{name}::rule"
            # Skip if already present (idempotent)
            if key in cache._cache:
                continue

            cache.put(
                key=key,
                value=description,
                category="danger",
                source_learning_id=f"feedback_bridge:{md_file.name}",
                match_count=0,
            )
            ingested += 1
        except Exception as e:
            logger.debug("[FEEDBACK_BRIDGE] Failed to parse %s: %s", md_file.name, e)

    if ingested > 0:
        logger.info("[FEEDBACK_BRIDGE] Ingested %d feedback memories into ENGRAM L1", ingested)

    return ingested


def _detect_claude_memory_dir() -> Optional[Path]:
    """Auto-detect Claude Code memory directory for this project.

    Looks for ~/.claude/projects/<sanitized-project-path>/memory/
    """
    import re as _re

    # Resolve the actual project root (not worktree)
    project_root = PROJECT_ROOT
    # If we're in a worktree, go up to the real project
    if ".claude/worktrees" in str(project_root):
        # .claude/worktrees/X is at PROJECT_ROOT, real root is 3 levels up
        parts = str(project_root).split(".claude/worktrees")
        if parts:
            project_root = Path(parts[0].rstrip("/"))

    sanitized = _re.sub(r"[/_.]", "-", str(project_root.resolve()))
    memory_dir = Path.home() / ".claude" / "projects" / sanitized / "memory"
    if memory_dir.is_dir():
        return memory_dir
    return None


def _parse_feedback_frontmatter(filepath: Path) -> tuple:
    """Parse YAML frontmatter from a feedback_*.md file.

    Returns (name, description) tuple. Returns ('', '') on parse failure.
    """
    text = filepath.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return ("", "")

    # Find closing ---
    end = text.find("---", 3)
    if end < 0:
        return ("", "")

    frontmatter = text[3:end].strip()
    name = ""
    description = ""
    for line in frontmatter.splitlines():
        line = line.strip()
        if line.startswith("name:"):
            name = line[5:].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            description = line[12:].strip().strip('"').strip("'")

    return (name, description)
