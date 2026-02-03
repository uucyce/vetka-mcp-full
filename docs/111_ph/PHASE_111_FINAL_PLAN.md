# Phase 111: Implementation Plan
## Doctor Tool + Refresh UI + NEW Markers + Quota Display

**Date:** 2026-02-03
**Status:** VERIFIED - Ready for Implementation
**Methodology:** 9 Haiku scouts + 1 Sonnet verifier

---

## Executive Summary

All reconnaissance complete. Sonnet verified critical paths with exact line numbers.

### Implementation Tasks (Priority Order)

| # | Task | File | Lines | Complexity |
|---|------|------|-------|------------|
| 1 | check_api_keys_health() | doctor_tool.py | Insert at 192 | Medium |
| 2 | POST /refresh endpoint | model_routes.py | Insert at 193 | Low |
| 3 | Refresh button UI | ModelDirectory.tsx | Header section | Low |
| 4 | NEW markers | ModelDirectory.tsx | Model list item | Low |
| 5 | Polza capitalization | model_fetcher.py | Line 111 | Trivial |
| 6 | Quota fetcher (optional) | NEW: quota_fetcher.py | - | Medium |

---

## Part 1: Doctor Tool Key Validation

### File: `src/mcp/tools/doctor_tool.py`

**Insert at Line 192** (after check_deepseek_health, before check_mcp_bridge_health):

```python
async def check_api_keys_health(self) -> HealthCheckResult:
    """
    Check API keys status and availability.

    Phase 111: Validates configured API keys for all providers.
    Returns DEGRADED if any provider has no available keys.
    """
    start = time.time()

    try:
        from src.utils.unified_key_manager import get_key_manager

        km = get_key_manager()
        stats = km.get_stats()

        issues = []
        providers_checked = 0
        providers_healthy = 0

        for provider, info in stats.get('providers', {}).items():
            providers_checked += 1
            key_count = info.get('count', 0)
            available = info.get('available', 0)

            if key_count == 0:
                issues.append(f"No keys configured for {provider}")
            elif available == 0:
                issues.append(f"{provider}: all {key_count} keys rate-limited")
            else:
                providers_healthy += 1

        # Determine overall status
        if not issues:
            status = HealthStatus.HEALTHY
            message = f"All {providers_checked} providers healthy with {stats.get('total_keys', 0)} keys"
        elif providers_healthy > 0:
            status = HealthStatus.DEGRADED
            message = f"{providers_healthy}/{providers_checked} providers healthy"
        else:
            status = HealthStatus.UNHEALTHY
            message = "No available API keys"

        duration = (time.time() - start) * 1000

        return HealthCheckResult(
            component="api_keys",
            status=status,
            message=message,
            duration_ms=duration,
            details={
                'total_keys': stats.get('total_keys', 0),
                'providers_checked': providers_checked,
                'providers_healthy': providers_healthy,
                'rate_limited_keys': stats.get('rate_limited', 0)
            },
            remediation=issues if issues else None
        )

    except Exception as e:
        duration = (time.time() - start) * 1000
        return HealthCheckResult(
            component="api_keys",
            status=HealthStatus.UNKNOWN,
            message=f"Failed to check keys: {str(e)}",
            duration_ms=duration,
            remediation=["Check unified_key_manager configuration"]
        )
```

**Modify Line 260** (in run_diagnostic):
```python
# Add after line 259 (deepseek check)
results.append(await self.check_api_keys_health())
```

---

## Part 2: Refresh Endpoint

### File: `src/api/routes/model_routes.py`

**Insert at Line 193** (after get_model_status endpoint):

```python
@router.post("/refresh")
async def refresh_model_cache(provider: Optional[str] = None):
    """
    Force refresh model cache.

    Phase 111: Manual cache invalidation for model discovery.
    Bypasses 24-hour cache to fetch latest models.

    Args:
        provider: Optional provider to refresh (openrouter, gemini, polza)
                  If None, refreshes all providers.

    Returns:
        success: bool
        count: number of models after refresh
        new_count: number of newly discovered models (if tracked)
    """
    from src.elisya.model_fetcher import get_all_models, load_cache

    # Get old count for comparison
    old_cache = load_cache()
    old_count = len(old_cache.get('models', [])) if old_cache else 0
    old_ids = {m['id'] for m in old_cache.get('models', [])} if old_cache else set()

    # Force refresh
    models = await get_all_models(force_refresh=True)

    # Calculate new models
    new_ids = {m['id'] for m in models}
    new_count = len(new_ids - old_ids)

    return {
        "success": True,
        "count": len(models),
        "previous_count": old_count,
        "new_count": new_count,
        "message": f"Refreshed: {len(models)} models ({'+' if new_count > 0 else ''}{new_count} new)"
    }
```

---

## Part 3: Refresh Button UI

### File: `client/src/components/ModelDirectory.tsx`

**Add to imports (top of file):**
```tsx
import { RefreshCw } from 'lucide-react';
```

**Add state (after other useState):**
```tsx
const [isRefreshing, setIsRefreshing] = useState(false);
```

**Add handler function:**
```tsx
const handleRefresh = useCallback(async () => {
  setIsRefreshing(true);
  try {
    const res = await fetch('/api/models/refresh', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      // Reload models list
      await fetchModels();
      // Show toast or notification
      console.log(`[ModelDirectory] ${data.message}`);
    }
  } catch (err) {
    console.error('[ModelDirectory] Refresh failed:', err);
  } finally {
    setIsRefreshing(false);
  }
}, [fetchModels]);
```

**Add button to header section (Lines 451-518, after search input):**
```tsx
<button
  onClick={handleRefresh}
  disabled={isRefreshing}
  style={{
    background: 'transparent',
    border: 'none',
    padding: 6,
    cursor: isRefreshing ? 'wait' : 'pointer',
    opacity: isRefreshing ? 0.5 : 1,
    display: 'flex',
    alignItems: 'center'
  }}
  title="Refresh model list"
>
  <RefreshCw
    size={16}
    color="#666"
    style={{
      animation: isRefreshing ? 'spin 1s linear infinite' : 'none'
    }}
  />
</button>
```

---

## Part 4: NEW Markers

### File: `client/src/components/ModelDirectory.tsx`

**Add helper function:**
```tsx
// NEW marker logic - show for models created within 7 days
const isNewModel = (model: Model): boolean => {
  if (!model.created) return false;
  const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60;
  const now = Date.now() / 1000; // Unix timestamp
  return (now - model.created) < SEVEN_DAYS_SECONDS;
};
```

**Add to model display (in model list item, after model name):**
```tsx
{/* Model name */}
<span style={{ fontSize: 13, color: '#e0e0e0' }}>{model.name}</span>

{/* NEW marker - Phase 111 */}
{isNewModel(model) && (
  <span style={{
    fontSize: 9,
    color: '#fff',
    background: '#333',
    padding: '1px 4px',
    borderRadius: 2,
    marginLeft: 6,
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  }}>
    NEW
  </span>
)}
```

---

## Part 5: Polza Capitalization

### File: `src/elisya/model_fetcher.py`

**Change Line 111:**
```python
# Before:
'provider': 'polza',

# After:
'provider': 'Polza',
```

**Also Line 175 (fallback scraper):**
```python
# Before:
'provider': 'polza',

# After:
'provider': 'Polza',
```

---

## Part 6: Quota Display (Optional - P3)

### New File: `src/elisya/quota_fetcher.py`

```python
"""
Phase 111: Quota fetcher for API providers.

Fetches usage/quota information from providers with public APIs.
Currently supports: OpenRouter

Usage:
    from src.elisya.quota_fetcher import get_provider_quota
    quota = await get_provider_quota('openrouter', api_key)
"""

import aiohttp
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


async def get_openrouter_quota(api_key: str) -> Dict[str, Any]:
    """
    Fetch quota from OpenRouter /auth/key endpoint.

    Returns:
        {
            'usage': float,        # Total usage in tokens
            'limit': float | None, # Credit limit (None = unlimited)
            'is_free': bool,       # Free tier status
            'rate_limits': {
                'rpm': int,        # Requests per minute
                'tpm': int         # Tokens per minute
            }
        }
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://openrouter.ai/api/v1/auth/key',
                headers={'Authorization': f'Bearer {api_key}'}
            ) as resp:
                if resp.status != 200:
                    return {'error': f'API returned {resp.status}'}

                data = await resp.json()
                key_data = data.get('data', {})

                return {
                    'usage': key_data.get('usage', 0),
                    'limit': key_data.get('credit_limit'),
                    'is_free': key_data.get('is_free_tier', True),
                    'rate_limits': {
                        'rpm': key_data.get('rate_limit_requests_per_minute', 60),
                        'tpm': key_data.get('rate_limit_tokens_per_minute', 300000)
                    }
                }
    except Exception as e:
        logger.error(f"Failed to fetch OpenRouter quota: {e}")
        return {'error': str(e)}


async def get_provider_quota(provider: str, api_key: str) -> Dict[str, Any]:
    """
    Get quota for any supported provider.

    Args:
        provider: Provider name (openrouter, gemini, etc.)
        api_key: API key for the provider

    Returns:
        Quota info dict or error dict
    """
    provider = provider.lower()

    if provider == 'openrouter':
        return await get_openrouter_quota(api_key)

    # Other providers don't have public quota APIs
    return {
        'supported': False,
        'message': f'{provider} does not have a public quota API'
    }
```

---

## Verification Checklist

After implementation, verify:

- [ ] `GET /health/deep` shows api_keys component
- [ ] `POST /api/models/refresh` returns model count + new_count
- [ ] Refresh button shows spinner during refresh
- [ ] NEW badge appears on models < 7 days old
- [ ] Polza displays as "Polza" (capitalized)
- [ ] No regressions in model selection
- [ ] No regressions in API key saving

---

## Test Commands

```bash
# Test doctor tool
curl http://localhost:5001/health/deep | jq '.results[] | select(.component == "api_keys")'

# Test refresh endpoint
curl -X POST http://localhost:5001/api/models/refresh | jq

# Check Polza models
curl http://localhost:5001/api/models | jq '.[] | select(.provider == "Polza")'
```

---

## Summary

**Total Changes:**
- 2 Python files modified (doctor_tool.py, model_routes.py)
- 1 Python file trivial change (model_fetcher.py)
- 1 React component modified (ModelDirectory.tsx)
- 1 New Python file (quota_fetcher.py - optional)

**Estimated Effort:** 1-2 hours for core features, +1 hour for quota display

**Risk:** Low - all changes are additive, no breaking changes

---

**Plan created by:** Claude Opus (Architect)
**Verified by:** Sonnet agent (ac7b99b)
**Status:** APPROVED FOR IMPLEMENTATION
