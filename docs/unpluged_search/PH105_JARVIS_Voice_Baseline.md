# MYCELIUM Research Report: Jarvis Voice Optimization
## WITHOUT VETKA TOOLS (Baseline)

**Generated:** 2026-02-01
**Agent:** Explore (MYCELIUM: Jarvis voice research)
**Tools Used:** grep, glob, file read (raw tools, no VETKA API)
**Duration:** 1m 5s, 17 tool uses, 90.1k tokens

---

## EXECUTIVE SUMMARY

Jarvis **stopped responding** after recent timeout fixes (Phase 104.5/105 commits). Root cause appears to be an **asyncio.wait_for() timeout in LLM generation** that triggers a fallback response without proper state management.

---

## 1. DIAGNOSED ISSUES - WHY JARVIS IS BROKEN NOW

### Issue 1: Aggressive Timeout in jarvis_llm.py (CRITICAL)
**File**: `src/voice/jarvis_llm.py` lines 228-235

```python
try:
    data = await asyncio.wait_for(
        _do_request(),
        timeout=self.config.timeout  # Default 30s
    )
except asyncio.TimeoutError:
    logger.error(f"[JarvisLLM] Ollama timeout after {self.config.timeout}s - preventing hang!")
    return "I'm taking too long to respond. Let me try a simpler answer."
```

### Issue 2: State Machine Breaks on Edge Cases
**File**: `src/api/handlers/jarvis_handler.py` lines 763-809

### Issue 3: Silent Failure in LLM Response Path
**File**: `src/api/handlers/jarvis_handler.py` lines 830-873

### Issue 4: Missing Ollama Server Check
`check_ollama()` method exists but **never called** in `generate()` path.

### Issue 5: TTS Mode Hardcoded to Quality (Slower)
**File**: `src/api/handlers/jarvis_handler.py` line 394
```python
TTS_MODE = "quality"  # 5-6s instead of 1s
```

---

## 2. COMPLETE VOICE FLOW MAPPING

```
CLIENT: startListening() → jarvis_audio_chunk → stopListening()
        ↓
BACKEND: jarvis_listen_stop(sid, data)
        ↓
    STT: mlx_whisper.transcribe() → transcript (2-5s)
        ↓
    EDGE CASES: confidence check → EARLY RETURN if low ⚠️
        ↓
    LLM: timeout_wrapped_prediction() → jarvis_llm.generate() (2-30s)
        ↓
    TTS: Qwen3TTSClient.synthesize() (5-6s quality mode)
        ↓
    EMIT: jarvis_audio { audio: base64 }
```

**Current Latency:** 9-16s normal, 30s+ on timeout

---

## 3. T9 PREDICTION STATUS

**Code exists but NEVER CALLED:**
- `_predict_draft()` in jarvis_handler.py lines 1086-1395
- Client ready for `jarvis_prediction` events
- Just needs wiring to STT→LLM gap

---

## 4. PROPOSED MARKERS

| Marker | Priority | Purpose |
|--------|----------|---------|
| MARKER_105_OLLAMA_TIMEOUT_CRITICAL | P1 | Fix timeout 30s→10s |
| MARKER_105_STATE_RECOVERY | P1 | Fix edge case returns |
| MARKER_105_TTS_FAST_MODE | P2 | Switch to fast TTS |
| MARKER_105_AUDIO_CACHE_SPARSE | P2 | Pre-rendered responses |
| MARKER_105_T9_PREDICTION_ACTIVATE | P3 | Wire T9 to STT gap |
| MARKER_105_CAM_FILLER_CACHE | P3 | "hmm", "let me think" |
| MARKER_105_CONTEXT_MODULATION | P3 | Camera + artifact context |
| MARKER_105_QWEN3_PHONEQUALITY | P4 | 16kHz phone quality |

---

## 5. OPTIMIZATION POTENTIAL

**Current:** 30s+ (timeout failure)
**Target:** 2-4s (with all optimizations)

- LLM timeout fix: 30s → 5s
- Fast TTS: 5-6s → 1s
- Audio cache: 1s → 0.2s
- T9 prediction: perceived instant

---

**MARKER:** MYCELIUM_RESEARCH_NO_VETKA_TOOLS_BASELINE
