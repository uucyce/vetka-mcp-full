# PHASE 162 — P4.P4 Node/Role/Workflow Guidance Impl Report (2026-03-07)

Status: implemented

## Implemented

### 1) Extended MiniContext payload contract
File: `client/src/components/mcc/MiniContext.tsx`

Added optional fields:
- `workflowId`
- `teamProfile`
- `workflowFamily`

### 2) MCC now computes workflow family and passes it into context payload
File: `client/src/components/mcc/MyceliumCommandCenter.tsx`

Added:
- `inferWorkflowFamily(...)`
- `selectedTaskMeta` extraction from task list
- `miniContextPayload` enrichment with:
  - `workflowId`
  - `teamProfile`
  - `workflowFamily`

Top hint matrix extension:
- marker: `MARKER_162.P4.P4.MYCO.TOP_HINT_NODE_ROLE_WORKFLOW_MATRIX.V1`
- workflow-open hints now include role-specific and family-specific actions.

### 3) MiniChat guidance matrix and quick context were expanded
File: `client/src/components/mcc/MiniChat.tsx`

Guidance matrix extension:
- marker: `MARKER_162.P4.P4.MYCO.CHAT_REPLY_NODE_ROLE_WORKFLOW_MATRIX.V1`
- role-specific branches (`architect`, `coder`, `verifier/eval`) and workflow-family hints.

Quick context extension sent to backend:
- `graph_kind`
- `workflow_id`
- `team_profile`
- `workflow_family`
- `label`
- `status`
- `model`
- `path`

### 4) Backend quick-reply matrix expanded by node/role/workflow
File: `src/api/routes/chat_routes.py`

Added:
- fallback workflow-family inference from `team_profile/workflow_id`
- family hint labels (`dragons/titans/g3/ralph_loop/...`)
- role-aware next actions for workflow-open states
- marker: `MARKER_162.P4.P4.MYCO.NODE_ROLE_WORKFLOW_NEXT_ACTIONS.V1`
- retrieval state query enrichment now includes:
  - `graph_kind`
  - `workflow_family`
  - `workflow_id`
  - `role`

### 5) Guide deepening (node/subnode/agent/role/workflow operations)
File: `docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md`

Added section:
- `16) Node/Role/Workflow detailed guidance matrix`
- marker: `MARKER_162.P4.P4.MYCO.NODE_ROLE_WORKFLOW_GUIDE_MATRIX.V1`

## Files changed
1. `client/src/components/mcc/MiniContext.tsx`
2. `client/src/components/mcc/MyceliumCommandCenter.tsx`
3. `client/src/components/mcc/MiniChat.tsx`
4. `src/api/routes/chat_routes.py`
5. `docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md`
6. `docs/162_ph_MCC_MYCO_HELPER/PHASE_162_P2_MYCO_TOPBAR_TITLE_ROADMAP_2026-03-06.md`
7. `docs/162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P4_NODE_ROLE_WORKFLOW_RECON_REPORT_2026-03-07.md`
8. `docs/162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P4_NODE_ROLE_WORKFLOW_IMPL_REPORT_2026-03-07.md`

