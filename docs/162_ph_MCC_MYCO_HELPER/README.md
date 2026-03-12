# Phase 162 — MCC MYCO Helper

## Navigation
1. Architecture base:
- `PHASE_162_MYCO_HELPER_ARCH_PLAN_2026-03-05.md`

2. P0 contracts:
- `MYCO_CONTEXT_PAYLOAD_CONTRACT_V1.md`
- `MYCO_CHAT_ROLE_CONTRACT_V1.md`
- `MYCO_HELP_RULES_LIBRARY_V1.md`
- `MYCO_ICON_STYLE_GUIDE_V1.md`
- `MYCO_TEST_MATRIX_V1.md`
- `PHASE_162_P0_CONTRACTS_REPORT_2026-03-06.md`

3. P1 implementation:
- `PHASE_162_P1_PASSIVE_MODE_REPORT_2026-03-06.md`
4. P2 roadmap + recon + implementation:
- `PHASE_162_P2_MYCO_TOPBAR_TITLE_ROADMAP_2026-03-06.md`
- `PHASE_162_P2_RECON_AND_IMPL_REPORT_2026-03-06.md`

5. P3.P0 recon:
- `PHASE_162_P3_P0_HIDDEN_MEMORY_RECON_REPORT_2026-03-06.md`
6. P3.P1 implementation:
- `PHASE_162_P3_P1_HIDDEN_MEMORY_IMPL_REPORT_2026-03-06.md`
7. P3.P2 implementation:
- `PHASE_162_P3_P2_ORCHESTRATION_MEMORY_REPORT_2026-03-06.md`
8. P3.P3 implementation:
- `PHASE_162_P3_P3_RAG_SPLIT_ORCHESTRATION_REPORT_2026-03-06.md`
- `MYCO_RAG_CORE_V1.md`
- `MYCO_RAG_AGENT_ROLES_V1.md`
- `MYCO_RAG_USER_PLAYBOOK_V1.md`
9. P3.P4 recon:
- `PHASE_162_P3_P4_RETRIEVAL_QUALITY_RECON_REPORT_2026-03-06.md`
10. P3.P4 implementation:
- `PHASE_162_P3_P4_RETRIEVAL_QUALITY_IMPL_REPORT_2026-03-06.md`
11. P4.P1 recon:
- `PHASE_162_P4_P1_PROACTIVE_CHAT_RECON_REPORT_2026-03-06.md`
12. P4.P1 implementation:
- `PHASE_162_P4_P1_PROACTIVE_CHAT_IMPL_REPORT_2026-03-06.md`
13. P4.P2 recon:
- `PHASE_162_P4_P2_PROACTIVE_GUIDANCE_RECON_REPORT_2026-03-07.md`
14. P4.P2 implementation:
- `PHASE_162_P4_P2_PROACTIVE_GUIDANCE_IMPL_REPORT_2026-03-07.md`
15. P4.P3 recon:
- `PHASE_162_P4_P3_MYCELIUM_CAPABILITY_RAG_RECON_REPORT_2026-03-07.md`
16. P4.P3 implementation:
- `PHASE_162_P4_P3_MYCELIUM_CAPABILITY_RAG_IMPL_REPORT_2026-03-07.md`

## Current status
- `P0` complete.
- `P1` complete (passive-mode skeleton + store mode + chat role wiring).
- `P2` complete (top-row MYCO UI + title simplification + chat/dock behavior polish).
- `P3.P0` complete (hidden memory recon + marker lock for narrow implementation).
- `P3.P1` complete (hidden memory bridge + quick chat fastpath + ENGRAM payload contract).
- `P3.P2` complete (multitask+digest orchestration snapshot in MYCO payload + ENGRAM runtime fact persist).
- `P3.P3` complete (RAG-ready instruction split + enriched multitask contract for helper replies).
- `P3.P4` complete (retrieval bridge + glossary alias expansion + quality gate + coverage tests).
- `P4.P1` complete (proactive context-switch MYCO replies in compact/expanded chat + compact regression cleanup).
- `P4.P2` complete (state-aware post-drill proactive guidance in top hint + chat matrix).
- `P4.P3` complete (MYCELIUM capability matrix + state-keyed RAG enrichment + drill-state context bridge).

## Root P2 contract (fixed)
1. Add `MYCO` button (icon + label) in MCC top tab-row.
2. Click toggles helper mode: `off -> passive -> active`.
3. While MYCO replies, icon temporarily switches to animated `APNG/WebP` state.
4. Window title reduced to `MYCELIUM`.
5. Chat minimized/restore path keeps MYCO presence and speaking animation.

17. P4.P4 recon:
- `PHASE_162_P4_P4_NODE_ROLE_WORKFLOW_RECON_REPORT_2026-03-07.md`
18. P4.P4 implementation:
- `PHASE_162_P4_P4_NODE_ROLE_WORKFLOW_IMPL_REPORT_2026-03-07.md`

Current phase status:
- `P4.P4` complete (node/role/workflow-family guidance matrix, enriched quick context, stronger state-keyed MYCO hints).

19. P4.P5 recon:
- `PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_RECON_REPORT_2026-03-07.md`
20. P4.P5 implementation:
- `PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_IMPL_REPORT_2026-03-07.md`

Current phase status:
- `P4.P5` complete (runtime scenario lock tests for MYCO quick-reply matrix).
