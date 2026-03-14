# GOLDEN_DESIGN_DAG_V1

Status: Draft for approval (B1 closure candidate)  
Date: 2026-02-23  
Owner: Architect + Danila

Markers:
- `MARKER_155.READINESS.BLOCKER.B1.DESIGN_SOURCE_OF_TRUTH`
- `MARKER_155.GOLDEN_DAG.V1`
- `MARKER_155.INPUT_MATRIX.ROOT_SCORE.V1`

## 1. Purpose
Canonical approved Design DAG artifact for MCC/Mycelium.
This file is the single source of truth for architecture intent before implementation.

Process position:
`Research -> Design -> Plan -> Implement -> Verifier/Eval`

## 2. Canonical Root Semantics (Frozen Proposal)
Root definition:
- Root is the foundational source node with highest architecture influence score.
- Influence score is derived from approved channels (structural/reference/temporal/semantic), not UI convenience.
- Root must be explainable with evidence.

Root policy:
- One canonical root at overview level.
- Multi-root reality may be condensed into one super-root only by explicit verifier report.

Approved root (current project):
- `vetka_live_03` (project root)

## 3. Node Type Policy (Overview vs Drill)
Overview (L1):
- Allowed node types: `project`, `directory`, `module`.
- Forbidden: raw file-level explosion.

Drill (L2):
- Allowed node types: `file`, `task`, `workflow`, `agent`.

State colors (fixed):
- `white`: implemented/confirmed
- `gray/transparent`: planned/not implemented

## 4. Edge Type Policy (Approved)
Edge channels:
- `structural` (imports/dependency)
- `reference` (docs/spec citations)
- `temporal` (earlier -> later causal relation)
- `semantic` (embedding-based relation)
- `multimodal` (artifact/media cross-type)

Visibility:
- Overview: backbone edges only.
- Focus/click: expand to top-ranked local edges with evidence.

## 5. Golden DAG Snapshot (v1 expanded)
Policy: overview-level canonical graph is adaptive in size and is governed by readability budgets, not fixed node counts.

Anti-hardcode rule:
- No fixed node count target (for example 20/30/40) is allowed.
- Node set grows/shrinks by project scope and readability constraints.
- Canonical requirement is structural clarity, not a preselected graph size.

### 5.1 Nodes (canonical set)
| id | label | type | level | state |
|---|---|---|---|---|
| n01 | vetka_live_03 | project | 0 | white |
| n02 | src | directory | 1 | white |
| n03 | client | directory | 1 | white |
| n04 | docs | directory | 1 | white |
| n05 | data | directory | 1 | white |
| n06 | tests | directory | 1 | white |
| n07 | tools | directory | 1 | white |
| n08 | scripts | directory | 1 | white |
| n09 | app | directory | 1 | white |
| n10 | pulse | directory | 1 | white |
| n11 | frontend | directory | 1 | white |
| n12 | config | directory | 1 | white |
| n13 | src/api | module | 2 | white |
| n14 | src/orchestration | module | 2 | white |
| n15 | src/scanners | module | 2 | white |
| n16 | src/memory | module | 2 | white |
| n17 | src/knowledge_graph | module | 2 | white |
| n18 | src/layout | module | 2 | white |
| n19 | src/visualizer | module | 2 | white |
| n20 | src/mcp | module | 2 | white |
| n21 | src/elisya | module | 2 | white |
| n22 | src/workflows | module | 2 | white |
| n23 | src/services | module | 2 | white |
| n24 | src/search | module | 2 | white |
| n25 | src/monitoring | module | 2 | white |
| n26 | src/agents | module | 2 | white |
| n27 | client/src/components/mcc | module | 2 | gray |
| n28 | client/src/store | module | 2 | white |
| n29 | client/src/services | module | 2 | white |
| n30 | data/workflows+tasks+artifacts | module | 2 | white |

### 5.2 Backbone edges (canonical set)
| source | target | channel | rationale |
|---|---|---|---|
| n01 | n02 | structural | project contains backend core |
| n01 | n03 | structural | project contains client UI |
| n01 | n04 | reference | project architecture/spec knowledge |
| n01 | n05 | structural | project runtime data/state |
| n01 | n06 | structural | project verification layer |
| n01 | n07 | structural | project toolchain layer |
| n01 | n08 | structural | project automation scripts |
| n01 | n09 | structural | app layer |
| n01 | n10 | structural | pulse subsystem |
| n01 | n11 | structural | alternate frontend layer |
| n01 | n12 | structural | config layer |
| n02 | n13 | structural | API surface from backend core |
| n02 | n14 | structural | orchestration from backend core |
| n02 | n15 | structural | scanners from backend core |
| n02 | n16 | structural | memory services from backend core |
| n02 | n17 | structural | KG/DAG model from backend core |
| n02 | n18 | structural | layout engine from backend core |
| n02 | n19 | structural | visualizer from backend core |
| n02 | n20 | structural | MCP integration from backend core |
| n02 | n21 | structural | Elisya orchestration from backend core |
| n02 | n22 | structural | workflow engine from backend core |
| n02 | n23 | structural | shared services from backend core |
| n02 | n24 | structural | search subsystem from backend core |
| n02 | n25 | structural | monitoring subsystem |
| n02 | n26 | structural | agent subsystem |
| n03 | n27 | structural | MCC UI feature module |
| n03 | n28 | structural | client state management |
| n03 | n29 | structural | client service/adapters |
| n05 | n30 | structural | persistent workflow/task/artifact storage |
| n27 | n28 | structural | MCC UI depends on client state |
| n27 | n29 | structural | MCC UI depends on client adapters |
| n14 | n22 | structural | orchestration uses workflow runtime |
| n14 | n26 | structural | orchestration coordinates agents |
| n16 | n21 | structural | memory context integrated with Elisya |
| n17 | n18 | structural | graph model feeds layout engine |
| n18 | n19 | structural | layout feeds visualization |
| n15 | n30 | structural | scanners update persisted artifacts/tasks/workflows |
| n13 | n25 | structural | API behavior monitored by monitoring subsystem |

Notes:
- This is canonical backbone for overview readability, not full dependency graph.
- Additional edges appear only in focused drill with evidence.

## 6. Drill Zones (L2 expansion policy)
- Zone A (Architecture Core): `n13..n26`.
- Zone B (MCC UI): `n27, n28, n29`.
- Zone C (Project Memory/Data): `n30`.

Drill behavior:
- click node -> show task card + top local edges + workflow assignment
- double-click -> enter local subgraph in same canvas (no scene swap)

## 7. Workflow-Team Relation (Frozen)
- Task attaches to architecture node.
- Team/workflow attaches to task.
- Workflow does not replace architecture DAG.

## 8. Approval Contract
Approval checklist:
- [ ] Root semantics accepted
- [ ] Node type policy accepted
- [ ] Edge type policy accepted
- [ ] Golden nodes/edges accepted
- [ ] Overview/drill visibility accepted

Approvers:
- Architect: ____________________
- Product owner (Danila): ____________________
- Date: ____________________

## 9. Change Policy
- Any topology change to this golden artifact requires explicit approval.
- JEPA predictions remain overlay-only until approved into this file.
- Runtime graph drift is reported against this artifact.

## 10. Exit Criteria (B1 Closure)
`MARKER_155.READINESS.BLOCKER.B1` is CLOSED when:
1. This file is approved and signed.
2. Root semantics and golden backbone are frozen.
3. Verifier reads this file as design baseline.
