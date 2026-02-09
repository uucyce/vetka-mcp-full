# Phase 126: Balance System Fix

**Date:** 2026-02-09
**Status:** IMPLEMENTATION READY
**Priority:** P1
**Source:** Phase 117 bugs + Grok research

---

## Problem Summary

| Bug | Symptom | Root Cause |
|-----|---------|------------|
| BUG-1 | OpenRouter shows $9999.79 | Parsing `limit_remaining` as balance (it's credit limit) |
| BUG-2 | Balance bar always 0% | `percent` not computed in API response |
| BUG-3 | No balance for Gemini/xAI/Anthropic | No public balance endpoints |
| BUG-4 | 402 doesn't zero balance | `report_failure()` doesn't update balance |
| BUG-5 | Same balance for all provider keys | Single fetch per provider, not per key |

---

## Architecture Overview

```
Current Flow (broken):

GET /api/keys/balance
    └── fetch_provider_balance("openrouter")
            └── GET openrouter.ai/api/v1/auth/key (ONE key)
                    └── parse limit_remaining as balance  ← WRONG
                            └── return to ALL keys       ← WRONG


Target Flow:

GET /api/keys/balance
    └── for EACH key:
            fetch_provider_balance(provider, key_index)
                └── GET provider API
                        └── detect free_tier → balance=0
                        └── paid → balance=limit_remaining
                        └── compute percent
                        └── return per-key data

+ on 402/403:
    report_failure(key) → set balance=0 immediately
```

---

## Files to Modify

| File | Marker | Changes |
|------|--------|---------|
| `src/utils/unified_key_manager.py` | MARKER_126.1 | Fix OpenRouter parse, add per-key fetch, 402→balance=0 |
| `src/api/routes/config_routes.py` | MARKER_126.2 | Compute percent, return per-key balances |
| `src/elisya/provider_registry.py` | MARKER_126.3 | Zero balance on 402/403 in _report_key_failure |
| `client/src/components/ModelDirectory.tsx` | MARKER_126.4 | Handle per-key balance data |

---

## MARKER_126.1: unified_key_manager.py

### 126.1A: Fix OpenRouter Balance Parse

**Location:** `fetch_provider_balance()` lines 461-480

**Current (broken):**
```python
'openrouter': {
    'url': 'https://openrouter.ai/api/v1/auth/key',
    'auth': 'Bearer',
    'parse': lambda data: {
        'balance': data.get('data', {}).get('limit_remaining'),  # WRONG
        'limit': data.get('data', {}).get('limit'),
        'used': data.get('data', {}).get('usage')
    }
},
```

**Fixed (MARKER_126.1A):**
```python
'openrouter': {
    'url': 'https://openrouter.ai/api/v1/auth/key',
    'auth': 'Bearer',
    'parse': lambda data: _parse_openrouter_balance(data)
},
```

**Add helper function before BALANCE_ENDPOINTS:**
```python
# MARKER_126.1A: OpenRouter balance parser with free-tier detection
def _parse_openrouter_balance(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse OpenRouter /api/v1/auth/key response correctly.

    Free-tier keys have:
      - limit: null (no spending limit)
      - limit_remaining: 9999.xx (max credit, NOT real money)
      - usage: 0.xx (actual spend)
      - is_free_tier: true

    Paid keys have:
      - limit: 50.0 (actual spending cap)
      - limit_remaining: 35.42 (remaining within cap)
      - usage: 14.58 (actual spend)
    """
    d = data.get('data', {})

    limit = d.get('limit')  # null for free-tier
    limit_remaining = d.get('limit_remaining', 0)
    usage = d.get('usage', 0)
    is_free_tier = d.get('is_free_tier', limit is None)

    if is_free_tier:
        # Free-tier: no real balance, only usage tracking
        return {
            'balance': 0.0,
            'limit': 0.0,
            'used': usage,
            'is_free_tier': True,
            'exhausted': usage > 0  # Any usage means free credits used
        }
    else:
        # Paid: limit_remaining is actual balance
        return {
            'balance': limit_remaining,
            'limit': limit or 0,
            'used': usage,
            'is_free_tier': False,
            'exhausted': limit_remaining <= 0
        }
```

### 126.1B: Per-Key Balance Fetch

**Location:** After `fetch_provider_balance()`, add new method

```python
# MARKER_126.1B: Fetch balance for specific key by index
async def fetch_key_balance(self, provider: str, key_index: int = 0) -> Optional[Dict[str, Any]]:
    """
    Fetch balance for a specific key, not just the active one.

    Args:
        provider: Provider name (openrouter, polza, etc.)
        key_index: Index of key in provider's key list

    Returns:
        Balance data dict or None
    """
    import httpx

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

    endpoint = BALANCE_ENDPOINTS.get(provider)
    if not endpoint:
        return None

    # Get specific key by index
    provider_key = self._get_provider_key(provider)
    keys = self.keys.get(provider_key, [])
    if key_index >= len(keys):
        return None

    record = keys[key_index]
    key = record.key

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            headers = {'Authorization': f'{endpoint["auth"]} {key}'}
            resp = await client.get(endpoint['url'], headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                parsed = endpoint['parse'](data)

                # Update record
                record.balance = parsed.get('balance')
                record.balance_limit = parsed.get('limit')
                record.balance_updated_at = datetime.now()

                # Compute percent
                if record.balance is not None and record.balance_limit and record.balance_limit > 0:
                    parsed['percent'] = round((record.balance / record.balance_limit) * 100, 1)
                else:
                    parsed['percent'] = 0.0

                parsed['key_index'] = key_index
                parsed['key_masked'] = record.mask()
                return parsed

            elif resp.status_code in (402, 403):
                # MARKER_126.1C: Payment required or forbidden - zero balance
                record.balance = 0.0
                record.balance_updated_at = datetime.now()
                return {
                    'balance': 0.0,
                    'limit': record.balance_limit or 0,
                    'used': 0,
                    'percent': 0.0,
                    'exhausted': True,
                    'error': f'HTTP {resp.status_code}',
                    'key_index': key_index,
                    'key_masked': record.mask()
                }
            else:
                return {'error': f'HTTP {resp.status_code}', 'key_index': key_index}

    except Exception as e:
        logger.warning(f"[MARKER_126.1B] Balance fetch failed for {provider}[{key_index}]: {e}")
        return {'error': str(e), 'key_index': key_index}
```

### 126.1C: Zero Balance on 402/403

**Location:** In `report_failure()` method, after `record.mark_rate_limited()`

```python
def report_failure(self, key: str, mark_cooldown: bool = True, auto_rotate: bool = True,
                   status_code: Optional[int] = None):
    """
    Report key failure and optionally rotate to next key.

    MARKER_126.1C: If status_code is 402/403, zero the balance.
    """
    for provider, provider_keys in self.keys.items():
        for record in provider_keys:
            if record.key == key:
                if mark_cooldown:
                    record.mark_rate_limited()
                else:
                    record.failure_count += 1

                # MARKER_126.1C: Payment required - zero balance immediately
                if status_code in (402, 403):
                    record.balance = 0.0
                    record.balance_updated_at = datetime.now()
                    logger.info(f"[MARKER_126.1C] Zeroed balance for {record.mask()} after {status_code}")

                # ... rest of rotation logic
```

---

## MARKER_126.2: config_routes.py

### 126.2A: Per-Key Balance Endpoint

**Location:** Replace `get_keys_balance()` at line 598

```python
@router.get("/keys/balance")
async def get_keys_balance():
    """
    MARKER_126.2A: Get balance for ALL keys, not just one per provider.
    Returns per-key balance with computed percent.
    """
    from src.utils.unified_key_manager import get_key_manager
    km = get_key_manager()

    result = {}

    # Providers with balance API support
    balance_providers = ['openrouter', 'polza']

    for provider_name in balance_providers:
        provider_key = km._get_provider_key(provider_name)
        keys = km.keys.get(provider_key, [])

        if not keys:
            continue

        key_balances = []
        for idx, record in enumerate(keys):
            try:
                balance_data = await km.fetch_key_balance(provider_name, idx)
                if balance_data:
                    key_balances.append(balance_data)
            except Exception as e:
                key_balances.append({
                    'error': str(e),
                    'key_index': idx,
                    'key_masked': record.mask()
                })

        result[provider_name] = {
            'keys': key_balances,
            'total_balance': sum(kb.get('balance', 0) for kb in key_balances if 'balance' in kb),
            'keys_count': len(keys),
            'exhausted_count': sum(1 for kb in key_balances if kb.get('exhausted', False))
        }

    return {'success': True, 'balances': result}
```

---

## MARKER_126.3: provider_registry.py

### 126.3A: Pass Status Code to report_failure

**Location:** Line 1218, in error handling

**Current:**
```python
self._report_key_failure(key, mark_cooldown=mark_cooldown)
```

**Fixed:**
```python
# MARKER_126.3A: Pass status code for balance zeroing
self._report_key_failure(key, mark_cooldown=mark_cooldown, status_code=response.status_code)
```

### 126.3B: Update _report_key_failure Signature

**Location:** Line 1105

```python
def _report_key_failure(self, key: str, mark_cooldown: bool = True, status_code: Optional[int] = None):
    """Report key failure and auto-rotate to next key if available."""
    from src.utils.unified_key_manager import get_key_manager

    km = get_key_manager()
    # MARKER_126.3B: Pass status_code to zero balance on 402/403
    km.report_failure(key, mark_cooldown=mark_cooldown, auto_rotate=True, status_code=status_code)
```

---

## MARKER_126.4: ModelDirectory.tsx

### 126.4A: Handle Per-Key Balance Data

**Location:** `fetchBalances()` callback, line 421

**Current (broken):**
```typescript
const balanceData = data.balances[provider.provider];
if (!balanceData || balanceData.error) {
  return provider;
}

const updatedKeys = provider.keys.map((key) => ({
  ...key,
  balance: balanceData.balance,        // Same for all keys
  balance_limit: balanceData.limit,    // Same for all keys
  balance_percent: balanceData.percent,
}));
```

**Fixed (MARKER_126.4A):**
```typescript
const fetchBalances = useCallback(async () => {
  try {
    const res = await fetch('/api/keys/balance');
    const data = await res.json();
    if (!data.success || !data.balances) return;

    setProviders((prevProviders) =>
      prevProviders.map((provider) => {
        const providerData = data.balances[provider.provider];
        if (!providerData?.keys) {
          return provider;
        }

        // MARKER_126.4A: Match balance to each key by index
        const updatedKeys = provider.keys.map((key, idx) => {
          const keyBalance = providerData.keys.find(
            (kb: any) => kb.key_index === idx || kb.key_masked === key.key
          );

          if (!keyBalance || keyBalance.error) {
            return key;
          }

          return {
            ...key,
            balance: keyBalance.balance,
            balance_limit: keyBalance.limit,
            balance_percent: keyBalance.percent,
            is_free_tier: keyBalance.is_free_tier,
            exhausted: keyBalance.exhausted,
          };
        });

        return { ...provider, keys: updatedKeys };
      })
    );
  } catch (err) {
    console.error('[ModelDirectory] Failed to fetch balances:', err);
  }
}, []);
```

### 126.4B: Visual Indicator for Exhausted Keys

**Location:** Balance bar render, around line 1416

```typescript
{/* MARKER_126.4B: Balance bar with exhausted state */}
<div style={{
  width: '100%',
  height: 3,
  background: '#1a1a1a',
  borderRadius: 2,
  overflow: 'hidden',
}}>
  <div style={{
    width: `${Math.min(apiKey.balance_percent || 0, 100)}%`,
    height: '100%',
    background: apiKey.exhausted
      ? '#f66'  // Red for exhausted
      : (apiKey.balance_percent || 0) > 20
        ? '#7ab3d4'  // VETKA blue for healthy
        : '#555',    // Dim for low
    transition: 'width 0.3s ease',
  }} />
</div>
<span style={{
  fontSize: 8,
  color: apiKey.exhausted ? '#f66' : '#666',
  fontFamily: 'monospace',
  whiteSpace: 'nowrap',
}}>
  {apiKey.is_free_tier
    ? 'FREE'
    : typeof apiKey.balance === 'number'
      ? `$${apiKey.balance.toFixed(2)}`
      : '—'}
</span>
```

---

## New File: BalanceTracker (Optional Enhancement)

**Location:** `src/orchestration/balance_tracker.py`

For usage tracking after each LLM call:

```python
"""
MARKER_126.5: Balance Tracker for real-time usage monitoring.
Tracks tokens and estimated cost after each LLM call.
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger("BALANCE_TRACKER")

BALANCES_FILE = Path(__file__).parent.parent.parent / "data" / "usage_tracking.json"


@dataclass
class UsageRecord:
    provider: str
    key_masked: str
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    last_updated: float = 0.0


class BalanceTracker:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.records: Dict[str, UsageRecord] = {}
        self._load()

    def _load(self):
        if BALANCES_FILE.exists():
            try:
                data = json.loads(BALANCES_FILE.read_text())
                for key, val in data.items():
                    self.records[key] = UsageRecord(**val)
            except Exception as e:
                logger.error(f"[BalanceTracker] Load failed: {e}")

    def _save(self):
        try:
            data = {k: asdict(v) for k, v in self.records.items()}
            BALANCES_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"[BalanceTracker] Save failed: {e}")

    def record_usage(self, provider: str, key_masked: str, model: str,
                     tokens_in: int, tokens_out: int, cost_usd: float = 0.0):
        """Call after each LLM response."""
        key = f"{provider}_{key_masked}"

        if key not in self.records:
            self.records[key] = UsageRecord(provider=provider, key_masked=key_masked, model=model)

        r = self.records[key]
        r.tokens_in += tokens_in
        r.tokens_out += tokens_out
        r.cost_usd += cost_usd
        r.model = model
        r.last_updated = time.time()

        self._save()

    def get_all(self) -> list:
        return [asdict(r) for r in self.records.values()]

    def get_total_cost(self) -> float:
        return sum(r.cost_usd for r in self.records.values())


_tracker = None

def get_balance_tracker() -> BalanceTracker:
    global _tracker
    if _tracker is None:
        _tracker = BalanceTracker()
    return _tracker
```

---

## Implementation Order

1. **unified_key_manager.py** — MARKER_126.1A,B,C (core fix)
2. **config_routes.py** — MARKER_126.2A (API response)
3. **provider_registry.py** — MARKER_126.3A,B (402 handling)
4. **ModelDirectory.tsx** — MARKER_126.4A,B (UI update)
5. **balance_tracker.py** — MARKER_126.5 (optional usage tracking)

---

## Test Scenarios

| Test | Expected |
|------|----------|
| OpenRouter free-tier key | balance=0, is_free_tier=true |
| OpenRouter paid key with $15.42 | balance=15.42, percent=30.8 |
| Key gets 402 | balance zeroed immediately |
| 3 keys for same provider | 3 different balances returned |
| Polza with $5.00 balance | balance=5.00, percent=50 |

---

## Markers Index

| Marker | File | Description |
|--------|------|-------------|
| MARKER_126.1A | unified_key_manager.py | OpenRouter free-tier detection |
| MARKER_126.1B | unified_key_manager.py | Per-key balance fetch |
| MARKER_126.1C | unified_key_manager.py | Zero balance on 402/403 |
| MARKER_126.2A | config_routes.py | Per-key balance API response |
| MARKER_126.3A | provider_registry.py | Pass status_code to failure handler |
| MARKER_126.3B | provider_registry.py | Updated _report_key_failure signature |
| MARKER_126.4A | ModelDirectory.tsx | Per-key balance UI handling |
| MARKER_126.4B | ModelDirectory.tsx | Exhausted key visual indicator |
| MARKER_126.5 | balance_tracker.py | Optional usage tracking service |

---

**Report by:** Claude Opus 4.5
**Total markers:** 9
**Estimated effort:** 3-4 hours
