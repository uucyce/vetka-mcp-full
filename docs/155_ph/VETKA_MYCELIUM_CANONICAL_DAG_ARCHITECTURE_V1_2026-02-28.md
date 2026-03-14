# VETKA + MYCELIUM Canonical DAG Architecture V1 (2026-02-28)

Status: Draft for implementation lock  
Scope: Unified graph contract for VETKA and MYCELIUM, single source of truth for workflow rendering and conversion.

## 1. Problem Statement
Current MCC behavior mixes multiple sources (`template`, `fallback`, partial `dag`) and can draw vectors that do not match real pipeline execution.

Target behavior:
1. DAG in UI must reflect real pipeline execution (`runtime`) by default.
2. Template graph remains planning artifact, never auto-substitutes runtime.
3. Any source format (`py`, `json`, `md`, `xml`, `xlsx`) must convert into one canonical graph schema.

## 2. Three Graph Layers (Frozen)
Aligned with base architecture (`G_design`, `G_runtime`, `G_predict`):

1. `G_design`
- Approved architecture/workflow intent (planner/template).
- Editable by architect/user with approval flow.

2. `G_runtime`
- Observed execution graph built from pipeline events/logs.
- Primary source for workflow visualization in MCC.

3. `G_predict`
- JEPA predictive overlay.
- Dashed and non-destructive; never rewrites `G_design`/`G_runtime`.

## 3. Canonical DAG Schema (Core Contract)
All importers/exporters must target this shape.

```json
{
  "graph": {
    "id": "string",
    "version": "1.0.0",
    "source_format": "python|json|markdown|xml|xlsx|runtime_events",
    "execution_mode": "design|runtime|predict",
    "created_at": "ISO-8601",
    "updated_at": "ISO-8601"
  },
  "nodes": [
    {
      "id": "string",
      "type": "phase|agent|task|gate|artifact|group|condition|parallel|loop|transform",
      "label": "string",
      "role": "system|architect|scout|researcher|coder|verifier|eval|deployer",
      "status": "pending|running|done|failed|skipped",
      "meta": {}
    }
  ],
  "edges": [
    {
      "id": "string",
      "source": "node_id",
      "target": "node_id",
      "kind": "flow|conditional|feedback|predicted",
      "condition": "always|on_pass|on_fail|on_major_fail|on_retry",
      "meta": {}
    }
  ],
  "layout_hints": {
    "direction": "bottom_up",
    "layering": "canonical",
    "spacing": {
      "x": 118,
      "y": 100
    }
  }
}
```

## 4. Runtime Truth Rules
1. MCC workflow view default source: `G_runtime`.
2. `G_design` shown only as explicit "plan mode".
3. `G_predict` shown only as overlay (dashed, confidence-weighted).
4. No fake entities for control flow:
- Retry is edge condition (`on_fail`) to existing target node.
- Replan is conditional edge (`on_major_fail`) to architect stage.

## 5. Pipeline Canonical Sequence (Dragon/Titan)
Frozen execution chain:

`Task intake -> Architect(recon request) -> parallel recon(Scout + Researcher) -> Architect(final subtask plan) -> Coder -> Verifier -> (on_fail -> Coder, on_major_fail -> Architect) -> quality summary -> completion/dispatch`

Notes:
1. `Eval` is metric/score layer; can be node or meta event, but does not replace verifier gate.
2. `Retry Coder` is preferred as conditional feedback edge, not standalone mandatory node.

## 6. Import/Export Matrix
Canonical graph is intermediary for all formats.

1. Importers:
- `python` (pipeline declarations / runtime events)
- `json` (template/workflow data)
- `markdown` (table/list workflow syntax)
- `xml` (BPMN-like or custom)
- `xlsx` (tabular workflow sheet)

2. Exporters:
- canonical -> `json`
- canonical -> `markdown`
- canonical -> `xlsx`
- canonical -> `xml`
- canonical -> `python` (generated pipeline scaffold)

3. Round-trip requirement:
- `format -> canonical -> format` must preserve topology (`nodes`, `edges`, `conditions`) and role semantics.

## 7. API Contract (V1)
1. `GET /api/workflow/runtime-graph/{task_id}`
- Returns canonical `G_runtime` graph.

2. `GET /api/workflow/design-graph/{workflow_id}`
- Returns canonical `G_design`.

3. `GET /api/workflow/predict-graph/{task_id}`
- Returns canonical `G_predict` overlay edges/nodes.

4. `POST /api/workflow/convert`
- Input: source format payload.
- Output: canonical graph.

5. `POST /api/workflow/export/{format}`
- Input: canonical graph.
- Output: target format payload/file.

## 8. UI Binding Contract (Single Canvas)
1. Single window only (no forced workflow popup).
2. Workflow frame is local reserved area near selected task.
3. Layout can change positions, but cannot mutate edge semantics.
4. Interaction:
- click: select/highlight
- double-click: expand/collapse local subgraph
- empty click: clear selection

## 9. Anti-Hardcode Policy
1. No ad-hoc source arbitration by UI heuristics.
2. No synthetic edges that are absent in canonical source.
3. No fallback graph generation in render layer (fallback only in backend converter with explicit `source_format=fallback` and audit marker).
4. All transformations logged with marker + reason.

## 10. Dead-Code and Drift Control
1. Deprecate template-only inline builders after runtime source is stable.
2. Keep migration shims behind feature flags with expiry date.
3. Add drift checker:
- Compare `G_design` vs `G_runtime` per run.
- Emit discrepancy report and confidence summary.

## 11. Implementation Roadmap (No Big-Bang)
Phase A: Schema + Builder
1. Freeze canonical JSON schema and validation.
2. Build runtime event->graph builder in backend.
3. Add API `runtime-graph/{task_id}`.

Phase B: UI Source Switch
1. MCC workflow view consumes runtime graph first.
2. Template graph moved to explicit plan mode.
3. Predict overlay rendered separately.

Phase C: Converters
1. Add xlsx/md/xml importers.
2. Add exporters and round-trip tests.

Phase D: Governance
1. Drift reports and discrepancy metrics.
2. Spectral overlays for anomaly hints (optional, non-blocking).

## 12. Acceptance Checklist
1. For same task run, DAG topology equals runtime event chain.
2. `on_fail` and `on_major_fail` are visible as conditional feedback vectors.
3. No direct architect->coder edge when recon stage is present in runtime.
4. Switching source mode (`runtime/design/predict`) does not mutate underlying graph state.
5. Round-trip `xlsx -> canonical -> xlsx` preserves dependencies and conditions.
6. JEPA overlay can be toggled off with zero impact on runtime graph.

## 13. Immediate Next Actions
1. Implement backend `runtime event -> canonical graph` builder.
2. Add MCC flag: `workflow_source = runtime|design|predict` (default `runtime`).
3. Add first converter: `xlsx <-> canonical` for operator-friendly editing.

