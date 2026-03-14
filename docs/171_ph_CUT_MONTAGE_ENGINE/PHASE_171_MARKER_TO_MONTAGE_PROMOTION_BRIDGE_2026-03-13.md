# PHASE 171 Marker To Montage Promotion Bridge (2026-03-13)

## Purpose

Connect Phase 170 time markers to Phase 171 montage state so editorial decisions can be persisted instead of living only as marker bundles.

## Route

- `POST /api/cut/montage/promote-marker`

## Input

- `sandbox_root`
- `project_id`
- `marker_id`
- `author`
- optional `decision_id`
- optional `lane_id`
- `decision_status = accepted | rejected`
- optional `editorial_intent`

## Behavior

1. load CUT project
2. load `time_marker_bundle`
3. resolve target marker by `marker_id`
4. build montage decision from marker timing/provenance
5. upsert into `cut_montage_state_v1`
6. carry forward `time_marker_bundle` revision into `source_bundle_revisions`

## Output

- `decision`
- `montage_state`
- `edit_event`

## Rules

- marker promotions use `source_family=marker`
- provenance is rooted in `cue_provenance_ids=[marker_id]`
- accepted/rejected buckets are mutually exclusive by `decision_id`
- default editorial intent is derived from marker kind when not supplied

## Markers

- `MARKER_171.MONTAGE_ENGINE.MARKER_PROMOTION_BRIDGE`
- `MARKER_171.MONTAGE_ENGINE.TIME_MARKER_PROVENANCE`
