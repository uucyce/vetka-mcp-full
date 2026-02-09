ЦУ для Курсора (Phase 126.1 Balance Tracker):
	1	Следуй плану из docs/126_phCur/PHASE_126_BALANCE_SYSTEM.md точно как написано
	2	Маркеры: MARKER_126.1 через MARKER_126.7 — ставь в код
	3	Стиль UI: Nolan monochrome! Палитра: #111, #222, #333, #e0e0e0, #888, #666. Никакого цвета кроме белого/серого. Цветные акценты ТОЛЬКО для статуса (красный=ошибка, зелёный=ок) и только приглушённые (#2a3a2a, #3a2a2a)
	4	НЕ трогай: DevPanel.tsx уже переписан в 126.0 с табами. Добавь новую вкладку 'balance' в массив TABS и тип Tab
	5	Тесты: напиши tests/test_phase126_1_balance_tracker.py по образцу test_phase126_0_pipeline_stats.py — source-based assertions + marker checks
	6	Endpoint: добавь в debug_routes.py (не в config_routes.py) — там уже все debug endpoints
	7	НЕ используй внешние библиотеки для UI — только CSS, как в PipelineStats.tsx

А я (Claude Code Desktop) тем временем займусь стилем кнопок.





# Phase 126: Unified Balance & Usage Tracking System

**Date:** 2026-02-09
**Status:** IMPLEMENTATION READY
**Priority:** P1

---

## Problem Statement

1. OpenRouter показывает фейковый баланс ($9999.79 вместо реального)
2. Нет трекинга usage для провайдеров без balance API
3. Нет единой панели для мониторинга расходов
4. 402/403 ошибки не обнуляют баланс

---

## Provider Capability Matrix

| Provider | Balance API | Usage in Response | Cost Tracking | Notes |
|----------|-------------|-------------------|---------------|-------|
| OpenRouter | /api/v1/auth/key | prompt_tokens, completion_tokens | limit_remaining (paid only) | Free-tier shows fake $9999 |
| Polza | /api/v1/account/balance | prompt_tokens, completion_tokens | balance field | Works correctly |
| OpenAI | No public endpoint | prompt_tokens, completion_tokens | Via usage response | Track locally |
| Anthropic | No public endpoint | input_tokens, output_tokens | Via usage response | Track locally |
| Google/Gemini | No public endpoint | promptTokenCount, candidatesTokenCount | Via usage response | Track locally |
| xAI/Grok | No public endpoint | prompt_tokens, completion_tokens | Via usage response | Track locally |
| Mistral | No public endpoint | prompt_tokens, completion_tokens | Via usage response | Track locally |
| Ollama | N/A (local) | prompt_eval_count, eval_count | Free | Local models |
| Poe | No public endpoint | prompt_tokens, completion_tokens | Via usage response | Aggregator |
| NanoGPT | No public endpoint | prompt_tokens, completion_tokens | Via usage response | Aggregator |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     UNIFIED BALANCE SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐      ┌──────────────────┐      ┌────────────────┐ │
│  │  LLM Call Tool   │      │  Provider Calls  │      │  Balance APIs  │ │
│  │  (llm_call_tool) │      │  (registry.call) │      │  (OpenRouter)  │ │
│  └────────┬─────────┘      └────────┬─────────┘      └───────┬────────┘ │
│           │                         │                        │          │
│           │  usage response         │  usage response        │  balance │
│           └──────────┬──────────────┘                        │          │
│                      │                                       │          │
│                      ▼                                       ▼          │
│           ┌──────────────────────────────────────────────────────────┐  │
│           │                  BalanceTracker                          │  │
│           │  ┌─────────────────────────────────────────────────────┐ │  │
│           │  │ UsageRecord {                                       │ │  │
│           │  │   provider, key_masked, model,                      │ │  │
│           │  │   tokens_in, tokens_out, cost_usd,                  │ │  │
│           │  │   balance_usd, last_updated                         │ │  │
│           │  │ }                                                   │ │  │
│           │  └─────────────────────────────────────────────────────┘ │  │
│           │                                                          │  │
│           │  Methods:                                                │  │
│           │  - record_usage(provider, key, model, in, out, cost)    │  │
│           │  - update_balance(provider, key, balance)               │  │
│           │  - get_all() → List[UsageRecord]                        │  │
│           │  - get_totals() → {tokens, cost, by_provider}           │  │
│           └──────────────────────────────────────────────────────────┘  │
│                      │                                                  │
│                      ▼                                                  │
│           ┌──────────────────────────────────────────────────────────┐  │
│           │              /api/usage/balances                         │  │
│           │  Returns: usage per key + remote balance where available │  │
│           └──────────────────────────────────────────────────────────┘  │
│                      │                                                  │
│                      ▼                                                  │
│           ┌──────────────────────────────────────────────────────────┐  │
│           │              DevPanel: Balances Tab                       │  │
│           │  ┌────────────────────────────────────────────────────┐  │  │
│           │  │ Provider │ Key  │ Model │ In   │ Out  │ Cost │ Bal │  │  │
│           │  │ openai   │ sk** │ gpt-4 │ 12k  │ 8k   │ $0.42│  -  │  │  │
│           │  │ openrtr  │ sk** │ claude│ 45k  │ 22k  │ $1.20│$15  │  │  │
│           │  │ polza    │ pza* │ grok  │ 8k   │ 5k   │ $0.08│$4.2 │  │  │
│           │  └────────────────────────────────────────────────────┘  │  │
│           └──────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Files to Create/Modify

| File | Action | Marker |
|------|--------|--------|
| src/services/balance_tracker.py | CREATE | MARKER_126.1 |
| src/mcp/tools/llm_call_tool.py | MODIFY | MARKER_126.2 |
| src/utils/unified_key_manager.py | MODIFY | MARKER_126.3 |
| src/elisya/provider_registry.py | MODIFY | MARKER_126.4 |
| src/api/routes/config_routes.py | MODIFY | MARKER_126.5 |
| client/src/components/dev/BalancesPanel.tsx | CREATE | MARKER_126.6 |
| client/src/components/dev/DevPanel.tsx | MODIFY | MARKER_126.7 |

---

## MARKER_126.1: BalanceTracker Service

**File:** `src/services/balance_tracker.py`

```python
"""
MARKER_126.1: Balance Tracker — unified usage and balance monitoring.

Tracks:
- Token usage per provider/key/model (from LLM responses)
- Remote balance where available (OpenRouter, Polza)
- Estimated cost based on known pricing

Singleton pattern for global access.
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from threading import Lock

logger = logging.getLogger("BALANCE_TRACKER")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
USAGE_FILE = DATA_DIR / "usage_tracking.json"

# Pricing per 1M tokens (approximate, 2026 rates)
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
    # Default fallback
    "_default": {"input": 1.00, "output": 3.00},
}


@dataclass
class UsageRecord:
    """Usage record for a provider/key combination."""
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


class BalanceTracker:
    """
    Singleton tracker for all API usage and balances.

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
        """Estimate cost based on known pricing."""
        # Normalize model name
        model_lower = model.lower()
        pricing = None
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
        Record usage after LLM call.

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
        r.model = model  # Update to last used model
        r.last_used = time.time()

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
        Update remote balance for a key (from balance API).

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
        """Mark key as exhausted (402/403 received)."""
        key = self._get_key(provider, key_masked)
        if key in self.records:
            self.records[key].exhausted = True
            self.records[key].balance_usd = 0.0
            self._save()

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
        """Get aggregated totals."""
        total_in = sum(r.tokens_in for r in self.records.values())
        total_out = sum(r.tokens_out for r in self.records.values())
        total_cost = sum(r.cost_usd for r in self.records.values())

        by_provider = {}
        for r in self.records.values():
            if r.provider not in by_provider:
                by_provider[r.provider] = {
                    "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "keys": 0
                }
            by_provider[r.provider]["tokens_in"] += r.tokens_in
            by_provider[r.provider]["tokens_out"] += r.tokens_out
            by_provider[r.provider]["cost_usd"] += r.cost_usd
            by_provider[r.provider]["keys"] += 1

        return {
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "total_cost_usd": round(total_cost, 4),
            "by_provider": by_provider,
            "records_count": len(self.records)
        }

    def reset_daily(self):
        """Reset daily counters (call at midnight or manually)."""
        for r in self.records.values():
            r.tokens_in = 0
            r.tokens_out = 0
            r.cost_usd = 0.0
        self._save()
        logger.info("[BalanceTracker] Daily reset complete")


# Singleton accessor
_tracker: Optional[BalanceTracker] = None

def get_balance_tracker() -> BalanceTracker:
    global _tracker
    if _tracker is None:
        _tracker = BalanceTracker()
    return _tracker
```

---

## MARKER_126.2: LLM Call Tool Integration

**File:** `src/mcp/tools/llm_call_tool.py`

**Location:** After line 873, where `_emit_response_to_chat` is called

```python
# MARKER_126.2: Track usage in BalanceTracker
def _track_usage(self, provider: str, model: str, usage: Optional[Dict], key_masked: str = "****"):
    """Record usage to BalanceTracker after successful LLM call."""
    if not usage:
        return

    try:
        from src.services.balance_tracker import get_balance_tracker
        tracker = get_balance_tracker()

        # Normalize token field names (different providers use different names)
        tokens_in = (
            usage.get('prompt_tokens') or
            usage.get('input_tokens') or
            usage.get('promptTokenCount') or
            usage.get('prompt_eval_count') or
            0
        )
        tokens_out = (
            usage.get('completion_tokens') or
            usage.get('output_tokens') or
            usage.get('candidatesTokenCount') or
            usage.get('eval_count') or
            0
        )

        tracker.record_usage(
            provider=provider,
            key_masked=key_masked,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out
        )
    except Exception as e:
        logger.debug(f"[MARKER_126.2] Usage tracking failed: {e}")
```

**Insert at line ~874:**

```python
            # MARKER_90.4.0_START: Emit response to VETKA chat
            self._emit_response_to_chat(model, content, result.get('usage'))
            # MARKER_90.4.0_END

            # MARKER_126.2: Track usage for balance monitoring
            self._track_usage(
                provider=provider_name or "unknown",
                model=model,
                usage=result.get('usage'),
                key_masked=self._get_current_key_masked(provider_name)
            )
```

**Add helper method:**

```python
def _get_current_key_masked(self, provider: str) -> str:
    """Get masked version of current active key for provider."""
    try:
        from src.utils.unified_key_manager import get_key_manager
        km = get_key_manager()
        key = km.get_key(provider)
        if key and len(key) > 8:
            return f"{key[:4]}****{key[-4:]}"
        return "****"
    except:
        return "****"
```

---

## MARKER_126.3: OpenRouter Balance Fix

**File:** `src/utils/unified_key_manager.py`

**Replace BALANCE_ENDPOINTS section (lines 461-480):**

```python
# MARKER_126.3A: OpenRouter balance parser with free-tier detection
def _parse_openrouter_balance(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse OpenRouter /api/v1/auth/key response correctly.

    Free-tier:
      limit: null, limit_remaining: 9999.xx (NOT real money), is_free_tier: true

    Paid:
      limit: 50.0, limit_remaining: 35.42 (actual balance)
    """
    d = data.get('data', {})

    limit = d.get('limit')
    limit_remaining = d.get('limit_remaining', 0)
    usage = d.get('usage', 0)
    is_free_tier = d.get('is_free_tier', limit is None)

    if is_free_tier:
        return {
            'balance': 0.0,
            'limit': 0.0,
            'used': usage,
            'is_free_tier': True,
            'exhausted': usage > 0
        }
    else:
        return {
            'balance': limit_remaining,
            'limit': limit or 0,
            'used': usage,
            'is_free_tier': False,
            'exhausted': limit_remaining <= 0
        }


# MARKER_126.3B: Balance endpoints configuration
BALANCE_ENDPOINTS = {
    'openrouter': {
        'url': 'https://openrouter.ai/api/v1/auth/key',
        'auth': 'Bearer',
        'parse': _parse_openrouter_balance
    },
    'polza': {
        'url': 'https://api.polza.ai/api/v1/account/balance',
        'auth': 'Bearer',
        'parse': lambda data: {
            'balance': data.get('balance', 0),
            'limit': data.get('limit', 0),
            'used': data.get('used', 0),
            'is_free_tier': False,
            'exhausted': data.get('balance', 0) <= 0
        }
    }
}
```

**Modify `fetch_provider_balance` to update BalanceTracker (after line 506):**

```python
                    # MARKER_126.3C: Update BalanceTracker with remote balance
                    try:
                        from src.services.balance_tracker import get_balance_tracker
                        tracker = get_balance_tracker()
                        tracker.update_balance(
                            provider=provider,
                            key_masked=record.mask(),
                            balance=parsed.get('balance', 0),
                            limit=parsed.get('limit'),
                            is_free_tier=parsed.get('is_free_tier', False),
                            exhausted=parsed.get('exhausted', False)
                        )
                    except Exception as e:
                        logger.debug(f"[MARKER_126.3C] Tracker update failed: {e}")
```

**Modify `report_failure` to handle 402/403 (add parameter and logic):**

```python
def report_failure(self, key: str, mark_cooldown: bool = True,
                   auto_rotate: bool = True, status_code: Optional[int] = None):
    """
    Report key failure and optionally rotate to next key.

    MARKER_126.3D: If status_code is 402/403, zero the balance.
    """
    for provider, provider_keys in self.keys.items():
        for record in provider_keys:
            if record.key == key:
                if mark_cooldown:
                    record.mark_rate_limited()
                else:
                    record.failure_count += 1

                # MARKER_126.3D: Payment required - zero balance
                if status_code in (402, 403):
                    record.balance = 0.0
                    record.balance_updated_at = datetime.now()
                    logger.info(f"[MARKER_126.3D] Zeroed balance for {record.mask()}")

                    # Update tracker
                    try:
                        from src.services.balance_tracker import get_balance_tracker
                        tracker = get_balance_tracker()
                        tracker.mark_exhausted(
                            provider=provider.value if hasattr(provider, 'value') else str(provider),
                            key_masked=record.mask()
                        )
                    except:
                        pass

                # ... rest of rotation logic unchanged
```

---

## MARKER_126.4: Provider Registry 402 Handling

**File:** `src/elisya/provider_registry.py`

**Line 1218, pass status_code:**

```python
# MARKER_126.4A: Pass status code for balance zeroing
self._report_key_failure(key, mark_cooldown=mark_cooldown, status_code=response.status_code)
```

**Line 1105, update signature:**

```python
def _report_key_failure(self, key: str, mark_cooldown: bool = True,
                        status_code: Optional[int] = None):
    """Report key failure and auto-rotate to next key if available."""
    from src.utils.unified_key_manager import get_key_manager

    km = get_key_manager()
    # MARKER_126.4B: Pass status_code for 402/403 handling
    km.report_failure(key, mark_cooldown=mark_cooldown, auto_rotate=True,
                      status_code=status_code)
```

---

## MARKER_126.5: API Endpoint

**File:** `src/api/routes/config_routes.py`

**Add new endpoint after `/keys/balance`:**

```python
@router.get("/usage/balances")
async def get_usage_balances():
    """
    MARKER_126.5: Get unified usage and balance data.

    Returns:
        - records: Per-key usage (tokens, cost, balance where available)
        - totals: Aggregated by provider
        - providers_with_balance: Which providers have remote balance API
    """
    from src.services.balance_tracker import get_balance_tracker
    from src.utils.unified_key_manager import get_key_manager

    tracker = get_balance_tracker()
    km = get_key_manager()

    # Refresh remote balances for supported providers
    for provider in ['openrouter', 'polza']:
        try:
            await km.fetch_provider_balance(provider)
        except Exception as e:
            logger.debug(f"Balance refresh failed for {provider}: {e}")

    return {
        'success': True,
        'records': tracker.get_all(),
        'totals': tracker.get_totals(),
        'providers_with_balance': ['openrouter', 'polza'],
        'timestamp': time.time()
    }


@router.post("/usage/reset")
async def reset_usage():
    """MARKER_126.5B: Reset daily usage counters."""
    from src.services.balance_tracker import get_balance_tracker
    tracker = get_balance_tracker()
    tracker.reset_daily()
    return {'success': True, 'message': 'Usage counters reset'}
```

---

## MARKER_126.6: BalancesPanel Component

**File:** `client/src/components/dev/BalancesPanel.tsx`

```tsx
/**
 * MARKER_126.6: BalancesPanel — unified usage and balance monitoring.
 * Style: monochrome, minimal, data-focused.
 */

import { useState, useEffect, useCallback } from 'react';

interface UsageRecord {
  provider: string;
  key_masked: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  balance_usd: number | null;
  balance_limit: number | null;
  is_free_tier: boolean;
  exhausted: boolean;
  last_used: number;
}

interface Totals {
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_usd: number;
  by_provider: Record<string, {
    tokens_in: number;
    tokens_out: number;
    cost_usd: number;
    keys: number;
  }>;
}

export function BalancesPanel() {
  const [records, setRecords] = useState<UsageRecord[]>([]);
  const [totals, setTotals] = useState<Totals | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/usage/balances');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success) {
        setRecords(data.records || []);
        setTotals(data.totals || null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleReset = async () => {
    if (!confirm('Reset all usage counters?')) return;
    try {
      await fetch('/api/usage/reset', { method: 'POST' });
      fetchData();
    } catch (err) {
      console.error('Reset failed:', err);
    }
  };

  const formatTokens = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
    return n.toString();
  };

  const formatTime = (ts: number) => {
    if (!ts) return '-';
    return new Date(ts * 1000).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div style={{ padding: 16, fontSize: 12, color: '#ccc' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
        paddingBottom: 12,
        borderBottom: '1px solid #222'
      }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#ddd' }}>
            Usage & Balances
          </div>
          {totals && (
            <div style={{ color: '#666', marginTop: 4 }}>
              Total: {formatTokens(totals.total_tokens_in)} in,{' '}
              {formatTokens(totals.total_tokens_out)} out,{' '}
              <span style={{ color: '#c66' }}>${totals.total_cost_usd.toFixed(4)}</span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={handleReset}
            style={{
              padding: '5px 10px',
              background: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: 3,
              color: '#888',
              fontSize: 11,
              cursor: 'pointer'
            }}
          >
            Reset
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            style={{
              padding: '5px 10px',
              background: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: 3,
              color: '#aaa',
              fontSize: 11,
              cursor: 'pointer'
            }}
          >
            {loading ? '...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ color: '#c66', marginBottom: 12 }}>Error: {error}</div>
      )}

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #222', color: '#666' }}>
              <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Provider</th>
              <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Key</th>
              <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Model</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500 }}>In</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500 }}>Out</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500 }}>Cost</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500 }}>Balance</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500 }}>Last</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => (
              <tr
                key={i}
                style={{
                  borderBottom: '1px solid #1a1a1a',
                  opacity: r.exhausted ? 0.5 : 1
                }}
              >
                <td style={{ padding: '8px 0', color: '#aaa' }}>{r.provider}</td>
                <td style={{ padding: '8px 0', fontFamily: 'monospace', color: '#666' }}>
                  {r.key_masked}
                </td>
                <td style={{ padding: '8px 0', color: '#888' }}>
                  {r.model ? r.model.split('/').pop() : '-'}
                </td>
                <td style={{ padding: '8px 0', textAlign: 'right', color: '#5a7' }}>
                  {formatTokens(r.tokens_in)}
                </td>
                <td style={{ padding: '8px 0', textAlign: 'right', color: '#7a9' }}>
                  {formatTokens(r.tokens_out)}
                </td>
                <td style={{ padding: '8px 0', textAlign: 'right', color: '#c66' }}>
                  ${r.cost_usd.toFixed(4)}
                </td>
                <td style={{ padding: '8px 0', textAlign: 'right' }}>
                  {r.is_free_tier ? (
                    <span style={{ color: '#666' }}>FREE</span>
                  ) : r.exhausted ? (
                    <span style={{ color: '#c66' }}>$0.00</span>
                  ) : r.balance_usd !== null ? (
                    <span style={{ color: r.balance_usd > 5 ? '#6a8' : '#ca6' }}>
                      ${r.balance_usd.toFixed(2)}
                    </span>
                  ) : (
                    <span style={{ color: '#444' }}>-</span>
                  )}
                </td>
                <td style={{ padding: '8px 0', textAlign: 'right', color: '#555' }}>
                  {formatTime(r.last_used)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {records.length === 0 && !loading && (
        <div style={{ textAlign: 'center', color: '#555', padding: 40 }}>
          No usage data. Run LLM calls to populate.
        </div>
      )}

      {/* Provider Summary */}
      {totals && Object.keys(totals.by_provider).length > 0 && (
        <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #222' }}>
          <div style={{ fontSize: 11, color: '#666', marginBottom: 8 }}>By Provider</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            {Object.entries(totals.by_provider).map(([provider, data]) => (
              <div
                key={provider}
                style={{
                  padding: '8px 12px',
                  background: '#111',
                  borderRadius: 4,
                  border: '1px solid #222'
                }}
              >
                <div style={{ color: '#aaa', fontWeight: 500 }}>{provider}</div>
                <div style={{ color: '#666', fontSize: 10, marginTop: 4 }}>
                  {formatTokens(data.tokens_in + data.tokens_out)} tokens,{' '}
                  <span style={{ color: '#c66' }}>${data.cost_usd.toFixed(4)}</span>,{' '}
                  {data.keys} keys
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## MARKER_126.7: DevPanel Tab Integration

**File:** `client/src/components/dev/DevPanel.tsx`

**Add import:**

```tsx
import { BalancesPanel } from './BalancesPanel';
```

**Update tab type:**

```tsx
const [activeTab, setActiveTab] = useState<'tasks' | 'stats' | 'leagues' | 'balances'>('tasks');
```

**Add tab button and content:**

```tsx
// In tabs array:
{(['tasks', 'stats', 'leagues', 'balances'] as const).map(tab => (
  // ... existing button code
))}

// In content section:
{activeTab === 'balances' && <BalancesPanel />}
```

---

## Implementation Order

1. Create `src/services/balance_tracker.py` (MARKER_126.1)
2. Modify `src/mcp/tools/llm_call_tool.py` (MARKER_126.2)
3. Modify `src/utils/unified_key_manager.py` (MARKER_126.3)
4. Modify `src/elisya/provider_registry.py` (MARKER_126.4)
5. Modify `src/api/routes/config_routes.py` (MARKER_126.5)
6. Create `client/src/components/dev/BalancesPanel.tsx` (MARKER_126.6)
7. Modify `client/src/components/dev/DevPanel.tsx` (MARKER_126.7)

---

## Markers Index

| Marker | File | Description |
|--------|------|-------------|
| 126.1 | balance_tracker.py | BalanceTracker singleton service |
| 126.2 | llm_call_tool.py | Usage tracking after LLM calls |
| 126.3A | unified_key_manager.py | OpenRouter free-tier detection |
| 126.3B | unified_key_manager.py | Balance endpoints config |
| 126.3C | unified_key_manager.py | Tracker update on balance fetch |
| 126.3D | unified_key_manager.py | Zero balance on 402/403 |
| 126.4A | provider_registry.py | Pass status_code to failure handler |
| 126.4B | provider_registry.py | Updated method signature |
| 126.5 | config_routes.py | /api/usage/balances endpoint |
| 126.5B | config_routes.py | /api/usage/reset endpoint |
| 126.6 | BalancesPanel.tsx | UI component |
| 126.7 | DevPanel.tsx | Tab integration |

---

## Test Scenarios

| Test | Input | Expected |
|------|-------|----------|
| OpenRouter free-tier | limit=null | balance=0, is_free_tier=true |
| OpenRouter paid | limit=50, remaining=35 | balance=35, percent=70 |
| Key gets 402 | HTTP 402 response | balance=0, exhausted=true |
| Anthropic call | claude-sonnet-4 | Usage tracked, no remote balance |
| Multiple keys | 3 OpenRouter keys | 3 separate records |
| Cost estimation | gpt-4o 1000 in, 500 out | ~$0.0075 |
| Reset daily | POST /api/usage/reset | All counters = 0 |

---

**Total markers:** 12
**New files:** 2
**Modified files:** 5
**Estimated effort:** 4-5 hours

---

**Report by:** Claude Opus 4.5
