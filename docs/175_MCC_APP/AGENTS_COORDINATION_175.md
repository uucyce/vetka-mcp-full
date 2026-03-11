# Phase 175+ Multi-Agent Coordination Protocol

> **Commander:** Opus (Claude Code)
> **Date:** 2026-03-11
> **Goal:** MYCELIUM.app → stable standalone dmg/app
> **Branch policy:** Each agent works on own branch, Opus merges

---

## Agent Roster

| Agent | ID | Territory | Branch | Phase Focus |
|-------|----|-----------|--------|-------------|
| **Codex A** | codex-alpha | Backend API + TaskBoard | `codex-a/175-backend-api` | 175.0 + 175.7 |
| **Codex B** | codex-beta | Frontend Analytics + UI | `codex-b/152-analytics-ui` | 152.5-152.11 + store fixes |
| **Dragon Team** | dragon-ops | Build infra + optimization | via pipeline | 175.5-175.6 + APNG |
| **Opus** | opus | Integration + UI testing + git | main work branch | 175 integration + all commits |

---

## Territory Map (NO CROSS-EDITING)

```
CODEX A owns:                          CODEX B owns:
├── src/api/routes/mcc_routes.py       ├── client/src/components/mcc/MiniBalance.tsx
│   (ONLY task endpoints section)      ├── client/src/components/mcc/FilterBar.tsx (NEW)
├── src/api/routes/chat_routes.py      ├── client/src/components/analytics/ (NEW dir)
│   (ONLY /chat/quick endpoint)        │   ├── StatsDashboard.tsx
├── src/api/routes/taskboard_routes.py │   ├── TaskDrillDown.tsx
│   (NEW file — generic REST)          │   └── TaskDAGPanel.tsx
├── src/orchestration/task_board.py    ├── client/src/store/useMCCStore.ts
│   (ONLY ADDABLE_FIELDS + methods)    │   (ONLY key management + analytics state)
├── src/orchestration/taskboard_adapters.py (NEW)
├── tests/test_175_backend_api.py (NEW)
└── tests/test_175_taskboard_adapters.py (NEW)

DRAGON TEAM owns:                      OPUS owns:
├── scripts/build_mycelium.sh          ├── ALL commits + merges
├── scripts/optimize_apng.sh (NEW)     ├── client/src/components/mcc/MyceliumCommandCenter.tsx
├── dist-mcc/ (build output)           ├── client/src/components/mcc/DAGView.tsx
├── client/src-tauri-mcc/ (build test) ├── client/src/MyceliumStandalone.tsx
└── APNG → WebP conversion pipeline    ├── client/src/mycelium-entry.tsx
                                       ├── client/vite.config.ts
                                       ├── Integration tests (all surfaces)
                                       └── docs/175_MCC_APP/ (all coordination docs)
```

---

## Dependency Graph

```
            PARALLEL                          SEQUENTIAL
     ┌──────────────────┐
     │   CODEX A        │──────┐
     │  (3 endpoints)   │      │
     └──────────────────┘      │
                               ├──→ OPUS: Integration Test ──→ OPUS: Commit
     ┌──────────────────┐      │        (all 4 surfaces)           ↓
     │   CODEX B        │──────┘                              OPUS: dmg build
     │  (analytics UI)  │
     └──────────────────┘
                               ┌──→ OPUS: APNG verify
     ┌──────────────────┐      │
     │   DRAGON TEAM    │──────┘
     │  (build + APNG)  │
     └──────────────────┘
```

**Codex A + Codex B + Dragon = PARALLEL** (no file overlap)
**Opus = SEQUENTIAL after all 3** (integration + commit)

---

## Sync Protocol

1. Each agent reads THIS document before starting
2. Each agent writes status to their own phase doc (see individual briefs)
3. Agents NEVER modify files outside their territory
4. When blocked, write to `docs/175_MCC_APP/BLOCKED_<agent>.md`
5. Opus monitors all docs, resolves conflicts, handles merges
6. **Test-first:** Every change must pass tests before Opus commits

---

## Self-Correction Loop (ALL agents follow)

```
1. READ brief + referenced docs
2. WRITE tests first (TDD)
3. IMPLEMENT code
4. RUN tests → if FAIL → fix → goto 3
5. RUN full suite → if FAIL → fix → goto 3
6. WRITE completion report to phase doc
7. STOP — wait for Opus to review + commit
```

**NEVER commit directly.** Opus handles all git operations after verification.
