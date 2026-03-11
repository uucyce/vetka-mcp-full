# Codex A — Backend API + Generic TaskBoard

> **Agent:** Codex A (fresh session)
> **Territory:** Backend Python only (src/api/routes/, src/orchestration/)
> **Branch:** `codex-a/175-backend-api`
> **Phase:** 175.0A-C + 175.7
> **Estimated:** 6-8 hours total

---

## YOUR MISSION

Build the missing backend infrastructure that unblocks MYCELIUM.app standalone.
You own ALL backend API routes and TaskBoard logic. No frontend work.

---

## CONTEXT DOCUMENTS (READ FIRST)

1. **Architecture:** `docs/175_MCC_APP/RECON_175_UNIFIED.md` — Full recon of MCC dependencies
2. **Endpoint specs:** `docs/175_MCC_APP/CODEX_BRIEF_175_MCC_ENDPOINTS.md` — Original brief for 3 endpoints
3. **Coordination:** `docs/175_MCC_APP/AGENTS_COORDINATION_175.md` — Territory map, sync protocol
4. **Analytics backend:** `docs/152_ph/PHASE_152_ROADMAP.md` — Analytics engine architecture

---

## ROADMAP (execute top-to-bottom)

### Step 1: 3 Missing MCC Endpoints (Priority P0 — blocks everything)

**File:** `src/api/routes/mcc_routes.py`

#### 1A. PATCH /api/mcc/tasks/{task_id}
- TaskEditPopup.tsx sends: `{ preset, phase_type, description, title, priority }`
- Use `TaskBoard().update_task()` — check if method exists in `src/orchestration/task_board.py`
- If `update_task()` doesn't exist, add it (see Step 2)
- Whitelist fields: `title, description, preset, phase_type, priority, tags`
- Return updated task object

#### 1B. POST /api/mcc/tasks/{task_id}/feedback
- RedoFeedbackInput.tsx sends: `{ feedback, action }` where action = "redo"|"approve"|"reject"
- On redo: set status="pending", result_status=0.5
- On approve: result_status=1.0
- On reject: result_status=0.0
- `result_status` is already in ADDABLE_FIELDS (Phase 151.12)
- `feedback` field may need to be added to ADDABLE_FIELDS

**File:** `src/api/routes/chat_routes.py`

#### 1C. POST /api/chat/quick
- MiniChat.tsx sends: `{ message, context }` for inline quick chat
- Use lightweight model (grok-fast-4.1 via Polza) for single-turn response
- Max 500 tokens response
- Fallback if model unavailable: return `{ reply: "Backend model unavailable", status: "fallback" }`

**Reference existing patterns:** Look at `src/api/routes/chat_routes.py` for existing chat endpoints.
Look at how `group_message_handler.py` dispatches to models.

### Step 2: TaskBoard Extensions

**File:** `src/orchestration/task_board.py`

- Verify `update_task()` method exists with field whitelisting
- Add `feedback` to ADDABLE_FIELDS if not present
- Add `result_status` update capability (used by feedback endpoint)
- Test JSON persistence after updates

### Step 3: Generic TaskBoard REST API (Phase 175.7)

**File:** `src/api/routes/taskboard_routes.py` (NEW)

Create adapter-based REST API for multi-client support:

```python
router = APIRouter(prefix="/api/taskboard", tags=["taskboard"])

@router.post("/create")     # Create task (any client)
@router.get("/list")        # List tasks (with filters)
@router.post("/dispatch")   # Dispatch to pipeline
@router.patch("/{task_id}") # Update task
@router.get("/{task_id}")   # Get single task
```

Each endpoint accepts optional `adapter` field: "claude"|"cursor"|"vscode"|"opencode"

### Step 4: Adapter Layer

**File:** `src/orchestration/taskboard_adapters.py` (NEW)

```python
class BaseAdapter:
    async def create_task(self, data): ...
    async def dispatch_task(self, task_id): ...

class ClaudeMCPAdapter(BaseAdapter):
    """Uses existing TaskBoard directly."""

class CursorAdapter(BaseAdapter):
    """Translates to Cursor SSE format."""

class GenericRESTAdapter(BaseAdapter):
    """Default — direct TaskBoard access."""
```

Start with ClaudeMCPAdapter (wraps existing task_board.py) and GenericRESTAdapter.
Cursor/VSCode adapters can be stubs for now.

### Step 5: Register Routes in main.py

**File:** `main.py`

Add import and include_router for `taskboard_routes`.
Pattern: follow how `mcc_routes` is already registered.

---

## TESTS (write BEFORE implementation)

**File:** `tests/test_175_backend_api.py` (NEW)

```python
# T1: PATCH /api/mcc/tasks/{id} — updates task fields
# T2: PATCH /api/mcc/tasks/{id} — rejects unknown fields
# T3: PATCH /api/mcc/tasks/{id} — 404 for nonexistent task
# T4: POST /api/mcc/tasks/{id}/feedback — redo sets status=pending
# T5: POST /api/mcc/tasks/{id}/feedback — approve sets result_status=1.0
# T6: POST /api/mcc/tasks/{id}/feedback — reject sets result_status=0.0
# T7: POST /api/chat/quick — returns reply from model
# T8: POST /api/chat/quick — empty message returns 400
# T9: POST /api/chat/quick — model failure returns fallback
# T10: TaskBoard.update_task() persists changes to JSON
```

**File:** `tests/test_175_taskboard_adapters.py` (NEW)

```python
# T11: GenericRESTAdapter.create_task() creates task in board
# T12: GenericRESTAdapter.dispatch_task() dispatches correctly
# T13: ClaudeMCPAdapter wraps existing TaskBoard
# T14: POST /api/taskboard/create creates task
# T15: GET /api/taskboard/list returns all tasks
# T16: PATCH /api/taskboard/{id} updates task
# T17: Adapter selection based on request field
```

---

## SELF-CORRECTION ALGORITHM

```
1. Read mcc_routes.py to understand existing endpoint patterns
2. Read task_board.py to understand TaskBoard API
3. Read chat_routes.py to understand chat patterns
4. Write test_175_backend_api.py (17 tests)
5. Run: python -m pytest tests/test_175_backend_api.py -v
   → All should FAIL (endpoints don't exist yet)
6. Implement endpoints one by one
7. After each: python -m pytest tests/test_175_backend_api.py -v
   → Fix until green
8. Run full suite: python -m pytest tests/ -v --ignore=tests/phase170 --ignore=tests/phase168
   → Must not break existing tests
9. Write completion status to docs/175_MCC_APP/STATUS_CODEX_A.md
```

---

## FILES YOU OWN (only edit these)

| File | Action |
|------|--------|
| `src/api/routes/mcc_routes.py` | ADD 2 endpoints (task PATCH + feedback) |
| `src/api/routes/chat_routes.py` | ADD 1 endpoint (/chat/quick) |
| `src/api/routes/taskboard_routes.py` | NEW file (generic REST) |
| `src/orchestration/task_board.py` | ADD feedback to ADDABLE_FIELDS + update_task validation |
| `src/orchestration/taskboard_adapters.py` | NEW file (adapter layer) |
| `main.py` | ADD taskboard_routes import + include_router |
| `tests/test_175_backend_api.py` | NEW test file |
| `tests/test_175_taskboard_adapters.py` | NEW test file |
| `docs/175_MCC_APP/STATUS_CODEX_A.md` | Write completion status here |

## FILES YOU MUST NOT TOUCH

- ANY file under `client/` (frontend is Codex B + Opus territory)
- `src/orchestration/agent_pipeline.py` (Opus territory)
- `src/orchestration/pipeline_analytics.py` (Codex B reads, Opus owns)
- ANY file under `src-tauri-mcc/` (Opus territory)

---

## VERIFICATION COMMANDS

```bash
# Your tests only
python -m pytest tests/test_175_backend_api.py tests/test_175_taskboard_adapters.py -v

# Smoke test endpoints
curl -X PATCH localhost:5001/api/mcc/tasks/TEST -d '{"preset":"dragon_gold"}' -H 'Content-Type: application/json'
curl -X POST localhost:5001/api/mcc/tasks/TEST/feedback -d '{"feedback":"fix","action":"redo"}' -H 'Content-Type: application/json'
curl -X POST localhost:5001/api/chat/quick -d '{"message":"hello"}' -H 'Content-Type: application/json'

# Full regression (must pass)
python -m pytest tests/test_reflex_live.py tests/test_phase152_wave1.py -v
```

---

## SUCCESS CRITERIA

1. All 17 tests GREEN
2. 3 MCC endpoints respond correctly
3. Generic TaskBoard API works with at least 2 adapters
4. Zero regression in existing test suite
5. STATUS_CODEX_A.md written with results
