# MYCO Context Payload Contract V1

Status: `P0 CONTRACT`
Date: `2026-03-06`

Marker: `MARKER_162.MYCO.VIEWPORT_CONTEXT_PAYLOAD.V1`

## Purpose
Единый payload для helper-объяснений в MCC, независимо от режима (tree/workflow/node).

## Schema (runtime object)
```json
{
  "version": "v1",
  "timestamp_ms": 0,
  "mode": "off|passive|active",
  "ui": {
    "nav_level": "roadmap|tasks|workflow|running|results|first_run",
    "focus_scope_key": "string",
    "workflow_source_mode": "runtime|design|predict",
    "selected_node_id": "string|null",
    "selected_node_ids": ["string"],
    "selected_task_id": "string|null",
    "panel_focus": "tasks|chat|context|stats|balance|none"
  },
  "viewport": {
    "zoom": 0,
    "center": { "x": 0, "y": 0 },
    "visible_node_count": 0,
    "visible_edge_count": 0,
    "lod": "macro|meso|micro"
  },
  "node": {
    "id": "string|null",
    "kind": "project|task|agent|file|directory|workflow|node|null",
    "label": "string",
    "status": "pending|running|done|failed|unknown",
    "role": "architect|scout|researcher|coder|verifier|eval|null",
    "task_id": "string|null",
    "path": "string|null",
    "graph_kind": "string|null"
  },
  "event": {
    "type": "click|select|hover|nav_change|zoom_change|manual_help_request",
    "source": "canvas|miniwindow|chat|keyboard|system"
  }
}
```

## Budget rules
1. Payload max size: `<= 8 KB` JSON serialized.
2. No raw code/file body in payload.
3. If `visible_node_count > 120`, keep only aggregate counters.

## Required fields for explanation
1. `ui.nav_level`
2. `viewport.lod`
3. `node.kind`
4. `event.type`

## Fallback behavior
1. Если payload неполный -> MYCO returns short safe message:
   - "Я вижу текущий экран, но контекст неполный. Кликни по ноде, и я поясню точнее."
