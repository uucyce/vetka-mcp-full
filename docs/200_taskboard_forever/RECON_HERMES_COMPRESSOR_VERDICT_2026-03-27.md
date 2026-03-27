# RECON: HERMES Structured Compressor vs VETKA Memory Stack

**Date:** 2026-03-27 (v2 — переисследование по Commander rejection)
**Author:** Eta (Harness Engineer 2) + 6 Sonnet recon agents
**Task:** tb_1774499127_1

## Referenced Architecture Documents

| # | Document | Path |
|---|----------|------|
| A1 | Cognitive Stack Architecture | `docs/186_memory/VETKA_COGNITIVE_STACK_ARCHITECTURE.md` |
| A2 | Memory DAG Abbreviations (canonical glossary) | `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md` |
| A3 | Memory Closure Architecture | `docs/198ph_ZETA_memory_update/ARCHITECTURE_198_MEMORY_CLOSURE.md` |
| A4 | Role-First Init Architecture | `docs/196ph_init_role_vetka/ARCHITECTURE_196_ROLE_FIRST_INIT.md` |
| A5 | HERMES Adoption Roadmap | `docs/199_ph_HERMES_ADOPTION/ROADMAP_HERMES_ADOPTION.md` |
| A6 | Adaptive Context & JEPA Recon (Phase 157) | `docs/157_ph/MARKER_157_ADAPTIVE_CONTEXT_AND_JEPA_RECON_2026-03-01.md` |
| A7 | STM/MGC Original Design (Phase 99) | `docs/unpluged_search/PH99_STM_MGC_Memory_Architecture.md` |
| A8 | REFLEX Architecture Blueprint | `docs/172_vetka_tools/REFLEX_ARCHITECTURE_BLUEPRINT_2026-03-10.md` |
| A9 | Memory Closure Roadmap | `docs/198ph_ZETA_memory_update/ROADMAP_198_MEMORY_CLOSURE.md` |
| A10 | Feedback Memory Matrix | `docs/192_task_SQLite/RECON_FEEDBACK_MEMORY_MATRIX.md` |

---

## 1. Принцип VETKA: память принадлежит платформе, не агенту

Из A4 (Architecture 196, §5):
> **VETKA Memory (persistent, role-scoped):**
> - ENGRAM (per-role learnings) → survives session, survives agent replacement
> - MGC (compressed, garbage-collected) → "only MGC discards the chaff"
> - Experience Reports (per-role, per-session) → injected into next session_init(role=same)

Из A9 (Roadmap 198):
> "No static .md as memory — data must be dynamic, cached, compressed."
> "Memory that isn't triggered by context is just a filing cabinet nobody opens."

**Вывод:** Любое решение ДОЛЖНО хранить состояние в VETKA (SQLite/JSON/Qdrant), а не полагаться на внешние механизмы сжатия чата.

---

## 2. Что HERMES Compressor НА САМОМ ДЕЛЕ делает

Source: `hermes-agent/agent/context_compressor.py` (MIT, NousResearch)

**Это LLM-summarizer conversation history.** Алгоритм:
1. Защищает первые N сообщений (system prompt)
2. Защищает последние N сообщений (по token budget)
3. Средние сообщения → **отправляет в auxiliary LLM** → получает structured summary
4. Чистит orphaned tool_call/tool_result пары

**Шаблон (7 секций):** Goal / Constraints / Progress (Done/InProgress/Blocked) / Key Decisions / Relevant Files / Next Steps / Critical Context

**Итеративный:** хранит `_previous_summary`, при следующем сжатии обновляет (не пересоздаёт).

**Критичное:** Каждое сжатие = 1 LLM-вызов к вспомогательной модели (cost + latency).

---

## 3. Что у VETKA уже есть — ТОЧНАЯ карта подсистем

### Подсистемы, которые СЖИМАЮТ контекст

| Подсистема | Что сжимает | Метод | LLM? | Ref |
|------------|-------------|-------|------|-----|
| **ELISION** | JSON payload (session_init, task_board list) | Key renaming + path abbrev + vowel skip | Нет | A1, A3 |
| **HOPE** | Любой контент → LOD (LOW/MID/HIGH) | LLM (Ollama llama3.1:8b) | Да | A2 |
| **JEPA Overflow** | Pinned files при token pressure >80% | Cosine ranking → semantic core subset | Нет (embedding only) | A6 |
| **JEPA Session Lens** | ENGRAM + Qdrant learnings + tasks | Cosine ranking → top-15 relevant items | Нет (embedding only) | A3, A6 |
| **JEPA Task Lens** | Pending task list | Cosine re-rank by role intent | Нет (embedding only) | A3 |

### Подсистемы, которые ХРАНЯТ память (survive compaction)

| Подсистема | Storage | Persist | Ref |
|------------|---------|---------|-----|
| **ENGRAM L1** | `data/engram_cache.json` | TTL=0 для danger/architecture (permanent) | A3 |
| **TaskBoard** | `data/task_board.db` (SQLite WAL) | Полностью | A3 |
| **CORTEX** | `data/reflex/feedback_log.jsonl` | Полностью | A8, A10 |
| **Qdrant L2** | Vector DB | Полностью | A3 |
| **project_digest** | `data/project_digest.json` | Полностью | — |

### Подсистемы, которые ТЕРЯЮТСЯ при compaction

| Подсистема | Storage | Проблема | Ref |
|------------|---------|----------|-----|
| **SessionTracker** | RAM only | `claimed_task_id`, `files_edited`, `protocol_checkpoints` — всё теряется | A4 |
| **STM Buffer** | RAM + `data/stm_snapshot.json` | `save_to_disk()` СУЩЕСТВУЕТ но НИКТО не вызывает автоматически | A7 |
| **Role context** | Injected в chat при session_init | `owned_paths`, `blocked_paths`, `workflow_hints` — теряются | A4 |
| **Mid-session decisions** | Только в chat window | Архитектурные решения, отвергнутые подходы — НИЧТО не пишет на диск | — |
| **REFLEX state** | Constructed per-call | `ReflexContext` не кешируется между вызовами | A8 |

### JEPA — точное описание (из кода и A2/A6)

**JEPA = Joint Embedding Predictive Architecture.** В VETKA это НЕ только медиа:
- **Multi-provider embedding dispatcher** (HTTP runtime → Ollama → deterministic hash fallback)
- **Session Lens** — ранжирует memory items по релевантности к текущей роли
- **Task Lens** — ранжирует pending tasks по cosine к role intent
- **Overflow compression** — при token pressure выбирает semantic core из pinned files
- **Media path** — video/audio embedding через OpenCV + Whisper (оригинальная роль)
- **Link prediction** — `predict_new_links()` по cosine threshold для knowledge graph

Из A2 (DAG Glossary): *"JEPA: Joint Embedding Predictive Architecture (predictive embedding layer). Status: dormant."* — "dormant" относится к Meta V-JEPA weights, НЕ к самому адаптеру.

---

## 4. Gap Analysis: что HERMES закрывает, а что — нет

### Что HERMES закрывает:
- Structured summary conversation history (7 секций)
- Iterative update при повторном сжатии

### Что HERMES НЕ закрывает:
- **Не знает о VETKA state** — task IDs, owned_paths, role context
- **Не пишет на диск** — summary живёт в chat window, теряется при restart
- **Не интегрируется** с ENGRAM/STM/TaskBoard
- **Стоимость** — 1 LLM вызов на каждое сжатие

### Что VETKA на самом деле теряет (реальный gap):

```
При compaction ТЕРЯЕТСЯ:               HERMES поможет?
─────────────────────────────          ──────────────────
claimed_task_id                         НЕТ (TaskBoard на диске — нужен re-read)
files_edited                            ЧАСТИЧНО (Relevant Files секция)
mid-session decisions                   ДА (Key Decisions секция)
STM buffer                              НЕТ (STM нужен save_to_disk)
role_context / owned_paths              НЕТ (нужен re-inject из registry)
protocol_checkpoints                    НЕТ (нужен SessionTracker persist)
```

**HERMES закрывает 1 из 6 потерь** (mid-session decisions). Остальные 5 решаются через persist to disk — то что VETKA УЖЕ умеет, но не вызывает автоматически.

---

## 5. Вердикт: HERMES template полезен как ФОРМАТ, бесполезен как МЕХАНИЗМ

### Что взять от HERMES:
- **Шаблон 7 секций** — хорошая структура для checkpoint-файла
- **Iterative update** — идея обновлять, не пересоздавать

### Что НЕ брать:
- **LLM-вызов для сжатия** — дорого, медленно, не нужно когда данные уже structured
- **Conversation-turn compression** — не наша проблема (наша = state persistence)

### Что VETKA реально нужно (3 задачи):

**T1: STM auto-save** (low effort, high impact)
Вызывать `STMBuffer.save_to_disk()` при каждом `action=claim` / `action=complete` / periodic timer.
→ STM entries переживают compaction.

**T2: SessionTracker persist** (medium effort, high impact)
Писать `data/session_checkpoint.json` при каждом значимом action. Содержимое:
```json
{
  "claimed_task_id": "tb_xxx",
  "files_edited": ["src/foo.py", "src/bar.py"],
  "files_read": ["src/baz.py"],
  "decisions": [],
  "role": "Eta",
  "checkpoint_at": "2026-03-27T12:00:00"
}
```
`session_init` читает этот файл и восстанавливает состояние.

**T3: Decision capture** (medium effort, medium impact)
Единственный gap который HERMES реально закрывает.
Варианты:
- a) При `action=complete` добавить поле `decisions` (список строк) — пишется в TaskBoard
- b) ENGRAM entry при каждом значимом архитектурном решении (category=architecture)
- c) Structured checkpoint с секцией Decisions (формат HERMES, БЕЗ LLM)

---

## 6. Abbreviation Map (обновлённый, точный)

| Abbr | Full Name | Role in Memory Stack |
|------|-----------|---------------------|
| ELISION | Efficient Language-Independent Symbolic Inversion of Names | L0: JSON token compression |
| HOPE | Hierarchical Orthogonal Predictive Embedding | L1: LOD summarization (LLM) |
| MGC | Multi-Generation Cache | L2: 3-tier storage (RAM→SQLite→JSON) |
| ARC | Architecture Reasoning Cycle | L3: workflow transformation suggestions |
| CAM | Constructivist Agentic Memory | L1: saliency/surprise signal for ELISION L3 |
| JEPA | Joint Embedding Predictive Architecture | L1: multi-provider embedding + semantic ranking (Session Lens, Task Lens, Overflow, Media) |
| ENGRAM | L1 O(1) Pattern Cache | L2: permanent learned patterns (danger/architecture) |
| REFLEX | 8-Signal Tool Ranker | L1: orchestrates all signals → tool recs |
| STM | Short-Term Memory Buffer | L0: session working context (RAM + disk snapshot) |
| CORTEX | Feedback Cortex | L2: per-tool success/failure scoring |
| AURA | User Profile Store | L2: user preferences (RAM + Qdrant) |
| HERMES-SC | Hermes Structured Compressor | EXTERNAL: LLM-based conversation summary (7-section template) |

---

## 7. Рекомендация

**НЕ adopt HERMES как механизм.** Adopt шаблон 7 секций как формат для checkpoint-файла.

Реальные задачи (по приоритету):
1. **T1: STM auto-save** — fix one line, massive impact
2. **T2: SessionTracker persist** — new file, restores agent state after compaction
3. **T3: Decision capture** — ENGRAM entries at action=complete

Все три задачи — VETKA-native, zero LLM cost, survive any external compaction.
