# PHASE 155A — Grandma Mode RECON + Markers (2026-03-02)

Status: `RECON + markers`  
Source roadmap: `PHASE_155A_GRANDMA_MODE_ROADMAP_2026-03-02.md`  
Detailed Wave A recon: `PHASE_155A_WAVE_A_DETAILED_RECON_2026-03-02.md`  
Protocol: `RECON + markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## 1) Scope Baseline
Confirmed gaps (UX/runtime truth layer):
1. `MARKER_155A.P3.NODE_CONTEXT_WINDOW` — not done
2. `MARKER_155A.P3.MODEL_EDIT_BIND` — not done
3. `MARKER_155A.P3.STATS_CONTEXT` — partial
4. `MARKER_155A.P3.STREAM_CONTEXT` — not done
5. `MARKER_155A.P4.CONFLICT_POLICY` — not done

Additional scope from current analysis:
6. visual noise cleanup
7. architect model binding to selected balance key
8. workflow runtime-only truth (Grandma mode)
9. user edge editing + n8n landing compatibility (deferred after Wave D-RUNTIME)

## 2) Marker Set (new)

### 2.1 Wave A — UI cleanup + context shell
1. `MARKER_155A.WA.UI_NOISE_CLEANUP.V1`
2. `MARKER_155A.WA.DUPLICATE_TASK_STRIP_REMOVE.V1`
3. `MARKER_155A.WA.MINICONTEXT_SHELL.V1`
4. `MARKER_155A.WA.SELECTION_ROUTER_BASE.V1`
5. `MARKER_155A.WA.COLOR_POLICY_NO_RED.V1`

### 2.2 Wave B — context-aware windows
1. `MARKER_155A.P3.NODE_CONTEXT_WINDOW.V2`
2. `MARKER_155A.P3.STATS_CONTEXT.V2`
3. `MARKER_155A.P3.STREAM_CONTEXT.V2`
4. `MARKER_155A.WB.CHAT_SCOPE_ROUTING.V1`

### 2.3 Wave C — model/prompt controls
1. `MARKER_155A.P3.MODEL_EDIT_BIND.V2`
2. `MARKER_155A.WC.ARCH_MODEL_BIND_SELECTED_BALANCE_KEY.V1`
3. `MARKER_155A.WC.PREPROMPT_BEHAVIOR_VIEW.V1`

### 2.4 Wave D-RUNTIME — workflow runtime truth
1. `MARKER_155A.WD.WORKFLOW_RUNTIME_ONLY_TRUTH.V1`
2. `MARKER_155A.WD.RUNTIME_PIPELINE_RETRY_EDGE.V1`
3. `MARKER_155A.WD.RUNTIME_APPROVAL_GATE_COMPACT.V1`
4. `MARKER_155A.P4.CONFLICT_POLICY.V2` (gear-only, no new user-surface controls)

### 2.5 Wave E — n8n and templates
1. `MARKER_155A.WE.N8N_TYPE_PRESERVATION.V1`
2. `MARKER_155A.WE.TEAM_TEMPLATE_CONFIG.V1`
3. `MARKER_155A.WE.ARCH_TEAM_POLICY_BIND.V1`

## 3) Recon Checks Per Wave

### Wave A recon checks
1. Найти все места дублирования task summary в шапке.
2. Найти источники `SOURCE: ... ERROR` и решить перенос в dev-only слой.
3. Проверить текущую систему окон и точку внедрения `MiniContext`.
4. Провести инвентаризацию иконок:
   - reuse из VETKA assets,
   - fallback simple white svg.

### Wave B recon checks
1. Карта типов нод в MCC DAG (file/agent/task/gate/root).
2. Проверить текущий `selectedNodeId` pipeline в store -> windows.
3. Проверить stream feed источник и возможность фильтрации по scope.
4. Зафиксировать chat context routing contract:
   - task click -> task architect chat
   - empty/root -> project architect chat.

### Wave C recon checks
1. Где сейчас хранится role->model binding.
2. Где хранится выбранный key в `MiniBalance` и как связать с architect role.
3. Где лежат preprompts/role prompts и как безопасно их показывать/редактировать.

### Wave D-RUNTIME recon checks
1. Сопоставление runtime events и отрисованных edges (gap map).
2. Проверка retry/feedback визуализации (обратная дуга к coder, без retry-node дубля).
3. Проверка компактного approval gate (без group-оверлея).
4. Проверка runtime-only контракта для workflow: в пользовательском режиме не допускается переключение на design/predict.

### Wave E recon checks
1. Карта типов n8n нод/связей, которые уже импортируются.
2. Где теряется семантика при посадке в MCC DAG.
3. Контракт template/team policy (Ralph/G3/internal) и точка интеграции с Architect.

## 4) DoD By Wave (implementation gate)

### Wave A DoD
1. Удален визуальный шум из user surface.
2. Удален дубликат task strip.
3. `MiniContext` рендерится и реагирует на selection.
4. В основных компонентах нет красного UI для статусов.

### Wave B DoD
1. Все 5 типов клика меняют `MiniContext/Stats/Chat` предсказуемо.
2. Stream фильтр работает по текущему контексту.
3. Пустой canvas корректно переключает на project scope.

### Wave C DoD
1. Модель архитектора выбирается только от ключа, выбранного в `MiniBalance`.
2. Изменение модели роли применимо из `MiniContext`.
3. Видны preprompt и behavior для role node.

### Wave D-RUNTIME DoD
1. Workflow работает в runtime-only truth режиме (Grandma mode), без design/predict в пользовательском потоке.
2. Retry path читается явно как feedback loop (dashed) к coder.
3. Approval gate отображается компактно и не перекрывает граф.
4. Conflict policy управляется только через gear.
5. User edge editing вынесен в следующую фазу (после шаблонного блока G3/Ralph/n8n/OpenHands/Pulse).

### Wave E DoD
1. Импорт n8n не теряет типы/ключевые связи.
2. Team/template policy управляется и прозрачно отображается.
3. Architect использует выбранный template policy при генерации команды.

## 5) Recommended Implementation Order
1. `WA` -> `WB` -> `WC` -> `WD` -> `WE`
2. На каждом wave: сначала RECON report, потом узкая имплементация.
