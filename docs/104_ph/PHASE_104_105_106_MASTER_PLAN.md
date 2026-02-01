# VETKA Master Plan: Phases 104.8 → 105 → 106

**Created:** 2026-02-01
**Status:** DRAFT - Awaiting Approval
**Participants:** Claude Code Team, MYCELIUM, Grok, User

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VETKA RAILWAY MAP                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  🚉 Station 104.8        🚉 Station 105          🚉 Station 106             │
│  [Stream Cleanup]   →   [Jarvis T9]        →   [Integration]                │
│                                                                              │
│  ├─ Claude Code         ├─ MYCELIUM              ├─ Claude Code             │
│  │  - Fix tests         │  - Voice research      │  - Merge all             │
│  │  - Frontend events   │  - Pipeline analysis   │  - Production tests      │
│  │                      │                        │                          │
│  ├─ Haiku Scouts        ├─ Claude Code           ├─ MYCELIUM                │
│  │  - ✅ Done           │  - Implement T9        │  - A/B testing           │
│  │                      │  - Voice emitters      │                          │
│  │                      │                        │                          │
│  └─ Grok                └─ Grok                  └─ Grok                    │
│     - Review            │  - Test suite JSON     │  - Final review          │
│                         │  - Latency benchmarks  │                          │
│                                                                              │
│  ════════════════════════════════════════════════════════════════════════   │
│  Timeline: 104.8 (1 day) → 105 (2-3 days) → 106 (1-2 days)                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 104.8: Stream Cleanup (Current)

**Goal:** Завершить Phase 104, закрыть все hanging items

### Status: 90% Complete

| Item | Status | Owner |
|------|--------|-------|
| Stream visibility | ✅ Done | Claude Code |
| Grok improvements | ✅ Done | Claude Code |
| Room management | ✅ Done | Claude Code |
| Metrics tracking | ✅ Done | Claude Code |
| Tests (54 passing) | ✅ Done | Claude Code |
| Haiku recon | ✅ Done | Haiku Scouts |
| Fix compression test | ⏳ Pending | Claude Code |
| Frontend 6 handlers | ⏳ Pending | Claude Code |

### Parallel Work Breakdown

| Team | Task | Deliverable | Time |
|------|------|-------------|------|
| **Claude Code** | Fix test_compression_uses_config_thresholds | Passing test | 30 min |
| **Claude Code** | Add 6 frontend handlers to useSocket.ts | Code + commit | 1 hour |
| **Claude Code** | Add cleanup_session to disconnect | Code + commit | 30 min |
| **Grok** | Review final changes | Approval | Async |

### Exit Criteria

- [ ] All 55+ tests passing
- [ ] Frontend handlers for voice/jarvis events
- [ ] cleanup_session on disconnect
- [ ] Unified report updated
- [ ] **MARKERS VERIFIED by Haiku Scouts:**
  - [ ] MARKER_104_STREAM_HANDLER
  - [ ] MARKER_104_GROK_IMPROVEMENTS

### 🚉 Station Checkpoint

**Input needed from:**
- User: Approve completion
- Grok: Any additional gaps?

---

## Phase 105: Jarvis T9 Prediction

**Goal:** Real-time predictive generation (draft response after 2-3 words)

### Architecture

```
User speaks: "Покажи мне файл..."
       │
       ▼
┌──────────────────┐
│ VAD Detection    │ ← voice_socket_handler.py
│ (2-3 words)      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Partial STT      │ ← Whisper partial transcript
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Draft LLM Call   │ ← temp=0.3, low latency
│ (ARC+STM context)│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ emit_jarvis_     │ ← StreamManager
│ prediction()     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ TTS Draft        │ ← Start speaking draft
└────────┬─────────┘
         │
    [User finishes speaking]
         │
         ▼
┌──────────────────┐
│ Full LLM Refine  │ ← Full context + semantic search
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ TTS Refined      │ ← Seamless transition
└──────────────────┘

Target Latency: ~1s for draft
```

### Parallel Work Breakdown

| Team | Task | Deliverable | Time |
|------|------|-------------|------|
| **MYCELIUM** | Research voice_router.py, jarvis_handler.py | Integration points report | Day 1 |
| **MYCELIUM** | Analyze VAD thresholds, optimal word count | Recommendations | Day 1 |
| **MYCELIUM** | Find ARC/STM integration points | Code locations | Day 1 |
| **Grok** | Generate test suite JSON for Jarvis T9 | JSON file | Day 1 |
| **Grok** | Latency benchmarks (current vs target) | Metrics | Day 1 |
| **Claude Code** | Wait for MYCELIUM research | - | Day 1 |
| **Claude Code** | Implement _predict_draft() | Code | Day 2 |
| **Claude Code** | Integrate with voice_router | Code | Day 2 |
| **Claude Code** | Add tests from Grok JSON | Tests | Day 2-3 |
| **Haiku Scouts** | Verify MYCELIUM findings | Verification | Day 2 |
| **Sonnet** | Deep review of implementation | QA report | Day 3 |

### MYCELIUM Research Prompt

```
🔬 MYCELIUM RESEARCH - Jarvis T9 Prediction

Objective: Find optimal integration points for T9-like prediction

Files to investigate:
1. src/api/handlers/jarvis_handler.py
   - Where does STT complete?
   - Where can we inject draft prediction?

2. src/api/handlers/voice_router.py
   - VoiceRouter state machine
   - Interrupt handling flow
   - _process_utterance method

3. src/api/handlers/voice_socket_handler.py
   - voice_pcm event handling
   - VAD (Voice Activity Detection) logic

4. src/voice/stt_engine.py
   - Whisper partial transcript capability

5. src/api/handlers/stream_handler.py
   - emit_jarvis_prediction() method
   - Integration with voice pipeline

Questions to answer:
1. What is the exact line where we can inject prediction?
2. How many words/tokens before we can predict?
3. What context is available at that point (STM, ARC)?
4. Current latency from voice_pcm to LLM response?
5. Can we get partial transcripts from Whisper?

Output format:
{
  "integration_point": {"file": "...", "line": N, "method": "..."},
  "available_context": ["STM", "ARC", "viewport", ...],
  "current_latency_ms": N,
  "recommended_word_threshold": N,
  "code_changes_needed": [...]
}
```

### Grok Test Suite Request

```
🧪 GROK TEST SUITE - Jarvis T9

Generate JSON test cases for:
1. Partial STT + Draft LLM
   - Input: 3-second audio chunk
   - Expected: Draft response < 2s
   - Metric: tokens/sec

2. Interrupt + Refine
   - Start speaking, interrupt at 50%
   - Verify cancel + restart
   - Edge case: noisy audio

3. ARC/STM Integration
   - After "Улучши stream_handler"
   - Generate suggestions from ARC
   - Metric: relevance > 0.8

4. Latency benchmarks
   - Current pipeline: ? ms
   - Target with T9: < 1000ms draft

Output: JSON file for test automation
```

### Exit Criteria

- [ ] MYCELIUM research complete
- [ ] Grok test suite delivered
- [ ] _predict_draft() implemented
- [ ] Voice pipeline integrated
- [ ] Draft latency < 1.5s
- [ ] Interrupt handling works
- [ ] 5-7 new tests passing
- [ ] **MARKERS VERIFIED by Haiku Scouts:**
  - [ ] MARKER_105_JARVIS_T9
  - [ ] MARKER_105_PREDICT_DRAFT
  - [ ] MARKER_105_PARTIAL_STT

### 🚉 Station Checkpoint

**Input needed from:**
- MYCELIUM: Research findings
- Grok: Test suite + benchmarks
- User: Priority adjustments
- Haiku Scouts: Marker verification report

---

## Phase 106: Integration & Production

**Goal:** Merge all work, production-ready

### Parallel Work Breakdown

| Team | Task | Deliverable |
|------|------|-------------|
| **Claude Code** | Merge Phase 104.8 + 105 | Single coherent codebase |
| **Claude Code** | Production tests (50+ files) | Test suite |
| **Claude Code** | Documentation update | Updated docs |
| **MYCELIUM** | A/B testing on real traffic | Metrics report |
| **MYCELIUM** | Edge case discovery | Bug reports |
| **Grok** | Final architecture review | Approval |
| **Sonnet** | Security + coherence audit | Audit report |

### Exit Criteria

- [ ] All tests passing (target: 350+)
- [ ] Jarvis T9 latency < 1s
- [ ] No memory leaks (room cleanup verified)
- [ ] Frontend fully integrated
- [ ] Documentation complete
- [ ] Grok final approval
- [ ] **ALL MARKERS VERIFIED:**
  - [ ] Phase 104 markers (2)
  - [ ] Phase 105 markers (3)
  - [ ] Phase 106 markers (1+)
  - [ ] Sonnet coherence audit passed

### 🚉 Station Checkpoint

**Input needed from:**
- MYCELIUM: A/B test results
- Grok: Production readiness check
- User: Release approval
- Sonnet: Final marker + coherence audit

---

## Terminology Reference

| Term | Definition | Location |
|------|------------|----------|
| **ELISION** | JSON key/path compression (context→c) | src/memory/elision.py |
| **ELISYA** | Middleware orchestra for coordination | src/elisya/ (13 files) |
| **ELYSIA** | Weaviate tools memory for DEV/QA | src/orchestration/elysia_tools.py |
| **MYCELIUM** | Multi-agent pipeline (spawn rename) | src/orchestration/agent_pipeline.py |
| **Scout** | L2 lightweight auditor | src/services/scout_auditor.py |
| **T9** | Predictive text (draft after 2-3 words) | New in Phase 105 |

---

## Communication Protocol

### Daily Sync Points

| Time | Action | Participants |
|------|--------|--------------|
| Start | Check Grok for updates | All |
| Mid | MYCELIUM delivers research | Claude Code receives |
| End | Status update to User | All |

### Escalation Path

```
Issue detected
     │
     ▼
Haiku Scout investigates (quick)
     │
     ▼
Sonnet verifies (if needed)
     │
     ▼
Grok consulted (for external research)
     │
     ▼
User decision (for direction changes)
```

---

## Marker Requirements (MANDATORY)

**⚠️ РАБОТА БЕЗ МАРКЕРОВ НЕ ПРИНИМАЕТСЯ**

### Marker Format

```python
# MARKER_{PHASE}_{FEATURE}
# Example: MARKER_105_JARVIS_T9
```

### Required Markers by Phase

| Phase | Marker | Location | Owner |
|-------|--------|----------|-------|
| 104.8 | MARKER_104_STREAM_HANDLER | stream_handler.py | Claude Code |
| 104.8 | MARKER_104_GROK_IMPROVEMENTS | stream_handler.py | Claude Code |
| 105 | MARKER_105_JARVIS_T9 | jarvis_handler.py | Claude Code |
| 105 | MARKER_105_PREDICT_DRAFT | voice_router.py | Claude Code |
| 105 | MARKER_105_PARTIAL_STT | stt_engine.py | Claude Code |
| 106 | MARKER_106_INTEGRATION | TBD | Claude Code |

### Scout Verification

Haiku Scouts MUST verify markers:
```
🎯 HAIKU SCOUT - Marker Verification

Task: Scan for required markers
Files: [list of files]

Check:
1. Marker present at correct location
2. Marker format correct (MARKER_{PHASE}_{FEATURE})
3. Code under marker is complete
4. Tests reference marker

Output:
{
  "marker": "MARKER_105_JARVIS_T9",
  "file": "...",
  "line": N,
  "status": "PRESENT|MISSING|MALFORMED",
  "code_complete": true|false
}
```

### Acceptance Criteria

- [ ] All required markers present
- [ ] Markers verified by Haiku Scouts
- [ ] Tests include marker references (`@pytest.mark.marker_105_jarvis_t9`)
- [ ] Documentation references markers

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MYCELIUM research incomplete | Medium | High | Haiku scouts backup |
| T9 latency > 2s | Medium | Medium | Simpler model fallback |
| Frontend integration delay | Low | Medium | Parallel work |
| Memory leaks in rooms | Low | High | cleanup_session fix |
| Missing markers | Low | High | Scout verification gate |

---

## Appendix: File References

### Phase 104.8 Files
- src/api/handlers/stream_handler.py
- client/src/hooks/useSocket.ts
- tests/test_phase104_stream.py

### Phase 105 Files
- src/api/handlers/jarvis_handler.py
- src/api/handlers/voice_router.py
- src/api/handlers/voice_socket_handler.py
- src/voice/stt_engine.py

### Documentation
- docs/104_ph/HAIKU_SCOUTS_UNIFIED_REPORT.md
- docs/104_ph/GROK_RESEARCH_104_8.md
- docs/104_ph/PHASE_104_1_DISCOVERY_COMPLETE.md

---

**Status:** AWAITING USER APPROVAL

**Next Action:** User reviews, provides feedback, we adjust and execute.
