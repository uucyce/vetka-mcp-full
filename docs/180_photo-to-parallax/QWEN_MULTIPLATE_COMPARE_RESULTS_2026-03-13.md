# Qwen Multiplate Compare Results

Дата: `2026-03-13`

## Что сделано

Собран первый полный compare-flow:

`manual plate stack -> export -> multiplate render`

против

`qwen plate plan -> plate stack proposal -> export -> multiplate render`

## Новый flow

- `photo_parallax_plate_export.sh <sample>`
- `photo_parallax_plate_export.sh <sample> --apply-qwen-plan`
- `photo_parallax_render_preview_multiplate.py`
- `photo_parallax_compare_qwen_multiplate.py`
- wrapper:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_multiplate_flow.sh`

## Что изменено в exporter

- `parallax_plate_export.spec.ts` теперь умеет опционально применять `Qwen` plan перед export:
  - `PARALLAX_LAB_APPLY_QWEN_PLAN=1`
- `photo_parallax_plate_export.sh` поддерживает:
  - `--apply-qwen-plan`
- `Qwen` export pack сохраняется отдельно:
  - `photo_parallax_playground/output/plate_exports_qwen/<sample>`

## Render outputs

`Qwen` multiplate renders:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen/hover-politsia/preview_multiplate.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen/keyboard-hands/preview_multiplate.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen/truck-driver/preview_multiplate.mp4`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen/render_preview_multiplate_summary.json`

## Compare outputs

Compare собран на `3/3` complex scenes:

- `hover-politsia`
- `keyboard-hands`
- `truck-driver`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_multiplate/render_compare_qwen_multiplate_summary.json`

Batch sheet:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_multiplate/compare_batch_sheet.png`

Per-scene compare:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_multiplate/hover-politsia/compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_multiplate/keyboard-hands/compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_multiplate/truck-driver/compare_sheet.png`

## Что видно по контракту

`hover-politsia`:

- manual stack:
  - `vehicle`
  - `walker`
  - `street steam`
  - `background city`
  - `no vehicle`
- qwen stack:
  - `vehicle`
  - `walker`
  - `street steam`
  - `background city`
  - `no-people`
  - `no-vehicle`

`keyboard-hands`:

- manual stack:
  - `hands+note`
  - `keyboard`
  - `monitors+background`
  - `no hands`
- qwen stack:
  - `hands+note`
  - `keyboard`
  - `monitors+background`
  - `no-hands`
  - `no-keyboard`

`truck-driver`:

- manual stack:
  - `driver`
  - `truck cabin`
  - `roadside`
  - `no driver`
- qwen stack:
  - `driver`
  - `truck cabin`
  - `roadside`
  - `no-driver`

## Практический вывод

`Qwen Plate Planner` уже полезен не только как naming layer, а как structural proposal layer:

- он умеет добавлять missing `special-clean` plates;
- он даёт осмысленные названия и plate families;
- он не ломает export/render path.

Но он пока остаётся только proposal layer:

- final acceptance still should be deterministic or manual;
- visual quality compare должен решаться по render review, а не только по JSON structure;
- `Qwen` не должен напрямую заменять extraction/cleanup.

## Следующий шаг

Следующий правильный шаг по roadmap:

- ввести `proposal quality gate` для `Qwen plate plan`
- решить, когда `Qwen`:
  - просто enriches current stack,
  - а когда реально заменяет manual default stack для complex scene
