# MCC Drill-Down Architecture Plan (2026-02-26)

Статус: draft v1 (на основе live-audit кодовой базы и UI-диагностики)

## 1. Цель

Стабилизировать раскрытие узлов в MCC как единый механизм `drill-down` (matryoshka), без хаотичной перестройки всего DAG.

Ключевой UX-контракт:
- Клик по `task`-ноде: toggle `expand/collapse` workflow для этой task.
- Клик по `task` повторно: сворачивает этот же workflow.
- Клик по пустому месту: сбрасывает только выделение/подсветку связей, но не ломает layout.
- Клик по обычной node/папке: раскрывает следующий уровень структуры (локально, в том же canvas).
- Раскрытие всегда локально у ноды-источника, а не «в другом конце» графа.
- Workflow раскрывается **из task-ноды** и локально раздвигает мешающие ветки/файлы (только зона коллизии).
- Workflow слой — микро-слой: визуальный масштаб узлов примерно **в 10 раз меньше** архитектурных.
- Workflow DAG обязан сохранять читаемую структуру (ветвление/иерархия), не превращаться в «комок» или полоску.
- Направление DAG фиксированное: **снизу -> вверх** (root/task context внизу, исполнение/команда выше, результат/новый код наверху).
- Тот же принцип применяется к папкам/директориям: при раскрытии показывается следующий уровень (файлы/папки) как вложенная matryoshka-структура, масштаб глубже примерно x10 меньше родителя.

### Locked Contract (обязательный для реализации)
- anchor-first: origin раскрытия = выбранная task-нода;
- local-push only: допускается только локальный push для конфликтующих соседних нод;
- no random placement: запрет на поиск «свободной области» с отрывом от anchor;
- same-canvas only: запрет на отдельное окно/сцену для workflow;
- deterministic fallback: если сверху нет места, fallback только `top -> down` от той же task-ноды.
- bottom-to-top invariant: любой раскрытый подграф (task workflow или folder-depth) строится по оси снизу-вверх.

## 2. Root Cause (по текущей базе)

Текущая проблема не в zoom, а в архитектуре рендера:
- workflow-ноды подмешиваются в тот же общий layout-pass, что и архитектура;
- в итоге global auto-layout перетасовывает сцену;
- fallback workflow иногда короткий (2-3 ноды), поэтому раскрытие выглядит как обрывок.

Критичные точки в коде:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `client/src/components/mcc/DAGView.tsx`
- `client/src/utils/dagLayout.ts`

## 3. Целевая архитектура (Layered Drill)

### 3.1 Слои рендера

- `Layer A: Architecture Base Graph`
  - стабильный граф кода/папок/task-anchor;
  - не должен перестраиваться от каждого `selectedTaskId`.

- `Layer B: Expanded Subgraph Overlay`
  - локальный подграф раскрытого узла (task workflow или node children);
  - позиционируется относительно anchor-ноды;
  - анимируется отдельно;
  - не запускает полный relayout `Layer A`.

### 3.2 State Machine раскрытия

Единый state:
- `drillTarget: { kind: 'task' | 'node' | null, id: string | null }`
- `drillState: 'collapsed' | 'expanding' | 'expanded' | 'collapsing'`

Переходы:
- click same target: `expanded -> collapsing -> collapsed`
- click new target: `expanded(A) -> collapsing(A) -> expanding(B) -> expanded(B)`
- pane click: reset selection/highlight only (без forced collapse, если не задано иначе)

### 3.3 Политика источников данных

При раскрытии task:
1. `primary`: `/api/dag?task_id=...` (если детальный result есть)
2. `secondary`: `/api/mcc/workflows/{workflow_key}` (template)
3. `fallback`: минимальный skeleton

Правило полноты:
- выбирать источник с максимальной структурной полнотой (nodes+edges, не только 3 роли).

## 4. Контракт взаимодействий

### 4.1 Task node
- single click: toggle раскрытия workflow
- double click: опционально zoom-to-fit локального workflow, без смены "комнаты"

### 4.2 Non-task node (папка/файл/модуль)
- single click: selection + edge highlight
- second click или explicit action: раскрытие children/next depth

### 4.3 Pane click
- clear highlight/selection
- не выполнять full graph reset

## 5. Layout Contract (без хаоса)

Для раскрытого подграфа:
- anchor = выбранная нода;
- subgraph bbox строится локально вокруг anchor;
- соседние base-ноды получают мягкий local push только в зоне коллизии;
- после collapse эти local offsets откатываются.

Запреты:
- не смешивать expanded-subgraph с base-layout в одном глобальном dagre pass;
- не менять `graphIdentity` из-за одного только выбора task.

## 6. Визуальный контракт

- Раскрытый DAG должен быть читаемым: уровни, ветвление, не полоска.
- Badge на узлах: `children_count` / `subgraph_count`.
- В правом mini-окне: список имен раскрытых узлов + активная task + краткая метрика полноты (N nodes / M edges).

## 7. План внедрения (по этапам)

### P0 — Stabilization
- зафиксировать state-machine drill;
- убрать trigger полного relayout при selection-only;
- унифицировать pane-click reset.

### P1 — Task Drill Layer
- выделить отдельный overlay-layer для task workflow;
- реализовать local placement + local collision push;
- добавить toggle по повторному клику.

### P2 — Node/Folder Drill
- добавить раскрытие для non-task узлов (next-depth);
- поддержать nested matryoshka (один активный путь).

### P3 — UX/Telemetry
- добавить badges количества содержимого;
- добавить mini-window summary (active node/task names);
- диагностические логи drill state transitions.

## 8. Definition of Done

- [ ] Клик по task раскрывает workflow локально у task-ноды.
- [ ] Повторный клик по той же task сворачивает workflow.
- [ ] Клик по пустому месту только сбрасывает выделение/подсветку.
- [ ] Non-task узлы раскрывают следующий уровень структуры локально.
- [ ] Нет «улетающих» полос и глобальной хаотичной перестройки.
- [ ] Для fallback используется полноценный template-workflow, а не обрывок.
- [ ] На узлах виден счетчик вложенности.
- [ ] В mini summary видны названия активных узлов/тасков.

## 9. Риски

- Риск регрессии drag/pin-позиций при разделении слоев.
- Риск конфликтов между edge-highlight и drill-overlay selection.
- Риск избыточной анимации на больших графах (нужен debounce + frame budget).

## 10. Рекомендуемые маркеры

- `MARKER_155A.G23.DRILL_LAYER_SPLIT`
- `MARKER_155A.G23.DRILL_STATE_MACHINE`
- `MARKER_155A.G23.TASK_TOGGLE_CONTRACT`
- `MARKER_155A.G23.NODE_DRILL_NEXT_DEPTH`
- `MARKER_155A.G23.MINI_SUMMARY_NAMES`
