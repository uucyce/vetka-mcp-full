# PHASE 171 Montage State Contract Seed (2026-03-13)

## Purpose

Seed the first persisted montage state so Phase 171 can promote cues and markers into durable editorial decisions.

## Contract

- Schema: `cut_montage_state_v1`
- File: `docs/contracts/cut_montage_state_v1.schema.json`
- Runtime persistence: `cut_runtime/state/montage_state.latest.json`

## Persisted fields

- `revision`
- `source_bundle_revisions`
- `accepted_decisions[]`
- `rejected_decisions[]`
- `updated_at`
- `updated_by`

Each decision carries:
- stable `decision_id`
- `source_family`
- `cue_provenance_ids`
- `confidence`
- `score`
- `editorial_intent`
- `timeline_id`
- `lane_id`
- `anchor_sec` / `start_sec` / `end_sec`
- `source_bundle_id`
- `source_bundle_revision`
- `author`

## Project-state surface

`/api/cut/project-state` now returns:
- `montage_state`
- `montage_ready`

This keeps montage persistence additive. Existing CUT lanes continue to work when montage state is absent.

## Validation rules

- accepted bucket only allows `status=accepted`
- rejected bucket only allows `status=rejected`
- unique `decision_id` per bucket
- numeric fields are bounded and non-negative
- timestamps must be ISO datetime strings

## Markers

- `MARKER_171.MONTAGE_ENGINE.STATE_CONTRACT`
- `MARKER_171.MONTAGE_ENGINE.PROJECT_STATE_SURFACE`
