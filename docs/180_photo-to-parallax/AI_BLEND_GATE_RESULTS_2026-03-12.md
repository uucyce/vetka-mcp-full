# AI Blend Gate Results

Date: 2026-03-12

## Goal

Добавить internal quality gate для `AI blend`, не расширяя UI:

- `accept`
- `reject`
- `keep-manual`

И выпускать visual compare artifacts:

- `before AI`
- `after AI`
- compare sheet

## Implemented

`layered workflow` probe обновлён:

- сохраняет `layered_before_ai.png`
- сохраняет `layered_after_ai.png`
- пишет gate fields в summary:
  - `selectionCoverageDelta`
  - `midgroundCoverageDelta`
  - `gateDecision`
  - `gateReason`

Добавлен review script:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_gate_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_gate_review.sh`

Он строит:

- sample-level `layered_gate_compare_sheet.png`
- batch-level `layered_gate_batch_sheet.png`
- `layered_gate_summary.json`

## Gate Rule

Текущая research-rule простая и намеренно conservative:

- `keep-manual`, если `AI` ничего не добавил
- `reject`, если `selectionCoverageDelta < -0.05`
- `accept`, если `abs(selectionCoverageDelta) <= 0.05`
- иначе `keep-manual`

Это пока не финальная продуктовая логика, а первый безопасный gate для исследований.

## Current Readout

Сводка:

- `accept = 2`
- `reject = 1`
- `keep-manual = 0`
- `avg_selection_delta = -0.00573`

По sample:

- `cassette-closeup`
  - `delta = +0.0098`
  - decision: `accept`
- `keyboard-hands`
  - `delta = -0.0671`
  - decision: `reject`
- `hover-politsia`
  - `delta = +0.0401`
  - decision: `accept`

## Interpretation

Главный вывод:

- `AI blend` уже нельзя применять безусловно;
- even on small sample set есть как полезные, так и вредные сдвиги;
- значит в продукте `AI Assist` должен быть quality-guarded internal stage, а не ещё одна пользовательская кнопка по умолчанию.

Это соответствует целевому UX:

- основной продукт должен остаться near-one-click;
- advanced gating, compare и debug остаются hidden research/pro tooling.

## Artifacts

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/layered_gate_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/layered_gate_batch_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/cassette-closeup/layered_gate_compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/keyboard-hands/layered_gate_compare_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/hover-politsia/layered_gate_compare_sheet.png`

## Verification

- `npm test`
- `npm run build`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_edit_flow.sh 'cassette-closeup,keyboard-hands,hover-politsia' --no-open`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_gate_review.sh --no-open`

## Next Step

Следующий правильный шаг:

1. Не добавлять новый UI control.
2. Ввести `RGB contour snap` и edge feather cleanup как internal/manual-quality stage.
3. Потом уже смотреть, какие из research controls реально заслуживают попадания в упрощённый продуктовый UI.
