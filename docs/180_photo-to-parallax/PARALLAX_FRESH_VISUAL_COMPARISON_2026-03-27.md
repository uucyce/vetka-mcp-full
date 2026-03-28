# Parallax Fresh Visual Comparison: hover-politsia

Date: `2026-03-27`
Task: `tb_1774594729_1`
Agent: Alpha (Engine Architect, cross-domain assist)

## 1. Scope

Compare the **fresh authoritative render** (2026-03-27, content-addressed) against the March 12 visual baseline. Classify issues into: already fixed by fresh rerender, still visually weak, compositor/export fix candidates.

Fresh bundle:
- Render: `output/render_preview_multiplate_qwen_gated_camera_contract_fresh_20260327/hover-politsia/`
- Inspection: `output/video_inspection/hover-politsia-camera-contract-fresh-20260327/`

Baseline reference: `output/custom_renders/depth-anything-v2-small/drone-portrait_*`

---

## 2. What the Fresh Render Got Right (Fixed by Rerender)

| Issue | Status | Evidence |
|-------|--------|----------|
| Stale artifact provenance | **FIXED** | SHA256 differs from old mp4 (430KB vs 263KB); content-addressed hashes captured |
| Fog-only-motion hypothesis | **DISPROVEN** | motion_energy.png shows SUV as dominant motion source, not just fog |
| Depth quality | **GOOD** | rigid_slab_risk: low, weak_background_separation_risk: low, mean_per_frame_std: 63.44 |
| Camera safety | **PASS** | Auto-bumped overscan 19% → 26.07%; no risky plates flagged |
| Multi-plate routing | **WORKING** | 3 visible plates rendered across 9 depth bands, 3 transitions |

The fresh bundle substantially weakens the old fog-only-motion hypothesis. Parallax motion is real, driven by the SUV body shifting in the frame. Depth maps are stable across all 20 sampled frames.

---

## 3. What Is Still Visually Weak

### 3.1 CRITICAL: plate_04 ("background city") — Zero Coverage, No Files

**This is the primary visual quality issue.**

| Field | Layout value | Manifest value |
|-------|-------------|----------------|
| plateCoverage | 0.9216 (92% of frame) | 0 |
| files | expected rgba/mask/depth | `{}` (empty) |
| PNGs on disk | expected 3 files | **NONE** |
| highestDisocclusionRisk | 32.08% | — |

The background-far plate covers 92% of the frame according to the layout, but the export pipeline produces **nothing** for it.

**Root cause in `App.tsx:buildPlateCompositeMaps()`:**
```typescript
const renderablePlates = plateStack.filter(
  (plate) => plate.visible && plate.role !== "background-far" && plate.role !== "special-clean"
);
```

Background-far is explicitly excluded from per-plate rasterization. Instead, it gets an implicit complement:
```typescript
const backgroundAlpha = clamp(1 - unionAlpha * 0.94, 0.06, 1);
```

This means the background:
- Has **no per-pixel depth-aware compositing** — it's just "whatever the foreground doesn't claim"
- Gets exported as a single `background_rgba.png` (top-level, not plate-keyed)
- In the renderer, placed as a **static base layer with ZERO parallax motion**

**Visual consequence:** The viewer sees foreground objects (SUV, walker, steam) sliding over a frozen background. The old 2-layer renderer applied empirical motion to BOTH layers (`bg_factor_x=0.28` for orbit). The new renderer treats background as inert.

### 3.2 Hard Alpha Edges on Plate PNGs

`buildPlateCompositeMaps()` does NOT apply any blur to exported plate masks. The `manual.blurPx` parameter exists but is only consumed in `buildProxyMaps()` for the preview overlay — not in the export path.

Combined with depth-band alpha (not semantic segmentation), this produces:
- Aliased depth-boundary edges visible when plates are parallax-displaced
- Hard cutout appearance on foreground subject edges

### 3.3 Environment-Mid Plate (steam) is Nearly Invisible

| Metric | Value |
|--------|-------|
| Layout plateCoverage | 0.1232 (12.3%) |
| Manifest coverage | 0.0159 (1.6%) |
| Ratio | 8x less than expected |

The `environment-mid` alpha formula uses square-law compression: `roleAlpha = atmospheric * atmospheric`. Anything with a weak midground/depth signal rounds to near-zero. The steam plate renders as thin wisps rather than a volumetric atmospheric layer.

### 3.4 No Inter-Plate Blur / Transition Softening

The downstream ffmpeg renderer applies `gblur=sigma=0.8` to the depth LUT mask per band, but this is a binary depth-range mask blur — not an alpha edge blur. The plate RGBA's own alpha edges remain hard.

---

## 4. Comparison: Old Baseline vs Current Pipeline

| Dimension | Old (visual success) | Current (technical pass, visual weak) |
|-----------|---------------------|--------------------------------------|
| Layers | 2 (overscan bg + subject RGBA) | N plates × 3 depth bands + static bg |
| BG motion | Empirical `bg_factor=0.28` — background moves | **ZERO** — static base, no parallax |
| FG motion | Empirical `fg_factor=0.92` | Physics-based `focal_px * shift / Z` |
| Alpha source | Baked subject RGBA alpha (clean) | Depth-band computed (noisy edges) |
| Blur | N/A (baked masks were clean) | None on export; 0.8px on depth LUT only |
| Depth model | depth-anything-v2-small | depth-pro OR synthetic Gaussian fallback |

**The old renderer looked better because:**
1. Background MOVED — even a small bg parallax (0.28× travel) sells depth
2. Only 2 layers — no inter-band seam artifacts
3. Subject alpha was pre-baked (clean, semantic) not computed from depth bands

---

## 5. Recommended Fix Path

### Priority 1: Give Background Parallax Motion (COMPOSITOR FIX)

**Where:** `scripts/photo_parallax_render_preview_multiplate.py` — `build_filter_complex()`

Currently, `backgroundRgba` is placed as a static `overlay` at `[layer0]` with no motion expression. Apply a reduced parallax:

```
parallax_bg = -(zoom_px * camera_shift / z_far) * 0.6
```

This approximates the old `bg_factor=0.28` behavior within the new camera model. The background should move less than foreground but NOT be static.

**Effort:** Low (add motion expr to background overlay)
**Impact:** High (eliminates "cutout on frozen backdrop" feel)

### Priority 2: Export plate_04 as a Real Plate (EXPORTER SEMANTICS FIX)

**Where:** `photo_parallax_playground/src/App.tsx` — `buildPlateCompositeMaps()`

Remove `background-far` from the exclusion filter. Instead, give it a dedicated alpha computation:
```typescript
if (plate.role === "background-far") {
  roleAlpha = clamp(1 - unionAlpha * 0.94, 0.06, 1);
}
```

This makes plate_04 a real exported plate with rgba/mask/depth files, enabling the renderer to apply per-plate parallax to it like any other plate.

**Effort:** Medium (need to handle the implicit→explicit transition)
**Impact:** High (unlocks background parallax in multiplate pipeline)

### Priority 3: Add Alpha Blur to Plate Export (EXPORTER FIX)

**Where:** `photo_parallax_playground/src/App.tsx` — `buildPlateCompositeMaps()`

After writing per-plate `ImageData`, apply a Gaussian blur pass to the alpha channel before `toDataURL()`. Use the existing `manual.blurPx` parameter (already in settings, just not wired to export).

**Effort:** Low
**Impact:** Medium (softens depth-boundary cutout edges)

### Priority 4: Boost Environment-Mid Coverage (COMPOSITOR TUNING)

**Where:** `photo_parallax_playground/src/App.tsx` — environment-mid alpha formula

Replace square-law with linear attenuation:
```typescript
// Current: roleAlpha = atmospheric * atmospheric  (too aggressive)
// Proposed: roleAlpha = atmospheric * 0.7          (gentler falloff)
```

**Effort:** Low
**Impact:** Low-Medium (makes atmospheric layers more visible)

---

## 6. Fix Path Summary

| # | Fix | Where | Type | Effort | Impact |
|---|-----|-------|------|--------|--------|
| P1 | Background parallax motion | renderer .py | compositor | low | HIGH |
| P2 | Export plate_04 as real plate | App.tsx | exporter semantics | medium | HIGH |
| P3 | Alpha blur on plate export | App.tsx | exporter | low | medium |
| P4 | Softer environment-mid alpha | App.tsx | compositor tuning | low | low-medium |

**Recommended order:** P1 first (immediate visual improvement, no upstream changes needed), then P2 (structural fix enabling long-term multiplate background parallax), then P3+P4 as polish.

---

## 7. Verdict

The fresh render proves that the multiplate pipeline is **technically functional** — motion is real, depth is accurate, camera safety works. The visual weakness is not a rendering bug but an **architectural gap**: the background plate was designed as a passive complement rather than an active parallax participant. The old 2-layer renderer's empirical background motion was the key ingredient that sold the illusion of depth. Restoring background motion (P1) is the single highest-leverage fix.
