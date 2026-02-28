# MCC Drilldown Stage Success Rulebook (2026-02-28)

## Статус этапа
Этап стабилизации single-canvas drilldown в MCC закрыт как успешный.

Цель этапа:
1. Убрать хаотичное поведение inline workflow DAG.
2. Зафиксировать матрешку в одном окне без перехода в отдельный экран.
3. Ввести понятную геометрию связей и предсказуемую физику раскрытия.
4. Закрепить изменения маркерами и регресс-тестами.

## Что реализовано
1. Введен `reserved workflow frame` (невидимый «столик») для inline workflow около выбранной task-ноды.
2. Включен канонический layout inline workflow с детерминированной раскладкой и анти-spaghetti фильтрацией ребер.
3. Зафиксирована логика top/bottom handle routing (геометрический контракт).
4. Исправлен приоритет раскрытия: node-drill не конфликтует с task-drill.
5. Санитизация pin-координат для временных inline-узлов (`wf_`, `rd_`), чтобы не было разлета.
6. Мини-слой (workflow/rd) визуально облегчён: меньше handles, тоньше линии, меньше шрифтовый вес.
7. Ориентация inline workflow переведена в bottom-up (старт от task снизу, результат выше).

## Законы (контракты) этапа
1. Single-canvas law:
Весь drilldown работает в одном canvas MCC. Новое окно не открывается.

2. Reserved frame law:
Inline workflow всегда рендерится внутри фиксированного reserved frame рядом с task.

3. Geometry law:
Глобально: вход в ноду снизу (`target-bottom`), выход из ноды вверх (`source-top`).

4. Task linkage law:
Связи file/folder -> task входят в `target-bottom` task-карточки.

5. Workflow bridge law:
Bridge task->workflow выходит из верхней точки task и входит в нижнюю точку entry workflow-ноды.

6. Node drill law:
Раскрытие обычной ноды (папка/модуль) имеет приоритет над task drill при non-task double-click.

7. Inline pin law:
Persisted pins для `wf_`/`rd_` не применяются, чтобы временные слои не «залипали» и не ломали frame-физику.

8. Bottom-up workflow law:
В roadmap inline workflow раскладывается снизу вверх: старт ниже, финальные стадии выше.

## Визуальные правила
1. Размер карточек inline workflow не уменьшать дальше текущего минимума без отдельного визуального согласования.
2. Уменьшать сначала не площадь, а визуальный вес (толщина рамки, размер handles, шрифт).
3. Разрежение добивается увеличением межузлового шага в layout, а не хаотическим push всего графа.
4. Пунктирные bridge/inline edges должны быть слабее по контрасту, чем структурные ребра архитектуры.

## Маркеры, добавленные/актуализированные в этом этапе
1. `MARKER_155A.G26.WF_CANONICAL_LAYOUT`
2. `MARKER_155A.G26.WF_CANONICAL_PACKING`
3. `MARKER_155A.G26.WF_EDGE_PRUNE_CANONICAL`
4. `MARKER_155A.G26.WF_MINI_SCALE_MICRO`
5. `MARKER_155A.G26.WF_ANCHOR_ROOT_LOCK`
6. `MARKER_155A.G26.NODE_DRILL_RICHER_PATH_FALLBACK`
7. `MARKER_155A.G27.RESERVED_WORKFLOW_FRAME`
8. `MARKER_155A.G27.PIN_SANITIZE_INLINE`
9. `MARKER_155A.G27.NODE_DRILL_PRIORITY`
10. `MARKER_155A.G27.MICRO_HANDLE_DOWNSCALE`
11. `MARKER_155A.G27.GLOBAL_HANDLE_FLOW`
12. `MARKER_155A.G27.WF_BOTTOM_UP_ORIENTATION`

## Последовательность ключевых коммитов (этот этап)
1. `4e2aa6d6` canonicalize inline workflow micro-dag + prune spaghetti
2. `f5490a29` richer node-drill path fallback
3. `2d0182ea` root lock to selected task anchor
4. `02972662` reserved workflow frame + micro-scale inline rendering
5. `e79d2e6e` stabilize frame + micro overlay interactions
6. `3baabb83` top/bottom handle anchor routing
7. `e962f21e` global top-output bottom-input geometry
8. `ecd4ac32` bottom-up workflow orientation
9. `aa1f2420` frame spacing + compact inline labels
10. `206e20c7` restore inline card area + reduce border/font weight

## Регресс-контроль
1. Основной контракт-тест: `tests/test_phase155_p0_drilldown_markers.py`
2. Последний прогон: `20 passed`.
3. Любой следующий визуальный тюнинг делать только при сохранении маркер-контрактов.

## Что нельзя ломать на следующем шаге
1. Нельзя возвращать отдельное workflow-окно вместо inline матрешки.
2. Нельзя отключать reserved frame.
3. Нельзя снимать global handle flow contract (top output / bottom input).
4. Нельзя смешивать одновременно expanded task-drill и expanded node-drill без явной арбитрации.

## Next-step рекомендации
1. Делать микро-тюнинг только параметрами (`xGap`, `yGap`, stroke width, font scale).
2. Не трогать общую структуру DAG pipeline без отдельного RFC.
3. Для спорных UX-изменений фиксировать before/after скрины и отдельный mini-changelog.

