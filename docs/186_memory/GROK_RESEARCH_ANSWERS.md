# Grok Research Answers — VETKA Memory Architecture

> Ответы Grok на 25 вопросов из GROK_RESEARCH_QUESTIONS.md
> Дата: 2026-03-16
> Статус: REVIEWED by Opus — actionable items extracted

---

## Ключевые решения (что меняем)

### REFLEX веса (scorer.py) — НОВЫЕ vs ТЕКУЩИЕ

```
Signal              Current  → Grok    Δ     Rationale
─────────────────   ───────  ──────  ─────  ──────────────────────
#1 semantic_match    0.30   → 0.22   -0.08  Перебор; phase+STM важнее
#2 cam_surprise      0.15   → 0.12   -0.03  Эвристика < проверенные данные
#3 cortex_feedback   0.15   → 0.18   +0.03  Проверенный сигнал, поднять
#4 aura_pref         0.10   → 0.10    0     Без изменений
#5 stm_relevance     0.10   → 0.15   +0.05  Recent actions важнее семантики
#6 phase_match       0.10   → 0.18   +0.08  Контекст фазы = сильный сигнал
#7 hope_lod          0.05   → 0.05    0     Вспомогательный
#8 mgc_heat          0.05   → 0.00   -0.05  Временно 0 (поднять до 0.09 после ENGRAM L1)
                     ─────    ─────
                     1.00     1.00
```

**Дополнительно:** Sparse signal boost — CAM и HOPE при срабатывании ×1.5. Реализовать в scorer.py (~15 строк).

### ENGRAM L1 ключ — 4 компонента

```
БЫЛО:    agent::filename::action
СТАЛО:   agent::filename::action::phase_type

Пример:  opus::session_tools.py::edit::fix
         opus::session_tools.py::edit::build  (другой урок!)
```

**Compound keys для multi-file patterns:**
```
pair::scorer.py::feedback.py::modify     → "всегда меняются вместе"
pair::task_board.py::task_tracker.py::fix → "при фиксе одного проверь второй"
```

### STM — две правки

1. **Decay:** linear → exponential + rehearsal
   ```python
   # БЫЛО:   weight *= (1 - 0.1 * age_minutes)
   # СТАЛО:  weight = base * exp(-0.05 * age_minutes)
   #         При повторном обращении: reset age to 0
   ```

2. **Adaptive maxlen:**
   ```python
   maxlen = 15 if agent_type == "claude_code" else 8
   ```

### ENGRAM L1 eviction — LFU + LRU hybrid

```python
eviction_score = frequency * 0.8 + recency * 0.2
# Evict lowest score when cache full

# Per-category decay:
# "danger", "architecture" → permanent (no decay)
# "pattern", "optimization" → 60 days
# "tool_select" → 30 days
```

### Demotion (L1 → L2)

```
Если агент проигнорировал cached lesson
  И задача succeeded (success_rate > 0.8)
  → demote из L1 обратно в L2
  → lesson может быть устаревшим
```

### AURA — per-agent

```python
# БЫЛО:    AURA[user_id]
# СТАЛО:   AURA[agent_type][user_id]

# Opus знает свой стиль с Danila
# Codex знает свой стиль с Danila
```

**AURA → ENGRAM feed:** tool_usage > 5 раз → auto-promote в ENGRAM L1.

### Per-category AURA decay

```python
decay_rates = {
    "communication_style": 0.01,  # /week (почти не меняется)
    "viewport_patterns":   0.03,  # /week
    "tool_usage_patterns": 0.05,  # /week (меняется чаще)
}
```

### Feedback loops (не только линейная цепочка)

```
MYCELIUM failure → CAM boost (surprise ↑) + STM boost (weight ↑)
                 → CORTEX record (failure)
                 → Resource Learnings extract pitfall
```

---

## Решения "оставить как есть"

| Вопрос | Решение | Почему |
|--------|---------|--------|
| Cross-session STM | Не нужен | STM = минуты; cross-session = ENGRAM/Qdrant |
| Двойное STM (промпт + REFLEX) | Оставить | Не bias, а усиление |
| Promotion threshold = 3 | Оставить | Статистически достаточно при ~50 q/day |
| Строковый ключ (не hash) | Оставить | <1000 записей, debug важнее |
| HOPE weight = 0.05 | Оставить | Вспомогательный сигнал |
| Sensory memory | Не добавлять | STM уже покрывает |
| JEPA activation | Phase 190+ | Сначала ENGRAM L1 |

---

## Решения для подвисших задач

| Задача | Grok recommendation | Action |
|--------|---------------------|--------|
| Merge REFLEX | Мерджить as-is, tune потом | Merge first, then new weights |
| TaskBoard worktree | CORTEX = success только после main merge | Update CORTEX logic |
| Playwright unification | Migration: old tool_id → alias в CORTEX | Add alias mapping |

---

## Вопросы к Grok-ответам (Opus review)

| Grok сказал | Opus комментарий |
|-------------|-----------------|
| MGC weight → 0.00 временно | Рискованно обнулять. Лучше 0.03 чтобы не потерять сигнал |
| ELISYA module rename | Не нужен — модуль уже в src/elisya/, переименование файла ничего не даёт |
| L3 fallback = git grep | Осторожно — git grep может быть дорогим. Добавить timeout 500ms |
| Sparse ×1.5 | Хорошая идея, но нужен A/B тест на 50 задачах |
| Per-agent weights.json | Правильно что "не сразу". Phase 190+ |

---

## Итоговый приоритет реализации (обновлённый)

| # | Задача | Строк | Приоритет | Блокер |
|---|--------|-------|-----------|--------|
| 0 | **Merge REFLEX branch to main** | 0 (merge) | БЛОКЕР | Без этого нельзя менять веса |
| 1 | **MEMORY.md cleanup (831→50)** | -700 | Критично | Нет |
| 2 | **semantic_recall в session_init** | +20 | Критично | resource_learnings.py |
| 3 | **REFLEX weights rebalance** | ~10 | Критично | REFLEX merge (задача 0) |
| 4 | **agent_briefing в session_init** | +30 | Важно | task_board.py |
| 5 | **STM: exp decay + adaptive maxlen** | ~15 | Важно | Нет |
| 6 | **AURA rename (engram→aura) + per-agent** | ~30 | Важно | Нет |
| 7 | **digest.agent_focus** | +15 | Важно | digest schema |
| 8 | **ENGRAM L1 cache (4-key + compound)** | +80 | После L2 | semantic_recall (задача 2) |
| 9 | **L1 eviction (LFU+LRU hybrid)** | +20 | После L1 | ENGRAM L1 (задача 8) |
| 10 | **L1 demotion mechanism** | +15 | После L1 | ENGRAM L1 (задача 8) |
| 11 | **AURA → ENGRAM feed** | +10 | После L1 | AURA + ENGRAM L1 |
| 12 | **Feedback loops (failure → CAM/STM)** | +15 | Nice to have | Нет |
