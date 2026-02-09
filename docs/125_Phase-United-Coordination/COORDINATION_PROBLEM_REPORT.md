# VETKA United Coordination — Problem Report

## Executive Summary

VETKA has multiple parallel systems that need unified coordination:
- Multiple Claude agents working simultaneously (Code, Desktop)
- TaskBoard for Mycelium Pipeline dispatch
- BMAD methodology
- Git for version control (post-factum)
- Future: VETKA 3D visualization of work in progress

**Core Problem:** Coordination happens AFTER work (git commits), but we need coordination BEFORE work starts.

---

## Current Systems Audit

### 1. TaskBoard (Phase 121)
**Location:** `src/orchestration/task_board.py`, `data/task_board.json`

```
Purpose: Queue tasks for Mycelium Pipeline (Dragon/Titan teams)
Flow: Add Task → Priority Queue → Dispatch → Pipeline → Update Status
Scope: Pipeline execution tasks only
```

**Strengths:**
- Priority system (1-5)
- Complexity tracking
- Dependencies between tasks
- Status lifecycle (pending → running → done)

**Gap:** Doesn't track which AGENT is working on what (Claude Code vs Desktop)

---

### 2. Phase Numbering (Ad-hoc)
**Location:** Commit messages, MARKER comments

```
Current: Manual numbering in commit messages
Problem: Phase 124 conflict — both Claude Code and Desktop used it
```

**Conflict Example:**
| Agent | Phase 124 Work |
|-------|----------------|
| Claude Code | Wobble Animation, Camera, Glow timing |
| Claude Desktop | FC wrappers, E2E fixes, Task Board UI |

**Gap:** No reservation/coordination mechanism

---

### 3. BMAD Methodology
**Location:** `docs/` folder, methodology docs

```
Purpose: Big-picture planning and methodology
Scope: High-level architecture decisions
```

**Gap:** Not integrated with real-time task coordination

---

### 4. Git (Post-factum)
**Location:** `.git/`

```
Purpose: Version control, history
Timing: AFTER work is done
```

**Gap:** Discovers conflicts after the fact, not before

---

### 5. VETKA 3D Visualization
**Location:** `client/src/components/canvas/`

```
Purpose: Visual representation of project structure
Current: Files, folders, chat nodes, artifacts
```

**Opportunity:** Could visualize active work, agent assignments, phase progress

---

## The Philosophy: Before vs After

```
CURRENT STATE:
┌─────────────────────────────────────────────────────────────┐
│  Agent A starts work                                        │
│  Agent B starts work (unknowingly on same area)             │
│  ... work happens ...                                       │
│  Git commit A                                               │
│  Git commit B  ← CONFLICT DISCOVERED HERE (too late!)       │
└─────────────────────────────────────────────────────────────┘

DESIRED STATE:
┌─────────────────────────────────────────────────────────────┐
│  Agent A: "I want to work on X"                             │
│  Coordinator: "X is available, assigned Phase 125"          │
│  Agent B: "I want to work on X"                             │
│  Coordinator: "X is taken by Agent A, try Y instead"        │
│  ... work happens without conflicts ...                     │
│  Git commits are clean                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Proposed: United Coordination System

### Core Components

1. **Phase Registry** — Who is working on what phase
2. **Work Reservation** — Lock areas before starting
3. **Agent Roster** — Active agents and their capabilities
4. **Live Dashboard** — VETKA 3D visualization of work in progress

### Data Model Draft

```json
{
  "coordination": {
    "next_phase_id": 128,
    "active_agents": {
      "claude-code-session-abc": {
        "name": "Claude Code",
        "started": "2026-02-09T01:00:00Z",
        "working_on": ["Phase-125", "client/src/components/canvas/"]
      },
      "claude-desktop-session-xyz": {
        "name": "Claude Desktop",
        "started": "2026-02-09T00:30:00Z",
        "working_on": ["Phase-126", "src/orchestration/"]
      }
    },
    "reserved_areas": {
      "client/src/components/canvas/FileCard.tsx": "claude-code-session-abc",
      "src/orchestration/agent_pipeline.py": "claude-desktop-session-xyz"
    },
    "phases": {
      "125": {"name": "Wobble Animation", "agent": "claude-code", "status": "in_progress"},
      "126": {"name": "Pipeline Improvements", "agent": "claude-desktop", "status": "in_progress"}
    }
  },
  "task_board": { /* existing TaskBoard */ },
  "bmad": { /* methodology reference */ }
}
```

### Integration Points

1. **CLAUDE.md** — Add coordination protocol
2. **MCP Tools** — `vetka_reserve_phase`, `vetka_release_phase`, `vetka_get_active_work`
3. **VETKA 3D** — Visualize active work (glow for files being edited, agent avatars?)
4. **Heartbeat** — Periodic check-in from agents

---

## Questions for Grok Research

1. How to handle agent session management (timeouts, crashes)?
2. File-level vs folder-level vs phase-level locking?
3. How does this integrate with existing TaskBoard?
4. BMAD integration — how to connect high-level planning?
5. VETKA 3D visualization — how to show "work in progress"?
6. Conflict resolution — what if two agents need same file?
7. Git integration — auto-generate branch names from phases?

---

## Files to Analyze

- `src/orchestration/task_board.py` — existing task queue
- `src/orchestration/mycelium_heartbeat.py` — heartbeat system
- `src/orchestration/agent_pipeline.py` — pipeline execution
- `CLAUDE.md` — agent instructions
- `client/src/store/useStore.ts` — frontend state
- `client/src/components/canvas/FileCard.tsx` — node visualization
- `docs/` — BMAD and methodology docs

---

## Next Steps

1. Grok research on unified coordination architecture
2. Design decision on scope (phase-level vs file-level)
3. Prototype in `src/coordination/` or extend TaskBoard
4. MCP tools for agent coordination
5. VETKA 3D visualization of active work
