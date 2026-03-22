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
- **Frontend:** React + Three.js 3D visualization
- **Config:** `data/templates/model_presets.json` (team presets), `.mcp.json` (MCP servers)

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

## Multi-Agent Sync

Three agents, ONE codebase, ONE TaskBoard:

| Agent | Role | Typical Tasks |
|-------|------|---------------|
| **Opus** (Claude Code) | Architect-Commander | Architecture, pipeline, infra |
| **Cursor** | Frontend Engineer | UI, DAG viz, components |
| **Codex** (worktree) | Specialist | Tests, cleanup, isolated modules |

### Task Lifecycle

```
1. LIST:     vetka_task_board action=list filter_status=pending
2. CLAIM:    vetka_task_board action=claim task_id=<id> assigned_to=<agent>
3. DO WORK:  Edit files, run tests
4. COMPLETE: vetka_task_board action=complete task_id=<id>
             → auto: git commit + digest + push (on main) + task closed
```

### File Ownership

- **Claim = declare files** in task description: `"Working on: VideoPreview.tsx, AudioLevelMeter.tsx (new)"`
- **Never edit files** claimed by another agent
- **Conflict?** STOP → report overlap → wait for user to decide
- **Only the author** (or a QA verifier) can close a task

### Worktree Rules

| Content | Where | Why |
|---------|-------|-----|
| Code (*.ts, *.py) + tests | Worktree ✅ | Isolated dev |
| Docs, CLAUDE.md, handoffs | **Main only** ❌ | Must be visible to all agents |
| Task board | **MCP only** | Single source of truth |

Worktree docs are invisible to other agents and the user.
Need a shared doc from worktree? Ask the user to cherry-pick it to main.

**⚠️ Task completion from worktree — MANDATORY:**
MCP server runs on main repo, so `_detect_git_branch()` always returns `main`.
**You MUST pass `branch` explicitly:**
```
vetka_task_board action=complete task_id=<id> branch=claude/<worktree-name>
```
This sets status to `done_worktree` instead of `done`. Without `branch=`, the task wrongly closes as `done` on main.

**Ports:** Main = 3001/5001. Worktrees = 3003+/shared 5001.

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
2. **No code without a task** — follow the decision tree above
3. **No raw `git commit`** — always `vetka_task_board action=complete`
4. **MARKER_XXX.Y** convention for code comments
5. **Tests:** `python -m pytest tests/ -v`
