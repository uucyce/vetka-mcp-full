# PHASE 168 W9.E MYCO Runtime Wiring Report

Date: 2026-03-11
Protocol stage: IMPL NARROW -> VERIFY TEST

## 1. Objective

Wire MYCO role motion assets into narrow MCC runtime surfaces without replacing the top-level system MYCO helper.

Target surfaces:
- `mini_chat_compact`
- `mini_stats_compact`

Protected system surfaces:
- `top_avatar`
- `top_hint`
- expanded MYCO helper surfaces remain system-owned in this wave

## 2. Implemented Seams

### 2.1 Runtime asset registry

Added:
- `client/src/components/mcc/mycoRolePreview.ts`

This registry:
- imports synced APNG role assets from `client/src/assets/myco/`
- keeps system MYCO assets separate from role assets
- resolves deterministic variants for parallel roles:
  - `coder1/coder2`
  - `scout1/scout2/scout3`

Key exports:
- `resolveMiniChatCompactAvatar(...)`
- `resolveMiniStatsCompactRoleAsset(...)`
- `resolveSystemMycoAsset(...)`

## 3. Narrow Runtime Wiring

### 3.1 Compact MiniChat

File:
- `client/src/components/mcc/MiniChat.tsx`

Marker:
- `MARKER_168.MYCO.RUNTIME.MINI_CHAT_COMPACT_ROLE_PREVIEW.V1`

Behavior:
- compact MiniChat may show role-aware MYCO preview asset
- expanded MiniChat still uses system MYCO asset
- top helper remains untouched

### 3.2 Compact MiniStats

File:
- `client/src/components/mcc/MiniStats.tsx`

Marker:
- `MARKER_168.MYCO.RUNTIME.MINI_STATS_COMPACT_ROLE_PREVIEW.V1`

Behavior:
- compact Stats shows a role preview asset next to the `WORKFLOW` action
- the preview is derived from current task/workflow context
- if no role-safe asset is available, Stats remains text-first

## 4. Asset Source Policy

Built artifacts were mirrored into client-safe assets:
- `client/src/assets/myco/architect_primary.apng`
- `client/src/assets/myco/coder_coder1.apng`
- `client/src/assets/myco/coder_coder2.apng`
- `client/src/assets/myco/researcher_primary.apng`
- `client/src/assets/myco/scout_scout1.apng`
- `client/src/assets/myco/scout_scout2.apng`
- `client/src/assets/myco/scout_scout3.apng`
- `client/src/assets/myco/verifier_primary.apng`

Reason:
- Vite/Tauri runtime should consume repo-bundled assets, not raw files from `artifacts/`

## 5. Bug Fixed During W9.E

File:
- `client/src/components/mcc/MiniStats.tsx`

Fix:
- changed `setStatsMode('overview')` -> `setStatsMode('ops')`

Reason:
- `StatsPanelMode` only allows `ops | diagnostics`
- `overview` was a stale enum value and broke TypeScript validation

## 6. Verification

Tests:
- `tests/phase168/test_myco_runtime_role_preview_contract.py`
- `tests/phase168/test_myco_motion_batch_builder_contract.py`
- `tests/phase168/test_myco_mcc_motion_probe_contract.py`
- `tests/phase168/test_myco_mcc_probe_runner_contract.py`
- `tests/phase168/test_myco_trigger_state_mapping_contract.py`

Observed result in this wave:
- `11 passed, 1 warning`

## 7. What W9.E Deliberately Does Not Do

W9.E does not yet:
- drive live trigger switching by task state changes
- replace top MYCO with role avatars
- animate expanded Stats workflow surfaces
- bind role assets into every MCC panel

Those remain for the next wave.

## 8. Next Step

Proceed to:
- `W9.F` trigger-aware runtime state switching
- MCC probe verification for live role transitions across compact surfaces
