# Qwen Gated Multiplate Results

Дата: `2026-03-13`

## Что сделано

Собран первый полный `gate-aware` flow:

`manual stack -> Qwen Plate Gate -> gated plate stack -> export -> multiplate render -> compare`

Инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_gate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_gate.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_gated_multiplate_flow.sh`

Дополнительно зафиксирован runtime hardening:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_plate_export.spec.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_plate_export.sh`

## Что изменено в export / orchestration

- export-spec больше не держит readiness внутри одной длинной `page.evaluate`, а делает внешний polling из Playwright;
- `truck-driver` readiness теперь гидратируется стабильнее через `hydrateSourceRasterFromStage()` и `hydrateSourceRasterFromAsset()`;
- exporter получил retry policy:
  - до `3` попыток;
  - повторное освобождение `tcp:1434`;
  - `sleep 2` между попытками.

Практический смысл:

- gate-aware path больше не зависит от single-pass headless удачи;
- `truck-driver` теперь проходит как часть полного batch flow, а не только отдельно.

## Результат на complex scenes

Полный gated compare собран на `3/3` сценах:

- `hover-politsia`
- `keyboard-hands`
- `truck-driver`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/render_compare_qwen_multiplate_summary.json`

Batch sheet:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/compare_batch_sheet.png`

## Gate decisions

`hover-politsia`

- decision: `enrich-current-stack`
- gated render count: `3`
- special clean count: `2`
- routed clean count: `2`

`keyboard-hands`

- decision: `keep-current-stack`
- gated render count: `2`
- special clean count: `1`
- routed clean count: `1`

`truck-driver`

- decision: `keep-current-stack`
- gated render count: `2`
- special clean count: `1`
- routed clean count: `1`

## Product вывод

Теперь policy выглядит достаточно жёстко:

- raw `Qwen plate plan` не идёт напрямую в final render;
- в final export/render идёт только `gated_plate_stack`;
- `Qwen` подтверждён как `enrichment layer`, а не unconditional replacement.

На текущем sample set:

- лучший `Qwen` кейс остаётся `hover-politsia`;
- `keyboard-hands` и `truck-driver` пока безопаснее оставлять на current stack.

## Следующий шаг

Следующий правильный шаг по roadmap:

- определить `multi-plate routing rule`, то есть когда scene должна автоматически входить в `Multi-Plate` mode вместо `Portrait Base`;
- затем расширить plate-oriented sample set и quality metrics уже вокруг `gated stack`, а не raw planner output.
