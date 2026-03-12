# PHASE 155A — Grandma Mode UX Roadmap (2026-03-02)

Status: `ROADMAP (pre-implementation)`  
Protocol: `ROADMAP -> RECON+markers -> WAIT GO -> IMPL NARROW -> VERIFY`

## 1) Product Principles (hard constraints)
1. Grandma mode: максимум 3 явных действия в основном экране.
2. Удаляем визуальный шум и неочевидные контролы.
3. Никаких новых постоянных кнопок в canvas.
4. Продвинутые/диагностические действия только через `gear/dev panel`.
5. Цветовая политика: красный цвет под запретом (до отдельного разрешения).
6. Стиль: минималистичный, функциональный, графически очевидный.

## 2) Visual/Design Policy
1. Сохраняем существующий стиль MCC как базу (не делаем новый дизайн с нуля).
2. Иконки:
   - сначала переиспользуем готовые `png/svg` из VETKA,
   - если нет, создаем простые белые `svg`.
3. Контраст и читаемость выше декоративности.
4. Маркеры ошибок/диагностики не должны красить основной UI в тревожный режим.
5. Элементы с непонятной ценностью для пользователя удаляются или уезжают в dev panel.

## 3) Current Noise To Remove (from screenshots)
1. Дублирующая строка task в шапке (верхняя инфополоса) — убрать.
2. Непрозрачные индикаторы/кнопки без явной пользы:
   - `SOURCE: RUNTIME · ERROR` в основном UI -> убрать из user surface (оставить в dev diagnostics).
3. Плавающие/малообъяснимые мини-кнопки в углах (если не являются core-action) -> убрать.

## 4) Mini-Window Set (target)
1. `MiniTasks` (остается)
2. `MiniStats` (остается, становится context-aware)
3. `MiniChat` (остается, становится context-aware)
4. `MiniBalance` (остается)
5. `MiniContext` (новое окно, универсальный “глаз”, аналог artifact-view)

## 5) Context Routing Matrix (single-canvas behavior)
1. Click `file node`:
   - `MiniContext`: содержимое файла + метаданные + связи + артефакты.
   - `MiniStats`: file-scope.
   - `MiniChat`: file-context.
2. Click `agent/workflow node`:
   - `MiniContext`: модель, статус, stream-state, preprompt, behavior profile.
   - `MiniStats`: model/agent-scope.
   - `MiniChat`: architect-in-workflow context.
3. Click `task node`:
   - `MiniContext`: task card + workflow links + outputs/artifacts.
   - `MiniStats`: team/task-scope.
   - `MiniChat`: чат архитектора команды задачи.
4. Click `root/empty canvas`:
   - `MiniContext`: project summary.
   - `MiniStats`: project-wide.
   - `MiniChat`: чат архитектора всего проекта.

## 6) Architect UX Contract (corrected)
1. Модель архитектора выбирается строго по ключу, выбранному пользователем в `MiniBalance`.
2. Не по “всем доступным ключам” и не автоматически “по лучшему”.
3. В `MiniContext` для architect node видны:
   - текущая модель,
   - preprompt/сценарий,
   - режим поведения (template/policy).

## 7) Workflow Truth + Editability
1. Проверяем соответствие отображаемого DAG реальному runtime execution.
2. Вводим режим truth-overlay:
   - `design edges` vs `runtime observed edges`.
3. Пользователь может редактировать/добавлять связи (edge editing) с валидацией.
4. Импорт из `n8n`:
   - сохраняем типы нод/связей как есть,
   - MCC view не должен ломать семантику исходного workflow.
5. `Grandma mode` contract:
   - для workflow-режима единственный источник истины: `runtime`,
   - режимы `design/predict` не участвуют в пользовательском workflow UX,
   - `design/predict` допустимы только как dev-диагностика для архитектурного DAG.

## 8) Team/Template Configuration
1. Явная настройка состава команды и порядка ролей (Ralph, G3, internal template).
2. Явный policy, как Architect создает команды по запросу пользователя.
3. Для каждой роли видим:
   - assigned model,
   - preprompt,
   - execution order.

## 9) Execution Waves
1. Wave A (UI cleanup + context shell):
   - remove noise + duplicate task strip
   - add `MiniContext` shell
   - basic selection routing
2. Wave B (context-aware windows):
   - `MiniStats` full node-aware
   - `MiniChat` scope routing (task/team/project)
   - stream filtering by scope
3. Wave C (agent/model controls):
   - model edit bind in `MiniContext`
   - architect model bound to selected balance key
   - preprompt/behavior visibility
4. Wave D-RUNTIME (workflow runtime truth):
   - workflow runtime-only truth in grandma mode
   - retry/feedback readability in mini-windows
   - source-mode guard (`runtime` forced for workflow focus)
5. Wave E (n8n landing + templates):
   - n8n type-preserving landing
   - team/template config for Ralph/G3/internal

## 10) Definition of Done (Roadmap-level)
1. Пользователь без тех. контекста понимает, где смотреть статус и где менять поведение.
2. В основном UI нет неочевидных кнопок/индикаторов.
3. Один клик по ноде всегда меняет контекст окон предсказуемо.
4. Workflow отображает и исполняет только runtime truth в пользовательском режиме.

## 11) Next-Phase TODO (pipeline debug + workflow families)
1. Отдельная фаза отладки pipeline truth:
   - сверка runtime-ветвления vs визуальный DAG по реальным событиям,
   - проверка retry/feedback циклов и условий gate,
   - верификация ролей `verifier`/`eval` и их фактических сигналов (`pass/fail` vs `score`).
2. Унификация workflow-библиотеки (архитектурные семейства):
   - `BMAD`,
   - `Ralph-loop`,
   - `G3 (critic/coder)`,
   - `OpenHands-inspired` оркестрация,
   - `Pulse` (не музыкальный): multi-objective scheduling для cloud-edge-IoT.
3. Для каждого семейства:
   - контракт ролей/узлов/edges,
   - шаблон импорта/экспорта,
   - policy выбора модели и preprompt,
   - правила truth-overlay и drift-диагностики.
4. Ограничение исполнения:
   - в рамках Phase 155A не расширяем pipeline-фичи до полного мульти-family runtime,
   - только фиксируем TODO и готовим интерфейсные посадочные места.
5. Debug tail (regression watch):
   - восстановить и зафиксировать контракт `MiniChat model button -> open MiniContext model chooser`,
   - добавить UI-contract тест, чтобы повторно не ломалось.
