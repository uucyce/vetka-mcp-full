# MYCELIUM MCP Tool Reference

> Auto-generated from MCP schema definitions on 2026-03-18 06:20 UTC
> Generator: `scripts/generate_mcp_docs.py` (MARKER_191.5)
> Total tools: **24**

## Table of Contents

- [`mycelium_approve_artifact`](#mycelium-approve-artifact)
- [`mycelium_call_model`](#mycelium-call-model)
- [`mycelium_devpanel_stream`](#mycelium-devpanel-stream)
- [`mycelium_execute_workflow`](#mycelium-execute-workflow)
- [`mycelium_health`](#mycelium-health)
- [`mycelium_heartbeat_status`](#mycelium-heartbeat-status)
- [`mycelium_heartbeat_tick`](#mycelium-heartbeat-tick)
- [`mycelium_implement`](#mycelium-implement)
- [`mycelium_list_artifacts`](#mycelium-list-artifacts)
- [`mycelium_pipeline`](#mycelium-pipeline)
- [`mycelium_playground_create`](#mycelium-playground-create)
- [`mycelium_playground_destroy`](#mycelium-playground-destroy)
- [`mycelium_playground_diff`](#mycelium-playground-diff)
- [`mycelium_playground_list`](#mycelium-playground-list)
- [`mycelium_reject_artifact`](#mycelium-reject-artifact)
- [`mycelium_research`](#mycelium-research)
- [`mycelium_review`](#mycelium-review)
- [`mycelium_task_board`](#mycelium-task-board)
- [`mycelium_task_dispatch`](#mycelium-task-dispatch)
- [`mycelium_task_import`](#mycelium-task-import)
- [`mycelium_track_done`](#mycelium-track-done)
- [`mycelium_track_started`](#mycelium-track-started)
- [`mycelium_tracker_status`](#mycelium-tracker-status)
- [`mycelium_workflow_status`](#mycelium-workflow-status)

---

## `mycelium_approve_artifact`

Approve an artifact for deployment/integration.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `artifact_id` | `string` | Yes | — | Artifact ID |
| `reason` | `string` | No | — | — |

---

## `mycelium_call_model`

Call any LLM model through MYCELIUM async infrastructure (Grok, GPT, Claude, Gemini, Ollama). Native async — never blocks. Supports function calling for compatible models.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | `string` | Yes | — | Model name (e.g., grok-4, gpt-4o, claude-sonnet) |
| `messages` | `array[any]` | Yes | — | Chat messages [{role, content}] |
| `temperature` | `number` | No | — | Temperature 0-2 |
| `max_tokens` | `number` | No | — | Max response tokens |
| `model_source` | `string` | No | — | Provider: polza, openai, anthropic, google, ollama |
| `inject_context` | `object` | No | — | Context injection config |
| `tools` | `array[any]` | No | — | Function calling tools |

---

## `mycelium_devpanel_stream`

Get DevPanel WebSocket broadcaster info: connected clients, port, status.

*No parameters*

---

## `mycelium_execute_workflow`

Execute full VETKA workflow. Types: pm_to_qa, pm_only, dev_qa.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `request` | `string` | Yes | — | Workflow request |
| `workflow_type` | `string` | No | — | pm_to_qa, pm_only, dev_qa |
| `workflow_family` | `string` | No | — | Optional MCC workflow family for contract-aware REFLEX preflight |
| `include_eval` | `boolean` | No | — | — |
| `timeout` | `number` | No | — | — |

---

## `mycelium_health`

MYCELIUM health check: uptime, active pipelines, WS clients, VETKA connectivity.

*No parameters*

---

## `mycelium_heartbeat_status`

Get Heartbeat Engine status: last tick, total ticks, tasks dispatched/completed/failed.

*No parameters*

---

## `mycelium_heartbeat_tick`

Execute one heartbeat tick: read new messages from group chat, parse task triggers (@dragon, /task, /fix, /build, /research), dispatch via pipeline.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `group_id` | `string` | No | — | Group chat ID to monitor |
| `dry_run` | `boolean` | No | — | Preview tasks without executing |

---

## `mycelium_implement`

Plan implementation for a task (use workflow for execution).

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task` | `string` | Yes | — | Task to plan |
| `dry_run` | `boolean` | No | — | — |

---

## `mycelium_list_artifacts`

List artifacts by status (pending, approved, rejected, all).

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | `string` | No | — | Filter: pending, approved, rejected, all |
| `limit` | `number` | No | — | — |

---

## `mycelium_pipeline`

Mycelium agent pipeline for fractal task execution. Auto-triggers researcher on unclear parts. Phases: research (explore), fix (debug), build (implement), test (verify). Progress streams to chat + DevPanel WebSocket in real-time. NON-BLOCKING: returns immediately, pipeline runs in background.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task` | `string` | Yes | — | Task description |
| `phase_type` | `string` | No | — | Pipeline phase: research, fix, build, test |
| `preset` | `string` | No | — | Team preset: dragon_bronze, dragon_silver, dragon_gold |
| `provider` | `string` | No | — | LLM provider override |
| `chat_id` | `string` | No | — | Chat ID for progress streaming |
| `auto_write` | `boolean` | No | — | Auto-write files (false=staging mode) |
| `playground_id` | `string` | No | — | Playground ID for sandboxed execution (files scoped to worktree) |

---

## `mycelium_playground_create`

Create an isolated playground (git worktree) for safe agent experiments. Pipeline writes go to the worktree, not main codebase. Returns playground_id to pass to mycelium_pipeline.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task` | `string` | No | — | What the agent will work on |
| `preset` | `string` | No | — | Team preset (default: dragon_silver) |
| `auto_write` | `boolean` | No | — | Allow file writes in playground (default: true) |

---

## `mycelium_playground_destroy`

Destroy a playground and clean up its git worktree.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `playground_id` | `string` | Yes | — | Playground ID to destroy |

---

## `mycelium_playground_diff`

Get git diff of changes made in a playground vs source branch.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `playground_id` | `string` | Yes | — | Playground ID |

---

## `mycelium_playground_list`

List active playground instances with status, age, and pipeline run count.

*No parameters*

---

## `mycelium_reject_artifact`

Reject an artifact with feedback.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `artifact_id` | `string` | Yes | — | Artifact ID |
| `feedback` | `string` | No | — | Rejection feedback |

---

## `mycelium_research`

Research a topic: semantic search → read files → summarize.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `topic` | `string` | Yes | — | Research topic |
| `depth` | `string` | No | — | quick, medium, deep |

---

## `mycelium_review`

Review a file and suggest improvements.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | `string` | Yes | — | File to review |

---

## `mycelium_task_board`

Task Board CRUD (add/list/get/update/remove/summary/claim/complete/active_agents/merge_request/promote_to_main). Priority queue for pipeline dispatch.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | `string` | Yes | — | Operation to perform Values: `add`, `list`, `get`, `update`, `remove`, `summary`, `claim`, `complete`, `active_agents`, `merge_request`, `promote_to_main` |
| `title` | `string` | No | — | Task title (required for add) |
| `description` | `string` | No | — | Detailed task description — free text for context, problem statement, approach |
| `profile` | `string` | No | — | Task intake profile with protocol defaults Values: `p6` |
| `priority` | `number` | No | — | 1=critical, 2=high, 3=medium, 4=low, 5=someday |
| `phase_type` | `string` | No | — | Task type Values: `build`, `fix`, `research`, `test` |
| `complexity` | `string` | No | — | Estimated complexity Values: `low`, `medium`, `high` |
| `preset` | `string` | No | — | Pipeline preset override |
| `tags` | `array[string]` | No | — | Tags for categorization |
| `dependencies` | `array[string]` | No | — | Task IDs that must complete first |
| `project_id` | `string` | No | — | Logical project ID. For add: assigns project. For list: filters tasks by project (shows matching + unassigned). |
| `project_lane` | `string` | No | — | Specific multitask lane/MCC tab identifier |
| `architecture_docs` | `array[string]` | No | — | Architecture docs linked to the task |
| `recon_docs` | `array[string]` | No | — | Recon docs linked to the task |
| `allowed_paths` | `array[string]` | No | — | Target files/directories this task should modify. Also serves as ownership guard — agent should not touch files outside this list. Example: ['src/orchestration/task_board.py', 'src/mcp/tools/'] |
| `completion_contract` | `array[string]` | No | — | Acceptance criteria checklist. Each item = one verifiable condition the agent must satisfy. Example: ['API returns 200 on valid input', 'unit tests pass', 'no console errors in browser'] |
| `implementation_hints` | `string` | No | — | Algorithm hints, approach notes, or technical guidance for the implementing agent. Free text. Example: 'Use re.search with word boundary, not substring match. Check _commit_matches_task for the pattern.' |
| `closure_tests` | `array[string]` | No | — | Shell commands required for closure proof. Example: ['python -m pytest tests/test_task_board.py -v', 'python -c "import ast; ast.parse(open(f).read())"'] |
| `closure_files` | `array[string]` | No | — | Files allowed for scoped auto-commit at task completion. If set, only these files are staged. |
| `assigned_to` | `string` | No | — | Agent name: opus, cursor, dragon, grok |
| `agent_type` | `string` | No | — | Agent type: claude_code, cursor, mycelium, grok, human |
| `task_id` | `string` | No | — | Task ID (required for get/update/remove/claim/complete) |
| `status` | `string` | No | — | — Values: `pending`, `queued`, `claimed`, `running`, `done`, `done_worktree`, `done_main`, `failed`, `cancelled` |
| `filter_status` | `string` | No | — | Filter by status (optional for list) |
| `limit` | `number` | No | — | Max tasks to return in list (default: 40, max: 100) |
| `force_no_docs` | `boolean` | No | — | Bypass doc requirement gate. Use only when truly no relevant docs exist. |
| `commit_hash` | `string` | No | — | Git commit hash (for complete) |
| `commit_message` | `string` | No | — | Commit message (for complete) |
| `branch` | `string` | No | — | Git branch name (for complete). If on worktree branch, status=done_worktree. If omitted, auto-detects. |
| `worktree_path` | `string` | No | — | Absolute path to worktree root. Required for auto-commit when agent runs in a worktree. |

---

## `mycelium_task_dispatch`

Dispatch tasks from Task Board to pipeline. If task_id given, dispatches that task. Otherwise picks highest-priority pending task.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | `string` | No | — | Specific task ID to dispatch |
| `chat_id` | `string` | No | — | Chat ID for progress |

---

## `mycelium_task_import`

Import tasks from a todo text file into the Task Board. Auto-detects priority and phase_type from content.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | `string` | Yes | — | Path to todo file |
| `source_tag` | `string` | No | — | Tag for imported tasks |

---

## `mycelium_track_done`

Mark a task as completed. Updates project digest + tracker. Use for any agent: dragon, cursor, opus, titan.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `marker` | `string` | Yes | — | Task marker (e.g. C33E, MARKER_133.FIX1) |
| `description` | `string` | Yes | — | What was done |
| `source` | `string` | No | — | Who did it: cursor, dragon, opus, titan |
| `files_changed` | `array[any]` | No | — | List of changed file paths |

---

## `mycelium_track_started`

Mark a task as started. Any agent can call this.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | `string` | Yes | — | Task ID or marker |
| `title` | `string` | Yes | — | Task title |
| `source` | `string` | No | — | Who started: cursor, dragon, opus |

---

## `mycelium_tracker_status`

Get task tracker status: in-progress tasks, completed count, last completed, digest headline.

*No parameters*

---

## `mycelium_workflow_status`

Get status of a workflow execution by workflow ID.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `workflow_id` | `string` | Yes | — | Workflow ID |

---
