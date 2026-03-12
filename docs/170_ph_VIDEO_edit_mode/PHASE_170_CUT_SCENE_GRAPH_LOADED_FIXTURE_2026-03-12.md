# PHASE 170 CUT Scene Graph Loaded Fixture (2026-03-12)

## Purpose

Provide a deterministic loaded-state fixture for `/cut` so visual review and browser smoke tests no longer stop on the empty `No graph nodes available.` state.

## Files

- Fixture payload: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/e2e/fixtures/cutSceneGraphLoadedFixture.cjs`
- Smoke test: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/e2e/cut_scene_graph_loaded_review.spec.cjs`

## Fixture contents

The fixture intentionally includes the minimum useful editorial graph state:
- one selected timeline clip: `clip_a`
- one selected scene: `scene_01`
- `scene_graph_view` with structural and intelligence edges
- `dag_projection` ready for `DAGView`
- focused inspector nodes
- media-native render hints with poster preview and waveform sync badge
- thumbnail, transcript, waveform, sync, time-marker bundles

## Expected visible outcomes in NLE

### MARKER_170.LOADED_FIXTURE.NLE_READY
The main editor should show:
- `Graph Ready`
- `Scene Graph peer pane ready`
- `Scene Graph Surface`

### MARKER_170.LOADED_FIXTURE.CARD_READY
The pane should show:
- `Compact Graph Card`
- poster image for `Take A`
- sync pill `sync waveform`
- bucket text `bucket selected_shot`

### MARKER_170.LOADED_FIXTURE.CROSSLINK_READY
The pane should show:
- `clip-linked graph nodes: 3`
- `active graph node: Take A · take`
- `graph buckets: primary_structural, selected_shot, intel_overlay`

## Why this matters

This fixture is the first stable path for screenshot and smoke coverage of the promoted Scene Graph pane with real payload, without depending on live bootstrap jobs or external media processing.
