# Qwen Plate Planner Results

Дата: `2026-03-13`

## Что сделано

- Добавлен локальный planner:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_plan.py`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_plan.sh`
- Planner читает:
  - source image
  - `global_depth_bw.png`
  - current `plate_stack.json`
- Planner пишет:
  - `output/qwen_plate_plans/<sample>.json`
  - `public/qwen_plate_plans/<sample>.json`
  - `manifest.json`

## Что умеет planner

- предлагать `recommended_plate_count`
- давать `scene_summary`
- раскладывать сцену на `plates[]`
- рекомендовать `special_clean_plates[]`
- собирать `plate_stack_proposal`

## Что дочищено в этом шаге

- `special-clean` дедуплицируются
- `cleanVariant` нормализуется в slug-вариант:
  - `no-hands`
  - `no-vehicle`
  - `no-driver`
- `target_plate` резолвится не только по `plate_01`, но и по semantic label
- `plate_stack_proposal` теперь приклеивает `cleanVariant` только к целевому visible plate, а не размазывает его по всем слоям

## Batch status

Прогон подтверждён на:

- `hover-politsia`
- `keyboard-hands`
- `truck-driver`

Ключевые результаты:

- `hover-politsia`
  - planner предложил `vehicle`, `walker`, `street steam`, `background city`
  - special clean:
    - `no-people` -> `walker`
    - `no-vehicle` -> `vehicle`
- `keyboard-hands`
  - planner предложил `hands+note`, `keyboard`, `monitors+background`
  - special clean:
    - `no-hands` -> `hands+note`
    - `no-keyboard` -> `keyboard`
- `truck-driver`
  - planner предложил `driver`, `truck cabin`, `roadside`
  - special clean:
    - `no-driver` -> `driver`

## Sandbox bridge

В sandbox добавлен hidden bridge:

- app загружает `/qwen_plate_plans/<sample>.json`
- в debug panel появился блок `Qwen Plate Plan`
- proposal можно применить в текущий `plateStack` через `apply qwen plan`
- browser API также умеет:
  - `window.vetkaParallaxLab.applyQwenPlatePlan()`

## Что это значит продуктово

Это уже не просто semantic note, а первый рабочий мост:

`global depth -> Qwen scene decomposition -> plate stack proposal`

При этом planner всё ещё остаётся только proposal-layer:

- он не режет пиксели
- он не заменяет mask extraction
- он не идёт напрямую в final render без deterministic validation

## Ограничения

- `keyboard-hands` всё ещё менее стабилен, чем `hover-politsia` и `truck-driver`
- planner может возвращать лишние `special-clean` plate-ы
- proposal пока применяется только через hidden/debug path
- final render пока не делает auto-accept planner без ручного или deterministic gate
