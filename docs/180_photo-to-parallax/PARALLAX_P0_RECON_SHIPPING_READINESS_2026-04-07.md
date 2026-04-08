# Parallax P0 Recon Shipping Readiness

Дата фиксации: `2026-04-07`
Статус: `functional readiness snapshot for next chat`
Задача: `tb_1775579318_21940_1`

## 1. Purpose

Этот документ фиксирует только фактический shipping status по functional roadmap:

- `depth`
- `layer extraction`
- `clean plates / hole fill`
- `headless package`
- `motion`
- `AE-friendly export`

Это не UI-документ.

## 2. Short Verdict

Короткий итог по состоянию на `2026-04-07`:

- `Depth`: уже близко к отдельному shipping tool
- `Layer extraction`: архитектурно и частично practically есть, но качество и determinism ещё не достаточно спокойные
- `Clean plates`: уже существуют, но всё ещё остаются quality/blocker долги
- `Headless package`: pieces exist, but one canonical non-UI package path is still missing
- `Motion`: уже существует headlessly и ближе к shipping, чем казалось
- `AE export/import`: отдельного AE path в коде пока нет

## 3. Depth

### What Exists

- Есть реальный CLI:
  - [vetka_parallax_cli.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/vetka_parallax_cli.py)
- Он умеет:
  - `single image -> auto depth -> parallax video`
  - `manifest -> per-layer parallax video`
- Внутри использует:
  - `generate_depth()` из [cut_depth_service.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/cut_depth_service.py)
  - `build_parallax_ffmpeg_cmd()` из `cut_depth_engine`
- `cut_depth_service.py` already has:
  - cache directory logic
  - AI backends
  - `ffmpeg-luma` fallback
  - explicit `depth_map.png` and `depth_preview.png` outputs

### Factual Constraints

- Depth generation currently lives in shared CUT service, not in a dedicated parallax-only package layer.
- The CLI's primary shipping output is still video, not a dedicated depth-export command surface.
- The older roadmap still contains an unchecked item for canonical grayscale depth export in [PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md).

### Shipping Verdict

`Depth` is the strongest near-shipping subproduct.

It is not “missing”; it mostly needs a narrower standalone export path and packaging discipline.

## 4. Layer Extraction

### What Exists

- There is a real offline extractor:
  - [photo_parallax_layer_extract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layer_extract.py)
- It outputs:
  - `layer_space.json`
  - `prototype.json`
- It reads real inputs from disk:
  - source RGB
  - `depth_master_16.png`
  - `plate_stack.json`
  - `plate_layout.json`
  - `clean_plate.png`
  - special-clean assets like `clean_no_vehicle` and `clean_no_people`
- The canonical architecture already declares `layer_space.json` as primary artifact:
  - [PARALLAX_EXPLICIT_LAYER_EXTRACTION_ARCHITECTURE_2026-03-27.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_EXPLICIT_LAYER_EXTRACTION_ARCHITECTURE_2026-03-27.md)

### Factual Constraints

- The extractor itself writes a non-canonical `prototype.json` sidecar and explicitly warns that:
  - some layers are provisional
  - some layers have `canonicalReady=false`
  - walker/vehicle masks are still not SAM-quality
  - steam/background masks remain provisional in places
- The extractor still uses:
  - bbox + depth band heuristics
  - clean-diff logic
  - fallback soft masks
- This matches the known product complaint that layer quality can still look too proxy-like.

### Shipping Verdict

`Layer extraction` is real and no longer hypothetical, but it is not yet calm enough to call “Pavel-safe shipping” without a verification pass on canonical samples.

## 5. Clean Plates / Hole Fill

### What Exists

- The extractor assembles hole-filled background output inside [photo_parallax_layer_extract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layer_extract.py)
- It uses:
  - LaMa clean plate
  - `clean_no_vehicle`
  - `clean_no_people`
  - partial blend masks
- Multi-plate render path is already `special-clean aware` per docs:
  - [MULTIPLATE_COMPARE_AND_SPECIAL_CLEAN_RESULTS_2026-03-13.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/MULTIPLATE_COMPARE_AND_SPECIAL_CLEAN_RESULTS_2026-03-13.md)
- Current open blockers still exist in TaskBoard:
  - `tb_1774648952_26537_1` extractor source sync
  - `tb_1774649270_26537_1` distinct special-clean export per target

### Factual Constraints

- Hole fill is still explicitly described as `LaMa-only`
- Complex occlusions are not solved generatively
- The extractor itself warns that background cleanup can still keep foreground residue
- Distinct clean plate generation per target is still not fully trusted, because it remains an open `needs_fix`

### Shipping Verdict

`Clean plates` exist and are product-real, but they remain one of the main blockers between “interesting pipeline” and “comfortable shipment.”

## 6. Headless Package

### What Exists

- There are many real root-level scripts in [scripts](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts):
  - depth bakeoff
  - plate export
  - render preview
  - multi-plate render
  - qwen planning/gating
  - layer extraction
  - one CLI
- There is a current plate export wrapper:
  - [photo_parallax_plate_export.sh](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_plate_export.sh)

### Factual Constraints

- `photo_parallax_plate_export.sh` still depends on Playwright/UI export flow:
  - it runs `npx playwright test e2e/parallax_plate_export.spec.ts`
- Inside `photo_parallax_playground/scripts` itself there is no real shipping package script beyond dev-server stop.
- Current headless pieces are fragmented across multiple scripts and contracts.
- `vetka_parallax_cli.py` renders video, but it is not yet the one canonical package entrypoint for:
  - depth
  - layers
  - clean plates
  - manifest

### Shipping Verdict

`Headless package` is the main product gap.

The raw ingredients already exist, but they are not yet unified into one deterministic no-UI export path.

## 7. Motion

### What Exists

- `vetka_parallax_cli.py` already exposes motion presets:
  - `orbit`
  - `orbit_zoom`
  - `dolly_zoom_in`
  - `dolly_zoom_out`
  - `linear`
  - `gentle`
  - `dramatic`
- It also exposes:
  - duration
  - focal length
  - quality presets
- Multi-plate render path already contains:
  - camera geometry
  - depth-to-z mapping
  - motion expressions
  - preset-driven render settings
  - per-layer motion scaling

### Factual Constraints

- Motion is already headless, but today it is split between:
  - `vetka_parallax_cli.py`
  - `photo_parallax_render_preview_multiplate.py`
  - camera/lens research docs
- It is not yet clearly packaged as “the Pavel motion tool”.

### Shipping Verdict

`Motion` is closer to shipping than UI history made it look.

If package export becomes deterministic, motion can ride on top of it quickly.

## 8. AE-Friendly Export

### What Exists

- The product direction is documented repeatedly:
  - [PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md)
  - [PARALLAX_LAYERPACK_HANDOFF_2026-03-27.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_LAYERPACK_HANDOFF_2026-03-27.md)
- Canonical artifacts already point in the right direction:
  - `layer_space.json`
  - `plate_export_manifest.json`
  - layer RGBA/depth/clean outputs

### Factual Constraints

- Repo-wide search did not find:
  - `.jsx`
  - `.aep` generation
  - AE import script
  - AE-specific exporter implementation
- There is CUT manifest import support in backend routes, but not an AE import path.

### Shipping Verdict

`AE-friendly export` is still a product target, not an implemented path.

The manifest and asset structure already exist, but the AE bridge itself is absent.

## 9. Shortest Shipping Path

The shortest practical path from current state to Pavel-facing shipment is:

1. `Depth` — make standalone export path explicit and deterministic
2. `Layer extraction` — verify canonical samples and close known extractor drift
3. `Clean plates` — close distinct special-clean and hole-fill blockers
4. `Headless package` — unify current scripts into one no-UI package flow
5. `Motion` — reuse existing motion presets on top of the package
6. `AE-friendly export` — add import script / package structure, not native plugin

## 10. Main Risk

The main risk is not motion and not UI.

The main risk is:

- extraction/export chain quality and determinism

That is the narrowest place between “interesting prototype” and “send it to Pavel”.

## 11. Recommended Next Task

If the next chat should start with the most leverage, the best first working task is:

- `tb_1775579318_21940_2` only if we want the fastest standalone win via depth

or

- `tb_1775579319_21940_1` if we want to attack the real bottleneck for Pavel shipment

Pragmatic recommendation:

- start with `P0 depth` only if we want the quickest independent deliverable
- start with `P1 layer-pack shipping` if we want the shortest path to the actual Pavel tool
