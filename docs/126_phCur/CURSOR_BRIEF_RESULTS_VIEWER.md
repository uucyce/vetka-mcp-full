# CURSOR BRIEF: Pipeline Results Viewer in DevPanel

## Problem
Dragon generates code (stored in pipeline_tasks.json → subtasks[].result), but there's no way to see it in UI. User can't review or apply generated code.

## Goal
Click on a done task in Board tab → see generated code → copy/apply.

## Data Source
File: `data/pipeline_tasks.json`
Structure: `{ task_id: { subtasks: [{ result: "```ts\n...\n```", status: "done", description: "..." }] } }`

Each task in task_board.json has `pipeline_task_id` linking to pipeline_tasks.json.

## What Needs to Change

### 1. Backend: New endpoint
`GET /api/debug/pipeline-results/{task_id}` → returns subtask results

```python
@router.get("/pipeline-results/{task_id}")
async def get_pipeline_results(task_id: str):
    tasks = json.loads(TASKS_FILE.read_text())
    task = tasks.get(task_id)
    if not task:
        return {"error": "not found"}
    return {
        "task_id": task_id,
        "status": task.get("status"),
        "subtasks": [
            {
                "description": s.get("description", "")[:100],
                "status": s.get("status"),
                "result": s.get("result"),
                "marker": s.get("marker")
            }
            for s in task.get("subtasks", [])
        ]
    }
```

### 2. Frontend: TaskCard expand
When a done task with `pipeline_task_id` is clicked → fetch results → show code blocks.

- Expand section below TaskCard
- Each subtask: description + code in `<pre>` with monospace
- "Copy" button per subtask result
- Nolan style: dark bg (#181818), light monospace text

### 3. DevPanel wiring
- `expandedTaskId` state
- On TaskCard click: if done + has pipeline_task_id → fetch → expand
- Collapse on second click

## Markers
- MARKER_127.0A: Backend endpoint
- MARKER_127.0B: TaskCard expanded view
- MARKER_127.0C: DevPanel expand logic

## Style
- Same Nolan monochrome
- Code blocks: `#181818` bg, `#d0d0d0` text, monospace
- Copy button: small, top-right of code block

## Estimated Effort
2-3 hours, low-medium complexity.
