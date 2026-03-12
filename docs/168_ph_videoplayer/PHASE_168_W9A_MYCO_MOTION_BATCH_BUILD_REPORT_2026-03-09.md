# PHASE 168 — W9.A MYCO Motion Batch Build Report

Date: 2026-03-09
Status: implemented and verified
Protocol stage: IMPL NARROW -> VERIFY TEST

Related docs:
- `docs/168_ph_videoplayer/PHASE_168_MYCO_MOTION_ASSET_PIPELINE_RECON_2026-03-09.md`
- `docs/168_ph_videoplayer/MYCO_MOTION_DEV_UI_TOOL_V1.md`
- `docs/167_MCC_workflow/PHASE_167_EXTENDED_STATS_WORKFLOW_PANEL_ROADMAP_2026-03-08.md`

## 1. What was added

New batch builder:
- `scripts/media/build_myco_motion_assets.py`

New contract test:
- `tests/phase168/test_myco_motion_batch_builder_contract.py`

Updated media tools guide:
- `scripts/media/README.md`

## 2. Baseline preset frozen

- `mode=luma`
- `fps=8`
- `luma-threshold=52`
- `alpha-blur=0.8`

## 3. Verified outputs

Batch manifest:
- `artifacts/myco_motion/team_A/batch_manifest.json`

Built assets:
- `artifacts/myco_motion/team_A/architect/primary/architect_master.mp4`
- `artifacts/myco_motion/team_A/architect/primary/architect_primary.apng`
- `artifacts/myco_motion/team_A/coder/coder1/coder_coder1.apng`
- `artifacts/myco_motion/team_A/coder/coder2/coder_coder2.apng`
- `artifacts/myco_motion/team_A/researcher/primary/researcher_primary.apng`
- `artifacts/myco_motion/team_A/scout/scout1/scout_scout1.apng`
- `artifacts/myco_motion/team_A/scout/scout2/scout_scout2.apng`
- `artifacts/myco_motion/team_A/scout/scout3/scout_scout3.apng`
- `artifacts/myco_motion/team_A/verifier/primary/verifier_primary.apng`

## 4. Architect path

`architect` is no longer a manual two-file exception at use time.

It is now assembled first:
- `arch1.mp4`
- `arch1-2.mp4`

Then converted from the assembled master clip.

## 5. Verify results

Automated verify completed:
- `pytest -q tests/phase168/test_myco_motion_batch_builder_contract.py`
- result: `2 passed`

Runtime verify completed:
- dry run manifest built successfully
- full batch build completed successfully
- manifest confirms `8` built assets
- manifest marker:
  - `MARKER_168.MYCO.MOTION.BATCH_BUILD.V1`

## 6. What W9.A does not do yet

W9.A does **not** yet:
- wire assets into MCC runtime surfaces,
- define trigger-state switching rules,
- validate APNG behavior inside compact MCC panels,
- perform MCC-specific motion readability checks.

Those remain the next phase.

## 7. Next correct step

Proceed to W9.B:
- define MCC-specific MYCO probe
- target compact surfaces and trigger states
- validate readability, dominance, and layout stability before runtime integration
