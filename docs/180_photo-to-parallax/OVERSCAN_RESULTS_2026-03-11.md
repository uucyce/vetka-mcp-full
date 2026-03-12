# Overscan Results

Дата прогона: `2026-03-11`

## 1. Что сделано

На этом шаге `overscan` перестал быть только risk-моделью в sandbox UI и стал реальным asset stage.

Собраны:

- `overscan_plate.png`
- `overscan_mask.png`
- `overscan_seeded.png`
- `overscan_debug_sheet.png`
- `layout.json`

Новые инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_overscan_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_overscan_bakeoff.sh`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/overscan_bakeoff/overscan_bakeoff_summary.json`

Outputs root:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/overscan_bakeoff`

## 2. Как работает текущий overscan path

Текущий quality path:

1. взять `LaMa clean_plate`;
2. взять recommended motion из `sample_analysis_2026-03-10.json`;
3. перевести `recommended_overscan_pct` в canvas expansion;
4. построить expanded canvas;
5. замаскировать только внешнюю overscan-зону;
6. снова прогнать `LaMa`, но уже как outpaint вокруг clean plate;
7. сохранить `layout.json` с motion metadata.

Важно:

- `clean plate` и `overscan plate` теперь реально разнесены как два разных артефакта;
- renderer может работать уже не с эвристикой, а с готовым expanded background plate.

## 3. Агрегат

### `Depth Anything V2 Small`

- entries: `4`
- avg overscan score: `11.67046`
- avg runtime: `4.42605s`
- chosen padding mode: `reflect`
- motion types:
  - `orbit`
  - `pan`
  - `dolly-out + zoom-in`

### `Depth Pro`

- entries: `4`
- avg overscan score: `11.67598`
- avg runtime: `7.12887s`
- chosen padding mode: `reflect`
- motion types:
  - `orbit`
  - `pan`
  - `dolly-out + zoom-in`

## 4. Что подтвердилось

- `overscan_plate` можно стабильно строить поверх текущего `LaMa clean plate`;
- текущий `LaMa` path достаточен и для outpaint-style расширения на sample set;
- `layout.json` уже можно считать рабочим контрактом для следующего render stage.

Размеры expanded plates по кейсам:

- `cassette-closeup`: `3034 × 1708`
- `keyboard-hands`: `2978 × 1676`
- `hover-politsia`: `2996 × 1686`
- `drone-portrait`: `1206 × 1206`

## 5. Что не подтвердилось

- необходимость разных seeding modes на текущем sample set.

На текущих `8` кейсах:

- `reflect` стабильно выбирался как winner;
- `edge` не дал измеримого выигрыша по seam continuity score;
- значит пока нет оснований усложнять overscan stage отдельной seeding-веткой.

## 6. Принятое решение

Текущий overscan split:

- base path:
  - можно при необходимости остаться на более дешёвом background scaling без quality guarantees;
- quality path:
  - `LaMa clean_plate -> motion-driven expansion -> LaMa overscan_plate`

То есть следующий шаг уже не про “как сделать overscan вообще”, а про:

- `ffmpeg preview`;
- safe camera motion;
- render contract.

## 7. Motion contract

`layout.json` теперь содержит:

- `motion_type`
- `travel_x_pct`
- `travel_y_pct`
- `zoom`
- `speed`
- `duration_sec`
- `fps`
- layer z offsets

Текущее heuristic mapping:

- portrait / square-ish -> `dolly-out + zoom-in`
- wide street scenes -> `pan`
- central close-up / strong focus bias -> `orbit`

Это ещё не финальный UX-presets layer, но уже достаточно, чтобы запускать первый renderer.

## 8. Следующий шаг

Следующий логичный этап:

1. собрать первый `ffmpeg preview` из:
   - `subject_rgba`
   - `overscan_plate`
   - `layout.json`
2. проверить mild motion presets против cardboard/disocclusion risk;
3. после этого уже решать, нужен ли более сложный renderer или `3-layer` режим.
