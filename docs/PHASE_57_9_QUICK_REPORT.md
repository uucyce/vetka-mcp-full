# 🎯 PHASE 57.9 QUICK REPORT - TAVILY KEY VISIBILITY BUG

## TL;DR
✅ **Tavily key IS saved correctly**
❌ **Tavily key NOT visible in UI**

**ROOT CAUSE**: Missing FastAPI endpoint `GET /api/keys`

---

## 📊 WHAT WORKS vs WHAT'S BROKEN

### ✅ Working Part (Backend)
```
Log: "✅ Learned Tavily key pattern! Key saved to config."
File: data/config.json → "tavily": "tvly-dev-ZIhXWoj..."
File: data/learned_key_patterns.json → Tavily pattern with 0.85 confidence
Flow: User paste → Hostess asks → User responds "Tavily" → Saved ✓
```

### ❌ Broken Part (Frontend/UI)
```
File: client/src/components/ModelDirectory.tsx:162
Code: fetch('/api/keys')
Issue: This endpoint DOES NOT EXIST in FastAPI
Result: 404 Not Found → providers = [] → Tavily not shown
```

---

## 🔴 MARKER #1: MISSING_ENDPOINT

**Location**: `src/api/routes/config_routes.py`
**Type**: Missing `@router.get("/keys")`
**Impact**: UI cannot fetch saved keys list
**Fix**: Add ~50 lines of endpoint code

**Context**:
- Existing endpoints: `/api/keys/status` (line 259), `/api/keys/validate` (line 328)
- Missing endpoint: `/api/keys` (should return full list with providers)
- Frontend expects: `{providers: [{provider: 'tavily', keys: [...]}]}`

---

## 🔴 MARKER #2: ENDPOINT_FORMAT_MISMATCH

**Location**: `config_routes.py` endpoint implementation
**Issue**: Different key storage formats in config.json
**Types**:
- `tavily`: String (single key)
- `openrouter`: Dict with `{paid: key, free: [keys]}`
- `gemini`: Array of keys
- `nanogpt`: Array of keys

**Endpoint needs to handle all 4 formats and normalize them**

---

## 🔴 MARKER #3: DATA_MASKING_NEEDED

**Location**: GET /api/keys response
**Issue**: Should NOT return full key values
**Format**: Must mask like `tvly-dev-...eM9F` (first 8 + ... + last 4)

---

## 📁 FILE LOCATIONS

### Broken Component
```python
# frontend/TypeScript - waiting for endpoint
client/src/components/ModelDirectory.tsx
  Line 160-170: fetchKeys() function
  Line 173-177: useEffect that calls fetchKeys()
  Line 162: fetch('/api/keys') ← expecting response
```

### Working Components (no changes needed)
```python
# Backend - working perfectly
src/elisya/key_learner.py → learn_key_type() ✓
src/api/handlers/user_message_handler.py → calls learner ✓
data/config.json → stores tavily key ✓
data/learned_key_patterns.json → stores pattern ✓
```

### Missing Component
```python
# Backend - MISSING endpoint
src/api/routes/config_routes.py → NO @router.get("/keys") endpoint
```

---

## 🧪 VERIFICATION CHECKLIST

- [x] Tavily key saved in config.json line 28: `"tavily": "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"`
- [x] Pattern learned in learned_key_patterns.json: `"tavily": {...}`
- [x] Hostess asks for provider: "What service is this for?"
- [x] User responds "Tavily": Handled in user_message_handler.py
- [x] Key persisted to config: Yes, logged as "Key saved to config"
- [ ] GET /api/keys endpoint exists: **NO** ❌
- [ ] UI fetches and displays tavily: **NO** ❌ (because no endpoint)

---

## 🔗 DEPENDENCY CHAIN

```
User Experience Flow:
├─ Paste unknown key → Works ✓
├─ Hostess asks provider → Works ✓
├─ Respond "Tavily" → Works ✓
├─ Key saved to config.json → Works ✓
├─ Refresh page → Works ✓
├─ ModelDirectory.fetchKeys() → Fails ❌
│  └─ fetch('/api/keys') → 404 Not Found
└─ UI shows empty key list → Fails ❌
```

---

## 💡 SOLUTION SUMMARY

**Problem**: Single missing endpoint prevents UI from seeing saved keys

**Files to modify**: 1 file
- `src/api/routes/config_routes.py` (add GET /api/keys)

**Lines to add**: ~50 lines of endpoint code

**Time estimate**: 15-20 min (including testing)

---

## 🎬 AFTER FIX EXPECTED RESULT

```
ModelDirectory opens
  → Calls: fetch('/api/keys')
  → Response: 200 OK {providers: [{provider: 'tavily', keys: [...]}]}
  → UI renders: "Tavily: tvly-dev-...eM9F" in saved keys list
```

---

**DIAGNOSIS COMPLETE** ✓

For full analysis, see: `PHASE_57_9_ANALYSIS.md`
