# PHASE 168 — W9.G Team_A Integration and Runtime Polish

Date: 2026-03-11
Status: implemented
Protocol stage: IMPL NARROW -> VERIFY TEST

## Goal

Integrate the new `team_A` icon pack as the canonical static role layer for MCC while preserving APNG assets only for trigger transitions.

## Implemented

### 1. Static role layer switched to `team_A`

Source:
- `/Users/danilagulin/Documents/VETKA_Project/icons/myco_logos/team_A`

Normalized runtime assets:
- `client/src/assets/myco/team_A/architect_primary.png`
- `client/src/assets/myco/team_A/coder_coder1.png`
- `client/src/assets/myco/team_A/coder_coder2.png`
- `client/src/assets/myco/team_A/researcher_primary.png`
- `client/src/assets/myco/team_A/scout_scout1.png`
- `client/src/assets/myco/team_A/scout_scout2.png`
- `client/src/assets/myco/team_A/scout_scout3.png`
- `client/src/assets/myco/team_A/verifier_primary.png`

### 2. Motion assets kept for trigger pulses only

APNG pack remains in:
- `client/src/assets/myco/*.apng`

Policy:
- steady-state `Chat` / `Stats` role previews use static `team_A` icons
- runtime pulses use APNG variants only during short transitions

### 3. Resolver split formalized

File:
- `client/src/components/mcc/mycoRolePreview.ts`

Functions:
- `resolveRolePreviewAsset(...)` -> static icon
- `resolveRoleMotionAsset(...)` -> motion APNG

Markers:
- `MARKER_168.MYCO.RUNTIME.TEAM_A_STATIC_ROLE_ICONS.V1`
- `MARKER_168.MYCO.RUNTIME.TEAM_A_MOTION_ROLE_ICONS.V1`

## Result

This removes the previous ambiguity where role icons and role animations shared the same resolver path.

Current runtime contract:
- top helper stays MYCO
- architect/task chat uses static architect icon in steady state
- compact `Stats` uses static role icon in steady state
- live workflow/task/model transitions may briefly pulse APNG motion

## Verification

Tests:
- `tests/phase168/test_myco_runtime_role_preview_contract.py`
- `tests/phase168/test_myco_runtime_trigger_switching_contract.py`
