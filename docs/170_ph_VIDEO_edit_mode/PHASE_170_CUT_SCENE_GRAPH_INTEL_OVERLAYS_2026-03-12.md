# PHASE 170 - CUT Scene Graph Intelligence Overlays Plan
**Date:** 2026-03-12  
**Status:** frozen for architecture chain step C2  
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_EDGE_TAXONOMY_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_LOD_CLUSTERING_PLAN_2026-03-12.md`

## Goal
Define how JEPA/V-JEPA/TTR/PULSE and related intelligence systems enrich Scene Graph without replacing structural editorial logic.

## Overlay principle
Structural graph first.
Intelligence second.
Overlays may propose, rank, annotate, and cluster, but they do not own the base graph.

## Overlay families
### JEPA / V-JEPA
Use for:
- semantic scene affinity
- visual motif recurrence
- candidate scene or take correspondence
- semantic anchor proposals

Expected outputs:
- `semantic_match` or future `visual_match` edges
- candidate `semantic_anchor` nodes
- confidence values and source attribution

### TTR / PULSE
Use for:
- rhythm alignment
- pacing continuity
- beat similarity
- transition support signals

Expected outputs:
- future `rhythm_match` edges
- beat/transition hints in inspector
- optional cluster support at medium/far zoom

### CAM-linked cognition
Use for:
- context-rich marker influence
- attention hints for scenes/takes carrying strong memory or note density

Expected outputs:
- future `cam_anchor` or `cam_context` relations
- inspector highlights, not graph spam

## Confidence policy
- every overlay edge or node must carry a source family and confidence band
- low-confidence overlays should be hidden or dimmed by default
- no low-confidence overlay should visually dominate structural flow

## Fallback policy
- if overlays fail, the scene graph still renders from structural contracts alone
- if one overlay family is unavailable, others remain additive but optional
- CUT launch must not block on JEPA/PULSE availability

## UI policy
- overlays should be filterable
- overlay-heavy views should be opt-in or zoom-sensitive
- inspector may show why an overlay exists and what data produced it

## Anti-rules
- no opaque model-only graph mutations without taxonomy mapping
- no overlay family may bypass node/edge taxonomy
- no intelligence edge should control default Sugiyama rank ordering

## Markers
- `MARKER_170.SCENE_GRAPH.INTEL_OVERLAYS_PLAN_FROZEN`
- `MARKER_170.SCENE_GRAPH.JEPA_VJEPA_OVERLAY_ROLE`
- `MARKER_170.SCENE_GRAPH.TTR_PULSE_OVERLAY_ROLE`
- `MARKER_170.SCENE_GRAPH.OVERLAY_CONFIDENCE_POLICY`
