# SCOUT 1: API Key Routing Conflicts

## ASPECT
API Key Routing Conflicts - User reports "OpenAI API key not found" error when calling @gpt-5.2-pro, while PM (also using gpt-5.2-codex from OpenAI) works. Same API key used by different roles may conflict.

---

## Current Implementation

### File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py`
**Lines: 85-163 (OpenAIProvider class)**

The OpenAI provider uses a two-level fallback strategy:
1. First tries `self.config.api_key` (pre-configured key)
2. Falls back to `APIKeyService().get_key('openai')` (lines 106-109)
3. Raises `ValueError("OpenAI API key not found")` if both fail (line 112)

**Key lookup path:** Lines 106-112
```python
api_key = self.config.api_key
if not api_key:
    from src.orchestration.services.api_key_service import APIKeyService
    api_key = APIKeyService().get_key('openai')

if not api_key:
    raise ValueError("OpenAI API key not found")
```

### File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/services/api_key_service.py`
**Lines: 48-77 (get_key method)**

The service attempts to retrieve keys using a provider name map:
- `openai` → `ProviderType.OPENAI` (line 65)
- Calls `self.key_manager.get_active_key(provider_type)` (line 70)

**Problem:** APIKeyService.get_key() maps only these providers:
```python
provider_map = {
    'openrouter': ProviderType.OPENROUTER,
    'gemini': ProviderType.GEMINI,
    'ollama': ProviderType.OLLAMA,
    'nanogpt': ProviderType.NANOGPT,
}
```

**MISSING:** `'openai'` and `'anthropic'` are NOT in this map! (lines 58-63)

### File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/utils/unified_key_manager.py`
**Lines: 31-43, 255-278**

The UnifiedKeyManager has `ProviderType.OPENAI` defined (line 42), but:

**Key pooling:** OpenRouter uses rotation (lines 185-222):
- Maintains `_current_openrouter_index` state (line 157)
- Returns "paid key" (index 0) by default
- Skips rate-limited keys in cooldown (24h)

**Other providers:** Return first available key (lines 273-275), NO rotation

**Concurrent request issue:** Multiple simultaneous requests to same provider will all get the SAME key (no queue/pool management)

---

## Root Cause Analysis

### Issue 1: Missing Provider Mapping
**Location:** `api_key_service.py:58-63`

The `provider_map` in `APIKeyService.get_key()` doesn't include `'openai'` or `'anthropic'`, causing:
- `APIKeyService().get_key('openai')` returns `None`
- Provider detection fails silently with warning message only (line 67)
- Falls through to `ValueError` in provider_registry

### Issue 2: No Key Pooling for Concurrent Requests
**Location:** `unified_key_manager.py:273-275`

Non-OpenRouter providers (OpenAI, Anthropic, Gemini) don't implement key rotation/pooling:
```python
for record in self.keys.get(provider_key, []):
    if record.is_available():
        return record.key  # Returns SAME key every time
```

With multiple concurrent requests:
- All requests get identical key
- Rate limiting hits faster
- No fallback to next available key
- Single key becomes bottleneck

### Issue 3: Single Instance per Provider
**Location:** `provider_registry.py:620-645`

`ProviderRegistry` is a singleton with one `OpenAIProvider` instance:
```python
self._providers[Provider.OPENAI] = OpenAIProvider(ProviderConfig())
```

All calls to OpenAI go through same provider instance with same empty `ProviderConfig()`, forcing every call to fetch key again.

---

## Problems Found

1. **Missing Provider Mapping:** `openai` and `anthropic` not in APIKeyService.get_key() provider_map
2. **No Concurrent Key Pooling:** Only OpenRouter rotates keys; other providers return first available key repeatedly
3. **No Key Balancing:** Multiple concurrent requests to same provider compete for single key
4. **Silent Failure:** Unknown providers logged with warning but still raise ValueError upstream
5. **No Fallback Keys:** When primary key fails, no automatic rotation to backup key (except OpenRouter)
6. **State Not Shared:** Each APIKeyService instance gets new UnifiedKeyManager, no shared state

---

## Recommended Fixes

### FIX 1: Add Missing Provider Mapping
File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/services/api_key_service.py:58-63`

Add `openai` and `anthropic` to provider_map:
```python
provider_map = {
    'openai': ProviderType.OPENAI,
    'anthropic': ProviderType.ANTHROPIC,
    'openrouter': ProviderType.OPENROUTER,
    'gemini': ProviderType.GEMINI,
    'ollama': ProviderType.OLLAMA,
    'nanogpt': ProviderType.NANOGPT,
}
```

### FIX 2: Implement Key Rotation for All Providers
File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/utils/unified_key_manager.py:255-278`

Add `_current_provider_index` state for each provider and rotate like OpenRouter:
```python
def get_active_key_rotating(self, provider: ProviderKey) -> Optional[str]:
    """Get next available key with rotation for load balancing."""
    available = [r for r in self.keys.get(provider, []) if r.is_available()]
    if not available:
        return None

    # Round-robin rotation for concurrent requests
    idx = self._get_next_index(provider) % len(available)
    return available[idx].key
```

### FIX 3: Implement Automatic Failover
File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py:106-112`

On API key error, try next available key:
```python
api_key = self.config.api_key or APIKeyService().get_key('openai')
attempts = 0
while not api_key and attempts < 3:
    # Report failure and rotate to next key
    key_service.report_failure(api_key)
    api_key = key_service.get_next_available_key('openai')
    attempts += 1
```

---

## Impact

**Priority:** CRITICAL - Blocks concurrent multi-role workflows

**Affected Users:**
- PM using gpt-5.2-codex (may be hitting rate limit, forcing rotation)
- Other users on gpt-5.2-pro without automatic fallback
- Shared team accounts with single API key

**Severity:**
- Single concurrent request: Works with minor latency
- 2-3 concurrent requests: Second request fails with "key not found"
- Rate limited: All subsequent requests fail (no recovery)

