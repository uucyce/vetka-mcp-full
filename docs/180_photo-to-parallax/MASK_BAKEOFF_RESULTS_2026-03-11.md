# Mask Bake-off Results

Дата фиксации: `2026-03-11`

Артефакты запуска:

- summary JSON: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_bakeoff/mask_bakeoff_summary.json`
- outputs root: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_bakeoff`

## 1. Что сравнивалось

Для каждого `depth` backend были прогнаны несколько схем coarse mask:

- `Otsu`
- global `percentile threshold`
- global `k-means`
- `focus-percentile`
- `seed-grow`

Новый quality-first runner использует:

- sample-specific `focus prior`;
- `expanded/context boxes`;
- polarity-aware scoring;
- `seed-grow` от высокоуверенных пикселей внутри focus box;
- morphology cleanup;
- connected-component filtering;
- penalties за spill за пределы context box.

## 2. Ключевой вывод

Глобальные threshold-only маски оказались недостаточно устойчивыми на широких сценах и кадрах с выраженной глубинной плоскостью пола/стола.

Самое важное улучшение дал переход к схеме:

`depth -> polarity prior -> focus seed -> support grow -> cleanup -> score`

Это убрало главную проблему предыдущего шага: победу масок, которые покрывали почти весь кадр или крупные плоскости фона.

## 3. Итоги по sample set

| Backend | Sample | Best candidate | Наблюдение |
| --- | --- | --- | --- |
| `Depth Anything V2 Small` | `cassette-closeup` | `seed-grow__direct-s72-g48` | Маска стала семантически правильной: foreground больше не подменяется фоном внутри focus box. |
| `Depth Anything V2 Small` | `drone-portrait` | `kmeans__direct-c2` | Портрет отделяется стабильно, но край всё ещё грубый для финального matte. |
| `Depth Anything V2 Small` | `hover-politsia` | `seed-grow__direct-s72-g48` | Ложная full-frame маска ушла, теперь выделяется именно летающий автомобиль. |
| `Depth Anything V2 Small` | `keyboard-hands` | `kmeans__direct-c2` | Маска всё ещё широкая: тянет значимую часть клавиатуры как foreground slab. |
| `Depth Pro` | `cassette-closeup` | `seed-grow__inverted-s72-g48` | Самый аккуратный результат на предмете в руках. |
| `Depth Pro` | `drone-portrait` | `kmeans__inverted-c2` | Лучшее quality separation на портрете из текущего bake-off. |
| `Depth Pro` | `hover-politsia` | `seed-grow__direct-s72-g48` | Выделение машины рабочее, но есть лишние фрагменты дыма/бумаги. |
| `Depth Pro` | `keyboard-hands` | `kmeans__inverted-c2` | Наиболее пригодный вариант для hands+keyboard, но foreground всё ещё слишком массивный для clean plate без refine-стадии. |

## 4. Что это значит продуктово

### Уже достаточно хорошо

- крупный центральный subject;
- portrait-style foreground;
- object-in-hands сценa;
- wide scene с одним главным левитирующим объектом, если есть focus prior.

### Пока недостаточно хорошо

- тонкие контуры;
- волосы, провода, полупрозрачные области;
- сцены, где foreground physically лежит на большой плоскости;
- clean plate generation без дополнительного refine этапа.

## 5. Quality-first recommendation

Если приоритет именно качество, а не скорость:

1. Основной depth backend для следующего этапа: `Depth Pro`.
2. Fallback depth backend: `Depth Anything V2 Small`.
3. Coarse mask strategy: `polarity-aware seed-grow`.
4. Следующий обязательный шаг: `MaskRefiner`.

Причина простая:

- `Depth Pro` в среднем даёт более убедительную separation geometry на `cassette-closeup`, `drone-portrait` и `keyboard-hands`;
- `Depth Anything V2 Small` остаётся полезным fallback на отдельных wide-scene кейсах и как быстрый baseline.

## 6. Обновлённое решение по архитектуре

Текущий coarse stage больше нельзя описывать как просто `threshold depth map`.

Более точное описание:

`depth -> normalized orientation candidates -> focus-seeded grow -> morphology -> connected-component cleanup -> heuristic score -> coarse mask`

Это и должно стать canonical contract для research sandbox до подключения `SAM 2` или другого refiner backend.

## 7. Что делать дальше

Следующий этап больше не про поиск лучшего threshold.

Нужен `refinement layer`:

- `SAM 2` или иной mask refiner на входе из coarse depth mask;
- экспорт `subject_rgba`;
- quality metric для края маски;
- после этого только переходить к `clean_plate`.

## 8. Practical Decision

На `2026-03-11` coarse mask research можно считать достаточно зрелым для перехода к следующей фазе:

- `Depth Pro` принимается как quality-first baseline;
- `Depth Anything V2 Small` остаётся fallback/backend для сравнения;
- `seed-grow + polarity prior` принимается как текущий canonical coarse-mask strategy;
- дальнейшие улучшения следует делать уже через refinement, а не через бесконечный подбор глобальных threshold.
