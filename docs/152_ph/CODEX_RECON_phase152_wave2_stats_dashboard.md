# CODEX RECON — Phase 152 Wave 2 (152.5 + 152.6)

## Protocol
RECON выполнен. Имплементация НЕ начиналась.

## Scope
- 152.5 `StatsDashboard.tsx`
- 152.6 `TaskDrillDown.tsx`

## MARKERS (проверенные точки)
- `MARKER_152.W2.API_READY`: backend роуты готовы в `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/analytics_routes.py`
  - `/summary`, `/task/{task_id}`, `/agents`, `/trends`, `/cost`, `/teams` подтверждены.
- `MARKER_152.W2.STATS_TAB_ENTRY`: текущий Stats-tab рендерит `PipelineStats` в `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/panels/DevPanel.tsx`.
- `MARKER_152.W2.COMPACT_KEEP`: compact-режим `PipelineStats` используется в `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MCCDetailPanel.tsx` (оставить).
- `MARKER_152.W2.TASKCARD_DEAD`: `TaskCard.tsx` сейчас не используется в JSX-дереве (поиск `'<TaskCard'` пустой).
- `MARKER_152.W2.ACTUAL_TASK_ENTRY`: реальная точка задач — `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MCCTaskList.tsx`.
- `MARKER_152.W2.RECHARTS_OK`: `recharts@3.7.0` уже установлен, dependency добавлять не нужно.
- `MARKER_152.W2.BASELINE_TS_ISSUE`: общий `client build` уже падает на несвязанном файле `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/NodeInspector.tsx:71`.

## Выводы без гаданий
1. Brief-указание «добавить кнопку в TaskCard» конфликтует с фактом: `TaskCard` не участвует в текущем UI.
2. Для 152.6 корректная интеграция drill-down должна идти через `MCCTaskList` (кнопка/триггер на выбранной задаче).
3. Для 152.5 безопасно:
   - сделать новый `StatsDashboard.tsx`,
   - подключить его только в `DevPanel` (tab `stats`),
   - не трогать `PipelineStats` compact-path.

## Узкий план IMPL (после GO)
1. Создать `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/panels/StatsDashboard.tsx`:
   - fetch 5 analytics endpoint-ов,
   - loading/error-safe рендер,
   - `mode: 'compact' | 'expanded'`.
2. Подключить `StatsDashboard` в `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/panels/DevPanel.tsx` вместо expanded `PipelineStats`.
3. Создать `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/panels/TaskDrillDown.tsx`.
4. Интегрировать открытие модалки в `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MCCTaskList.tsx` (а не в `TaskCard.tsx`, который мертвый).
5. VERIFY точечно по файлам (`npx tsc --noEmit ...StatsDashboard.tsx ...TaskDrillDown.tsx ...MCCTaskList.tsx ...DevPanel.tsx`).

## Что уже сделано в этой итерации
- Отдельный коммит за 152.7/152.8: `774556bc` (push выполнен).
