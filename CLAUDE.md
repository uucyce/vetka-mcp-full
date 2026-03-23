# VETKA Project — Agent Instructions

## TL;DR — Your First Task in 3 Steps
```
1. mcp__vetka__vetka_session_init          → get project context + current phase
2. mcp__vetka__vetka_task_board action=list filter_status=pending  → find a task
3. Claim → Do work → mcp__vetka__vetka_task_board action=complete task_id=<id>
```

## ON CONNECT (MANDATORY)

1. Call `mcp__vetka__vetka_session_init` — loads current phase, digest, preferences.
2. Check your environment:
   ```bash
   git branch --show-current
   ```
   - **`main`** → you can create docs, commit freely, auto-push is ON.
   - **`claude/*` or other** → you are in a **worktree**. Code only, no shared docs. See [Worktree Rules](#worktree-rules).
3. Read latest handoff: `docs/190_ph_CUT_WORKFLOW_ARCH/HANDOFF_CUT_COMMANDER_*.md` (most recent by date).
4. Read latest feedback: `docs/190_ph_CUT_WORKFLOW_ARCH/feedback/FEEDBACK_WAVE*.md` (most recent).

**MCP namespace:** All tools use full prefix: `mcp__vetka__<tool>` or `mcp__mycelium__<tool>`.
If using ToolSearch: `select:mcp__vetka__vetka_session_init`.

## WORK ENTRY PROTOCOL (MANDATORY)

**ZERO naked commits.** Every line of code MUST trace to a task on the board.

### Decision tree — before ANY code change:

```
START
  │
  ├─ Is there a Roadmap doc for this phase?
  │   ├─ NO  → Create roadmap: docs/{phase}_ph/ROADMAP_{phase}.md
  │   │         Then generate tasks from it → task board
  │   │
  │   └─ YES → Are there tasks on the board for this work?
  │       │
  │       ├─ YES → Claim it:
  │       │         vetka_task_board action=claim task_id=<id> assigned_to=<agent>
  │       │         → DO WORK → vetka_task_board action=complete task_id=<id>
  │       │
  │       └─ NO  → DUPLICATE CHECK first:
  │                 1. vetka_task_board action=list → scan ALL pending/hold tasks
  │                 2. Search for keywords from your new task title
  │                 3. Overlap found → UPDATE existing task, don't create new
  │                 4. No match → CREATE: vetka_task_board action=add title="..." priority=N phase_type=...
  │                 → Claim → DO WORK → Complete
  │
  └─ NEVER skip to coding. NEVER use raw git commit.
```

### Task Board — MCP ONLY (MANDATORY)

**NEVER read or write `data/task_board.json` directly.** Always use MCP:
- `vetka_task_board action=add` — create
- `vetka_task_board action=list` — read
- `vetka_task_board action=update` — modify
- `vetka_task_board action=complete` — close (auto-commits + digest + push)

Direct JSON edits bypass validation and create invisible tasks. This already caused a data loss bug.

### Task granularity:
- **Big feature (>30 min):** Roadmap doc → multiple tasks → claim one at a time
- **Small fix (<30 min):** Create 1 task → claim → fix → complete
- **Research:** `phase_type=research` → complete (no commit needed)

### Commit flow (the ONLY path):
```
vetka_task_board action=complete task_id=<id>
  → auto-stages changed files (scoped, not -A)
  → auto-commits with [task:tb_xxxx]
  → pre-commit hook updates digest
  → post-commit hook pushes (on main only)
  → task marked done
```
Optional: pass `commit_message` to customize. Default: `"complete: {task title} [task:{task_id}]"`.
If commit fails, task stays open — fix and retry.

**Best practice:** Always include `[task:tb_xxxx]` in commit messages for reliable auto-close.

## Architecture

- **Stack:** Tauri (Rust) + React (TypeScript) + Python FastAPI backend
- **Backend:** FastAPI + SocketIO on port 5001
- **Frontend:** React + Three.js 3D visualization + Dockview panels
- **Config:** `data/templates/model_presets.json` (team presets), `.mcp.json` (MCP servers)
- **Reference:** FCP7 User Manual = "Old Testament" (NLE spec), `CUT_Interface_Architecture_v1.docx` = "New Testament"

### Dual MCP Servers

| Server | Namespace | Port | Purpose |
|--------|-----------|------|---------|
| **VETKA** | `mcp__vetka__*` | 5001 | Fast stateless: search, read, edit, git, camera |
| **MYCELIUM** | `mcp__mycelium__*` | 8082 WS | Async: pipelines, LLM calls, heartbeat |

VETKA = fast ops. MYCELIUM = long-running pipelines (60-300s) in a separate process.

### Mycelium Pipeline

Fractal agent system: Architect → Researcher → Coder → Verifier.
Auto-tier selection based on complexity. Three Dragon tiers (Bronze/Silver/Gold) — see `model_presets.json`.

Chat commands: `@dragon <task>`, `@doctor <question>`, `@pipeline <task>`.

## Multi-Agent Fleet

Up to 6 agents, ONE codebase, ONE TaskBoard. Fleet composition is dynamic — see latest handoff for active agents and branches.

### Roles (current as of session init)

| Role | Branch Pattern | Domain |
|------|---------------|--------|
| **Commander** (Opus on main) | `main` | Architecture, dispatch, merge, QA gate |
| **Engine** agent | `claude/cut-engine` | Store, timeline, editing ops, hotkeys |
| **Media** agent | `claude/cut-media` | Audio, video, codecs, export, color |
| **UX** agent | `claude/cut-ux` | Panels, menus, CSS, visual polish |
| **QA** agents (1-2) | `claude/cut-qa`, `claude/cut-qa-2` | Tests, compliance, regression |
| **Harness** agent | worktree | Task board fixes, MCP tools, infra |

For current agent assignments, check: `vetka_task_board action=list` → `assigned_to` field.

### Commander Protocol

**Commander (Opus on main) NEVER writes code.** Not even one-line fixes. Always delegate to an agent.

Commander responsibilities:
1. **Dispatch** — give strategic missions with horizon, not incremental tasks
2. **QA Gate** — every merge must pass QA verification first
3. **Merge** — `vetka_task_board action=merge_request` (never raw `git merge`)
4. **Debrief** — 6 provocative questions at session end (see feedback docs)

Commander role prompt: `docs/190_ph_CUT_WORKFLOW_ARCH/COMMANDER_ROLE_PROMPT.md`

### QA Gate (MANDATORY before merge)

```
Agent completes work → done_worktree
  → QA agent reviews: vetka_task_board action=verify task_id=<id> verdict=PASS|FAIL
  → Commander merges: vetka_task_board action=merge_request task_id=<id>
  → done_main
```

**No merge without QA PASS.** No exceptions, no "quick merge."

### Task Lifecycle

```
1. LIST:     vetka_task_board action=list filter_status=pending
2. CLAIM:    vetka_task_board action=claim task_id=<id> assigned_to=<agent>
3. DO WORK:  Edit files, run tests
4. COMPLETE: vetka_task_board action=complete task_id=<id> [branch=claude/<name>]
             → auto: git commit + digest + task status updated
5. QA:       vetka_task_board action=verify task_id=<id> verdict=PASS
6. MERGE:    vetka_task_board action=merge_request task_id=<id>
             → auto: git merge to main + push + done_main
```

### File Ownership

- **Claim = declare files** in task description: `"Working on: VideoPreview.tsx, AudioLevelMeter.tsx (new)"`
- **Never edit files** claimed by another agent
- **Conflict?** STOP → report overlap → wait for user to decide
- **Only the author** (or a QA verifier) can close a task

### Worktree Rules

| Content | Where | Why |
|---------|-------|-----|
| Code (*.ts, *.py) + tests | Worktree branch | Isolated dev |
| Docs, roadmaps, handoffs | **Main only** | Must be visible to all agents |
| Task board | **MCP only** | Single source of truth |

Worktree docs are invisible to other agents and the user.
Need a shared doc from worktree? Ask the user to cherry-pick it to main.

**Task completion from worktree — MANDATORY:**
MCP server runs on main repo, so `_detect_git_branch()` always returns `main`.
**You MUST pass `branch` explicitly:**
```
vetka_task_board action=complete task_id=<id> branch=claude/<worktree-name>
```
This sets status to `done_worktree` instead of `done`. Without `branch=`, the task wrongly closes as `done` on main.

**Ports:** Main = 3001/5001. Worktrees = 3003+/shared 5001.

## UI Design Rules

- **Monochrome ONLY.** ZERO color except color correction panels and markers.
- **Grey palette:** `#0a0a0a` / `#111` / `#1a1a1a` / `#2a2a2a` / `#888` / `#ccc`
- **FCP7 principle:** Professional NLE = no candy colors. White monochrome SVG/PNG icons only.
- **No emoji/colored icons** in UI components. Ever.
- **Pre-merge check:** Grep for non-monochrome hex values before any merge.

## Key Dynamic References

| What | Where |
|------|-------|
| Current phase + state | `vetka_session_init` (always call first) |
| Active tasks | `vetka_task_board action=list` |
| Task details + recon docs | `vetka_task_board action=get task_id=<id>` → field `recon_docs` |
| Agent roadmaps | `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_*.md` |
| Agent feedback/debrief | `docs/190_ph_CUT_WORKFLOW_ARCH/feedback/` |
| Session handoffs | `docs/190_ph_CUT_WORKFLOW_ARCH/HANDOFF_CUT_COMMANDER_*.md` |
| Commander role | `docs/190_ph_CUT_WORKFLOW_ARCH/COMMANDER_ROLE_PROMPT.md` |
| FCP7 manual (Old Testament) | `docs/besedii_google_drive_docs/` or Google Drive |
| CUT architecture (New Testament) | `CUT_Interface_Architecture_v1.docx` |

## Methodology (Opus = Commander)

For non-trivial tasks, deploy your army:

| Regiment | Use For | Speed |
|----------|---------|-------|
| Haiku Scouts (3-9 parallel) | Recon: grep, read, MARKER tags | Seconds |
| Sonnet Verifiers (2-3) | Cross-check, unified report | Medium |
| Dragon (via @dragon) | Implementation (auto-tier) | Minutes |
| Grok (via user relay) | Web research, codebase analysis | User relays |
| Opus (you) | Architecture, final decisions | Save budget |

**Battle plan:** Recon (Haiku) → Verify (Sonnet) → Research (Grok) → Execute (Dragon) → Review (Opus).
Always write the FULL plan before executing. The user wants to see WHO does WHAT.

## Rules

1. **`session_init` FIRST** — every new conversation
2. **Read latest handoff + feedback** — before any work
3. **No code without a task** — follow the decision tree above
4. **No raw `git commit`** — always `vetka_task_board action=complete`
5. **No merge without QA** — always verify before merge_request
6. **Commander never codes** — delegate everything, even one-liners
7. **MARKER_XXX.Y** convention for code comments
8. **Tests:** `python -m pytest tests/ -v`
9. **Monochrome UI** — zero color except correction/markers
10. **Don't ask obvious questions** — if it's in loaded docs, just execute
