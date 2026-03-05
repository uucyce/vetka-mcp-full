# PHASE 162 — MCC MYCO Helper (Context Guide) Architecture Plan (2026-03-05)

Status: `ROADMAP + RECON MARKERS`
Protocol: `RECON -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## 0) Что думаю (коротко)
Идея правильная и своевременная: это не "косметика", а обязательный слой объяснимости (comprehension layer) для grandma-mode.
Нужен именно контекстный guide, который объясняет текущий LOD/viewport и действие пользователя, а не еще один постоянный шумный UI-элемент.

## 1) Выделенные пункты из твоего потока (as requirements)
1. Нужен helper-режим (вкл/выкл), без постоянного навязывания.
2. Helper должен понимать контекст интерфейса:
- где пользователь: дерево, workflow, конкретная нода, панель;
- что выбрано;
- какой viewport (камера/видимая область/LOD).
3. На клик по объектам helper должен объяснять "что это" и "что можно сделать дальше".
4. Сообщения helper должны идти в чат (не отдельный тяжелый UI поток).
5. При включении helper в чате появляется отдельная роль (рабочее имя: `MYCO`).
6. Для LLM-режима helper должен использовать viewport/context-pack, как в VETKA (технология already proven).
7. Должен работать и rule-based fallback (без LLM), чтобы не ломаться на пустых ключах/API.
8. Нужен минималистичный визуальный персонаж/иконка в стиле MCC (без красного, белый SVG/PNG для Tauri).
9. Нужно связать helper с элементами MCC через явный map (что helper знает о каждом компоненте).
10. Нужен отдельный фазовый roadmap + исследовательский чеклист перед имплементацией.

## 2) Naming decision
Рабочее имя для фазы: `MYCO`.
- Внутренняя роль: `helper_myco`.
- UI label: `MYCO`.
- Event namespace: `mcc-myco-*`.

## 3) Scope boundaries (чтобы не расползлось)
### In scope (Phase 162)
1. Toggle helper mode (`OFF / PASSIVE / ACTIVE`).
2. Context ingest: nav level + selected node + focus scope + viewport snapshot.
3. Chat integration: сообщения MYCO в существующий MiniChat/expanded chat.
4. Rule-first guidance templates для основных сущностей (project/task/agent/file/workflow).
5. Optional LLM enhancer (if API/ключ доступен), но не обязательный.
6. UI icon + helper badge в рамках текущего minimalist style.

### Out of scope (для этой фазы)
1. Автоперестройка pipeline.
2. Автоматическое редактирование DAG helper-ом.
3. Новый отдельный "assistant panel" поверх существующих mini-window.
4. Полный мультиязычный tutoring engine.

## 4) Proposed architecture
## 4.1 Data flow
1. UI events -> `MYCO Controller`
2. `MYCO Controller` собирает:
- `navLevel`
- `selectedNodeId/Ids`
- `node metadata`
- `focusScopeKey`
- `workflowSourceMode`
- `viewport snapshot` (zoom, visible nodes count, center)
3. `Context Builder` нормализует payload.
4. `Decision Engine`:
- сначала rules/templates;
- затем optional LLM enrichment.
5. Output -> chat message (`role: helper_myco`).

## 4.2 Modes
1. `OFF`: helper выключен.
2. `PASSIVE`: отвечает только по явному запросу/кнопке.
3. `ACTIVE`: реагирует на клики и смену контекста короткими подсказками.

## 4.3 Contracts (new markers)
1. `MARKER_162.MYCO.MODE_TOGGLE.V1`
2. `MARKER_162.MYCO.VIEWPORT_CONTEXT_PAYLOAD.V1`
3. `MARKER_162.MYCO.CHAT_ROLE_INJECTION.V1`
4. `MARKER_162.MYCO.RULES_FALLBACK.V1`
5. `MARKER_162.MYCO.LLM_ENRICHMENT_OPTIONAL.V1`
6. `MARKER_162.MYCO.UI_ICON_BIND.V1`
7. `MARKER_162.MYCO.NODE_HELP_MAP.V1`

## 5) What to research before implementation
1. Текущий viewport payload в VETKA: формат, частота, объём.
2. Точки в MCC, где уже есть достаточно контекста (без дорогой пересборки).
3. Где лучше встраивать helper role в chat store, не ломая architect role.
4. Минимальный event bus контракт для click/hover/focus changes.
5. Ограничения Tauri по SVG/PNG иконке в текущем стекe.

## 6) What to write/spec first
1. `MYCO_CONTEXT_PAYLOAD_CONTRACT_V1.md`
2. `MYCO_HELP_RULES_LIBRARY_V1.md`
3. `MYCO_CHAT_ROLE_CONTRACT_V1.md`
4. `MYCO_ICON_STYLE_GUIDE_V1.md`
5. `MYCO_TEST_MATRIX_V1.md`

## 7) Full checklist (implementation-ready)
1. Добавить store-поле `helperMode` (`off|passive|active`).
2. Добавить lightweight `useViewportContext` hook.
3. Добавить controller, подписанный на select/camera/nav events.
4. Добавить rule-engine (локальные шаблоны подсказок).
5. Добавить optional LLM enhancer (guarded by key/provider).
6. Прокинуть helper messages в chat stream с ролью `helper_myco`.
7. Добавить toggle-кнопку helper в существующий UX слой (без нового постоянного окна).
8. Добавить icon asset (white minimal mushroom/question mark), no red.
9. Добавить map "node kind -> guidance template".
10. Покрыть тестами:
- mode toggle contract;
- payload completeness;
- chat role injection;
- fallback without LLM;
- no-noise behavior in OFF mode.

## 8) Risks and controls
1. Risk: helper начнет спамить.
- Control: rate-limit + concise mode + passive default.
2. Risk: helper ломает основной чат.
- Control: отдельная role, без изменения architect pipeline.
3. Risk: expensive context every click.
- Control: context budget + debounce + viewport summary, not raw dump.
4. Risk: визуальный шум.
- Control: один toggle + chat output only.

## 9) Sequencing with current workstream
1. Не блокируем текущий Phase 155 runtime-flow.
2. Делаем MYCO как отдельную фазу (`162`) параллельно, через контракты и узкие шаги.
3. После утверждения roadmap: начинаем с `P0 contracts + P1 passive mode`.

## 10) GO gate for implementation
Start implementation only after explicit command:
`GO 162-P0`.
