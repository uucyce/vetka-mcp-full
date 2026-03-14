# Grok Research Request: Phase 152 — MCC Deep Stats + Dual DAG Architecture

## Context
VETKA is a Tauri (Rust) + React (TypeScript) + Python FastAPI application for visual AI agent orchestration. It has a **Mycelium Command Center (MCC)** that manages agent pipeline execution through a visual DAG interface.

**Phase 151 (just completed):** UX overhaul — unified header, per-agent stats collection, user feedback blending, onboarding overlay, compact/expanded panels.

**Phase 152 goal:** Transform MCC from a monitoring tool into a full analytics + project management platform.

## Current Architecture

### Backend Data Available (agent_pipeline.py)
```python
pipeline_stats = {
    "preset": "dragon_silver",           # Team preset
    "league": "dragon",                  # dragon | titan
    "phase_type": "build",               # build | fix | research
    "subtasks_total": 4,
    "subtasks_completed": 3,
    "success": True,
    "llm_calls": 12,
    "tokens_in": 45000,
    "tokens_out": 8000,
    "verifier_avg_confidence": 0.85,
    "duration_s": 220.6,
    "agent_stats": {
        "scout": {"calls": 2, "tokens_in": 3000, "tokens_out": 500, "duration_s": 8.0, "success_count": 2, "fail_count": 0, "retries": 0},
        "architect": {"calls": 1, "tokens_in": 5000, "tokens_out": 2000, "duration_s": 15.0, ...},
        "researcher": {"calls": 1, "tokens_in": 4000, "tokens_out": 1500, "duration_s": 12.0, ...},
        "coder": {"calls": 4, "tokens_in": 20000, "tokens_out": 3000, "duration_s": 120.0, "retries": 2, ...},
        "verifier": {"calls": 4, "tokens_in": 13000, "tokens_out": 1000, "duration_s": 25.0, ...},
    }
}
```

### Task Board (task_board.py)
Each task has: id, title, description, priority, complexity, phase_type, preset, status (pending/queued/running/done/failed/cancelled/hold), source, tags, assigned_to, agent_type, created_by, stats (pipeline_stats), result_status (applied/rework/rejected), adjusted_stats.

### Current Gaps
1. **No time-series data** — stats are per-task snapshots, no trending
2. **No retry/escalation tracking** in final stats (only coder retries tracked)
3. **No tier upgrade events** — `_upgrade_coder_tier()` works but not recorded in stats
4. **No chat_id in task** — tasks lose chat provenance after creation
5. **No playground↔task persistent link** — binding is dispatch-time only
6. **No STM persistence** — short-term memory dies on agent restart
7. **No fullscreen result viewer** — results stuck in 240px side panel
8. **No task editing UI** — users can't modify tasks from MCC
9. **No search by chat ID** — can't find tasks by originating chat
10. **Tasks from ALL sources mixed** — Dragon, Codex, Opus, manual all in one list

### User's Vision (verbatim feedback)
> "Статистика должна отвечать: За какое время? Кто - каждая роль и команда в целом? сколько токенов? сколько кругов перепроверки/эффективность. Объем выполненных задач какой, каждая задача в отдельности. Это должны быть графики полноценные с несколькими параметрами."

> "Два DAG: главный DAG — задач/проекта, на задачу определяется DAG воркфлоу-команда. Изначально часть превью — клик во весь экран DAG команды."

## Research Deliverables

### Deliverable 1: Analytics Dashboard Architecture
**Question:** How should we architect a full analytics dashboard for AI agent pipeline stats?

Research needed:
- **Time-series visualization** for agent performance over time (last hour, day, week, month)
  - What charting library? (Recharts is already in project, vs Nivo, vs Victory, vs custom Canvas)
  - What data format? Per-run snapshots → time-bucketed aggregations
  - Specific chart types for: success rate trend, token consumption trend, duration trend, retry frequency
- **Multi-dimensional comparison**:
  - Team comparison (Dragon Bronze vs Silver vs Gold)
  - Per-role efficiency (Scout avg time, Coder retry rate, Verifier rejection rate)
  - Cross-run improvement tracking (is the team getting better?)
- **Per-task drill-down**: Click task → full timeline (Scout started → Architect planned → Coder wrote → Verifier checked → retry → done)
  - Gantt chart or waterfall timeline per task
  - Token budget visualization (pie chart: who consumed what)
- **Weak-link detection**: Automated identification of bottleneck roles
  - What metrics define "weak"? Success rate < 60%? Retry count > 2? Duration > 2x median?
  - Visual highlighting (red glow, warning badge, ranked list)
- **Cost tracking**: Tokens → estimated cost per model per run

Reference examples: Datadog APM traces, Grafana dashboards, GitHub Actions workflow visualization, Weights & Biases experiment tracking.

### Deliverable 2: Dual DAG Architecture — Task DAG + Workflow DAG
**Question:** How to implement a two-level DAG system where Project/Task DAG is the top level, and each task node can drill down into its Workflow/Team DAG?

Research needed:
- **Task DAG (Level 1 — Roadmap):**
  - Nodes = tasks from TaskBoard
  - Edges = dependencies (already in task_board.py: `dependencies` field)
  - Layout: Sugiyama/hierarchical for sequential tasks, parallel lanes for concurrent
  - Auto-generation: "Titan team reads all docs/todos and forms Task DAG automatically"
  - How to determine parallel vs sequential? (by dependency graph? by file conflict matrix?)
  - Status coloring: pending (gray), running (pulse), done (green), failed (red), hold (yellow)

- **Workflow DAG (Level 2 — Team execution):**
  - Current implementation: Scout → Architect → Researcher → Coder → Verifier
  - Each node shows: model, duration, tokens, confidence
  - Existing in `DAGView.tsx` — already works

- **Visual drill-down UX:**
  - Option A: Click task node → zooms into workflow DAG (like Google Maps zoom)
  - Option B: Click task node → opens overlay/modal with workflow DAG
  - Option C: Split view — Task DAG left, Workflow DAG right (click to sync)
  - Option D: Nested nodes — task node expands inline to show sub-DAG (ComfyUI group)
  - Which is best for our use case? Consider: "Grandma" UX, screen real estate, back-navigation

- **ReactFlow multi-level support:**
  - Can ReactFlow handle two DAG instances? (yes, multiple `<ReactFlow>` components)
  - Shared vs separate state management
  - Animated transitions between levels

Reference examples: ComfyUI nested groups, n8n sub-workflows, Figma component drill-down, Notion nested pages, Miro zoom-to-frame.

### Deliverable 3: Task Management UX
**Question:** How should task editing, provenance tracking, and fullscreen views work in MCC?

Research needed:
- **Task editing:**
  - Inline editing (click field → edit) vs modal editor vs side panel
  - Which fields are editable? (title, description, priority, tags, assigned_to)
  - Drag-to-reorder priority in task list
  - Bulk operations (select many → change status/priority)

- **Task provenance (chat linkage):**
  - Backend: Add `source_chat_id`, `source_chat_type` fields to TaskBoard
  - Frontend: "Created from Chat: {chat_title}" link on task detail
  - Reverse lookup: navigate from task → originating chat message
  - Search tasks by chat ID

- **Fullscreen result viewer:**
  - Expandable from both: task card (right panel) and task DAG node
  - Content: code diff, verifier feedback, subtask timeline, artifacts
  - Tabs: Code | Diff | Timeline | Artifacts
  - Copy/apply/reject buttons (already exist in compact view)

- **Filtering and sorting:**
  - By source (Dragon/Opus/Cursor/manual)
  - By agent (who executed it)
  - By date range
  - By status
  - Search by keyword

### Deliverable 4: Context Pipeline — Files, Memory, Digest
**Question:** How should files, context, and memory flow through the MCC system?

Research needed:
- **File attachment in VETKA chat:**
  - Current: chat messages are text-only in group chat
  - Desired: attach files to task (like GitHub issue attachments)
  - How do LLM agents receive file context? (inject into prompt vs tool call)
  - Current: Scout scans files → Architect gets summary → Coder uses FC tools to read
  - Gap: User can't manually attach specific files to a task

- **Context compression for agents:**
  - Current: ELISION compression (40-60% token savings) via `vetka_get_conversation_context`
  - Current: CAM (Context-Aware Memory) with surprise detection
  - Current: Engram user preferences
  - Gap: Pipeline agents don't use ELISION/CAM — they get raw context from Scout
  - Should pipeline agents get compressed context? Tradeoff: quality vs cost

- **Mycelium memory (learning from past runs):**
  - Current: STM (Short-Term Memory) — volatile, dies on restart
  - Current: Task Board persists stats — can compute team performance
  - Missing: Long-term memory of "what worked" per task type
  - Idea: Qdrant collection for pipeline execution history (searchable by task type, similar code patterns)
  - Idea: feedback_loop — when user marks "applied", store the successful pipeline trace as exemplar

- **Session init for user:**
  - `vetka_session_init` is MCP-only (agent tool)
  - User doesn't see session context in UI
  - Desired: Show project digest, phase info, recent activity in MCC header or dedicated panel
  - Idea: "Digest" tab in DevPanel with auto-refreshing project state

- **Multi-agent task visibility:**
  - User wants to see Opus/Codex/Dragon task distribution
  - Current: TaskBoard has `assigned_to` and `agent_type` fields
  - Missing: Visual representation (who's working on what, currently)
  - Idea: Agent activity bar (already exists: AgentStatusBar) + live task assignment view

### Deliverable 5: Git Integration + BMAD Method
**Question:** How should git integration and BMAD workflow method connect to MCC?

Research needed:
- **Current BMAD template:**
  - `data/templates/bmad_workflow.json` — 11 nodes, 13 edges (1 feedback loop)
  - Nodes: scout → architect → researcher → coder → measure → adjust → approval_gate → deploy
  - DAGExecutor in `src/orchestration/dag_executor.py` can execute this
  - Gap: No git integration node (commit, push, PR)

- **Git workflow in pipeline:**
  - Current: `vetka_git_commit` MCP tool — manual commit by Opus/Cursor
  - Pipeline agents can't commit (no git tool in FC loop)
  - Should coder auto-commit? Or should there be a "deploy" node that handles git?
  - Playground promote = git cherry-pick from worktree to main

- **File specification for tasks:**
  - Current: User writes "fix useStore.ts" → Scout finds it
  - Desired: Explicit file attachment ("work on THESE files")
  - Could be: `target_files` field on task (Scout reads these first)
  - Could be: Pinned files via `vetka_get_pinned_files` injected into pipeline

- **BMAD loop visibility:**
  - The feedback edge (measure → adjust → coder retry) is the "BMAD loop"
  - User should see: how many BMAD iterations happened, what changed per iteration
  - Visual: Loop counter badge on feedback edge in DAG

### Deliverable 6: Wireframes
Provide wireframe descriptions (ASCII or structured) for:

1. **Stats Dashboard (fullscreen):**
   - Top: summary cards (runs, success%, tokens, cost estimate)
   - Middle: time-series chart (line chart: success rate over time, area chart: token usage over time)
   - Bottom-left: Per-agent cards with bars (current implementation, enhanced)
   - Bottom-right: Team comparison matrix

2. **Dual DAG view:**
   - Default: Task DAG (roadmap view) — full width
   - Click task node: Workflow DAG appears (how?)
   - Show both levels simultaneously or drill-down?
   - Mini-map for navigation

3. **Fullscreen Result Viewer:**
   - Tabs: Code | Diff | Timeline | Artifacts
   - Code tab: syntax-highlighted code output per subtask
   - Diff tab: unified diff with green/red highlighting
   - Timeline tab: Gantt chart of agent activity (Scout → ... → Verifier)
   - Artifacts tab: list of generated files with preview

4. **Task Editor:**
   - Inline or modal?
   - Fields layout
   - Action buttons (save, cancel, delete, dispatch)

## Technical Constraints
- Frontend: React + TypeScript, Recharts already available, ReactFlow for DAG
- Backend: Python FastAPI, SocketIO for real-time
- Data: JSON files (task_board.json), Qdrant for vector search
- Style: Nolan monochrome (dark, #111/#222/#e0e0e0, minimal color, Itten accents)
- Must be "Grandma-friendly" — clear, obvious, no jargon in UI

## Output Format
Please provide:
1. Structured recommendations for each deliverable (numbered, with pros/cons)
2. Wireframe descriptions
3. Suggested implementation order (what delivers most value first)
4. Estimated complexity per deliverable (simple/moderate/complex)
5. Any reference implementations or libraries to consider
