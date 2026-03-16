# Grok Research: Open Questions for VETKA Memory Architecture

> Контекст: мы спроектировали когнитивный стек VETKA (13 подсистем). Есть открытые вопросы по весам, границам, и оптимизации. Нужен research от Grok.
>
> Документы для контекста (прочитать перед ответами):
> - `docs/186_memory/VETKA_COGNITIVE_STACK_ARCHITECTURE.md` — полная архитектура
> - `docs/186_memory/VETKA_DYNAMIC_MEMORY_BLUEPRINT.md` — Blueprint v1.1
> - `docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md` — глоссарий v2

---

## Блок 1: REFLEX веса — калиброваны ли они?

### Текущие веса (Phase 172, заданы вручную):

```
#1 semantic_match   0.30  (embedding similarity vs tool intent_tags)
#2 cam_surprise     0.15  (CAM novelty score)
#3 cortex_feedback  0.15  (CORTEX historical success rate)
#4 aura_pref        0.10  (AURA user tool preferences)
#5 stm_relevance    0.10  (STM recency of related actions)
#6 phase_match      0.10  (build/fix/research alignment)
#7 hope_lod         0.05  (HOPE zoom level)
#8 mgc_heat         0.05  (MGC cache frequency)
```

### Вопросы:

**Q1.1:** Правильно ли что semantic_match доминирует (0.30)? В реальности агенты часто знают какой tool нужен не по семантике, а по контексту (phase, recent actions). Не стоит ли поднять phase_match и stm_relevance?

**Q1.2:** CORTEX и CAM имеют одинаковый вес (0.15). Но CORTEX = проверенные данные (success rate), а CAM = эвристика (surprise). Не должен ли CORTEX быть выше?

**Q1.3:** HOPE и MGC имеют минимальные веса (0.05). Это потому что они менее полезны, или потому что их сигналы ещё не зрелые? Если MGC начнёт точно отражать "горячие" файлы — не стоит ли поднять до 0.10?

**Q1.4:** Нужен ли adaptive weight tuning? Например: если для agent_type=codex фронтенд-tools всегда выигрывают — стоит ли автоматически подстраивать веса per-agent? Или это overengineering?

**Q1.5:** DeepSeek Engram paper упоминает "новую ось разреженности" — можно ли применить аналогичный принцип к REFLEX scoring? Например: некоторые сигналы = "sparse" (срабатывают редко, но когда срабатывают — очень точны), а некоторые = "dense" (срабатывают всегда, но с меньшей точностью). Нужна ли двухрежимная scoring system?

---

## Блок 2: ENGRAM L1 — формат ключа

### Текущее предложение:

```python
key = f"{agent_type}::{filename}::{action_type}"
# Пример: "opus::session_tools.py::edit"
```

### Вопросы:

**Q2.1:** Достаточно ли 3 компонентов (agent, file, action)? Или нужна 4-компонентная N-грамма, включающая phase_type? Пример: `"opus::session_tools.py::edit::fix"` vs `"opus::session_tools.py::edit::build"` могут давать разные lessons.

**Q2.2:** Как обрабатывать multi-file patterns? Например, "scorer.py и feedback.py всегда меняются вместе" — это паттерн про два файла. Ключ `"*::scorer.py::pattern"` не захватывает связь с feedback.py. Нужен ли compound key или отдельный тип записи "file_pair"?

**Q2.3:** DeepSeek Engram использует hash от N-gram входных токенов. Мы используем строковую конкатенацию. Для 200 записей это не проблема, но если cache вырастет до 1000+ — нужен ли integer hash для производительности? Или Python dict и так O(1) для строковых ключей?

**Q2.4:** Wildcard matching: сейчас `"*::file::action"` = fallback для любого agent. Нужна ли более гранулярная wildcard система? Например `"*::*.py::modify"` = "для любого Python файла при модификации"?

---

## Блок 3: STM — роль в новой архитектуре

### Текущее состояние:

STM = deque(maxlen=10), decay за минуты, источники: user/agent/system/hope/cam/pipeline.

### Вопросы:

**Q3.1:** STM сейчас per-session (умирает при перезапуске). Нужно ли cross-session STM? Например: "в прошлой сессии ты редактировал session_tools.py и получил ошибку" — это STM или уже ENGRAM/Qdrant territory?

**Q3.2:** STM decay formula: `weight *= (1 - 0.1 * age_minutes)`. Это линейный decay. Нейронауки говорят что человеческая STM имеет экспоненциальный decay с "rehearsal" эффектом (повторное обращение reset-ит timer). Стоит ли сменить на exponential + rehearsal?

**Q3.3:** STM maxlen=10. Для Claude Code сессии это может быть мало (сессия длится часами). Для Chat agent — может быть много (быстрые вопросы). Нужен ли adaptive maxlen per agent_type?

**Q3.4:** STM feeds into REFLEX signal #5 (weight 0.10). Но STM также влияет на контекст промпта (recent actions). Это двойное использование — не создаёт ли оно bias? Если STM и так в промпте, нужен ли ещё REFLEX-сигнал?

---

## Блок 4: L2 → L1 promotion — пороги и decay

### Текущее предложение:

- Promotion threshold: match_count ≥ 3
- Eviction: LRU + temporal decay (30 days)
- Max entries: 200

### Вопросы:

**Q4.1:** Порог 3 — эмпирический. В ML обычно используют statistical significance. Для 200 записей при ~50 queries/day — какой порог даёт баланс между "не промоутим мусор" и "не пропускаем полезное"?

**Q4.2:** LRU vs LFU: LRU evicts самый старый, LFU — самый редко используемый. Для ENGRAM кажется LFU правильнее (мы хотим сохранить часто используемые паттерны, даже если они старые). Или гибрид LRU+LFU?

**Q4.3:** Temporal decay 30 дней — для проекта который живёт месяцы, это может быть слишком агрессивно. Паттерн "agent_pipeline.py = danger zone" актуален всегда. Нужна ли категория "permanent" entries без decay?

**Q4.4:** Counter-promotion: если ENGRAM L1 hit даёт неправильный результат (агент проигнорировал cached advice и всё прошло нормально) — нужен ли механизм demotion обратно в L2?

---

## Блок 5: AURA — scope и связь с другими системами

### Текущее:

AURA хранит per-user: communication_style, viewport_patterns, tool_usage_patterns.

### Вопросы:

**Q5.1:** AURA = per-user. Но в multi-agent setup (Opus + Codex + Cursor работают для одного юзера) — нужна ли per-agent AURA? Т.е. Opus знает свой стиль работы с Danila, а Codex знает свой.

**Q5.2:** AURA сейчас влияет только на REFLEX (signal #4, 0.10). Но AURA знает tool_usage_patterns — это прямой input для ENGRAM L1 (если юзер всегда использует tool X для task Y — это deterministic knowledge). Нужен ли feed AURA → ENGRAM?

**Q5.3:** AURA temporal decay: `confidence -= 0.05/week`. Через 20 недель confidence = 0. Но communication_style обычно не меняется за 5 месяцев. Нужен ли per-category decay rate? (стиль общения = slow decay, tool preferences = fast decay)

---

## Блок 6: Архитектурные вопросы

**Q6.1:** Cognitive chain сейчас: AURA → STM → CAM → ENGRAM → Qdrant → REFLEX → MYCELIUM → CORTEX. Это линейная модель. В реальном мозге всё параллельно + есть обратные связи (feedback loops). Нужны ли explicit feedback loops помимо CORTEX → REFLEX? Например: MYCELIUM failure → STM boost (agent помнит провал ярче)?

**Q6.2:** ELISYA = координация + Qdrant collection (vetka_elisya). Это два разных использования одного имени. Стоит ли разделить? Или оставить как есть (одно имя, два аспекта)?

**Q6.3:** JEPA = dormant. Есть ли смысл его активировать для predictive tool selection? Т.е. JEPA предсказывает "на основе текущего контекста, следующий tool будет X" ещё до того как REFLEX scoring начнётся.

**Q6.4:** Каскадный fallback: ENGRAM miss → Qdrant miss → что дальше? Сейчас — ничего (agent работает без context). Нужен ли L3 fallback (git log search, file grep)?

**Q6.5:** Сколько уровней в реальном мозге? Психология выделяет sensory memory (~250ms), STM (~30s), working memory (~minutes), LTM (permanent). У нас STM + ENGRAM + Qdrant = 3 уровня. Нужен ли "sensory memory" (совсем короткий buffer, <1s, для input parsing)?

---

## Блок 7: Подвисшие задачи — связь с памятью

**Q7.1:** Merge REFLEX branch: после мерджа веса REFLEX могут измениться. Стоит ли сначала ответить на Q1.1-Q1.5 (веса), а потом мерджить? Или мерджить as-is и tune потом?

**Q7.2:** TaskBoard worktree lifecycle (done_worktree → done_main): как это влияет на CORTEX? Если таск closed в worktree, но ещё не в main — CORTEX должен считать это success или pending?

**Q7.3:** Playwright + Chrome Control unification: это не связано с памятью напрямую, но если объединённый tool будет иметь другой tool_id — CORTEX потеряет историю старых tool_ids. Нужна ли migration strategy для feedback_log.jsonl?

---

## Формат ответа (для Grok)

Для каждого вопроса:
1. **Ответ** (1-3 предложения)
2. **Обоснование** (почему именно так)
3. **Рекомендация для VETKA** (конкретное действие: изменить/оставить/отложить)
4. **Confidence** (low/medium/high)

Если вопрос требует эксперимента, а не теоретического ответа — так и сказать.
