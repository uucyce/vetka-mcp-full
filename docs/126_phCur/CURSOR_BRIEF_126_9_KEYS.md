# CURSOR BRIEF: Phase 126.9 — Key Selection → Pipeline Launch

## Goal
When user clicks an API key row in BalancesPanel, that key becomes the active key for the next pipeline dispatch.

## Current State
- BalancesPanel.tsx already shows all keys with balance/usage
- MARKER_126.9 TODO is already placed in BalancesPanel.tsx
- Pipeline dispatch goes through `POST /api/debug/task-board/dispatch`
- `AgentPipeline._apply_preset()` sets `self.provider_override` from preset config
- `call_model_v2()` uses `UnifiedKeyManager.get_key_with_rotation()` to pick a key

## What Needs to Change

### 1. Frontend: BalancesPanel.tsx (MARKER_126.9)
- Add `onClick` handler on each key row
- Selected key gets visual highlight (brighter border, subtle glow)
- Store selection in zustand: `useStore.getState().setSelectedKey({ provider, key_masked })`
- Show selected key badge somewhere visible (e.g. in dispatch button area)

### 2. Frontend: useStore.ts
- Add state: `selectedKey: { provider: string, key_masked: string } | null`
- Add action: `setSelectedKey(key)` and `clearSelectedKey()`

### 3. Frontend: DevPanel.tsx
- When dispatching, include `selected_key` in POST body:
  ```ts
  body: JSON.stringify({
    task_id: taskId,
    selected_key: useStore.getState().selectedKey
  })
  ```

### 4. Backend: debug_routes.py (dispatch endpoint)
- Read `selected_key` from request body
- Pass to `board.dispatch_task(task_id, selected_key=selected_key)`

### 5. Backend: task_board.py (dispatch_task)
- Accept `selected_key` param
- Pass to AgentPipeline: `pipeline.selected_key = selected_key`

### 6. Backend: agent_pipeline.py
- In `_apply_preset()` or at LLM call time:
  - If `self.selected_key` is set, tell UnifiedKeyManager to use that specific key
  - `km.set_preferred_key(provider, key_masked)` — new method

### 7. Backend: unified_key_manager.py
- Add `set_preferred_key(provider, key_masked)` — sets temporary preference
- In `get_key_with_rotation()`: if preferred key is set for this provider, return it first
- Auto-clear preference after pipeline completes (or after N calls)

## Markers to Use
- MARKER_126.9A: BalancesPanel key click handler
- MARKER_126.9B: useStore selectedKey state
- MARKER_126.9C: DevPanel dispatch with selected_key
- MARKER_126.9D: debug_routes passing selected_key
- MARKER_126.9E: task_board + agent_pipeline wiring
- MARKER_126.9F: UnifiedKeyManager preferred key

## Style
- Nolan monochrome: selected key row gets `border-left: 2px solid #e0e0e0`
- No emoji, no color — just brightness change
- Selected indicator: small `▸` arrow or brighter text

## Tests Needed
- test_phase126_9_key_selection.py (12+ tests)
- Classes: TestKeySelectionUI, TestDispatchWithKey, TestKeyManagerPreference

## Dependencies
- BalancesPanel.tsx (Cursor built it)
- useStore.ts (existing)
- unified_key_manager.py (existing)
- agent_pipeline.py (existing)

## Estimated Effort
3-4 hours, medium complexity.
