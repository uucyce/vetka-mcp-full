"""
MARKER_126.1: Balance Tracker — unified usage and balance monitoring.

Tracks:
- Token usage per provider/key/model (from LLM responses)
- Remote balance where available (OpenRouter, Polza)
- Estimated cost based on known pricing

Singleton pattern for global access.

@status active
@phase 126.1
@depends dataclasses, json, pathlib
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from threading import Lock

logger = logging.getLogger("BALANCE_TRACKER")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
USAGE_FILE = DATA_DIR / "usage_tracking.json"

# MARKER_126.1A: Pricing per 1M tokens (approximate, 2026 rates)
PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    # Anthropic
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-haiku": {"input": 0.25, "output": 1.25},
    # Google
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # xAI
    "grok-4": {"input": 3.00, "output": 15.00},
    "grok-4-fast": {"input": 5.00, "output": 25.00},
    # Polza/Asian models (cheaper)
    "qwen": {"input": 0.50, "output": 2.00},
    "kimi": {"input": 0.80, "output": 3.00},
    "glm": {"input": 0.30, "output": 1.00},
    # Default fallback
    "_default": {"input": 1.00, "output": 3.00},
}


@dataclass
class UsageRecord:
    """MARKER_126.1B: Usage record for a provider/key combination."""
    provider: str
    key_masked: str
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    balance_usd: Optional[float] = None
    balance_limit: Optional[float] = None
    is_free_tier: bool = False
    exhausted: bool = False
    last_used: float = 0.0
    last_balance_check: float = 0.0
    created_at: float = field(default_factory=time.time)
    call_count: int = 0


class BalanceTracker:
    """
    MARKER_126.1C: Singleton tracker for all API usage and balances.

    Thread-safe with Lock for concurrent access.
    Persists to JSON for session continuity.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.records: Dict[str, UsageRecord] = {}
        self._file_lock = Lock()
        self._load()
        logger.info("[BalanceTracker] Initialized")

    def _load(self):
        """Load persisted usage data."""
        if USAGE_FILE.exists():
            try:
                data = json.loads(USAGE_FILE.read_text())
                for key, val in data.get("records", {}).items():
                    self.records[key] = UsageRecord(**val)
                logger.info(f"[BalanceTracker] Loaded {len(self.records)} records")
            except Exception as e:
                logger.error(f"[BalanceTracker] Load failed: {e}")

    def _save(self):
        """Persist usage data to disk."""
        with self._file_lock:
            try:
                data = {
                    "records": {k: asdict(v) for k, v in self.records.items()},
                    "updated_at": time.time()
                }
                USAGE_FILE.write_text(json.dumps(data, indent=2))
            except Exception as e:
                logger.error(f"[BalanceTracker] Save failed: {e}")

    def _get_key(self, provider: str, key_masked: str) -> str:
        """Generate unique key for provider+key combination."""
        return f"{provider}:{key_masked}"

    def _estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """MARKER_126.1D: Estimate cost based on known pricing."""
        model_lower = model.lower()
        pricing = None

        # Find matching pricing
        for name, rates in PRICING.items():
            if name in model_lower:
                pricing = rates
                break

        if not pricing:
            pricing = PRICING["_default"]

        cost = (tokens_in / 1_000_000) * pricing["input"]
        cost += (tokens_out / 1_000_000) * pricing["output"]
        return round(cost, 6)

    def record_usage(
        self,
        provider: str,
        key_masked: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: Optional[float] = None
    ):
        """
        MARKER_126.1E: Record usage after LLM call.

        Args:
            provider: Provider name (openai, anthropic, etc.)
            key_masked: Masked key (sk-****, pza_****)
            model: Model name used
            tokens_in: Input/prompt tokens
            tokens_out: Output/completion tokens
            cost_usd: Optional explicit cost (otherwise estimated)
        """
        key = self._get_key(provider, key_masked)

        if key not in self.records:
            self.records[key] = UsageRecord(
                provider=provider,
                key_masked=key_masked,
                model=model
            )

        r = self.records[key]
        r.tokens_in += tokens_in
        r.tokens_out += tokens_out
        r.model = model
        r.last_used = time.time()
        r.call_count += 1

        # Calculate cost
        if cost_usd is not None:
            r.cost_usd += cost_usd
        else:
            r.cost_usd += self._estimate_cost(model, tokens_in, tokens_out)

        self._save()
        logger.debug(
            f"[Balance] {provider}/{key_masked} {model}: "
            f"+{tokens_in}/{tokens_out} tokens, total ${r.cost_usd:.4f}"
        )

    def update_balance(
        self,
        provider: str,
        key_masked: str,
        balance: float,
        limit: Optional[float] = None,
        is_free_tier: bool = False,
        exhausted: bool = False
    ):
        """
        MARKER_126.1F: Update remote balance for a key (from balance API).

        Args:
            provider: Provider name
            key_masked: Masked key
            balance: Current balance in USD
            limit: Balance limit if known
            is_free_tier: Whether this is a free-tier key
            exhausted: Whether key is exhausted (402/403)
        """
        key = self._get_key(provider, key_masked)

        if key not in self.records:
            self.records[key] = UsageRecord(
                provider=provider,
                key_masked=key_masked
            )

        r = self.records[key]
        r.balance_usd = balance
        r.balance_limit = limit
        r.is_free_tier = is_free_tier
        r.exhausted = exhausted
        r.last_balance_check = time.time()

        self._save()

    def mark_exhausted(self, provider: str, key_masked: str):
        """MARKER_126.1G: Mark key as exhausted (402/403 received)."""
        key = self._get_key(provider, key_masked)
        if key in self.records:
            self.records[key].exhausted = True
            self.records[key].balance_usd = 0.0
            self._save()
            logger.info(f"[BalanceTracker] Marked {provider}/{key_masked} as exhausted")

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all usage records for API response."""
        return [asdict(r) for r in self.records.values()]

    def get_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """Get records for specific provider."""
        return [
            asdict(r) for r in self.records.values()
            if r.provider == provider
        ]

    def get_totals(self) -> Dict[str, Any]:
        """MARKER_126.1H: Get aggregated totals."""
        total_in = sum(r.tokens_in for r in self.records.values())
        total_out = sum(r.tokens_out for r in self.records.values())
        total_cost = sum(r.cost_usd for r in self.records.values())
        total_calls = sum(r.call_count for r in self.records.values())

        by_provider: Dict[str, Dict[str, Any]] = {}
        for r in self.records.values():
            if r.provider not in by_provider:
                by_provider[r.provider] = {
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "calls": 0,
                    "keys": 0
                }
            by_provider[r.provider]["tokens_in"] += r.tokens_in
            by_provider[r.provider]["tokens_out"] += r.tokens_out
            by_provider[r.provider]["cost_usd"] += r.cost_usd
            by_provider[r.provider]["calls"] += r.call_count
            by_provider[r.provider]["keys"] += 1

        return {
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "total_cost_usd": round(total_cost, 4),
            "total_calls": total_calls,
            "by_provider": by_provider,
            "records_count": len(self.records)
        }

    def reset_daily(self):
        """Reset daily counters (call at midnight or manually)."""
        for r in self.records.values():
            r.tokens_in = 0
            r.tokens_out = 0
            r.cost_usd = 0.0
            r.call_count = 0
        self._save()
        logger.info("[BalanceTracker] Daily reset complete")

    def sync_from_key_manager(self) -> int:
        """
        MARKER_126.3D: Sync all keys from UnifiedKeyManager.

        Creates UsageRecord for ALL configured keys, not just used ones.
        Updates status (available, exhausted) from KeyManager state.

        Returns:
            Number of keys synced
        """
        try:
            from src.utils.unified_key_manager import get_key_manager
            km = get_key_manager()

            synced = 0
            for provider_key, key_records in km.keys.items():
                # Get provider name as string
                provider_name = provider_key.value if hasattr(provider_key, 'value') else str(provider_key)

                for record in key_records:
                    key_masked = record.mask()
                    tracker_key = self._get_key(provider_name, key_masked)

                    # Create record if doesn't exist
                    if tracker_key not in self.records:
                        self.records[tracker_key] = UsageRecord(
                            provider=provider_name,
                            key_masked=key_masked
                        )

                    # Update from KeyManager state
                    r = self.records[tracker_key]

                    # Sync availability status
                    if not record.is_available():
                        r.exhausted = True
                    elif r.exhausted and record.is_available():
                        # Key recovered from cooldown
                        r.exhausted = False

                    # Sync balance info from APIKeyRecord
                    if record.balance is not None:
                        r.balance_usd = record.balance
                    if record.balance_limit is not None:
                        r.balance_limit = record.balance_limit

                    synced += 1

            self._save()
            logger.info(f"[BalanceTracker] Synced {synced} keys from KeyManager")
            return synced

        except Exception as e:
            logger.error(f"[BalanceTracker] Sync failed: {e}")
            return 0


# MARKER_126.1I: Singleton accessor
_tracker: Optional[BalanceTracker] = None


def get_balance_tracker() -> BalanceTracker:
    """Get singleton BalanceTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = BalanceTracker()
    return _tracker
