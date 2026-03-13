# Multiplate Final Render Results

Дата: `2026-03-13`

## Что сделано

Добавлен первый final render path, который читает не sandbox preview state, а реальные exported multi-plate assets:

- [renderer](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.py)
- [wrapper](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.sh)

Входы:

- `background_rgba.png`
- `plate_XX_rgba.png`
- `plate_layout.json`
- `plate_export_manifest.json`

Выходы:

- `preview_multiplate.mp4`
- `preview_multiplate_poster.png`
- `preview_multiplate_report.json`

## Что проверено

`multiplate final render` собран минимум на `3` complex scenes:

- `hover-politsia`
- `keyboard-hands`
- `truck-driver`

Сводка:

- [summary](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/render_preview_multiplate_summary.json)

Примеры:

- [hover mp4](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/hover-politsia/preview_multiplate.mp4)
- [hover poster](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/hover-politsia/preview_multiplate_poster.png)
- [keyboard poster](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/keyboard-hands/preview_multiplate_poster.png)
- [truck poster](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/truck-driver/preview_multiplate_poster.png)

## Важный фикс

Во время внедрения найден и исправлен scale bridge bug:

- exported plate assets были в reduced preview resolution;
- initial render path трактовал их как full-res;
- из-за этого первый poster получался с маленьким изображением в центре.

Теперь renderer вычисляет `asset_scale` относительно `layout.source.width` и корректно растягивает exported assets до финального canvas.

## Что это означает

Это первый шаг, где pipeline уже выглядит так:

- `plate export pack -> ffmpeg multiplate final render`

А не так:

- `sandbox preview only`.

То есть multi-plate ветка теперь дошла до реального видео-рендера.

## Обновление

После этого первого шага renderer был расширен:

- hidden `special-clean` / `cleanVariant` plate-ы теперь используются как clean underlay в multi-plate render path;
- собран отдельный compare `2-layer base vs multi-plate final render`;
- подробности вынесены в:
  [MULTIPLATE_COMPARE_AND_SPECIAL_CLEAN_RESULTS_2026-03-13.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/MULTIPLATE_COMPARE_AND_SPECIAL_CLEAN_RESULTS_2026-03-13.md)
