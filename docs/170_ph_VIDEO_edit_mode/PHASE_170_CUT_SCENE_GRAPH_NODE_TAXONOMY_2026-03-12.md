# PHASE 170 - CUT Scene Graph Node Taxonomy
**Date:** 2026-03-12  
**Status:** frozen for architecture chain step A1  
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_V1_DRAFT_2026-03-09.md`

## Goal
Freeze the editorial node taxonomy for CUT Scene Graph so graph rendering, inspector behavior, and future intelligence overlays attach to stable semantic entities.

## Rules
- Every node type must have a clear inspection use case.
- Node types should describe editorial structure, not low-level worker internals.
- Intelligence systems may propose nodes, but they must land into this taxonomy or an approved additive extension.

## Required base fields for all nodes
- `node_id`
- `node_type`
- `label`
- `record_ref` or `null`
- `metadata` object

## V1 frozen node types
### `scene`
Meaning:
- primary narrative or editorial scene unit

Expected metadata:
- `timeline_lane` optional
- `scene_index` optional
- `summary` optional

Inspector questions:
- what scene is this
- which takes/assets belong here
- where does it sit in sequence

### `take`
Meaning:
- a specific take candidate within a scene

Expected metadata:
- `scene_id`
- `source_path` optional
- `quality_hint` optional
- `duration_sec` optional

Inspector questions:
- which scene does this belong to
- is this the active or alternate take
- what media record does it resolve to

### `asset`
Meaning:
- referenced media or support asset connected to scene/take structure

Expected metadata:
- `asset_kind` optional
- `source_path` optional
- `modality` optional

Inspector questions:
- what file or support material is linked here
- does it belong to one scene or many

### `note`
Meaning:
- human-authored editorial or director note

Expected metadata:
- `author` optional
- `note_kind` optional
- `target_node_id` optional

Inspector questions:
- what guidance or commentary applies here
- is this blocking, optional, or contextual

## Planned V2 node types
These are approved as future additive types, not required for the current shell slice.

### `beat`
Narrative or rhythm beat inside or across scenes.

### `transition`
Editorial transition anchor between scenes/takes.

### `marker_group`
Clustered time-marker aggregate for a scene or shot.

### `sync_anchor`
Hard-sync or recommended-sync anchor node.

### `semantic_anchor`
Semantically meaningful event/idea anchor suggested by intelligence overlays.

### `cam_anchor`
Context-aware memory anchor tied to marked moments.

### `alt_branch`
Alternative editorial branch or what-if path.

## Mapping rules to other CUT surfaces
- `storyboard` is shot-first and can resolve into `take` or `scene` nodes
- `timeline` is temporal and should link to `take` / `scene` identity, not replace them
- `selected shot` / inspector may focus a graph node inferred from active media path

## Anti-rules
- no compositor-FX node taxonomy here
- no raw worker job nodes in the editorial graph
- no opaque JEPA-only or PULSE-only node categories outside approved extensions

## Markers
- `MARKER_170.SCENE_GRAPH.NODE_TAXONOMY_FROZEN`
- `MARKER_170.SCENE_GRAPH.NODE_TYPES_V1`
- `MARKER_170.SCENE_GRAPH.NODE_TYPES_V2_GATE`
