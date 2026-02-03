# Phase 111: Reconnaissance Report
## Haiku Scouts Synthesis - Doctor Tool + Refresh UI + NEW Markers + Quota Display

**Date:** 2026-02-03
**Methodology:** 9 Haiku scouts (parallel reconnaissance)
**Status:** RECONNAISSANCE COMPLETE - Ready for Verification

---

## Executive Summary

Phase 111 targets P2 features from the Phase 110 audit:
1. **Doctor Tool** - Add `check_api_keys_health()` for key validation
2. **Refresh Button** - Per-provider or global model refresh in UI
3. **NEW Markers** - Show recently added models (7-day window)
4. **Polza UI** - Consistent display naming
5. **Quota Display** - Show usage/balance in SAVED KEYS section

### Scout Summary Matrix

| Scout | Target | Key Finding | Action Required |
|-------|--------|-------------|-----------------|
| 1 | ModelDirectory.tsx | NO refresh button, NO NEW markers | ADD both |
| 2 | model_routes.py | NO /refresh endpoint | ADD endpoint |
| 3 | model_fetcher.py | `created` field exists, no `is_new` | ADD is_new logic |
| 4 | doctor_tool.py | NO check_api_keys_health() | IMPLEMENT |
| 5 | SAVED KEYS UI | NO quota display | ADD quota bar |
| 6 | key_handlers.py | NO quota in socket responses | EXTEND |
| 7 | Quota APIs | OpenRouter has /auth/key endpoint | IMPLEMENT fetcher |
| 8 | model_registry.py | NO refresh_provider() method | ADD method |
| 9 | Toast/Spinner | Custom CSS animations exist | REUSE patterns |

---

## Part 1: Current Architecture Gaps

### 1.1 Doctor Tool - Missing Key Validation

**File:** `src/mcp/tools/doctor_tool.py`

**Current Health Checks:**
- `check_ollama_health()` ✓ (Lines 70-136)
- `check_deepseek_health()` ✓ (Lines 138-191)
- `check_mcp_bridge_health()` ✓ (Lines 193-238)
- `check_api_keys_health()` ❌ **MISSING**

**Implementation Blueprint:**
```python
async def check_api_keys_health(self) -> HealthCheckResult:
    """Check API keys status and validity."""
    from src.utils.unified_key_manager import get_key_manager

    km = get_key_manager()
    stats = km.get_stats()

    # Check each provider has at least one working key
    issues = []
    for provider, info in stats['providers'].items():
        if info['count'] == 0:
            issues.append(f"No keys for {provider}")
        elif info.get('all_rate_limited'):
            issues.append(f"{provider}: all keys rate-limited")

    status = HealthStatus.HEALTHY if not issues else HealthStatus.DEGRADED

    return HealthCheckResult(
        component="api_keys",
        status=status,
        message=f"{stats['total_keys']} keys across {stats['provider_count']} providers",
        duration_ms=0,
        details=stats,
        remediation=issues if issues else None
    )
```

---

### 1.2 Refresh Button - Missing Infrastructure

**Frontend:** `client/src/components/ModelDirectory.tsx`
- NO refresh button exists (Scout 1)
- Auto-fetch on open only (Lines 152-205)
- 60-second status polling (Lines 208-222)

**Backend:** `src/api/routes/model_routes.py`
- NO `/refresh` endpoint (Scout 2)
- `force_refresh` param exists in model_fetcher but NOT exposed

**Required Changes:**

1. **Add Backend Endpoint:**
```python
# model_routes.py
@router.post("/refresh")
async def refresh_models(provider: Optional[str] = None, force: bool = True):
    """Force refresh model cache."""
    if provider:
        models = await refresh_provider(provider)
    else:
        models = await get_all_models(force_refresh=force)
    return {'status': 'refreshed', 'count': len(models)}
```

2. **Add Frontend Button:**
```tsx
// ModelDirectory.tsx - Header section
<button onClick={handleRefresh} disabled={isRefreshing}>
  {isRefreshing ? <Loader2 className="animate-spin" /> : <RefreshCw />}
</button>
```

---

### 1.3 NEW Markers - Implementation Plan

**Current State (Scout 3):**
- `created` Unix timestamp exists in models_cache.json
- NO `is_new` field
- NO `added_at` tracking

**Implementation Options:**

**Option A: Calculate on-the-fly (RECOMMENDED - Minimal changes)**
```tsx
// ModelDirectory.tsx
const isNew = (model) => {
  const SEVEN_DAYS = 7 * 24 * 60 * 60; // seconds
  return (Date.now() / 1000 - model.created) < SEVEN_DAYS;
};
```

**Option B: Add to save_cache() (More robust)**
```python
# model_fetcher.py - save_cache()
def save_cache(models, source='mixed'):
    current_time = time.time()
    for model in models:
        model['is_new'] = (current_time - model.get('created', 0)) < 604800
    # ...save
```

**UI Display (per Phase 111 spec):**
```tsx
{isNew(model) && (
  <span style={{ color: '#fff', fontSize: 9, marginLeft: 4 }}>NEW</span>
)}
```

---

### 1.4 Polza UI Consistency

**Current Display (Scout 1):**
- Provider: `"polza"` (lowercase)
- Source: `"polza_direct"` or `"polza_scraped"`
- NOT in DUAL_SOURCE_MODELS (no xAI/OR dual display)

**Options:**

1. **Keep as-is:** Display "polza" like other providers
2. **Capitalize:** Change to "Polza" in model_fetcher.py line 111
3. **Add suffix:** "Polza (POLZA)" or "Polza via POLZA"

**Recommendation:** Option 2 - Simple capitalization for consistency:
```python
# model_fetcher.py line 111
'provider': 'Polza',  # Was 'polza'
```

---

### 1.5 Quota Display in SAVED KEYS

**Current State (Scout 5):**
- `APIKeyInfo` interface has: id, provider, key, status
- NO quota fields
- NO usage display

**Provider Quota APIs (Scout 7):**

| Provider | Endpoint | Response |
|----------|----------|----------|
| OpenRouter | GET /api/v1/auth/key | `{ usage, credit_limit, is_free_tier }` |
| Gemini | (no direct API) | N/A |
| Anthropic | (no direct API) | N/A |

**Implementation Plan:**

1. **Create quota_fetcher.py:**
```python
async def get_openrouter_quota(api_key: str) -> dict:
    """Fetch quota from OpenRouter /auth/key endpoint."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            'https://openrouter.ai/api/v1/auth/key',
            headers={'Authorization': f'Bearer {api_key}'}
        ) as resp:
            data = await resp.json()
            return {
                'usage': data.get('data', {}).get('usage', 0),
                'limit': data.get('data', {}).get('credit_limit'),
                'is_free': data.get('data', {}).get('is_free_tier', True)
            }
```

2. **Add to key_handlers.py response:**
```python
# Extend key_status response
{
    'providers': {
        'openrouter': {
            'count': 13,
            'active': True,
            'quota': {  # NEW
                'usage': 12345,
                'limit': None,
                'remaining': 'unlimited'
            }
        }
    }
}
```

3. **UI Component:**
```tsx
{apiKey.quota && (
  <div style={{ fontSize: 9, color: '#666' }}>
    {apiKey.quota.remaining === 'unlimited'
      ? '∞ tokens'
      : `${apiKey.quota.remaining} left`}
  </div>
)}
```

---

## Part 2: File Change Matrix

| File | Changes | Priority |
|------|---------|----------|
| `src/mcp/tools/doctor_tool.py` | Add check_api_keys_health() | P2 |
| `src/api/routes/model_routes.py` | Add POST /refresh endpoint | P2 |
| `src/elisya/model_fetcher.py` | Add is_new to save_cache() | P2 |
| `client/src/components/ModelDirectory.tsx` | Add Refresh button + NEW markers | P2 |
| `src/elisya/quota_fetcher.py` | NEW FILE - quota fetching | P2 |
| `src/api/handlers/key_handlers.py` | Extend key_status with quota | P2 |

---

## Part 3: UI Components Available

**Toast/Spinner (Scout 9):**
- Lucide `<Loader2>` with CSS spin animation ✓
- Custom `@keyframes slideIn` for notifications ✓
- ActivityMonitor has Socket.IO real-time updates ✓
- Color scheme: `#4aff9e` (success), `#4a9eff` (active)

**Example Refresh Toast:**
```tsx
const showRefreshToast = (newCount: number) => {
  // Use existing ActivityMonitor pattern
  setToast({
    message: `Updated: +${newCount} new models`,
    type: 'success',
    duration: 4000
  });
};
```

---

## Part 4: Implementation Order

### Step 1: Doctor Tool Key Validation
- Add `check_api_keys_health()` to doctor_tool.py
- Integrate with existing health check flow
- Test via `/health/deep` endpoint

### Step 2: Refresh Endpoint
- Add `POST /api/models/refresh` to model_routes.py
- Support `?provider=openrouter` for targeted refresh
- Return count of refreshed models

### Step 3: Refresh Button UI
- Add button to ModelDirectory.tsx header
- Use Lucide `RefreshCw` icon
- Show spinner during refresh
- Toast notification on complete

### Step 4: NEW Markers
- Calculate from `created` timestamp
- 7-day window
- White text badge (monochrome theme)

### Step 5: Polza Display
- Capitalize provider name
- No other changes needed

### Step 6: Quota Display (if time permits)
- Create quota_fetcher.py
- OpenRouter only (has public API)
- Add to SAVED KEYS section

---

## Part 5: Verification Checklist

After implementation, verify:

- [ ] Doctor Tool shows key health in diagnostics
- [ ] Refresh button triggers model list refresh
- [ ] NEW marker appears on models < 7 days old
- [ ] Polza displays as "Polza" (capitalized)
- [ ] OpenRouter quota shows in SAVED KEYS (optional)
- [ ] Toast shows "Updated: +X new" on refresh
- [ ] No regressions in existing functionality

---

## Appendix: Scout Agent IDs

For resuming if needed:
- Scout 1 (ModelDirectory): `a8223d5`
- Scout 2 (model_routes): `a5ab133`
- Scout 3 (model_fetcher): `a99241a`
- Scout 4 (doctor_tool): `aa7e9bc`
- Scout 5 (SAVED KEYS): `a8bf2a5`
- Scout 6 (key_handlers): `ae05ed8`
- Scout 7 (Quota APIs): `aea1d9a`
- Scout 8 (model_registry): `a654b93`
- Scout 9 (Toast/Spinner): `a950947`

---

**Report compiled by:** Claude Opus (Architect)
**Next Step:** Launch Sonnet verifier for critical path validation
**Then:** ПЕРЕКУР before implementation
