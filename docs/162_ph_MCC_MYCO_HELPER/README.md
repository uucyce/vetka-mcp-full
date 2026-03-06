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

## Current status
- `P0` complete.
- `P1` complete (passive-mode skeleton + store mode + chat role wiring).
- `P2` in progress (top-row MYCO UI + title simplification + chat/dock behavior polish).

## Root P2 contract (fixed)
1. Add `MYCO` button (icon + label) in MCC top tab-row.
2. Click toggles helper mode: `off -> passive -> active`.
3. While MYCO replies, icon temporarily switches to animated `APNG/WebP` state.
4. Window title reduced to `MYCELIUM`.
5. Chat minimized/restore path keeps MYCO presence and speaking animation.
