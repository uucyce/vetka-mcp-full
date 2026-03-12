# PHASE 168 W9.C MYCO MCC Probe Impl Report

Status: implemented and verified
Date: 2026-03-09
Markers:
- MARKER_168.MYCO.MCC_PROBE.RUNNER.V1
- MARKER_168.MYCO.MCC_PROBE.SYNTHETIC_APP.V1
- MARKER_168.MYCO.MCC_PROBE.PLAYWRIGHT.V1

## Scope
Implement the first MCC-specific MYCO motion probe runner for synthetic UI surfaces before runtime trigger wiring.

Covered surfaces:
- `top_avatar`
- `mini_chat_compact`

Covered states:
- `speaking`
- `ready`

## Implementation
Added synthetic probe shell:
- `player_playground/src/MycoProbeApp.tsx`

Added probe mode entry:
- `player_playground/src/App.tsx`
- query contract: `?mode=myco&surface=<surface>&state=<state>`

Added Playwright probe:
- `player_playground/e2e/myco_mcc_probe.spec.ts`

Added runner:
- `scripts/myco_mcc_probe_review.sh`

Added runner contract test:
- `tests/phase168/test_myco_mcc_probe_runner_contract.py`

## Asset Used For Verification
- `artifacts/myco_motion/team_A/coder/coder2/coder_coder2.apng`

## Verification
Command 1:
```bash
scripts/myco_mcc_probe_review.sh \
  /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/artifacts/myco_motion/team_A/coder/coder2/coder_coder2.apng \
  top_avatar \
  speaking
```

Result 1:
- screenshot: `player_playground/output/myco_probe/latest-top_avatar-speaking.png`
- snapshot: `player_playground/output/myco_probe/latest-top_avatar-speaking.json`
- summary:
  - `clipRatio=0`
  - `textOverlapRatio=0`
  - `motionDominanceScore=0.3713`
  - `readabilityPass=true`

Command 2:
```bash
scripts/myco_mcc_probe_review.sh \
  /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/artifacts/myco_motion/team_A/coder/coder2/coder_coder2.apng \
  mini_chat_compact \
  ready
```

Result 2:
- screenshot: `player_playground/output/myco_probe/latest-mini_chat_compact-ready.png`
- snapshot: `player_playground/output/myco_probe/latest-mini_chat_compact-ready.json`
- summary:
  - `clipRatio=0`
  - `textOverlapRatio=0.0352`
  - `motionDominanceScore=0.4679`
  - `readabilityPass=true`

Pytest:
```bash
pytest -q tests/phase168/test_myco_motion_batch_builder_contract.py \
  tests/phase168/test_myco_mcc_motion_probe_contract.py \
  tests/phase168/test_myco_mcc_probe_runner_contract.py
```

Result:
- `5 passed`

## Narrow Fixes Made During Verify
The initial runner passed asset path as repo-relative while Playwright executed inside `player_playground`, causing `ENOENT` for the probe asset.

Fix:
- normalize probe asset path to absolute in `scripts/myco_mcc_probe_review.sh`

## Known Limitation
Two probe sessions started in parallel can race on the Playwright `webServer` startup for port `1424`.

Current policy:
- run probe sessions sequentially
- keep this as an explicit constraint until parallel probe orchestration is needed

## Conclusion
W9.C is complete for the first safe stage:
- synthetic MCC probe exists
- screenshot and JSON snapshot generation work
- asset fit/readability can now be verified before runtime MYCO trigger wiring
