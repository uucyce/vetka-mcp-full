# PHASE 164 — P2/P3 Recon From MYCO Scenario Author Checklist (2026-03-08)

Status: `RECON+markers` complete.  
Protocol step: `REPORT` (waiting explicit `GO` before `IMPL NARROW`).

## Input
Reference document reviewed:
- [MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/163_ph_myco_VETKA_help/MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md)

Current phase baseline:
- [PHASE_164_RECON_MARKERS_REPORT_2026-03-07.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/164_MYCO_ARH_MCC/PHASE_164_RECON_MARKERS_REPORT_2026-03-07.md)
- [PHASE_164_P1_IMPL_REPORT_2026-03-08.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/164_MYCO_ARH_MCC/PHASE_164_P1_IMPL_REPORT_2026-03-08.md)

## Recon Summary
The checklist from phase 163 is valid as a quality gate for phase 164 and reveals 4 concrete P2/P3 deltas.

### Already covered (164-P0/P1)
1. UI windows/control inventory baseline exists (P0 docs).
2. Shared role-aware instruction core exists (P1 backend bind for MYCO + Architect quick path).
3. Project/task architect scope binding exists.
4. Context-tools hint injection exists.

### Gaps still open
1. Full deterministic trigger matrix per control is not yet formalized as executable contract.
2. Recovery branch matrix is still partial (auth/quota/provider-down/disabled-mode/etc.).
3. Anti-noise/silence/dedupe rules exist in parts but not locked as unified gate policy.
4. Quality gate is not fully encoded as one end-to-end test contract tied to scenario author checklist.

## Marker Set (new)
1. `MARKER_164.P2.FULL_TRIGGER_MATRIX_FROM_UI_ATLAS.V1`
2. `MARKER_164.P2.RECOVERY_BRANCHES_MATRIX.V1`
3. `MARKER_164.P3.ANTI_NOISE_SILENCE_DEDUPE_GATE.V1`
4. `MARKER_164.P3.QUALITY_GATE_AUTOTEST_BIND.V1`

## Evidence Alignment (163 checklist -> 164 scope)
1. `Working phase 5: deterministic trigger matrix` -> 164 P2 trigger contracts.
2. `Working phase 6: anti-noise and silence rules` -> 164 P3 gate policy.
3. `Working phase 7: recovery branches` -> 164 P2 recovery matrix.
4. `Quality gate section` -> 164 P3 test bind.

## Narrow Plan (pending GO)
### 164-P2
1. Build deterministic trigger matrix doc from current MCC UI atlas and runtime context keys.
2. Add recovery branch matrix for MYCO+architect quick path:
- zero keys vs configured keys
- provider auth error
- quota/rate limit
- provider timeout/down
- disabled feature/mode
- roadmap/workflow context mismatch
3. Add targeted contract tests for trigger mapping and recovery routing.

### 164-P3
1. Normalize anti-noise rules into one policy table:
- typing silence
- stale hint purge on context switch
- solved setup no-repeat
- no duplicate hint for same state key
2. Bind policy to deterministic checks (tests + marker lock).
3. Add quality-gate checklist test to ensure docs/contracts/code stay aligned.

## Verification Plan (pending GO)
1. `tests/test_phase164_p2_trigger_matrix_contract.py`
2. `tests/test_phase164_p2_recovery_matrix_contract.py`
3. `tests/test_phase164_p3_anti_noise_gate_contract.py`
4. `tests/test_phase164_p3_quality_gate_bind.py`

## Risk Notes
1. Avoid mixing broad UI rewrites with P2/P3; keep changes narrow and contract-first.
2. Preserve existing MYCO/architect behavior while tightening trigger/recovery and anti-noise logic.
3. No hardcoded scenario shortcuts; all mappings must come from normalized context keys.

## Gate
`REPORT` delivered.

Next protocol step: `WAIT GO`.
