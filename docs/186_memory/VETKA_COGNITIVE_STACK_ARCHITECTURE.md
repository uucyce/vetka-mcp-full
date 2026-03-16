# VETKA Cognitive Stack — Полная архитектура памяти v1.1

> Единый документ: все подсистемы памяти, их роли, связи, и две ортогональные оси (тип данных vs уровень доступа).
> Для всех потребителей: Claude Code, Codex, MCC Architects, Jarvis, VETKA Chat agents.
>
> Дата: 2026-03-16
> Авторы: Opus + Danila + Sonnet (critic) + GPT (naming + cognitive framing)
> v1.1: ELISYA corrected from "just a collection" to full context middleware

## 0. Биологическая метафора

```
VETKA      = скелет/дерево         (структура знаний)
MYCELIUM   = грибница/мозг         (распределённая сеть агентов — execution)
ELISYA     = нервная система       (координация/сознание/синхронизация — middleware)
ELISION    = забывание/абстракция  (сжатие контекста — compression)
AURA       = аура собеседника      (кто перед нами — user profile)
ENGRAM     = рефлексы/инстинкты    (что знаем точно — O(1) cache)
STM        = оперативная память    (что было секунду назад)
CAM        = внимание              (что неожиданно/важно)
REFLEX     = выбор действия        (какой tool использовать)
CORTEX     = обучение на опыте     (feedback loop)
HOPE       = фокус/масштаб         (на каком уровне абстракции)
MGC        = быстрый доступ к данным (cache hierarchy)
CUT        = зрение/монтаж         (media cognition)
```

---

## 1. Две оси памяти

Память в VETKA описывается двумя независимыми осями:

### Ось 1: ТИП данных (ЧТО хранится)

| Тип | Система | Отвечает на вопрос | Пример |
|-----|---------|-------------------|--------|
| **User profile** | AURA | Кто перед нами? | "Danila предпочитает короткие ответы на русском" |
| **System knowledge** | ENGRAM + Qdrant | Что система знает? | "scorer.py и feedback.py всегда меняются вместе" |
| **Working context** | STM | Что происходит прямо сейчас? | "Последние 5 действий: edit → test → fail → fix → test" |
| **Attention focus** | CAM | Что важно/неожиданно? | "Файл X изменился необычно — surprise 0.87" |
| **Tool effectiveness** | CORTEX | Какие инструменты работают? | "vetka_search_semantic success_rate=0.92 для phase:build" |
| **Project state** | Digest + TaskBoard | Где мы в проекте? | "Phase 186, 3 pending tasks, branch claude/vigorous-cori" |

### Ось 2: УРОВЕНЬ доступа (КАК быстро достаётся)

| Уровень | Скорость | Механизм | Детерминированность | Вместимость |
|---------|----------|----------|---------------------|-------------|
| **L0: RAM hot** | <1ms | Dict/deque in Python process | Полная | ~200 entries |
| **L1: Deterministic cache** | <1ms | Hash lookup, JSON на диске | Полная | ~200 entries |
| **L2: Semantic search** | ~200ms | Qdrant cosine similarity | Нет (зависит от embeddings) | ~unlimited |
| **L3: Raw storage** | ~1s | File read, git log, API call | Полная | unlimited |

### Матрица: тип x уровень

Каждая подсистема живёт на пересечении:

| | L0 (RAM hot) | L1 (Determ. cache) | L2 (Qdrant semantic) | L3 (Files/Git) |
|---|---|---|---|---|
| **AURA** (user profile) | `ram_cache[user_id]` | — | `vetka_user_memories` | — |
| **ENGRAM** (system knowledge) | — | `engram_cache.json` (NEW) | `VetkaResourceLearnings` | `resource_learnings.json` fallback |
| **STM** (working context) | `deque(maxlen=10)` | — | — | — |
| **CAM** (attention) | surprise scores in RAM | — | — | — |
| **CORTEX** (tool feedback) | — | — | — | `feedback_log.jsonl` |
| **MGC** (graph cache) | Gen0: RAM | — | Gen1: Qdrant | Gen2: JSON files |
| **Digest** (project state) | — | — | — | `project_digest.json` |
| **TaskBoard** (tasks) | — | — | — | `task_board.json` via MCP |

---

## 2. Полный когнитивный стек (порядок обработки)

```
USER INPUT
    │
    ▼
┌─────────────────────────────────────────────────┐
│  AURA — User Profile                             │
│  "Кто перед нами?"                               │
│  src/memory/engram_user_memory.py → aura_store.py│
│  RAM cache + Qdrant(vetka_user_memories)          │
│  Влияет на: REFLEX (signal #4, weight 0.10)      │
│             prompt style, response length         │
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  STM — Short-Term Memory                         │
│  "Что только что произошло?"                     │
│  src/memory/stm_buffer.py                        │
│  deque(maxlen=10), decay: weight *= (1-0.1*min)  │
│  Sources: user, agent, system, hope, cam, pipe   │
│  Влияет на: REFLEX (signal #5, weight 0.10)      │
│             context for next action               │
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  CAM — Constructivist Agentic Memory             │
│  "Что неожиданно/важно?"                         │
│  src/orchestration/cam_engine.py                 │
│  Surprise detection: 0.0-1.0 score               │
│  Влияет на: REFLEX (signal #2, weight 0.15)      │
│             STM boosting (surprise → higher weight)│
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  ENGRAM — Deterministic Knowledge Cache (L1)     │
│  "Знаем ли мы это точно?"                        │
│  src/memory/engram_cache.py (NEW, не реализован) │
│  Dict[key, lesson], O(1), <1ms                   │
│  Auto-populated from L2 при match_count ≥ 3      │
│  HIT → return instantly                          │
│  MISS → fall through to Qdrant (L2)              │
└────────────────────┬────────────────────────────┘
                     │
    ▼ (miss)         ▼ (hit → skip)
┌─────────────────────────────────────────────────┐
│  QDRANT — Semantic Memory (L2)                   │
│  "Что мы можем вспомнить?"                       │
│  src/memory/qdrant_client.py                     │
│  Collections:                                    │
│    VetkaResourceLearnings — patterns, pitfalls   │
│    vetka_elisya — file index, code context       │
│    VetkaTree — knowledge graph nodes             │
│    VetkaGroupChat — chat history                 │
│    vetka_user_memories — AURA data               │
│  Cosine similarity, ~200ms                       │
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  REFLEX — Tool Selection                         │
│  "Какой инструмент использовать?"                │
│  src/reflex/scorer.py (8 signals)                │
│  Inputs: все вышестоящие системы                  │
│  Output: ranked tool list, top-3                 │
│                                                  │
│  Signal weights:                                 │
│  #1 semantic_match   0.30  (embedding vs intent) │
│  #2 cam_surprise     0.15  (CAM novelty)         │
│  #3 cortex_feedback  0.15  (CORTEX success rate) │
│  #4 aura_pref        0.10  (AURA user habits)    │
│  #5 stm_relevance    0.10  (STM recency)         │
│  #6 phase_match      0.10  (build/fix/research)  │
│  #7 hope_lod         0.05  (HOPE zoom level)     │
│  #8 mgc_heat         0.05  (MGC cache frequency) │
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  MGC — Multi-Generational Cache                  │
│  "Быстрый доступ к данным графа"                 │
│  src/memory/mgc_cache.py                         │
│  Gen0: RAM (hot) → Gen1: Qdrant → Gen2: JSON    │
│  Promotion: access_count ≥ threshold → Gen0      │
│  Влияет на: REFLEX (signal #8, weight 0.05)      │
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  HOPE — Hierarchical Processing                  │
│  "На каком уровне абстракции работаем?"          │
│  src/agents/hope_enhancer.py                     │
│  LOW: global overview (matryoshka outer)         │
│  MID: detailed analysis (matryoshka middle)      │
│  HIGH: fine-grained specifics (matryoshka inner) │
│  Влияет на: REFLEX (signal #7, weight 0.05)      │
│             STM truncation (hope_truncate=500)    │
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  ELISYA — Context Middleware + Agent Language     │
│  "Язык, на котором агенты думают вместе"         │
│                                                  │
│  TWO components under one name:                  │
│                                                  │
│  A) Python module (src/elisya/):                 │
│     ElisyaState — shared memory between agents   │
│       fields: semantic_path, lod_level, tint,    │
│       conversation_history, few_shots, score      │
│     ElisyaMiddleware — context reframing:        │
│       1. Truncate by LOD (500-10000 tokens)      │
│       2. Apply semantic tint (Security/Perf/...) │
│       3. Fetch similar past outputs from Qdrant  │
│       4. Inject few-shot examples (score > 0.8)  │
│     ModelRouter — task→model routing             │
│     ProviderRegistry — multi-provider LLM calls  │
│     KeyManager — API key rotation                │
│                                                  │
│  B) Qdrant collection (vetka_elisya):            │
│     File embeddings for semantic code search      │
│     Used by: embedding_pipeline, hybrid_search   │
│                                                  │
│  + ELISION compression (40-60% token savings)    │
│                                                  │
│  Влияет на: ALL agents (context they receive)    │
│  Feeds from: CAM (surprise), STM (recent), HOPE │
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  MYCELIUM — Agent Execution                      │
│  "Выполнение задач"                              │
│  src/orchestration/agent_pipeline.py             │
│  Architect → Researcher → Coder → Verifier       │
│  Fractal: tasks can spawn sub-pipelines          │
│  Dragon tiers: Bronze / Silver / Gold            │
└────────────────────┬────────────────────────────┘
                     │
    ▼                ▼
┌─────────────────────────────────────────────────┐
│  CORTEX — Learning Loop (feedback)               │
│  "Что сработало, что нет?"                       │
│  src/reflex/feedback.py                          │
│  Append-only JSONL: tool_id, success, useful     │
│  Score = success*0.40 + useful*0.35 + verifier*0.25│
│  Decay: exp(-0.1 * days_old)                     │
│  Feeds back into: REFLEX signal #3               │
│                                                  │
│  Resource Learnings (post-merge):                │
│  src/orchestration/resource_learnings.py         │
│  Extracts patterns/pitfalls → Qdrant             │
│  Feeds into: ENGRAM L1 (auto-promote at ≥3 hits) │
└─────────────────────────────────────────────────┘
```

---

## 3. Потоки данных: READ path vs WRITE path

### READ path (session_init → agent gets context)

```
session_init(agent_type, user_id)
    │
    ├─ 1. Digest       → phase, headline, pending, achievements
    ├─ 2. TaskBoard     → pending_count, in_progress, my_tasks
    ├─ 3. AURA          → user preferences (comm style, tools)
    ├─ 4. ENGRAM L1     → deterministic hits for current files (NEW)
    ├─ 5. Qdrant L2     → semantic recall: 3-5 relevant learnings (NEW)
    ├─ 6. STM           → last 5-10 actions (if same session)
    ├─ 7. REFLEX        → top-3 tool recommendations
    ├─ 8. Agent briefing → my tasks + don't-touch files (NEW)
    │
    └─ Result: ~50 строк targeted context
```

### WRITE path (after task completion)

```
task_board.complete(task_id)
    │
    ├─ 1. TaskBoard     → status, status_history, stats
    ├─ 2. Git commit    → pre-commit hook → digest auto-sync
    ├─ 3. CORTEX        → reflex_feedback.record_outcome()
    ├─ 4. Resource Learnings → extract patterns → Qdrant
    ├─ 5. ENGRAM L1     → auto-promote if learning matched ≥3x (NEW)
    ├─ 6. STM           → add completion event
    │
    └─ NO: program.md (дубль digest)
       NO: отдельный ENGRAM collection (дубль resource_learnings)
```

### PROMOTION path (L2 → L1, самообучение)

```
Qdrant semantic search returns learning X
    │
    ├─ match_count[X] += 1
    │
    ├─ if match_count[X] >= 3:
    │      ENGRAM_CACHE[key(X)] = X.text
    │      → Next time: O(1) instead of ~200ms
    │
    └─ if match_count[X] < 3:
           → Stay in L2 (Qdrant only)
```

---

## 4. Naming: когнитивный стек VETKA

| Имя | Расшифровка | Роль в когнитивной модели | Файл |
|-----|-------------|--------------------------|------|
| **AURA** | Adaptive User Response Archive | Personality — кто перед нами | `aura_store.py` (rename from engram_user_memory.py) |
| **STM** | Short-Term Memory | Working memory — что сейчас | `stm_buffer.py` |
| **CAM** | Constructivist Agentic Memory | Attention — что важно | `cam_engine.py` |
| **ENGRAM** | (True Engram, DeepSeek-inspired) | Instincts — что знаем точно, O(1) | `engram_cache.py` (NEW) |
| **QDRANT** | (Vector DB, L2) | Long-term memory — что можем вспомнить | `qdrant_client.py` + collections |
| **REFLEX** | Reactive Execution & Function Linking EXchange | Actions — какой tool использовать | `reflex/scorer.py` |
| **CORTEX** | (Layer 3 of REFLEX) | Learning — что сработало | `reflex/feedback.py` |
| **MGC** | Multi-Generational Cache | Cache hierarchy — быстрый доступ к графу | `mgc_cache.py` |
| **HOPE** | Hierarchical Optimized Processing Enhanced | Abstraction — на каком уровне детализации | `hope_enhancer.py` |
| **ELISYA** | Efficient Language-Independent Synchronization | Context middleware — язык общения агентов + context reframing | `src/elisya/` (module: state, middleware, router, providers) + Qdrant `vetka_elisya` (file index) |
| **ELISION** | Efficient Language-Independent Symbolic Inversion | Compression — сжатие контекста (40-60%) | `elision.py` |
| **MYCELIUM** | Multi-agent Yielding Cognitive Execution Layer | Execution — запуск pipeline | `agent_pipeline.py` |
| **CUT** | (Cinema Utility Tools) | Media cognition — монтаж/видео | CUT subsystem |

### Когнитивная аналогия

```
Человек                    VETKA
────────                   ─────
Узнаю собеседника       →  AURA
Помню что было минуту назад → STM
Замечаю необычное       →  CAM
Знаю таблицу умножения  →  ENGRAM (L1)
Вспоминаю через ассоциации → Qdrant (L2)
Выбираю инструмент      →  REFLEX
Учусь на ошибках        →  CORTEX
Фокусируюсь на уровне   →  HOPE
Формулирую мысль для собеседника → ELISYA (context reframing + LOD + tint)
Координирую руки и ноги  →  MYCELIUM (execution)
Сжимаю воспоминания в суть → ELISION (compression)
```

---

## 5. Что упущено в Blueprint v1.1 (и добавлено здесь)

| Система | В Blueprint v1.1 | Здесь | Роль |
|---------|-----------------|-------|------|
| STM | Упомянут как REFLEX signal #5 | Полное описание | Working memory, deque(10), decay |
| MGC | Упомянут как REFLEX signal #8 | Полное описание | 3-tier cache (RAM→Qdrant→JSON) |
| HOPE | Упомянут как REFLEX signal #7 | Полное описание | Abstraction levels (LOW/MID/HIGH) |
| CAM | Упомянут как REFLEX signal #2 | Полное описание | Surprise detection, attention |
| ELISION | Не упомянут | Добавлен | Compression layer (40-60%) |
| JEPA | Не упомянут | Отмечен как dormant | Predictive layer (not active) |
| ARC | Не упомянут | Отмечен как dormant | Reasoning cycle (not active) |

### Dormant systems (существуют но не активны в текущем flow)

| Система | Файл | Статус | Когда активировать |
|---------|------|--------|-------------------|
| **JEPA** | `src/agents/jepa_predictor.py` (if exists) | Dormant | Когда нужна предсказательная модель |
| **ARC** | `src/agents/arc_solver_agent.py` | Active (standalone) | Для architecture decisions |

---

## 6. Зависимости между подсистемами

```
AURA ──────────► REFLEX (#4)
                    │
STM ───────────► REFLEX (#5)
                    │
CAM ───────────► REFLEX (#2) ──► STM (surprise boost)
                    │
CORTEX ────────► REFLEX (#3)
                    │
HOPE ──────────► REFLEX (#7) ──► STM (truncation)
                    │
MGC ───────────► REFLEX (#8)
                    │
ENGRAM L1 ─────► session_init (direct inject, before REFLEX)
                    │
Qdrant L2 ─────► session_init (semantic recall, fallback from L1)
                    │
Resource Learnings ──► ENGRAM L1 (auto-promote at ≥3 matches)
                    │
CORTEX ──► Resource Learnings (close feedback loop)
```

**Критическая цепочка:**
```
CORTEX records outcome
  → Resource Learnings extracts pattern
    → Qdrant stores (L2)
      → Matched ≥3 times → ENGRAM promotes (L1)
        → Next query: instant O(1) answer
```

Это и есть **самообучение**: L2 → L1 promotion = система превращает опыт в рефлексы.

---

## 7. Подвисшие задачи (контекст для roadmap)

| Задача | Блокирует | Статус |
|--------|-----------|--------|
| Merge REFLEX branch to main | Все изменения в REFLEX scorer | Branch `claude/distracted-beaver` |
| TaskBoard worktree lifecycle | Multi-agent sync (done_worktree → done_main) | Designed, not implemented |
| Playwright + Chrome Control unification | Visual verification for CUT | Two tools need merging |
| Memory architecture (этот документ) | ENGRAM L1, semantic_recall, AURA rename | This document = Phase 186 |

---

## 8. Open questions (для Grok research)

См. отдельный документ: `docs/186_memory/GROK_RESEARCH_QUESTIONS.md`
