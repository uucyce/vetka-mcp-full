# Handoff: Zeta F4 — Wire Memory Routing to Real Subsystem APIs
**Task:** tb_1774161488_20
**Date:** 2026-03-22
**From:** Opus (Zeta)
**To:** Next agent implementing F4

---

## What Exists

`src/services/smart_debrief.py` has `_route_to_memory()` that detects triggers via regex:
- REFLEX: tool mentions → `triggered["reflex_tools"]`
- AURA: user/UX mentions → `triggered["aura_ux"]`
- MGC: file paths → `triggered["mgc_files"]`
- ENGRAM: patterns/principles → `triggered["engram_learning"]`
- CORTEX: fallback → `triggered["cortex_general"]`

**Currently:** Logs triggers, returns dict. Does NOT call subsystem APIs.

**Need:** Replace detection-only with actual writes to each subsystem.

---

## Exact API Calls to Add

### 1. REFLEX/CORTEX — Tool feedback

**File:** `src/services/reflex_feedback.py`
**Singleton:** `get_reflex_feedback()`

```python
from src.services.reflex_feedback import get_reflex_feedback

fb = get_reflex_feedback()
fb.record(
    tool_id="vetka_read_file",       # from regex match
    success=False,                    # bug = negative, workaround = context-dependent
    useful=False,
    phase_type="research",            # from report context
    agent_role=report.agent_callsign, # "Alpha", "Beta", etc.
    extra={"source": "smart_debrief", "text": text[:200]},
)
```

**Logic:** If debrief mentions tool as broken/сломан → `success=False, useful=False`.
If mentions tool as working well → `success=True, useful=True`.
Detect sentiment from context (near "сломан/broken/error" = negative, near "работает/works/лучше" = positive).

### 2. ENGRAM — Learning/pattern store

**File:** `src/memory/engram_cache.py`
**Singleton:** `get_engram_cache()`

```python
from src.memory.engram_cache import get_engram_cache

cache = get_engram_cache()
cache.put(
    key=f"debrief::{report.agent_callsign}::{hash(text) % 10000}",
    value=text[:500],                  # the learning text
    category="pattern",                # or "optimization", "architecture"
    source_learning_id=f"debrief:{report.session_id}",
)
```

**Categories:** `pattern` for coding patterns, `optimization` for performance,
`architecture` for system design insights, `danger` for things to avoid.

### 3. AURA — User/UX insights

**File:** `src/memory/aura_store.py`
**Singleton:** `get_aura_store()`

```python
from src.memory.aura_store import get_aura_store

aura = get_aura_store()
aura.set_preference(
    agent_type="claude_code",
    user_id="default",
    category="ux_insights",           # new category for debrief UX observations
    key=f"debrief_{report.session_id[:8]}",
    value=text[:300],
    confidence=0.6,
)
```

**Note:** AURA expects Qdrant client. If Qdrant unavailable, RAM cache still works.
Use `try/except` — AURA failure must not crash smart_debrief.

### 4. MGC — File heat markers

**File:** `src/memory/mgc_cache.py`
**Singleton:** `get_mgc_cache()`

```python
from src.memory.mgc_cache import get_mgc_cache

mgc = get_mgc_cache()
for file_path in file_matches:
    # Touch to mark as hot (3+ touches = stays in Gen0)
    existing = mgc.get(f"debrief_hot:{file_path}")
    if existing is None:
        mgc.set(f"debrief_hot:{file_path}", {
            "reason": text[:200],
            "agent": report.agent_callsign,
            "session": report.session_id,
        })
    # Subsequent touches auto-increment access_count
```

---

## Implementation Pattern

Replace current `_route_to_memory()` in `smart_debrief.py`:

```python
def _route_to_memory(text: str, report) -> dict:
    triggered = {}

    # REFLEX: tool mentions
    tool_matches = _TOOL_PATTERN.findall(text)
    if tool_matches:
        triggered["reflex_tools"] = list(set(tool_matches))
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            fb = get_reflex_feedback()
            is_negative = _BUG_PATTERNS.search(text) is not None
            for tool in set(tool_matches):
                fb.record(
                    tool_id=tool,
                    success=not is_negative,
                    useful=not is_negative,
                    phase_type="research",
                    agent_role=report.agent_callsign or "unknown",
                    extra={"source": "smart_debrief"},
                )
        except Exception:
            pass  # Never crash routing

    # AURA: user/UX mentions
    if _USER_PATTERN.search(text):
        triggered["aura_ux"] = True
        try:
            from src.memory.aura_store import get_aura_store
            aura = get_aura_store()
            aura.set_preference(
                agent_type="claude_code",
                user_id="default",
                category="ux_insights",
                key=f"debrief_{report.session_id[:8]}",
                value=text[:300],
                confidence=0.6,
            )
        except Exception:
            pass

    # MGC: file path mentions
    file_matches = _FILE_PATTERN.findall(text)
    if file_matches:
        triggered["mgc_files"] = list(set(file_matches))
        try:
            from src.memory.mgc_cache import get_mgc_cache
            mgc = get_mgc_cache()
            for fp in set(file_matches):
                mgc.set(f"debrief_hot:{fp}", {
                    "reason": text[:200],
                    "agent": report.agent_callsign,
                })
        except Exception:
            pass

    # ENGRAM: pattern/principle mentions
    if _LEARNING_PATTERN.search(text):
        triggered["engram_learning"] = True
        try:
            from src.memory.engram_cache import get_engram_cache
            cache = get_engram_cache()
            cache.put(
                key=f"debrief::{report.agent_callsign}::{hash(text) % 10000}",
                value=text[:500],
                category="pattern",
                source_learning_id=f"debrief:{report.session_id}",
            )
        except Exception:
            pass

    # CORTEX: fallback
    if not triggered:
        triggered["cortex_general"] = True

    return triggered
```

---

## Constraints

1. **Every subsystem call wrapped in try/except** — smart_debrief must never crash
2. **No Qdrant dependency** — AURA falls back to RAM, MGC falls back to JSON
3. **Existing tests marked @stale** — Sigma marked them, need to update mocks after wiring
4. **Text truncation** — max 500 chars to ENGRAM, 300 to AURA, 200 to MGC
5. **Singleton access** — always use `get_*()` factories, never construct directly

---

## Test Strategy

After wiring, tests should mock each subsystem singleton:
```python
with patch("src.services.reflex_feedback.get_reflex_feedback") as mock_fb, \
     patch("src.memory.engram_cache.get_engram_cache") as mock_eng, \
     patch("src.memory.aura_store.get_aura_store") as mock_aura, \
     patch("src.memory.mgc_cache.get_mgc_cache") as mock_mgc:
    ...
```

Verify: each trigger calls the right subsystem with correct params.

---

*"Мышеловки расставлены. Осталось подключить провода."*
