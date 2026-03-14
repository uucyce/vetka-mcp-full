# VETKA — STRATEGIC ARCHITECTURE PLAN 2026
## Phase 136 → Phase 145 | Commander: Opus | Date: 2026-02-11

---

## I. EXECUTIVE SUMMARY

VETKA — 3D knowledge graph platform с AI-агентами.
Stack: Tauri (Rust) + React (TypeScript) + Python FastAPI + Three.js.
Dual MCP: VETKA (port 5001, fast) + MYCELIUM (port 8082, async pipelines).
Three-agent army: Opus (architect), Cursor (frontend), Codex (backend).

**Стратегическая цель:** от IDE с 3D-визуализацией к autonomous knowledge platform,
где агенты и люди совместно строят деревья знаний.

---

## II. CURRENT STATE — Phase 136 Scorecard

| Layer | Status | Maturity | Notes |
|-------|--------|----------|-------|
| 3D Visualization (Three.js tree) | ✅ Done | 80% | Tree rendering, camera, directed mode |
| Backend API (FastAPI + SocketIO) | ✅ Done | 80% | 20+ route groups, SocketIO rooms |
| Mycelium Pipeline (Dragon teams) | ✅ Done | 75% | Bronze/Silver/Gold auto-tier, fractal subtasks |
| MCP Dual Architecture | ✅ Done | 85% | VETKA + MYCELIUM split, no blocking |
| TaskBoard Multi-Agent | ✅ Done | 70% | Claim/complete/auto-close on commit |
| MCC DevPanel | ✅ Done | 65% | DAG, Board, Stats, Architect Chat, Artifacts, Cmd+K |
| Unified Search | ⚠️ Partial | 45% | Backend router done (Codex), Cmd+K frontend done (Cursor), web/social stubs |
| Folder Modes | ✅ Done | 60% | Auto-detect React/Vue/Python/etc, badge UI |
| Chat-File Links | ✅ Done | 55% | Link API + clickable badges |
| Save/Undo | ✅ Done | 50% | Ctrl+S/Ctrl+Z for artifacts |
| Heartbeat Daemon | ⚠️ Partial | 55% | Timer fixed, junk guard, but polling not event-driven |
| Knowledge Graph | 🔴 Gap | 10% | Architecture in docs, code not started |
| Playground (R&D Sandbox) | 🔴 Gap | 5% | Architecture in docs (Phase 134), code not started |
| Messenger Integration | 🔴 Gap | 0% | Telegram/Matrix relay described in docs |
| Social/Federation | 🔴 Gap | 0% | ActivityPub/shared trees described in docs |
| Jarvis Superagent | 🔴 Gap | 0% | Chat agent with Engram memory — planned |

---

## III. COMPLETED IN THIS SESSION (Phase 136)

### Opus (Commander)
- Multi-Agent Sync Protocol designed and documented
- TaskBoard cleaned (15 junk tasks removed)
- Heartbeat daemon bugs fixed (undefined var, unresponsive toggle)
- Junk task guard (min 15 chars)
- CLAUDE.md updated for all agents
- Strategic recon: 8 doc directories analyzed

### Codex (Backend)
- Auto-close tasks on git commit (MARKER_136.AUTO_CLOSE_COMMIT)
- Unified Search backend: POST /api/search/unified (MARKER_136.UNIFIED_SEARCH_BACKEND)
- Artifact approve/reject API: GET/POST endpoints (MARKER_136.ARTIFACT_API)
- Artifact scanner extended: data/artifacts + src/vetka_out
- Chat compression 500 chars
- File connections API
- CLI removal (-691 lines)
- 16+ tests passing

### Cursor (Frontend)
- Wave 1: ACTIVITY tab removed, heartbeat countdown, enhanced stats
- Wave 2: ArtifactViewer, ArchitectChat, CommandPalette Cmd+K, heartbeat fix
- Wave 3: Folder modes auto-detect, Chat-file links, Save/Undo Ctrl+S/Z

---

## IV. STRATEGIC ROADMAP — 5 Sprints

### SPRINT 1 — "Combat Ready" (Phase 137, ~1 week)
**Goal:** Stabilize, eliminate remaining bugs, event-driven autonomy.

| # | Task | Owner | Priority | Complexity | Deadline | Acceptance Test |
|---|------|-------|----------|------------|----------|-----------------|
| S1.1 | Heartbeat: event-driven dispatch (SocketIO emit on new task) | Opus | P1 | High | 2026-02-14 | New task in board triggers dispatch without polling delay; verified by integration test + MCC live update |
| S1.2 | Unified Search: wire web provider (Tavily via vetka_web_search) | Codex | P1 | Medium | 2026-02-13 | `/api/search/unified` returns web source results with normalized score and URL dedup |
| S1.3 | Unified Search: wire Cmd+K frontend → unified backend | Cursor | P1 | Medium | 2026-02-13 | Cmd+K query calls `/api/search/unified`; UI groups results by source and opens selected item |
| S1.4 | MCC Stats: connect to real pipeline_history data | Cursor | P2 | Medium | 2026-02-15 | Stats panel values match `/api/debug/pipeline-history` on refresh and live updates |
| S1.5 | Artifact panel: connect Cursor ArtifactViewer → Codex API endpoints | Cursor | P2 | Low | 2026-02-15 | Approve/reject in UI updates `/api/artifacts` state and re-renders status badges |
| S1.6 | Tests: heartbeat daemon + unified search E2E | Codex | P2 | Medium | 2026-02-13 | `tests/test_heartbeat_daemon.py` + `tests/test_unified_search_e2e.py` + auto-close commit tests all green |
| S1.7 | TaskBoard: cleanup old P4-P5 stale tasks | Opus | P3 | Low | 2026-02-16 | Stale backlog triaged (close/archive/relabel) with changelog entry and board diff |

### SPRINT 2 — "Jarvis Awakens" (Phase 138, ~1-2 weeks)
**Goal:** Intelligent chat agent that knows user, searches everything.

| # | Task | Owner | Priority | Complexity | Deadline | Acceptance Test |
|---|------|-------|----------|------------|----------|-----------------|
| S2.0 | MCC Deep Fix: heartbeat dual panel, artifacts panel, overall QA | Cursor | P1 | Medium | 2026-02-22 | MCC smoke suite passes and no critical UI regressions in 24h |
| S2.1 | UI Layout: center search bar, icons horizontal right, remove top-right labels | Cursor | P1 | Medium | 2026-02-22 | Visual regression snapshots pass desktop/mobile and layout matches spec |
| S2.2 | Jarvis MCP: dedicated MCP server (non-blocking, Engram memory, workflow router) | Codex | P1 | High | 2026-02-24 | New MCP Jarvis server runs independently; pipeline load does not degrade Jarvis latency (>95p target met) |
| S2.3 | Jarvis Voice Pipeline: streaming TTS with pre-generation + filler phrases | Dragon Gold | P1 | High | 2026-02-26 | Voice roundtrip median <2.5s first audio; full response appended without overlap artifacts |
| S2.4 | Jarvis in Unified Search: voice mode integration (mic before text input) | Cursor | P1 | High | 2026-02-26 | Mic-first mode works in Unified Search; voice input routes to Jarvis and returns voice output |
| S2.5 | Model Directory: auto-detect local + API voice models (Polza, Qwen TTS) | Codex | P1 | Medium | 2026-02-21 | Model Directory lists local+remote providers with refresh and capability badges (text/voice/image/embed) |
| S2.6 | Agent Voice IDs: persistent voice assignment per agent + voice messages in chat | Dragon Silver | P2 | Medium | 2026-02-27 | Agent voice config persisted; chat voice messages replay correctly after restart |
| S2.7 | Model fallback chain with key roaming | Codex | P2 | High | 2026-02-27 | Simulated provider outages recover automatically via fallback order without user-visible failure |
| S2.8 | Jarvis Realtime Start (Jarvis button only): sentence/chunk TTS kickoff from early context (viewport + pin + first words) | Codex | P1 | High | 2026-02-28 | Applies only to dedicated Jarvis live dialog; group/solo chat keep full voice-message responses |

### Sprint Definition of Done (S1-S2)
- Task is linked to TaskBoard ID and has recon + implementation report in `docs/*_ph/`.
- Code merged with marker(s), and targeted tests added or updated.
- `vetka_git_commit` used for commit message containing `tb_...` for auto-close traceability.
- Acceptance test from sprint table is executed and result captured in report.
- No unresolved P1/P2 regressions in touched area.

### SPRINT 3 — "Living Knowledge" (Phase 139, ~2 weeks)
**Goal:** Knowledge Graph construction — VETKA becomes intelligent.

| # | Task | Agent | Priority | Complexity |
|---|------|-------|----------|------------|
| S3.1 | build_tag_hierarchy(): cluster embeddings → hierarchy | Dragon Gold | P1 | High |
| S3.2 | Adaptive spread in Three.js (similarity → cluster tightness) | Cursor | P1 | High |
| S3.3 | Batch edge discovery (Qdrant recommend → graph edges) | Codex | P1 | Medium |
| S3.4 | Progressive loading UI (streaming 100K+ nodes) | Cursor | P2 | High |
| S3.5 | UMAP real-time projections | Dragon Gold | P2 | High |
| S3.6 | Knowledge level tags from Phase 72 formulas | Codex | P2 | Medium |

### SPRINT 4 — "The Playground" (Phase 140, ~1-2 weeks)
**Goal:** Experimental sandbox where Dragons/Titans experiment freely.

| # | Task | Agent | Priority | Complexity |
|---|------|-------|----------|------------|
| S4.1 | /mycelium_playground/ isolation backend (rsync mirror + scoped MCP) | Codex | P1 | High |
| S4.2 | Sandbox MCP tools (read/write/test within playground only) | Codex | P1 | High |
| S4.3 | Approval workflow UI (diff review → approve/reject → merge) | Cursor | P1 | High |
| S4.4 | Token budget tracker (2M tokens/day limit per agent) | Codex | P2 | Medium |
| S4.5 | Auto-merge gate (verifier confidence >0.95 → auto-approve) | Opus | P2 | Medium |
| S4.6 | MCC Playground tab: live experiments view | Cursor | P2 | Medium |

### SPRINT 5 — "Social VETKA" (Phase 141-145, ~3-4 weeks)
**Goal:** VETKA as platform — humans + agents in shared knowledge space.

| # | Task | Agent | Priority | Complexity |
|---|------|-------|----------|------------|
| S5.1 | Telegram bot relay (webhook → pipeline) | Codex | P2 | Medium |
| S5.2 | SocketIO rooms for user groups | Codex | P2 | Medium |
| S5.3 | Shared trees: fork/merge/subscribe | Cursor + Dragon | P2 | High |
| S5.4 | NeoBloom: agent-generated visualization artifacts | Dragon Gold | P2 | High |
| S5.5 | ActivityPub federation (basic) | Future | P3 | Very High |
| S5.6 | E2E encryption (libsignal/MLS) | Future | P3 | Very High |

---

## V. PLAYGROUND ARCHITECTURE (Detail)

```
PRODUCTION                         PLAYGROUND
vetka_live_03/                     mycelium_playground/
  src/ ─── rsync mirror ──────→     src/ (read-write)
  data/ ── snapshot copy ──────→     data/ (isolated)
  tests/ ─ copy ───────────────→     tests/ (sandboxed)

Dragon/Titan agents:
  ✅ Read any file
  ✅ Write new/modified files
  ✅ Run tests (pytest in sandbox)
  ✅ Call MCP tools (scoped to playground/)
  ❌ Cannot commit to production
  ❌ Cannot modify main.py / MCP configs
  ❌ Cannot access user secrets / .env

Workflow:
  1. Agent receives task → runs in playground/
  2. Generates artifact with confidence score
  3. Verifier checks (gate: >0.95 auto-approve, <0.95 human review)
  4. Artifact appears in MCC Playground tab
  5. Human clicks "Approve" → rsync diff → production merge
  6. Or clicks "Reject" → feedback sent to agent for retry

Token Budget:
  - 2M tokens/day per agent
  - 3 parallel pipeline limit
  - Cost dashboard in MCC BALANCE tab
```

---

## V-B. JARVIS VOICE ARCHITECTURE (Detail)

### Core Concept
Jarvis = Superagent, NOT a chat panel feature. Lives in Unified Search bar (centered).
Hybrid architecture: Engram user memory + multi-model team + workflow templates.

### MCP Architecture
```
MCP VETKA (5001)     — fast stateless (search, files, camera)
MCP MYCELIUM (8082)  — async pipelines (Dragon teams)
MCP JARVIS (NEW)     — dedicated non-blocking voice+agent (won't lag during pipeline)
  ├── Engram memory (user preferences, history)
  ├── Workflow router (per-request workflow selection)
  ├── Voice pipeline (STT → LLM → TTS streaming)
  └── Tool access (full VETKA control: search, camera, files, pipeline)
```

### Voice Pipeline — Low-Latency Strategy (Jarvis Button Mode)
```
Current baseline: full-message generation usually ~2-4s on local M4 (4bit), but we still need faster first-audio.

Solution (Jarvis button mode): 2-stage streaming-first pipeline.
Group/solo chat mode: emit full voice messages (no early kickoff).

Stage 1 — Early sentence kickoff (while user speaks, ~0.3-1.2s):
  Based on: viewport context + first words of user input
  Generate first short sentence BEFORE user finishes.
  Stream first audio chunk immediately.

Stage 2 — Full response continuation (after user done, ~2-4s):
  Complete LLM response, split by sentences, stream sequentially.
  Preserve one voice_id per agent/role during the full turn.

Timeline:
  User speaks ──────────────────┐
  Stage 1 early chunk (parallel)│──▶ [starts before full text is ready]
  User stops ───────────────────┘
  Stage 2 full stream ──────────────▶ [continues without voice switch]
```

### Voice Activation (No Extra Button)
```
Search bar states:
  1. Empty + no keyboard focus → microphone icon visible (voice mode ready)
  2. User starts typing → microphone hides, text search active
  3. User clicks mic / says trigger word → recording wave appears
  4. Voice message sent → agents respond via TTS automatically
  5. Text message sent → agents respond via text (normal mode)

Trigger: voice input = voice output. Text input = text output.
```

### Agent Voice Identity
```
Each agent gets permanent voice_id:
  - Jarvis (superagent): deep calm male voice
  - Dragon Bronze: fast energetic voice
  - Dragon Silver: measured professional voice
  - Dragon Gold: authoritative slow voice

Stored in: data/agent_voice_config.json
  {
    "jarvis": {"voice_id": "dylan", "provider": "qwen_tts", "speed": 1.0},
    "dragon_bronze": {"voice_id": "eric", "provider": "qwen_tts", "speed": 1.15},
    "dragon_silver": {"voice_id": "ryan", "provider": "qwen_tts", "speed": 1.0},
    "dragon_gold": {"voice_id": "uncle_fu", "provider": "qwen_tts", "speed": 0.95},
    ...
  }

Voice messages in chat:
  - Appear as waveform bars (like Telegram/WhatsApp voice messages)
  - Agent avatar + wave + duration
  - Click to play, auto-play in voice conversation mode
  - Emotional tone auto-detected from LLM response sentiment
```

### Model Directory Fix
```
Problem: "No models found" — hardcoded model list, no auto-detection.

Fix:
  1. Scan Polza API for available models (including voice: tts, stt)
  2. Scan local Ollama for installed models
  3. Scan Qwen TTS local server if running
  4. Auto-categorize: text/voice/image/embedding
  5. Show ALL in Model Directory with provider badges
```

### UI Layout Redesign
```
Current (broken):
  ┌─ Search ─┐ [icons]     [small labels top-right]
  │ top-left │ vertical
  └──────────┘ cramped

Target:
  ┌──────────────────────────────────────────────┐
  │            [Search Bar — CENTERED]            │
  │            width: 50%, min: 400px             │
  │            + mic icon when empty              │
  └──────────────────────────────────────────────┘
                        [Chat] [Artifact] [MCC] ← horizontal, top-right
                        (no small labels)

  Chat panel: slides from RIGHT (doesn't overlap icons)
  MCC panel: slides from RIGHT below chat (or bottom)
```

---

## VI. KEY ARCHITECTURAL DECISIONS (Updated with Grok Research 2026-02-11)

### Decision 1: Search Stack ✅ RESEARCHED
**Current:** Qdrant (vector) + Weaviate (BM25) + RRF fusion
**Grok Finding:** Keep Weaviate (GraphQL federation fit) + ADD Meilisearch as BM25 fallback.
Meilisearch: 5K QPS vs Weaviate 2K, 3x lighter memory (2-4GB vs 8-12GB for 1M docs).
**Decision:** Dual BM25 — Weaviate for hybrid+graph, Meilisearch for fast keyword fallback.
**Effort:** 1 day (Meilisearch Docker + SDK drop-in). Phase 140.1.

### Decision 2: Knowledge Graph Backend ✅ RESEARCHED
**Current:** Qdrant stores vectors, no explicit graph.
**Grok Finding:** Custom Poincaré (GeoOpt/PyTorch) >> Gensim. GPU train 10K nodes in 2min.
Hierarchy recall +25% vs cosine. Encode tree depth as hyperbolic radius (root=0, leaves=0.9).
**Decision:** Custom PoincaréBall encoder → Qdrant (cosine approx OK). Fits Sugiyama Y-axis.
**Effort:** 2 days. Phase 141.

### Decision 3: Playground Isolation ✅ RESEARCHED
**Grok Finding:** Docker+seccomp >> chroot (escape vulns) >> rsync (no exec isolation).
Docker: 100ms startup, namespaces+seccomp, network_disabled, 256MB mem limit.
**Decision:** Docker container per agent run (python:3.12-slim + seccomp:default).
Rsync for code mirror PRE-exec, Docker for sandboxed execution.
**Effort:** 1 day (docker-py). Phase 142.

### Decision 4: Autonomous Dispatch ✅ RESEARCHED
**Grok Finding:** SocketIO (50ms latency, 1K rooms) good for UI. Redis Streams (10ms, 10K+ scale) for backend.
Pattern: task_board.add() → emit 'task_claimed' → agent picks up → emit 'task_done'.
**Decision:** SocketIO + Redis Streams hybrid. SocketIO for UI push, Redis for agent queue.
**Effort:** 3 days. Phase 140.2 (start with SocketIO-only in Sprint 1).

---

## VII. GROK RESEARCH SUMMARY (2026-02-11)

Full report: `docs/136_ph/Research ReporGROK.txt`

| Topic | Key Finding | VETKA Action | Phase |
|-------|------------|--------------|-------|
| Meilisearch vs Weaviate | Keep both: Weaviate for graph, Meili for fast BM25 | Add Meilisearch Docker | 140.1 |
| Poincaré Embeddings | Custom GeoOpt/PyTorch, +25% hierarchy recall | poincare_encoder.py | 141 |
| Sandbox Security | Docker+seccomp best, chroot unsafe for LLM code | sandbox_exec.py | 142 |
| Event-Driven Dispatch | SocketIO+Redis Streams hybrid | Replace polling heartbeat | 140.2 |

---

## VIII. REMAINING PENDING TASKS (Pre-Sprint)

These old tasks should be triaged into Sprint 1-2 or archived:

| Task ID | Title | Priority | Action |
|---------|-------|----------|--------|
| tb_1770805987_8 | Jarvis superagent | P2 | → Sprint 2 (S2.1) |
| tb_1770577538_9 | Research: search/embedding models | P4 | Archive or → Sprint 3 |
| tb_1770577538_10 | Research: folder auto-detection | P4 | ✅ Done by Cursor W3 → Close |
| tb_1770577538_12 | Model fallback chain | P4 | → Sprint 2 (S2.4) |
| tb_1770577538_1 | Fix file positioning directed mode | P5 | → Sprint 1 backlog |
| tb_1770577538_5 | Fix drag and drop import | P5 | → Sprint 1 backlog |
| tb_1770577538_7 | Fix group chat naming | P5 | → Sprint 1 backlog |

---

## IX. SUCCESS METRICS

### A) Shipped Metrics (Delivery)
| Metric | Current | Sprint 1 Target | Sprint 5 Target |
|--------|---------|-----------------|-----------------|
| TaskBoard tasks auto-closed (with `tb_...` in commit) | 30% | 80% | 95% |
| Pipeline E2E success rate | ~60% | 75% | 90% |
| Search providers implemented | 3 (file, semantic, web) | 4 (+ social adapter) | 5 (+ messenger) |
| Knowledge graph backend features shipped | 0 | 0 | 6 core modules |
| Playground capabilities shipped | 0 | 0 | Full isolate+approve flow |
| Test suite count (strategic areas) | ~40 | 60+ | 100+ |

### B) Adopted Metrics (Usage/Impact)
| Metric | Current | Sprint 1 Target | Sprint 5 Target |
|--------|---------|-----------------|-----------------|
| Cmd+K usage share of search requests | n/a | 40% | 75% |
| Artifact approve/reject actions from MCC | n/a | 30/day | 150/day |
| Median time from task creation to first claim | n/a | <5 min | <1 min |
| Human interventions per pipeline task | ~3 | ~1 | ~0.2 |
| Voice sessions/day (Jarvis) | 0 | 0 | 100+ |
| Cross-user shared tree operations/day | 0 | 0 | 200+ |

---

## X. RISK LOG

| ID | Risk | Probability | Impact | Mitigation | Owner | Trigger |
|----|------|-------------|--------|------------|-------|---------|
| R1 | Agents commit via plain git, auto-close not triggered | High | High | Enforce `vetka_git_commit` in DoD + pre-commit checks in agent prompts | Opus | Task done but board status unchanged |
| R2 | S2.2 Jarvis MCP blocks due to shared-state contention | Medium | High | Isolate Jarvis runtime + contract tests for routing/latency | Codex | p95 latency regression under pipeline load |
| R3 | Model directory provider APIs unstable | Medium | Medium | Cache + graceful degradation + provider health badges | Codex | Empty/partial model list in UI |
| R4 | Event-driven heartbeat introduces duplicate dispatch | Medium | High | Idempotent dispatch key + dedup window + audit tests | Opus | Same task executed multiple times |
| R5 | Playground isolation leaks write access | Low | Critical | Docker seccomp + readonly mounts + integration security tests | Codex | Any write outside sandbox path |
| R6 | Scope creep in Sprint 2 (voice + UI + MCP at once) | High | Medium | Phase gates with acceptance test per task and strict WIP limits | Opus | >2 P1 tasks overdue simultaneously |

---

## XI. PHASE TIMELINE

```
Feb 2026   ├─ Phase 137: Combat Ready (Sprint 1)
           │    Event-driven heartbeat, search wiring, stabilize
           │
Mar 2026   ├─ Phase 138: Jarvis Awakens (Sprint 2)
           │    Superagent, model routing, deep folder modes
           │
           ├─ Phase 139: Living Knowledge (Sprint 3)
           │    Knowledge graph construction, clustering, UMAP
           │
Apr 2026   ├─ Phase 140: The Playground (Sprint 4)
           │    Sandbox, approval workflow, token budgets
           │
           ├─ Phase 141-145: Social VETKA (Sprint 5)
           │    Telegram, shared trees, federation
           │
May+ 2026  └─ Phase 146+: VETKA Public
                 Open beta, user onboarding, marketplace
```

---

*Generated by Opus Commander | Phase 136 | 2026-02-11*
*Based on reconnaissance of: 125_ph, 127_ph, 128_ph, 130_ph, 134_ph, 136_ph, 139_ph, 140_ph docs*
