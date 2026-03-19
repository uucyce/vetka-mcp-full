"""
REFLEX Feedback Guard — Pre-call safety gate for tool execution.

MARKER_193.1.GUARD

Layer 0 of REFLEX: checks danger rules BEFORE a tool is called or recommended.
Three rule sources: ENGRAM L1 danger entries, CORTEX failure history, static JSON.

Flow:
  1. check_tool(tool_id, context) → GuardResult(allowed, warnings, blocked_reason)
  2. filter_recommendations(recs, context) → recs with 'warning'/'blocked' fields
  3. get_active_dangers(agent_type, phase_type) → matching DangerRule list

On ANY error: log warning, return safe (allowed=True). Never break the pipeline.

Part of VETKA OS:
  VETKA > REFLEX > Guard (this file)

@status: active
@phase: 193.1
@depends: engram_cache, reflex_feedback
@used_by: reflex_integration (IP-6, IP-7), fc_loop (IP-8 pre-call gate)
"""

import fnmatch
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Feature flag: guard enabled by default when REFLEX is enabled
REFLEX_GUARD_ENABLED = os.getenv("REFLEX_GUARD_ENABLED", "true").lower() in ("true", "1", "yes")

# CORTEX failure thresholds for auto-warn
# MARKER_193.7: Raised min_calls from 3→10 to avoid false positives
# from noisy CORTEX feedback (e.g., vetka_read_file "fails" when file not found)
_FAILURE_MIN_CALLS = int(os.getenv("REFLEX_GUARD_MIN_CALLS", "10"))
_FAILURE_MAX_SUCCESS_RATE = float(os.getenv("REFLEX_GUARD_MAX_SUCCESS_RATE", "0.15"))

# Static rules file path (relative to project root)
_RULES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "reflex_guard_rules.json",
)


@dataclass
class DangerRule:
    """A single danger rule that can block/warn/demote a tool.

    tool_pattern: glob pattern — "preview_start" or "preview_*"
    context_pattern: glob for project/phase — "CUT" or "*"
    reason: human-readable explanation
    source: "engram_l1" | "cortex_failure" | "static_rules"
    severity: "block" | "warn" | "demote"
    created_at: unix timestamp
    """
    tool_pattern: str
    context_pattern: str
    reason: str
    source: str
    severity: str = "warn"
    created_at: float = field(default_factory=time.time)

    def matches_tool(self, tool_id: str) -> bool:
        """Check if tool_id matches this rule's tool_pattern (glob)."""
        return fnmatch.fnmatch(tool_id, self.tool_pattern)

    def matches_context(self, context: "GuardContext") -> bool:
        """Check if context matches this rule's context_pattern (glob).

        Checks against project_id, phase_type, and combined string.
        A match on ANY component counts.
        """
        if self.context_pattern == "*":
            return True
        pat = self.context_pattern.lower()
        # Match against each component individually
        candidates = [
            context.project_id.lower() if context.project_id else "",
            context.phase_type.lower() if context.phase_type else "",
            context.context_str.lower(),
        ]
        return any(fnmatch.fnmatch(c, pat) for c in candidates if c)


@dataclass
class GuardContext:
    """Context for guard evaluation — what agent/phase/project is active."""
    agent_type: str = ""
    phase_type: str = ""
    project_id: str = ""

    @property
    def context_str(self) -> str:
        """Combined context string for pattern matching."""
        parts = [p for p in (self.project_id, self.phase_type) if p]
        return "/".join(parts) if parts else "*"


@dataclass
class GuardResult:
    """Result of a guard check on a single tool."""
    allowed: bool = True
    warnings: List[str] = field(default_factory=list)
    blocked_reason: str = ""
    matched_rules: List[DangerRule] = field(default_factory=list)


class FeedbackGuard:
    """MARKER_193.1.GUARD — Pre-call safety gate for REFLEX tool recommendations.

    Checks three sources of danger rules before allowing tool execution:
    1. ENGRAM L1 danger entries (hard blocks from user feedback)
    2. CORTEX failure history (tools with >3 calls and <20% success → warn)
    3. Static rules from data/reflex_guard_rules.json (user-defined)

    Thread-safe singleton via get_feedback_guard().
    """

    def __init__(self) -> None:
        self._danger_rules: List[DangerRule] = []
        self._cortex_cache: Dict[str, Dict[str, Any]] = {}
        self._cortex_cache_ts: float = 0.0
        self._cortex_cache_ttl: float = 60.0  # refresh every 60s
        self._load_danger_rules()

    def check_tool(self, tool_id: str, context: GuardContext) -> GuardResult:
        """Check if a tool is safe to use in the given context.

        Returns GuardResult with allowed=False if any 'block' rule matches,
        or warnings for 'warn'/'demote' rules.
        """
        if not REFLEX_GUARD_ENABLED:
            return GuardResult()

        result = GuardResult()

        # Check static + ENGRAM rules
        for rule in self._danger_rules:
            if rule.matches_tool(tool_id) and rule.matches_context(context):
                result.matched_rules.append(rule)
                if rule.severity == "block":
                    result.allowed = False
                    result.blocked_reason = f"BLOCKED: {rule.reason} (source: {rule.source})"
                else:
                    result.warnings.append(f"WARNING: {rule.reason} (source: {rule.source})")

        # Check CORTEX failure history (dynamic)
        cortex_result = self._check_cortex_failures(tool_id, context)
        if cortex_result:
            result.matched_rules.append(cortex_result)
            result.warnings.append(
                f"WARNING: {cortex_result.reason} (source: {cortex_result.source})"
            )

        return result

    def filter_recommendations(
        self, recs: List[Dict], context: GuardContext
    ) -> List[Dict]:
        """Filter/annotate recommendation list with guard results.

        For each rec dict:
        - blocked tools: adds 'blocked'=True, 'blocked_reason'=str, removes from list
        - warned tools: adds 'warning'=str
        - demoted tools: reduces 'score' by 50%

        Returns new list (blocked tools excluded).
        """
        if not REFLEX_GUARD_ENABLED:
            return recs

        filtered: List[Dict] = []
        for rec in recs:
            tool_id = rec.get("tool_id", "")
            result = self.check_tool(tool_id, context)

            if not result.allowed:
                # Blocked — exclude from recommendations
                rec_copy = dict(rec)
                rec_copy["blocked"] = True
                rec_copy["blocked_reason"] = result.blocked_reason
                logger.info("[GUARD] Blocked recommendation: %s — %s", tool_id, result.blocked_reason)
                continue  # Don't add to filtered list

            if result.warnings:
                rec = dict(rec)
                rec["warning"] = "; ".join(result.warnings)
                # Demote score for warned tools
                for rule in result.matched_rules:
                    if rule.severity == "demote":
                        rec["score"] = round(rec.get("score", 0.0) * 0.5, 4)

            filtered.append(rec)

        return filtered

    def get_active_dangers(
        self, agent_type: str = "*", phase_type: str = "*"
    ) -> List[DangerRule]:
        """Get all active danger rules matching the given context."""
        if not REFLEX_GUARD_ENABLED:
            return []

        ctx = GuardContext(agent_type=agent_type, phase_type=phase_type)

        active: List[DangerRule] = []

        # Static + ENGRAM rules
        for rule in self._danger_rules:
            if rule.matches_context(ctx):
                active.append(rule)

        # Add CORTEX-derived rules
        cortex_rules = self._get_cortex_danger_rules()
        for rule in cortex_rules:
            if rule.matches_context(ctx):
                active.append(rule)

        return active

    def reload_rules(self) -> int:
        """Force reload of all danger rules. Returns count loaded."""
        self._danger_rules.clear()
        self._cortex_cache.clear()
        self._cortex_cache_ts = 0.0
        self._load_danger_rules()
        return len(self._danger_rules)

    def add_rule(self, rule: DangerRule) -> None:
        """Add a danger rule at runtime (e.g., from auto-promote)."""
        # Avoid duplicates
        for existing in self._danger_rules:
            if (existing.tool_pattern == rule.tool_pattern
                    and existing.context_pattern == rule.context_pattern
                    and existing.source == rule.source):
                return
        self._danger_rules.append(rule)
        logger.info("[GUARD] Added rule: %s → %s (%s)", rule.tool_pattern, rule.severity, rule.reason)

    # ─── Private: Rule Loading ───────────────────────────────────

    def _load_danger_rules(self) -> None:
        """Load rules from all static sources (ENGRAM L1 + JSON file)."""
        self._load_engram_dangers()
        self._load_static_rules()
        if self._danger_rules:
            logger.info("[GUARD] Loaded %d danger rules", len(self._danger_rules))

    def _load_engram_dangers(self) -> None:
        """Source 1: ENGRAM L1 entries with category='danger' → block rules."""
        try:
            from src.memory.engram_cache import get_engram_cache
            cache = get_engram_cache()
            all_entries = cache.get_all()

            for _key, entry in all_entries.items():
                cat = entry.get("category", "default")
                if cat != "danger":
                    continue

                # Parse tool_pattern from key, context from value
                key = entry.get("key", "")
                value = entry.get("value", "")

                # Convention: key = tool_pattern, value = "reason | context_pattern"
                # Or value = just reason (context_pattern = "*")
                parts = value.split("|", 1)
                reason = parts[0].strip()
                context_pattern = parts[1].strip() if len(parts) > 1 else "*"

                if key and reason:
                    self._danger_rules.append(DangerRule(
                        tool_pattern=key,
                        context_pattern=context_pattern,
                        reason=reason,
                        source="engram_l1",
                        severity="block",
                        created_at=entry.get("created_at", time.time()),
                    ))

        except Exception as e:
            logger.debug("[GUARD] Failed to load ENGRAM dangers: %s", e)

    def _load_static_rules(self) -> None:
        """Source 3: Static rules from data/reflex_guard_rules.json."""
        try:
            if not os.path.exists(_RULES_FILE):
                return

            with open(_RULES_FILE, "r") as f:
                data = json.load(f)

            rules = data.get("rules", [])
            for r in rules:
                tool_pattern = r.get("tool_pattern", "")
                if not tool_pattern:
                    continue

                self._danger_rules.append(DangerRule(
                    tool_pattern=tool_pattern,
                    context_pattern=r.get("context_pattern", "*"),
                    reason=r.get("reason", "Static guard rule"),
                    source="static_rules",
                    severity=r.get("severity", "warn"),
                    created_at=r.get("created_at", time.time()),
                ))

        except Exception as e:
            logger.debug("[GUARD] Failed to load static rules from %s: %s", _RULES_FILE, e)

    # ─── Private: CORTEX Failure Checks ──────────────────────────

    def _refresh_cortex_cache(self) -> None:
        """Refresh CORTEX per-tool stats cache if stale."""
        now = time.time()
        if now - self._cortex_cache_ts < self._cortex_cache_ttl:
            return

        try:
            from src.services.reflex_feedback import get_reflex_feedback
            fb = get_reflex_feedback()
            summary = fb.get_feedback_summary()
            self._cortex_cache = summary.get("per_tool", {})
            self._cortex_cache_ts = now
        except Exception as e:
            logger.debug("[GUARD] Failed to refresh CORTEX cache: %s", e)

    def _check_cortex_failures(self, tool_id: str, context: GuardContext) -> Optional[DangerRule]:
        """Source 2: Check if tool has high failure rate in CORTEX.

        Returns a DangerRule (severity='warn') if:
        - call_count >= _FAILURE_MIN_CALLS (default 3)
        - success_rate < _FAILURE_MAX_SUCCESS_RATE (default 0.2)
        """
        self._refresh_cortex_cache()

        stats = self._cortex_cache.get(tool_id)
        if not stats:
            return None

        count = stats.get("count", 0)
        success_rate = stats.get("success_rate", 1.0)

        if count >= _FAILURE_MIN_CALLS and success_rate < _FAILURE_MAX_SUCCESS_RATE:
            return DangerRule(
                tool_pattern=tool_id,
                context_pattern="*",
                reason=f"Low success rate: {success_rate:.0%} over {count} calls",
                source="cortex_failure",
                severity="warn",
                created_at=time.time(),
            )

        return None

    def _get_cortex_danger_rules(self) -> List[DangerRule]:
        """Get all CORTEX-derived danger rules (tools with high failure rate)."""
        self._refresh_cortex_cache()

        rules: List[DangerRule] = []
        for tool_id, stats in self._cortex_cache.items():
            count = stats.get("count", 0)
            success_rate = stats.get("success_rate", 1.0)

            if count >= _FAILURE_MIN_CALLS and success_rate < _FAILURE_MAX_SUCCESS_RATE:
                rules.append(DangerRule(
                    tool_pattern=tool_id,
                    context_pattern="*",
                    reason=f"Low success rate: {success_rate:.0%} over {count} calls",
                    source="cortex_failure",
                    severity="warn",
                    created_at=time.time(),
                ))

        return rules


# ─── Singleton ───────────────────────────────────────────────────

_guard_instance: Optional[FeedbackGuard] = None


def get_feedback_guard() -> FeedbackGuard:
    """Get or create the FeedbackGuard singleton."""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = FeedbackGuard()
    return _guard_instance
