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

**Проблема:** Ollama 8B получает `architecture_docs: ["docs/190.../CUT_TARGET_ARCHITECTURE.md"]` — путь, не содержимое. Модель не умеет читать файлы сама.

**Решение:** В `dispatch_task()` перед вызовом pipeline:
1. Прочитать каждый файл из `architecture_docs[]` и `recon_docs[]`
2. Обрезать до N токенов на файл (default: 2000 tokens ≈ 8KB)
3. Обрезать суммарно до M токенов (default: 6000 tokens ≈ 24KB)
4. Добавить в task description как секцию `## Architecture Context`

```python
# В task_board.py: dispatch_task() или _prepare_dispatch_payload()
def _inject_doc_context(task: dict, max_per_doc: int = 2000, max_total: int = 6000) -> str:
    """Read architecture_docs + recon_docs, truncate, return context block."""
    docs = list(task.get("architecture_docs") or []) + list(task.get("recon_docs") or [])
    if not docs:
        return ""
    
    sections = []
    total_chars = 0
    char_per_doc = max_per_doc * 4  # ~4 chars per token
    char_total = max_total * 4
    
    for doc_path in docs:
        full_path = PROJECT_ROOT / doc_path
        if not full_path.exists():
            sections.append(f"<!-- {doc_path}: NOT FOUND -->")
            continue
        try:
            content = full_path.read_text(encoding="utf-8")[:char_per_doc]
            if total_chars + len(content) > char_total:
                content = content[:max(0, char_total - total_chars)]
            if content:
                sections.append(f"### {doc_path}\n{content}")
                total_chars += len(content)
        except Exception:
            sections.append(f"<!-- {doc_path}: READ ERROR -->")
    
    if not sections:
        return ""
    return "\n\n## Architecture Context\n\n" + "\n\n---\n\n".join(sections)
```

**Точка инжекта:** `task_board.py` → `dispatch_task()` или `_build_task_text()`
Нужно найти где формируется текст для pipeline.

**Файлы:**
- `src/orchestration/task_board.py` — dispatch_task, _build_task_text
- Возможно: `src/orchestration/agent_pipeline.py` — если текст формируется там

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
