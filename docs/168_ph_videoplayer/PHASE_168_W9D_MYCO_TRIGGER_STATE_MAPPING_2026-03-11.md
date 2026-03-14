# PHASE 168 W9.D MYCO Trigger-State Mapping

Status: implemented and verified
Date: 2026-03-11
Markers:
- `MARKER_168.MYCO.TRIGGER_STATE.MAPPING.V1`
- `MARKER_168.MYCO.TRIGGER_STATE.ROLE_PLACEMENT.V1`
- `MARKER_168.MYCO.TRIGGER_STATE.VARIANT_ASSIGN.V1`

## Goal
Freeze runtime-safe trigger/state mapping before live MCC animation wiring.

Primary architectural decision:
- top MYCO surfaces remain **system-helper only**;
- role assets do **not** replace top MYCO identity;
- role assets are routed only into role-aware task/workflow panels.

This answers the current design question directly:
- `coder/scout/researcher/architect/verifier` shown in probe were **examples for fit/readability**;
- they are **not** the final replacement for MYCO in the top bar.

## Output
Generated mapping manifest:
- `artifacts/myco_motion/team_A/trigger_state_mapping.json`

Source inputs:
- `artifacts/myco_motion/team_A/batch_manifest.json`
- current generic MYCO runtime assets in `client/src/assets/myco/`

Builder:
- `scripts/media/build_myco_trigger_state_mapping.py`

## Surface Policy

### System-helper only
These stay on generic MYCO assets:
- `top_avatar`
- `top_hint`

Channel:
- `system_myco`

Allowed states:
- `idle`
- `ready`
- `speaking`

### Role-preview surfaces
These are allowed to show role-specific assets with fallback to generic MYCO:
- `mini_chat_compact`
- `mini_chat_expanded`
- `mini_stats_compact`
- `mini_stats_expanded`

Channel:
- `role_preview`

Fallback:
- `system_myco`

## Variant Assignment
Singleton roles:
- `architect -> primary`
- `researcher -> primary`
- `verifier -> primary`

Parallel roles:
- `coder -> coder1, coder2`
- `scout -> scout1, scout2, scout3`

Assignment rule:
- ordinal cycle by visible runtime order
- no random selection
- same ordinal keeps same variant while runtime slice is stable

## Trigger Routing
Important routes frozen in manifest:

- `idle/ready/speaking`
  - targets: `top_avatar`, `top_hint`
  - channel: `system_myco`

- `workflow_selected`
  - targets: `mini_stats_compact`, `mini_stats_expanded`
  - channel: `role_preview`
  - role source: `workflow_lead_role`

- `model_selected`
  - targets: `mini_chat_compact`, `mini_chat_expanded`
  - channel: `role_preview`
  - role source: `selected_role`

- `task_started/task_completed/task_failed`
  - targets: `mini_stats_compact`, `mini_stats_expanded`
  - channel: `role_preview`
  - role source: `active_running_role`

- `parallel_role_active`
  - targets: `mini_chat_expanded`, `mini_stats_expanded`
  - channel: `role_preview`
  - role source: `parallel_role_set`

## Why This Mapping Is Correct
This preserves MYCO identity where the product already has a stable helper language:
- top bar helper remains recognizable,
- helper/hint channel does not flicker between agent personas,
- task/workflow panels get the role richness where it is contextually justified.

This also avoids the wrong visual implication that:
- selecting a coder means MYCO itself becomes coder.

Instead:
- MYCO remains advisor/orchestrator,
- role assets appear in role-aware execution surfaces.

## Verification
Contract test:
```bash
pytest -q tests/phase168/test_myco_trigger_state_mapping_contract.py
```

Result:
- `3 passed`

## Next Step
- `W9.E`: first narrow runtime wiring using this manifest
- target surfaces first:
  - `mini_chat_compact`
  - `mini_stats_compact`
- top MYCO surfaces remain untouched in the first runtime pass
