# MCC RECON AUDIT: Workflow Drill/Inline DAG

Date: 2026-02-27
Scope: `client/src/components/mcc/MyceliumCommandCenter.tsx`, `client/src/components/mcc/DAGView.tsx`, `client/src/utils/dagLayout.ts`, workflow node renderers.

## Executive Summary

Root cause подтвержден: поведение workflow-drill расползлось между несколькими слоями (state machine в MCC, layout+visual policies в DAGView, fallback graph builders), из-за чего правки накладываются друг на друга и дают противоречивый эффект.

Ключевой факт: проблема не в одном баге, а в конфликте трех механизмов одновременно:
1. Авто-раскрытие через `selectedTaskId` (MCC).
2. Ручной toggle через double-click (MCC+DAGView).
3. Глобальный post-layout для архитектуры, в который «вшит» workflow mini-layer (DAGView).

---

## Findings (по критичности)

### P0-1. Drill state machine конфликтует сама с собой
- File: `MyceliumCommandCenter.tsx`
- Marker: `MARKER_155A.P2.DRILL_POLICY` / `taskDrillState`
- Evidence:
  - Авто-раскрытие при смене `selectedTaskId` (`setTaskDrillState('expanded')` в эффекте около 1493-1503).
  - Ручной toggle в `handleLevelAwareNodeDoubleClick` (около 2092-2102).
  - Дополнительный toggle по keyboard `onDrillTask` (около 2246-2254).
- Impact:
  - Нельзя гарантировать единственный источник истины для раскрытия.
  - Single-click/select может неявно приводить к раскрытию, даже если UX контракт «только double-click».

### P0-2. Workflow visual policy зашит в architecture layout pass
- File: `DAGView.tsx`
- Marker: блок `if (layoutMode === 'architecture')` + workflow section (`wf_` around 310+).
- Evidence:
  - Размещение `wf_*` делается внутри того же post-layout блока, что и архитектурные ноды.
  - В том же цикле идет «расталкивание» соседних веток.
- Impact:
  - Любая правка архитектурного layout влияет на workflow.
  - Получается «смешивание» вместо изолированного фрактального слоя.

### P0-3. Некорректный контракт данных для мини-нод
- File: `MyceliumCommandCenter.tsx` + `dagLayout.ts`
- Marker: `MARKER_155A.P0.WF_MINI_LAYER`
- Evidence:
  - В `overlayWorkflowOnSelectedTask` добавляются `width/height` в `DAGNode` (около 648+), но базовый `DAGNode` тип этих полей не содержит.
  - В реальном рендере размеры нод определяются компонентами (`AgentNode/SubtaskNode/ProposalNode`) и/или dag layout, а не произвольным полем ноды.
- Impact:
  - Часть правок «не туда»: кажется, что размер задается, но UI не обязан его учитывать.
  - Повышает шум и вводит в заблуждение при отладке.

### P0-4. Непрозрачный fallback pipeline для workflow
- File: `MyceliumCommandCenter.tsx`
- Markers: fallback effects around 1420-1490
- Evidence:
  - Одновременно существуют 3 источника workflow:
    1) live `dagNodes/dagEdges`,
    2) `buildInlineWorkflowFromPipeline` из `/debug/pipeline-results`,
    3) `buildInlineWorkflowFromTemplate` из `/mcc/workflows/{key}`.
  - Выбор делается эвристикой (`hasDetailedWorkflow`, сравнение длин template vs pipeline).
- Impact:
  - Непредсказуемая смена формы DAG при одинаковом UX действии.
  - Сложно стабильно воспроизвести баг/фикс.

### P1-1. Дубли и наложения в DAGView
- File: `DAGView.tsx`
- Evidence:
  - `hasInlineWorkflow` вычисляется дважды (в `fractalNodes useMemo` и отдельно через `useMemo` около 448 и 478).
  - Highlight effect и fractal dim effect оба управляют `opacity`, но по разным условиям.
- Impact:
  - Поведение opacity/подсветки зависит от порядка эффектов, легко поймать регресс.

### P1-2. Async click timer использует `event.shiftKey` внутри `setTimeout`
- File: `DAGView.tsx` around onNodeClick
- Evidence:
  - Значение `event.shiftKey` считывается в delayed callback.
- Impact:
  - Потенциально хрупко (зависит от жизненного цикла synthetic event/окружения).
  - Нужно snapshot (`const additive = !!event.shiftKey`) до таймера.

### P1-3. Избыточная агрессивность dimming при inline workflow
- File: `DAGView.tsx` around `fractalNodes`
- Evidence:
  - При наличии `wf_*` вся не-workflow сцена получает `opacity: 0.18`.
- Impact:
  - Пользователь воспринимает как «дерево пропало».

### P2-1. Монолитность файлов блокирует безопасные правки
- `MyceliumCommandCenter.tsx`: ~3280 LOC
- `DAGView.tsx`: ~933 LOC
- `dagLayout.ts`: ~644 LOC
- Impact:
  - Высокий риск побочных эффектов даже от точечных фиксов.
  - Рефакторинг нужен для снижения MTTR.

---

## Dead/Noise Code Candidates (кандидаты на чистку)

1. `AUTO_DRILL_ZOOM` флаг: в текущем скоупе используется не как единый gate всех zoom side-effects.
2. `bridgeEdges` в `overlayWorkflowOnSelectedTask`: сейчас всегда пустой массив — можно убрать до момента реального bridge policy.
3. Поля `width/height` в remapped workflow node: удалить из overlay-функции, если не вводим их официально в тип и рендер-контракт.
4. Дублирующие вычисления `hasInlineWorkflow` в DAGView.
5. Разнести dim policy и edge-highlight policy, чтобы не конкурировали за один и тот же визуальный канал.

---

## Confirmed Root Cause For “Wrong tables changed”

Причина подтверждена:
- мы меняли «геометрию workflow» и одновременно пытались менять «визуальный размер нод» в другом слое.
- первый слой: layout spacing (`xGap/yGap`) — влияет на расстояния;
- второй слой: node renderer styles (`minWidth/padding/fontSize`) — влияет на размеры карточек.

Из-за неполного data-contract (непрозрачный флаг mini) правки попадали не на тот слой.

---

## Narrow Refactor Plan (следующий шаг)

### Step A (P0, безопасно)
- Ввести единый drill reducer/state machine:
  - `collapsed | expanded` только через явные события: `TASK_DBLCLICK`, `ESC`, `TASK_CHANGED`.
  - Убрать авто-раскрытие из эффекта `selectedTaskId`.

### Step B (P0)
- Вынести workflow layout в отдельную pure-функцию:
  - input: `workflowNodes/Edges`, `overlayAnchorPos`
  - output: positioned micro-layer
  - без side-effect “push architecture nodes”.

### Step C (P1)
- В DAGView оставить один визуальный policy layer:
  - либо dim, либо highlight (не одновременно как сейчас).

### Step D (P1)
- Нормализовать data contract:
  - `data.render = { mini: true, kind: 'workflow' }`
  - убрать ad-hoc поля на корне `DAGNode` без type support.

---

## Marker Inventory Added/Relevant

- `MARKER_155A.P0.WF_MINI_LAYER` (current experimental micro-layer path)
- `MARKER_155A.P2.DRILL_POLICY` (current drill keyboard/click policy)
- `MARKER_155A.G21.SINGLE_CANVAS_STATE` (shared canvas contract)

