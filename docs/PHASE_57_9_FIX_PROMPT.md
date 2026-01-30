# 🔧 PHASE 57.9 FIX PROMPT - Ready for Implementation

## ISSUE SUMMARY
When user learns new API key (Tavily) via Hostess:
- ✅ Key gets saved to `config.json`
- ✅ Pattern gets learned in `learned_key_patterns.json`
- ❌ Key NOT visible in ModelDirectory UI
- **ROOT CAUSE**: Frontend calls `GET /api/keys` endpoint that doesn't exist

---

## THE FIX (Single Endpoint Implementation)

### Location
**File**: `src/api/routes/config_routes.py`
**After**: Line 350 (after `@router.get("/keys/validate")`)
**Before**: Line 353 (before `@router.get("/agents/status")`)

### Required Functionality
1. Read `data/config.json`
2. Extract all keys from `api_keys` section
3. Handle 4 different storage formats:
   - **String**: `"tavily": "tvly-dev-xxx"`
   - **Dict with paid/free**: `"openrouter": {"paid": "sk-or-xxx", "free": ["sk-or-yyy", ...]}`
   - **Array**: `"gemini": ["AIzaSyDxID6..."]`
4. Mask keys (show first 8 chars + "..." + last 4 chars)
5. Return normalized response

### Expected Response Format
```json
{
  "success": true,
  "providers": [
    {
      "provider": "tavily",
      "keys": [
        {
          "id": "tavily-1",
          "provider": "tavily",
          "key": "tvly-dev-ZIhXWoj...eM9F",
          "status": "active"
        }
      ]
    },
    {
      "provider": "openrouter",
      "keys": [
        {
          "id": "openrouter-paid",
          "provider": "openrouter",
          "key": "sk-or-v1-04d4...9193",
          "status": "active",
          "type": "paid"
        },
        {
          "id": "openrouter-free-1",
          "provider": "openrouter",
          "key": "sk-or-v1-08b3...b296",
          "status": "active",
          "type": "free"
        }
      ]
    },
    {
      "provider": "gemini",
      "keys": [
        {
          "id": "gemini-1",
          "provider": "gemini",
          "key": "AIzaSyDxID6HnNc...rA",
          "status": "active"
        }
      ]
    }
  ],
  "count": 3
}
```

---

## IMPLEMENTATION CHECKLIST

- [ ] Create new endpoint: `@router.get("/keys")`
- [ ] Import required modules (Path, json)
- [ ] Read config.json from `data/config.json`
- [ ] Parse `api_keys` section
- [ ] Handle "anthropic" provider (skip it - not managed by system)
- [ ] For each provider, handle 3 formats:
  - [ ] String keys (tavily, nanogpt single)
  - [ ] Dict keys (openrouter paid/free)
  - [ ] Array keys (gemini, nanogpt array)
- [ ] Create response with normalized structure
- [ ] Add proper error handling (try/except)
- [ ] Return 200 with structured data

---

## KEY MASKING LOGIC

```python
def mask_key(key: str) -> str:
    if len(key) < 12:
        return "***"
    return f"{key[:8]}...{key[-4:]}"
```

Examples:
- `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` → `tvly-dev-...eM9F`
- `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` → `sk-or-v1-...9193`
- `AIzaSyDxID6HnNc5Zn2ww5EUE-U6lQruR8VNErA` → `AIzaSyDxI...VNErA`

---

## CONFIG.JSON STRUCTURE REFERENCE

Current structure (from data/config.json):
```json
{
  "api_keys": {
    "openrouter": {
      "paid": "sk-or-v1-...",
      "free": ["sk-or-v1-...", "sk-or-v1-...", ...]
    },
    "gemini": ["AIzaSy...", "AIzaSy...", "AIzaSy..."],
    "anthropic": null,
    "nanogpt": ["sk-nano-..."],
    "tavily": "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"
  }
}
```

---

## EXISTING SIMILAR CODE (Reference)

From `src/api/handlers/key_handlers.py:183-207` - shows how to handle different formats:

```python
# Helper to count keys
def count_keys(value) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return 1 if value else 0
    if isinstance(value, list):
        return len([k for k in value if k])
    if isinstance(value, dict):
        total = 0
        if value.get('paid'):
            total += 1
        if isinstance(value.get('free'), list):
            total += len(value['free'])
        return total
    return 0
```

Use similar pattern for GET /api/keys endpoint

---

## VALIDATION TESTS (After Implementation)

### Test 1: Check Tavily appears
```bash
curl http://localhost:5001/api/keys
# Should return tavily in providers array
```

### Test 2: Check masking
```bash
# Response should show "tvly-dev-...eM9F" NOT full key
```

### Test 3: Check all providers
```bash
# Should include: tavily, openrouter, gemini, nanogpt
# Should NOT include: anthropic (it's null)
```

### Test 4: UI loads correctly
```bash
1. Open ModelDirectory
2. Click API Keys section
3. Should see Tavily key listed
4. Should see other keys (OpenRouter, Gemini, etc.)
```

---

## INTEGRATION WITH FRONTEND

**Frontend is ALREADY READY** - no changes needed:

From `client/src/components/ModelDirectory.tsx:160-170`:
```typescript
const fetchKeys = useCallback(async () => {
  try {
    const res = await fetch('/api/keys');  // ← Will work once endpoint exists
    const data = await res.json();
    if (data.providers) {
      setProviders(data.providers);  // ← Will populate this state
    }
  } catch (err) {
    console.error('[ModelDirectory] Failed to fetch keys:', err);
  }
}, []);
```

Frontend is waiting for this endpoint. It will just work once added.

---

## DEPLOYMENT NOTES

- [ ] No database changes needed
- [ ] No config changes needed
- [ ] Only backend endpoint addition
- [ ] No breaking changes
- [ ] Backwards compatible (new endpoint, doesn't affect existing code)
- [ ] No async dependencies (just file read)
- [ ] Ready for immediate deployment after implementation

---

## TIME ESTIMATES

- Implementation: 15 min
- Testing: 5 min
- Code review: 5 min
- Total: 25 min

---

## READY TO IMPLEMENT? ✓

**APPROVAL**: Yes, this is exactly what's needed.

**PRIORITY**: High - blocks Tavily key visibility in UI

**COMPLEXITY**: Low - straightforward endpoint with simple logic

**RISK**: None - read-only operation, no side effects
