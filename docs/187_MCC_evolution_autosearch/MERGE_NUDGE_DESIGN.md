# 189: Merge Nudge — автоматическое напоминание о мерже worktree → main

## Проблема

Агент завершает таски в worktree (`done_worktree`), но нет сигнала "ветка готова к мержу".
Проверенный код висит в ветке, забывается, не попадает в main.

## Два подхода (взаимозаменяемы, выбираем один)

### Вариант A: PostToolUse Hook (рекомендуемый старт)

**Суть:** Shell-хук после `vetka_task_board` проверяет ветку и шепчет агенту.

```
Agent calls vetka_task_board
  → PostToolUse hook fires
    → bash: git branch → claude/*? → git rev-list main..HEAD --count
      → stdout: "[merge-nudge] Branch claude/X: 3 commits ahead of main — consider merging"
        → Agent sees this in context → relays to user
```

**Плюсы:** 5 минут работы, zero dependencies, работает сразу.
**Минусы:** Не знает action/status из MCP ответа — срабатывает на любой task_board вызов (list, get...). Фильтруем грубо: молчим на main, говорим только на claude/* с коммитами.

**Шум:** Низкий. На main — тишина. На worktree без коммитов — тишина. Только когда реально есть что мержить.

**Реализация:**
```json
// .claude/settings.json → hooks.PostToolUse
{
  "matcher": "mcp__vetka__vetka_task_board",
  "hooks": [{
    "type": "command",
    "command": "branch=$(git branch --show-current 2>/dev/null); case \"$branch\" in claude/*) ahead=$(git rev-list main..HEAD --count 2>/dev/null || echo 0); [ \"$ahead\" -gt 0 ] && echo \"[merge-nudge] Branch $branch: $ahead commits ahead of main — consider merging\" ;; esac",
    "timeout": 3000
  }]
}
```

### Вариант B: REFLEX branch_maturity (эволюция)

**Суть:** REFLEX получает новый сигнал `branch_maturity` при расчёте рекомендаций.

```
REFLEX score calculation
  → branch_maturity signal:
    → count done_worktree tasks for current branch
    → if count >= threshold (default: 2) → boost "merge_to_main" suggestion
    → REFLEX output: { tool_id: "merge_to_main", score: 0.8, reason: "3 verified tasks on branch" }
```

**Плюсы:** Учитывает task statuses (не просто коммиты), интегрируется в существующий scoring, может учитывать приоритет/complexity тасков.
**Минусы:** Требует новый tool в catalog (`merge_to_main`), изменения в REFLEX scoring, тестирование весов.

**Когда нужен:** Когда Вариант A уже работает и хочется точнее: не "3 коммита", а "2 verified tasks priority 1-2".

## Рекомендация

**Старт: Вариант A.** Один хук, 10 строк, мгновенный эффект.
**Эволюция: Вариант B** заменяет A когда REFLEX scoring стабилен и нужна гранулярность.
Не нужны оба одновременно — B supersedes A.

## Файлы

| Вариант | Файл | Изменение |
|---------|------|-----------|
| A | `.claude/settings.json` | +1 PostToolUse hook |
| B | `data/reflex/tool_catalog.json` | +1 tool `merge_to_main` |
| B | `src/reflex/scoring.py` (или где scoring) | +branch_maturity signal |
| B | `src/mcp/tools/task_board_tools.py` | query done_worktree by branch |
