# Key Routing Code Map - Lines to Change

## File: src/utils/unified_key_manager.py

### Change 1: Line 2-3 (Header comment)
```
BEFORE: VETKA UnifiedKeyManager - Phase 57.12
AFTER:  VETKA UnifiedKeyManager - Phase 57.12 (FREE KEY PRIORITY)
```

### Change 2: Lines 189-190 (get_openrouter_key docstring)
```python
BEFORE:
Phase 57.11: Returns PAID key (index 0) by default.

AFTER:
Phase 57.12: Returns FREE key (index 0) by default.
```

### Change 3: Line 220 (get_openrouter_key comment)
```python
BEFORE:
# Return current key (defaults to index 0 = paid key)

AFTER:
# Return current key (defaults to index 0 = free key)
```

### Change 4: Lines 237-244 (Function rename + docstring)
```python
BEFORE:
def reset_to_paid(self) -> None:
    """
    Reset to paid key (index 0).
    Call at start of new conversation or after successful responses.
    """

AFTER:
def reset_to_free(self) -> None:
    """
    Reset to free key (index 0).
    Call at start of new conversation or after successful responses.
    """
```

Also update the log message (line 243):
```python
BEFORE:
logger.info(f"[UnifiedKeyManager] Reset to paid key (was index {self._current_openrouter_index})")

AFTER:
logger.info(f"[UnifiedKeyManager] Reset to free key (was index {self._current_openrouter_index})")
```

### Change 5: Lines 467-470 (add_openrouter_key logic)
```python
BEFORE:
if is_paid:
    self.keys[ProviderType.OPENROUTER].insert(0, record)
else:
    self.keys[ProviderType.OPENROUTER].append(record)

AFTER:
if is_paid:
    self.keys[ProviderType.OPENROUTER].append(record)
else:
    self.keys[ProviderType.OPENROUTER].insert(0, record)
```

Also update the message (line 475):
```python
BEFORE:
"message": f"OpenRouter key added {'(paid)' if is_paid else '(free)'}",

AFTER:
"message": f"OpenRouter key added {'(paid - appended)' if is_paid else '(free - inserted)'}",
```

### Change 6: Lines 551-563 (_load_provider_keys dict block)
SWAP THE ENTIRE BLOCK ORDER:

```python
BEFORE:
elif isinstance(keys_data, dict):
    if paid_key := keys_data.get('paid'):
        if validator(paid_key):
            record = APIKeyRecord(provider=provider, key=paid_key, alias='paid')
            self.keys[provider].append(record)
            loaded += 1

    for i, key in enumerate(keys_data.get('free', [])):
        if key and validator(key):
            record = APIKeyRecord(provider=provider, key=key, alias=f'free_{i + 1}')
            self.keys[provider].append(record)
            loaded += 1

AFTER:
elif isinstance(keys_data, dict):
    # Load FREE keys FIRST (they become index 0+)
    for i, key in enumerate(keys_data.get('free', [])):
        if key and validator(key):
            record = APIKeyRecord(provider=provider, key=key, alias=f'free_{i + 1}')
            self.keys[provider].append(record)
            loaded += 1

    # Load PAID key LAST (becomes higher index)
    if paid_key := keys_data.get('paid'):
        if validator(paid_key):
            record = APIKeyRecord(provider=provider, key=paid_key, alias='paid')
            self.keys[provider].append(record)
            loaded += 1
```

### Change 7: Lines 585-589 (save_to_config logic)
```python
BEFORE:
if provider_name == 'openrouter':
    config['api_keys']['openrouter'] = {
        'paid': active_keys[0] if active_keys else None,
        'free': active_keys[1:] if len(active_keys) > 1 else []
    }

AFTER:
if provider_name == 'openrouter':
    config['api_keys']['openrouter'] = {
        'paid': active_keys[-1] if active_keys else None,  # LAST key is paid
        'free': active_keys[:-1] if len(active_keys) > 1 else []  # ALL except last are free
    }
```

---

## Search Markers in Code

These are the lines with searchable text for verification:

1. **Line 189:** `Phase 57.11: Returns PAID key` → search for this string
2. **Line 220:** `defaults to index 0 = paid key` → search for this string
3. **Line 237:** `def reset_to_paid(self)` → search for this function name
4. **Line 468:** `.insert(0, record)` → in add_openrouter_key context
5. **Line 553:** `if paid_key := keys_data.get('paid')` → in _load_provider_keys
6. **Line 587:** `'paid': active_keys[0]` → in save_to_config

---

## Verification Checklist After Changes

- [ ] Phase 57.12 comment updated on line 2
- [ ] Line 189: Phase 57.12 + "Returns FREE key"
- [ ] Line 220: "free key" instead of "paid key"
- [ ] Line 237: Function renamed to `reset_to_free()`
- [ ] Line 243: Log message mentions "free key"
- [ ] Lines 468-470: Logic inverted (paid→append, free→insert)
- [ ] Lines 551-563: FREE block BEFORE paid block
- [ ] Lines 587-588: paid=active_keys[-1], free=active_keys[:-1]
- [ ] No syntax errors: `python -m py_compile src/utils/unified_key_manager.py`

---

## Impact Analysis

### What Changes:
- Default key selection order (FREE becomes first)
- Function naming (`reset_to_paid` → `reset_to_free`)
- Config loading/saving logic

### What DOESN'T Change:
- Public API (get_key(), get_active_key() still work the same)
- Key validation rules
- APIKeyService wrapper (it calls get_active_key, which still returns index 0)
- Rate limiting and cooldown logic

### Backward Compatibility:
- If code calls `reset_to_paid()`, it will BREAK (need to find all usages)
- If code relies on "index 0 = paid", it will BREAK (unlikely in API-level code)
