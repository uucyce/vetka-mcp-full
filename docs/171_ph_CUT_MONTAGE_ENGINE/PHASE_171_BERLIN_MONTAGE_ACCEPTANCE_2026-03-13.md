# Phase 171 Berlin Montage Acceptance

## Scope

Task:
- `tb_1773372827_8`

## Acceptance lane

- reserved port: `3211`
- sandbox: `codex54_cut_fixture_sandbox`
- fixture: `client/e2e/fixtures/cut_berlin_fixture_state.json`

## Assertions covered

- Berlin fixture loads only on the reserved fixture lane
- Punch remains visible in the `Music Track` bucket after hydration and reload
- project-state summary surfaces montage-ready cue information
- CUT status text reflects the Punch cue summary in a stable, browser-testable way

## Closure proof

Primary browser proof:
- `client/e2e/cut_berlin_fixture_smoke.spec.cjs`
- `client/e2e/cut_berlin_music_acceptance.spec.cjs`
- `client/e2e/cut_berlin_montage_fixture_smoke.spec.cjs`

Supporting backend proof:
- focused phase170 pytest around music contract/store/project-state summary
