# PHASE L: Time-Based API Key Rotation

**Date:** 2025-12-27
**Status:** COMPLETED

---

## Problem

OpenRouter API keys have **daily limits per account**. Previous implementation:

```python
_failed_keys = set()  # Just a set, no timestamps

# Reset only when ALL keys failed
if all keys in _failed_keys:
    _failed_keys.clear()
```

**Issue:** Keys stayed blocked forever until ALL keys failed simultaneously. With 10 keys from different accounts (each with own daily limit), this logic was wrong.

---

## Solution: Time-Based Reset (24 hours)

### Changes in `main.py` (lines 121-262)

#### 1. Data Structure Change

```python
# BEFORE
_failed_keys = set()

# AFTER
_failed_keys = {}  # {key: timestamp}
_FAILED_KEY_RESET_HOURS = 24
```

#### 2. New Cleanup Function

```python
def _cleanup_expired_failed_keys():
    """Remove keys from failed list if they failed more than 24 hours ago"""
    global _failed_keys
    now = _time.time()
    reset_threshold = _FAILED_KEY_RESET_HOURS * 3600  # 24h in seconds

    expired_keys = [
        key for key, timestamp in _failed_keys.items()
        if now - timestamp > reset_threshold
    ]

    for key in expired_keys:
        del _failed_keys[key]
        print(f"🔓 Key unlocked after {_FAILED_KEY_RESET_HOURS}h: {key[:25]}...")
```

#### 3. Updated `get_openrouter_key()`

```python
def get_openrouter_key() -> str:
    """Get current OpenRouter API key (skips recently failed keys)"""
    global _current_key_index

    keys = _load_openrouter_keys()

    # Cleanup expired failed keys (24h reset)
    _cleanup_expired_failed_keys()  # <-- NEW

    # Find next working key
    attempts = 0
    while attempts < len(keys):
        key = keys[_current_key_index % len(keys)]
        if key not in _failed_keys:
            return key
        _current_key_index = (_current_key_index + 1) % len(keys)
        attempts += 1

    # All keys failed - emergency reset
    print("⚠️  All API keys marked as failed, resetting...")
    _failed_keys.clear()
    return keys[0]
```

#### 4. Updated `rotate_openrouter_key()`

```python
def rotate_openrouter_key(mark_failed: bool = True) -> str:
    """
    Rotate to next API key.
    If mark_failed=True, marks current key as failed with timestamp.
    Keys will be automatically unlocked after 24 hours.
    """
    global _current_key_index

    keys = _load_openrouter_keys()

    # Cleanup expired failed keys first
    _cleanup_expired_failed_keys()  # <-- NEW

    with _key_lock:
        current_key = keys[_current_key_index % len(keys)]

        if mark_failed and current_key:
            _failed_keys[current_key] = _time.time()  # <-- Store with timestamp
            print(f"❌ Marked key as failed: {current_key[:25]}... (total failed: {len(_failed_keys)}/{len(keys)}, resets in {_FAILED_KEY_RESET_HOURS}h)")

        # ... rest of rotation logic
```

---

## How It Works Now

### Individual Key Tracking

Each key has its own timer:

```python
_failed_keys = {
    "sk-or-v1-aaa...": 1735300000,  # failed at 10:00 → unlocks at 10:00 next day
    "sk-or-v1-bbb...": 1735310000,  # failed at 12:47 → unlocks at 12:47 next day
    "sk-or-v1-ccc...": 1735320000,  # failed at 15:33 → unlocks at 15:33 next day
}
```

### Two Reset Mechanisms

| Mechanism | When | Use Case |
|-----------|------|----------|
| **Time-based (24h)** | Each key individually after 24h from its fail time | Normal operation with daily limits |
| **Emergency reset** | When ALL keys failed AND none passed 24h yet | Fallback for catastrophic failures |

### Log Messages

```
❌ Marked key as failed: sk-or-v1-04d4e5a4... (total failed: 1/10, resets in 24h)
🔄 Rotated to key #2: sk-or-v1-08b39403...
🔓 Key unlocked after 24h: sk-or-v1-04d4e5a4...
```

---

## Bug Fix: OPENROUTER_KEYS Not Defined

Also fixed startup error:

```python
# BEFORE (line 319)
print(f"🔑 {len(OPENROUTER_KEYS)} API keys configured for rotation")

# AFTER
print(f"🔑 {len(_load_openrouter_keys())} API keys configured for rotation")
```

Old variable `OPENROUTER_KEYS` was removed when we switched to `_load_openrouter_keys()` function.

---

## Files Changed

| File | Lines | Changes |
|------|-------|---------|
| `main.py` | 121-129 | Added `_time` import, changed `_failed_keys` to dict, added `_FAILED_KEY_RESET_HOURS` |
| `main.py` | 187-200 | New `_cleanup_expired_failed_keys()` function |
| `main.py` | 203-224 | Updated `get_openrouter_key()` with cleanup call |
| `main.py` | 227-262 | Updated `rotate_openrouter_key()` with timestamp storage |
| `main.py` | 319 | Fixed `OPENROUTER_KEYS` → `_load_openrouter_keys()` |

---

## Testing

```bash
# Start server
python main.py

# Expected output:
💰 Economic model config loaded: default=deepseek/deepseek-chat
🔑 Loaded paid OpenRouter key: sk-or-v1-04d4e5a4cc6f2...
🔑 Loaded 9 free OpenRouter keys from config.json
🔑 Total OpenRouter keys available: 10
🔑 10 API keys configured for rotation
```

### Test Key Rotation

1. Send message with `@haiku`
2. If key fails (402), see log:
   ```
   ❌ Marked key as failed: sk-or-v1-xxx... (total failed: 1/10, resets in 24h)
   🔄 Rotated to key #2: sk-or-v1-yyy...
   ```
3. After 24 hours, key automatically unlocks:
   ```
   🔓 Key unlocked after 24h: sk-or-v1-xxx...
   ```

---

## Summary

| Before | After |
|--------|-------|
| `set()` - no timestamps | `dict` with `{key: timestamp}` |
| Reset only when ALL fail | Individual 24h reset per key |
| Keys blocked forever | Keys auto-unlock after daily limit resets |
| `OPENROUTER_KEYS` variable | `_load_openrouter_keys()` function |

**Result:** Each of 10 API keys (from different OpenRouter accounts) now correctly resets after its own 24-hour daily limit period.
