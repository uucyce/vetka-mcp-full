MARKER_163.MYCO.VETKA.HELP_HINT_LIBRARY.V1
LAYER: L3
DOMAIN: UI|CHAT|AGENTS|VOICE|MEMORY
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_VETKA_HELP_HINT_LIBRARY_V1.md
LAST_VERIFIED: 2026-03-07

# MYCO VETKA Help Hint Library (V1)

## Synopsis
Ready-to-use contextual hint content for proactive MYCO behavior in VETKA, with RU/EN variants.

## Table of Contents
1. Hint templates by context
2. Next-best-step hints
3. Edge-case hints
4. Cross-links
5. Status matrix

## Treatment
Hints are concise, action-oriented, and mapped to real event/state contexts.

## Short Narrative
MYCO does not wait for confusion. It describes current scene, available actions, and best next step in one compact move.

## Full Spec
### Hints: "what you see"
- `TAG:MYCO.HELP.PROACTIVE.NEXT_STEP`
- Scene: VETKA main workspace
  - RU: "Ты в VETKA: дерево, чат и артефакты в одном поле."
  - EN: "You are in VETKA: tree, chat, and artifacts in one field."
- Scene: MCC helper topbar active
  - RU: "MYCO активен в верхней плашке, подсказка уже учитывает фокус ноды."
  - EN: "MYCO is active in top bar; hint already reflects node focus."

### Hints: "what you can do"
- Node selected
  - RU: "Открой контекст ноды и уточни цель: я соберу следующий шаг по роли."
  - EN: "Open node context and state your goal; I will assemble the next role-aware step."
- Workflow expanded
  - RU: "Проверь роль агента, модель и промпт, затем запусти run/retry."
  - EN: "Check agent role, model, and prompt, then run/retry."
- Group mention
  - RU: "Используй @mention, чтобы адресно вызвать нужную модель или агента."
  - EN: "Use @mention to target a specific model or agent."
- Phonebook/model selection
  - RU: "Открой телефонную книжку моделей и выбери маршрут (provider/source) под задачу."
  - EN: "Open model phonebook and pick provider/source route for this task."
- Key selection
  - RU: "Выбери ключ или оставь auto-select: это влияет на провайдера и лимиты."
  - EN: "Select a key or keep auto-select: this affects provider and limits."
- Unified search contexts
  - RU: "Переключай `vetka/`, `web/`, `file/`: это разные источники поиска."
  - EN: "Switch `vetka/`, `web/`, `file/`: these are different search sources."
- Phonebook + key selection result
  - RU: "Phonebook выбирает модель, key selector выбирает ключ: вместе они задают реальный execution path."
  - EN: "Phonebook picks model, key selector picks key: together they define real execution path."

### Hints: "next best step"
- Empty focus
  - RU: "Сначала выбери ноду в дереве, иначе подсказка будет слишком общей."
  - EN: "Select a tree node first; otherwise guidance will stay generic."
- Helper off mode
  - RU: "Helper mode выключен. Включи passive/active для проактивных подсказок."
  - EN: "Helper mode is off. Switch to passive/active for proactive guidance."
- Voice mode
  - RU: "Говори короткими шагами, я удержу контекст и дам action-план."
  - EN: "Speak in short steps; I will keep context and return an action plan."
- Web search no provider
  - RU: "Для `web/` не найден ключ провайдера. Добавь Tavily/Serper ключ в key drawer."
  - EN: "No provider key for `web/`. Add Tavily/Serper key in key drawer."
- External FS result
  - RU: "Файл найден вне индекса VETKA. Добавить в сканер сейчас?"
  - EN: "File found outside VETKA index. Ingest it into scanner now?"

### Control-question hint pack (`TAG:MYCO.HELP.CONTROL_QUESTIONS`)
- Trigger: user opens Model Directory.
  - RU: "Это телефонная книжка моделей. Выбирай модель/провайдера, чтобы зафиксировать маршрут ответа."
  - EN: "This is model phonebook. Pick model/provider to lock response routing."
- Trigger: user opens KeyDropdown.
  - RU: "Тут можно выбрать любимый ключ или оставить auto-select. Это влияет на провайдера и лимиты."
  - EN: "Here you can choose favorite key or keep auto-select. It affects provider and limits."
- Trigger: user toggles favorites.
  - RU: "Избранное ключей/моделей/файлов ускоряет повторные сценарии и восстановление контекста."
  - EN: "Favorites for keys/models/files speed up repeated scenarios and context restore."
- Trigger: user switches search context to `web/`.
  - RU: "`web/` ищет в интернете. Если ключ провайдера не задан, добавь его в key drawer."
  - EN: "`web/` searches internet. If provider key is missing, add it in key drawer."
- Trigger: user switches search context to `file/`.
  - RU: "`file/` ищет по локальной ФС, в том числе вне текущего дерева VETKA."
  - EN: "`file/` searches local FS, including paths outside current VETKA tree."
- Trigger: user found file outside index.
  - RU: "Хочешь включить этот путь в VETKA? Запущу add/index и переключу на scanner."
  - EN: "Want this path inside VETKA? I can run add/index and switch to scanner."

### Long-tail surface hint pack (`TAG:MYCO.HELP.LONG_TAIL_SURFACE`)
- Trigger: user opens mention popup.
  - RU: "Выбери @mention адресно — это самый быстрый способ точного routing."
  - EN: "Pick @mention precisely — this is the fastest path to targeted routing."
- Trigger: user opens group creator panel.
  - RU: "Проверь роли и модели группы до запуска, чтобы избежать хаотичного диалога."
  - EN: "Verify group roles and models before run to avoid chaotic dialogue."
- Trigger: user opens onboarding modal/overlay.
  - RU: "Пройди шаги последовательно: source -> sandbox -> старт проекта."
  - EN: "Follow steps in order: source -> sandbox -> project start."
- Trigger: user opens media player/viewer toolbar.
  - RU: "Сначала playback/fullscreen, затем действия над артефактом."
  - EN: "Handle playback/fullscreen first, then artifact actions."

### Button catalog integration
- Full generated catalog: `docs/163_ph_myco_VETKA_help/MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md`.
- Catalog scope: all `<button>` tags in `client/src` (336 items snapshot).

### Contract-backed anchors
- MCC state-matrix hints source: `client/src/components/mcc/MiniChat.tsx:74`.
- Top hint role/workflow matrix source: `client/src/components/mcc/MyceliumCommandCenter.tsx:2404`.
- Backend role/workflow next action pack: validated by `tests/test_phase162_p4_p4_node_role_workflow_matrix_contract.py:31`.
- Phonebook and key surfaces: `client/src/components/ModelDirectory.tsx:2`, `client/src/components/mcc/KeyDropdown.tsx:24`.
- Unified search contexts and modes: `client/src/components/search/UnifiedSearchBar.tsx:251`, `client/src/components/search/UnifiedSearchBar.tsx:208`.

## Cross-links
See also:
- [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [Scenarios](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [UI-Capability Matrix](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [Gap Registry](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [Recon Report](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
- [Search Phonebook Keys Guide](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [Long-tail Surfaces Scenarios](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [Cloud Social Search Contract](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)

## Status matrix
| Hint pack | Status | Evidence |
|---|---|---|
| MCC proactive hint language basis | Implemented | `client/src/components/mcc/MiniChat.tsx:74`; `client/src/components/mcc/MyceliumCommandCenter.tsx:2404` |
| VETKA-specific proactive copy | Partially Implemented | defined in this library, pending UI bind |
| Voice-aware MYCO prompts in VETKA main | Planned/Not Implemented | no MYCO UI bind in `client/src/App.tsx` |

## Global cross-links
- [MYCO_VETKA_MASTER_INDEX_V1](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [MYCO_VETKA_INFORMATION_ARCHITECTURE_V1](./MYCO_VETKA_INFORMATION_ARCHITECTURE_V1.md)
- [MYCO_VETKA_USER_SCENARIOS_ROOT_V1](./MYCO_VETKA_USER_SCENARIOS_ROOT_V1.md)
- [MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1](./MYCO_VETKA_UI_CAPABILITY_IMPLEMENTATION_MATRIX_V1.md)
- [MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1](./MYCO_VETKA_CHAT_AND_AGENT_OPERATIONS_V1.md)
- [MYCO_VETKA_CONTEXT_MEMORY_STACK_V1](./MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md)
- [MYCO_VETKA_HELP_HINT_LIBRARY_V1](./MYCO_VETKA_HELP_HINT_LIBRARY_V1.md)
- [MYCO_VETKA_GAP_AND_REMINDERS_V1](./MYCO_VETKA_GAP_AND_REMINDERS_V1.md)
- [MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [MYCO_VETKA_BUTTON_HINT_CATALOG_V1](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1](./MYCO_VETKA_LONG_TAIL_SURFACES_SCENARIOS_V1.md)
- [MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1](./MYCO_VETKA_CLOUD_SOCIAL_SEARCH_CONTRACT_V1.md)
- [MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1](./MYCO_VETKA_SEARCH_PHONEBOOK_KEYS_OPERATING_GUIDE_V1.md)
- [MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1](./MYCO_VETKA_STRICT_COVERAGE_AUDIT_V1.md)
- [PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07](./PHASE_163_MYCO_VETKA_DOC_RECON_REPORT_2026-03-07.md)
