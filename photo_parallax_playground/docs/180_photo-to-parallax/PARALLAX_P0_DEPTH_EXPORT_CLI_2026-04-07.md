# Parallax P0 Depth Export CLI

Дата фиксации: `2026-04-07`
Задача: `tb_1775579318_21940_2`
Статус: `shipping entrypoint for standalone depth export`

## Purpose

Этот CLI даёт минимальный headless depth-инструмент из текущего `photo_parallax_playground` без UI-операций.

Он нужен как первый practical artifact для Паши и CUT:

- взять один sample;
- получить стабильный `global_depth_bw.png`;
- получить sidecar metadata;
- использовать depth в After Effects как matte / displacement source.

## Invocation

Из корня repo:

```bash
node scripts/parallax_depth_export.mjs --sample hover-politsia
```

С кастомным output path:

```bash
node scripts/parallax_depth_export.mjs \
  --sample keyboard-hands \
  --output /absolute/path/to/depth-export
```

## Output Contract

CLI пишет:

- `global_depth_bw.png`
- `depth_export_preview.png`
- `depth_export_manifest.json`
- `depth_export_state.json`
- `depth_export_snapshot.json`
- `depth_export_job_state.json`
- `depth_export_readiness.json`

## Pavel Win

Минимальный прямой win для Паши:

- depth можно забрать как отдельный артефакт без playground UI;
- output layout детерминирован;
- sidecar JSON объясняет source/depth state для downstream handoff;
- depth можно сразу подхватить в AE как map для compositing/displacement.

## Current Scope

Что делает этот P0:

- запускает app headlessly через Playwright;
- дожидается готовности source raster;
- экспортирует текущий global depth;
- сохраняет preview screenshot и metadata.

Что не делает этот P0:

- не собирает layer pack;
- не делает clean plates;
- не строит AE import script;
- не заменяет будущий headless package.
