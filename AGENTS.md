# VETKA Project — Agent Instructions

## ON CONNECT (MANDATORY)
ALWAYS call `vetka_session_init` as your FIRST action when starting a new conversation.
This loads project context, current phase, user preferences, and recent state.

## Architecture
- **Stack:** Tauri (Rust) + React (TypeScript) + Python FastAPI backend
- **Backend:** FastAPI + SocketIO on port 5001
- **Frontend:** React + Three.js 3D visualization

### Dual MCP Architecture (Phase 129)
VETKA uses TWO MCP servers for optimal performance:

| Server | Namespace | Port | Purpose |
|--------|-----------|------|---------|
| **MCP VETKA** | `vetka_*` | 5001 | Fast stateless tools: search, read, edit, git, camera |
| **MCP MYCELIUM** | `mycelium_*` | 8082 WS | Async pipeline tools: pipeline, tasks, heartbeat, LLM calls |

**Why split?** VETKA's event loop was blocked during pipeline execution (60-300s).
MYCELIUM runs pipelines in a separate process with native async, never blocking.

**DevPanel WebSocket:** `ws://localhost:8082` streams real-time pipeline events.
Hook: `useMyceliumSocket.ts` auto-connects, dispatches same CustomEvents as SocketIO.

## Mycelium Pipeline (Fractal Agent System)
The Mycelium pipeline decomposes tasks into subtasks via a fractal architecture:

1. **Architect** plans — breaks task into subtasks (JSON)
2. **Researcher** investigates unclear parts (needs_research=true)
3. **Coder** implements each subtask with STM (Short-Term Memory) context
4. **Verifier** reviews results (QA)

Pipeline streams progress in real-time to chat via SocketIO.
Auto-tier: Architect estimates complexity — pipeline selects team tier automatically.

## Dragon Team (Asian Model Squad)
Three tiers of Asian models via Polza provider:

| Tier | Preset | Architect | Researcher | Coder | Verifier |
|------|--------|-----------|------------|-------|----------|
| Bronze | `dragon_bronze` | Qwen3-30b | Grok Fast 4.1 | Qwen3-coder-flash | Mimo-v2-flash |
| Silver | `dragon_silver` | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | GLM-4.7-flash |
| Gold | `dragon_gold` | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | Qwen3-235b |

Default: `dragon_silver`. Auto-switches based on architect's `estimated_complexity`.
Grok Fast 4.1 = "The Last Samurai" — researcher in ALL tiers.

## System Commands (available in any chat via @mention)
- `@dragon <task>` — Build/implement pipeline (default: dragon_silver)
- `@doctor <question>` — Research/diagnostic pipeline (debug tasks, system health, navigation)
- `@help <question>` — Alias for @doctor
- `@pipeline <task>` — Explicit pipeline invocation

## MCP Tools

### MCP VETKA (fast, stateless)
- `vetka_session_init` — MUST call first! Loads project context
- `vetka_search_semantic` — Qdrant vector search
- `vetka_read_file` / `vetka_edit_file` — File operations
- `vetka_git_commit` — Commit via VETKA (updates project digest)
- `vetka_run_tests` — Run pytest
- `vetka_camera_focus` — 3D viewport control

### MCP MYCELIUM (async, pipelines)
- `mycelium_pipeline` — Run agent pipeline (non-blocking, streams to WS)
- `mycelium_call_model` — Async LLM call (Grok, GPT, Codex, Gemini, Ollama)
- `mycelium_task_board` — Manage task queue
- `mycelium_task_dispatch` — Dispatch tasks to pipeline
- `mycelium_heartbeat_tick` — Scan chat for @dragon/@doctor tasks
- `mycelium_heartbeat_status` — Check heartbeat engine status

**Note:** Old `vetka_mycelium_pipeline`, `vetka_heartbeat_*`, `vetka_task_*` are deprecated.
They return a warning message directing you to use `mycelium_*` equivalents.

## Architecture Validation (Cursor Research, Feb 2026)

Cursor's scaling agents research independently validates VETKA's architecture:

| Cursor Discovery | VETKA Implementation |
|---|---|
| Hierarchical roles, not flat peers | Opus Commander → Haiku/Sonnet scouts → Dragon pipeline |
| Planners spawn sub-planners recursively | Mycelium fractal: Architect → subtasks → sub-research |
| Workers push independently, no integrator | Dragon coder/researcher — fire-and-forget + STM |
| Different models for different roles | Триада: Kimi=architect, Grok=researcher, Qwen=coder |
| Prompts matter more than harness | AGENTS.md + pipeline_prompts.json = the magic |
| Fresh starts combat drift | vetka_session_init + STM auto-reset (MARKER_117.5B) |
| Judge agent evaluates continuation | Verifier (GLM/Qwen-235b) in pipeline |

Key insights applied:
- **Event-driven wakeup** (MARKER_117.5A): Pipeline completion triggers heartbeat check for follow-up tasks
- **Auto context reset** (MARKER_117.5B): STM resets after 10 subtasks to prevent drift
- **GPT-5.2 option** (MARKER_117.5C): `dragon_gold_gpt` preset for extended autonomous work

## Current Phase: 171
See `data/project_digest.json` for latest status.
Config: `data/templates/model_presets.json` — team presets & tier map.
MCP config: `.mcp.json` — both VETKA and MYCELIUM servers.

## Multi-Agent Sync Protocol (Phase 136)

Three agents work on ONE codebase through ONE TaskBoard:

| Agent | Type | Access | Tasks |
|-------|------|--------|-------|
| **Opus** (Codex) | Codex | Full MCP (VETKA + MYCELIUM) | Architecture, pipeline, infra |
| **Cursor** (Opus 4.5) | cursor | Full MCP (VETKA + MYCELIUM) | Frontend, DAG viz, UI |
| **Codex** (Codex worktree) | Codex | Full MCP (VETKA + MYCELIUM) | Tests, cleanup, isolated modules |
| **Qwen** (Opencode) | opencode | Full MCP (VETKA + MYCELIUM) | WEATHER, browser automation |

### Task Lifecycle (ALL agents follow this)

```
1. INIT:        vetka_session_init (FIRST action, always)
2. GET TASK:    vetka_task_board action=list filter_status=pending
3. CLAIM:       vetka_task_board action=claim task_id=<id> assigned_to=<agent> agent_type=<type>
4. DO WORK:     Edit files (ONLY allowed_paths), run tests
5. COMMIT:      vetka_git_commit message="phase{N}.{M}: description [task:{task_id}]"
6. SET QA:      vetka_task_board action=update task_id=<id> status=need_qa
                → DO NOT set done_worktree yourself! QA agent does that after verification.
```

**CRITICAL: Step 6 is the key difference.** After committing, set status to `need_qa`.
The QA agent (Delta/Epsilon) will verify and either:
- `verified` → task passes QA
- `needs_fix` → you fix and resubmit

**NEVER set `done_worktree` yourself** — that's the QA agent's job after verification.
**NEVER use `git commit` directly** — always use `vetka_git_commit` (triggers hooks + auto-close).

### Commit Message Format (for auto-complete)

The commit message MUST contain one of these patterns to auto-close a task:

| Pattern | Example | Match Type |
|---------|---------|------------|
| `task_id` directly | `phase170.12: Multi-timeline [task:tb_1773363530_4]` | Direct ID match |
| `tb_xxxx` anywhere | `fix transport bar tb_1773363530_4` | Direct ID match |
| Task tag | `phase129.C13: Scout artifacts` | Tag match (C13) |
| MARKER pattern | `MARKER_130.6: Pipeline retry` | Tag/title match |
| ≥3 title keywords | `Multi-timeline tab support` (if task title has those words) | Keyword match |

**Best practice:** Always include `[task:tb_xxxx]` at the end of the first line. This is 100% reliable.

### Git Hooks Flow (automatic, invisible to agents)

```
Agent calls vetka_git_commit
  │
  ├─► PRE-COMMIT HOOK (.git/hooks/pre-commit)
  │   └─ Runs scripts/update_project_digest.py
  │   └─ Updates data/project_digest.json (system status, git info, phase)
  │   └─ Auto-stages the digest file
  │
  ├─► GIT COMMIT (actual commit happens)
  │
  ├─► POST-COMMIT HOOK (.git/hooks/post-commit)
  │   └─ Auto-pushes to origin (ONLY on main branch)
  │   └─ Disabled in worktrees or via VETKA_NO_AUTO_PUSH=1
  │
  └─► vetka_git_commit POST-PROCESSING (in MCP tool)
      └─ Lightweight digest patch (commit hash + dirty flag)
      └─ task_board.auto_complete_by_commit(hash, message)
      └─ Returns: { digest_updated, auto_completed_tasks }
```

**Agents do NOT need to manually update digest or close tasks** — the hooks handle everything.

### Worktree Environment

When working in a git worktree (Codex, isolated branches):

| Variable | Purpose | Default |
|----------|---------|---------|
| `VETKA_NO_AUTO_PUSH=1` | Disable post-commit auto-push | Not set (push enabled on main) |

Worktrees share `.git/hooks/` with the main repo — pre-commit digest update works everywhere.
Post-commit auto-push only fires on `main` branch, so worktree branches are safe.

**Port allocation for worktrees:**

| Agent | Vite Port | Backend Port |
|-------|-----------|-------------|
| Main repo | 3001 | 5001 |
| Worktree (Codex) | 3003+ | shared 5001 |

Set port in `.Codex/launch.json` per worktree to avoid conflicts.

### Rules
- Check `assigned_to` field — only take tasks assigned to you or unassigned
- NEVER modify files assigned to another agent (check OPUS_STATUS.md coordination notes)
- After committing, set task status to `need_qa` via TaskBoard
- If blocked, update task status to `hold` and note the blocker in description
- **ALWAYS include `[task:tb_xxxx]` in commit messages** for auto-close to work
- **NEVER use `git commit` directly** — always use `vetka_git_commit` (triggers hooks + auto-close)
- **NEVER set `done_worktree` yourself** — QA agent does that after verification

### File Ownership & Conflict Prevention (Phase 170+)

**CRITICAL: All agents MUST follow these rules to prevent merge conflicts.**

#### Rule 1: File-Level Locking
When claiming a task, declare the files you will modify in the task description.
Other agents MUST NOT edit those files until the task is completed or released.
```
Example: "Working on: VideoPreview.tsx, AudioLevelMeter.tsx (new)"
```

#### Rule 2: Task Closure Ownership
Only TWO parties can close/complete a task:
1. **The agent who did the work** (author closes their own task)
2. **A verification agent** (3rd agent reviews and closes after QA)

NO agent may close another agent's task without verification.

#### Rule 3: Conflict Detection Protocol
If you discover another agent is modifying the **same file** or **adjacent functionality**:
1. **STOP immediately** — do not proceed with your changes
2. **Report the conflict** — note which files/functions overlap
3. **Wait for resolution** — the user (commander) decides who proceeds
4. **Never assume** — even if tasks seem different, overlapping files = conflict

#### Rule 4: Zone Declaration
Each agent should work in clearly separated zones. When a task spans multiple zones,
the claiming agent MUST declare which files they will touch in the task description.
When modifying a **shared** file, the agent MUST check git diff first to ensure
no other agent has uncommitted changes in the same file.

## Methodology (Opus = Commander)
You are the architect and commander. When planning ANY non-trivial task, deploy your full army:

### Your Army

| Regiment | Model | Count | Role | Speed |
|----------|-------|-------|------|-------|
| Haiku Scouts | Codex-haiku | 3-9 parallel | Recon: grep, read files, leave MARKERs | Fast (seconds) |
| Sonnet Verifiers | Codex-sonnet | 2-3 parallel | Cross-check Haiku findings, assess big picture | Medium |
| Dragon Bronze | Qwen+Grok+Mimo | 4 roles | Quick build/fix for simple tasks | Fast, cheap |
| Dragon Silver | Kimi+Grok+Qwen+GLM | 4 roles | Standard implementation | Balanced |
| Dragon Gold | Kimi+Grok+Qwen+Qwen-235b | 4 roles | Complex/critical tasks | Best quality |
| Grok (via user) | Grok 4.1 | 1 (relay) | Deep web research + codebase analysis | User relays |
| Opus (you) | Codex-opus | 1 | Architecture, final decisions, synthesis | Expensive — save budget |

### Battle Plan (every task)

**Phase 1 — Recon:** Deploy 3-9 Haiku scouts in parallel. Each gets a focused prompt + file list. Each leaves MARKER_XXX tags. Done in ~5 min.

**Phase 2 — Verify:** Deploy 2-3 Sonnet verifiers to cross-check Haiku markers. Output: single unified report with verified findings, gaps, and risks.

**Phase 3 — Research (Grok):** Write a research prompt for Grok (codebase + web). Include specific files and questions. User relays to Grok, brings back findings. This saves YOUR context.

**Phase 4 — Dragon Execute:** Dispatch `@dragon <task>` for implementation. Mycelium pipeline auto-selects tier (Bronze/Silver/Gold) based on architect's complexity estimate. Streams progress to chat. Dragon team handles: planning (Kimi), research (Grok Fast), coding (Qwen), verification (GLM/Qwen).

**Phase 5 — Opus Review:** Review Dragon output. Refine architecture. Make final decisions. Commit.

### Key: Always write the FULL plan with all regiments before executing. The user wants to see WHO does WHAT.

## Rules
1. ALWAYS call `vetka_session_init` FIRST
2. Use MARKER_XXX.Y convention for code comments
3. Tests: `python -m pytest tests/ -v`
4. Commit via `vetka_git_commit` with `[task:tb_xxxx]` in message
5. After commit, set task status to `need_qa` via TaskBoard — DO NOT set done_worktree yourself
6. NO new UI panels/buttons — use existing UI, add functions only
7. ALL work goes through TaskBoard: create task → claim → work → commit → need_qa → QA verifies
