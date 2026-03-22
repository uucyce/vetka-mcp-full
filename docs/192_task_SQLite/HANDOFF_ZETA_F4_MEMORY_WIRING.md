# HANDOFF: ZETA-F4 — Wire `_route_to_memory()` to Real Subsystem APIs
**Task:** `tb_1774161488_20`
**Phase:** 195 | **Author:** Opus (Commander) | **Date:** 2026-03-22
**Status:** READY FOR IMPLEMENTATION

---

## 1. Current State

`src/services/smart_debrief.py:120-153` — `_route_to_memory()` detects triggers via regex but only **logs** them. No actual writes to memory subsystems.

```
CURRENT:  text → regex → dict of triggers → logger.debug()
TARGET:   text → regex → dict of triggers → REAL API calls → logger.debug()
```

---

## 2. Exact API for Each Subsystem

### 2.1 REFLEX/CORTEX — `reflex_feedback.record()`

**File:** `src/services/reflex_feedback.py`
**Singleton:** `get_reflex_feedback() → ReflexFeedback`
**Reset (tests):** `reset_reflex_feedback()`
**Storage:** `data/reflex/feedback_log.jsonl` (append-only JSONL, thread-safe)

```python
from src.services.reflex_feedback import get_reflex_feedback

fb = get_reflex_feedback()
fb.record(
    tool_id="vetka_read_file",   # str — tool name from regex match
    success=False,               # bool — False for negative mentions, True for positive
    useful=False,                # bool — same heuristic
    phase_type="research",       # str — from report.domain or "research"
    agent_role="debrief",        # str — fixed "debrief" for this source
    execution_time_ms=0.0,       # float — 0 (not a real execution)
    subtask_id="",               # str — empty (no pipeline subtask)
    extra={"source": "smart_debrief", "text": text[:200]},  # Optional[Dict]
)
# Returns: FeedbackEntry
```

**Sentiment heuristic:** Check if text near tool mention contains `_BUG_PATTERNS` → `success=False, useful=False`. Otherwise → `success=True, useful=True`.

**Existing caller pattern:** `src/services/reflex_integration.py:reflex_post_fc()` uses identical try/except wrapping, same `get_reflex_feedback()` call.

---

### 2.2 AURA — `aura_store.set_preference()`

**File:** `src/memory/aura_store.py`
**Singleton:** `get_aura_store(qdrant_client=None) → AuraStore`
**Storage:** RAM (Gen0) + Qdrant (Gen1), hybrid

```python
from src.memory.aura_store import get_aura_store

store = get_aura_store()  # qdrant_client=None uses global
store.set_preference(
    agent_type="default",                    # str — fixed "default"
    user_id="default",                       # str — fixed "default"
    category="communication_style",          # str — see heuristic below
    key="debrief_ux_insight",                # str — fixed key
    value=text[:500],                        # Any — truncated text
    confidence=0.3,                          # float — low, debrief is noisy
)
```

**Important:** `get_aura_store()` may init Qdrant client internally. If Qdrant is down, it raises. **MUST** wrap in try/except.

**Category heuristic:**
- `re.search(r'UI|UX|viewport|panel|layout', text, re.IGNORECASE)` → `"viewport_patterns"`
- otherwise → `"communication_style"`

**Known categories (from schema):** `communication_style`, `viewport_patterns`, `tree_structure`, `project_highlights`, `temporal_patterns`, `tool_usage_patterns`

---

### 2.3 MGC — `mgc_cache.set_sync()`

**File:** `src/memory/mgc_cache.py`
**Singleton:** `get_mgc_cache() → MGCCache`
**Storage:** Gen0=RAM, Gen1=Qdrant, Gen2=JSON. `set_sync()` → Gen0.

```python
from src.memory.mgc_cache import get_mgc_cache

mgc = get_mgc_cache()
mgc.set_sync(
    key=f"debrief_hot:{file_path}",         # str — namespaced key
    value={"source": "smart_debrief", "text": text[:200], "agent": report.agent_callsign},
    size_bytes=0,                            # int — 0 (metadata only)
)
```

**Critical: use `set_sync()`, NOT `await set()`!** `_route_to_memory` is synchronous. MGC provides both async (`set`/`get`) and sync (`set_sync`/`get_sync`) interfaces. The sync API (MARKER_119.1) is Gen0-only and handles LRU eviction via `_evict_lru_sync()`.

**No explicit `mark_hot()` exists.** Calling `set_sync()` places entry in Gen 0 (RAM). Subsequent `get_sync()` calls invoke `touch()` which increments `access_count`. At `access_count >= 3` (promotion_threshold), entry stays hot permanently.

---

### 2.4 ENGRAM — `engram_cache.put()`

**File:** `src/memory/engram_cache.py`
**Singleton:** `get_engram_cache() → EngramCache`
**Storage:** `data/engram_cache.json` (max 200 entries, LFU eviction)

```python
from src.memory.engram_cache import get_engram_cache

cache = get_engram_cache()
cache.put(
    key=f"{report.agent_callsign}::debrief::learning::{report.domain or 'research'}",
    # str — 4-part hierarchical key: agent::context::action::phase_type
    value=text[:300],                        # str — truncated learning text
    category="pattern",                      # str — see heuristic below
    source_learning_id=f"debrief:{report.session_id}",  # Optional[str]
    match_count=0,                           # int — 0 (fresh entry, not promoted from L2)
)
# Returns: bool — True if new, False if overwrite
```

**Category heuristic:**
- `re.search(r'always|never|принцип|principle|rule|правил', text, re.IGNORECASE)` → `"architecture"` (permanent, TTL=0)
- otherwise → `"pattern"` (TTL=60 days)

**All categories with TTL:** `danger`=permanent, `architecture`=permanent, `pattern`=60d, `optimization`=60d, `tool_select`=30d, `default`=90d.

**Key format convention:** `agent::filename::action::phase_type` — used by existing callers (aura_store L1 promotion, failure_feedback danger promotion).

---

## 3. Ready Code: `_route_to_memory()` with Real Calls

Replace `smart_debrief.py:120-153` with:

```python
def _route_to_memory(text: str, report) -> dict:
    """
    Route text to memory subsystems via regex triggers.
    Each subsystem call is isolated in try/except — never crashes the debrief.
    Returns dict of triggered subsystems for logging/testing.
    """
    triggered = {}

    # REFLEX/CORTEX: tool name mentions → record feedback
    tool_matches = _TOOL_PATTERN.findall(text)
    if tool_matches:
        tools_deduped = list(set(tool_matches))
        triggered["reflex_tools"] = tools_deduped
        is_negative = bool(_BUG_PATTERNS.search(text))
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            fb = get_reflex_feedback()
            for tool_name in tools_deduped:
                fb.record(
                    tool_id=tool_name,
                    success=not is_negative,
                    useful=not is_negative,
                    phase_type=report.domain or "research",
                    agent_role="debrief",
                    execution_time_ms=0.0,
                    subtask_id="",
                    extra={"source": "smart_debrief", "text": text[:200]},
                )
            logger.debug("[SmartDebrief] REFLEX recorded %d tools (neg=%s)", len(tools_deduped), is_negative)
        except Exception as e:
            logger.debug("[SmartDebrief] REFLEX write failed (non-fatal): %s", e)

    # AURA: user/UX mentions → store insight
    if _USER_PATTERN.search(text):
        triggered["aura_ux"] = True
        try:
            from src.memory.aura_store import get_aura_store
            store = get_aura_store()
            cat = "viewport_patterns" if re.search(r"UI|UX|viewport|panel|layout", text, re.IGNORECASE) else "communication_style"
            store.set_preference(
                agent_type="default",
                user_id="default",
                category=cat,
                key="debrief_ux_insight",
                value=text[:500],
                confidence=0.3,
            )
            logger.debug("[SmartDebrief] AURA stored UX insight (cat=%s)", cat)
        except Exception as e:
            logger.debug("[SmartDebrief] AURA write failed (non-fatal): %s", e)

    # MGC: file path mentions → hot file marker
    file_matches = _FILE_PATTERN.findall(text)
    if file_matches:
        files_deduped = list(set(file_matches))
        triggered["mgc_files"] = files_deduped
        try:
            from src.memory.mgc_cache import get_mgc_cache
            mgc = get_mgc_cache()
            for fpath in files_deduped:
                mgc.set_sync(
                    key=f"debrief_hot:{fpath}",
                    value={"source": "smart_debrief", "text": text[:200], "agent": report.agent_callsign},
                    size_bytes=0,
                )
            logger.debug("[SmartDebrief] MGC marked %d hot files", len(files_deduped))
        except Exception as e:
            logger.debug("[SmartDebrief] MGC write failed (non-fatal): %s", e)

    # ENGRAM: pattern/principle mentions → L1 learning entry
    if _LEARNING_PATTERN.search(text):
        triggered["engram_learning"] = True
        try:
            from src.memory.engram_cache import get_engram_cache
            cache = get_engram_cache()
            cat = "architecture" if re.search(r"always|never|принцип|principle|rule|правил", text, re.IGNORECASE) else "pattern"
            cache.put(
                key=f"{report.agent_callsign or 'unknown'}::debrief::learning::{report.domain or 'research'}",
                value=text[:300],
                category=cat,
                source_learning_id=f"debrief:{report.session_id}",
                match_count=0,
            )
            logger.debug("[SmartDebrief] ENGRAM stored learning (cat=%s)", cat)
        except Exception as e:
            logger.debug("[SmartDebrief] ENGRAM write failed (non-fatal): %s", e)

    # CORTEX: fallback — everything goes to general feedback
    if not triggered:
        triggered["cortex_general"] = True
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            fb = get_reflex_feedback()
            fb.record(
                tool_id="__general_debrief__",
                success=True,
                useful=True,
                phase_type=report.domain or "research",
                agent_role="debrief",
                extra={"source": "smart_debrief", "text": text[:200]},
            )
            logger.debug("[SmartDebrief] CORTEX general fallback recorded")
        except Exception as e:
            logger.debug("[SmartDebrief] CORTEX fallback write failed (non-fatal): %s", e)

    return triggered
```

---

## 4. Test Strategy

### 4.1 Mock Pattern — Lazy Imports Require Source-Module Patching

Since all imports are **inside try/except** (lazy), patch at the **source module**, not at `smart_debrief`:

```python
import pytest
from unittest.mock import patch, MagicMock
from src.services.smart_debrief import _route_to_memory
from src.services.experience_report import ExperienceReport


@pytest.fixture
def report():
    return ExperienceReport(
        session_id="test-f4",
        agent_callsign="Zeta",
        domain="engine",
        branch="claude/cut-engine",
        timestamp="2026-03-22T10:00:00Z",
    )


@pytest.fixture
def mock_reflex():
    with patch("src.services.reflex_feedback.get_reflex_feedback") as m:
        fb = MagicMock()
        m.return_value = fb
        yield fb


@pytest.fixture
def mock_aura():
    with patch("src.memory.aura_store.get_aura_store") as m:
        store = MagicMock()
        m.return_value = store
        yield store


@pytest.fixture
def mock_mgc():
    with patch("src.memory.mgc_cache.get_mgc_cache") as m:
        mgc = MagicMock()
        m.return_value = mgc
        yield mgc


@pytest.fixture
def mock_engram():
    with patch("src.memory.engram_cache.get_engram_cache") as m:
        cache = MagicMock()
        m.return_value = cache
        yield cache
```

### 4.2 Test Cases — `TestMemoryRoutingWired`

```python
class TestMemoryRoutingWired:
    """F4: _route_to_memory with real subsystem writes."""

    def test_reflex_negative_tool_feedback(self, report, mock_reflex):
        """Tool mention + bug pattern → record(success=False)."""
        _route_to_memory("vetka_read_file сломан — HTTP 422", report)
        mock_reflex.record.assert_called_once()
        kw = mock_reflex.record.call_args.kwargs
        assert kw["tool_id"] == "vetka_read_file"
        assert kw["success"] is False
        assert kw["useful"] is False
        assert kw["agent_role"] == "debrief"

    def test_reflex_positive_tool_feedback(self, report, mock_reflex):
        """Tool mention without bug → record(success=True)."""
        _route_to_memory("Read tool works great for large files", report)
        mock_reflex.record.assert_called_once()
        kw = mock_reflex.record.call_args.kwargs
        assert kw["tool_id"] == "Read"
        assert kw["success"] is True

    def test_reflex_multiple_tools(self, report, mock_reflex):
        """Multiple tool mentions → one record() per unique tool."""
        _route_to_memory("vetka_read_file and Bash both useful here", report)
        assert mock_reflex.record.call_count == 2

    def test_aura_viewport_category(self, report, mock_aura):
        """UI/UX mention → set_preference(category='viewport_patterns')."""
        _route_to_memory("пользователь не видит warnings в UI", report)
        mock_aura.set_preference.assert_called_once()
        kw = mock_aura.set_preference.call_args.kwargs
        assert kw["category"] == "viewport_patterns"
        assert kw["confidence"] == 0.3
        assert len(kw["value"]) <= 500

    def test_aura_communication_category(self, report, mock_aura):
        """User mention without UI/UX → communication_style."""
        _route_to_memory("user prefers русский в ответах", report)
        mock_aura.set_preference.assert_called_once()
        kw = mock_aura.set_preference.call_args.kwargs
        assert kw["category"] == "communication_style"

    def test_mgc_hot_file(self, report, mock_mgc):
        """File path mention → set_sync() with namespaced key."""
        _route_to_memory("task_board.py:847 has branch detection bug", report)
        mock_mgc.set_sync.assert_called_once()
        kw = mock_mgc.set_sync.call_args.kwargs
        assert kw["key"].startswith("debrief_hot:")
        assert "task_board.py" in kw["key"]
        assert kw["size_bytes"] == 0

    def test_mgc_multiple_files(self, report, mock_mgc):
        """Multiple file mentions → one set_sync() per unique file."""
        _route_to_memory("Both task_board.py and session_tools.py need fixing", report)
        assert mock_mgc.set_sync.call_count == 2

    def test_engram_architecture(self, report, mock_engram):
        """Principle keywords → put(category='architecture')."""
        _route_to_memory("Принцип: always pass branch= from worktree", report)
        mock_engram.put.assert_called_once()
        kw = mock_engram.put.call_args.kwargs
        assert kw["category"] == "architecture"
        assert len(kw["value"]) <= 300
        assert kw["match_count"] == 0

    def test_engram_pattern(self, report, mock_engram):
        """Pattern mention without principle keywords → put(category='pattern')."""
        _route_to_memory("Этот паттерн координации через markdown эффективнее", report)
        mock_engram.put.assert_called_once()
        kw = mock_engram.put.call_args.kwargs
        assert kw["category"] == "pattern"

    def test_cortex_fallback(self, report, mock_reflex):
        """No triggers → general feedback to CORTEX."""
        _route_to_memory("Simple observation about the project", report)
        mock_reflex.record.assert_called_once()
        kw = mock_reflex.record.call_args.kwargs
        assert kw["tool_id"] == "__general_debrief__"

    def test_subsystem_crash_does_not_propagate(self, report):
        """If a subsystem raises, _route_to_memory still returns dict normally."""
        with patch("src.services.reflex_feedback.get_reflex_feedback", side_effect=RuntimeError("Qdrant down")):
            result = _route_to_memory("vetka_read_file broken", report)
        assert "reflex_tools" in result  # trigger detected even though write failed

    def test_text_truncation(self, report, mock_reflex, mock_engram):
        """Long text is truncated: REFLEX extra.text ≤200, ENGRAM value ≤300."""
        long_text = "vetka_read_file " + "x" * 1000 + " always apply this pattern"
        _route_to_memory(long_text, report)
        reflex_kw = mock_reflex.record.call_args.kwargs
        assert len(reflex_kw["extra"]["text"]) <= 200
        engram_kw = mock_engram.put.call_args.kwargs
        assert len(engram_kw["value"]) <= 300

    def test_multiple_subsystems_fire(self, report, mock_reflex, mock_aura, mock_mgc, mock_engram):
        """One text can trigger ALL subsystems simultaneously."""
        text = "vetka_read_file in task_board.py — пользователь should always use this pattern"
        result = _route_to_memory(text, report)
        assert "reflex_tools" in result
        assert "aura_ux" in result
        assert "mgc_files" in result
        assert "engram_learning" in result
        mock_reflex.record.assert_called()
        mock_aura.set_preference.assert_called()
        mock_mgc.set_sync.assert_called()
        mock_engram.put.assert_called()
```

### 4.3 Integration Test

```python
class TestProcessSmartDebriefWired:
    """F4: Full pipeline with wired memory routing."""

    def test_full_pipeline_writes_to_subsystems(self):
        report = ExperienceReport(
            session_id="test-f4-int",
            agent_callsign="Alpha",
            domain="engine",
            branch="claude/cut-engine",
            timestamp="2026-03-22T00:00:00Z",
            lessons_learned=[
                "Q1: task_board.py:847 _detect_current_branch() always returns main. Сломано.",
                "Q2: Handoff docs через markdown — отличный паттерн координации.",
            ],
            recommendations=[
                "Q3: active_agents можно обогатить из AgentRegistry.",
            ],
        )
        mock_board = MagicMock()
        mock_board.add_task.return_value = "tb_auto_1"

        with (
            patch("src.orchestration.task_board.TaskBoard", return_value=mock_board),
            patch("src.services.reflex_feedback.get_reflex_feedback", return_value=MagicMock()),
            patch("src.memory.aura_store.get_aura_store", return_value=MagicMock()),
            patch("src.memory.mgc_cache.get_mgc_cache", return_value=MagicMock()),
            patch("src.memory.engram_cache.get_engram_cache", return_value=MagicMock()),
        ):
            results = process_smart_debrief(report)

        assert len(results["tasks_created"]) >= 1
        assert len(results["memory_routes"]) == 3
        # Verify triggers detected
        triggers = [r["triggered"] for r in results["memory_routes"]]
        assert any("mgc_files" in t for t in triggers)      # task_board.py
        assert any("engram_learning" in t for t in triggers)  # паттерн
```

---

## 5. All Constraints

| # | Constraint | Rationale |
|---|-----------|-----------|
| 1 | **Every subsystem call in its own `try/except`** | One crash must not kill the entire debrief or block other subsystems |
| 2 | **`text[:200]` for REFLEX extra, `[:500]` for AURA, `[:300]` for ENGRAM** | Prevent memory bloat from long debrief answers |
| 3 | **No Qdrant direct dependency in smart_debrief.py** | Import only `get_*()` factories. AURA/MGC use Qdrant internally but smart_debrief never touches it |
| 4 | **Lazy imports inside try/except** | If a subsystem module is broken/missing, others still work |
| 5 | **`agent_role="debrief"` for all REFLEX calls** | Distinguishes debrief feedback from pipeline execution feedback in aggregation |
| 6 | **`confidence=0.3` for AURA** | Debrief insights are noisy — low confidence prevents overriding explicit user preferences |
| 7 | **`match_count=0` for ENGRAM** | Fresh L1 entry, not promoted from L2 — prevents inflated promotion scores |
| 8 | **Regex-only routing, zero LLM calls** | Deterministic, <5ms, no token cost |
| 9 | **Return value unchanged** | `_route_to_memory()` still returns `dict` of triggers — all existing tests pass without modification |
| 10 | **Sync-only API calls** | `_route_to_memory` is sync → `set_sync()` for MGC, not `await set()` |
| 11 | **`bare except` → `except Exception`** | Never catch KeyboardInterrupt/SystemExit |
| 12 | **Log failures at `debug` level** | Non-fatal, no noise in production logs |

---

## 6. Files to Touch

| File | Action |
|------|--------|
| `src/services/smart_debrief.py` | Replace `_route_to_memory()` (lines 120-153) with wired version |
| `tests/test_smart_debrief.py` | Add `TestMemoryRoutingWired` class, remove `@pytest.mark.stale` |

**No new files.** No changes to subsystem modules.

---

## 7. Verification Checklist

- [ ] `python -m pytest tests/test_smart_debrief.py -v` — all green
- [ ] Existing `TestMemoryRouting` (7 tests) still pass — return value unchanged
- [ ] Existing `TestProcessSmartDebrief` (2 tests) still pass
- [ ] New `TestMemoryRoutingWired` (13 tests) pass
- [ ] No `import qdrant_client` in `smart_debrief.py`
- [ ] Each subsystem try/except tested with `side_effect=RuntimeError`
- [ ] Text truncation verified: 200/500/300 limits
- [ ] `grep -c "except Exception" smart_debrief.py` = 5 (one per subsystem)

---

*"F2 built the mousetraps. F4 wires them to real cheese."*
