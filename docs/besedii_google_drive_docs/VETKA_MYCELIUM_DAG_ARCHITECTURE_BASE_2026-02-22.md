# VETKA / Mycelium: DAG Architecture Base (2026-02-22)

Status: Draft for alignment before next implementation wave.
Scope: MCC (Mycelium Command Center) single-window UX, architectural DAG design process, JEPA role, memory-system integration.

## 1. Why this document exists

Core insight: a readable acyclic DAG is not produced by layout alone. It requires a process artifact.

Reference insight (from transcript):
- If process is weak, model speed increases but quality/complexity degrades.
- Working sequence must be explicit: Research -> Design -> Plan -> Implement -> Verifier/Eval.
- Design must be reviewed/approved before implementation.

For VETKA this means:
- Architectural DAG is a first-class approved artifact.
- Runtime graph and predictive overlays are separate layers.
- UI stays one-window; context changes by drill, not scene switch.

## 2. User scenarios (first launch)

### A) Continue existing project (large codebase)
1. User opens MCC.
2. Architect-planner runs Research over project.
3. System proposes Design DAG candidate.
4. User + architect approve/adjust DAG.
5. Only then: tasks/workflows are attached and executed.

### B) New project (empty)
1. User opens MCC.
2. Architect-planner bootstraps project architecture DAG from intent/templates.
3. User approves skeleton DAG.
4. Tasks and workflows are generated from approved nodes.

## 3. Graph contract (must not be mixed)

### G_design (approved architecture)
- Source of truth for project structure and planned dependency intent.
- Includes directory/module hierarchy and planned nodes.
- States:
  - white: implemented/confirmed in code
  - gray/transparent: planned/not yet implemented

### G_runtime (observed reality)
- Extracted from scanners and input_matrix channels.
- Reflects actual code/artifact relations and evolution.
- Used for drift detection vs G_design.

### G_predict (JEPA overlay)
- Predictive edges/nodes with confidence.
- Dashed/overlay only.
- Never auto-rewrites G_design.

## 4. Mandatory process pipeline

1. Research
- Narrow relevant scope.
- Produce compact evidence package (files, modules, artifacts, references, timestamps).

2. Design
- Build architecture DAG candidate (acyclic, human-readable).
- Include C4/data-flow/sequence level where needed.
- Explicitly mark assumptions and unresolved edges.

3. Plan
- Convert approved DAG nodes into phases/tasks.
- Define acceptance checks and rollback criteria.

4. Implement
- Execute with gates and verification.
- Update G_runtime continuously.
- Update G_design only through explicit approval.

5. Verifier/Eval
- Run architecture conformance checks against approved G_design.
- Run quality gates on graph health and readability before merge/deploy.
- Explicit verdict: PASS / FAIL / NEEDS REVISION.

## 5. One-window MCC behavior

- Single canvas always.
- Overview: architecture-level DAG (directory/module level first).
- Drill on node:
  - reveal task card
  - reveal selected node dependencies
  - reveal assigned team workflow (if exists)
- No “new room” scene switch.

## 6. Why folders/directories are required in overview

Without directory-level aggregation, file graph becomes unreadable “rail/heap”.

Required:
- Overview graph uses folder/module nodes.
- File-level detail appears on drill.
- Cross-links are progressive disclosure (on-click / focused mode).

## 7. JEPA role in VETKA

JEPA is not a replacement for deterministic DAG construction.

JEPA is:
- predictive layer for candidate relations/evolution,
- noise-reduction aid for context packaging,
- helper for planner/architect recommendations.

JEPA is not:
- authoritative source of architecture truth,
- auto-commit mechanism for topology changes.

## 8. Input_matrix and knowledge level

Knowledge level must follow causal semantics, not arbitrary layout output.

High-level rule:
- lower levels: earlier/foundational/source nodes
- upper levels: derived/specialized nodes

Practical edge channels:
- explicit import/reference
- temporal precedence + semantic relation
- documentary reference/citation
- multimodal relation (video/audio/book/script/doc)

## 9. Verifier/Eval quality gates (DAG acceptance)

Required gates for approved architecture DAG:
- Acyclicity gate: no cycle in approved view.
- Monotonicity gate: source level < target level for all visible edges.
- Readability gate: no overloaded first-screen layers (balanced distribution).
- Spectral gate: laplacian health checks (connectivity, anomaly ratio, eigengap sanity).
- Traceability gate: every edge has channel + evidence.
- Drift gate: runtime deviations from approved design are explicitly flagged.

## 10. Architectural decision

Creation and approval of Architecture DAG is a dedicated task.
It is equivalent in importance to project master prompt/spec.

VETKA principle:
- VETKA is memory,
- VETKA is project,
- VETKA is team/workflow,
- therefore architecture DAG approval is a core governance step.

## 11. What must be clarified before next implementation wave

Mandatory decisions:
1. Canonical root semantics.
Use one definition and keep it stable across all modules (source/foundation, not visual convenience).
2. Overview node type policy.
Directory/module only in overview; file-level only on drill.
3. Edge visibility policy.
Minimal backbone by default, expanded links only on focus/click.
4. Spectral gate thresholds.
Set concrete PASS/FAIL thresholds for eigengap, anomaly ratio, and layer imbalance.
5. JEPA merge policy.
JEPA remains overlay only; define explicit human approval path for promotion into design.

## 12. Sources used

- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/mycelium__bdmitriipro_transcript_youtube.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/terens_tao_GROK.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Convolutional_neural_network_GROK.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Jepa_GROK-VETKA.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/besedii_best_part.txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Opus 46 Discrepancy Theory & Equitable Coloring (Tao гл. 12) .txt
- /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Opus46# 🌊 Fourier Analysis on Graphs (Tao гл. 13) → Spectral Tools для Архитектора VETKA + JEPA.txt
