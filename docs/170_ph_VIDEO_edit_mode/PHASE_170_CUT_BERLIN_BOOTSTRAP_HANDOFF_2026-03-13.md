# Phase 170 CUT Berlin Bootstrap Handoff

## Scope

Task lanes:
- `tb_1773382600_243`
- `tb_1773382600_244`
- `tb_1773382600_245`

Sandbox:
- hint: `codex54_cut_fixture_sandbox`
- reserved port: `3211`
- browser lane: isolated only, no shared Playwright live runner

## What is in place

- manifest/profile lane: `berlin_fixture_v1` is wired through bootstrap and project-state
- source fixture: [client/e2e/fixtures/cut_berlin_fixture_state.json](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/e2e/fixtures/cut_berlin_fixture_state.json)
- smoke lane: [client/e2e/cut_berlin_fixture_smoke.spec.cjs](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/e2e/cut_berlin_fixture_smoke.spec.cjs)
- music acceptance lane: [client/e2e/cut_berlin_music_acceptance.spec.cjs](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/e2e/cut_berlin_music_acceptance.spec.cjs)

## Source-browser polish

Allowed UI touch point:
- [client/src/components/cut/CutEditorLayout.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/cut/CutEditorLayout.tsx)

Current source-browser behavior for the Berlin fixture:
- groups hydrated assets into stable buckets: `Video Clips`, `Boards`, `Music Track`, fallback `Audio Assets` / `Still Images`
- marks the Punch track as `Primary music`
- keeps `Audio sync lane` visible when the item is backed by the `audio_sync` timeline lane
- exposes stable selectors for bucket and item assertions so browser coverage does not depend on fragile text-only queries

## Acceptance coverage

Reserved-port coverage on `3211` currently proves:
- the Berlin fixture loads only inside the Codex54 sandbox lane
- source-browser hydration surfaces the Punch file name
- the Punch entry remains in the `Music Track` bucket after reload
- the Punch entry keeps its `Primary music` and `Audio sync lane` badges after hydration

## Remaining CUT gaps

- no dedicated runtime contract yet for music phrasing or beat-grid output
- `CutStandalone` still owns broader hydration wiring and remains intentionally out of scope for this lane
- fixture acceptance proves browser identity and visibility, not editorial playback correctness
- app packaging and dmg work remain blocked by shared frontend TypeScript failures outside the Berlin fixture lane

## Recommended next owner moves

1. keep using the reserved-port `3211` browser lane for any future Berlin fixture assertions
2. add backend contract coverage once `cut_music_sync_result_v1` exists
3. wire a dedicated music-sync worker before attempting timeline-level rhythmic edit automation
