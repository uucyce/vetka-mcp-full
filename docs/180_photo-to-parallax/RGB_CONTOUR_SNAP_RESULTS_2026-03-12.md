# RGB Contour Snap Results

Дата: `2026-03-12`

## Что сделано

- Добавлен internal postprocess `RGB contour snap + feather cleanup` поверх `layered_edit_flow`.
- Добавлен internal gate `base layered mask` vs `contour-snapped mask`.
- Gate не создаёт новый продуктовый режим и не требует новой пользовательской кнопки.

Новые скрипты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_gate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_gate.sh`

## Что измеряется

Review stage считает:

- `boundaryScoreBefore`
- `boundaryScoreAfter`
- `boundaryScoreDelta`
- `alphaMeanDelta`

Gate stage принимает `contour-snapped` вариант только если:

- review decision = `improved`
- `boundaryScoreDelta >= 0.008`
- `abs(alphaMeanDelta) <= 0.03`

Иначе сохраняется `layered-base`.

## Результат на текущем sample set

Review summary:

- entries: `4`
- improved: `3`
- neutral: `1`
- regressed: `0`
- avg boundary score delta: `+0.01195`

Gate summary:

- entries: `4`
- `accept-snapped`: `3`
- `keep-base`: `1`
- accepted rate: `0.75`

Новый контрольный кейс:

- `drone-portrait` не получил выигрыша от contour snap;
- `boundaryScoreDelta = -0.00247`;
- internal gate оставил `layered-base`.

## Практический вывод

- `RGB contour snap` даёт измеримый плюс только на части research-кейсов.
- Это должен быть internal quality stage после `layered_edit_flow`, а не новая сущность в UX.
- Следующий продуктовый смысл не в расширении панели контролов, а в том, чтобы этот postprocess автоматически включался только там, где он реально улучшает край.

## Артефакты

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/contour_snap_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/contour_snap_batch_sheet.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/contour_snap_gate_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/cassette-closeup/contour_snap_gate.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/keyboard-hands/contour_snap_gate.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/hover-politsia/contour_snap_gate.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow/drone-portrait/contour_snap_gate.json`

## Команды проверки

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_layered_edit_flow.sh \
  'cassette-closeup,keyboard-hands,hover-politsia,drone-portrait' --no-open

/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_review.sh --no-open

/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_contour_snap_gate.sh
```
