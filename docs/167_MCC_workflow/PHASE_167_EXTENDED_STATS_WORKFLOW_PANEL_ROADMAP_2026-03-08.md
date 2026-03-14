# PHASE 167 — Extended Stats/Workflow Panel Roadmap

Date: 2026-03-08
Protocol stage: RECON+markers -> REPORT -> WAIT GO
Scope: phased implementation plan only

Related docs:
- `docs/167_MCC_workflow/RECON_workflow_selection_levels_2026-03-08.md`
- `docs/167_MCC_workflow/PHASE_167_EXTENDED_STATS_WORKFLOW_PANEL_ARCHITECTURE_2026-03-08.md`

## 1. Objective

Deliver an MCC runtime panel where:

- task workflow choice is explicit,
- workflow banks are visible,
- stats and workflow choice are unified,
- MYCO can proactively reinforce the right tools and roles,
- the current drill-first workflow remains intact.

## 2. Core Principles

1. No duplicate runtime surface.
`Stats` evolves; deprecated workflow surfaces stay deprecated.

2. User selection beats heuristic.
Heuristic workflow choice remains default only until the user explicitly chooses.

3. Banks are explicit.
`core`, `saved`, `n8n`, `comfyui`, `imported` must be distinct in UI and contracts.

4. MYCO advises, not owns selection.
MYCO explains and reinforces workflow choice; it does not replace the chooser.

5. Monochrome by default.
No new color language. No random icon library.

## 3. Confirmed Implementation Base

The roadmap reuses these existing seams:

- `client/src/components/mcc/MiniStats.tsx`
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `client/src/components/mcc/MiniChat.tsx`
- `src/api/routes/mcc_routes.py`
- `src/api/routes/workflow_template_routes.py`
- `src/services/architect_prefetch.py`
- `src/services/workflow_store.py`
- `src/services/myco_memory_bridge.py`

## 4. Phased Delivery

### W1. Contract and catalog unification

Goal:
- define one MCC-facing workflow catalog contract for all banks.

Deliverables:
- catalog response shape for:
  - bank
  - id
  - title
  - family
  - source
  - description
  - compatibility tags
  - lightweight runtime metrics if available
- clear normalization rules for:
  - `workflow_bank`
  - `workflow_family`
  - `selection_origin`

Likely backend seam:
- `src/api/routes/mcc_routes.py`

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.CATALOG_API.V1`
- `MARKER_167.STATS_WORKFLOW.CATALOG_NORMALIZE.V1`

Tests:
- `tests/mcc/test_mcc_workflow_catalog_contract.py`
- `tests/mcc/test_mcc_workflow_bank_normalization.py`

### W2. Task binding and restore policy

Goal:
- store explicit workflow choice on selected tasks.

Deliverables:
- task metadata contract for:
  - `workflow_bank`
  - `workflow_id`
  - `workflow_family`
  - `team_profile`
  - `selection_origin`
- restore order:
  - explicit task binding
  - saved session state
  - heuristic prefetch
  - fallback template

Likely seams:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- current task metadata storage path already used for node/task state

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.TASK_BINDING.V1`
- `MARKER_167.STATS_WORKFLOW.RESTORE_ORDER.V1`

Tests:
- `tests/mcc/test_mcc_workflow_task_binding_contract.py`
- `tests/mcc/test_mcc_workflow_restore_priority.py`

### W3. Compact Stats upgrade

Goal:
- make compact `Stats` explicitly offer `WORKFLOW` for the selected task without becoming noisy.

Deliverables:
- compact fields for selected task:
  - explicit `WORKFLOW` action/prompt
  - workflow family
  - workflow bank
  - team profile
  - workflow/team statistics summary
  - selection origin
  - one MYCO hint line

Constraint:
- no dense bank picker in compact mode,
- compact mode remains glanceable.

Likely seam:
- `client/src/components/mcc/MiniStats.tsx`

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.UI_COMPACT_CONTEXT.V1`
- `MARKER_167.STATS_WORKFLOW.UI_COMPACT_MYCO_HINT.V1`

Tests:
- `tests/mcc/test_mcc_stats_workflow_compact_contract.py`

### W4. Expanded Stats selector

Goal:
- turn expanded `Stats` into the explicit workflow chooser.

Deliverables:
- sections:
  - current task
  - active workflow
  - bank tabs
  - workflow catalog list/cards
  - team/agent stats
  - MYCO rationale
- one main action:
  - `Select for task`

Constraint:
- use current MCC panel language,
- do not reintroduce `WorkflowToolbar`.

Likely seam:
- `client/src/components/mcc/MiniStats.tsx`

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.UI_EXPANDED_SELECTOR.V1`
- `MARKER_167.STATS_WORKFLOW.UI_BANK_TABS.V1`
- `MARKER_167.STATS_WORKFLOW.UI_SELECT_ACTION.V1`

Tests:
- `tests/mcc/test_mcc_stats_workflow_expanded_contract.py`

### W5. Workflow banks onboarding

Goal:
- expose real multi-bank workflow inventory incrementally.

Delivery order:
1. `core`
2. `saved`
3. `n8n`
4. `comfyui`
5. `imported`

Reason:
- this minimizes risk and lets the core selector ship before all ecosystem banks are normalized.

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.BANK_CORE.V1`
- `MARKER_167.STATS_WORKFLOW.BANK_SAVED.V1`
- `MARKER_167.STATS_WORKFLOW.BANK_N8N.V1`
- `MARKER_167.STATS_WORKFLOW.BANK_COMFYUI.V1`
- `MARKER_167.STATS_WORKFLOW.BANK_IMPORTED.V1`

Tests:
- `tests/mcc/test_mcc_workflow_bank_core.py`
- `tests/mcc/test_mcc_workflow_bank_saved.py`
- `tests/mcc/test_mcc_workflow_bank_external.py`

### W6. MYCO tool reinforcement

Goal:
- MYCO should proactively remind project/task architects which tools matter for the chosen workflow.

Deliverables:
- workflow-aware MYCO hint contract,
- role-aware tool reminder priority,
- hidden memory retrieval keyed by:
  - workflow family
  - bank
  - role
  - task context

Priority model:
1. workflow-required tools
2. role-required tools
3. project-context tools
4. favorite tools

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.MYCO_HINTS.V1`
- `MARKER_167.STATS_WORKFLOW.MYCO_TOOL_PRIORITY.V1`

Tests:
- `tests/mcc/test_mcc_workflow_myco_hint_contract.py`

### W7. Observability and diagnostics

Goal:
- make workflow selection inspectable in runtime and logs.

Deliverables:
- diagnostics fields for:
  - active workflow
  - bank
  - selection origin
  - binding state
  - heuristic vs user override
- optional badges in compact stats

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.DIAGNOSTICS.V1`
- `MARKER_167.STATS_WORKFLOW.BADGES.V1`

Tests:
- `tests/mcc/test_mcc_workflow_diagnostics_contract.py`

### W8. MYCO instruction corpus expansion

Goal:
- create dedicated MYCO instruction packs for workflow selection, workflow banks, and tool reinforcement scenarios.

Deliverables:
- new hidden instruction docs for:
  - workflow family guidance
  - bank-specific usage (`core/saved/n8n/comfyui/imported`)
  - role-specific workflow tool priorities
  - task architect vs project architect reminders
- reindex path for new docs into hidden MYCO retrieval corpus

Constraint:
- docs remain hidden retrieval material,
- MYCO guidance stays deterministic and supportive, not a second chooser.

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.MYCO_INSTRUCTIONS.V1`
- `MARKER_167.STATS_WORKFLOW.MYCO_INSTRUCTION_INDEX.V1`

Tests:
- `tests/mcc/test_mcc_workflow_myco_instruction_corpus_contract.py`

### W9. MYCO role motion assets and trigger pipeline

Goal:
- prepare role-specific MYCO motion assets for MCC triggers without breaking the current monochrome runtime shell.

Asset source paths:
- static role studies:
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A`
- motion source mp4:
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4`

Current motion inventory:
- architect:
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/arch1.mp4`
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/arch1-2.mp4`
- coder:
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/coder1.mp4`
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/coder2.mp4`
- researcher:
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/researcher1.mp4`
- scout:
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/scout.mp4`
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/scout2.mp4`
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/scout3.mp4`
- verifier:
  - `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A_mp4/verif1.mp4`

Build order:
1. source role mp4 audit
2. architect two-part assembly (`arch1` + `arch1-2`) into one master clip
3. `mp4 -> apng` conversion
4. UI self-review/probe
5. trigger mapping in MCC

Toolchain:
- MP4 -> APNG:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/media/mp4_to_apng_alpha.py`
- documentation source:
  - `/Users/danilagulin/Documents/CinemaFactory/docs/08_MEDIA_PIPELINE/MP4_TO_APNG_ALPHA_TOOL.md`
- UI review wrapper:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/player_lab_review.sh`
- UI probe spec:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/player_playground/e2e/dream_player_probe.spec.ts`

Trigger intent to support later:
- user selected model
- model/task started
- model/task completed
- role selected
- workflow entered
- MYCO proactive reply

Constraints:
- monochrome/house style remains authoritative
- role variants are allowed (`coder1/coder2`, `scout/scout2/scout3`)
- researcher/architect/verifier remain singleton by default

Markers to add later:
- `MARKER_167.STATS_WORKFLOW.MYCO_ROLE_ASSETS.V1`
- `MARKER_167.STATS_WORKFLOW.MYCO_APNG_PIPELINE.V1`
- `MARKER_167.STATS_WORKFLOW.MYCO_TRIGGER_ANIMATIONS.V1`

Tests:
- `tests/mcc/test_mcc_myco_role_asset_manifest_contract.py`
- `tests/mcc/test_mcc_myco_trigger_animation_contract.py`
Implementation notes:
- `docs/168_ph_videoplayer/PHASE_168_W9A_MYCO_MOTION_BATCH_BUILD_REPORT_2026-03-09.md`
- `docs/168_ph_videoplayer/PHASE_168_W9B_MYCO_MCC_PROBE_CONTRACT_2026-03-09.md`
- `docs/168_ph_videoplayer/PHASE_168_W9C_MYCO_MCC_PROBE_IMPL_REPORT_2026-03-09.md`
- `docs/168_ph_videoplayer/PHASE_168_W9D_MYCO_TRIGGER_STATE_MAPPING_2026-03-11.md`
- `docs/168_ph_videoplayer/PHASE_168_W9E_MYCO_RUNTIME_WIRING_REPORT_2026-03-11.md`
- `docs/168_ph_videoplayer/PHASE_168_W9F_RUNTIME_TRIGGER_SWITCHING_REPORT_2026-03-11.md`
- `docs/168_ph_videoplayer/PHASE_168_W9G_TEAM_A_INTEGRATION_AND_RUNTIME_POLISH_2026-03-11.md`
- `docs/contracts/myco_mcc_motion_probe_contract_v1.json`

W9 status:
- `W9.A` complete: batch builder + architect assembly + APNG pack
- `W9.B` complete: MCC-specific probe contract
- `W9.C` complete: first synthetic MCC probe runner verified on `top_avatar` and `mini_chat_compact`
- `W9.D` complete: trigger-state mapping manifest preserves top MYCO identity and routes role assets only to role-aware surfaces
- `W9.E` complete: narrow runtime wiring for `mini_chat_compact` and `mini_stats_compact` via role-safe asset registry, with top MYCO surfaces still system-owned
- `W9.F` trigger-aware runtime state switching and MCC probe verification for live role transitions
  status: complete
  scope:
  - compact `Stats` reacts to workflow/task runtime events for current task only
  - compact `Chat` keeps MYCO canonical in helper mode and role-specific in architect mode
- `W9.G` role-trigger runtime polish and live MCC transition verification
  status: complete
  scope:
  - static `team_A` becomes canonical role icon layer
  - APNG role assets remain transition-only
  - compact `Chat` and compact `Stats` stop mixing steady-state icon chrome with motion assets
- next: MYCO instruction corpus expansion + final role-trigger UI polish on top of new icons

## 5. Workflow Inventory To Verify Before IMPL

This inventory must be explicitly verified during W1/W5:

- `Mycelium-pipeline`
  - check whether it remains execution-only or also becomes a template-family surface
- `ralph_loop`
- `g3_critic_coder`
- `bmad_default`
- additional coding templates already in `data/templates/workflows`
- `n8n` convertible workflows
- `ComfyUI` convertible workflows

Open issue:
- if `mycelium_pipeline` remains MCP-only, it should still appear in the chooser via a normalized catalog entry instead of disappearing from the user-facing model.

## 6. Risks

### R1. Workflow term overload

Mitigation:
- enforce bank/family/id separation in contracts and UI labels.

### R2. Stats panel overload

Mitigation:
- compact mode stays read-first,
- heavy controls live only in expanded mode.

### R3. External bank inconsistency

Mitigation:
- ship bank support incrementally,
- normalize catalog contract before UI commits to details.

### R4. MYCO overreach

Mitigation:
- MYCO provides hints and tool reinforcement only,
- chooser authority remains in `Stats`.

## 7. Suggested User-Facing Wording

Expanded Stats sections should use plain English labels:

- `Active Workflow`
- `Workflow Bank`
- `Team`
- `Suggested By`
- `Select for Task`
- `Why This Workflow`

Avoid:
- overloaded internal terms,
- engine-specific jargon in first-line labels.

## 8. Test Policy

Before any runtime implementation:

1. add contract tests first,
2. then add narrow UI/backend implementation,
3. then verify MCC-only test slices,
4. only then widen to real runtime QA.

Minimum wave discipline:
- W1/W2 backend contracts first,
- W3/W4 UI after backend contract stabilizes,
- W6 MYCO after workflow contract exists.
- W8 MYCO instruction corpus after W6/W7 contracts exist.
- W9 MYCO motion assets after W8 instruction corpus and after new icons are normalized.

## 9. Recommended Immediate Next Step

Next protocol step after this report:

`WAIT GO`

If approved, the narrowest safe start is:
- W1 contract unification for workflow catalog,
- with tests first,
- no visual rewrite yet.
