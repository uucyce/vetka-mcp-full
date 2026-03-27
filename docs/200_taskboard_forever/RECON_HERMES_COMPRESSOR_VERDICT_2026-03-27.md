# RECON: HERMES Structured Compressor — Adopt / Defer / Kill?

**Date:** 2026-03-27
**Author:** Eta (Harness Engineer 2) + 3 Sonnet recon agents
**Task:** tb_1774499127_1
**Verdict:** DEFER — не пятое колесо, но не наш приоритет сейчас

---

## 1. Что делает HERMES Compressor

**Сжимает conversation turns** (историю чата), а не JSON payload.

Алгоритм (5 фаз):
1. Tool result pruning — заменяет старые tool outputs на placeholder (rule-based)
2. Head protection — сохраняет первые N сообщений (system prompt)
3. Tail protection — сохраняет последние N сообщений по token budget
4. **LLM-based summarization** — средние сообщения → structured markdown через ВЫЗОВ LLM
5. Tool-pair sanitization — чистит orphaned tool_call/tool_result пары

**Шаблон (7 секций):**
```
## Goal
## Constraints & Preferences
## Progress (Done / In Progress / Blocked)
## Key Decisions
## Relevant Files
## Next Steps
## Critical Context
```

**Критично:** Требует LLM-вызов (auxiliary model). Iterative — хранит `_previous_summary`, обновляет при каждом сжатии.

---

## 2. Что уже есть в VETKA (8 подсистем)

| Подсистема | Тип | Сжимает контекст окна? | Structured summary? |
|------------|-----|----------------------|-------------------|
| **ELISION** | JSON key/path abbreviation | DA — primary role | NET — сжимает структуру, не создаёт |
| **HOPE** | LLM LOD (LOW/MID/HIGH) | Косвенно — выбирает detail level | Частично: Global/Detailed/Specifics |
| **MGC** | 3-tier cache (RAM→SQLite→JSON) | NET | NET |
| **ARC** | Graph transformation suggestions | NET | NET |
| **CAM** | Saliency/surprise scoring | Косвенно — surprise_map для ELISION L3 | NET |
| **JEPA** | Media embedding extraction | NET — работает с видео/аудио | NET |
| **ENGRAM** | O(1) pattern cache | NET — recall layer | NET |
| **REFLEX** | 8-signal tool ranker | Косвенно — выбирает HOPE LOD | NET |

**Вывод:** Ни одна подсистема не сжимает conversation history. ELISION сжимает injected context payload на старте промпта. Когда чат длинный — никто не помогает.

---

## 3. Что делает Claude Code нативно

Claude Code имеет встроенный **auto-compact**:
- Триггер: ~83-95% контекстного окна (настраивается через `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`)
- Сжатие: 60-90% token reduction
- Формат: **freeform prose** — НЕ структурированный
- Ручной: `/compact [focus]`

**Известные потери при auto-compact:**
- CLAUDE.md инструкции деградируют
- Точные error messages теряются
- Naming conventions и project-specific rules забываются
- Task state (какой subtask в работе) теряется
- Триггер по token count, а не по task boundary

**Post-compaction hooks** существуют — можно re-inject структурированный контекст после compact.

---

## 4. Gap Analysis

```
HERMES compressor закрывает gap?

                    VETKA ELISION    Claude Code     HERMES
                    ────────────     auto-compact    compressor
Target:             JSON payload     Chat turns      Chat turns
Method:             Rule-based       LLM (native)    LLM (auxiliary)
Structured:         NET              NET (prose)     DA (7 sections)
Iterative:          NET              NET             DA
LLM required:      NET              DA (built-in)   DA (extra call)
Task-aware:         NET              NET             NET (generic)
VETKA-aware:        DA               NET             NET
```

**Gap существует:** structured conversation compression с сохранением task state.

**Но Claude Code уже делает 80% работы** — auto-compact сжимает turns.
Оставшиеся 20% — потеря структуры (task IDs, owned paths, decisions).

---

## 5. Вердикт: DEFER

### Почему НЕ kill:
- Gap реальный: auto-compact теряет structured state
- Post-compaction hook pattern позволяет re-inject VETKA state без LLM-вызова

### Почему НЕ adopt сейчас:
- **Стоимость:** Каждое сжатие = LLM-вызов к auxiliary model (latency + cost)
- **Risk:** Предыдущий Hermes adoption (FTS5) вызвал 3-дневный застой
- **80/20:** Claude Code auto-compact закрывает 80% потребности бесплатно
- **Alternatives:** Post-compaction hook + structured state file = 90% value за 10% effort

### Рекомендуемый путь (если/когда понадобится):
1. **Phase 1 (minimal):** Post-compaction hook → re-inject `session_init` context из файла
2. **Phase 2 (medium):** Structured state snapshot при каждом `action=complete` → файл
3. **Phase 3 (full):** HERMES-style LLM compressor только если Phase 1-2 недостаточно

### Аббревиатура для glossary:
```
HERMES-SC  = Hermes Structured Compressor
             Conversation-turn LLM summarizer (7-section template)
             Status: DEFERRED — use Claude Code auto-compact + post-compaction hooks first
             Gap: structured state preservation after compaction
             Cost: 1 LLM call per compaction cycle
```

---

## 6. Subsystem Abbreviation Map (обновлённый)

| Abbr | Full Name | Layer | Context Compression? |
|------|-----------|-------|---------------------|
| ELISION | Efficient Language-Independent Symbolic Inversion of Names | L0: Token | DA — JSON payload |
| HOPE | Hierarchical Orthogonal Predictive Embedding | L1: LOD | Косвенно — detail level |
| MGC | Multi-Generation Cache | L2: Storage | NET |
| ARC | Architecture Reasoning Cycle | L3: Reasoning | NET |
| CAM | Constructivist Agentic Memory | L1: Signal | Косвенно — surprise для ELISION |
| JEPA | Joint Embedding Predictive Architecture | L4: Media | NET |
| ENGRAM | L1 O(1) Pattern Cache | L2: Recall | NET |
| REFLEX | 8-Signal Tool Ranker | L1: Orchestration | Косвенно — выбирает LOD |
| HERMES-SC | Structured Conversation Compressor | L0: Turns | DA — но requires LLM |
| CC-COMPACT | Claude Code Auto-Compact | L0: Turns | DA — freeform prose |
