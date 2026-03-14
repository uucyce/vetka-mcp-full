# PHASE 162 — P4.P4 Node/Role/Workflow Guidance Recon (2026-03-07)

Goal: make MYCO guidance context-complete on workflow level (no generic roadmap fallback when workflow/node-role context is available).

## Inputs reviewed
1. `client/src/components/mcc/MyceliumCommandCenter.tsx`
2. `client/src/components/mcc/MiniContext.tsx`
3. `client/src/components/mcc/MiniChat.tsx`
4. `src/api/routes/chat_routes.py`
5. `docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md`

## Findings (before P4.P4)
1. MiniChat sent only partial state (`nav_level`, drill flags, `node_kind`, `task_id`, `role`).
2. Missing fields for workflow-specific guidance:
- `graph_kind`
- `workflow_id`
- `team_profile`
- `workflow_family`
- node runtime details (`status/model/path`)
3. Backend next-action matrix used drill/nav state, but had limited role/family branching.
4. Top hint matrix in MCC had workflow-state branches, but role/family were not reflected in hints.
5. Instruction guide had capability/state matrix, but not exhaustive per node/role/workflow switch operations.

## Decision
Implement narrow P4.P4 upgrade:
1. Extend context contract MiniChat -> quick chat.
2. Extend quick-reply role/family matrix.
3. Extend top hint matrix with role/family cues.
4. Add detailed node/role/workflow matrix into MYCO guide.

## Markers (P4.P4)
1. `MARKER_162.P4.P4.MYCO.TOP_HINT_NODE_ROLE_WORKFLOW_MATRIX.V1`
2. `MARKER_162.P4.P4.MYCO.CHAT_REPLY_NODE_ROLE_WORKFLOW_MATRIX.V1`
3. `MARKER_162.P4.P4.MYCO.NODE_ROLE_WORKFLOW_NEXT_ACTIONS.V1`
4. `MARKER_162.P4.P4.MYCO.NODE_ROLE_WORKFLOW_GUIDE_MATRIX.V1`

GO token: `GO 162-P4.P4`
