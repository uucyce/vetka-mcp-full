# VETKA + MYCELIUM Canonization Roadmap V1.1 (2026-02-28)

Status: Execution roadmap (V1.1 patch)  
Depends on: `docs/155_ph/VETKA_MYCELIUM_CANONICAL_DAG_ARCHITECTURE_V1_2026-02-28.md`  
Context source: `docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt`

## 0. V1.1 Patch Scope
This patch adds missing implementation-critical items:
1. Schema versioning protocol.
2. Storage contract for `G_design` / `G_runtime` / `G_predict`.
3. Runtime event schema as builder input contract.
4. Spectral + discrepancy checks as explicit stages (not optional footnotes).
5. Scale/performance bounds.
6. Approval/auth and Engram integration as formal dependencies.

## 1. Core Goal
Сделать единый графовый канон, где любой источник (`py/json/md/xml/xlsx`) превращается в один DAG-контракт, а MCC рисует прежде всего реальное исполнение (`G_runtime`), не шаблон.

## 2. Input Matrix Integration (Decision)
`input_matrix` включаем в ядро канонизации, не как опцию.

Что берем из идеи:
1. Универсальные связи:
- explicit (явный import/reference)
- temporal (A created before B + similarity)
- referential (link/citation)
- semantic (embedding similarity)
2. Универсальные сканеры по типам контента.
3. Y-axis semantics: `time + knowledge_level`.

Что это дает в каноне:
1. `nodes[].meta.level` и `nodes[].meta.created_at`.
2. `edges[].meta.channel` (`explicit|temporal|referential|semantic`).
3. `edges[].meta.evidence` и `edges[].meta.score`.
4. Нормированный вектор направления (`source -> target`) по причинности.

## 3. Target State
1. `G_design`: план/шаблон.
2. `G_runtime`: факт исполнения из событий pipeline.
3. `G_predict`: JEPA overlay (dashed).
4. `input_matrix` channels enrich both `G_design` and `G_runtime`, but do not rewrite runtime causal edges.

## 4. Implementation Phases

### P0 — Schema Lock
1. Зафиксировать canonical JSON schema (graph/nodes/edges/layout_hints).
2. Добавить поля input_matrix:
- `edge.meta.channel`
- `edge.meta.evidence`
- `edge.meta.score`
- `node.meta.level`
3. Добавить schema validator в backend.
4. Добавить Schema Versioning Protocol:
- `schema_version` in payload
- semver policy (`MAJOR` breaking, `MINOR` additive, `PATCH` non-structural fixes)
- migration scripts `vX -> vY`
5. Зафиксировать Storage Contract:
- `G_design`: persisted and versioned (workflow registry + audit trail)
- `G_runtime`: persisted per run/task (immutable snapshots + latest pointer)
- `G_predict`: ephemeral by default, optional persisted snapshots when approved for analysis

Done criteria:
1. Любой DAG payload валидируется одной схемой.
2. Есть regression tests на schema compatibility.
3. Backward compatibility and migration tests for at least one schema bump.
4. Storage locations and retention rules documented and implemented.

### P1 — Runtime Builder (Source of Truth)
1. Построить `runtime_graph_builder` из event log pipeline (`emit_progress`, timeline events).
2. Зафиксировать canonical event schema, который builder потребляет:
- event id, ts, run_id, task_id, role, phase, action, payload, status
- ordering guarantees and out-of-order reconciliation rules
3. Добавить fault handling:
- duplicate events
- late events
- missing terminal events
2. Явно кодировать conditional edges:
- `on_fail`
- `on_major_fail`
- `on_pass`
4. Убрать synthetic retry nodes из runtime-builder (retry = edge condition).

Done criteria:
1. Endpoint `/api/workflow/runtime-graph/{task_id}` возвращает canonical runtime graph.
2. Для одной и той же задачи DAG совпадает с последовательностью событий.
3. Builder deterministic under out-of-order event replay.

### P2 — MCC Source Switch
1. В MCC ввести `workflow_source_mode = runtime|design|predict`.
2. Default: `runtime`.
3. `design` и `predict` — только по явному переключению.
4. Убрать silent fallback template->runtime подмену.
5. Добавить source badge в UI (`runtime|design|predict`).
6. P2.5 — Spectral Layout Quality:
- discrepancy-based balanced layering check (Tao ch.12)
- eigengap/community sanity check (Tao ch.13)
- verifier hint surface in MCC (non-blocking warnings)

Done criteria:
1. В обычном режиме UI показывает runtime DAG.
2. Визуальные правила не меняют topology.
3. Spectral/discrepancy warnings visible without mutating graph semantics.

### P3 — Multi-format Conversion
1. Importers:
- `python` (declaration/runtime)
- `json`
- `markdown`
- `xml`
- `xlsx`
2. Exporters:
- canonical -> `json/md/xml/xlsx/py-scaffold`
3. Round-trip tests:
- `xlsx -> canonical -> xlsx`
- `md -> canonical -> md`

Done criteria:
1. Topology and conditions preserved after round-trip.
2. Edge channels from input_matrix stay intact.

### P4 — Input Matrix Enrichment
1. Подключить channel scorers (`explicit/temporal/referential/semantic`) как graph enrich stage.
2. Добавить endpoint:
- `/api/workflow/enrich/input-matrix/{graph_id}`
3. Добавить фильтры в UI:
- show by channel
- threshold by score
4. Добавить spectral community tool hook for architecture clustering assistance.

Done criteria:
1. Пользователь может видеть связи по каналу.
2. Threshold не ломает базовую причинную цепочку runtime.
3. Community hints available as optional explorer tool.

### P5 — Predictive Overlay and Drift
1. JEPA edges только в `G_predict`, dashed.
2. Drift checker:
- compare `G_design` vs `G_runtime`
- discrepancy summary + alerts
3. Spectral anomaly hooks (Laplacian/eigengap) as formal diagnostics.
4. Expose drift diagnostics in both API and MCC panel.

Done criteria:
1. Predict overlay можно включать/выключать без изменения runtime topology.
2. Drift report доступен через API и в UI.
3. Spectral anomaly report emitted for runtime runs with diagnostics payload.

## 5. Endpoint Plan (V1)
1. `GET /api/workflow/runtime-graph/{task_id}`
2. `GET /api/workflow/design-graph/{workflow_id}`
3. `GET /api/workflow/predict-graph/{task_id}`
4. `POST /api/workflow/convert`
5. `POST /api/workflow/export/{format}`
6. `POST /api/workflow/enrich/input-matrix/{graph_id}`
7. `GET /api/workflow/drift-report/{task_id}`
8. `GET /api/workflow/schema/versions`
9. `POST /api/workflow/schema/migrate`
10. `GET /api/workflow/event-schema`

## 5.1 Approval / Auth Dependency (Post-V1 but formalized)
1. `G_design` mutations require role-aware approval policy.
2. Audit trail must record who approved structural workflow changes.
3. Runtime and predict graphs remain read-only for non-admin mutators.

## 6. Risks and Controls
1. Risk: runtime and template conflict in same canvas.
- Control: explicit source mode + badge.
2. Risk: temporal channel creates noisy edges.
- Control: `score + evidence + threshold`.
3. Risk: UI layout mutates semantics.
- Control: topology immutability tests.
4. Risk: graph scale exceeds readable/renderable threshold.
- Control: folder-level aggregation in overview + progressive drill + graphon-style approximation for very large graphs.
5. Risk: event loss/out-of-order creates invalid runtime DAG.
- Control: canonical event schema + replay reconciliation + integrity checks.

## 6.1 Testing and Benchmark Strategy
1. Unit tests:
- schema validator
- event->graph builder
- converters
2. Integration tests:
- endpoint -> MCC render -> topology verification
3. Fault tests:
- out-of-order events
- duplicate events
- missing terminal events
4. Round-trip tests:
- `xlsx/md/xml/json` topology and conditions preservation
5. Benchmarks:
- conversion latency target
- runtime graph build latency target
- UI render threshold target by node/edge count

## 6.2 Engram Dependency (Post-V1)
1. Persist viewed/approved graph preferences to Engram user memory.
2. Allow user-level defaults (`workflow_source_mode`, channel filters, thresholds).
3. Keep this integration decoupled from canonical schema core.

## 7. Checklist (Execution) — Updated
### P0 — Schema Lock
1. [ ] Canonical schema file committed.
2. [ ] Schema validator in backend.
3. [ ] Schema versioning protocol defined.
4. [ ] Storage contract decided (`G_design/G_runtime/G_predict`).

### P1 — Runtime Builder
5. [ ] Event log schema defined.
6. [ ] Runtime graph builder implemented.
7. [ ] Conditional edges (`on_fail/on_pass/on_major_fail`) working.
8. [ ] Endpoint: `GET /api/workflow/runtime-graph/{task_id}`.

### P2 — MCC Source Switch
9. [ ] MCC switched to runtime default.
10. [ ] Source mode badge in UI (`runtime|design|predict`).
11. [ ] Silent fallback removed.
12. [ ] Discrepancy-based balanced layering check integrated.

### P3 — Multi-format Conversion
13. [ ] `xlsx` importer/exporter.
14. [ ] `md` importer/exporter.
15. [ ] Round-trip topology preservation tests.
16. [ ] Edge channels preserved after round-trip.

### P4 — Input Matrix Enrichment
17. [ ] Channel scorers connected.
18. [ ] Endpoint: `POST /api/workflow/enrich/input-matrix/{graph_id}`.
19. [ ] UI filters by channel + threshold.
20. [ ] Spectral community detection available as tool.

### P5 — Predictive Overlay and Drift
21. [ ] JEPA overlay isolated from runtime.
22. [ ] Drift checker: `G_design` vs `G_runtime`.
23. [ ] Drift report in API and UI.
24. [ ] Spectral anomaly hooks (Laplacian eigengap).

### Post-V1 Dependencies
25. [ ] Approval flow / audit trail.
26. [ ] Engram memory integration.
27. [ ] Scale strategy for `>10K` nodes.
28. [ ] Performance benchmarks and SLOs.

## 8. Direct Answer to Strategic Question
Да, при этой канонизации мы действительно сможем визуализировать любой скрипт/формат, включая Excel, и обратно экспортировать, без потери логики исполнения.  
`input_matrix_idea` уже учтен концептуально и в кодовой базе частично (через MCC SCC graph markers), но в canonical runtime workflow-пайплайне он пока не доведен до полного системного контракта — этот roadmap именно закрывает этот разрыв.
