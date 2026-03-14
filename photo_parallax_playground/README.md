# VETKA Photo Parallax Lab

Standalone sandbox for researching `photo -> 2.5D parallax` without integrating into the main product yet.

## Goals

- test mild parallax motion on still images;
- estimate overscan/disocclusion/cardboard risks before backend integration;
- expose browser self-analysis tools through `window.debug` and `window.vetkaParallaxLab`;
- produce repeatable screenshot + JSON review artifacts.

## Run

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground
npm install
npm run dev
npm test
npm run test:e2e
```

Open [http://127.0.0.1:1434](http://127.0.0.1:1434).

## Review Probe

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_review.sh hover-politsia
```

Artifacts are written to:

```text
photo_parallax_playground/output/review/latest-parallax-review.png
photo_parallax_playground/output/review/latest-parallax-review.json
```

## Algorithmic Matte Contract

Export one sample-level `algorithmic_matte.json` bundle:

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_algorithmic_matte_contract.sh cassette-closeup
```

Compare `brush/group` versus `algorithmic matte` on preset scenes:

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_algorithmic_matte_compare.sh \
  'cassette-closeup,keyboard-hands,hover-politsia'
```

Outputs land in:

```text
photo_parallax_playground/output/algorithmic_matte_contract
photo_parallax_playground/output/algorithmic_matte_compare
```

## Manual Contracts and Layered Flow

Export separate `manual_hints.json` and `group_boxes.json`:

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_manual_contracts.sh cassette-closeup
```

Export layered bundles with:

- manual hints
- group boxes
- algorithmic matte
- `AI blend`

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_edit_flow.sh \
  'cassette-closeup,keyboard-hands,hover-politsia'
```

Outputs land in:

```text
photo_parallax_playground/output/manual_contracts
photo_parallax_playground/output/layered_edit_flow
```

Build internal `AI blend gate` compare sheets from the layered bundle:

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_gate_review.sh
```

Run internal `RGB contour snap` review and choose final hidden mask variant:

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_review.sh --no-open
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_gate.sh
```

`photo_parallax_contour_snap_review.sh` already prefers the project Python environment when available.

Run whole-object selection review across `before-ai / after-ai / internal-final`:

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_object_selection_review.sh
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_objectness_gate.sh
```

## Depth Bake-off

Bootstrap the isolated depth environment:

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_depth_bootstrap.sh
```

Run both depth backends on the sample set:

```bash
HF_HUB_DISABLE_XET=1 /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_depth_bakeoff.sh \
  --backend depth-anything-v2-small \
  --backend depth-pro \
  --pred-only
```

Outputs land in:

```text
photo_parallax_playground/output/depth_bakeoff
```

## Browser Debug API

Console examples:

```js
window.vetkaParallaxLab.snapshot()
window.vetkaParallaxLab.print()
window.vetkaParallaxLab.setSample("drone-portrait")
window.vetkaParallaxLab.setMotion(3.2, 1.4, 1.05)
window.vetkaParallaxLab.setFocus(0.5, 0.45, 0.34, 0.62, 0.14)
window.vetkaParallaxLab.toggleDebug()
```

Self-analysis helpers:

```js
debug.logs(50)
debug.search("parallax")
debug.errors(20)
debug.warnings(20)
debug.printLogs()
debug.stats()
debug.inspect("overscan")
debug.find("setMotion")
debug.functions("set")
debug.network("/api", 20)
debug.findRequest("sample")
debug.watch("setMotion")
```
