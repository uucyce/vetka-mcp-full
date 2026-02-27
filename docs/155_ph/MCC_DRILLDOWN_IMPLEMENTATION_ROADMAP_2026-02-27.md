# MCC Drill-Down Implementation Roadmap + Cleanup Check (2026-02-27)

Статус: RECON + implementation spec (без смены стека).
Основание: `MCC_DRILLDOWN_MECHANICS_SYNTHESIS_2026-02-27.md` + текущая codebase MCC.

## 0. Progress Snapshot

Выполнено:
- `P0.1` Drill contract hardening (explicit toggle, no hidden zoom side-effects).
- `P0.2` Workflow source arbitration v1 (priority: `dag -> template -> pipeline`).
- `P0.3` Size control contract locked (mini sizing path documented in node render layer).
- `P1.1` Focus+context partial: inline mode keeps context while preserving selected-edge emphasis.
- `P1.2` Local relayout partial: bounded repel vector replaces one-way downward push.
- `P3.1` Legacy dependency removed: `MiniTasks(expanded)` no longer uses deprecated `MCCTaskList`.
- `P3.2` Runtime guard added: main MCC path protected from deprecated component imports.

В процессе:
- `P1.3` incremental/reuse tuning under rapid toggle stress.
- `P2` threshold/breadcrumb/lazy consistency hardening.
- `P3` final deprecated-surface retirement strategy (archive/remove policy).

Недавно добавлено (P2):
- roadmap node drill thresholds: `DEPTH1_LIMIT=6`, `DEPTH2_PER_PARENT_LIMIT=3`, `DEPTH2_TOTAL_LIMIT=8`.
- overflow markers `+N more` для порционного раскрытия при скрытых узлах.

## 1. Сверка с текущей архитектурой

Текущий каркас уже подходит под single-canvas концепцию:
- `MyceliumCommandCenter.tsx`: единый источник graph composition (`graphForView`), overlay tasks/workflow/node-drill.
- `DAGView.tsx`: единый renderer + layout engine + camera/LOD.
- `dagLayout.ts`: базовый layout + профильная вертикальная раскладка + mini-метаданные.
- `useMCCStore.ts`: nav/action state machine.

Главный вывод:
- Проблема не в библиотеке, а в **контракте слоев и источников данных workflow**.
- Нужен жесткий arbitration по источнику workflow + локальная физика раскрытия.

## 2. Маркер-карта (новые и ключевые)

### 2.1 Новые маркеры этого шага
- `MARKER_155A.G24.WF_SOURCE_FANOUT`  
  файл: `client/src/components/mcc/MyceliumCommandCenter.tsx`  
  смысл: `selectedTaskId` запускает 3 параллельных источника workflow (dag + pipeline fallback + template).

- `MARKER_155A.G24.WF_TEMPLATE_KEY_POLICY`  
  файл: `client/src/components/mcc/MyceliumCommandCenter.tsx`  
  смысл: normalize `wf_*` -> `bmad_default` может прятать task-specific workflow intent.

- `MARKER_155A.G24.WF_SOURCE_ARBITRATION`  
  файл: `client/src/components/mcc/MyceliumCommandCenter.tsx`  
  смысл: текущий выбор fallback основан на "больше нод", не на семантическом приоритете.

- `MARKER_155A.G24.DRILL_TOGGLE_SINGLE_SOURCE`  
  файл: `client/src/components/mcc/MyceliumCommandCenter.tsx`  
  смысл: explicit single-source toggle раскрытия task workflow.

- `MARKER_155A.G24.INCREMENTAL_LAYOUT_ARBITRATION`  
  файл: `client/src/components/mcc/DAGView.tsx`  
  смысл: tradeoff incremental layout в architecture режиме.

- `MARKER_155A.G24.HIGHLIGHT_BYPASS_WHEN_INLINE`  
  файл: `client/src/components/mcc/DAGView.tsx`  
  смысл: при inline workflow bypass подсветки связей.

- `MARKER_155A.G24.CLICK_DBLCLICK_DEBOUNCE`  
  файл: `client/src/components/mcc/DAGView.tsx`  
  смысл: единый debounce-контракт single/double click.

- `MARKER_155A.G24.NODE_SIZE_CONTROL_PATH`  
  файл: `client/src/utils/dagLayout.ts`  
  смысл: реальный контроль micro-size идет через node components, не через dagre width/height.

- `MARKER_155A.G24.LEGACY_EXPANDED_TASK_PANEL`  
  файл: `client/src/components/mcc/MiniTasks.tsx`  
  смысл: expanded mini-task все еще опирается на deprecated `MCCTaskList`.

- `MARKER_155A.G24.ACTION_SEMANTICS_REVIEW`  
  файл: `client/src/store/useMCCStore.ts`  
  смысл: roadmap actions (`Launch/Ask/Add`) требуют semantic alignment/context-gating.

### 2.2 Ключевые существующие маркеры, на которые опираемся
- `MARKER_155A.G21.SINGLE_CANVAS_STATE`
- `MARKER_155A.G23.WF_LAYER_PHYSICS_V1`
- `MARKER_155A.G23.LOCAL_PUSH_V1`
- `MARKER_155A.G23.NODE_DRILL_NEXT_DEPTH`
- `MARKER_155A.P0.WF_MINI_LAYER`
- `MARKER_155A.P2.DRILL_POLICY`
- `MARKER_155A.G23.NO_SINK_ACCUMULATION`

## 3. Выявленные проблемы (dead code, недострой, логические разрывы)

### 3.1 Удаленный мертвый код (сделано в этом шаге)
Файл: `client/src/components/mcc/MyceliumCommandCenter.tsx`
- удалены неиспользуемые состояния/переменные:
  - `leftCollapsed`, `rightCollapsed`
  - `lastFractalZoomKeyRef`
  - `handleRoadmapNodeDrill`
  - `selectedNodeData`, `selectedEdgeData`
  - tooltip hooks `ttTeam/ttSandbox/ttHeartbeat/ttKey/ttStats/ttExecute`
  - `AUTO_DRILL_ZOOM`
  - неиспользуемый импорт `useLimitedTooltip`
  - неиспользуемый селектор `setRoadmapFocus`

### 3.2 Неразрешенные разрывы
1. Workflow source arbitration размытый (`dag` vs `pipeline fallback` vs `template`).
2. Inline workflow рендерится локально, но schema-contract (fixed layered order) не зафиксирован полностью.
3. При inline workflow подсветка связей отключается целиком (не всегда желаемо).
4. Folder drill может выдавать бедный срез при sparse-edges (хоть path-fallback и добавлен).
5. Legacy panel dependency: `MiniTasks(expanded)` -> deprecated `MCCTaskList`.
6. Депрекейт-компоненты остаются в дереве (`WorkflowToolbar`, `RailsActionBar`, `MCCDetailPanel`, `TaskDAGView`) и увеличивают риск двойной логики.

### 3.3 Замурованные/legacy поверхности
- `client/src/components/mcc/MCCTaskList.tsx` (deprecated, но еще активен через MiniTasks expanded)
- `client/src/components/mcc/WorkflowToolbar.tsx` (deprecated)
- `client/src/components/mcc/RailsActionBar.tsx` (deprecated)
- `client/src/components/mcc/MCCDetailPanel.tsx` (deprecated)
- `client/src/components/mcc/TaskDAGView.tsx` (по факту мимо основного пути)

## 4. Точный implementation roadmap (по 6 механикам)

## P0 — Contract Lock (обязательно)

1. Drill-down contract hardening
- Что: единый контракт single-click select / double-click toggle / empty-click clear.
- Где: `DAGView.tsx` + `MyceliumCommandCenter.tsx`.
- Маркеры: `G24.CLICK_DBLCLICK_DEBOUNCE`, `G24.DRILL_TOGGLE_SINGLE_SOURCE`.
- Готово когда: нет скрытого zoom-side-effect, toggle обратим и детерминирован.

2. Workflow source arbitration v1
- Что: ввести явный приоритет источников:
  1) `dagNodes` (если валидный workflow graph),
  2) `template fallback`,
  3) `pipeline fallback`.
- Где: блок `graphForView` в `MyceliumCommandCenter.tsx`.
- Маркеры: `G24.WF_SOURCE_FANOUT`, `G24.WF_SOURCE_ARBITRATION`, `G24.WF_TEMPLATE_KEY_POLICY`.
- Готово когда: одинаковый task всегда открывает один и тот же workflow shape.

3. Size control contract
- Что: зафиксировать mini-size в node components как единственный визуальный канал масштаба.
- Где: `dagLayout.ts` + `nodes/*.tsx`.
- Маркер: `G24.NODE_SIZE_CONTROL_PATH`.
- Готово когда: изменение mini-scale всегда влияет на реальные карточки.

## P1 — Focus + Context / Local Relayout

1. Focus contract without full bypass
- Что: для inline workflow оставить контекст архитектуры, но вернуть частичную подсветку выбранных связей.
- Где: `DAGView.tsx` highlighting effect.
- Маркер: `G24.HIGHLIGHT_BYPASS_WHEN_INLINE`.
- Готово когда: выделение не пропадает полностью при inline workflow.

2. Local push boundaries
- Что: ограничить push-region и добавить cap на cumulative shift в кадре.
- Где: `DAGView.tsx` `LOCAL_PUSH_V1` block.
- Готово когда: соседние ветки не улетают, overlay не превращается в "кашу".

3. Incremental layout policy tune
- Что: адаптивный режим reuse/reset для architecture + overlay.
- Где: `DAGView.tsx` `INCREMENTAL_LAYOUT_ARBITRATION`.
- Готово когда: нет sink-drift и нет резких глобальных пересборок.

## P2 — Auto-collapse / Threshold / Breadcrumb

1. Threshold policy formalization
- Что: depth/breadth caps + +N overflow badges для folder/task drill.
- Где: `overlayRoadmapNodeChildren` + node renderers.
- Готово когда: large branch не создает визуальный шум.

2. Breadcrumb unification
- Что: единый path для task drill и folder drill в `MCCBreadcrumb`.
- Где: `MCCBreadcrumb.tsx` + store drill context.
- Готово когда: путь всегда объясняет, где находится пользователь.

3. Lazy unfold consistency
- Что: очищать временные inline-узлы строго на collapse и при смене anchor.
- Где: `MyceliumCommandCenter.tsx` state transitions.
- Готово когда: нет артефактов от предыдущего раскрытия.

## P3 — Cleanup Wave (legacy/замурованное)

1. Развязать `MiniTasks(expanded)` от `MCCTaskList`.
- Маркер: `G24.LEGACY_EXPANDED_TASK_PANEL`.

2. Удалить или вынести в `archive/` deprecated UI:
- `WorkflowToolbar.tsx`
- `RailsActionBar.tsx`
- `MCCDetailPanel.tsx`
- `TaskDAGView.tsx` (если не используется в runtime path)

3. Привести action semantics в `LEVEL_CONFIG` к контекстной терминологии.
- Маркер: `G24.ACTION_SEMANTICS_REVIEW`.

## 5. Проверочный чек (GO/NO-GO)

1. Двойной клик по task overlay всегда раскрывает/сворачивает один и тот же workflow.
2. Раскрытие workflow не открывает второе окно и не меняет route/nav level.
3. При раскрытии нет глобального уезда камеры и массового исчезновения дерева.
4. При клике на пустое место выделение сбрасывается стабильно после N повторов.
5. Folder drill показывает группу детей (не одиночный случайный узел), с порогами.
6. Inline workflow визуально меньше архитектурных узлов и читается как отдельный слой.
7. Legacy-путь `MCCTaskList` не является обязательной зависимостью core-flow.
8. В dev-сборке нет новых runtime warning/error по циклам state update.

## 6. Ответ на вопрос “нужно ли еще расширять каждый пункт?”

Да, может помочь, но уже не обязательно для старта.
Текущий документ уже достаточно конкретен, чтобы идти в имплементацию волнами P0->P1->P2->P3.
Если нужно, отдельно можно выпустить `P0 execution sheet` (таблица: шаг, файл, функция, тест-кейс, expected diff).
