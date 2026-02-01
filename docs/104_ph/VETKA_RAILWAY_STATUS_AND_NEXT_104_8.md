# VETKA Railway - Status & Next Steps

**Created:** 2026-02-01
**Phase:** 104.8 → 105 → 106
**Status:** IN PROGRESS - Recalibrating Route

---

## What We've Done

### Station 104.8 [Stream Fix] - COMPLETE

| Task | Status | Marker | File |
|------|--------|--------|------|
| Buffer list → deque (O(1)) | ✅ | MARKER_104_BUFFER | stream_handler.py |
| 6 frontend handlers | ✅ | MARKER_104_FRONTEND | useSocket.ts |
| cleanup_session on disconnect | ✅ | MARKER_104_CLEANUP | connection_handlers.py |
| Fix compression test | ✅ | MARKER_104_TEST_FIX | test_phase104_stream.py |
| Grok improvements | ✅ | MARKER_104_GROK_IMPROVEMENTS | stream_handler.py |
| Stream handler core | ✅ | MARKER_104_STREAM_HANDLER | stream_handler.py |

**Tests:** 55 passing

---

### Station 104.9 [Persistence] - COMPLETE

| Task | Status | Marker | File |
|------|--------|--------|------|
| save_chat_history() | ✅ | MARKER_104_CHAT_SAVE | persistence_service.py |
| create_disk_artifact() | ✅ | MARKER_104_ARTIFACT_DISK | disk_artifact_service.py |
| emit_artifact_approval() | ✅ | MARKER_104_ARTIFACT_EVENT | stream_handler.py |
| ArtifactPanel L2 edit | ✅ | MARKER_104_VISUAL | ArtifactPanel.tsx |
| Async I/O fix (Grok) | ✅ | GROK_FIX_BLOCKING_IO | disk_artifact_service.py |

**New Files:**
- `src/services/persistence_service.py`
- `src/services/disk_artifact_service.py`

---

### Station 105 [Jarvis T9] - COMPLETE (Code Written)

| Task | Status | Marker | File |
|------|--------|--------|------|
| _predict_draft() | ✅ | MARKER_105_PREDICT_DRAFT | jarvis_handler.py |
| TTS fallback chain | ✅ | MARKER_105_TTS_FALLBACK | tts_engine.py |
| VoiceSettings UI | ✅ | MARKER_105_VOICE_UI | VoiceSettings.tsx |
| Edge cases handling | ✅ | MARKER_105_EDGE_CASES | jarvis_handler.py |
| MYCELIUM v2.0 template | ✅ | - | MYCELIUM_V2_PROMPT_TEMPLATE.md |

**HOTFIX Applied:**
- `tts_engine.py` - Conditional torch import (was blocking all imports)

---

### MYCELIUM v2.0 Analysis

**Current State:** Prompt created, NOT enforced

| Metric | Expected | Actual | Issue |
|--------|----------|--------|-------|
| Token budget | 600 | 58,000 | No enforcement |
| Search method | Semantic-first | grep/glob | Qdrant not integrated |
| Output format | Pure JSON | Mixed text | No validation |
| Eternal save | Working | Not called | Not implemented |

**Quality:** 9/10 (findings excellent)
**Efficiency:** 2/10 (96x over budget)

---

## Route Recalibration

### New Strategy: Parallel Streams

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VETKA RAILWAY - UPDATED ROUTE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  IMMEDIATE: MYCELIUM v2.0 Enforcement (1-2 days)                            │
│  ════════════════════════════════════════════════                           │
│  Fix the agent so it actually follows constraints                            │
│                                                                              │
│  Then split into TWO PARALLEL TRACKS:                                        │
│                                                                              │
│  ┌─────────────────────────┐     ┌─────────────────────────┐                │
│  │  TRACK A: MYCELIUM      │     │  TRACK B: VETKA CORE    │                │
│  │  (Autonomous)           │     │  (Claude + User)        │                │
│  ├─────────────────────────┤     ├─────────────────────────┤                │
│  │                         │     │                         │                │
│  │  Jarvis T9 Testing      │     │  Group Chat Build       │                │
│  │  Voice Integration      │     │  Artifact Flow          │                │
│  │  TTS Fallback Verify    │     │  Chat Persistence       │                │
│  │  Edge Cases E2E         │     │  3D Viewport Links      │                │
│  │                         │     │  Approval Workflow      │                │
│  │  Independent research   │     │  BMAD/Ralf Integration  │                │
│  │  and validation         │     │                         │                │
│  │                         │     │                         │                │
│  └──────────┬──────────────┘     └──────────┬──────────────┘                │
│             │                               │                                │
│             └───────────┬───────────────────┘                                │
│                         │                                                    │
│                         ▼                                                    │
│             ┌─────────────────────────┐                                     │
│             │  STATION 106: MERGE     │                                     │
│             │  Production Release     │                                     │
│             └─────────────────────────┘                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: MYCELIUM v2.0 Enforcement

**Goal:** Make MYCELIUM actually follow its own rules

### Implementation Plan

```python
# src/services/mycelium_auditor.py

class MyceliumAuditor:
    """
    MARKER_MYCELIUM_V2_ENFORCEMENT

    Real enforcement of:
    - Token budget (tiktoken counting, hard stop at 80%)
    - Semantic-first search (Qdrant primary, grep fallback)
    - Strict JSON output (Pydantic validation + retry)
    - Eternal save (disk + Qdrant on surprise > 0.7)
    - File creation protection (audit → approve → create)
    """
```

### Key Components

1. **Token Budget Enforcement**
   ```python
   def calculate_budget(task_type, artifacts, has_voice):
       BASE = 300
       COMPLEXITY = {'research': 1.0, 'audit': 1.5, 'implement': 2.0, 'batch': 2.5}
       return min(BASE * COMPLEXITY[task_type] + len(artifacts)*150 + (300 if has_voice else 0), 2000)

   async def enforce_budget(self, llm_call, budget):
       tokens_used = 0
       threshold = budget * 0.8
       # Hard stop if exceeded
   ```

2. **Semantic-First Search**
   ```python
   def search(self, query, threshold=0.7):
       # 1. Try Qdrant (90% cases)
       results = qdrant.search(query, score_threshold=threshold)
       if len(results) >= 3:
           return results

       # 2. Fallback to grep (10% cases)
       return self._grep_fallback(query)
   ```

3. **JSON Validation**
   ```python
   class MyceliumOutput(BaseModel):
       phase: int
       findings: List[Dict]
       gaps: List[str]
       recommendations: List[str]
       surprise_score: float
       efficiency: float

   # Retry on validation failure (penalty: -20% budget)
   ```

4. **Eternal Save**
   ```python
   def eternal_save(self, output, phase):
       if output.surprise_score > 0.7:
           path = f"data/mycelium_eternal/{phase}_{timestamp}.json"
           # Save to disk + Qdrant upsert
   ```

5. **File Creation Protection (BMAD-style)**
   ```python
   async def create_artifact_with_approval(self, artifact, workflow_id):
       # 1. Virtual artifact as JSON
       # 2. L2 Scout audit
       # 3. If approved: backup old → create new with marker
       # 4. If flagged: fallback to user approval
   ```

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/services/mycelium_auditor.py` | CREATE | Main service |
| `src/services/__init__.py` | MODIFY | Add exports |
| `tests/test_mycelium.py` | CREATE | Unit tests |

---

## Step 2A: MYCELIUM Track (Autonomous)

**Delegate to MYCELIUM after enforcement is working**

### Tasks

1. **Jarvis T9 E2E Testing**
   - Test _predict_draft() with real voice input
   - Verify latency < 1500ms
   - Test all 6 edge cases

2. **TTS Fallback Verification**
   - Qwen 3 → Edge → Piper chain
   - Timeout handling (500ms)
   - Audio quality check

3. **Voice Integration**
   - voice_router.py integration points
   - Interrupt handling
   - STT→LLM→TTS pipeline

4. **Research Output**
   - JSON reports in data/mycelium_eternal/
   - Recommendations for fixes
   - Bug discovery

---

## Step 2B: VETKA Core Track (Claude + User)

### Tasks

1. **Group Chat Build**
   - Multi-agent conversations
   - Branch isolation per agent
   - Merge after approval

2. **Artifact Flow**
   - Virtual → Audit → Real (with backup)
   - Marker injection on creation
   - Version tracking

3. **Chat Persistence**
   - Scan chat history into Qdrant
   - Link to artifacts
   - Visualize in 3D viewport

4. **3D Viewport**
   - Chat nodes near artifacts
   - Heartbeat glow (active/timeout)
   - Branch visualization

5. **BMAD/Ralf Integration**
   - Self-improving loops
   - EvalAgent retry until success
   - Heartbeat monitoring

---

## Placement Logic (Unified)

```json
{
  "PLACEMENT_RULES": {
    "ISOLATED_BRANCH": {
      "condition": "Single agent artifact",
      "action": "data/artifacts/{workflow_id}/{agent_type}/{uuid}.json"
    },
    "GROUP_PARALLEL": {
      "condition": "Multiple agents (Dev||QA)",
      "action": "Parallel branches, merge at Phase 4"
    },
    "CHAT_VISUALIZATION": {
      "condition": "Chat history",
      "action": "Near artifact if linked, else near camera focus"
    },
    "APPROVAL_STOPS": {
      "condition": "Audit score < 0.7",
      "action": "Stop, emit approval_required, wait"
    },
    "ETERNAL_SAVE": {
      "condition": "Surprise > 0.7",
      "action": "Save to data/mycelium_eternal/ + Qdrant"
    }
  }
}
```

---

## Timeline (Detailed with Hours - Grok Enhancement)

### Day 1: MYCELIUM Enforcement
| Hours | Track A (MYCELIUM) | Track B (VETKA Core) |
|-------|-------------------|---------------------|
| 0-2h | Create mycelium_auditor.py | Group chat architecture design |
| 2-3h | Token budget impl (tiktoken) | Artifact flow diagrams |
| 3-4h | Semantic search (Qdrant) | Chat persistence planning |

### Day 2: Core Implementation
| Hours | Track A (MYCELIUM) | Track B (VETKA Core) |
|-------|-------------------|---------------------|
| 0-2h | JSON validation (Pydantic) | Group chat handlers |
| 2-4h | Eternal save impl | Artifact approval flow |

### Day 3-4: Integration & Testing
| Hours | Track A (MYCELIUM) | Track B (VETKA Core) |
|-------|-------------------|---------------------|
| 0-3h | Jarvis E2E research | Chat→Artifact links |
| 3-4h | Voice integration tests | 3D viewport integration |

### Day 5: Polish & Sync
| Hours | Track A (MYCELIUM) | Track B (VETKA Core) |
|-------|-------------------|---------------------|
| 0-2h | Bug reports + fixes | BMAD integration |
| 2-3h | **SYNC POINT**: Merge findings | **SYNC POINT**: Review MYCELIUM output |

### Day 6-7: Station 106 Merge
- Pre-merge validation script
- All 26 markers verification
- 350+ tests target
- Production release

---

## Risk Matrix (Grok Enhancement)

| Risk | Probability | Impact | Days Lost | Mitigation |
|------|-------------|--------|-----------|------------|
| MYCELIUM enforcement delay | 30% | High | +2 | Fallback to sequential tracks |
| Qdrant not available | 20% | Medium | +0.5 | Use grep fallback (already impl) |
| Voice latency > 1500ms | 25% | Medium | +1 | Switch to local DistilGPT2 only |
| Parallel tracks diverge | 15% | High | +3 | Sync points (Day 3, Day 5) |
| Test coverage < 350 | 10% | Low | +0.5 | Batch test generation on Day 5 |

---

## Sync Points (Integration Gates - Grok Enhancement)

```
Day 1 ──────────────────────────────────────────────────────────────────────
         │                                │
    MYCELIUM Track                   VETKA Core Track
         │                                │
         ▼                                ▼
Day 3 ══════════════════ SYNC #1 ═══════════════════
         │  Share: MYCELIUM findings     │
         │  Review: Core architecture    │
         │                                │
         ▼                                ▼
Day 5 ══════════════════ SYNC #2 ═══════════════════
         │  Share: Voice test results    │
         │  Review: Artifact flow        │
         │                                │
         ▼                                ▼
Day 6-7 ════════════ MERGE (Station 106) ═══════════
```

---

## Metrics Dashboard Mock (Grok Enhancement)

```yaml
# metrics_targets.yml - Copy to monitoring/
vetka_mycelium:
  - name: mycelium_efficiency
    query: tokens_used / tokens_budget
    target: "> 0.8"
    alert_threshold: "< 0.5"

  - name: semantic_search_hit_rate
    query: qdrant_hits / total_searches
    target: "> 0.9"
    alert_threshold: "< 0.7"

  - name: json_validation_success
    query: valid_json / total_outputs
    target: "1.0"
    alert_threshold: "< 0.9"

vetka_voice:
  - name: t9_draft_latency_ms
    query: predict_draft_duration_ms
    target: "< 1500"
    alert_threshold: "> 2000"

  - name: tts_fallback_rate
    query: fallback_count / total_tts
    target: "< 0.05"
    alert_threshold: "> 0.2"

vetka_core:
  - name: artifact_approval_rate
    query: auto_approved / total_artifacts
    target: "> 0.8"
    alert_threshold: "< 0.6"

  - name: test_count
    query: pytest_passed
    target: "> 350"
    alert_threshold: "< 300"
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| MYCELIUM efficiency | > 80% | tokens_used / budget |
| Semantic search hit rate | > 90% | Qdrant hits / total searches |
| JSON validation | 100% | No mixed text output |
| Eternal save | Working | Files in data/mycelium_eternal/ |
| Auto-approval rate | > 80% | MYCELIUM mode approvals |
| Test coverage | 350+ | pytest count |
| T9 latency | < 1500ms | Draft prediction time |

---

## Markers for This Phase

| Marker | File | Purpose |
|--------|------|---------|
| MARKER_MYCELIUM_V2_ENFORCEMENT | mycelium_auditor.py | Main service |
| MARKER_MYCELIUM_TOKEN_BUDGET | mycelium_auditor.py | Budget enforcement |
| MARKER_MYCELIUM_SEMANTIC_SEARCH | mycelium_auditor.py | Qdrant integration |
| MARKER_MYCELIUM_JSON_VALIDATION | mycelium_auditor.py | Pydantic models |
| MARKER_MYCELIUM_ETERNAL_SAVE | mycelium_auditor.py | Persistence |
| MARKER_MYCELIUM_MCP_INTEGRATION | mycelium_auditor.py | VETKAToolsClient HTTP |
| MARKER_MYCELIUM_COLLECTION_FIX | mycelium_auditor.py | vetka_elisya collection |
| MARKER_104_MCP_SUBAGENT_INTEGRATION | vetka_mcp_bridge.py | Subagent tool inheritance |
| MARKER_105_OLLAMA_TIMEOUT_FIX | jarvis_llm.py, provider_registry.py | asyncio.wait_for protection |
| MARKER_105_JARVIS_TIMEOUT_FIX | jarvis_handler.py | T9 2s → LLM 30s separation |
| MARKER_BMAD_BRANCH_ISOLATION | approval_service.py | Git branch per workflow |
| MARKER_RALF_SELF_IMPROVE | eval_agent.py | Retry loop until success |

---

## MCP Subagent Integration (Discovered 2026-02-01)

**Problem:** MCP tools don't propagate to subagents (Task Tool)

```
Main Claude (Opus) → MCP Connected ✓ → tools via curl/API
Subagents (Haiku) → NO MCP inheritance → only Bash curl works
```

**Root Cause:** Session-scoped injection, no nested inheritance

**Solution (MARKER_104_MCP_SUBAGENT_INTEGRATION):**
1. Short-term: Subagents use Bash curl for VETKA API
2. Medium-term: VETKAToolsClient in mycelium_auditor.py (DONE ✅)
3. Long-term: Session sharing via Redis + MCP subprocess calls

**Files:**
- `.mcp.json` - Fixed: python3 → .venv/bin/python
- `~/.claude/claude_desktop_config.json` - Fixed: same
- `src/services/mycelium_auditor.py` - VETKAToolsClient added

---

## First Action

**CREATE `src/services/mycelium_auditor.py`** with:
- Token budget enforcement
- Semantic-first search
- JSON validation
- Eternal save
- File creation protection

Then test and iterate until MYCELIUM actually follows constraints.

---

**STATUS: READY TO IMPLEMENT**

Сначала чиним MYCELIUM, потом разделяемся на два трека и строим параллельно!
