# PLAN 189.E: Task Quality Improvements for Localguys
**Date:** 2026-03-18
**Phase:** 189
**Agent:** claude_code (Opus)
**Source:** Agent feedback + recon analysis

---

## 1. Контекст

Localguys (Ollama 8B) получают таски через dispatch, но:
- `architecture_docs` — массив путей-строк, модель не читает файлы
- Мёртвые ссылки в `architecture_docs` не детектятся
- Description может быть стеной текста без summary
- Session init не передаёт memory context

---

## 2. Задачи

### 189.15: Auto-inject architecture_docs content при dispatch
**Приоритет:** P1 (высокий импакт)
**Сложность:** Средняя
**Детальный рекон:** `RECON_189_AUTO_INJECT_ARCH_DOCS_2026-03-18.md`

**Проблема:** Ollama 8B получает `architecture_docs` как path-строки, не содержимое.
Evidence chain (code audit): task_board.py:655 хранит пути → roadmap_task_sync.py:186 пакует пути →
architect_prefetch.py:517 считает кол-во → agent_pipeline.py:3720 вставляет строку путей →
dispatch (task_board.py:2064) собирает `task_text = title + desc` → **docs content НИГДЕ не читается**.

**Решение:** Context Budget Guard — адаптивный inject с учётом модели:

1. **Injection point:** `task_board.py:dispatch_task()`, lines 2064-2066
   ```python
   task_text = f"{task['title']}\n\n{task.get('description', '')}"
   # >>> INSERT HERE: doc context injection <<<
   result = await pipeline.execute(task_text, task["phase_type"])
   ```

2. **Context budget по модели** (через LLMModelRegistry):
   ```
   docs_budget = min(available * 0.5, context_length * 0.30)
   ```
   | Model | Context | 30% Budget | Docs fit |
   |-------|---------|------------|----------|
   | Ollama 8B | 8-32K | 2.4-9.6K | 1-3 docs MAX |
   | Qwen 30B | 131K | ~39K | 10-15 docs |
   | Claude Opus | 200K | ~60K | 20+ docs |

3. **ELISION compression** (src/memory/elision.py) — 40-60% savings, уже используется в pipeline STM

4. **Шаги имплементации:**
   - `_load_task_docs(task)` — read files, return content
   - `_estimate_docs_budget(preset)` — model context → budget
   - Inject в task_text между desc и pipeline.execute()
   - Truncation: per-doc cap → total cap → ELISION L2-3 → top-N docs
   - Log: task_weight, docs_budget, docs_included, docs_truncated

**Файлы:**
- `src/orchestration/task_board.py` — dispatch_task (injection point)
- `src/elisya/llm_model_registry.py` — context_length per model
- `src/memory/elision.py` — compression
- `data/templates/model_presets.json` — tier → model mapping

---

### 189.16: Validation architecture_docs paths при add_task
**Приоритет:** P2 (средний)
**Сложность:** Лёгкая

**Проблема:** Мёртвые ссылки в architecture_docs не детектятся. Файл мог быть переименован/удалён.

**Решение:** В `add_task()` проверить каждый путь, вернуть warning если не найден:
```python
def _validate_doc_refs(docs: list, field_name: str) -> list:
    """Return warnings for missing doc paths."""
    warnings = []
    for doc_path in docs:
        full = PROJECT_ROOT / str(doc_path)
        if not full.exists():
            warnings.append(f"{field_name}: '{doc_path}' not found")
    return warnings
```

Добавить в response `add_task`:
```json
{
  "success": true,
  "task_id": "tb_xxx",
  "warnings": ["architecture_docs: 'docs/old_file.md' not found"]
}
```

**Не блокировать** создание — только warning.

**Файлы:**
- `src/orchestration/task_board.py` — add_task()
- `src/mcp/tools/task_board_tools.py` — handle_task_board() add action response

---

### 189.17: Summary field в TaskData + auto-generation
**Приоритет:** P2 (средний)
**Сложность:** Лёгкая

**Проблема:** MiniTasks expanded view показывает title + status, но нет краткого описания. Description бывает стеной текста (CUT-таски: dataclass + алгоритмы).

**Решение:**
1. Добавить `summary?: string` в TaskData interface (TaskCard.tsx)
2. При создании таска — авто-генерация если summary не передан:
   ```python
   if not summary:
       # Первое предложение description, или title[:100]
       desc = str(task.get("description") or "").strip()
       first_line = desc.split("\n")[0].strip()
       summary = first_line[:100] if first_line and not first_line.startswith('"""') else title[:100]
   ```
3. Показывать в MiniTasks expanded view под title
4. Добавить `summary` в MCP schema + task_board_tools list response

**Файлы:**
- `client/src/components/panels/TaskCard.tsx` — TaskData interface
- `client/src/components/mcc/MiniTasks.tsx` — expanded view render
- `src/orchestration/task_board.py` — add_task() auto-gen
- `src/mcp/tools/task_board_tools.py` — schema + list response

---

### 189.18: Memory digest в session_init response
**Приоритет:** P3 (низкий)
**Сложность:** Лёгкая

**Проблема:** Агент при session_init не получает ключевые правила из memory (feedback memories).

**Решение:** Добавить в session_init response:
```json
{
  "memory_digest": {
    "feedback_count": 3,
    "last_updated": "2026-03-18",
    "key_rules": [
      "no docs in worktree — must be on main",
      "always close via task_board, never raw git commit",
      "no preview for CUT — use direct render"
    ]
  }
}
```

Источник: scan Claude memory files или CLAUDE.md rules.

**Файлы:**
- `src/mcp/vetka_mcp_bridge.py` — session_init handler
- Или: `src/services/session_service.py` (если есть)

---

## 3. Порядок выполнения

```
189.15 (auto-inject)     ← самый высокий импакт, делаем первым
    ↓
189.16 (validation)      ← попутно, быстро
    ↓
189.17 (summary field)   ← UI polish
    ↓
189.18 (memory digest)   ← если останется время
```

## 4. Зависимости

- 189.15 зависит от понимания dispatch flow (нужен рекон dispatch_task)
- 189.16 независим
- 189.17 независим от 189.15-16
- 189.18 независим

Все таски: `project_id: "vetka"`, `project_lane: "task_board"`
