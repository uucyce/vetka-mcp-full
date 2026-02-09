# CURSOR BRIEF: Doctor Triage Flow Fix

## Problem
@doctor command in group chat triggers triage but the flow is broken:
- Doctor dispatches tasks immediately instead of showing triage result in chat
- User doesn't see Doctor's analysis before task goes to pipeline
- No visual feedback of what Doctor decided (abstract/concrete, team suggestion)

## What Already Exists
- `src/api/handlers/group_message_handler.py` — `_doctor_triage()` method (MARKER_125.1C)
- `data/templates/pipeline_prompts.json` — `doctor` prompt
- Doctor LLM call → JSON result with `abstraction`, `reformulated_task`, `suggested_team`, etc.
- TaskBoard `hold` status for abstract tasks (MARKER_125.1B)
- `approve tb_xxx` command to dispatch held tasks

## What Needs Fixing

### 1. Doctor Response in Chat (MARKER_127.4A)
After Doctor LLM call, **show result in chat** before dispatching:
```
@doctor: Analyzing task...
@doctor: 📋 Abstraction: concrete
@doctor: 🔄 Reformulated: "Add toggleFavorite to useStore.ts with localStorage persistence"
@doctor: 🐉 Suggested: dragon_silver (build)
@doctor: ⚡ Dispatching to Task Board...
```
Currently it silently adds to board. User sees nothing.

**File:** `src/api/handlers/group_message_handler.py`
**Method:** `_doctor_triage()` — after LLM call, emit chat messages with analysis

### 2. Doctor Prompt Improvement (MARKER_127.4B)
Current doctor prompt is basic. Improve:
- Add examples of concrete vs abstract tasks
- Output `estimated_subtasks` count (helps architect)
- Output `key_files` list (helps scout)

**File:** `data/templates/pipeline_prompts.json` → `doctor.system`

### 3. Intake Reply Format (MARKER_127.4C)
After `@doctor <task>`, show quick-action buttons in chat:
```
1d — Run now (Dragon)
2d — Queue (Dragon)
h — Hold for review
```
Currently uses `_send_intake_prompt()` but only for @dragon.
Doctor should have its own post-triage prompt.

**File:** `src/api/handlers/group_message_handler.py`

## Style Guide
- Emit as `message_type: "system"` (gray text, not agent bubble)
- No emoji overload — one per line max
- Use existing `_emit_group_message()` pattern

## DO NOT
- Change pipeline execution logic
- Modify agent_pipeline.py
- Add new socket events (use existing group_message)
- Add new UI components (chat already renders system messages)

## Tests
Add 5+ tests in `tests/test_phase127_4_doctor_triage.py`:
- Doctor response appears in chat
- Concrete task auto-dispatches
- Abstract task goes to hold
- Reformulated task is in English
- Quick-action reply works
