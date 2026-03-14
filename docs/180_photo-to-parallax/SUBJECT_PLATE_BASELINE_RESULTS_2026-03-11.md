# Subject RGBA and Clean Plate Baseline Results

Дата фиксации: `2026-03-11`

Артефакты запуска:

- summary JSON: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/subject_plate_bakeoff/subject_plate_bakeoff_summary.json`
- outputs root: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/subject_plate_bakeoff`

Использованный baseline backend для clean plate:

- `OpenCV inpaint`
- методы:
  - `Telea`
  - `Navier-Stokes`

## 1. Что теперь умеет pipeline

После выбранной финальной mask pipeline теперь собирает:

- `subject_mask.png`
- `subject_rgba.png`
- `subject_preview.png`
- `clean_plate.png`
- `hole_mask.png`
- `hole_overlay.png`
- `source_cutout_debug.png`

Это первый стабильный `asset contract`, который уже можно использовать дальше в render track.

## 2. Главный вывод

`subject_rgba` уже можно считать рабочим выходом.

`clean_plate` на OpenCV inpaint работает только как baseline, а не как quality target.

То есть:

- для умеренных дыр baseline ещё полезен;
- для крупных удалённых объектов, особенно в portrait сценах, нужен более сильный inpaint backend.

## 3. Итоги по sample set

### Сцены, где baseline ещё пригоден

- `hover-politsia`
  - и на `Depth Anything V2 Small`, и на `Depth Pro`;
  - hole area умеренная;
  - result выглядит достаточно пригодно как временный clean plate.

- `cassette-closeup`
  - usable как rough baseline;
  - artefacts заметны, но контракт plate уже рабочий.

### Сцены, где baseline слабый

- `drone-portrait`
  - hole area очень большая;
  - OpenCV inpaint не даёт правдоподобного background reconstruction;
  - это уже явный кейс для `LaMa` или другого более сильного backend.

- `keyboard-hands`
  - большой foreground slab;
  - plate technically строится, но качество недостаточно для хорошего параллакса без заметных артефактов.

## 4. Промежуточный выбор по inpaint baseline

В текущем bake-off чаще всего выигрывают:

- `Navier-Stokes` на wide scenes и больших дырках;
- `Telea` на более компактных object masks.

Но разница между ними не меняет главный продуктовый вывод:

оба метода годятся как temporary fallback, но не как финальный quality path.

## 5. Product implications

После этого шага архитектура уточняется так:

1. `subject_rgba` уже можно считать частью canonical export contract.
2. `clean_plate` уже есть как baseline output.
3. Следующий quality jump должен идти не из mask tuning, а из:
   - более сильного inpaint backend;
   - затем `overscan plate`.

## 6. Что считать решённым

На `2026-03-11` можно считать закрытыми:

- first `subject_rgba` contract;
- first `clean_plate` baseline contract;
- автоматический выбор простого inpaint backend из нескольких кандидатов.

## 7. Что ещё не решено

- high-quality clean plate;
- background consistency на больших удалениях;
- layered exports beyond `subject_rgba`;
- `overscan plate`;
- final motion/render integration.

## 8. Practical Decision

Следующий шаг надо делать не в сторону дальнейшего тюнинга OpenCV inpaint.

Нужен следующий backend comparison:

- `LaMa` как quality target для `clean_plate`;
- OpenCV inpaint оставить как fallback/baseline.
