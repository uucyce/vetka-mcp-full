# RECON: AURA Preferences Not Loading (has_preferences: false)

**Phase:** 191.5
**Date:** 2026-03-18
**Status:** ROOT CAUSE FOUND

---

## Symptom

`session_init` returns `has_preferences: false` — AURA preferences not loading.

```json
"user_preferences": {
  "user_id": "default",
  "has_preferences": false
}
```

## Root Cause: user_id Mismatch

**The `session_init` default user_id is `"default"`, but Qdrant has data under `"danila"` and `"default_user"` — NOT `"default"`.**

### Evidence

Qdrant collection `vetka_user_memories` contains 2 points:

| Point ID | `_user_id` | Has Data |
|----------|-----------|----------|
| 2087867496301599866 | `"danila"` | Yes (all 6 categories) |
| 2567633202323356977 | `"default_user"` | Yes (all 6 categories) |

`session_init` calls `aura.get_user_preferences("default")` which hashes to point ID `3731451336796438715` — **does not exist in Qdrant**.

### Hash Mapping (uuid5)

```
"default"      -> 3731451336796438715  ← MISS (no data)
"danila"       -> 2087867496301599866  ← HIT
"default_user" -> 2567633202323356977  ← HIT
"danilagulin"  -> 4005838775774162915  ← MISS
```

## Call Chain

```
session_init(user_id="default")           # session_tools.py:165
  → get_aura_store()                      # singleton, aura_store.py:595
    → AuraStore(qdrant_client)            # Qdrant connected OK
  → aura.get_user_preferences("default")  # aura_store.py:284
    → _agent_cache("default")            # RAM empty (no data loaded for "default")
    → _qdrant_get_full("default")         # aura_store.py:374
      → point_id = hash("default") = 3731451336796438715
      → qdrant.retrieve(ids=[3731451336796438715])  # NO MATCH
      → returns None
  → prefs is None → has_preferences: false
```

## Secondary Issue: RAM Cache Cold Start

`_load_hot_data()` (called in `__init__`) scrolls ALL points from Qdrant, but loads them into RAM cache keyed by `_user_id` from payload. So `"danila"` preferences ARE in RAM — but `session_init` never asks for `"danila"`, it asks for `"default"`.

## Fix Options

### Option A: Change session_init default user_id (RECOMMENDED)
Change `session_tools.py:165` from `"default"` to `"danila"`:
```python
user_id = arguments.get("user_id", "danila")
```
**Pro:** Minimal change, matches MCP bridge (`vetka_get_user_preferences` already defaults to `"danila"`).
**Con:** Hardcoded username.

### Option B: Normalize user_id mapping
Add a mapping/alias system: `"default"` → `"danila"` for the current user.
Could use env var or config for the active user.

### Option C: Migrate Qdrant data
Upsert a copy of `"danila"` preferences under `"default"` point ID.
**Con:** Two copies to maintain, drift risk.

### Option D: session_init auto-fallback
If `"default"` returns None, try first available user from RAM cache or Qdrant scroll.
**Con:** Implicit, could return wrong user in multi-user scenario.

## Implemented Fix: Option A + B + Auto-Bootstrap

**Status:** APPLIED (MARKER_191.5)

### 1. user_id resolution chain (session_tools.py:165)
```python
user_id = arguments.get("user_id") or os.environ.get("VETKA_USER_ID") or "danila"
```
Priority: explicit arg > `VETKA_USER_ID` env var > fallback `"danila"`

### 2. Auto-bootstrap for new users (session_tools.py:226-245)
If `get_user_preferences()` returns None → auto-create default profile via `create_user_preferences()`, set `preferred_language="ru"`, persist to RAM cache.
New users get `has_preferences: true` on first session.

### Multi-user support
- Set `VETKA_USER_ID=username` in env → works for any user
- New user → auto-bootstrapped profile on first connect
- Existing user → loaded from Qdrant as before

## Architecture Notes

- **AURA Store:** `src/memory/aura_store.py` (683 lines)
- **Schema:** `src/memory/user_memory.py` — 6 preference categories (ViewportPatterns, TreeStructure, ProjectHighlights, CommunicationStyle, TemporalPatterns, ToolUsagePatterns)
- **Storage:** Qdrant `vetka_user_memories` (L2) + RAM cache (L0)
- **Decay:** Per-category (0.01–0.05/week)
- **REFLEX weight:** Signal #4, 0.10
- **MCP bridge:** `vetka_get_user_preferences` defaults to `user_id="danila"` (correct)
- **session_init:** defaults to `user_id="default"` (WRONG — this is the bug)
