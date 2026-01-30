# Key Routing Quick Reference

## Current State: PAID KEY = index 0 (default)

When you call `get_openrouter_key()` → returns `index 0` → which is the PAID key

```
Configuration order:
┌─────────────────────────────────────┐
│ self.keys[OPENROUTER][0] = PAID KEY │  ← Currently returned by default
│ self.keys[OPENROUTER][1] = FREE KEY │
│ self.keys[OPENROUTER][2] = FREE KEY │
│ ...                                  │
└─────────────────────────────────────┘
```

## Required Changes

### 1. Rename Function
```
reset_to_paid()  →  reset_to_free()
```

### 2. Change Load Order
In `_load_provider_keys()` (lines 551-563):
```python
# BEFORE: load PAID first, then FREE
# AFTER: load FREE first, then PAID
```

### 3. Invert Add Logic
In `add_openrouter_key()` (lines 467-470):
```python
# BEFORE:
if is_paid:
    insert(0)     # PAID at index 0
else:
    append()      # FREE at end

# AFTER:
if is_paid:
    append()      # PAID at end
else:
    insert(0)     # FREE at index 0
```

### 4. Update Save Logic
In `save_to_config()` (line 587):
```python
# BEFORE: active_keys[0] saved as 'paid'
# AFTER: active_keys[0] saved as 'free'
```

### 5. Update Comments
- Line 189: Phase 57.11 (update to FREE)
- Line 220: "index 0 = free key"
- Line 239: "Reset to free key"

## After Changes: FREE KEY = index 0 (default)

```
Configuration order (NEW):
┌─────────────────────────────────────┐
│ self.keys[OPENROUTER][0] = FREE KEY │  ← Will be returned by default
│ self.keys[OPENROUTER][1] = FREE KEY │
│ ...                                  │
│ self.keys[OPENROUTER][N] = PAID KEY │
└─────────────────────────────────────┘
```

## Files to Modify
- `src/utils/unified_key_manager.py` - PRIMARY (5 locations)

## Files to Check
- `src/orchestration/services/api_key_service.py` - Uses the manager (NO CHANGES NEEDED)
