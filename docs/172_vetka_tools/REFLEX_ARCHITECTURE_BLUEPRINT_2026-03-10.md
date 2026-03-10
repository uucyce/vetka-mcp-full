# REFLEX — Reactive Execution & Function Linking EXchange
## Architecture Blueprint v1.0 (2026-03-10)

**Author:** Opus Commander
**Recon:** 4 parallel scouts, full codebase trace
**Scope:** Tool recall engine for all VETKA agents

---

## Position in VETKA OS

```
VETKA ─── Visual Enhanced Tree Knowledge Architecture
├── MYCELIUM   (agents)           — КТО делает
├── ELISYA     (orchestration)    — КАК координирует
├── MYCO       (UI helper)        — ЧТО подсказывает пользователю
├── CAM        (surprise memory)  — ЧТО неожиданного в данных
├── ELISION    (compression)      — КАК сжимает контекст
├── ENGRAM     (long-term memory) — ЧТО помнит о пользователе
├── STM        (working memory)   — ЧТО сейчас в фокусе
├── MGC        (graph cache)      — ЧТО кэшировано
├── CUT        (media montage)    — ЧТО монтирует
├── HOPE       (hierarchical LOD) — НА КАКОМ уровне детализации
├── JEPA       (predictive)       — ЧТО предсказывает
├── ARC        (reasoning)        — КАК рассуждает
└── REFLEX     (tool recall)      — ЧЕМ делает  ← NEW
```

**Аналогия:** Павловский рефлекс. Контекст = стимул → REFLEX = мгновенный выбор инструмента.
Без LLM вызова. Чистый scoring на сигналах памяти.

---

## Проблема (текущее состояние)

### Рекон показал: инструменты назначаются СТАТИЧЕСКИ

| Роль | Инструменты | Как выбираются |
|------|-------------|----------------|
| Scout | ripgrep (prefetch, не tool call) | Hardcoded в `_scout_prefetch()` |
| Researcher | Tavily web search (prefetch) | Hardcoded в `_research()` |
| Architect | Нет инструментов | Только контекст-инъекция |
| **Coder** | 5 read-only tools в FC loop | **Hardcoded** `PIPELINE_CODER_TOOLS` |
| Verifier | Нет инструментов | Только контекст-инъекция |
| Doctor | Role-based permissions | `get_tools_for_agent("Dev")` — всегда Dev |

**Проблема №1:** Coder работающий с видео получает те же 5 инструментов, что и coder работающий с Python.

**Проблема №2:** Researcher всегда ищет в вебе, даже если ответ уже в кодовой базе.

**Проблема №3:** Нет feedback loop — система не учится какие инструменты работают лучше для каких задач.

---

## Архитектура REFLEX

### 3 слоя

```
┌─────────────────────────────────────────────┐
│  Layer 3: FEEDBACK CORTEX                   │
│  (обучение на результатах)                  │
│  context + tool + result + success → learn   │
├─────────────────────────────────────────────┤
│  Layer 2: REFLEX SCORER                     │
│  (мгновенный scoring без LLM)              │
│  signals → score(tool) → ranked top-N        │
├─────────────────────────────────────────────┤
│  Layer 1: REFLEX REGISTRY                   │
│  (каталог инструментов с метаданными)       │
│  tool_id + intent_tags + trigger_patterns    │
└─────────────────────────────────────────────┘
```

### Layer 1: REFLEX REGISTRY

**Файл:** `src/services/reflex_registry.py`
**Данные:** `data/reflex/tool_catalog.json`

Каждый инструмент описывается:

```json
{
  "tool_id": "vetka_search_semantic",
  "namespace": "vetka",
  "kind": "search",
  "intent_tags": ["find", "locate", "concept", "meaning", "similar"],
  "trigger_patterns": {
    "file_types": ["*"],
    "phase_types": ["research", "fix", "build"],
    "keywords": ["where", "find", "search", "look for", "related to"]
  },
  "cost": {
    "latency_ms": 200,
    "tokens": 0,
    "risk_level": "read_only"
  },
  "permission": "READ",
  "deprecated_aliases": [],
  "active": true
}
```

**Источники каталога:**
- `src/tools/registry.py` → ToolDefinition objects
- `src/tools/fc_loop.py` → PIPELINE_CODER_TOOLS
- `src/agents/tools.py` → AGENT_TOOL_PERMISSIONS
- `src/mcp/vetka_mcp_bridge.py` → MCP tool registrations
- `src/mcp/mycelium_mcp_server.py` → Mycelium tools
- CUT endpoints (`src/api/routes/cut_routes.py`) → 19 CUT tools

**Автогенерация:** `scripts/generate_reflex_catalog.py` — сканирует код, строит каталог.

### Layer 2: REFLEX SCORER

**Файл:** `src/services/reflex_scorer.py`

Чистая функция: `recommend(context, available_tools) → List[ScoredTool]`

**Входные сигналы (10 источников, уже существуют в системе):**

| Сигнал | Источник | Что даёт | Вес |
|--------|----------|----------|-----|
| Семантика задачи | Qdrant/Weaviate | Близость intent_tags к задаче | 0.30 |
| CAM surprise | `surprise_detector.py` | Неожиданность контекста | 0.15 |
| ENGRAM preferences | `engram_user_memory.py` | `tool_usage_patterns` пользователя | 0.10 |
| STM recency | `stm_buffer.py` | Что сейчас в working memory | 0.10 |
| Phase type | Pipeline config | fix/build/research → разные наборы | 0.10 |
| HOPE LOD level | `hope_enhancer.py` | Zoom: HIGH→impl tools, LOW→overview | 0.05 |
| MGC cache heat | `mgc_cache.py` | Gen0 файлы = горячий контекст | 0.05 |
| **Feedback score** | **НОВОЕ: feedback_cortex** | Историческая успешность tool+context | **0.15** |

**Формула:**
```python
def score(tool: ToolEntry, context: ReflexContext) -> float:
    return (
        semantic_match(tool.intent_tags, context.task_embedding) * 0.30 +
        cam_relevance(tool, context.cam_activations)              * 0.15 +
        feedback_score(tool.tool_id, context.task_type)           * 0.15 +
        engram_preference(tool.tool_id, context.user_prefs)       * 0.10 +
        stm_relevance(tool, context.stm_items)                    * 0.10 +
        phase_match(tool.trigger_patterns, context.phase_type)    * 0.10 +
        hope_lod_match(tool, context.hope_level)                  * 0.05 +
        mgc_heat(tool, context.mgc_stats)                         * 0.05
    )
```

**Выход:** Top-N инструментов с confidence score.

```python
@dataclass
class ScoredTool:
    tool_id: str
    score: float          # 0.0 - 1.0
    reason: str           # "semantic match: 0.89, feedback: 0.92"
    source_signals: Dict  # breakdown per signal
```

### Layer 3: FEEDBACK CORTEX (обучение)

**Файл:** `src/services/reflex_feedback.py`
**Данные:** `data/reflex/feedback_log.jsonl` (append-only log)

**Каждый запуск инструмента записывает:**

```json
{
  "ts": "2026-03-10T20:30:00Z",
  "tool_id": "vetka_search_semantic",
  "agent_role": "coder",
  "phase_type": "fix",
  "task_embedding_hash": "a1b2c3",
  "context_signals": {
    "cam_surprise": 0.72,
    "stm_items": 3,
    "hope_level": "HIGH"
  },
  "result": {
    "success": true,
    "execution_time_ms": 180,
    "result_useful": true,
    "verifier_passed": true
  }
}
```

**Агрегация (периодическая):**

```python
# Для каждой пары (tool_id, task_type):
feedback_score = (
    success_rate * 0.40 +          # tool вернул success
    usefulness_rate * 0.35 +       # результат был использован агентом
    verifier_pass_rate * 0.25      # верификатор принял финальный результат
)
```

**Как определяется `result_useful`:**
- Coder: если после tool call контент изменился (не просто повторение)
- Researcher: если результат вошёл в финальный ответ
- Verifier: если tool results помогли найти проблему

**Decay:** Старые записи теряют вес: `weight *= exp(-0.1 * days_old)`

---

## Точки врезки (6 injection points)

Рекон выявил точные места в коде:

### IP-1: FC Loop — Pre-Execution (fc_loop.py:493)
```python
# BEFORE call_model_v2() with tools
if reflex_enabled:
    scored = await reflex_scorer.recommend(
        context=ReflexContext.from_subtask(subtask, stm, cam),
        available_tools=CODER_TOOL_SCHEMAS,
    )
    tool_schemas = reflex_scorer.prioritize_schemas(
        CODER_TOOL_SCHEMAS, scored, max_tools=5
    )
```
**Эффект:** Coder получает контекстно-релевантные инструменты.

### IP-2: FC Loop — Safety Gate (fc_loop.py:524)
```python
# INSTEAD OF hard block
if func_name not in PIPELINE_CODER_TOOLS:
    if reflex_enabled:
        dynamic_ok = reflex_scorer.approve_dynamic_tool(func_name, context)
        if dynamic_ok.confidence > 0.8:
            # Allow with logging
```
**Эффект:** Динамический whitelist — coder может использовать CUT tools если работает с видео.

### IP-3: FC Loop — Post-Execution (fc_loop.py:550)
```python
# AFTER tool execution
result = await executor.execute(call)
if reflex_enabled:
    await reflex_feedback.record(
        tool_id=func_name, result=result,
        context=current_context, agent_role="coder"
    )
```
**Эффект:** Каждый вызов записывается для обучения.

### IP-4: Pipeline — Agent Tool Assignment (agent_pipeline.py:3464)
```python
# BEFORE _execute_subtask()
if reflex_enabled:
    recommended = await reflex_scorer.recommend_for_role(
        role="coder", subtask=subtask, phase_type=phase_type
    )
    subtask.context["reflex_tools"] = recommended
```
**Эффект:** Не только coder — каждая роль получает рекомендации.

### IP-5: Verifier — Feedback Signal (agent_pipeline.py:954)
```python
# AFTER verification
if reflex_enabled:
    await reflex_feedback.record_outcome(
        subtask_id=subtask.id,
        tools_used=subtask.context.get("tools_used", []),
        verifier_passed=verification.get("passed", False),
    )
```
**Эффект:** Замыкание feedback loop — верификатор оценивает эффективность инструментов.

### IP-6: Session Init — Recommendations (vetka_session_init)
```python
# IN session_init response
if reflex_enabled:
    session_data["recommended_tools"] = reflex_scorer.recommend_for_session(
        phase=current_phase, user_prefs=engram_prefs,
        recent_activity=stm_buffer.get_recent()
    )
```
**Эффект:** Каждый агент (Opus, Codex, Dragon) при подключении видит рекомендованные инструменты.

---

## Feedback Loop — Полный цикл

```
1. ЗАДАЧА поступает
       ↓
2. REFLEX SCORER читает сигналы:
   CAM(surprise) + ENGRAM(prefs) + STM(recent) +
   HOPE(LOD) + MGC(cache) + FEEDBACK(history)
       ↓
3. REFLEX выдаёт ranked tools для роли
       ↓
4. Агент ИСПОЛЬЗУЕТ инструменты (FC loop / prefetch)
       ↓
5. REFLEX FEEDBACK записывает:
   {tool, context, result, success}
       ↓
6. VERIFIER оценивает итог
       ↓
7. REFLEX FEEDBACK обновляет score:
   {tool, context, verifier_passed}
       ↓
8. Следующая ЗАДАЧА → scorer использует обновлённые scores
       ↓
   ЦИКЛ ПОВТОРЯЕТСЯ (система учится)
```

---

## Что REFLEX НЕ делает

- **НЕ заменяет** AGENT_TOOL_PERMISSIONS (безопасность остаётся)
- **НЕ вызывает** LLM для scoring (чистая математика, <5ms)
- **НЕ добавляет** новые UI элементы (правило: NO NEW PANELS)
- **НЕ ломает** обратную совместимость (graceful fallback если reflex_enabled=False)
- **НЕ дублирует** MYCO (MYCO = UI подсказки пользователю, REFLEX = tool scoring для агентов)
- **НЕ дублирует** CAM (CAM = surprise detection, REFLEX = потребитель CAM сигналов)

---

## Файловая структура

```
src/services/
├── reflex_registry.py      # Layer 1: Tool catalog + metadata
├── reflex_scorer.py         # Layer 2: Scoring engine (10 signals → score)
└── reflex_feedback.py       # Layer 3: Feedback cortex (learn from results)

data/reflex/
├── tool_catalog.json        # Auto-generated tool catalog
└── feedback_log.jsonl       # Append-only feedback log

scripts/
└── generate_reflex_catalog.py  # Catalog auto-generator from code

tests/
├── test_reflex_registry.py     # Catalog completeness, schema validation
├── test_reflex_scorer.py       # Scoring formula, signal integration
├── test_reflex_feedback.py     # Feedback recording, aggregation, decay
└── test_reflex_integration.py  # E2E: task → score → execute → feedback
```
