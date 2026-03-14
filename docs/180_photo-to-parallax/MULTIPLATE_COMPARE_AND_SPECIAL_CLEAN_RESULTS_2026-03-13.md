# Multiplate Compare And Special-Clean Results

Дата: `2026-03-13`

## Что сделано

Закрыт следующий practical step после первого `multiplate final render`:

- renderer стал `special-clean aware`;
- собран compare `2-layer base vs multi-plate final render`;
- compare summary теперь явно пишет `skipped` причины, а не молча теряет неполные кейсы.

Основные файлы:

- [multiplate renderer](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.py)
- [multiplate wrapper](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.sh)
- [compare runner](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_multiplate.py)
- [compare wrapper](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_multiplate.sh)

## Special-Clean Underlay

Раньше `special-clean` plate-ы экспортировались, но не участвовали в финальном видео-рендере.

Теперь hidden `special-clean` / `cleanVariant` plate-ы:

- читаются из `plate_export_manifest.json`;
- подмешиваются как clean underlay до `background_rgba`;
- попадают в `preview_multiplate_report.json` через поле `special_clean_count`.

Это уже рабочий мост к AE-подобной логике:

- `no vehicle`
- `no hands`
- `no driver`

не просто лежат в pack, а реально становятся частью comp path.

## Plate-Local Clean Routing

Поверх global underlay сделан следующий шаг:

- `cleanVariant` теперь живёт и на видимом plate, которому нужен clean underlay;
- renderer матчится по `cleanVariant` между visible plate и hidden `special-clean` plate;
- clean asset подмешивается локально перед конкретным plate, а не только как общий сценовый фон.

Это уже ближе к AE-логике `plate-specific clean`.

Подтверждение:

- [hover report](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/hover-politsia/preview_multiplate_report.json)
- [keyboard report](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/keyboard-hands/preview_multiplate_report.json)

Текущее значение:

- `hover-politsia` -> `routed_clean_count = 1`
- `keyboard-hands` -> `routed_clean_count = 1`
- `truck-driver` -> `routed_clean_count = 1`

Сводка:

- [multiplate render summary](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/render_preview_multiplate_summary.json)

Примеры:

- [hover poster](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/hover-politsia/preview_multiplate_poster.png)
- [keyboard poster](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/keyboard-hands/preview_multiplate_poster.png)
- [truck poster](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate/truck-driver/preview_multiplate_poster.png)

## Compare Between Legacy Base And Multiplate

Compare pack собран для первых complex scenes:

- [summary](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_multiplate/render_compare_multiplate_summary.json)
- [batch sheet](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_multiplate/compare_batch_sheet.png)

Готовые compare-кейсы:

- [hover compare sheet](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_multiplate/hover-politsia/compare_sheet.png)
- [hover compare video](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_multiplate/hover-politsia/compare_grid.mp4)
- [keyboard compare sheet](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_multiplate/keyboard-hands/compare_sheet.png)
- [keyboard compare video](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_multiplate/keyboard-hands/compare_grid.mp4)

Текущий честный статус:

- `hover-politsia` -> compare собран;
- `keyboard-hands` -> compare собран;
- `truck-driver` -> `skipped`, потому что отсутствует legacy `2-layer` base preview.

Это не blocker для `multiplate` renderer, но это blocker именно для `legacy-vs-multiplate` compare на этой сцене.
Browser export blocker у `truck-driver` уже снят: multiplate/export path снова рабочий, а `skipped` теперь относится только к отсутствующему legacy compare base.

## Вывод

Этот шаг уже полезен не как demo, а как product bridge:

- export pack умеет хранить special clean variants;
- final renderer умеет их читать и маршрутизировать plate-local;
- compare flow уже показывает, где `multiplate` реально отличается от старого `2-layer` пути.

Следующий логичный шаг:

- не расширять compare бесконечно,
- а либо собрать для `truck-driver` legacy base preview,
- либо перестать держать compare-gate зависимым от старого `2-layer` path;
- затем двигать `Qwen Plate Planner -> plate stack proposal -> export/render`.
