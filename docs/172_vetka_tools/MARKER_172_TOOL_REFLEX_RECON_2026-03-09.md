# MARKER 172 — Доп. Recon: Reflex-механизмы инструментов (Artifact Coder vs Chat Roles)

Date: 2026-03-09

## Что проверял
- `src/orchestration/agent_pipeline.py` (coder pipeline / artifact flow)
- `src/tools/fc_loop.py` (tool FC loop для coder)
- `src/tools/registry.py` + `src/search/hybrid_search.py` (semantic/keyword backends, Qdrant/Weaviate)
- `src/mcp/tools/llm_call_tool.py` и `llm_call_tool_async.py` (inject_context)
- `src/agents/tools.py` + `src/orchestration/orchestrator_with_elisya.py` (role-based CAM tools)
- `src/api/handlers/group_message_handler.py` и `user_message_handler.py` (chat routing)

## Вывод по вопросу
Да, в коде присутствуют ДВЕ разные линии рефлексов инструментов:

1. **Artifact/Coder линия (Elisya + semantic tool context)**
2. **Chat-role линия (CAM-инструменты + CAM-weighted context)**

Они существуют параллельно и частично пересекаются.

---

## 1) Artifact/Coder Reflex (в коде есть)

### Подтверждения
- Coder pipeline включает FC loop и ограниченный набор read-only инструментов:
  - `src/orchestration/agent_pipeline.py` — `execute_fc_loop(...)` для `phase_type in ("fix", "build")`
  - `src/tools/fc_loop.py` — `PIPELINE_CODER_TOOLS = [vetka_read_file, vetka_search_semantic, vetka_search_files, vetka_search_code, vetka_list_files]`
- Coder получает auto-context инъекцию:
  - `agent_pipeline.py`: `call_args["inject_context"] = {"semantic_query": subtask.description, ...}`
  - `llm_call_tool_async.py`: `_gather_inject_context()` собирает `semantic_query`, `files`, `session`, `chat`, `prefs`, `CAM (optional)`, затем ELISION compression.
- Семантический инструмент coder уходит в `vetka_elisya` (Qdrant) и может использовать Weaviate path через hybrid search:
  - `src/tools/registry.py` (`VetkaSearchSemanticTool`) — code-only search по коллекции `vetka_elisya`
  - `src/search/hybrid_search.py` — keyword ветка через Weaviate BM25 + fallback в Qdrant

### Практический смысл
Coder действительно работает не только «из чата»: он в pipeline получает целевой tool-loop и контекст для работы с файлами/патчами.

---

## 2) Chat Roles + CAM Reflex (в коде есть)

### Подтверждения
- Group chat роли мапятся в orchestrator agent types (`PM/Dev/QA/Architect/Researcher`) и идут через `orchestrator.call_agent(...)`:
  - `src/api/handlers/group_message_handler.py`
- В orchestrator есть role-aware выдача tools с добавлением CAM tools:
  - `src/orchestration/orchestrator_with_elisya.py::get_tools_for_agent(...)`
- Базовая матрица прав на CAM tools есть:
  - `src/agents/tools.py::AGENT_TOOL_PERMISSIONS`
  - CAM tools: `calculate_surprise`, `compress_with_elision`, `adaptive_memory_sizing`
- В group chat контекст для моделей уже включает CAM-weighted pinned-context:
  - `group_message_handler.py` коммент: `Qdrant(40%) + CAM(20%) + ...`

### Практический смысл
Для ролей, отвечающих в чате, CAM-сигнал реально встроен и в tool-права, и в контекст.

---

## Найденные слабые места (до тестов)

1. **Неоднородный вызов tool-наборов в чат-путях**
- Часть путей берёт `get_tools_for_agent("Dev")` независимо от роли (solo/mention flows), что размывает role-specific рефлексы.

2. **Legacy naming в mention handler**
- В `src/api/handlers/mention/mention_handler.py` в system guidance встречаются старые имена (`camera_focus`, `search_semantic`), при том что в registry унифицировано через `vetka_*`.

3. **Weaviate — не гарантированный основной путь**
- В `hybrid_search` Weaviate используется в keyword ветке, но предусмотрены fallback-и в Qdrant; фактический runtime может часто идти через Qdrant-only.

4. **Прямых контрактных тестов именно на split-механику “artifact reflex vs chat CAM reflex” почти нет**
- Есть много тестов на части системы, но нет одного явного e2e-контракта на этот dual-mode.

---

## Короткий verdict
- **Кодовая база уже содержит оба механизма**, которые ты описал.
- **Риск сейчас не в отсутствии кода, а в несогласованности путей и неполном e2e покрытии**.
- Перед стабилизацией стоит сделать один интеграционный тест/проверку на dual-mode reflex routing.
