# Algorithmic Matte Contract and Compare Results

Date: 2026-03-11

## Goal

Закрыть следующий research step после `algorithmic matte edit modes`:

- вынести `algorithmic_matte.json` в отдельный файловый артефакт;
- собрать repeatable compare-runner против `brush/group` на проблемных sample scenes.

## Implemented

Добавлены runner-ы:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_algorithmic_matte_contract.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_algorithmic_matte_compare.sh`

Добавлены Playwright probes:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_algorithmic_matte_contract.spec.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_algorithmic_matte_compare.spec.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/algorithmic_matte_presets.ts`

Добавлен browser-export слой в `window.vetkaParallaxLab.getState()`:

- `selectionCoverage`
- `midgroundCoverage`
- `matteCoverage`
- hint/group coverages
- `nearMean`

## Output Contract

`contract` runner теперь пишет отдельный sample-level bundle:

- `algorithmic_matte.json`
- `algorithmic_matte_job_state.json`
- `algorithmic_matte_state.json`
- `algorithmic_matte_snapshot.json`
- `algorithmic_matte_selection.png`
- `algorithmic_matte_manifest.json`

Путь примера:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/algorithmic_matte_contract/cassette-closeup/algorithmic_matte.json`

## Compare Outputs

`compare` runner на каждом sample сохраняет:

- `brush_group_selection.png`
- `algorithmic_matte_selection.png`
- `brush_group_job_state.json`
- `algorithmic_matte_job_state.json`
- `compare_summary.json`

Общий summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/algorithmic_matte_compare/algorithmic_matte_compare_summary.json`

## Current Readout

На текущих preset-сценах `algorithmic matte` не заменяет `brush/group`, а даёт другой режим формы маски:

- `cassette-closeup`
  - `brush/group selectionCoverage = 0.413`
  - `algorithmic matte selectionCoverage = 0.1862`
  - matte работает уже точнее и уже, но пока переводит больше площади в `midground`.
- `keyboard-hands`
  - `brush/group selectionCoverage = 0.5533`
  - `algorithmic matte selectionCoverage = 0.4215`
  - matte тоже даёт более узкий захват и лучше подходит как локальный roto assist, чем как глобальный group lock.
- `hover-politsia`
  - `brush/group selectionCoverage = 0.4563`
  - `algorithmic matte selectionCoverage = 0.4723`
  - на wide scene matte уже ближе по масштабу к brush/group и выглядит как реальный альтернативный edit path.

## Interpretation

Практический вывод сейчас такой:

- `brush/group` остаётся лучшим coarse semantic lock;
- `algorithmic matte` уже годится как локальный shape editor;
- для close-up сцен он полезнее как refinement around difficult edges, а не как единственный способ построить foreground layer.

Именно это хорошо совпадает с исходной идеей: `roto-style algorithmic matte` не должен вытеснять grouping, а должен сидеть поверх него.

## Verification

- `npm test`
- `npm run build`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_algorithmic_matte_contract.sh cassette-closeup --no-open`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_algorithmic_matte_compare.sh 'cassette-closeup,keyboard-hands,hover-politsia' --no-open`

## Next step

Следующий правильный шаг:

1. Вынести `manual_hints.json` и `group_boxes.json` в такие же отдельные файловые contracts.
2. Добавить layered workflow:
   - `group lock`
   - `algorithmic matte refine`
   - `AI assist patch`
3. Потом переходить к real `RGB contour snap` и edge-aware feathering.
