# CURSOR BRIEF: Results Viewer — View & Apply Pipeline Code

## Context
Phase 128.1 (Opus) added project awareness to coder prompt.
Pipeline now generates better code. Need UI to view and APPLY it.

Previous brief `CURSOR_BRIEF_RESULTS_VIEWER.md` covered basic viewing.
This brief extends it with **Apply** functionality.

## What Exists
- Backend: `GET /api/debug/pipeline-results/{task_id}` — DONE (MARKER_127.0A)
- TaskCard in DevPanel Board tab — shows task status
- Pipeline saves results to `pipeline_tasks.json`
- Each subtask has: `description`, `result` (code blocks), `marker`, `status`

## What Needs to Change

### 1. TaskCard Expand (Board Tab)
When user clicks a **done** task with `pipeline_task_id`:
- Fetch `GET /api/debug/pipeline-results/{task_id}`
- Show expandable section below card
- Each subtask: description + code in `<pre>` block
- **Copy** button (copies code to clipboard)
- **Apply** button (POST to new endpoint, writes file to disk)

### 2. Backend: Apply Endpoint
`POST /api/debug/pipeline-results/apply`

```python
@router.post("/pipeline-results/apply")
async def apply_pipeline_result(data: Dict):
    """Apply a subtask result — write code to disk."""
    task_id = data["task_id"]
    subtask_idx = data["subtask_idx"]
    # Read pipeline_tasks.json → find subtask → extract code blocks
    # Parse file path from code comment (// file: path/to/file.ext)
    # Write to disk
    return {"success": True, "files_written": [...]}
```

### 3. Activity Tab Enhancement
Show live `pipeline_activity` events with more detail:
- Role icon (Scout, Coder, Verifier)
- Tool calls (when coder reads files)
- Verifier verdict (passed/failed + confidence)

## Markers
- MARKER_128.2A: TaskCard expand with results
- MARKER_128.2B: Apply endpoint in debug_routes.py
- MARKER_128.2C: Copy/Apply buttons in expanded view

## Style
- Nolan monochrome (same as existing)
- Code: `#181818` bg, `#d0d0d0` text, `JetBrains Mono` or monospace
- Apply button: subtle green accent `#2d5a2d` (Nolan muted)
- Copy button: neutral `#333`

## File Hints
- `client/src/components/panels/TaskCard.tsx` — expand view
- `client/src/components/panels/DevPanel.tsx` — expand state
- `src/api/routes/debug_routes.py` — apply endpoint

## Estimated Effort
3-4 hours, medium complexity.
