# MYCELIUM Research Report: Jarvis Voice Optimization
## WITH VETKA TOOLS (MCP Integration)

**Generated:** 2026-02-01
**Agent:** Explore (MYCELIUM+VETKA: Jarvis research)
**Tools Used:** VETKA API semantic search, grep fallback, file read
**Search Method:** vetka_api (primary), qdrant_direct (fallback)

---

## EXECUTIVE SUMMARY

**ROOT CAUSE IDENTIFIED:** The `timeout_wrapped_prediction()` function is called with **T9_MODEL_TIMEOUT_MS=2000ms** (2 seconds), but this is applied to **full LLM generation** which requires 30 seconds!

The issue is **NOT** a complete breakage but a **critical architectural mismatch**: T9 timeout framework misapplied to full Ollama LLM calls.

---

## 1. DIAGNOSED ISSUES

### Issue 1: CRITICAL - Wrong Timeout Applied
**Location:** `jarvis_handler.py` line 36 + lines 838-846

```python
T9_MODEL_TIMEOUT_MS = 2000  # 2 seconds - DESIGNED FOR T9 DRAFT PREDICTION!

# But applied to FULL LLM generation:
result = await timeout_wrapped_prediction(
    predict_func=_generate_llm_response,  # This calls llm.generate() which needs 30s!
    partial_input=transcript,
    timeout_ms=T9_MODEL_TIMEOUT_MS  # 2 seconds - WAY TOO SHORT!
)
```

**Why it breaks:**
1. Ollama needs 5-15s for voice response
2. jarvis_llm.py has timeout=30s (correct)
3. But jarvis_handler.py wraps it with 2s timeout!
4. TimeoutError fires, falls back to template

### Issue 2: Type Mismatch in Wrapper
**Location:** `jarvis_handler.py` lines 242-252

Wrapper expects `(response, confidence)` tuple, but `llm.generate()` returns plain string.

### Issue 3: Architectural Mismatch
T9 prediction framework (2s timeout, draft responses) misapplied to full LLM generation (30s timeout, complete responses).

---

## 2. THE FIX (3 lines!)

```python
# Option A: Change timeout
T9_MODEL_TIMEOUT_MS = 2000
JARVIS_LLM_TIMEOUT_MS = 30000  # ADD THIS

# Option B: Remove wrapper for full LLM
response_text = await llm.generate(transcript, session.user_id, context)
# Don't wrap with timeout_wrapped_prediction()
```

---

## 3. PROPOSED MARKERS

| Marker | Priority | Change |
|--------|----------|--------|
| MARKER_105_JARVIS_TIMEOUT_FIX | CRITICAL | 2s → 30s for LLM |
| MARKER_105_LLM_DIRECT_CALL | HIGH | Remove wrapper for LLM |
| MARKER_105_T9_PREDICTION_SEPARATE | MEDIUM | Separate module for T9 |
| MARKER_105_AUDIO_QUALITY_REDUCTION | MEDIUM | 16kHz phone quality |
| MARKER_105_PRE_RENDERED_CACHE | LOW | Voice cache system |

---

## 4. FILES TO MODIFY

| File | Line | Change |
|------|------|--------|
| jarvis_handler.py | 36 | Add JARVIS_LLM_TIMEOUT_MS=30000 |
| jarvis_handler.py | 838-852 | Remove timeout wrapper OR use longer timeout |
| jarvis_handler.py | 828-859 | Simplify to direct async/await |
| tts_engine.py | 630-642 | Add 16kHz sample rate option |

---

## 5. COMPARISON: With vs Without VETKA Tools

| Aspect | Without VETKA Tools | With VETKA Tools |
|--------|---------------------|------------------|
| Root cause | "Aggressive timeout" (vague) | **2s T9 timeout applied to 30s LLM** (precise) |
| Fix complexity | "Reduce to 10s" (wrong) | **3-line fix: separate T9 vs LLM timeout** |
| Architecture insight | Generic flow map | **Identified misapplied framework** |
| Search quality | Raw grep patterns | **Semantic understanding of relationships** |

**Key difference:** VETKA Tools found the **architectural mismatch** - T9 framework misapplied to full LLM.

---

## 6. IMPLEMENTATION PRIORITY

**PHASE 1 (RESTORE):**
1. Change T9_MODEL_TIMEOUT_MS from 2000 → 30000 for LLM
2. OR add separate JARVIS_LLM_TIMEOUT_MS = 30000
3. Test basic voice

**PHASE 2 (IMPROVE):**
4. Extract T9 prediction to separate module
5. Reduce TTS sample rate to 16kHz

**PHASE 3 (OPTIMIZE):**
6. Build voice response cache
7. Add draft prediction UI

---

**MARKER:** MYCELIUM_RESEARCH_WITH_VETKA_TOOLS
**Agent ID:** a22fe0b
