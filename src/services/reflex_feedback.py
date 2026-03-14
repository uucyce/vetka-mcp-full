"""
REFLEX Feedback CORTEX — Learning loop for tool selection.

MARKER_172.P3.FEEDBACK

Layer 3 of REFLEX (Reactive Execution & Function Linking EXchange).
Records tool usage outcomes, aggregates per (tool_id, phase_type) scores,
and feeds back into Scorer (Layer 2) for continuous improvement.

Storage: append-only JSONL log → periodic compaction.
Aggregation: score = success_rate * 0.40 + usefulness * 0.35 + verifier_pass * 0.25
Decay: weight *= exp(-0.1 * days_old)

NO LLM calls. File-based persistence. Thread-safe writes.

Part of VETKA OS:
  VETKA > REFLEX > Feedback CORTEX (this file)

@status: active
@phase: 172.P3
@depends: reflex_scorer (reads scores), agent_pipeline (records outcomes)
@used_by: reflex_scorer._feedback_score(), P4 injection points
"""

import json
import logging
import math
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# --- Paths ---
REFLEX_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "reflex"
FEEDBACK_LOG_PATH = REFLEX_DATA_DIR / "feedback_log.jsonl"

# --- Aggregation formula weights ---
AGG_SUCCESS_WEIGHT = 0.40
AGG_USEFULNESS_WEIGHT = 0.35
AGG_VERIFIER_WEIGHT = 0.25

# --- Decay ---
DECAY_LAMBDA = 0.1   # exp(-0.1 * days_old)

# --- Compaction ---
MAX_LOG_ENTRIES = 1000  # Compact when exceeding this
COMPACT_KEEP = 500      # After compaction, keep newest N raw entries

# --- Default score (cold start) ---
DEFAULT_FEEDBACK_SCORE = 0.5


@dataclass
class FeedbackEntry:
    """Single feedback record in the JSONL log.

    MARKER_172.P3.LOG
    """
    tool_id: str
    phase_type: str = "research"
    agent_role: str = "coder"
    success: bool = True            # Did the tool call succeed?
    useful: bool = True             # Was the result useful? (content changed, issue found)
    verifier_passed: bool = True    # Did the verifier approve the subtask?
    execution_time_ms: float = 0.0  # Tool call latency
    subtask_id: str = ""            # Link to subtask for outcome tracking
    timestamp: str = ""             # ISO 8601 UTC
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "FeedbackEntry":
        return FeedbackEntry(
            tool_id=d.get("tool_id", ""),
            phase_type=d.get("phase_type", "research"),
            agent_role=d.get("agent_role", "coder"),
            success=d.get("success", True),
            useful=d.get("useful", True),
            verifier_passed=d.get("verifier_passed", True),
            execution_time_ms=d.get("execution_time_ms", 0.0),
            subtask_id=d.get("subtask_id", ""),
            timestamp=d.get("timestamp", ""),
            extra=d.get("extra", {}),
        )


@dataclass
class AggregatedScore:
    """Aggregated score for a (tool_id, phase_type) pair."""
    tool_id: str
    phase_type: str
    score: float              # 0.0 - 1.0
    sample_count: int         # How many entries contributed
    success_rate: float       # Weighted success rate
    usefulness_rate: float    # Weighted usefulness rate
    verifier_rate: float      # Weighted verifier pass rate


class ReflexFeedback:
    """
    MARKER_172.P3.FEEDBACK

    REFLEX Layer 3: Feedback CORTEX.
    Records tool usage, aggregates scores, feeds back to Scorer.

    Thread-safe: uses threading.Lock for file writes.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self._log_path = log_path or FEEDBACK_LOG_PATH
        self._lock = threading.Lock()
        self._cache: Optional[List[FeedbackEntry]] = None
        self._cache_dirty = False

    def record(
        self,
        tool_id: str,
        success: bool = True,
        useful: bool = True,
        phase_type: str = "research",
        agent_role: str = "coder",
        execution_time_ms: float = 0.0,
        subtask_id: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> FeedbackEntry:
        """Record a tool usage event. Appends to JSONL log.

        Called after each tool execution in fc_loop (IP-3).

        Args:
            tool_id: Which tool was used
            success: Did the call succeed (no error)?
            useful: Was the result useful (content changed, issue found)?
            phase_type: Current pipeline phase
            agent_role: Which agent used the tool
            execution_time_ms: Call latency
            subtask_id: Link to pipeline subtask
            extra: Additional metadata

        Returns:
            The recorded FeedbackEntry.
        """
        entry = FeedbackEntry(
            tool_id=tool_id,
            phase_type=phase_type,
            agent_role=agent_role,
            success=success,
            useful=useful,
            execution_time_ms=execution_time_ms,
            subtask_id=subtask_id,
            extra=extra or {},
        )

        self._append_entry(entry)
        return entry

    def record_outcome(
        self,
        subtask_id: str,
        tools_used: List[str],
        verifier_passed: bool,
        phase_type: str = "research",
        agent_role: str = "coder",
    ) -> int:
        """Close the feedback loop: link verifier result to tool records.

        Called after verification in agent_pipeline (IP-5).
        Creates entries for each tool used, with verifier_passed flag.

        Args:
            subtask_id: The subtask that was verified
            tools_used: List of tool_ids used during the subtask
            verifier_passed: Did the verifier approve?
            phase_type: Pipeline phase
            agent_role: Agent role

        Returns:
            Number of entries recorded.
        """
        count = 0
        for tool_id in tools_used:
            entry = FeedbackEntry(
                tool_id=tool_id,
                phase_type=phase_type,
                agent_role=agent_role,
                success=True,
                useful=True,
                verifier_passed=verifier_passed,
                subtask_id=subtask_id,
            )
            self._append_entry(entry)
            count += 1
        return count

    def get_score(self, tool_id: str, phase_type: str = "*") -> float:
        """Get aggregated feedback score for a tool.

        Args:
            tool_id: Tool to score
            phase_type: Filter by phase ("*" for all phases)

        Returns:
            Aggregated score 0.0-1.0, or DEFAULT_FEEDBACK_SCORE if no data.
        """
        entries = self._load_entries()
        filtered = [
            e for e in entries
            if e.tool_id == tool_id
            and (phase_type == "*" or e.phase_type == phase_type)
        ]

        if not filtered:
            return DEFAULT_FEEDBACK_SCORE

        return self._aggregate_entries(filtered).score

    def get_scores_bulk(self, phase_type: str = "*") -> Dict[str, float]:
        """Get scores for ALL tools at once. Used by Scorer to populate feedback_scores.

        Returns:
            Dict of {tool_id: score}. Missing tools get DEFAULT_FEEDBACK_SCORE.
        """
        entries = self._load_entries()
        if not entries:
            return {}

        # Group by tool_id
        groups: Dict[str, List[FeedbackEntry]] = {}
        for e in entries:
            if phase_type != "*" and e.phase_type != phase_type:
                continue
            groups.setdefault(e.tool_id, []).append(e)

        scores = {}
        for tool_id, tool_entries in groups.items():
            agg = self._aggregate_entries(tool_entries)
            scores[tool_id] = agg.score

        return scores

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the feedback log.

        Returns:
            Dict with tool_count, total_entries, top_tools, avg_success_rate, etc.
        """
        entries = self._load_entries()
        if not entries:
            return {
                "total_entries": 0,
                "tool_count": 0,
                "top_tools": [],
                "avg_success_rate": 0.0,
                "avg_usefulness_rate": 0.0,
            }

        # Group by tool
        groups: Dict[str, List[FeedbackEntry]] = {}
        for e in entries:
            groups.setdefault(e.tool_id, []).append(e)

        # Compute per-tool stats
        tool_stats = []
        total_success = 0
        total_useful = 0
        for tool_id, tool_entries in groups.items():
            successes = sum(1 for e in tool_entries if e.success)
            useful_count = sum(1 for e in tool_entries if e.useful)
            total_success += successes
            total_useful += useful_count
            tool_stats.append({
                "tool_id": tool_id,
                "count": len(tool_entries),
                "success_rate": successes / len(tool_entries),
                "usefulness_rate": useful_count / len(tool_entries),
            })

        # Sort by count descending
        tool_stats.sort(key=lambda x: x["count"], reverse=True)

        return {
            "total_entries": len(entries),
            "tool_count": len(groups),
            "top_tools": tool_stats[:10],
            "avg_success_rate": total_success / len(entries) if entries else 0.0,
            "avg_usefulness_rate": total_useful / len(entries) if entries else 0.0,
        }

    def get_feedback_summary(self) -> Dict[str, Any]:
        """MARKER_178.3.3: Summary for session_init reflex_report.

        Returns total_entries, success_rate, useful_rate, verified_rate,
        and per_tool breakdown for top tools.
        """
        entries = self._load_entries()
        if not entries:
            return {
                "total_entries": 0,
                "success_rate": 0.0,
                "useful_rate": 0.0,
                "verified_rate": 0.0,
                "per_tool": {},
                "tools": {},
            }

        total = len(entries)
        success_count = sum(1 for e in entries if e.success)
        useful_count = sum(1 for e in entries if e.useful)
        verified_count = sum(1 for e in entries if getattr(e, 'verifier_passed', None) is True)

        # Per-tool breakdown
        groups: Dict[str, List[FeedbackEntry]] = {}
        for e in entries:
            groups.setdefault(e.tool_id, []).append(e)

        per_tool = {}
        for tool_id, tool_entries in sorted(groups.items(), key=lambda x: -len(x[1]))[:10]:
            s = sum(1 for e in tool_entries if e.success)
            per_tool[tool_id] = {
                "count": len(tool_entries),
                "success_rate": round(s / len(tool_entries), 3),
            }

        return {
            "total_entries": total,
            "success_rate": round(success_count / total, 3),
            "useful_rate": round(useful_count / total, 3),
            "verified_rate": round(verified_count / total, 3) if total > 0 else 0.0,
            "per_tool": per_tool,
            "tools": per_tool,
        }

    def compact(self) -> int:
        """Compact the log: aggregate old entries, keep newest COMPACT_KEEP raw.

        Called automatically when log exceeds MAX_LOG_ENTRIES.

        Returns:
            Number of entries removed.
        """
        entries = self._load_entries()
        if len(entries) <= MAX_LOG_ENTRIES:
            return 0

        original_count = len(entries)

        # Keep newest COMPACT_KEEP entries
        entries.sort(key=lambda e: e.timestamp)
        kept = entries[-COMPACT_KEEP:]

        # Rewrite the log
        with self._lock:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "w") as f:
                for entry in kept:
                    f.write(json.dumps(entry.to_dict()) + "\n")
            self._cache = kept
            self._cache_dirty = False

        removed = original_count - len(kept)
        logger.info("[REFLEX CORTEX] Compacted log: %d → %d entries (%d removed)",
                     original_count, len(kept), removed)
        return removed

    @property
    def entry_count(self) -> int:
        """Number of entries in the log."""
        return len(self._load_entries())

    # --- Internal methods ---

    def _append_entry(self, entry: FeedbackEntry) -> None:
        """Append a single entry to the JSONL log (thread-safe)."""
        # MARKER_178.1.5: Auto-create feedback log
        if not FEEDBACK_LOG_PATH.exists():
            FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            FEEDBACK_LOG_PATH.touch()
        with self._lock:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
            # Invalidate cache
            if self._cache is not None:
                self._cache.append(entry)

        # Auto-compact if needed
        if self._cache and len(self._cache) > MAX_LOG_ENTRIES:
            self.compact()

    def _load_entries(self) -> List[FeedbackEntry]:
        """Load all entries from JSONL log. Caches in memory."""
        if self._cache is not None:
            return self._cache

        entries: List[FeedbackEntry] = []
        if not self._log_path.exists():
            self._cache = entries
            return entries

        try:
            with open(self._log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            d = json.loads(line)
                            entries.append(FeedbackEntry.from_dict(d))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning("[REFLEX CORTEX] Failed to load log: %s", e)

        self._cache = entries
        return entries

    def _aggregate_entries(self, entries: List[FeedbackEntry]) -> AggregatedScore:
        """Aggregate a list of entries into a single score.

        Formula: score = success_rate * 0.40 + usefulness * 0.35 + verifier_pass * 0.25
        Decay: MARKER_173.P5.INTEGRATE — phase-specific half-life via ReflexDecayEngine.
        Falls back to fixed DECAY_LAMBDA if engine import fails.
        """
        if not entries:
            return AggregatedScore(
                tool_id="",
                phase_type="*",
                score=DEFAULT_FEEDBACK_SCORE,
                sample_count=0,
                success_rate=0.0,
                usefulness_rate=0.0,
                verifier_rate=0.0,
            )

        # MARKER_173.P5.INTEGRATE: Use adaptive decay engine
        decay_engine = None
        try:
            from src.services.reflex_decay import ReflexDecayEngine
            decay_engine = ReflexDecayEngine()
        except ImportError:
            pass  # Fall back to fixed DECAY_LAMBDA

        now = datetime.now(timezone.utc)

        weighted_success = 0.0
        weighted_useful = 0.0
        weighted_verifier = 0.0
        total_weight = 0.0

        # Pre-compute tool success rate for success-weighted decay
        tool_success_rate = None
        if decay_engine and entries:
            successes = sum(1 for e in entries if e.success)
            tool_success_rate = successes / len(entries) if entries else None

        for entry in entries:
            # Compute age in days
            try:
                ts = datetime.fromisoformat(entry.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
            except (ValueError, TypeError):
                age_days = 0.0

            # Decay weight — use adaptive engine or fixed lambda
            if decay_engine:
                weight = decay_engine.compute_weight(
                    age_days=age_days,
                    phase_type=entry.phase_type,
                    success_rate=tool_success_rate,
                )
            else:
                weight = math.exp(-DECAY_LAMBDA * age_days)
            total_weight += weight

            weighted_success += weight * (1.0 if entry.success else 0.0)
            weighted_useful += weight * (1.0 if entry.useful else 0.0)
            weighted_verifier += weight * (1.0 if entry.verifier_passed else 0.0)

        if total_weight == 0.0:
            return AggregatedScore(
                tool_id=entries[0].tool_id,
                phase_type=entries[0].phase_type,
                score=DEFAULT_FEEDBACK_SCORE,
                sample_count=len(entries),
                success_rate=0.0,
                usefulness_rate=0.0,
                verifier_rate=0.0,
            )

        success_rate = weighted_success / total_weight
        usefulness_rate = weighted_useful / total_weight
        verifier_rate = weighted_verifier / total_weight

        score = (
            success_rate * AGG_SUCCESS_WEIGHT
            + usefulness_rate * AGG_USEFULNESS_WEIGHT
            + verifier_rate * AGG_VERIFIER_WEIGHT
        )
        score = min(1.0, max(0.0, score))

        return AggregatedScore(
            tool_id=entries[0].tool_id,
            phase_type=entries[0].phase_type,
            score=round(score, 4),
            sample_count=len(entries),
            success_rate=round(success_rate, 4),
            usefulness_rate=round(usefulness_rate, 4),
            verifier_rate=round(verifier_rate, 4),
        )

    def _invalidate_cache(self) -> None:
        """Force reload from disk on next access."""
        self._cache = None


# --- Singleton ---

_feedback_instance: Optional[ReflexFeedback] = None


def get_reflex_feedback() -> ReflexFeedback:
    """Get or create singleton ReflexFeedback."""
    global _feedback_instance
    if _feedback_instance is None:
        _feedback_instance = ReflexFeedback()
    return _feedback_instance


def reset_reflex_feedback() -> None:
    """Reset singleton (for testing)."""
    global _feedback_instance
    _feedback_instance = None
