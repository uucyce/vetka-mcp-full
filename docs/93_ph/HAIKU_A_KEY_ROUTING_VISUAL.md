# Key Routing Visual Architecture

## Current Architecture (PAID-FIRST)

```
┌─────────────────────────────────────────────────────────────────┐
│                      CONFIG.JSON STRUCTURE                      │
└─────────────────────────────────────────────────────────────────┘

{
  "api_keys": {
    "openrouter": {
      "paid": "sk-or-v1-04d4e5a4cc6f20be...",  ← PAID KEY
      "free": [
        "sk-or-v1-08b39403601eca10edd...",     ← FREE KEY 1
        "sk-or-v1-2335b0236e5e80213...",       ← FREE KEY 2
        ... 7 more free keys
      ]
    }
  }
}

     ↓ _load_provider_keys() [CURRENT]
     ↓

┌─────────────────────────────────────────────────────────────────┐
│           UNIFIEDKEYMANAGER.KEYS[OPENROUTER] LIST              │
└─────────────────────────────────────────────────────────────────┘

  index[0] ┌─────────────────────────────────────────────────┐
           │ APIKeyRecord(                                   │
           │   key="sk-or-v1-04d4e5a4cc...",               │
           │   alias='paid',                                │
           │   is_available()=True                          │
           │ )                                              │
           └─────────────────────────────────────────────────┘ ← PAID KEY

  index[1] ┌─────────────────────────────────────────────────┐
           │ APIKeyRecord(                                   │
           │   key="sk-or-v1-08b39403...",                 │
           │   alias='free_1',                              │
           │   is_available()=True                          │
           │ )                                              │
           └─────────────────────────────────────────────────┘ ← FREE KEY 1

  index[2] ┌─────────────────────────────────────────────────┐
           │ APIKeyRecord(                                   │
           │   key="sk-or-v1-2335b023...",                 │
           │   alias='free_2',                              │
           │   is_available()=True                          │
           │ )                                              │
           └─────────────────────────────────────────────────┘ ← FREE KEY 2

  ...

  index[9] ┌─────────────────────────────────────────────────┐
           │ APIKeyRecord(                                   │
           │   key="sk-or-v1-d73c172...",                  │
           │   alias='free_9',                              │
           │   is_available()=True                          │
           │ )                                              │
           └─────────────────────────────────────────────────┘ ← FREE KEY 9

     ↓ get_openrouter_key() [CURRENT]
     ↓ _current_openrouter_index = 0 (default)
     ↓

┌─────────────────────────────────────────────────────────────────┐
│                    RETURNED KEY (CURRENT)                       │
└─────────────────────────────────────────────────────────────────┘

   ➜ "sk-or-v1-04d4e5a4cc6f20be..." (PAID KEY) ✓
```

---

## Future Architecture (FREE-FIRST)

```
┌─────────────────────────────────────────────────────────────────┐
│                      CONFIG.JSON STRUCTURE                      │
│                         (UNCHANGED!)                            │
└─────────────────────────────────────────────────────────────────┘

{
  "api_keys": {
    "openrouter": {
      "paid": "sk-or-v1-04d4e5a4cc6f20be...",  ← PAID KEY
      "free": [                                  ← Still named "free"
        "sk-or-v1-08b39403601eca10edd...",     ← Still FREE KEYS
        "sk-or-v1-2335b0236e5e80213...",
        ... 7 more free keys
      ]
    }
  }
}

     ↓ _load_provider_keys() [NEW - CHANGED ORDER]
     ↓ NOW: Load free keys FIRST, then paid key
     ↓

┌─────────────────────────────────────────────────────────────────┐
│           UNIFIEDKEYMANAGER.KEYS[OPENROUTER] LIST              │
│                        (NEW ORDER!)                            │
└─────────────────────────────────────────────────────────────────┘

  index[0] ┌─────────────────────────────────────────────────┐
           │ APIKeyRecord(                                   │
           │   key="sk-or-v1-08b39403...",                 │
           │   alias='free_1',                              │
           │   is_available()=True                          │
           │ )                                              │
           └─────────────────────────────────────────────────┘ ← FREE KEY 1 (NOW FIRST!)

  index[1] ┌─────────────────────────────────────────────────┐
           │ APIKeyRecord(                                   │
           │   key="sk-or-v1-2335b023...",                 │
           │   alias='free_2',                              │
           │   is_available()=True                          │
           │ )                                              │
           └─────────────────────────────────────────────────┘ ← FREE KEY 2

  ...

  index[8] ┌─────────────────────────────────────────────────┐
           │ APIKeyRecord(                                   │
           │   key="sk-or-v1-d73c172...",                  │
           │   alias='free_9',                              │
           │   is_available()=True                          │
           │ )                                              │
           └─────────────────────────────────────────────────┘ ← FREE KEY 9

  index[9] ┌─────────────────────────────────────────────────┐
           │ APIKeyRecord(                                   │
           │   key="sk-or-v1-04d4e5a4cc...",               │
           │   alias='paid',                                │
           │   is_available()=True                          │
           │ )                                              │
           └─────────────────────────────────────────────────┘ ← PAID KEY (NOW LAST!)

     ↓ get_openrouter_key() [UNCHANGED CALL]
     ↓ _current_openrouter_index = 0 (default)
     ↓

┌─────────────────────────────────────────────────────────────────┐
│                    RETURNED KEY (FUTURE)                        │
└─────────────────────────────────────────────────────────────────┘

   ➜ "sk-or-v1-08b39403..." (FREE KEY) ✓
```

---

## Function Call Flow

### Current Flow (Paid-First)

```
┌─────────────────────────────────────────────────────────┐
│  User code: get_openrouter_key()                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ├─ Check if rotate=True? NO
                   │
                   ├─ idx = self._current_openrouter_index % len(available_keys)
                   │  └─ idx = 0 % 10 = 0
                   │
                   ├─ Return available_keys[0].key
                   │  └─ Available[0] = PAID (because loaded first)
                   │
                   └─ Returns: "sk-or-v1-04d4..." (PAID)

                   Cost: HIGH (uses paid key by default)
```

### Future Flow (Free-First)

```
┌─────────────────────────────────────────────────────────┐
│  User code: get_openrouter_key()                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ├─ Check if rotate=True? NO
                   │
                   ├─ idx = self._current_openrouter_index % len(available_keys)
                   │  └─ idx = 0 % 10 = 0
                   │
                   ├─ Return available_keys[0].key
                   │  └─ Available[0] = FREE (because loaded first)
                   │
                   └─ Returns: "sk-or-v1-08b..." (FREE)

                   Cost: SAVINGS (uses free key by default)
```

---

## Code Changes Map

### Change Location 1: _load_provider_keys() [Lines 551-563]

**BEFORE:**
```
Load paid key first (index 0)
    ↓
Load free keys (index 1+)
```

**AFTER:**
```
Load free keys first (index 0+)
    ↓
Load paid key last (index N)
```

### Change Location 2: add_openrouter_key() [Lines 468-470]

**BEFORE:**
```
if is_paid:
    insert(0)  ← paid goes to front
else:
    append()   ← free goes to back
```

**AFTER:**
```
if is_paid:
    append()   ← paid goes to back
else:
    insert(0)  ← free goes to front
```

### Change Location 3: save_to_config() [Lines 587-588]

**BEFORE:**
```
'paid': active_keys[0]  ← save first key as paid
'free': active_keys[1:] ← save rest as free
```

**AFTER:**
```
'paid': active_keys[-1]  ← save last key as paid
'free': active_keys[:-1] ← save all-except-last as free
```

### Change Location 4: Function Rename [Line 237]

**BEFORE:**
```python
def reset_to_paid(self) -> None:
```

**AFTER:**
```python
def reset_to_free(self) -> None:
```

---

## Impact Summary

### What Changes
- Default key selection: PAID → FREE (saves costs)
- Function name: reset_to_paid() → reset_to_free()
- Internal list order: PAID-first → FREE-first
- Log messages: "paid" → "free"

### What Stays the Same
- config.json structure (still has "paid" and "free" keys)
- API method signatures
- Rotation mechanism
- Rate limiting logic
- Validation rules

### Behavioral Impact

| Action | Before | After | Impact |
|--------|--------|-------|--------|
| Call get_openrouter_key() | Returns PAID | Returns FREE | Cost savings |
| Call rotate_to_next() | Cycles through all | Cycles through all | Same |
| Call reset_to_free() | ERROR (no such func) | Resets to index 0 | FIX |
| Save to config | [0]=paid, [1:]=free | [-1]=paid, [:-1]=free | Same structure |
| Load from config | paid first, free last | free first, paid last | Implementation detail |

---

## Rotation Example

### Current Rotation Pattern (10 keys)

```
Start:           get_openrouter_key()
  ↓
Index 0 (PAID) ← DEFAULT, call rotate_to_next()
  ↓
Index 1 (FREE), call rotate_to_next()
  ↓
Index 2 (FREE), call rotate_to_next()
  ↓
... continues...
  ↓
Index 9 (FREE), call rotate_to_next()
  ↓
Index 0 (PAID) ← Back to start
```

**Pattern: Uses PAID by default, uses FREE during failures**

### Future Rotation Pattern (10 keys)

```
Start:           get_openrouter_key()
  ↓
Index 0 (FREE) ← DEFAULT, call rotate_to_next()
  ↓
Index 1 (FREE), call rotate_to_next()
  ↓
... continues...
  ↓
Index 8 (FREE), call rotate_to_next()
  ↓
Index 9 (PAID), call rotate_to_next()
  ↓
Index 0 (FREE) ← Back to start
```

**Pattern: Uses FREE by default, uses PAID during failures (as fallback)**

---

## File Locations Reference

```
Project Root: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/

Source Files:
├─ src/utils/unified_key_manager.py          ← PRIMARY (all 7 changes)
└─ src/orchestration/services/api_key_service.py  ← Consumer (no changes)

Config:
└─ data/config.json                          ← Loaded but structure unchanged

Documentation (Created):
├─ docs/93_ph/HAIKU_A_KEY_ROUTING.md         ← Full analysis
├─ docs/93_ph/HAIKU_A_KEY_ROUTING_QUICK.md   ← Quick ref
├─ docs/93_ph/HAIKU_A_KEY_ROUTING_CODE_MAP.md   ← Implementation guide
├─ docs/93_ph/HAIKU_A_KEY_ROUTING_SUMMARY.md    ← Executive summary
└─ docs/93_ph/HAIKU_A_KEY_ROUTING_VISUAL.md     ← This file
```

---

## Decision Matrix

| Factor | Analysis | Recommendation |
|--------|----------|-----------------|
| Complexity | 7 changes in 1 file | PROCEED |
| Risk | No external callers | PROCEED |
| Cost Savings | Significant (FREE first) | PROCEED |
| Rollback | Easy (git revert) | PROCEED |
| Testing | Existing tests should pass | PROCEED |
| Timeline | Can start immediately | PROCEED |
