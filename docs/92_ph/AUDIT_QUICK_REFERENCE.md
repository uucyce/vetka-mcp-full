# Phase 90.10: Audit Quick Reference
## Key Rotation, Cooldown & Provider Integration

### 📍 Report Location
`/docs/92_ph/HAIKU_5_KEY_ROTATION_SUPPLEMENT.md` (908 lines)

### 🎯 HAIKU_2 vs HAIKU_5 Coverage

| Aspect | HAIKU_2 (Detection Patterns) | HAIKU_5 (Rotation & Cooldown) |
|--------|--------|---------|
| Key format detection | ✅ 70+ providers | - |
| Validation rules | ✅ Regex patterns | - |
| Configuration loading | ✅ Config parser | - |
| **Key rotation** | - | ✅ Round-robin for OpenRouter |
| **24h cooldown** | - | ✅ mark_rate_limited() mechanics |
| **Paid/Free pools** | - | ✅ Prioritization strategy |
| **Provider integration** | - | ✅ XAI 403 handling + fallback |
| **API Key Service** | - | ✅ get_key() and report_failure() |
| **Singleton pattern** | - | ✅ get_key_manager() |

### 🔑 Core Files Referenced

1. **`src/utils/unified_key_manager.py`**
   - Lines 83-87: `mark_rate_limited()`
   - Lines 71-81: `is_available()`
   - Lines 185-222: `get_openrouter_key()`
   - Lines 224-235: `rotate_to_next()`

2. **`src/elisya/provider_registry.py`**
   - Lines 26-30: `XaiKeysExhausted` exception
   - Lines 694-732: 403 handling with key rotation
   - Lines 903-917: OpenRouter fallback

3. **`src/orchestration/services/api_key_service.py`**
   - Lines 48-84: `get_key(provider)`
   - Lines 124-132: `report_failure()`

### ⏰ 24-Hour Cooldown Flow

```
API Error (402/403/429)
    ↓
report_failure(key, mark_cooldown=True)
    ↓
record.mark_rate_limited()
    ↓
rate_limited_at = datetime.now()
    ↓
[COOLDOWN ACTIVE FOR 24 HOURS]
    ↓
is_available() checks:
  cooldown_end = rate_limited_at + timedelta(hours=24)
  if datetime.now() < cooldown_end: return False
    ↓
After 24h:
  rate_limited_at = None → key available again
```

### 🔄 Key Rotation Strategies

#### OpenRouter (Prioritized Paid)
```python
# Structure: [paid_key, free_key1, free_key2, ...]
# Default: index 0 (paid)
# Rotation: (index + 1) % len(available_keys)
get_openrouter_key()  # → always returns paid key by default
rotate_to_next()      # → explicit rotation when key fails
```

#### Other Providers (First Available)
```python
# For xAI, OpenAI, Anthropic, Gemini, etc.
for record in keys:
    if record.is_available():
        return record.key
# Returns first key that's not rate-limited
```

### 🚨 XAI 403 Handling

**Location:** `provider_registry.py:694-732`

```
XaiProvider.call() gets 403
    ↓
get_key_manager() [singleton]
    ↓
Find current key in ProviderType.XAI list
    ↓
record.mark_rate_limited()  ← 24h cooldown start
    ↓
Get next key: key_manager.get_active_key(ProviderType.XAI)
    ↓
┌─ If next_key found:
│  └─ Retry with new key
│     ├─ Success? → return
│     └─ Still 403? → continue loop
│
└─ If no next key (all cooldown):
   └─ raise XaiKeysExhausted
      └─ Caught in ProviderRegistry (line 903)
         └─ Fallback: OpenRouter.call(x-ai/model)
```

### 💾 Config Format

```json
{
  "api_keys": {
    "openrouter": {
      "paid": "sk-or-PAID_KEY",
      "free": ["sk-or-FREE1", "sk-or-FREE2"]
    },
    "xai": ["xai-key1", "xai-key2"],
    "gemini": "AIzaSy...",
    "openai": ["sk-proj-..."]
  }
}
```

**Loading logic:**
- OpenRouter: paid → index 0, free → index 1+
- Others: single or array → list of records

**Saving logic:**
- First active key → paid field
- Rest → free array
- Structure preserved across restarts

### 🎛️ Singleton Pattern

```python
# GLOBAL STATE
_unified_manager: Optional[UnifiedKeyManager] = None

def get_key_manager() -> UnifiedKeyManager:
    global _unified_manager
    if _unified_manager is None:
        _unified_manager = UnifiedKeyManager()
    return _unified_manager
```

**CRITICAL:**
- One instance per process
- All providers share same state
- Cooldown visible globally
- Phase 80.40: Fixed bug of creating new instances

### 📊 Key Status Dictionary

```python
key.get_status() returns:
{
    'masked': 'sk-o****4j8s',
    'alias': 'paid' or 'free_1',
    'active': True/False,
    'available': True/False,      # ← is_available() result
    'success_count': 5,
    'failure_count': 2,
    'cooldown_hours': 18.5        # ← remaining cooldown
}
```

### ⚠️ Important Implementation Details

1. **Cooldown is memory-only**
   - Not persisted to disk
   - Lost on app restart
   - All keys become available again

2. **Timestamp checks use datetime.now()**
   - Real-time comparison
   - No clock synchronization

3. **mark_rate_limited() called in XAI handler**
   - Not automatic
   - Provider must explicitly call it
   - Line 709 in provider_registry.py

4. **get_active_key() differs by provider**
   - OpenRouter: uses rotation logic
   - Others: first available

5. **Paid key prioritization**
   - insert(0) for paid when adding
   - append() for free keys
   - First key in list = paid

### 🐛 Phase 80.40 Bug Fixes

| Bug | Location | Fix |
|-----|----------|-----|
| `_keys` vs `keys` | line 707 | Use public `keys` attribute |
| New instance | line 702 | Use `get_key_manager()` singleton |
| Double prefix | line 912-913 | Strip both "xai/" and "x-ai/" |

### 🔗 Cross-References

- **HAIKU_2:** Detection patterns (70+ providers)
- **HAIKU_5:** This supplement (rotation + cooldown)
- **HAIKU_A (Phase 90):** Architecture overview
- **Provider Registry:** `src/elisya/provider_registry.py`
- **Key Manager:** `src/utils/unified_key_manager.py`

### ✅ Audit Coverage

- [x] Key rotation logic (round-robin for OpenRouter)
- [x] 24h cooldown mechanics (mark_rate_limited, is_available)
- [x] Paid vs Free pool separation
- [x] Provider registry XAI handling (403 + fallback)
- [x] APIKeyService integration
- [x] Singleton pattern
- [x] Config persistence format
- [x] Critical bugs fixed in Phase 80.40
- [x] All line numbers and exact code locations
- [x] Flow diagrams and decision trees

---

**Report Created:** 2026-01-25
**Haiku Model:** claude-haiku-4-5-20251001
**Phase:** 90.10
**Status:** Complete ✅
