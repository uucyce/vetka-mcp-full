# PHASE 170 cut_scene_graph_v1 Draft
**Date:** 2026-03-09  
**Status:** first draft  
**Scope:** lightweight scene graph state for `VETKA CUT`

## Goal
Define a first scene-graph contract that can coexist with timeline-first editing.

`cut_scene_graph_v1` should not try to be a full compositor graph.
It should be a structural/narrative graph for scenes, takes, and semantic edges.

## Marker
- `MARKER_170.CONTRACT.CUT_SCENE_GRAPH_V1`

## Why separate from timeline
Timeline answers:
1. what plays when,
2. on which lane,
3. what is selected now.

Scene graph answers:
1. what scenes exist,
2. how they relate,
3. which takes belong to each scene,
4. what semantic links connect them.

## Required fields
1. `schema_version`
2. `project_id`
3. `graph_id`
4. `revision`
5. `nodes`
6. `edges`
7. `updated_at`

## Node types (V1)
1. `scene`
2. `take`
3. `asset`
4. `note`

## Edge types (V1)
1. `contains`
2. `follows`
3. `semantic_match`
4. `alt_take`
5. `references`

## Proposed shape
```json
{
  "schema_version": "cut_scene_graph_v1",
  "project_id": "cut_demo_1234abcd",
  "graph_id": "main",
  "revision": 1,
  "nodes": [
    {
      "node_id": "scene_01",
      "node_type": "scene",
      "label": "Opening scene",
      "record_ref": null,
      "metadata": {
        "timeline_lane": "video_main"
      }
    },
    {
      "node_id": "take_01_a",
      "node_type": "take",
      "label": "Take A",
      "record_ref": "record_001",
      "metadata": {
        "scene_id": "scene_01"
      }
    }
  ],
  "edges": [
    {
      "edge_id": "edge_001",
      "edge_type": "contains",
      "source": "scene_01",
      "target": "take_01_a",
      "weight": 1.0
    }
  ],
  "updated_at": "2026-03-09T12:00:00Z"
}
```

## Mapping notes
1. `record_ref` should map to `vetka_montage_sheet_v1.records[*].record_id`
2. scene nodes should align with `scene_node_id` semantics from media contracts
3. semantic edges may be derived from `media_chunks_v1` and semantic search, but should remain lightweight in V1

## V1 non-goals
1. no node-based effects compositor
2. no procedural execution graph
3. no per-edge rich embeddings stored inline
4. no deep CAM history baked into graph nodes

## Follow-up
After this draft:
1. freeze schema
2. define relation to `cut_timeline_state_v1`
3. define scene-assembly pipeline that produces initial graph
