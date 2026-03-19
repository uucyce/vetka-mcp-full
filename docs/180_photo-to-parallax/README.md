# Photo-to-Parallax

Исследовательский пакет по инструменту `photo -> depth -> plate cleanup -> 2.5D parallax -> ffmpeg render`.

Актуальное разделение с `2026-03-13`:

- `Portrait Base`: depth-first workflow для портретов и простых сцен;
- `Multi-Plate`: следующий roadmap-track для сложных сцен, где одна глобальная маска уже неадекватна.

Содержимое:

- `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`: актуальный operational architecture doc для release-v1 и parallel tracks.
- `PARALLAX_DOC_REVIEW_2026-03-18.md`: ревизия актуальности существующих документов и planning rules.
- `QWEN_IMAGE_LAYERED_FIT_REVIEW_2026-03-18.md`: fit-review по `Qwen-Image-Layered` как candidate backend для layered decomposition.
- `HANDOFF_TO_FRESH_CHAT_RC1_2026-03-19.md`: короткий стартовый handoff для нового чата после закрытия release/recon backlog.
- `RELEASE_NOTES_V1_RC1_2026-03-19.md`: текущее RC1 summary, ограничения и артефакты.
- `PHOTO_TO_PARALLAX_RESEARCH_2026-03-10.md`: исследование по этапам пайплайна.
- `PHOTO_TO_PARALLAX_ARCHITECTURE_V1_2026-03-10.md`: архитектурный документ и границы MVP.
- `PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md`: дорожная карта с чек-листом.
- `PHOTO_TO_PARALLAX_PROTOCOL_LOG_2026-03-10.md`: протокол выполненных и новых подшагов.
- `HANDOFF_PHASE_180_2026-03-14.md`: handoff для старта нового чата без потери контекста.
- `DEPTH_BAKEOFF_RESULTS_2026-03-10.md`: первый реальный runtime/quality отчёт по `Depth Anything V2 Small` и `Depth Pro`.
- `MASK_BAKEOFF_RESULTS_2026-03-11.md`: quality-first отчёт по coarse mask стратегиям и решению по следующему шагу.
- `MASK_REFINE_RESULTS_2026-03-11.md`: отчёт по `SAM 2` refinement и правилу conditional refine.
- `SUBJECT_PLATE_BASELINE_RESULTS_2026-03-11.md`: baseline-отчёт по `subject_rgba` и `clean_plate`.
- `LAMA_CLEAN_PLATE_RESULTS_2026-03-11.md`: отчёт по `LaMa` против `OpenCV inpaint` и решению по quality path.
- `OVERSCAN_RESULTS_2026-03-11.md`: отчёт по `overscan_plate`, `layout.json` и motion-driven canvas expansion.
- `RENDER_PREVIEW_RESULTS_2026-03-11.md`: отчёт по первому `ffmpeg` renderer, `preview.mp4` и `render_report.json`.
- `RENDER_VISUAL_GATE_RESULTS_2026-03-11.md`: отчёт по review gate, side-by-side debug render и решению по `2-layer` vs `3-layer`.
- `SAFER_AND_THREE_LAYER_RESULTS_2026-03-11.md`: отчёт по reduced-motion fallback, `3-layer planner` и первому `3-layer preview renderer`.
- `MODE_COMPARE_REVIEW_RESULTS_2026-03-11.md`: отчёт по grid-видео и sandbox scorer для `2-layer / safe 2-layer / 3-layer`.
- `GUIDED_MASK_RESULTS_2026-03-11.md`: guided-mask отчёт по `mask_hint.png`, hinted `SAM 2` и новым layer exports.
- `UPSCALE_DEPTH_BAKEOFF_RESULTS_2026-03-11.md`: отчёт по `Real-ESRGAN x2 -> depth -> mask` и решению не включать upscale в default path.
- `ASSISTED_AND_LUXURY_STACK_2026-03-11.md`: quality-extension документ по guided masks, upscale, semantic judge и future temporal auxiliary.
- `PRODUCT_MODES_AND_UI_PLAN_2026-03-11.md`: новый product plan по режимам `Auto Base / Manual Pro / AI Assist` и первой волне UI controls.
- `MANUAL_PRO_UI_WAVE1_RESULTS_2026-03-11.md`: отчёт по первой рабочей волне `Manual Pro` controls в sandbox UI.
- `MANUAL_PRO_BRUSH_EDITOR_RESULTS_2026-03-11.md`: отчёт по первому рабочему `Closer / Farther / Protect / Erase` editor в sandbox UI.
- `MANUAL_PRO_GROUP_BOX_RESULTS_2026-03-11.md`: отчёт по первому region-level `Same Layer / Merge Group` editor в sandbox UI.
- `AI_ASSIST_QWEN_RESULTS_2026-03-11.md`: отчёт по локальному `qwen2.5vl:3b`, semantic group suggestions и sanitizing gate.
- `ALGORITHMIC_MATTE_BASELINE_RESULTS_2026-03-11.md`: отчёт по первому `click-to-grow` algorithmic matte / roto assist прототипу.
- `ALGORITHMIC_MATTE_EDIT_MODES_RESULTS_2026-03-11.md`: отчёт по `add / subtract / protect`, shared matte contract и browser export/import.
- `ALGORITHMIC_MATTE_CONTRACT_COMPARE_RESULTS_2026-03-11.md`: отчёт по отдельному `algorithmic_matte.json` contract и compare-runner `brush/group` vs `algorithmic matte`.
- `MANUAL_CONTRACTS_AND_LAYERED_FLOW_RESULTS_2026-03-11.md`: отчёт по `manual_hints.json`, `group_boxes.json` и первому layered workflow bundle с `AI blend`.
- `AI_BLEND_GATE_RESULTS_2026-03-12.md`: отчёт по internal `AI blend gate`, compare sheets и правилу не тащить research controls в конечный UI без доказанной необходимости.
- `RGB_CONTOUR_SNAP_RESULTS_2026-03-12.md`: отчёт по internal `RGB contour snap + feather cleanup`, gate между `layered-base` и `contour-snapped` и правилу держать этот этап внутри пайплайна.
- `OBJECT_SELECTION_QUALITY_RESULTS_2026-03-12.md`: отчёт по objectness-first scorer, сравнению `before-ai / after-ai / internal-final` и решению сместить quality focus с края на целостность объекта.
  Сейчас включает `6` сцен и batch-sheet по whole-object review.
- `REAL_DEPTH_BASELINE_RESULTS_2026-03-12.md`: отчёт по первому реальному `B/W depth preview`, depth-paint presets и проверке `white = closer / black = farther` на baked depth.
- `PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md`: разбор AE-референса Паши и продуктовый вывод про `multi-plate authoring`.
- `PLATE_STACK_DATA_MODEL_RESULTS_2026-03-13.md`: первый `plate stack` contract в sandbox, sample-specific plate presets и debug/export support.
- `QWEN_PLATE_PLANNER_SPEC_2026-03-13.md`: спецификация `Qwen Plate Planner` как semantic decomposition layer поверх `global depth`.
- `PLATE_EDITOR_AND_LAYOUT_BRIDGE_RESULTS_2026-03-13.md`: первый `plate order / visibility / z` editor и plate-aware bridge в layout snapshot.
- `PLATE_AWARE_LAYOUT_RESULTS_2026-03-13.md`: первый `exportPlateLayout()` contract и переход от `foreground/background` к plate-aware layout JSON.
- `PLATE_AWARE_PREVIEW_RENDER_RESULTS_2026-03-13.md`: первый live preview renderer, который читает `plateStack + exportPlateLayout()`, пусть пока и через proxy rectangular plates.
- `MULTIPLATE_ROUTING_RESULTS_2026-03-13.md`: первый deterministic routing rule между `Portrait Base` и `Multi-Plate`.
- `CAMERA_SAFE_AND_PLATE_RISK_RESULTS_2026-03-14.md`: первый `camera-safe` contract, per-plate overscan risk и transition risk для `Multi-Plate`.
- `PLATE_MASK_COMPOSITION_RESULTS_2026-03-13.md`: переход от прямоугольных proxy plate-ов к mask-based plate composition в live preview.
- `PLATE_RGBA_COMPOSITION_RESULTS_2026-03-13.md`: переход от `mask-only` preview к `background_rgba + plate_rgba[]` в браузерном stage preview.
- `PLATE_EXPORT_CONTRACT_RESULTS_2026-03-13.md`: первый export contract с `global depth + plate rgba/mask/depth + layout + stack`.
- `PLATE_EXPORT_FILES_RESULTS_2026-03-13.md`: первый реальный file/export flow на диск с `plate_01_rgba.png`, `plate_01_depth.png`, `global_depth_bw.png` и `plate_stack.json`.
- `MULTIPLATE_FINAL_RENDER_RESULTS_2026-03-13.md`: первый final render path, который читает exported plate assets и собирает `preview_multiplate.mp4`.
- `MULTIPLATE_COMPARE_AND_SPECIAL_CLEAN_RESULTS_2026-03-13.md`: compare `2-layer base vs multi-plate` и внедрение `special-clean aware` underlay в новом renderer.
- `QWEN_PLATE_PLANNER_RESULTS_2026-03-13.md`: первый рабочий `Qwen Plate Planner`, `qwen_plate_plan.json` и hidden bridge из planner proposal в `plateStack`.
- `QWEN_MULTIPLATE_COMPARE_RESULTS_2026-03-13.md`: compare `manual multiplate` против `qwen multiplate` на `3/3` complex scenes.
- `QWEN_PLATE_GATE_RESULTS_2026-03-13.md`: deterministic gate над `Qwen Plate Planner` с решениями `keep / enrich / replace`.
- `QWEN_GATED_MULTIPLATE_RESULTS_2026-03-13.md`: полный `gate-aware` flow `manual -> gate -> export -> render -> compare` на `3/3` complex scenes.
- `sample_analysis_2026-03-10.json`: автоматически собранная baseline-диагностика test images.

Связанная песочница:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground`

Связанные инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_prepare_samples.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_asset_analyzer.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_depth_paint_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_depth_bootstrap.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_depth_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_depth_bakeoff.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mask_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mask_bakeoff.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mask_refine_bootstrap.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mask_refine_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mask_refine_bakeoff.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_prepare_sample_hints.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_realesrgan_bootstrap.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_upscale_depth_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_upscale_depth_bakeoff.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_subject_plate_bootstrap.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_subject_plate_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_subject_plate_bakeoff.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_lama_bootstrap.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_lama_plate_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_lama_plate_bakeoff.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_overscan_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_overscan_bakeoff.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_safer_render_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_safer_render_bakeoff.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_three_layer_plan.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_three_layer_plan.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_3layer.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_3layer.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_plate_export.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_plate_export_batch.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_multiplate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_multiplate.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_plan.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_plan.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_qwen_multiplate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_qwen_multiplate.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_multiplate_flow.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_gate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_gate.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mode_routing_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mode_routing_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_modes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_modes.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_algorithmic_matte_contract.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_algorithmic_matte_compare.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_manual_contracts.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_edit_flow.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_gate_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_gate_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_gate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_gate.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_object_selection_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_object_selection_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_objectness_gate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_objectness_gate.sh`

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_semantic_group_suggest.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_semantic_group_suggest.sh`
