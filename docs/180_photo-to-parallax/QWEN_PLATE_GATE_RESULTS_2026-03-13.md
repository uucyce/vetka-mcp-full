# Qwen Plate Gate Results

Дата: `2026-03-13`

## Что сделано

Добавлен deterministic gate поверх `Qwen Plate Planner`:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_gate.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_plate_gate.sh`

Gate читает:

- manual `plate_stack.json`
- qwen-applied `plate_stack.json`
- `qwen_plate_plan.json`

И выдаёт:

- `keep-current-stack`
- `enrich-current-stack`
- `replace-current-stack`

Плюс сохраняет готовый `gated_plate_stack`.

## Output contract

Gate пишет:

- `photo_parallax_playground/output/qwen_plate_gates/<sample>.json`
- `photo_parallax_playground/public/qwen_plate_gates/<sample>.json`
- `manifest.json`

## Решения по complex scenes

### `hover-politsia`

- decision: `enrich-current-stack`
- confidence: `0.9`
- visible overlap: `1.0`
- new clean variants:
  - `no-people`

Практический смысл:

- manual stack уже хороший
- `Qwen` не должен заменять его целиком
- но `Qwen` полезно добавляет новый special-clean слой для `walker`

### `keyboard-hands`

- decision: `keep-current-stack`
- confidence: `0.5`
- visible overlap: `1.0`
- new clean variants:
  - `no-keyboard`

Практический смысл:

- структура сцены распознана правильно
- но confidence пока недостаточен для автоматического enrich/replace
- значит `Qwen` здесь остаётся только exploratory proposal

### `truck-driver`

- decision: `keep-current-stack`
- confidence: `0.9`
- visible overlap: `1.0`
- new clean variants:
  - none

Практический смысл:

- manual/default stack уже почти совпадает с полезным `Qwen` proposal
- planner не даёт enough net-new structure

## Hidden sandbox bridge

Sandbox теперь подгружает:

- `/qwen_plate_gates/<sample>.json`

И умеет:

- показывать decision в hidden `Qwen Plate Plan` block
- применять не raw planner proposal, а `gated_plate_stack`

Browser API:

- `window.vetkaParallaxLab.applyQwenPlateGate()`

## Product вывод

Gate уже даёт полезную product policy:

- `Qwen` не надо применять безусловно
- `Qwen` надо использовать как enrichment layer там, где:
  - scene structure совпадает с manual/default stack
  - и planner добавляет meaningful `special-clean` plate

Текущий лучший кейс:

- `hover-politsia`

## Residual risk

Повторный end-to-end `qwen_multiplate_flow.sh` остаётся headless-flaky на некоторых последующих export runs в Playwright:

- проблема в `sourceRasterReady` / browser export orchestration
- это не ломает сам gate
- gate можно считать по уже собранным manual/qwen stack outputs

То есть текущая проблема лежит в orchestration stability, а не в логике `Qwen Plate Gate`.
