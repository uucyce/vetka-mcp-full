# Manual Contracts and Layered Flow Results

Date: 2026-03-11

## Goal

Продолжить `Manual Pro` и `AI Assist` до отдельного контрактного слоя:

- вынести `manual_hints.json`;
- вынести `group_boxes.json`;
- собрать первый layered workflow bundle:
  - `group lock`
  - `algorithmic matte refine`
  - `AI blend`

## Implemented

В `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx` добавлены browser APIs:

- `exportManualHints()`
- `importManualHints(...)`
- `exportGroupBoxes()`
- `importGroupBoxes(...)`

Добавлены runner-ы:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_manual_contracts.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_edit_flow.sh`

Добавлены Playwright probes:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_manual_contracts.spec.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_layered_workflow.spec.ts`

## New Contracts

Теперь sandbox может выпускать отдельные state files:

- `manual_hints.json`
- `group_boxes.json`
- `algorithmic_matte.json`

Пример:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/manual_contracts/cassette-closeup/manual_hints.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/manual_contracts/cassette-closeup/group_boxes.json`

## Layered Workflow Bundle

Новый layered runner сохраняет по sample:

- `manual_hints.json`
- `group_boxes.json`
- `algorithmic_matte.json`
- `layered_before_ai.json`
- `layered_after_ai.json`
- `layered_job_state.json`
- `layered_selection.png`

Общий summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/layered_edit_flow_summary.json`

## Current Readout

Текущий layered workflow уже работает на `3` preset-сценах:

- `cassette-closeup`
  - `selectionCoverageBeforeAi = 0.413`
  - `selectionCoverageAfterAi = 0.4228`
  - `aiGroupCount = 1`
- `keyboard-hands`
  - `selectionCoverageBeforeAi = 0.5155`
  - `selectionCoverageAfterAi = 0.4484`
  - `aiGroupCount = 2`
- `hover-politsia`
  - `selectionCoverageBeforeAi = 0.4465`
  - `selectionCoverageAfterAi = 0.4866`
  - `aiGroupCount = 2`

## Interpretation

Практический вывод:

- layered path уже реален как исследовательский workflow;
- `AI blend` не всегда просто “расширяет маску”, а может и сужать coarse coverage;
- значит AI patch правильно держать как compare/blend stage, а не как always-on auto-merge.

Это согласуется с предыдущими выводами:

- `group lock` нужен как coarse semantic anchor;
- `algorithmic matte` нужен как local shape refine;
- `AI Assist` должен жить поверх них как optional semantic patch.

## Verification

- `npm test`
- `npm run build`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_manual_contracts.sh cassette-closeup --no-open`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_edit_flow.sh 'cassette-closeup,keyboard-hands,hover-politsia' --no-open`

## Next step

Следующий правильный шаг:

1. Добавить visual compare `layered before AI` vs `layered after AI`.
2. Ввести quality gate для AI blend:
   - accept
   - reject
   - keep-manual
3. После этого идти в real `RGB contour snap` и feather/edge cleanup.
