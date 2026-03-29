# Parallax Playground Control Recon

Дата фиксации: `2026-03-29`
Статус: `current viewer-first control audit`

## 1. Purpose

Этот recon фиксирует текущий live surface `photo_parallax_playground` так, как он реально собран сейчас в `App.tsx`.

Задача документа:

- перечислить все основные видимые controls по секциям;
- объяснить операторский смысл каждой группы controls;
- отделить main path от `Advanced Cleanup` и `Debug Snapshot`;
- выписать controls, которые сейчас создают cognitive overload.

Документ описывает текущий viewer-first UI, а не исторический CUT shell.

## 2. Current Operator Surface

Текущий экран делится на три класса controls:

1. `Main path`
   - `Import`
   - `Stage`
   - `Depth`
   - `Extract`
   - `Camera`
   - `Export`
   - `Inspector`
   - `Routing & Assist`

2. `Advanced Cleanup`
   - drawer для ручных и debug-heavy tools

3. `Debug Snapshot`
   - diagnostic overlay для внутренних метрик

Практический вывод:

- main path уже viewer-first по структуре;
- но controls всё ещё слишком плотные;
- оператору трудно быстро отделить:
  - “что трогать всегда”
  - “что трогать только если что-то сломалось”

## 3. Section-By-Section Control Map

### 3.1 Import

Назначение:

- выбрать sample и прочитать базовый scene context.

Текущие controls:

- sample buttons:
  - `Cassette close-up`
  - `Keyboard hands`
  - `Hover Politsia street`
  - `Drone portrait`
  - `Punk rooftop`
  - `Truck driver`
- sample note:
  - scenario text
  - resolution
  - tags

Операторский смысл:

- это точка входа в сцену;
- здесь ничего не настраивается, только выбирается source case.

### 3.2 Stage

Назначение:

- смотреть сцену, не меняя render route.

Текущие controls:

- preview mode segmented control:
  - `composite`
  - `depth`
  - `selection`

Операторский смысл:

- `composite`
  - посмотреть итоговый parallax preview
- `depth`
  - посмотреть depth map как grading surface
- `selection`
  - посмотреть текущую proxy/isolation logic

Текущий verdict:

- секция маленькая и понятная;
- это один из самых удачных блоков текущего UI.

### 3.3 Advanced Cleanup

Назначение:

- открыть manual/debug-heavy toolkit только для hard scenes.

Текущие high-level controls:

- `advanced cleanup` toggle
- summary chips:
  - `route ...`
  - routing reasons

Внутри drawer сейчас есть:

- `Focus Proxy`
- `Guided Hints`
- `Stage Tools`
- `Algorithmic Matte`
- `Hint Brushes`
- `Layer Guides`
- `AI Assist`
- `Plate Stack`
- `Qwen Plate Plan`

Операторский смысл:

- это не default path;
- это toolbox для случаев, когда обычного object/layer routing недостаточно.

Текущий verdict:

- сам факт выноса в drawer правильный;
- но внутри drawer controls всё ещё напоминают recon-lab, а не компактный cleanup lane.

### 3.4 Depth

Назначение:

- работать с depth map как с monochrome base.

Текущие controls:

- polarity pills:
  - `white = near`
  - `black = far`
- readout:
  - `depth window`
- sliders:
  - `near limit`
  - `far limit`
  - `gamma`
  - `softness`
  - `expand / shrink`
  - `blur`
- stats:
  - `depth src`
  - `depth polarity`
  - `depth window`
  - `near mean`

Операторский смысл:

- это не object editor;
- это базовая настройка глубинной поверхности всей сцены.

Текущий verdict:

- секция уже близка к правильному `DaVinci-like B/W` направлению;
- но для неопытного оператора здесь всё ещё слишком много параметров сразу.

### 3.5 Extract

Назначение:

- управлять extraction band и cleanup summary перед camera/export.

Текущие controls:

- `advanced cleanup` shortcut
- sliders:
  - `target depth`
  - `range`
  - `foreground bias`
  - `background bias`
  - `post-filter`
- stats:
  - `mask cover`
  - `midground`
- scene route summary

Операторский смысл:

- это главный extraction tuning block;
- именно здесь оператор определяет, насколько агрессивно сцена режется по depth logic.

Текущий verdict:

- функционально блок важный;
- но язык control names всё ещё слишком внутренний и не объясняет, когда трогать `bias` и `post-filter`.

### 3.6 Camera

Назначение:

- управлять motion и camera-safe route.

Текущие controls:

- button:
  - `safe preset`
- sliders:
  - `travel x`
  - `travel y`
  - `zoom`
  - `phase`
  - `overscan`
- render route segmented control:
  - `auto`
  - `safe`
  - `3-layer`
- stats:
  - `travel`
  - `render`
  - `safe x / y`
  - `safe overscan`
- camera-safe warning text

Операторский смысл:

- это motion safety block;
- главный вопрос здесь: можно ли двигать камеру без развала сцены.

Текущий verdict:

- блок полезный;
- но `auto / safe / 3-layer` без пояснения сейчас читается слабо.

### 3.7 Export

Назначение:

- отдать layout/assets/job state.

Текущие controls:

- actions:
  - `download layout`
  - `download assets`
  - `copy job state`
- export target cards:
  - `Depth BW`
  - `Layers RGBA`
  - `Preview`
- export status text
- summary texts:
  - auto-adjusted motion
  - visible plates / routing

Операторский смысл:

- action-first export path;
- это уже не summary-only секция.

Текущий verdict:

- одна из самых читаемых секций в main path.

### 3.8 Inspector

Назначение:

- дать object/layer overview для plate stack.

Текущие controls:

- stats:
  - `scene type`
  - `route`
  - `visible plates`
  - `risky plates`
  - `missing objects`
- plate chips для выбора active plate
- missing object candidate cards:
  - label
  - suggested role
  - reason
  - `pick on stage`
- selected plate detail stats:
  - `role`
  - `source`
  - `parallax`
  - `damping`
  - `coverage`
  - `safe overscan`
- cleanup / transition summary
- guide focus summary

Операторский смысл:

- это object-centric reading layer;
- здесь оператор решает, какой plate сейчас требует внимания.

Текущий verdict:

- блок очень важный;
- но визуально он сейчас слишком плотный, особенно когда одновременно есть:
  - existing plates
  - missing objects
  - draft plates

### 3.9 Routing & Assist

Назначение:

- показать routing decision и дать lightweight steering.

Текущие controls:

- scene type segmented control:
  - `portrait`
  - `single`
  - `group`
  - `wide`
  - `synthetic`
- stats:
  - `routing`
  - `special clean`
  - `transition risk`
  - `camera safe`
- summary texts:
  - cleanup strategy
  - missing detail watchlist
  - draft plates summary
  - layer guide summary
- recommendation cards
- actions:
  - `apply recommended action`
  - `focus guide match`
- manual assist buttons:
  - `protect region`
  - `refine silhouette`
  - `widen depth band`
  - `narrow depth band`
- slider:
  - `foreground overscale`
- role segmented control:
  - `fg`
  - `secondary`
  - `mid`
  - `back`
  - `clean`

Операторский смысл:

- это операторская decision layer;
- именно здесь system reasoning встречается с human steering.

Текущий verdict:

- по смыслу это один из главных продуктовых блоков;
- по плотности он сейчас перегружен и требует hierarchy cleanup.

### 3.10 Debug Snapshot

Назначение:

- дать внутренние diagnostics и dev metrics.

Текущие controls:

- button:
  - `print snapshot`
- readouts:
  - sample
  - preview mode
  - render mode
  - stage tool
  - group mode
  - counts
  - layout metrics
  - camera-safe diagnostics
  - risk metrics
  - helper API notes

Операторский смысл:

- это не продуктовый UI;
- это internal debug surface.

Текущий verdict:

- должен оставаться скрытым по умолчанию;
- не должен смешиваться с operator flow.

## 4. What Is Currently Confusing

По текущему live surface основную путаницу создают не отдельные controls сами по себе, а их плотность и равный визуальный вес.

Главные проблемные зоны:

1. `Depth` и `Extract`
   - слишком много близких численных control names без явного “touch this first”.

2. `Camera`
   - `auto / safe / 3-layer` требует human-readable explanation.

3. `Inspector`
   - existing plates, missing objects и draft plates живут слишком близко друг к другу.

4. `Routing & Assist`
   - recommendation layer, manual buttons, role reassignment и summaries борются за одно и то же внимание.

5. `Advanced Cleanup`
   - сам drawer правильный, но внутри него ещё слишком много legacy research energy.

## 5. Main Path Vs Secondary Path

Текущий recommended operator order по факту должен читаться так:

1. `Import`
2. `Stage`
3. `Depth`
4. `Extract`
5. `Camera`
6. `Export`
7. `Inspector`
8. `Routing & Assist`

Secondary path:

- `Advanced Cleanup`
- `Debug Snapshot`

Проблема текущего экрана:

- вторичный path уже вынесен из rail partially;
- но main path всё ещё не сокращён до действительно quick-read формы.

## 6. Controls Most Likely To Need Relabel Or Demotion

По текущему состоянию первыми кандидатами на cleanup/relabel выглядят:

- `foreground bias`
- `background bias`
- `post-filter`
- `phase`
- `auto / safe / 3-layer`
- `special clean`
- `transition risk`
- `foreground overscale`

Это не значит, что их нужно удалить.

Это значит:

- им нужен более понятный operator framing;
- часть из них, возможно, должна уйти на второй уровень;
- часть должна быть объединена в presets или guided wording.

## 7. Product Consequence

Главный factual вывод из этого recon:

- viewer-first refactor состоялся структурно;
- но semantic compression ещё не состоялась;
- сейчас UI уже ближе к продукту, чем раньше, но всё ещё требует сокращения operator surface.

Следовательно, следующий UI step должен быть не “добавить ещё controls”, а:

1. уменьшить cognitive load;
2. сделать hierarchy главных controls жёстче;
3. оставить сложные вещи доступными, но вторичными.

## 8. Immediate Next UI Follow-Up

Из этого recon прямо следует следующий practical step:

- отделить `draft plate` flow от общей operator каши;
- затем провести main-path simplification pass:
  - оставить top-priority controls видимыми сразу;
  - второстепенные controls свернуть, объяснить или перенести ниже.
