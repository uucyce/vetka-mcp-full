# Render Preview Results

Дата прогона: `2026-03-11`

## 1. Что сделано

Собран первый реальный `2-layer` renderer на базе:

- `subject_rgba.png`
- `overscan_plate.png`
- `layout.json`

Новые инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview.sh`

Новые выходы:

- `preview.mp4`
- `preview_poster.png`
- `render_report.json`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview/render_preview_summary.json`

Outputs root:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview`

## 2. Текущий render path

Renderer пока специально простой:

1. loop `overscan_plate` как background input;
2. loop `subject_rgba` как foreground input;
3. применить motion expressions из `layout.json`;
4. собрать `preview.mp4` через `ffmpeg`;
5. снять mid-frame poster;
6. сохранить `render_report.json` с filtergraph и probe metadata.

Текущая цель этого шага:

- не “идеальный cinematic render”;
- а первый детерминированный preview контракт, который уже можно гонять batch-ом и анализировать.

## 3. Агрегат

### `Depth Anything V2 Small`

- entries: `4`
- avg render runtime: `2.31474s`
- motion types:
  - `orbit`
  - `pan`
  - `dolly-out + zoom-in`

### `Depth Pro`

- entries: `4`
- avg render runtime: `2.42631s`
- motion types:
  - `orbit`
  - `pan`
  - `dolly-out + zoom-in`

## 4. Что подтверждено runtime-проверкой

- все `8` кейсов собраны без падения;
- выходы совпадают по ожидаемым параметрам:
  - `duration = 4.0s`
  - `fps = 24`
  - `nb_frames = 96`
- renderer корректно работает как для `2560x1440`, так и для `1024x1024`;
- текущий контракт `overscan -> render` уже можно считать рабочим.

## 5. Что сейчас делает motion layer

Текущая интерпретация `layout.json`:

- `pan`
  - линейный horizontal/vertical travel;
- `orbit`
  - horizontal travel + curved vertical motion;
- `dolly-out + zoom-in`
  - weaker background zoom + stronger foreground zoom.

На текущем этапе это ещё не финальная motion grammar, а первый deterministic preset layer.

## 6. Ограничения текущего preview renderer

- это пока только `2-layer renderer`;
- нет side-by-side debug render;
- нет final export presets;
- нет visual approval gate внутри pipeline;
- нет ещё `3-layer` режима, который может понадобиться против cardboard effect.

То есть шаг “renderer exists” закрыт, но шаг “preview выглядит устойчиво на user-facing quality bar” ещё нужно отдельно подтверждать.

## 7. Принятое решение

Текущее состояние render track:

- `ffmpeg preview renderer` принят как рабочий baseline;
- `render_report.json` принят как canonical debug artifact;
- следующий quality step должен идти не в новый backend, а в:
  - visual review;
  - safe preset tuning;
  - при необходимости `3-layer` layout.

## 8. Следующий шаг

Следующий логичный этап:

1. сделать visual pass по `preview.mp4` и `preview_poster.png`;
2. решить, где `2-layer` достаточно, а где нужен ранний `3-layer` режим;
3. после этого уже собирать side-by-side debug render и final presets.
