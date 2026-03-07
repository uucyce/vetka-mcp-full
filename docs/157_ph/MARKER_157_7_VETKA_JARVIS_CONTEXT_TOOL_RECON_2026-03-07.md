# MARKER_157_7_VETKA_JARVIS_CONTEXT_TOOL_RECON_2026-03-07

Status: `RECON COMPLETE`
Protocol: `RECON -> REPORT -> WAIT GO -> IMPLEMENT`
Date: `2026-03-07`

## 0) Список шагов (как ты сформулировал)
1. Зафиксировать `edge_ru_female` как основной голос везде.
2. Развивать умность ответа через полноту контекста.
3. Проверить, что Jarvis реально получает:
   - ARC
   - HOPE
   - JEPA
   - ENGRAM
   - STM
   - CAM
4. Проверить, что `elision` реально сжимает контекст в voice-пайплайне.
5. Проверить, получает ли Jarvis содержание файлов (не только названия/узлы).
6. Проверить, может ли Jarvis вызывать инструменты (tool/MCP/workflow), а не только генерить текст.
7. Изучить как это сделано в MYCELIUM/MYCO и перенести в Jarvis:
   - state-aware proactive guidance
   - state-key enriched retrieval
   - capability matrix
8. Сделать собственную базу RAG для VETKA-JARVIS (в симбиозе с памятью ENGRAM/STM/CAM).

---

## 1) Что реально есть сейчас (по коду)

### 1.1 Voice baseline
- `run.sh` уже на `edge` по умолчанию, профиль `vetka_ru_female`.
- Plan B fillers могут быть выключены флагами.

### 1.2 Jarvis context (текущий)
Источник: `src/voice/jarvis_llm.py:get_jarvis_context`
- Есть `STM` (recent context + session_summary).
- Есть `ENGRAM`:
  - `formality`
  - `preferred_language`
  - `prefers_russian`
  - `last_assistant_language`
  - `user_name`
- Есть `CAM` (через `surprise_detector` summary).
- Есть client-context из UI:
  - `viewport_context`
  - `pinned_files`
  - `open_chat_context`
  - `cam_context`
  - `llm_model`

### 1.3 Stage-machine
Источник: `src/api/handlers/jarvis_handler.py`
- Реализован stage2/stage3/stage4.
- Есть таймауты и trace (`/api/debug/jarvis/traces`).
- Сейчас это LLM refinement chain без реального tool-execution цикла.

### 1.4 Где MYCO сильнее
Источники:
- `client/src/components/mcc/MiniChat.tsx`
- `src/api/routes/chat_routes.py`
- `docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md`

Есть уже продвинутые механики:
- `MARKER_162.P4.P3.MYCO.CHAT_CONTEXT_DRILL_FIELDS.V1`
- `MARKER_162.P4.P3.MYCO.PROACTIVE_NEXT_ACTION_PACK.V1`
- `MARKER_162.P4.P3.MYCO.RAG_STATE_KEY_ENRICHMENT.V1`
- capability/state matrix в инструкции MYCO.

---

## 2) Разрыв (gap) между «хочу» и «есть»

## MARKER_157_7_GAP_MATRIX_V1
1. **ARC**:
- В Jarvis voice-path напрямую не подается как структурированный блок.
- ARC живет в orchestrator flow, но voice turn не вызывает ARC-процедуры.

2. **HOPE**:
- В `jarvis_prompt_enricher` есть интеграционные точки HOPE/ELISION, но JarvisLLM в voice-turn не использует расширенный HOPE-путь как обязательный контекстный слой.

3. **JEPA**:
- В Jarvis есть косвенный CAM/summary и в проекте есть context_packer JEPA fallback, но voice-path не прогоняется через единый `ContextPacker` контракт с trace поля `jepa_mode/jepa_latency`.

4. **ENGRAM/STM/CAM**:
- Подключены, но в облегченной форме.
- Есть признаки работы ENGRAM/STM, но недостаточно детерминированных фактов в ответах.

5. **ELISION**:
- Есть в prompt enricher/session summary, но нет жесткого voice-contract: что именно и когда сжимается + метрики до/после в trace.

6. **Содержание файлов**:
- В voice context обычно идут viewport/pinned/open_chat snippets, но нет гарантированного file-content pack по state-aware правилу (как в более тяжелом chat path).

7. **Tool/MCP вызовы**:
- Для Jarvis voice сейчас отсутствует прямой tool loop.
- В chat-route (`/chat`) tooling/orchestrator есть, в voice-route — нет равного контракта.

8. **MYCO-style proactive+RAG**:
- В MYCO сделано state-key enrichment + proactive next action pack.
- В Jarvis voice это пока не перенесено как единый state-aware RAG policy.

---

## 3) Что переносим из MYCO в VETKA-JARVIS

## MARKER_157_7_MYCO_TO_JARVIS_TRANSFER_V1
1. **State-key enrichment policy** (из `MARKER_162.P4.P3...RAG_STATE_KEY_ENRICHMENT`):
- Обогащать voice retrieval query полями состояния:
  - `nav_level`
  - `task_drill_state`
  - `roadmap_node_drill_state`
  - `workflow_inline_expanded`
  - `roadmap_node_inline_expanded`
  - `node_kind`, `role`, `active_task_id`

2. **Proactive next action pack**:
- После ответа добавлять короткий action-pack на основе state matrix (без «воды»).

3. **Capability matrix**:
- Отдельный RAG-док «что умеет VETKA-JARVIS voice сейчас» (и ограничения).

4. **Instruction RAG split**:
- Отделить:
  - core usage instructions
  - capability docs
  - troubleshooting/limits
  - memory policy docs

---

## 4) Новый target-контракт для voice контекста

## MARKER_157_7_VOICE_CONTEXT_CONTRACT_V2
Обязательные слои в каждом voice turn:
1. `identity_facts` (ENGRAM): имя, язык, стиль.
2. `short_memory` (STM): последние N ходов + session summary.
3. `state_facts` (UI drill/context): viewport + pins + open chat + drill fields.
4. `retrieval_facts` (RAG): state-key retrieval top-k snippets.
5. `cam_jepa_facts`:
   - CAM surprise summary
   - JEPA semantic digest (если trigger).
6. `compression_meta`:
   - pre/post chars/tokens
   - elision level
   - dropped blocks (если были).

---

## 5) Tooling-контракт для VETKA-JARVIS voice

## MARKER_157_7_VOICE_TOOL_LOOP_CONTRACT_V1
Jarvis voice должен иметь тот же минимум, что chat quick path:
1. Tool policy router:
   - `answer_only`
   - `retrieve_context`
   - `file_read`
   - `workflow_action`
   - `mcp_action`
2. Tool execution trace в `jarvis_trace`:
   - `tool_plan`
   - `tools_called`
   - `tool_errors`
   - `tool_latency_ms`
3. Безопасный режим:
   - если tool недоступен -> короткий fallback + честное объяснение.

---

## 6) Фазы имплементации (предлагаемый порядок)

## MARKER_157_7_IMPL_PHASES_V1
1. **157.7.1 Voice Context Packer Bridge**
- Перевести Jarvis context сборку на единый `ContextPacker`.
- Протянуть `jepa_mode`, `jepa_latency_ms`, `packing_path` в `jarvis_trace`.

2. **157.7.2 State-key Retrieval for Voice**
- Добавить state-key enrichment как в MYCO.
- В retrieval включать instruction docs по VETKA usage.

3. **157.7.3R Unified Model-Aware Context Packing**
- Удалить ad-hoc file-snippet path и локальные hard limits в Jarvis.
- На каждый stage/model делать repack через `ContextPacker.pack(...)`.
- Использовать packed блоки (`json_context/pinned_context/viewport_summary/jepa_context`) как основной prompt context.
- Adaptive budgeting оставлять централизованно в `provider_registry`.

4. **157.7.4 Voice Tool Loop (MVP)**
- Добавить tool-router перед final response.
- MVP tools: `retrieve_context`, `read_file`, `workflow_probe`.

5. **157.7.5 Proactive Guidance Pack**
- После основного ответа возвращать state-aware next actions (как в MYCO).

6. **157.7.6 RAG Base for VETKA-JARVIS**
- Отдельный hidden index для voice-инструкций + capability matrix.
- Синхронизация с ENGRAM/STM policy.

---

## 7) Go/No-Go критерии

## MARKER_157_7_GO_NO_GO_V1
Go, если:
1. `first_response_ms` не ухудшен >15% от текущего baseline.
2. На 10-turn сценарии:
   - имя пользователя воспроизводится корректно (из ENGRAM),
   - язык держится стабильно,
   - минимум 70% ответов содержат конкретные state/file facts.
3. Tool calls выполняются без silent fail, с trace.
4. Нет regressions в chat panel сценарии.

No-Go, если:
1. Появился рост `stt_retry`/silence.
2. Voice context ломает latency > p95 8s.
3. Ответы снова переходят в generic «общие фразы» без фактов.

---

## 8) Ключевой вывод recon

## MARKER_157_7_CONCLUSION_V1
Текущий Jarvis уже имеет базу памяти (STM/ENGRAM/CAM + UI context), но до уровня «умного и действенного» ему не хватает:
1. state-key RAG как в MYCO,
2. полного tool loop в voice path,
3. более глубокого memory/tool orchestration (ARC/HOPE chain) поверх уже подключенного ContextPacker+JEPA+ELISION.

Технически это реализуемо без смены базового голоса (`edge_ru_female`) и без возврата к Plan B.

## TODO (Voice profile)
- `MARKER_157_7_TODO_VOICE_PROFILE_LOCK.V1`: зафиксировать женский голос VETKA (`edge_ru_female`) как runtime default во всех voice entry points, и вынести переключение голоса в отдельный будущий UI-пункт.
