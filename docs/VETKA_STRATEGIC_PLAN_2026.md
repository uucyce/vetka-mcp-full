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

| # | Task | Agent | Priority | Complexity |
|---|------|-------|----------|------------|
| S1.1 | Heartbeat: event-driven dispatch (SocketIO emit on new task) | Opus | P1 | High |
| S1.2 | Unified Search: wire web provider (Tavily via vetka_web_search) | Codex | P1 | Medium |
| S1.3 | Unified Search: wire Cmd+K frontend → unified backend | Cursor | P1 | Medium |
| S1.4 | MCC Stats: connect to real pipeline_history data | Cursor | P2 | Medium |
| S1.5 | Artifact panel: connect Cursor ArtifactViewer → Codex API endpoints | Cursor | P2 | Low |
| S1.6 | Tests: heartbeat daemon + unified search E2E | Codex | P2 | Medium |
| S1.7 | TaskBoard: cleanup old P4-P5 stale tasks | Opus | P3 | Low |

### SPRINT 2 — "Jarvis Awakens" (Phase 138, ~1-2 weeks)
**Goal:** Intelligent chat agent that knows user, searches everything.

| # | Task | Agent | Priority | Complexity |
|---|------|-------|----------|------------|
| S2.1 | Jarvis superagent: chat handler with Engram memory + model routing | Opus→Dragon Gold | P1 | High |
| S2.2 | Jarvis: tool calling (search, file read, pipeline dispatch) | Codex | P1 | High |
| S2.3 | Jarvis UI: integrate into existing ChatPanel | Cursor | P1 | Medium |
| S2.4 | Model fallback chain with key roaming | Codex | P2 | High |
| S2.5 | Chat history: semantic search over conversations | Codex | P2 | Medium |
| S2.6 | Folder modes: deep mode (workflow/code/media/knowledge UI variants) | Cursor | P2 | High |

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

| Metric | Current | Sprint 1 Target | Sprint 5 Target |
|--------|---------|-----------------|-----------------|
| TaskBoard tasks auto-closed | 30% | 80% | 95% |
| Pipeline E2E success rate | ~60% | 75% | 90% |
| Search sources active | 2 (file, semantic) | 4 (+ web, social) | 5 (+ messenger) |
| Knowledge graph nodes | 0 | 0 | 50K+ |
| Playground experiments/day | 0 | 0 | 10+ |
| Human interventions/task | ~3 | ~1 | ~0.2 |
| Test coverage | ~40 tests | 60+ | 100+ |

---

## X. PHASE TIMELINE

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
