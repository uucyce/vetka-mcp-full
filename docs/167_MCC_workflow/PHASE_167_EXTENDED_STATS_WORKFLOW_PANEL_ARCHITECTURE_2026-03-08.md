# PHASE 167 — Extended Stats/Workflow Panel Architecture

Date: 2026-03-08
Protocol stage: RECON+markers -> REPORT (NO IMPL)
Scope: MCC runtime panel architecture only

## 1. Goal

Turn `Stats` into the explicit workflow control surface for MCC without breaking the current default behavior:

- keep `task node -> drill -> workflow` as the primary default path,
- keep compact `Stats` lightweight and readable,
- make workflow/team choice explicit when a task is selected,
- unify statistics, workflow choice, and MYCO guidance instead of scattering them across multiple duplicate panels.

This phase is architecture only. No code rewrite is proposed here.

## 2. Current Confirmed Runtime Seams

### 2.1 Stats surface already exists
- `client/src/components/mcc/MiniStats.tsx`
- Markers:
  - `MARKER_154.14A`
  - `MARKER_155.STATS.UI`

Confirmed:
- compact `MiniStats` already renders MCC-specific runtime signals,
- expanded `MiniStats` already renders global/project analytics,
- compact mode already shows workflow/graph/runtime hints:
  - `wf:{context.workflowSourceMode}`
  - graph verifier decision
  - runtime health
  - reinforcement hint (`rh:`)

Conclusion:
- `MiniStats` is already the least disruptive insertion point for explicit workflow controls.

### 2.2 Workflow library and selection already exist
- Core template library:
  - `src/services/architect_prefetch.py`
- MCC library routes:
  - `src/api/routes/mcc_routes.py`
- User workflow store:
  - `src/api/routes/workflow_template_routes.py`
  - `src/services/workflow_store.py`

Confirmed levels:
- MCP execution route level:
  - `workflow_type = pm_to_qa | pm_only | dev_qa`
- Architect template-family level:
  - `ralph_loop`
  - `g3_critic_coder`
  - `bmad_default`
  - other JSON templates from `data/templates/workflows`
- User workflow DAG level:
  - `/api/workflows`
- Runtime fallback visualization level:
  - `client/src/components/mcc/MyceliumCommandCenter.tsx`

Conclusion:
- the system already has workflow data sources,
- the gap is explicit runtime selection and clear user-facing semantics.

### 2.3 MYCO already has workflow-aware advisory seams
- `client/src/components/mcc/MiniChat.tsx`
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `src/services/myco_memory_bridge.py`

Relevant markers already present:
- `MARKER_162.P4.P2.MYCO.TOP_HINT_WORKFLOW_ACTIONS.V1`
- `MARKER_162.P4.P4.MYCO.TOP_HINT_NODE_ROLE_WORKFLOW_MATRIX.V1`
- `MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1`
- `MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1`

Conclusion:
- workflow choice should not create a new helper subsystem,
- it should feed existing MYCO advisory/memory surfaces.

## 3. Architectural Problem

The current runtime has three separate truths that are not yet made explicit to the user:

1. The user sees a workflow graph after drill, but the choice of workflow family is mostly implicit.
2. `Stats` knows enough to display workflow diagnostics, but not enough to act as a chooser.
3. MYCO can advise based on workflow context, but the active workflow selection is not first-class in the runtime UI.

This causes a gap:
- the user sees a team/workflow result,
- but not a clean place to confirm, compare, replace, or understand it.

## 4. Proposed Runtime Model

`Stats` becomes the canonical runtime surface for:

- project/task execution statistics,
- active workflow identity,
- workflow bank selection,
- team/agent summary,
- MYCO-supported tool reminders.

This does not replace drill.
It complements drill.

### 4.1 Default interaction model

When no task is selected:
- `Stats` behaves mostly like now,
- shows project-level analytics and high-level workflow diagnostics.

When a task node is selected:
- compact `Stats` becomes task-scoped,
- it shows:
  - explicit `WORKFLOW` action/prompt,
  - active workflow family,
  - workflow bank,
  - team profile,
  - workflow/team statistics summary,
  - brief health/perf summary,
  - one-line MYCO hint.

When expanded:
- `Stats` becomes the workflow control plane for the selected task.

### 4.2 Expanded Stats panel sections

The expanded window should be structured in this order:

1. `Current Task`
- selected task title, status, phase, scope

2. `Active Workflow`
- active family/template name
- bank source
- team/preset
- provenance:
  - `heuristic`
  - `user-selected`
  - `saved-task-binding`
  - `fallback`

3. `Workflow Banks`
- `Core`
- `Saved`
- `n8n`
- `ComfyUI`
- `Imported`

4. `Workflow Catalog`
- list/cards of workflows within the chosen bank
- compact metrics if available
- one default action:
  - `Select for task`

5. `Runtime Stats`
- task/project execution stats
- team breakdown
- agent performance

6. `MYCO Guidance`
- why this workflow fits
- what tools/roles are important next
- which tools should be pulled into context

This keeps workflow choice next to evidence instead of separating chooser and diagnostics.

### 4.3 Compact Stats rule

Compact `Stats` is not read-only when a task is selected.

It must remain visually compact, but it should still be explicit:

- show `WORKFLOW` as a first-class action,
- show current workflow/team stats next to that action,
- make it obvious that the selected task can switch workflow from this surface,
- defer full bank/catalog browsing to expanded mode.

This is the required compromise:
- compact mode stays small,
- but workflow choice is still explicit instead of hidden behind drill alone.

## 5. Workflow Banks Model

Workflow banks should be user-facing, explicit, and stable.

### 5.1 Bank definitions

`core`
- templates from `data/templates/workflows/*.json`
- examples:
  - `ralph_loop`
  - `g3_critic_coder`
  - `bmad_default`
  - `quick_fix`
  - `research_first`

`saved`
- user-created workflows from `data/workflows/*.json`
- existing `/api/workflows` contour

`n8n`
- workflows imported/generated through the n8n conversion path

`comfyui`
- workflows imported/generated through the ComfyUI conversion path

`imported`
- canonical imported workflows produced from MD/XML/XLSX/other converters

### 5.2 Important semantic rule

Bank is not family.

Examples:
- `core / ralph_loop`
- `core / g3_critic_coder`
- `saved / pipeline_variant_07`
- `n8n / content_sync_flow`
- `comfyui / storyboard_refiner`

This distinction is required to prevent the existing term collision around `workflow`.

## 6. Task Binding Model

The selected task should eventually carry explicit workflow binding metadata.

Recommended binding fields:

- `workflow_bank`
- `workflow_id`
- `workflow_family`
- `workflow_source_mode`
- `team_profile`
- `selection_origin`

Where:
- `workflow_bank` = `core | saved | n8n | comfyui | imported`
- `workflow_id` = stable key inside bank
- `workflow_family` = normalized family/class when applicable
- `workflow_source_mode` = current resolved source
- `team_profile` = runtime preset/team choice
- `selection_origin` = `heuristic | user | restored | fallback`

Rule:
- explicit user binding must override heuristic prefetch,
- heuristic remains default only when no explicit binding exists.

## 7. MYCO / Tool Memory Integration

### 7.1 MYCO role in this architecture

MYCO should not own workflow selection.
MYCO should explain and reinforce it.

MYCO receives:
- selected task,
- selected workflow bank/family,
- selected team profile,
- current graph/runtime health,
- tool/favorites/context hints.

MYCO outputs:
- one-line hint in compact `Stats`,
- richer rationale in expanded `Stats`,
- role/tool reminders in `MiniChat`.

### 7.2 Tool prioritization

Adaptive tool emphasis should be layered as:

1. workflow-required tools
2. role-required tools
3. project-context tools
4. favorite/frequent tools

This avoids accidental priority inversion where favorites override workflow-critical tools.

### 7.3 CAM / favorites / Weaviate

Current evidence suggests:
- favorites exist and already affect model/key behavior,
- CAM exists as a memory/context structure,
- hidden MYCO memory bridge already indexes instruction-like sources.

Architecture recommendation:
- use CAM/favorites/Weaviate as ranking signals,
- do not make them the authoritative source of workflow-tool policy.

## 8. UI Constraints

The panel must preserve current MCC design language:

- monochrome only,
- no new color semantics,
- no off-style icon library,
- no duplicate "workflow toolbar" revival,
- compact mode must remain fast and legible,
- expanded mode may add control density, but must stay aligned with current black/white panel grammar.

Future icon note:
- when custom MYCO black/white icons are provided, they should replace placeholder iconography through a dedicated icon pass, not mixed into workflow architecture work.

## 9. Confirmed Gaps To Close

### G1. Workflow choice is not explicit in runtime
Confirmed by:
- `TaskEditPopup.tsx`
- `WorkflowToolbar.tsx` deprecation
- heuristic selection in `architect_prefetch.py`

### G2. Stats knows diagnostics but is not yet a selector
Confirmed by:
- compact `wf:`/`graph:`/`rh:` hints in `MiniStats.tsx`
- expanded stats lacking workflow controls

### G3. Workflow terminology is overloaded
Confirmed levels:
- MCP execution route
- core template family
- user workflow DAG
- runtime drilled workflow graph

### G4. External banks are structurally possible but not yet unified
Confirmed by:
- template library routes
- workflow store routes
- conversion infrastructure

## 10. Proposed Architecture Decision

Decision:
- extend `MiniStats` into `Stats + Workflow Control`,
- keep `MyceliumCommandCenter` as graph host and drill surface,
- keep `MiniChat`/MYCO as advisor,
- avoid introducing a second standalone workflow chooser panel.

Reason:
- this reuses current seams,
- keeps workflow choice near evidence,
- reduces UI noise,
- avoids duplicating state across separate surfaces.

## 11. Markers For Future Implementation

Recommended new marker family for this feature:

- `MARKER_167.STATS_WORKFLOW.ARCH.V1`
- `MARKER_167.STATS_WORKFLOW.BANKS.V1`
- `MARKER_167.STATS_WORKFLOW.TASK_BINDING.V1`
- `MARKER_167.STATS_WORKFLOW.MYCO_GUIDANCE.V1`
- `MARKER_167.STATS_WORKFLOW.UI_EXPANDED_SELECTOR.V1`

## 12. Non-Goals For This Phase

Not part of this architecture phase:

- changing workflow execution engine semantics,
- rewriting drill graph rendering,
- replacing architect heuristic selection,
- adding colorful icon packs,
- implementing OpenClaw acceleration,
- reworking the whole task model.

## 13. Exit Criteria For Architecture Phase

This document is sufficient when:

- workflow banks are clearly defined,
- `Stats` is established as the canonical chooser surface,
- task-binding fields are specified,
- MYCO/tool-memory role is explicitly bounded,
- implementation can proceed in narrow waves without inventing a parallel subsystem.
