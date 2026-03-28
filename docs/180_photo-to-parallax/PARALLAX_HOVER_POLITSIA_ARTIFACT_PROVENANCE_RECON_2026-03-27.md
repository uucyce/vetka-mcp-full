# Parallax Hover-Politsia Artifact Provenance Recon

Дата: `2026-03-27`

## 1. Why This Recon Exists

Нужно было ответить на более узкий вопрос раньше любого нового renderer fix:

- смотрим ли мы действительно свежий `hover-politsia` render;
- или visual verdict был сделан по mp4, который уже оторвался от текущего export root.

Это критично, потому что layer-order audit на stale artifact даёт ложные выводы даже при корректной гипотезе про fog/head occlusion.

## 2. Historical Reviewed Artifact

Inspection pack, который использовался для review:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/video_inspection/hover-politsia-camera-contract/inspection.json`

Он указывает на input:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_camera_contract/hover-politsia/preview_multiplate.mp4`

## 3. Historical Stale Evidence

Historical `camera_contract` render:

- `preview_multiplate.mp4` -> `2026-03-20 03:37:40`
- `preview_multiplate_report.json` -> `created_at = 2026-03-20T00:37:40.427687+00:00`

The same render report points to mutable export paths:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_layout.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_export_manifest.json`

But those files were later overwritten:

- `plate_layout.json` -> `2026-03-20 05:58:43`
- `plate_export_manifest.json` -> `2026-03-20 05:58:43`
- `plate_stack.json` -> `2026-03-20 05:58:43`
- `plate_export_job_state.json` -> `2026-03-20 05:58:43`

Practical conclusion:

- the old reviewed mp4 cannot be treated as a render of the current export root;
- the old review bundle was path-linked, but not content-addressed.

## 4. Fresh Authoritative Bundle

A fresh authoritative bundle was regenerated from the current export root:

- fresh render root:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_camera_contract_fresh_20260327`
- fresh inspection root:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/video_inspection/hover-politsia-camera-contract-fresh-20260327`

The fresh render summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_camera_contract_fresh_20260327/render_preview_multiplate_summary.json`

The fresh inspection summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/video_inspection/hover-politsia-camera-contract-fresh-20260327/inspection.json`

## 5. Content Identity Captured At Fresh Rerender

Current export-root hashes at rerender time:

- `plate_layout.json`
  `1fdd75f063d76b69c4a380865bb75cad8f891c2e1f862d18871519330d1e0585`
- `plate_export_manifest.json`
  `cc14d914adb111d01feeab19f81c473b14af1314608586c78cfccbfd42ae9414`
- `plate_stack.json`
  `b1d1c5945f3dc15a2d85fcbf5cc83804d7ece90720560bddfb98c406e2866cbc`
- `plate_export_job_state.json`
  `42f455bef2700a6c3965eba4f4859b69da8d4fbe021c662a052459984cd537dd`

Fresh render identity differs materially from the historical `camera_contract` mp4:

- old mp4:
  - size: `263322`
  - sha256: `f4f4fbf665b276d5cbde277089a375e818536823991572c3024fdf0a355a01ba`
- fresh mp4:
  - size: `430952`
  - sha256: `e5a9cccdf2dcafda47805e6920d3ae804b601c465f834fcc875a3e536919416b`

## 6. Fresh Visual / Forensic Findings

The fresh bundle substantially weakens the old fog-only-motion hypothesis.

### Motion evidence

Fresh artifacts:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/video_inspection/hover-politsia-camera-contract-fresh-20260327/motion_diff.jpg`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/video_inspection/hover-politsia-camera-contract-fresh-20260327/motion_energy.png`

These show strong motion not only in steam but also in:

- vehicle silhouette / undercarriage edges;
- walker silhouette;
- nearby moving papers / scene edges.

### Plate evidence

Current export assets:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_03_rgba.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_02_rgba.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/background_rgba.png`

Important observation:

- `plate_03` (`street steam`, role `environment-mid`) does **not** overlap the walker/head area in the current export state;
- therefore the exact historical “steam rides over the head” symptom is **not** reproduced by the current export bundle as-is.

### Fresh machine-readable inspection

From fresh `inspection.json`:

- `depth_sample_rate = 5`
- `rigid_slab_risk = low`
- `weak_background_separation_risk = low`
- `rgb_motion.spatial_concentration = 0.0568`
- `depth_motion.spatial_concentration = 0.1013`

## 7. Updated Interpretation

What the fresh bundle proves:

- stale artifact review was a major contributor to the earlier bad verdict;
- the current export root does produce broader motion than “only fog moves”;
- the old fog-over-head symptom should now be treated as historical evidence, not as proven current-state behavior.

What it does **not** prove:

- that the current render is already visually ideal;
- that compositor policy is beyond suspicion;
- that proxy/synthetic plate semantics are solved.

The more accurate current risk statement is:

- the strongest remaining weakness is broader proxy-like / synthetic layer semantics and possible whole-object coherence or ghosting issues;
- not the exact old fog/head occlusion symptom as previously described from the stale bundle.

## 8. Remaining Follow-Up

1. Audit current compositor policy against the fresh bundle.
2. Decide whether any `order` / `z` / `depthPriority` policy change is still needed.
3. Keep provenance hardening on the roadmap so future reports carry content identity, not only file paths.
4. Continue weight reduction for inspection pack, since the fresh pack is still far above the `~800KB` architecture goal.

## 9. Recommended Current Fix Direction

Based on the fresh bundle, the best current fix direction is:

- exporter semantics first;
- camera tuning later;
- compositor-order tweaks only if still needed after exporter cleanup.

Why:

- current `plate_03` (`street steam`) no longer reproduces the historical head-overlap symptom;
- but it still exports as a broad rounded-rectangle participation zone rather than a shaped atmospheric layer;
- `background-far` is still residual;
- renderer still applies full 3-band split to already synthetic plates.

So the highest-value next engineering move is:

- reduce hard-box `environment-mid` authority;
- make atmospheric participation more shaped/semantic;
- then rerender and reassess whether any explicit compositor-order change is still necessary.

## 10. First Implementation Probe (`2026-03-27`)

A first exporter-side probe was run in:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`

Change direction:

- `environment-mid` no longer uses the older broad soft-box alpha formula;
- instead it is shaped more aggressively by actual `midground` / depth-band signal;
- goal: stop exporting atmospheric participation as an almost solid rounded rectangle.

Quick verification artifacts:

- default export mask after probe:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/hover-politsia/plate_03_mask.png`
- qwen-gated export mask after probe:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_03_mask.png`
- qwen-gated rerender after probe:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_semantics_tune_20260327_rerun/hover-politsia/preview_multiplate_poster.png`

Observed effect:

- `plate_03_mask` is no longer a nearly solid rounded rectangle;
- atmospheric participation is visibly more shaped and narrower;
- broad motion readability was preserved in quick RGB inspection of the tuned render;
- no obvious reintroduction of the old “fog over head” symptom.

Interpretation:

- this does not yet prove final visual success;
- but it is the first concrete evidence that exporter semantics, not camera tuning, is the productive direction for the next fix cycle.
