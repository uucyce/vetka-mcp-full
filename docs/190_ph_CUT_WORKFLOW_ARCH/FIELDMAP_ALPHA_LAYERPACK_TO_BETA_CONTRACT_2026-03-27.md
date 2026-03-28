# Canonical Field Map: Alpha Layer Pack → Beta Manifest Contract

**Date:** 2026-03-27
**Task:** `tb_1774611697_1`
**Agent:** Beta (Media/Color Pipeline Architect)
**Status:** VERIFIED — Alpha output is wire-compatible with Beta ingest

## Summary

Alpha's `layer_space.json` output (from `scripts/photo_parallax_layer_extract.py`) is **directly compatible** with Beta's `LayerManifest.from_dict()` and `ingest_layer_space()`. All camelCase JSON fields have matching fallback parsers in Beta code. Role normalization (kebab-case → underscore) works via `_ROLE_NORMALIZE`. No shim required.

---

## 1. Top-Level Manifest Fields

| Alpha JSON key | Beta Python field | Parse path | Notes |
|---|---|---|---|
| `contract_version` | `LayerManifest.contract_version` | `data.get("contract_version")` | Direct match |
| `sampleId` | `LayerManifest.sample_id` | `data.get("sampleId")` | Direct match |
| `sampleId` | `LayerManifest.manifest_id` | `data.get("sampleId")` | Same key, dual use |
| `source.path` | `LayerManifest.source_path` | `source.get("path")` | Nested in `source` object |
| `source.width` | `LayerManifest.source_width` | `source.get("width")` | Nested in `source` object |
| `source.height` | `LayerManifest.source_height` | `source.get("height")` | Nested in `source` object |
| `layers` | `LayerManifest.layers` | `data.get("layers")` | Array → `SemanticLayer.from_dict()` each |
| `space` | `LayerManifest.camera` | `data.get("space")` or `data.get("camera")` | Both keys accepted |
| `provenance` | `LayerManifest.provenance` | `data.get("provenance")` | Direct match, passthrough dict |
| _(absent)_ | `LayerManifest.depth_path` | `data.get("depth_path")` | Beta-only. Defaults to `""` |
| _(absent)_ | `LayerManifest.background_rgba_path` | Detected from filesystem | Beta looks for `background_rgba.png` sibling |

### Format Detection

Beta auto-detects via `"contract_version" in data and "layers" in data` → routes to `ingest_layer_space()`.

---

## 2. Layer Fields (`layers[]`)

| Alpha JSON key | Beta Python field | Parse path | Notes |
|---|---|---|---|
| `id` | `SemanticLayer.layer_id` | `d.get("layer_id") or d.get("id")` | Fallback accepts `id` |
| `role` | `SemanticLayer.role` | `normalize_role(d.get("role"))` | Kebab→underscore via `_ROLE_NORMALIZE` |
| `label` | `SemanticLayer.label` | `d.get("label")` | Direct match |
| `order` | `SemanticLayer.order` | `d.get("order") or d.get("index")` | Direct match |
| `depthPriority` | `SemanticLayer.depth_priority` | `d.get("depthPriority") or d.get("depth_priority")` | camelCase accepted |
| `z` | `SemanticLayer.z` | `d.get("z")` | Direct match |
| `visible` | `SemanticLayer.visible` | `d.get("visible")` | Direct match |
| `rgba` | `SemanticLayer.rgba_path` | `d.get("rgba_path") or d.get("rgba")` | Relative path, resolved by ingest |
| `mask` | `SemanticLayer.mask_path` | `d.get("mask_path") or d.get("mask")` | Relative path, resolved by ingest |
| `depth` | `SemanticLayer.depth_path` | `d.get("depth_path") or d.get("depth")` | Relative path, resolved by ingest |
| `coverage` | `SemanticLayer.coverage` | `d.get("coverage") or d.get("plateCoverage")` | Direct match |
| `parallaxStrength` | `SemanticLayer.parallax_strength` | `d.get("parallax_strength") or d.get("parallaxStrength")` | camelCase accepted |
| `motionDamping` | `SemanticLayer.motion_damping` | `d.get("motion_damping") or d.get("motionDamping")` | camelCase accepted |
| _(absent)_ | `SemanticLayer.clean_path` | `d.get("clean_path") or d.get("clean")` | Beta-only. Defaults to `""` |
| _(absent)_ | `SemanticLayer.clean_variant` | `d.get("clean_variant") or d.get("cleanVariant")` | Beta-only. Defaults to `""` |

### Role Normalization Map

| Alpha (kebab-case) | Beta (underscore) |
|---|---|
| `foreground-subject` | `foreground_subject` |
| `secondary-subject` | `secondary_subject` |
| `environment-mid` | `mid_environment` |
| `background-far` | `background` |
| `special-clean` | `special_clean` |

---

## 3. Camera/Space Fields (`space`)

| Alpha JSON key | Beta Python field | Parse path | Notes |
|---|---|---|---|
| `focalLengthMm` | `CameraContract.focal_length_mm` | `d.get("focalLengthMm") or d.get("focal_length_mm")` | camelCase accepted |
| `filmWidthMm` | `CameraContract.film_width_mm` | `d.get("filmWidthMm") or d.get("film_width_mm")` | camelCase accepted |
| `zNear` | `CameraContract.z_near` | `d.get("zNear") or d.get("z_near")` | camelCase accepted |
| `zFar` | `CameraContract.z_far` | `d.get("zFar") or d.get("z_far")` | camelCase accepted |
| `motionType` | `CameraContract.motion_type` | `d.get("motionType") or d.get("motion_type")` | camelCase accepted. Value `"portrait-base"` further normalized by CameraGeometry bridge |
| `durationSec` | `CameraContract.duration_sec` | `d.get("durationSec") or d.get("duration_sec")` | camelCase accepted |
| `travelXPct` | `CameraContract.travel_x_pct` | `d.get("travelXPct") or d.get("travel_x_pct")` | camelCase accepted |
| `travelYPct` | `CameraContract.travel_y_pct` | `d.get("travelYPct") or d.get("travel_y_pct")` | camelCase accepted |
| `zoom` | `CameraContract.zoom` | `d.get("zoom")` | Direct match |
| `overscanPct` | `CameraContract.overscan_pct` | `d.get("overscanPct") or d.get("overscan_pct")` | camelCase accepted |

---

## 4. Fields in Alpha Prototype-Only (NOT in canonical output)

These exist in `prototype.json` sidecar and are **not** part of `layer_space.json`. Beta does NOT read them.

| Prototype field | Purpose | Beta equivalent |
|---|---|---|
| `depthSource` | Depth model metadata | `provenance.depth_backend` (canonical) |
| `holeFill` | LaMa inpaint method | No canonical equivalent |
| `layers[].depthBand` | Raw depth value range | No canonical equivalent |
| `layers[].distanceHint` | near/mid/far | Derivable from `z` + `role` |
| `layers[].holeFilled` | Whether LaMa applied | No canonical equivalent |
| `layers[].maskMethod` | Mask generation method | No canonical equivalent |
| `qualityCaveats` | Known extraction limits | No canonical equivalent |

---

## 5. Beta-Only Fields (No Alpha Source)

These fields exist in Beta's dataclasses but Alpha does not emit them. All default safely.

| Beta field | Default | When populated |
|---|---|---|
| `SemanticLayer.clean_path` | `""` | When explicit clean plate is available (future: per-layer LaMa) |
| `SemanticLayer.clean_variant` | `""` | Semantic label for clean variant (e.g. "no-vehicle") |
| `LayerManifest.depth_path` | `""` | Global depth map path (separate from per-layer depth) |
| `LayerManifest.background_rgba_path` | `""` | Auto-detected from `background_rgba.png` sibling file |

### Potential Enhancement: `holefill_rgba` → `clean_path`

Alpha's extractor produces `*_holefill_rgba.png` for the background layer (LaMa inpainting). This is semantically equivalent to Beta's `clean_path` concept. Currently it is NOT referenced in `layer_space.json`.

**Recommendation:** Alpha should add an optional `clean` field to background layers in `layer_space.json`:
```json
{
  "id": "layer_plate_04_background_city",
  "role": "background-far",
  "clean": "layer_plate_04_background_city_holefill_rgba.png"
}
```
Beta's parser already handles this via `d.get("clean")` → `clean_path`.

---

## 6. Compatibility Verdict

| Check | Result |
|---|---|
| Alpha `layer_space.json` → Beta `ingest_layer_space()` | PASS — no conversion needed |
| Alpha `layer_space.json` → Beta `LayerManifest.from_dict()` | PASS — auto-detects format |
| Alpha `layer_space.json` → Beta `POST /cut/layers/import` | PASS — endpoint calls `ingest_manifest()` |
| Role normalization (kebab→underscore) | PASS — all 5 roles mapped |
| camelCase → snake_case field parsing | PASS — all fields have dual-key fallback |
| Gamma can read manifest via `GET /cut/layers/manifest` | PASS — returns `manifest.to_dict()` |
| No information loss from Alpha canonical output | PASS — all 12 layer + 10 space + provenance fields preserved |
| `holefill_rgba` → `clean_path` bridge | GAP — see recommendation above |

### No Shim Required

Alpha's canonical output and Beta's parser are wire-compatible. The only gap is the `holefill_rgba` → `clean_path` enhancement, which is optional and non-breaking. A follow-up task can be created if needed.

---

## 7. Reference Files

| File | Purpose |
|---|---|
| `src/services/cut_layer_manifest.py` | Beta canonical parser (SemanticLayer, CameraContract, LayerManifest) |
| `scripts/photo_parallax_layer_extract.py` | Alpha extractor (emits `layer_space.json`) |
| `docs/180_photo-to-parallax/PARALLAX_LAYERPACK_HANDOFF_2026-03-27.md` | Alpha handoff doc |
| `src/services/cut_parallax_bridge.py` | CameraContract → CameraGeometry bridge |
| `src/api/routes/cut_routes.py` | `/cut/layers/import` + `/cut/layers/manifest` endpoints |
