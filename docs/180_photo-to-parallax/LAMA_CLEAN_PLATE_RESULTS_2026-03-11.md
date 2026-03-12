# LaMa Clean Plate Results

Дата прогона: `2026-03-11`

## 1. Что проверялось

Цель шага:

- поднять `LaMa` как quality-target backend для `clean_plate`;
- сравнить его с текущим baseline на `OpenCV inpaint`;
- сохранить тот же export contract, чтобы следующий этап мог работать без смены интерфейсов.

Использованный runtime:

- wrapper: `simple-lama-inpainting` как lightweight operational path поверх `LaMa`;
- model: `big-lama.pt`;
- device: `mps`;
- sample set: текущие `4` сцены на `2` depth backend;
- всего кейсов: `8`.

Артефакты:

- summary JSON: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/lama_plate_bakeoff/lama_plate_bakeoff_summary.json`
- outputs root: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/lama_plate_bakeoff`

Новые инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_lama_bootstrap.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_lama_plate_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_lama_plate_bakeoff.sh`

## 2. Агрегат

### `Depth Anything V2 Small`

- entries: `4`
- improved vs baseline: `4/4`
- avg score delta: `+0.45468`
- avg runtime: `2.00981s`
- best delta: `+0.71711`
- worst delta: `+0.25973`

### `Depth Pro`

- entries: `4`
- improved vs baseline: `4/4`
- avg score delta: `+0.30880`
- avg runtime: `1.80254s`
- best delta: `+0.38953`
- worst delta: `+0.20953`

## 3. По сценам

- `depth-anything-v2-small / cassette-closeup`: `+0.34435`, лучший кандидат `lama_d31`
- `depth-anything-v2-small / drone-portrait`: `+0.49752`, лучший кандидат `lama_d31`
- `depth-anything-v2-small / hover-politsia`: `+0.71711`, лучший кандидат `lama_d21`
- `depth-anything-v2-small / keyboard-hands`: `+0.25973`, лучший кандидат `lama_d11`
- `depth-pro / cassette-closeup`: `+0.20953`, лучший кандидат `lama_d21`
- `depth-pro / drone-portrait`: `+0.34915`, лучший кандидат `lama_d31`
- `depth-pro / hover-politsia`: `+0.38953`, лучший кандидат `lama_d11`
- `depth-pro / keyboard-hands`: `+0.28700`, лучший кандидат `lama_d11`

## 4. Что это значит

Главный вывод:

- `LaMa` даёт реальный quality jump над `OpenCV inpaint`, а не только cosmetic variation.

Что подтвердилось:

- выигрыш есть на всех `8/8` кейсах;
- особенно полезен на:
  - `drone-portrait`
  - `cassette-closeup`
  - широких сценах с заметной disocclusion;
- `OpenCV inpaint` стоит оставить как:
  - fallback;
  - cheap baseline;
  - optional small-defect cleanup после более сильного inpaint.

Что не подтвердилось:

- идея одного fixed dilation для всех сцен.

По текущему набору видно:

- для крупных portrait-like дыр часто выигрывает `d31`;
- для некоторых wide/tabletop кейсов выигрывают `d11` или `d21`;
- значит hole growth должен оставаться candidate search, а не hardcoded constant.

## 5. Operational вывод

Официальный `advimman/lama` host install для нашей research-venv оказался слишком тяжёлым:

- legacy stack;
- старые pinned зависимости;
- лишняя стоимость интеграции для текущего R&D цикла.

Поэтому operational path зафиксирован так:

- research reference: `LaMa`
- runtime wrapper: `simple-lama-inpainting`
- local checkpoint: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/checkpoints/lama/big-lama.pt`

Это решение пока достаточно для sandbox и bake-off, потому что:

- модель запускается локально;
- даёт стабильный результат на `mps`;
- не ломает остальной pipeline contract.

## 6. Принятое решение

Для `clean_plate` canonical split теперь такой:

- `OpenCV inpaint` = `Base / fallback`
- `LaMa` = `quality-target / default quality path`

То есть следующий renderer и overscan-track должны рассчитывать на то, что:

- quality mode уже имеет `LaMa clean plate`;
- base mode по-прежнему может обходиться более дешёвым `OpenCV`.

## 7. Что дальше

Следующий логичный этап:

1. перейти в `overscan plate`;
2. проверить, даёт ли `guided mask` дополнительный выигрыш именно до `LaMa`, а не только на mask stage;
3. после этого собирать первый реальный `ffmpeg preview`.

## 8. Источники

- official research repo: `advimman/lama`
- operational wrapper used in sandbox: `simple-lama-inpainting`
