# MISTRAL BRIEF: Marker Audit & Placement for Phase 128

## Your Role
You are a code marker specialist. Your job is to:
1. Scan files for existing MARKER_ tags
2. Verify markers are accurate (line numbers match)
3. Place NEW markers where Phase 128 changes need to go

## Task 1: Verify Existing Markers in agent_pipeline.py

File: `src/orchestration/agent_pipeline.py` (~2600 lines)

Check these markers exist and are at correct locations:
- MARKER_128.1A: `_detect_project_context()` method
- MARKER_128.1B: project_context injection in `_execute_subtask()`
- MARKER_122.5B: scout_report to coder wiring
- MARKER_124.9B: marker_map rails formatting
- MARKER_127.3: verifier defaults (passed=False)

For each marker, report: `{marker_id}: line {N} — {status: OK|MOVED|MISSING}`

## Task 2: Place Markers for 128.2 (Results Apply)

File: `src/api/routes/debug_routes.py`
- Find existing `GET /pipeline-results/{task_id}` endpoint
- Place MARKER_128.2B_APPLY right after it for the new POST /apply endpoint

File: `client/src/components/panels/TaskCard.tsx`
- Find where task status is rendered
- Place MARKER_128.2A_EXPAND where expand view should go

File: `client/src/components/panels/DevPanel.tsx`
- Find Board tab rendering
- Place MARKER_128.2C_STATE where expandedTaskId state should go

## Output Format
```
MARKER AUDIT REPORT
===================
agent_pipeline.py:
  MARKER_128.1A: line 504 — OK (method _detect_project_context)
  MARKER_128.1B: line 2432 — OK (project_context injection)
  ...

NEW MARKERS PLACED:
  debug_routes.py:1795 — MARKER_128.2B_APPLY (after pipeline-results GET)
  TaskCard.tsx:42 — MARKER_128.2A_EXPAND (task expand section)
  DevPanel.tsx:15 — MARKER_128.2C_STATE (expandedTaskId state)
```

## Rules
- DO NOT modify any logic — only add `// MARKER_XXX` comments
- Use `// MARKER_XXX` for TypeScript, `# MARKER_XXX` for Python
- Each marker on its own line, with brief description
- Keep markers concise: `// MARKER_128.2A_EXPAND: Expand view for pipeline results`
