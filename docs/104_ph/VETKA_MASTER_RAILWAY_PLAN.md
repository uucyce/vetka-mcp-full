# VETKA Master Railway Plan

**Created:** 2026-02-01
**Status:** AWAITING USER APPROVAL
**Participants:** Claude Code Team, MYCELIUM, Grok, Haiku Scouts, Sonnet Verifiers

---

## Railway Overview

```
══════════════════════════════════════════════════════════════════════════════════════
                              VETKA RAILWAY v2.0
══════════════════════════════════════════════════════════════════════════════════════

  🚉 104.8           🚉 104.9              🚉 105               🚉 106
  [Stream Fix]  →   [Persistence]    →   [Jarvis T9]     →   [Production]
  ───────────       ─────────────        ───────────         ────────────
  │                 │                    │                   │
  ├─ Buffer fix     ├─ Artifact save     ├─ Predict draft    ├─ Merge all
  ├─ 6 handlers     ├─ Chat history      ├─ Voice integrate  ├─ Pre-merge checks
  ├─ cleanup()      ├─ Visual subtle     ├─ TTS fallback     ├─ Security audit
  └─ Tests fix      └─ Redis/Disk        ├─ Voice UI         ├─ 350+ tests
                                         └─ Edge cases       └─ Monitoring

  Voice Stack:                           Security:
  ├─ Qwen 3 TTS (primary)               ├─ JWT room validation
  ├─ Edge TTS (fallback)                └─ Artifact sanitization
  └─ Piper (offline)

══════════════════════════════════════════════════════════════════════════════════════
  Total: 5-7 days │ Coherence: 95% │ Tests: 350+ │ Markers: 26 │ Grok Score: 10/10
══════════════════════════════════════════════════════════════════════════════════════
```

---

## Station 104.8: Stream Cleanup

**Goal:** Закрыть все hanging items Phase 104

### Current Status

| Item | Status | Action Needed |
|------|--------|---------------|
| StreamManager core | ✅ Done | - |
| Grok improvements | ✅ Done | - |
| Room management | ✅ Done | - |
| Metrics tracking | ✅ Done | - |
| Tests 54 passing | ✅ Done | - |
| Haiku recon | ✅ Done | - |
| Fix compression test | ⏳ Pending | Test JSON, not strings |
| Frontend 6 handlers | ⏳ Pending | useSocket.ts |
| cleanup_session | ⏳ Pending | disconnect handler |
| Buffer → deque | ⏳ Pending | O(1) instead O(n) |

### Parallel Work

| Team | Task | Time | Marker |
|------|------|------|--------|
| **Claude Code** | Fix test (JSON data, not "x"*60) | 30 min | MARKER_104_TEST_FIX |
| **Claude Code** | Add 6 handlers to useSocket.ts | 1 hour | MARKER_104_FRONTEND |
| **Claude Code** | Add cleanup_session to disconnect | 30 min | MARKER_104_CLEANUP |
| **Claude Code** | Replace list → deque for buffer | 30 min | MARKER_104_BUFFER |
| **Haiku Scouts** | Verify all markers present | 30 min | - |

### Frontend Handlers to Add (useSocket.ts)

```typescript
// MARKER_104_FRONTEND - Add these 6 handlers
socket.on('voice_transcript', (data) => { ... });
socket.on('jarvis_interrupt', (data) => { ... });
socket.on('jarvis_prediction', (data) => { ... });
socket.on('stream_error', (data) => { ... });
socket.on('room_joined', (data) => { ... });
socket.on('room_left', (data) => { ... });
```

### Exit Criteria

- [ ] All 55+ tests passing
- [ ] 6 frontend handlers added
- [ ] cleanup_session on disconnect
- [ ] Buffer uses deque (O(1))
- [ ] Markers verified:
  - [ ] MARKER_104_STREAM_HANDLER
  - [ ] MARKER_104_GROK_IMPROVEMENTS
  - [ ] MARKER_104_TEST_FIX
  - [ ] MARKER_104_FRONTEND
  - [ ] MARKER_104_CLEANUP
  - [ ] MARKER_104_BUFFER

### 🚉 Station Checkpoint 104.8

**Input needed:**
- User: Approve completion
- Grok: Any gaps?

---

## Station 104.9: Persistence Foundations

**Goal:** Артефакты и чат-история сохраняются на диск

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PERSISTENCE FLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Agent generates artifact (>500 chars)                          │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────┐                                               │
│  │ create_disk_ │ → /artifacts/{name}.{ext}                     │
│  │ artifact()   │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ ARTIFACT_    │ → Socket.IO → UI показывает approval          │
│  │ APPROVAL     │    L1: yes/no, L2: edit, L3: reject           │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ save_chat_   │ → /data/chat_history/{workflow_id}.json       │
│  │ history()    │    (fallback если нет узла)                   │
│  └──────────────┘                                               │
│                                                                  │
│  Buffer Strategy:                                                │
│  - Primary: Redis (TTL 300s, max 1000)                          │
│  - Fallback: Disk JSON                                          │
│  - Compression: ELISION для >200 chars                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Parallel Work

| Team | Task | Time | Marker |
|------|------|------|--------|
| **Claude Code** | Implement save_chat_history() | 1 hour | MARKER_104_CHAT_SAVE |
| **Claude Code** | Implement create_disk_artifact() | 1 hour | MARKER_104_ARTIFACT_DISK |
| **Claude Code** | Add ARTIFACT_APPROVAL event | 30 min | MARKER_104_ARTIFACT_EVENT |
| **Claude Code** | Subtle visual in tree_renderer | 30 min | MARKER_104_VISUAL |
| **Claude Code** | Redis/Disk fallback logic | 1 hour | MARKER_104_PERSISTENCE |
| **MYCELIUM** | Research existing artifact code | 1 hour | Report |
| **Grok** | Review persistence latency | Async | Benchmarks |
| **Haiku Scouts** | Verify all markers | 30 min | - |

### Code Templates

#### save_chat_history()
```python
# MARKER_104_CHAT_SAVE
async def save_chat_history(workflow_id: str, events: list, sid: str):
    """Save chat history to disk when no node exists."""
    path = f"data/chat_history/{workflow_id}.json"
    data = {
        "workflow_id": workflow_id,
        "events": events,
        "sid": sid,
        "timestamp": datetime.now().isoformat()
    }

    # Try Redis first
    if redis_available():
        await redis.setex(f"chat:{workflow_id}", 300, json.dumps(data))
    else:
        # Fallback to disk
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f)

    logger.info(f"[PERSISTENCE] Chat saved: {workflow_id}")
```

#### create_disk_artifact()
```python
# MARKER_104_ARTIFACT_DISK
async def create_disk_artifact(
    name: str,
    content: str,
    artifact_type: str,
    workflow_id: str,
    socketio=None
):
    """Create artifact and save to disk if >500 chars."""
    if len(content) < 500:
        return None  # Too small for disk

    # Determine extension
    ext_map = {"python": "py", "typescript": "ts", "markdown": "md"}
    ext = ext_map.get(artifact_type, "txt")

    # Save to disk
    path = f"artifacts/{name}.{ext}"
    os.makedirs("artifacts", exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

    # Emit approval request
    if socketio:
        await socketio.emit('artifact_approval', {
            'path': path,
            'name': name,
            'size': len(content),
            'level': 'L1',  # Initial approval level
            'workflow_id': workflow_id
        }, namespace='/vetka')

    # Link to chat history
    await save_chat_history(workflow_id, [{
        "type": "artifact_created",
        "path": path,
        "name": name
    }], sid=None)

    logger.info(f"[ARTIFACT] Created: {path} ({len(content)} chars)")
    return path
```

### Visual Integration (Subtle, No Bright Colors)

```typescript
// tree_renderer.tsx - MARKER_104_VISUAL
// Артефакты отличаются subtle серой рамкой
const ArtifactNode = ({ artifact }) => (
  <div
    className="artifact-node"
    style={{
      border: '1px solid #333',      // Subtle gray border
      backgroundColor: '#1a1a1a',    // Dark background
      opacity: 0.9,                  // Slightly transparent
      borderRadius: '4px'
    }}
  >
    <FolderIcon style={{ color: '#666' }} />  {/* Gray icon */}
    <span>{artifact.name}</span>
  </div>
);
```

### Exit Criteria

- [ ] save_chat_history() working
- [ ] create_disk_artifact() working (>500 chars)
- [ ] ARTIFACT_APPROVAL event emits
- [ ] Visual subtle (gray, no bright colors)
- [ ] Redis fallback to disk works
- [ ] Tests for persistence (5+)
- [ ] Markers verified:
  - [ ] MARKER_104_CHAT_SAVE
  - [ ] MARKER_104_ARTIFACT_DISK
  - [ ] MARKER_104_ARTIFACT_EVENT
  - [ ] MARKER_104_VISUAL
  - [ ] MARKER_104_PERSISTENCE

### 🚉 Station Checkpoint 104.9

**Input needed:**
- MYCELIUM: Existing artifact code analysis
- Grok: Persistence latency OK?
- User: Visual style approved?

---

## Station 105: Jarvis T9 Prediction

**Goal:** Real-time predictive response after 2-3 words

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     JARVIS T9 FLOW                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User speaks: "Покажи мне файл..."                              │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────┐                                               │
│  │ VAD (2-3     │ ← voice_socket_handler.py                     │
│  │ words)       │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ Partial STT  │ ← Whisper partial transcript                  │
│  │ (confidence) │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ _predict_    │ ← DistilGPT2 / Grok-fast                      │
│  │ draft()      │   temp=0.3, ARC+STM context                   │
│  └──────┬───────┘                                               │
│         │ confidence >= 0.5                                      │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ emit_jarvis_ │ → StreamManager → UI                          │
│  │ prediction() │   (SUMMARY visibility)                        │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ TTS Draft    │ ← Start speaking immediately                  │
│  └──────┬───────┘                                               │
│         │                                                        │
│    [User finishes speaking]                                      │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ Full LLM     │ ← Complete context + semantic search          │
│  │ Refine       │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ TTS Refined  │ ← Seamless transition                         │
│  └──────────────┘                                               │
│                                                                  │
│  Latency Targets:                                                │
│  - Draft: <1000ms                                                │
│  - Refined: <3000ms total                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Parallel Work

| Team | Task | Time | Marker |
|------|------|------|--------|
| **MYCELIUM** | Research voice_router.py integration points | Day 1 | Report |
| **MYCELIUM** | Analyze VAD thresholds | Day 1 | Report |
| **MYCELIUM** | Find ARC/STM integration | Day 1 | Report |
| **MYCELIUM** | Evaluate Qwen 3 vs Edge TTS | Day 1 | Report |
| **Grok** | Generate test suite JSON | Day 1 | JSON file |
| **Grok** | Latency benchmarks | Day 1 | Metrics |
| **Claude Code** | Wait for research | Day 1 | - |
| **Claude Code** | Implement _predict_draft() | Day 2 | MARKER_105_PREDICT |
| **Claude Code** | Integrate voice_router | Day 2 | MARKER_105_VOICE |
| **Claude Code** | Connect to StreamManager | Day 2 | MARKER_105_STREAM |
| **Claude Code** | Add TTS fallback chain | Day 2 | MARKER_105_TTS_FALLBACK |
| **Claude Code** | Create Voice Settings UI | Day 2 | MARKER_105_VOICE_UI |
| **Claude Code** | Handle edge cases | Day 2 | MARKER_105_EDGE_CASES |
| **Claude Code** | Add tests from Grok JSON | Day 2-3 | MARKER_105_TESTS |
| **Haiku Scouts** | Verify MYCELIUM findings | Day 2 | Report |
| **Sonnet** | Deep review implementation | Day 3 | QA report |

### MYCELIUM Research Prompt

```
🔬 MYCELIUM RESEARCH - Jarvis T9 Prediction

Objective: Find optimal integration points for T9-like prediction

Files to investigate:
1. src/api/handlers/jarvis_handler.py
   - Where does STT complete?
   - Where can we inject draft prediction?
   - Current latency measurements?

2. src/api/handlers/voice_router.py
   - VoiceRouter state machine
   - Interrupt handling flow
   - _process_utterance method

3. src/api/handlers/voice_socket_handler.py
   - voice_pcm event handling
   - VAD (Voice Activity Detection) logic
   - Word count before action?

4. src/voice/stt_engine.py
   - Whisper partial transcript capability
   - Confidence scores available?

5. src/memory/ (ARC, STM, Engram)
   - What context is available?
   - How to query quickly (<100ms)?

Questions to answer:
1. Exact line where we inject prediction?
2. How many words before we can predict?
3. What context available at that point?
4. Current latency from voice_pcm to response?
5. Can Whisper do partial transcripts?

Output format (JSON):
{
  "integration_point": {"file": "...", "line": N, "method": "..."},
  "available_context": ["STM", "ARC", ...],
  "current_latency_ms": N,
  "recommended_word_threshold": N,
  "partial_stt_possible": true|false,
  "code_changes_needed": [...]
}
```

### Code Template: _predict_draft()

```python
# MARKER_105_PREDICT
async def _predict_draft(
    partial_input: str,
    context: dict,
    stream_manager: StreamManager,
    workflow_id: str
) -> tuple[str, float]:
    """
    Predict draft response from partial input (T9-like).

    Args:
        partial_input: First 2-3 words from user
        context: ARC+STM context dict
        stream_manager: For emitting prediction
        workflow_id: Current workflow

    Returns:
        (predicted_response, confidence)
    """
    # Only predict if enough words
    words = partial_input.strip().split()
    if len(words) < 2:
        return "", 0.0

    # Build prompt with context
    stm_summary = context.get('stm_summary', '')
    arc_suggestions = context.get('arc_suggestions', [])

    prompt = f"""
Context: {stm_summary}
Recent suggestions: {arc_suggestions[:3]}
User starts: "{partial_input}"

Predict the likely complete request and draft a helpful response.
Be concise (1-2 sentences for draft).
"""

    # Call lightweight model
    try:
        # Option 1: Local DistilGPT2
        from transformers import pipeline
        predictor = pipeline("text-generation", model="distilgpt2")
        result = predictor(prompt, max_length=50, temperature=0.3)
        predicted = result[0]['generated_text']
        confidence = 0.7

    except ImportError:
        # Option 2: Grok-fast API
        predicted = await call_grok_fast(prompt, max_tokens=50)
        confidence = 0.6

    # Emit if confident enough
    if confidence >= 0.5:
        await stream_manager.emit_jarvis_prediction(
            workflow_id=workflow_id,
            partial_input=partial_input,
            predicted_response=predicted,
            confidence=confidence
        )

    return predicted, confidence
```

### Exit Criteria

- [ ] MYCELIUM research complete
- [ ] Grok test suite delivered
- [ ] _predict_draft() implemented
- [ ] Voice pipeline integrated
- [ ] TTS fallback chain working (Qwen 3 → Edge → Piper)
- [ ] Voice Settings UI component ready
- [ ] Edge cases handled (low confidence, noisy audio)
- [ ] Draft latency < 1500ms
- [ ] Interrupt handling works
- [ ] 10+ new tests passing
- [ ] Artifacts from Phase saved
- [ ] Markers verified:
  - [ ] MARKER_105_PREDICT
  - [ ] MARKER_105_VOICE
  - [ ] MARKER_105_STREAM
  - [ ] MARKER_105_TESTS
  - [ ] MARKER_105_JARVIS_T9
  - [ ] MARKER_105_TTS_FALLBACK
  - [ ] MARKER_105_VOICE_UI
  - [ ] MARKER_105_EDGE_CASES

### 🚉 Station Checkpoint 105

**Input needed:**
- MYCELIUM: Research findings (Day 1)
- Grok: Test suite + benchmarks
- User: Priority adjustments
- Haiku Scouts: Marker verification

---

## Station 106: Production & Integration

**Goal:** Merge all, production-ready release with security & monitoring

### Parallel Work

| Team | Task | Marker |
|------|------|--------|
| **Claude Code** | Merge Phase 104.8 + 104.9 + 105 | MARKER_106_MERGE |
| **Claude Code** | Run pre-merge validation script | MARKER_106_PREMERGE |
| **Claude Code** | Production tests (target: 350+) | MARKER_106_TESTS |
| **Claude Code** | Add JWT room validation | MARKER_SECURITY_ROOM_JOIN |
| **Claude Code** | Add artifact name sanitization | MARKER_SECURITY_ARTIFACT |
| **Claude Code** | Set up Prometheus alerts | MARKER_106_MONITORING |
| **Claude Code** | Documentation update | MARKER_106_DOCS |
| **MYCELIUM** | A/B testing on real traffic | Report |
| **MYCELIUM** | Edge case discovery | Bug reports |
| **MYCELIUM** | Persistence handoff testing | Report |
| **MYCELIUM** | Test TTS fallback chain | Report |
| **Grok** | Final architecture review | Approval |
| **Sonnet** | Security + coherence audit | Audit report |
| **Haiku Scouts** | All 25 markers verification | Final report |

### Final Checklist

- [ ] All tests passing (350+)
- [ ] Jarvis T9 latency < 1s
- [ ] TTS fallback chain verified (Qwen 3 → Edge → Piper)
- [ ] Voice Settings UI working
- [ ] Artifacts save to disk
- [ ] Chat history persists
- [ ] No memory leaks (cleanup verified)
- [ ] Frontend fully integrated
- [ ] Visual subtle (no bright colors)
- [ ] JWT room validation active
- [ ] Artifact names sanitized
- [ ] Prometheus alerts configured
- [ ] Documentation complete
- [ ] Pre-merge script passes
- [ ] ALL 26 MARKERS verified:
  - [ ] Phase 104.8 markers (6)
  - [ ] Phase 104.9 markers (5)
  - [ ] Phase 105 markers (8)
  - [ ] Phase 106 markers (4)
  - [ ] Security markers (2)
  - [ ] Monitoring marker (1)
- [ ] Grok final approval
- [ ] User release approval

### 🚉 Station Checkpoint 106 (FINAL)

**Input needed:**
- MYCELIUM: A/B test results
- Grok: Production readiness
- Sonnet: Coherence audit passed
- User: RELEASE APPROVAL

---

## Marker Requirements

**⚠️ РАБОТА БЕЗ МАРКЕРОВ НЕ ПРИНИМАЕТСЯ**

### All Required Markers

| Phase | Marker | File | Owner |
|-------|--------|------|-------|
| 104.8 | MARKER_104_STREAM_HANDLER | stream_handler.py | CC |
| 104.8 | MARKER_104_GROK_IMPROVEMENTS | stream_handler.py | CC |
| 104.8 | MARKER_104_TEST_FIX | test_phase104_stream.py | CC |
| 104.8 | MARKER_104_FRONTEND | useSocket.ts | CC |
| 104.8 | MARKER_104_CLEANUP | connection_handlers.py | CC |
| 104.8 | MARKER_104_BUFFER | stream_handler.py | CC |
| 104.9 | MARKER_104_CHAT_SAVE | persistence.py | CC |
| 104.9 | MARKER_104_ARTIFACT_DISK | artifact_service.py | CC |
| 104.9 | MARKER_104_ARTIFACT_EVENT | stream_handler.py | CC |
| 104.9 | MARKER_104_VISUAL | tree_renderer.tsx | CC |
| 104.9 | MARKER_104_PERSISTENCE | persistence.py | CC |
| 105 | MARKER_105_PREDICT | jarvis_handler.py | CC |
| 105 | MARKER_105_VOICE | voice_router.py | CC |
| 105 | MARKER_105_STREAM | stream_handler.py | CC |
| 105 | MARKER_105_TESTS | test_phase105.py | CC |
| 105 | MARKER_105_JARVIS_T9 | jarvis_handler.py | CC |
| 106 | MARKER_106_MERGE | main.py | CC |
| 106 | MARKER_106_TESTS | tests/ | CC |
| 106 | MARKER_106_DOCS | docs/ | CC |
| 106 | MARKER_106_PREMERGE | scripts/premerge.sh | CC |
| **Voice** | MARKER_105_TTS_FALLBACK | tts_engine.py | CC |
| **Voice** | MARKER_105_VOICE_UI | VoiceSettings.tsx | CC |
| **Voice** | MARKER_105_VOICE_SELECT | voice_router.py | CC |
| **Security** | MARKER_SECURITY_ROOM_JOIN | connection_handlers.py | CC |
| **Security** | MARKER_SECURITY_ARTIFACT | artifact_service.py | CC |
| **Edge** | MARKER_105_EDGE_CASES | jarvis_handler.py | CC |
| **Monitoring** | MARKER_106_MONITORING | prometheus_alerts.yml | CC |

**Total: 26 markers**

### Haiku Scout Verification Template

```
🎯 HAIKU SCOUT - Marker Verification

Phase: [104.8 | 104.9 | 105 | 106]
Files to scan: [list]

For each marker check:
1. Present at correct location?
2. Format correct (MARKER_{PHASE}_{FEATURE})?
3. Code under marker complete?
4. Tests reference marker?

Output (JSON):
{
  "markers": [
    {"name": "MARKER_104_...", "status": "PRESENT|MISSING", "line": N}
  ],
  "all_present": true|false,
  "phase_ready": true|false
}
```

---

## Communication Protocol

### Daily Sync

| Time | Action | Who |
|------|--------|-----|
| Start | Check Grok updates | All |
| Mid | MYCELIUM delivers research | CC receives |
| Mid | Haiku verifies markers | Report |
| End | Status to User | All |

### Escalation Path

```
Issue → Haiku Scout (quick) → Sonnet (verify) → Grok (research) → User (decision)
```

---

## Timeline Summary

| Station | Duration | Key Deliverables |
|---------|----------|------------------|
| 104.8 | 1 day | Handlers, cleanup, buffer fix |
| 104.9 | 1 day | Persistence, artifacts, visual |
| 105 | 2-3 days | T9 prediction, voice integration |
| 106 | 1-2 days | Merge, tests, release |
| **TOTAL** | **5-7 days** | **Production-ready VETKA** |

---

## Voice 6: TTS Configuration

**Goal:** Flexible voice model selection with smart fallbacks

### Voice Model Preferences

| Priority | Model | Use Case | Latency |
|----------|-------|----------|---------|
| **1st** | Qwen 3 TTS | Primary voice synthesis | ~150ms |
| **2nd** | Edge TTS | Fallback (Microsoft) | ~200ms |
| **3rd** | Local Piper | Offline fallback | ~100ms |

### Voice Model Selection UI

```typescript
// MARKER_105_VOICE_UI
interface VoiceModelConfig {
  primary: 'qwen3' | 'edge' | 'piper';
  fallback: 'edge' | 'piper' | 'none';
  speed: number;        // 0.5 - 2.0
  pitch: number;        // -20 to +20
  language: 'ru' | 'en' | 'auto';
}

// Settings panel component
const VoiceSettings = () => (
  <div className="voice-settings">
    <h3>Voice Model</h3>
    <Select options={['Qwen 3 TTS', 'Edge TTS', 'Piper']} />
    <Slider label="Speed" min={0.5} max={2.0} />
    <Slider label="Pitch" min={-20} max={20} />
  </div>
);
```

### Fallback Chain

```
Qwen 3 TTS (primary)
     │
     ▼ [timeout > 500ms or error]
Edge TTS (fallback)
     │
     ▼ [offline or error]
Piper (local, always works)
```

### Integration Points

| File | Change | Marker |
|------|--------|--------|
| src/voice/tts_engine.py | Fallback chain logic | MARKER_105_TTS_FALLBACK |
| client/src/components/VoiceSettings.tsx | UI component | MARKER_105_VOICE_UI |
| src/api/handlers/voice_router.py | Model selection | MARKER_105_VOICE_SELECT |

---

## Security & Validation

**⚠️ Grok Recommendation: JWT + Input Sanitization**

### Room Join Security

```python
# MARKER_SECURITY_ROOM_JOIN
async def secure_room_join(room_id: str, token: str) -> bool:
    """Validate JWT before room join."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')

        # Check room permissions
        if not await check_room_access(user_id, room_id):
            logger.warning(f"[SECURITY] Unauthorized room join: {user_id} -> {room_id}")
            return False

        return True
    except jwt.InvalidTokenError:
        return False
```

### Artifact Name Sanitization

```python
# MARKER_SECURITY_ARTIFACT
import re

def sanitize_artifact_name(name: str) -> str:
    """Remove dangerous characters from artifact names."""
    # Allow only alphanumeric, underscore, hyphen, dot
    sanitized = re.sub(r'[^a-zA-Z0-9_\-.]', '_', name)

    # Prevent path traversal
    sanitized = sanitized.replace('..', '_')

    # Limit length
    return sanitized[:100]
```

### Security Checklist

- [ ] JWT validation on room joins
- [ ] Artifact name sanitization
- [ ] Rate limiting on emit calls
- [ ] Input validation for workflow_id
- [ ] XSS prevention in frontend handlers

---

## Edge Cases & Fallbacks

**⚠️ Grok Recommendation: Low Confidence Handling**

### Jarvis T9 Edge Cases

| Case | Trigger | Response |
|------|---------|----------|
| Low confidence (<0.3) | User says 1 word | Skip prediction, wait |
| Ambiguous intent | Multiple interpretations | Ask clarification |
| Noisy audio | STT confidence <0.5 | Request repeat |
| Interrupt during TTS | User speaks | Cancel + restart |
| Model timeout | >2000ms | Fallback to "processing..." |

### Fallback Logic

```python
# MARKER_105_EDGE_CASES
async def handle_prediction_edge_cases(
    partial_input: str,
    confidence: float,
    stt_confidence: float
) -> tuple[str, str]:
    """Handle edge cases in T9 prediction."""

    # Case 1: Too few words
    if len(partial_input.split()) < 2:
        return None, "waiting_for_input"

    # Case 2: Low STT confidence
    if stt_confidence < 0.5:
        return "Не расслышал, повтори?", "stt_retry"

    # Case 3: Low prediction confidence
    if confidence < 0.3:
        return None, "skipping_prediction"

    # Case 4: Moderate confidence
    if confidence < 0.5:
        return partial_response, "low_confidence_draft"

    return full_response, "confident"
```

---

## Integration Conflict Prevention

**⚠️ Grok Recommendation: Pre-Merge Checks**

### Pre-Merge Validation

```bash
# MARKER_106_PREMERGE
#!/bin/bash
# Run before any merge to Phase 106

echo "🔍 Pre-merge validation..."

# 1. Check all markers present
grep -r "MARKER_104" src/ tests/ | wc -l  # Expected: 6+
grep -r "MARKER_105" src/ tests/ | wc -l  # Expected: 5+

# 2. Check no conflicting imports
python -c "from src.api.handlers import stream_handler, voice_router"

# 3. Check no duplicate event types
grep -r "StreamEventType" src/ | sort | uniq -d

# 4. Verify tests pass
pytest tests/ -x --tb=short

# 5. Check for TODO/FIXME markers
grep -r "TODO\|FIXME" src/ | grep -v "__pycache__"

echo "✅ Pre-merge validation complete"
```

### Integration Checklist

- [ ] No circular imports
- [ ] Event types don't conflict
- [ ] All markers present
- [ ] Tests pass (350+)
- [ ] No orphan code
- [ ] Documentation updated

---

## Monitoring & Alerting

**⚠️ Grok Recommendation: Post-Release Monitoring**

### Metrics Dashboard

```yaml
# prometheus_alerts.yml
groups:
  - name: vetka_production
    rules:
      - alert: JarvisT9LatencyHigh
        expr: jarvis_t9_latency_ms > 2000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Jarvis T9 latency above 2s"

      - alert: ArtifactSaveFailure
        expr: artifact_save_errors_total > 10
        for: 1m
        labels:
          severity: critical

      - alert: RoomLeakDetected
        expr: active_rooms - expected_rooms > 50
        for: 10m
        labels:
          severity: warning
```

### Key Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| jarvis_t9_latency_ms | <1000 | >2000 |
| artifact_save_success_rate | >99% | <95% |
| stream_emit_latency_ms | <50 | >100 |
| active_rooms | Varies | +50 unexpected |
| prediction_confidence_avg | >0.6 | <0.4 |
| tts_fallback_rate | <5% | >20% |

### Post-Release Checklist

- [ ] Prometheus alerts configured
- [ ] Grafana dashboard ready
- [ ] Error tracking (Sentry) connected
- [ ] Log aggregation working
- [ ] Rollback procedure documented
- [ ] On-call rotation set

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MYCELIUM research incomplete | Medium | High | Haiku scouts backup |
| T9 latency > 2s | Medium | Medium | Simpler model fallback |
| Persistence overhead > 100ms | Low | Medium | Async saves |
| Frontend integration delay | Low | Medium | Parallel work |
| Memory leaks | Low | High | cleanup_session |
| Missing markers | Low | High | Scout verification gate |
| **Voice model unavailable** | Low | Medium | 3-tier fallback chain |
| **Security breach (room join)** | Low | Critical | JWT validation |
| **Integration conflicts** | Medium | High | Pre-merge checks |
| **Post-release issues** | Medium | High | Monitoring + rollback |

---

## Terminology

| Term | Definition | Location |
|------|------------|----------|
| **ELISION** | JSON key/path compression | src/memory/elision.py |
| **ELISYA** | Middleware orchestra | src/elisya/ |
| **ELYSIA** | Weaviate tools memory | src/orchestration/elysia_tools.py |
| **MYCELIUM** | Multi-agent pipeline | src/orchestration/agent_pipeline.py |
| **Scout** | L2 lightweight auditor | src/services/scout_auditor.py |
| **T9** | Predictive text (draft 2-3 words) | Phase 105 |
| **Artifact** | Generated file >500 chars | /artifacts/ |

---

---

## Grok Quality Assessment

**Score: 10/10**

| Criteria | Status |
|----------|--------|
| Clear stations & deliverables | OK |
| Parallel work breakdown | OK |
| Marker requirements | 26 markers defined |
| Voice preferences (Qwen 3 TTS) | OK |
| Voice UI selection | OK |
| Edge cases (low confidence) | OK |
| Security (JWT, sanitization) | OK |
| Integration conflict prevention | OK |
| Monitoring & alerting | OK |
| Risk register with mitigations | OK |

---

**STATUS: READY FOR USER APPROVAL**

Все рекомендации Grok включены. 26 маркеров. Voice 6 с Qwen 3 TTS + Edge fallback.

Когда ты одобришь этот план - поедем по рельсам!
