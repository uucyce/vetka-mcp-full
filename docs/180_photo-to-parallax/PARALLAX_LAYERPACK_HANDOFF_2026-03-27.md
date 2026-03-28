# Parallax Explicit Layer Pack — Handoff

Date: `2026-03-27`
Tasks: `tb_1774609710_1` (prototype), `tb_1774612826_1` (canonical compliance)
Agent: Alpha (Engine Architect)
Commits: `41d497a4` (prototype), `28ed5837` (canonical) on `claude/cut-engine`

## 1. What Is Canonical

The extractor emits **`layer_space.json`** — Beta's canonical manifest v1.0.0.

Spec source of truth: `docs/190_ph_CUT_WORKFLOW_ARCH/HANDOFF_LAYERFX_MANIFEST_CONTRACT_2026-03-27.md`

This output is directly ingestible by Beta's `/cut/layers/import` endpoint and `SemanticLayer.from_dict()` without manual conversion.

### Canonical Manifest Path

```
photo_parallax_playground/output/layer_packs/hover-politsia/layer_space.json
```

### Canonical File Tree

```
photo_parallax_playground/output/layer_packs/hover-politsia/
├── layer_space.json                                 (canonical v1.0.0)
├── prototype.json                                   (sidecar — NOT canonical)
├── layer_plate_01_vehicle_rgba.png                  (5.1M)  foreground-subject
├── layer_plate_01_vehicle_mask.png                  (25K)
├── layer_plate_01_vehicle_depth.png                 (207K)
├── layer_plate_02_walker_rgba.png                   (5.1M)  secondary-subject
├── layer_plate_02_walker_mask.png                   (11K)
├── layer_plate_02_walker_depth.png                  (189K)
├── layer_plate_03_street_steam_rgba.png             (5.1M)  environment-mid
├── layer_plate_03_street_steam_mask.png             (25K)
├── layer_plate_03_street_steam_depth.png            (209K)
├── layer_plate_04_background_city_rgba.png          (5.1M)  background-far
├── layer_plate_04_background_city_mask.png          (39K)
├── layer_plate_04_background_city_depth.png         (225K)
└── layer_plate_04_background_city_holefill_rgba.png (5.2M)  LaMa hole-fill
```

Script: `scripts/photo_parallax_layer_extract.py`
Run: `python3 scripts/photo_parallax_layer_extract.py --sample hover-politsia`

### Canonical Manifest Shape (v1.0.0)

```json
{
  "contract_version": "1.0.0",
  "sampleId": "hover-politsia",
  "source": { "path": "...", "width": 2560, "height": 1440 },
  "layers": [
    {
      "id": "layer_plate_01_vehicle",
      "role": "foreground-subject",
      "label": "vehicle",
      "order": 3,
      "depthPriority": 0.86,
      "z": 26,
      "visible": true,
      "rgba": "layer_plate_01_vehicle_rgba.png",
      "mask": "layer_plate_01_vehicle_mask.png",
      "depth": "layer_plate_01_vehicle_depth.png",
      "coverage": 0.3438,
      "parallaxStrength": 1.6,
      "motionDamping": 1.0
    }
  ],
  "space": {
    "focalLengthMm": 50,
    "filmWidthMm": 36,
    "zNear": 0.72,
    "zFar": 1.85,
    "motionType": "portrait-base",
    "durationSec": 4,
    "travelXPct": 5.3,
    "travelYPct": 1.89,
    "zoom": 1.058,
    "overscanPct": 26.07
  },
  "provenance": {
    "depth_backend": "depth-pro",
    "grouping_backend": "qwen-vl"
  }
}
```

All JSON fields camelCase. Roles kebab-case on disk. Python normalises on read via `SemanticLayer.from_dict()`.

## 2. What Is Prototype-Only (Sidecar)

The file `prototype.json` contains non-canonical metadata for debugging. It is **NOT** part of the Beta spec and should **NOT** be read by CUT pipeline code.

Contents:
- `depthSource` — depth model, polarity, path
- `holeFill` — method (lama_inpaint), source path
- `layers[].depthBand` — actual depth value range per layer
- `layers[].distanceHint` — near/mid/far
- `layers[].holeFilled` — whether LaMa background was applied
- `layers[].maskMethod` — how alpha was computed (subject_mask_bakeoff+depth / depth_band+bbox / complement)
- `qualityCaveats` — known extraction quality limits

## 3. Quality Caveats (Prototype-Only)

These are recorded in `prototype.json` and do NOT affect canonical format compliance:

1. **Walker mask is bbox+depth only** — feathered rectangle, not semantic silhouette. Needs SAM instance segmentation for pixel-accurate contour.
2. **Vehicle mask has building geometry spill** — subject_mask from bakeoff bleeds into left-side building at ~0.35 alpha. Needs SAM refinement or manual trim.
3. **Hole-fill is LaMa-only** — works for hover-politsia (vehicle removal), but complex multi-object occlusions would need generative inpaint.
4. **Steam/vehicle depth band overlap** — both occupy [0.005, 0.05x] range. Potential double-compositing at full opacity.

## 4. What Worked

- **LaMa clean_plate** as hole-filled background — already available from bakeoff pipeline
- **Subject mask from bakeoff** (0.85 weight) + depth band (0.35 weight) for vehicle isolation
- **Depth-band sampling from actual bbox regions** — the 16-bit depth map is compressed into [0, 0.08] range, linear z→depth mapping fails
- **Camera params from plate_layout.json** populate `space{}` block directly — no manual entry

## 5. Integration Path

Beta's pipeline is ready to consume this output:

```
layer_space.json → POST /cut/layers/import → SemanticLayer.from_dict() → LayerManifest
                                             CameraContract → CameraGeometry bridge
```

No manual translation needed. The extractor output is a drop-in input for Beta's import endpoint.
