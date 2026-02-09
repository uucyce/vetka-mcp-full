# CURSOR BRIEF: Result Lifecycle — Applied/Rejected Status

## Problem
After pipeline generates code, there's no way to mark whether it was:
- Applied (code was useful, integrated into project)
- Rejected (code was wrong, discarded)
- Needs Rework (partial — send back to pipeline)

External clients (OpenCode, Cursor) need this to close the loop.

## Goal
Add lifecycle status to pipeline results: `generated → reviewed → applied | rejected | rework`

## What Needs to Change

### 1. Backend: Status Tracking
Add `result_status` field to task_board.json tasks:

```python
# In task_board.py or debug_routes.py
@router.patch("/pipeline-results/{task_id}/status")
async def update_result_status(task_id: str, data: Dict):
    """Mark pipeline result as applied/rejected/rework."""
    status = data["status"]  # "applied" | "rejected" | "rework"
    reason = data.get("reason", "")

    board = get_task_board()
    board.update_task(task_id,
        result_status=status,
        result_reviewed_at=datetime.now().isoformat(),
        result_review_reason=reason
    )
    return {"success": True}
```

### 2. Frontend: Status Badge on TaskCard
For done tasks with `result_status`:
- `applied` → green checkmark badge
- `rejected` → red X badge
- `rework` → yellow refresh badge
- No status → gray "unreviewed" badge

### 3. Frontend: Action Buttons in Results View
When results are expanded (from C1 Results Viewer):
- "Mark Applied" button (green accent)
- "Reject" button (red accent)
- "Rework" button (yellow accent) — re-dispatches task
- Optional: reason text input

### 4. TaskBoard Summary Update
Board summary should show:
- Total applied / rejected / unreviewed counts
- "Review needed" badge count

## Markers
- MARKER_128.3A: Backend status endpoint
- MARKER_128.3B: TaskCard status badge
- MARKER_128.3C: Action buttons in expand view
- MARKER_128.3D: Board summary review counts

## Style
- Applied: muted green `#2d5a2d` (Nolan — never bright)
- Rejected: muted red `#5a2d2d`
- Rework: muted amber `#5a4a2d`
- Unreviewed: gray `#444`

## Data Model Addition
```json
// In task_board.json task entry:
{
  "result_status": "applied",        // NEW: applied | rejected | rework | null
  "result_reviewed_at": "2026-...",  // NEW: ISO timestamp
  "result_review_reason": "Good code, integrated" // NEW: optional
}
```

## Estimated Effort
2-3 hours, low-medium complexity.
Depends on: C1 (Results Viewer) being done first.
