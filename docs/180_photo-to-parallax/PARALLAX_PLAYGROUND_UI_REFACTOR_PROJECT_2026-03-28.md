# Parallax Playground UI Refactor Project

Дата фиксации: `2026-03-28`
Статус: `reconstructed after merge-loss incident`

## 1. Purpose

Этот документ фиксирует UI refactor plan для `photo_parallax_playground`.

Цель refactor:

- перевести playground в `viewer-first` режим;
- убрать legacy debug-first path из основного operator flow;
- встроить object/layer thinking без возврата к полному CUT shell.

## 2. Current Problem

Текущее старое состояние `App.tsx` показывает несколько системных проблем:

- preview и render routing смешаны в одном месте;
- левый rail перегружен advanced/debug controls;
- операторский path не читается как простой step-based workflow;
- нижние explanatory/debug cards сидят прямо в main path;
- object/layer thinking не выражен как компактный inspector layer.

Это мешает главной цели playground:

- быстро читать сцену,
- принять routing decision,
- проверить camera-safe motion,
- собрать export output,
- и только потом уходить в cleanup.

## 3. Refactor Direction

Главный принцип:

- main path = `Input -> Extract -> Camera -> Export`

Под этим понимается:

- `Input`
  - выбор source/sample
- `Extract`
  - isolate/depth band/cleanup summary
- `Camera`
  - motion, render route, camera-safe logic
- `Export`
  - action-first output path

Все advanced/manual/debug controls должны уходить из default path в отдельный cleanup/debug layer.

## 4. Product Invariants

Нельзя терять следующие инварианты:

- viewer-first layout важнее debug richness;
- UI должен быть простым и step-based;
- сложные сцены требуют scene routing по типу сцены;
- `synthetic_ai_scene` считается отдельным сложным классом;
- человек должен получать 2-3 high-leverage control points;
- playground не должен тащить в себя весь CUT dockview.

## 5. Refactor Waves

### UIR1. Viewer-First Shell

Цель:

- отделить `Stage` от render routing;
- оставить preview mode в `Stage`;
- вынести render route в `Camera`;
- перевести debug pane в overlay, а не в третью grid-колонку.

Критерии:

- `Stage` вместо старого `View`
- явный workflow strip
- debug pane больше не ломает основную сетку

### UIR2. Four-Step Flow

Цель:

- сделать основной путь линейным и читаемым:
  - `Input`
  - `Extract`
  - `Camera`
  - `Export`

Критерии:

- оператор может пройти сцену без входа в advanced panels;
- `Export` становится action-first, а не summary-only.

### UIR3. Advanced Cleanup Layer

Цель:

- вынести manual/debug-heavy controls из main path.

Из основного rail должны уйти:

- `Focus Proxy`
- `Guided Hints`
- `Stage Tools`
- `Algorithmic Matte`
- `Hint Brushes`
- `Merge Groups`
- `AI Assist`

Их место:

- отдельный `Advanced Cleanup` drawer/layer

### UIR4. Inspector

Цель:

- добавить компактный object/layer overview без возврата к debug-lab.

Минимальный состав:

- scene type
- routing mode
- visible plate count
- risky plate count
- выбор plate
- данные по выбранному plate:
  - role
  - source
  - parallax
  - damping
  - coverage
  - safe overscan
  - cleanup/transition summary

### UIR5. Remove Non-Operator Noise

Цель:

- убрать explanatory/debug cards из default operator path.

Из main path должны исчезнуть:

- `What changed in this wave`
- `Current sample decomposition`
- другие explanatory/debug cards, не нужные для step flow

### UIR6. Routing & Assist

Цель:

- показать scene routing и lightweight human steering как часть main UX.

Минимальный состав:

- scene type selector
- routing summary
- camera-safe status
- cleanup strategy summary
- high-leverage assist controls:
  - `protect region`
  - `refine silhouette`
  - `widen depth band`
  - `narrow depth band`
  - `belongs-to role`
  - `foreground overscale`

Следующий evolution step после этого:

- plate-aware assist recommendations
- action mapping для выбранного plate

## 6. What Was Already Verified In Session

В этой рабочей сессии на локальном dev server был подтверждён более новый UI-state, который соответствует направлению refactor:

- новый strip `Input / Extract / Camera / Export`
- `Stage` отделён от render routing
- render route переехал в `Camera`
- debug pane работал как overlay
- `Export` был переведён в action-first flow
- `Inspector` и `Routing & Assist` были собраны как компактный operator layer

Дополнительно было подтверждено:

- build проходил;
- console errors не было;
- warnings по `Canvas2D readback` были устранены через `willReadFrequently: true` для readback-heavy canvas paths.

## 7. Current Recovery Reality

На момент восстановления этого документа фактическое состояние ветки снова содержит старый UI:

- старый `View`
- overloaded left rail
- нижние explanatory cards
- отсутствие viewer-first markers

Следовательно, следующий практический шаг после возврата docs:

1. восстановить viewer-first baseline в `App.tsx` и `index.css`;
2. только потом продолжать assist/action mapping;
3. коммитить волны отдельно, чтобы UI state не существовал только в контексте чата.

## 8. Non-Goals

В этот refactor не входит:

- перенос всего CUT shell в playground;
- превращение playground в universal debug cockpit;
- замена архитектуры на одну новую модель;
- скрытие человека из pipeline.

## 9. Immediate Next Steps

После восстановления этого документа порядок работы должен быть таким:

1. Commit docs recovery.
2. Rebuild `UIR1 -> UIR3` в коде.
3. Вернуть `UIR4` inspector layer.
4. Вернуть `UIR6` routing + assist layer.
5. Затем продолжить plate-aware recommendations и one-click assist mapping.

## 10. Reconstruction Note

Этот документ восстановлен после merge-loss инцидента, в котором исходный файл отсутствовал во всех ветках и не мог быть возвращён из git history.

Поэтому он фиксирует:

- только уже подтверждённые в этой сессии UI decisions;
- только тот refactor path, который согласуется с существующими architecture/roadmap docs.
