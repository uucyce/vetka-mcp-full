# Parallax Explicit Layer Pack — Handoff

Date: `2026-03-27`
Task: `tb_1774609710_1`
Agent: Alpha (Engine Architect)
Commit: `41d497a4` on `claude/cut-engine`

## 1. Canonical Output Paths

```
photo_parallax_playground/output/layer_packs/hover-politsia/
├── layer_manifest.json                              (2.6K)  contract v2.0.0
├── layer_plate_01_vehicle_rgba.png                  (5.1M)  foreground-subject
├── layer_plate_01_vehicle_alpha.png                 (25K)
├── layer_plate_01_vehicle_depth.png                 (207K)
├── layer_plate_02_walker_rgba.png                   (5.1M)  secondary-subject
├── layer_plate_02_walker_alpha.png                  (11K)
├── layer_plate_02_walker_depth.png                  (189K)
├── layer_plate_03_street_steam_rgba.png             (5.1M)  environment-mid
├── layer_plate_03_street_steam_alpha.png            (25K)
├── layer_plate_03_street_steam_depth.png            (209K)
├── layer_plate_04_background_city_rgba.png          (5.1M)  background-far (source RGB)
├── layer_plate_04_background_city_alpha.png         (39K)
├── layer_plate_04_background_city_depth.png         (225K)
└── layer_plate_04_background_city_holefill_rgba.png (5.2M)  background-far (LaMa hole-fill)
```

Script: `scripts/photo_parallax_layer_extract.py`
Run: `python3 scripts/photo_parallax_layer_extract.py --sample hover-politsia`

## 2. Manifest Shape (v2.0.0)

```json
{
  "contract_version": "2.0.0",
  "sample_id": "hover-politsia",
  "source": { "path": "...", "width": 2560, "height": 1440 },
  "depth_source": {
    "kind": "real_depth_raster",
    "model": "depth-pro",
    "polarity": "white_near_black_far"
  },
  "layers": [
    {
      "id": "layer_plate_01_vehicle",
      "role": "foreground-subject",
      "semantic_label": "vehicle",
      "z": 26,
      "depth_band": [0.005, 0.056],
      "distance_hint": "near",
      "rgba": "layer_plate_01_vehicle_rgba.png",
      "alpha": "layer_plate_01_vehicle_alpha.png",
      "depth": "layer_plate_01_vehicle_depth.png",
      "hole_filled": false,
      "coverage": 0.3438
    }
  ],
  "hole_fill": {
    "method": "lama_inpaint",
    "source": ".../lama_plate_bakeoff/depth-pro/hover-politsia/clean_plate.png"
  }
}
```

Each layer has: `id`, `role`, `semantic_label`, `z`, `depth_band`, `distance_hint`, `rgba`, `alpha`, `depth`, `hole_filled`, `coverage`. Background adds `holefill_rgba`.

## 3. What Worked in Hole-Fill

**LaMa inpainted clean_plate** as background source is the correct approach:
- The `lama_plate_bakeoff` pipeline already produced a full-frame background with the vehicle removed
- Compositing LaMa RGB with complement alpha gives a usable hole-filled background layer
- The renderer composites foreground layers on top — so the holes in background alpha (where vehicle/walker are) are correct: those pixels are occluded by foreground

**Subject mask from bakeoff** as primary vehicle alpha (0.85 weight) blended with depth band (0.35 weight) gives much better isolation than depth alone. The bakeoff pipeline already solved the hard segmentation problem.

**Depth-band sampling from actual bbox regions** instead of z→normalised mapping is critical. The 16-bit depth map has values compressed into [0, 0.08] range — any assumed linear mapping fails.

## 4. What Still Breaks

### 4.1 Vehicle layer captures nearby building geometry
The subject_mask from bakeoff is good but not pixel-perfect. Left-side building geometry appears at ~0.35 alpha weight. Fixable with a tighter mask (SAM refinement or manual trim).

### 4.2 Walker has no instance mask — bbox+depth only
The walker layer is a feathered rectangle, not a semantic silhouette. Depth within the bbox selects the walker but also the pole and pavement behind. Needs a dedicated instance mask (SAM/GroundedSAM on the walker bbox).

### 4.3 Depth polarity documented wrong
`depth_master_16.png` actually has **low values = near, high values = far** (metric distance). The doc says "bright=near" which applies to the 8-bit preview PNG but not the 16-bit master. The extractor works around this by sampling actual values, but consumers must not assume polarity from the doc string.

### 4.4 Steam layer overlap
The street steam layer (environment-mid) and vehicle layer share similar depth bands [0.005, 0.056] vs [0.005, 0.053]. The steam under the vehicle is captured by both layers. Not visually broken at this stage but would produce double-compositing if both layers are rendered at full opacity.

## 5. Recommended Next Task

**Instance mask generation for walker + vehicle refinement.**

The single highest-leverage improvement: run SAM (Segment Anything) on each plate's bbox to get pixel-accurate instance masks. This replaces:
- Vehicle: subject_mask bakeoff blend → SAM-refined silhouette
- Walker: bbox+depth rectangle → SAM instance contour

This is the bridge between "depth-band proxy" and "authored layer" quality. The depth and bbox give SAM a strong prompt; SAM gives back a clean contour.

## 6. Comparison Summary: Proxy Plates vs Explicit Layers

| Dimension | Proxy (App.tsx) | Explicit (layer_extract.py) |
|-----------|----------------|----------------------------|
| Resolution | 640px proxy | 2560x1440 full-res |
| Vehicle mask | depth-band + box | subject_mask bakeoff + depth |
| Walker mask | depth-band + box (1.6% cov) | depth-band + box (7.3% cov) |
| Background | complement residual | complement + LaMa hole-fill |
| Hole-fill | none | LaMa inpaint |
| Manifest | v1.0.0 (plate-keyed) | v2.0.0 (layer-keyed) |
| App.tsx dependency | yes | none (offline script) |
