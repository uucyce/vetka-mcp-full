# Codex Brief: Phase 175 — Missing API Endpoints + MiniBalance Store

> **Assigned to:** Codex
> **Priority:** HIGH (blocks MCC standalone testing)
> **Estimated:** 4 hours total
> **Branch:** `codex/175-mcc-endpoints`

---

## Task 1: PATCH /api/mcc/tasks/{task_id} (1.5h)

### Context
`TaskEditPopup.tsx` (Phase 154.8) allows editing task team preset, phase type, and description.
Currently sends PATCH to `/api/mcc/tasks/{task_id}` — endpoint does NOT exist.

### Implementation

**File:** `src/api/routes/mcc_routes.py`

Add endpoint:
```python
@router.patch("/tasks/{task_id}")
async def update_mcc_task(task_id: str, data: dict = Body(...)):
    """Update task fields: title, description, preset, phase_type, priority."""
    board = TaskBoard()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")

    allowed = {"title", "description", "preset", "phase_type", "priority", "tags"}
    update_data = {k: v for k, v in data.items() if k in allowed}

    result = board.update_task(task_id, **update_data)
    return {"status": "ok", "task": result}
```

### Verify
- `TaskBoard.update_task()` already exists (check `src/orchestration/task_board.py`)
- If not, add it using `board.update()` pattern from existing code
- Test: `curl -X PATCH localhost:5001/api/mcc/tasks/TEST_ID -H 'Content-Type: application/json' -d '{"preset": "dragon_gold"}'`

---

## Task 2: POST /api/mcc/tasks/{task_id}/feedback (1h)

### Context
`RedoFeedbackInput.tsx` (Phase 154.10) submits redo feedback for completed tasks.
Sends POST to `/api/mcc/tasks/{task_id}/feedback` — endpoint does NOT exist.

### Implementation

**File:** `src/api/routes/mcc_routes.py`

```python
@router.post("/tasks/{task_id}/feedback")
async def submit_task_feedback(task_id: str, data: dict = Body(...)):
    """Submit user feedback (redo request) for a completed task."""
    board = TaskBoard()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")

    feedback_text = data.get("feedback", "")
    action = data.get("action", "redo")  # redo | approve | reject

    # Update task with feedback
    board.update_task(task_id,
        status="pending" if action == "redo" else task.get("status"),
        result_status=0.5 if action == "redo" else (1.0 if action == "approve" else 0.0),
        feedback=feedback_text
    )

    return {"status": "ok", "action": action, "task_id": task_id}
```

### Integration
- `result_status` field already in ADDABLE_FIELDS (Phase 151.12)
- `feedback` field may need to be added to ADDABLE_FIELDS in `task_board.py`

---

## Task 3: POST /api/chat/quick (1h)

### Context
`MiniChat.tsx` (Phase 154.12) sends quick chat messages for inline task guidance.
Sends POST to `/api/chat/quick` — endpoint does NOT exist.

### Implementation

**File:** `src/api/routes/chat_routes.py` (or `mcc_routes.py`)

```python
@router.post("/chat/quick")
async def quick_chat(data: dict = Body(...)):
    """Quick chat endpoint for MiniChat — single-turn LLM response."""
    message = data.get("message", "")
    context = data.get("context", {})

    if not message.strip():
        raise HTTPException(400, "Empty message")

    # Use lightweight model for quick responses
    from src.orchestration.model_router import ModelRouter
    router = ModelRouter()

    response = await router.call_model(
        model="grok-fast-4.1",  # Fast, cheap
        messages=[
            {"role": "system", "content": f"You are MCC assistant. Context: {json.dumps(context)[:500]}"},
            {"role": "user", "content": message}
        ],
        max_tokens=500
    )

    return {
        "status": "ok",
        "reply": response.get("content", ""),
        "model": response.get("model", "unknown")
    }
```

### Note
- MiniChat has a local `buildMycoReply()` fallback — this endpoint enhances but doesn't replace it
- If ModelRouter is too heavy, use a simpler HTTP call to the Polza/OpenRouter API directly
- Alternative: wire into existing `group_message_handler.py` for @doctor-style responses

---

## Task 4: MiniBalance Store Extraction (0.5h)

### Context
`MiniBalance.tsx` imports from main `useStore` (the VETKA app store), not `useMCCStore`.
Reads: `selectedKey`, `setSelectedKey`, `favoriteKeys`, `toggleFavoriteKey`.

For standalone MCC, these need to be available without the full VETKA store.

### Implementation

**File:** `client/src/store/useMCCStore.ts`

Add these fields to useMCCStore:
```typescript
// API key management (extracted from useStore for standalone MCC)
selectedKey: string;
setSelectedKey: (key: string) => void;
favoriteKeys: string[];
toggleFavoriteKey: (key: string) => void;
```

**File:** `client/src/components/mcc/MiniBalance.tsx`

Change import:
```typescript
// Before:
import { useStore } from '../../store/useStore';
// After:
import { useMCCStore } from '../../store/useMCCStore';
```

### Note
- Initialize `selectedKey` from localStorage or `/api/models` response
- `favoriteKeys` persist to localStorage: `mcc_favorite_keys`

---

## Testing

```bash
# After implementing all 3 endpoints:
python -m pytest tests/test_mcc_routes.py -v

# Manual smoke test:
curl -X PATCH localhost:5001/api/mcc/tasks/test -d '{"preset":"dragon_gold"}' -H 'Content-Type: application/json'
curl -X POST localhost:5001/api/mcc/tasks/test/feedback -d '{"feedback":"needs fix","action":"redo"}' -H 'Content-Type: application/json'
curl -X POST localhost:5001/api/chat/quick -d '{"message":"hello","context":{}}' -H 'Content-Type: application/json'
```

---

## Files to Modify

| File | Action | Lines |
|------|--------|-------|
| `src/api/routes/mcc_routes.py` | ADD 2 endpoints | ~40 |
| `src/api/routes/chat_routes.py` | ADD 1 endpoint | ~25 |
| `src/orchestration/task_board.py` | ADD `feedback` to ADDABLE_FIELDS | ~2 |
| `client/src/store/useMCCStore.ts` | ADD key management fields | ~15 |
| `client/src/components/mcc/MiniBalance.tsx` | CHANGE store import | ~5 |
| `tests/test_175_mcc_endpoints.py` | NEW test file | ~60 |
| **Total** | | **~147 lines** |
