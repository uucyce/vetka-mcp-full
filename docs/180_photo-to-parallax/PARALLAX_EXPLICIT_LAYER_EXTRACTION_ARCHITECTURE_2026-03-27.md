# Parallax Explicit Layer Extraction Architecture

Date: `2026-03-27`
Owner: `Codex / Commander`
Reference: `DaVinci Resolve Depth Map` as the mental model for depth-assisted isolation, but the output target is `explicit scene layers`, not a single graded depth matte.

## Canonical Contract Note

This document is the architecture pivot and product rationale.

It is **not** the canonical wire-format spec.

The canonical manifest contract is now:

- `docs/190_ph_CUT_WORKFLOW_ARCH/HANDOFF_LAYERFX_MANIFEST_CONTRACT_2026-03-27.md`

Source-of-truth rules:

- `layer_space.json` is canonical
- `contract_version = "1.0.0"`
- JSON/TS on disk uses `camelCase`
- Python normalizes to `snake_case` on ingest
- `plate_export_manifest.json` remains a legacy bridge only

## Executive Summary

`hover-politsia` confirmed the current limit of the proxy-plate path:

- the real depth map is useful and should remain a first-class asset;
- the visual failure is not primarily depth quality;
- the failure comes from routing scene pixels into synthetic plates via a mix of:
  - depth remap,
  - box priors,
  - residual complement logic,
  - post-blur cleanup.

This produces artifacts such as:

- subject plate contains nearby non-subject geometry;
- background plate behaves like a wide residual slab;
- layers collide or move like cardboard cutouts;
- masks look box-shaped even when the depth map is locally correct.

The correct architectural pivot is:

1. extract explicit semantic scene layers first;
2. assign each layer a stable distance-from-camera / depth band;
3. fill holes behind removed foreground objects;
4. render camera motion on top of those layers.

This is much closer to the authored-layer workflow used in Pasha's AE project.

## Current Truth

The following statements are now considered canonical for `hover-politsia`:

- The `depth map` is already product-useful on its own:
  - depth-aware grading,
  - title placement behind a subject,
  - depth masks as an effect input in CUT.
- The current exporter path improved materially after `P2/P3` and the follow-up semantic fixes:
  - `background-far` is no longer a frozen full-frame fallback;
  - subject/background overlap near the walker was reduced;
  - micro alpha halos were reduced by post-blur alpha flooring.
- However, the preview is still not final-acceptance quality:
  - the vehicle still behaves like a static object inside a plate;
  - the walker is still not semantically separated well enough;
  - the workflow is still `proxy plate synthesis`, not `real scene decomposition`.

## Problem Statement

The current `plateStack -> buildProxyMaps -> buildPlateCompositeMaps` path asks one system to do too many different jobs:

- depth remap,
- subject isolation,
- midground routing,
- background recovery,
- edge softening,
- renderer readiness.

That coupling is the reason one local fix often creates another local artifact.

The new architecture must split these concerns.

## Target Architecture

### 1. Layer Extraction Stage

Input:

- source RGB image
- real depth map
- object/instance detections
- optional user guidance

Output:

- explicit `scene layers`
- each layer has:
  - semantic identity
  - `rgba`
  - `alpha`
  - `depth band` or representative `z`
  - local depth stats
  - source provenance

Minimum useful layers for a still-photo scene:

- `foreground_subject`
- `secondary_subject`
- `mid_environment`
- `background`

Optional:

- `special_clean` variants per removed hero object
- extra object layers when semantic segmentation is good enough

### 2. Hole Fill Stage

When a foreground layer is removed, the newly revealed area behind it must be filled in the farther layer.

For MVP this does not require perfect generative inpainting.

Acceptable first strategies:

- clean plate from existing source-specific assets if available;
- local patch expansion from neighboring farther pixels;
- guided fill using the background layer's depth band and semantic mask;
- special-clean layer exports for hero removals.

### 3. Layer Manifest Stage

The renderer and CUT integration should stop reading ad hoc proxy assumptions and read one explicit contract.

Architecture-level example only:

```json
{
  "contract_version": "1.0.0",
  "sampleId": "hover-politsia",
  "source": {
    "path": "/abs/path/source.jpg",
    "width": 1920,
    "height": 1080
  },
  "layers": [
    {
      "id": "fg_01",
      "role": "foreground-subject",
      "label": "Vehicle",
      "order": 2,
      "depthPriority": 0.78,
      "z": 0.5,
      "visible": true,
      "rgba": "fg_01_rgba.png",
      "mask": "fg_01_mask.png",
      "depth": "fg_01_depth.png",
      "coverage": 0.3,
      "parallaxStrength": 1.3,
      "motionDamping": 1.0
    }
  ],
  "space": {
    "focalLengthMm": 50,
    "filmWidthMm": 36,
    "zNear": 0.72,
    "zFar": 1.85,
    "motionType": "orbit",
    "durationSec": 4.0,
    "travelXPct": 3.0,
    "travelYPct": 0.0,
    "zoom": 1.0,
    "overscanPct": 20.0
  }
}
```

For exact field semantics, normalization rules, and clip attachment model, use the canonical Beta spec above, not this architecture document.

### 4. Camera Render Stage

The renderer should receive explicit layers and not infer semantics from residual masks.

Renderer responsibilities:

- camera motion
- occlusion ordering
- disocclusion handling
- edge treatment
- layer-level motion tuning

Renderer should not decide:

- what belongs to a person versus a pole;
- what the background semantic region is;
- whether a plate is "close enough" to be a subject.

## Why This Is Better

- Separates `depth` from `semantics`.
- Turns the current system from `proxy slab generator` into a proper scene-layer pipeline.
- Matches the actual user goal:
  - get separate layers,
  - control camera freely,
  - stop doing hand-built roto/infill in AE when the machine can prepare it.
- Makes CUT integration cleaner because CUT wants effect inputs and layer assets, not fragile App.tsx-only heuristics.

## MVP Acceptance

The new architecture should be considered working for `hover-politsia` when all of the following are true:

1. Vehicle, walker, mid-environment, and background are exported as explicit layers.
2. The walker layer no longer drags the nearby pole with it as one semantic unit.
3. The background layer is hole-filled behind removed foreground objects well enough for camera motion.
4. The resulting preview no longer looks like moving box masks or residual slabs.
5. The same layer manifest is readable by:
   - parallax preview/render,
   - CUT depth/layer effects,
   - QA acceptance harness.

## Agent Lanes

These lanes are intentionally chosen to reduce file conflict and avoid "fake parallelism".

### Beta Lane

Mission:

- integrate explicit depth/layer assets into CUT as first-class effect data, building on the existing `DaVinci Depth Map` effect family work.

Ownership:

- `src/services/cut_effects_engine.py`
- `src/services/cut_depth_service.py`
- CUT clip/effect schemas
- CUT architecture docs

Deliverables:

- explicit layer manifest contract for CUT ingestion;
- effect-side support for layer/depth assets as reusable inputs;
- backend endpoint/service contract for importing generated layer packs.

### Gamma Lane

Mission:

- design and wire CUT UI for depth/layer workflows using NLE patterns, not playground-style debug layout.

Ownership:

- CUT frontend panels/components
- inspectors
- effect UI wiring
- visual workflow for layer/depth preview

Deliverables:

- layer stack / layer inspector UI;
- depth preview UI inspired by `DaVinci Resolve Depth Map`;
- clean user-facing controls for toggling layer visibility, order, and effect inputs.

### Alpha Lane

Mission:

- prototype offline explicit layer extraction and hole-fill for `hover-politsia` without touching the live `App.tsx` routing lane.

Ownership:

- `scripts/`
- export contract helpers
- docs/forensics/output artifacts

Deliverables:

- offline layer extraction prototype;
- one explicit layer pack for `hover-politsia`;
- hole-filled background proof of concept;
- comparison artifacts against the current proxy-plate export.

### Commander Lane

Mission:

- keep the live exporter stable enough for iteration while supervising the pivot to explicit layers.

Ownership:

- `photo_parallax_playground/src/App.tsx`
- current preview/export behavior
- acceptance and integration decisions

## Immediate Next Step

Do not spend more cycles trying to make synthetic proxy plates indistinguishable from authored layers.

Use the current exporter improvements as a bridge and move the project to:

- `explicit semantic layer extraction`
- `hole-filled farther layer reconstruction`
- `shared layer manifest`

That is the path most likely to free Pasha from manual AE labor instead of merely making the proxy preview slightly less broken.
