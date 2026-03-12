# Algorithmic Matte Baseline Results

Date: 2026-03-11

## Goal

Собрать первый рабочий `algorithmic matte / roto assist` прототип в sandbox без новых моделей:

- `click seed`
- `grow region`
- `edge-aware depth snap`
- `RGB / depth matte view`
- transparent overlay поверх stage

## Implemented

В `photo_parallax_playground/src/App.tsx` добавлен новый `Stage Tool`:

- `matte`

И новый matte-contract:

- `MatteSeed`
- `MatteSettings`
- `matteOverlayUrl`
- `matteCoverage`

UI теперь поддерживает:

- `matte view`: `rgb / depth`
- `show matte overlay`
- `grow radius`
- `edge snap`
- `matte opacity`
- `clear seeds`

Поведение:

- клик в режиме `matte` ставит seed;
- seed получает локальную proxy-depth оценку;
- matte выращивается по spatial radius + depth similarity;
- matte подмешивается в текущую selection mask;
- overlay можно смотреть как цветную transparent mask или как depth-style matte.

## Why this matters

Это первый общий инструмент для человека и для агента, ближе к `quick mask / roto assist`, а не к обычной кисти. Он не требует ручной прорисовки всего силуэта, а начинает работать от смыслового клика по области.

## Current limits

- используется proxy depth field, а не реальный depth asset;
- пока нет edge-snapping по реальному RGB contour;
- пока нет subtract/add mode кроме clear-seeds reset;
- пока нет сохранения в отдельный `algorithmic_matte.json`.

## Verification

- `npm test`
- `npm run build`
- `./scripts/photo_parallax_review.sh`

Artifacts:

- `photo_parallax_playground/output/review/latest-parallax-review.png`
- `photo_parallax_playground/output/review/latest-parallax-review.json`

## Next step

Следующий практический шаг:

1. Сохранение matte-state как отдельного job contract.
2. `add / subtract / protect edge` для matte seeds.
3. Compare `algorithmic matte` against current brush/group workflow.
4. Потом уже real edge snap по RGB/depth boundaries.
