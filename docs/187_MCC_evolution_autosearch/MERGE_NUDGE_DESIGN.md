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

## Вариант C: Merge Gate — блокировка случайного мержа (защита)

Варианты A и B — про "напомнить смержить". Вариант C — обратная задача: **не дать смержить непроверенное**.

**Проблема:** Агент или пользователь делает `git merge claude/X` — а ветка содержит код который решили переделать, или таск ещё не approved. Мерж проходит, мусор в main.

**Суть:** `pre-merge-commit` git hook проверяет TaskBoard перед мержем worktree ветки.

```
git merge claude/stupefied-torvalds
  → pre-merge-commit hook fires
    → query task_board: есть ли tasks для этой ветки?
      → all done_worktree + merge_approved? → OK, merge proceeds
      → any pending/in_progress? → BLOCK: "Branch has 2 unfinished tasks"
      → any done_worktree без merge_approved? → WARN: "1 task not yet approved for merge"
```

**Реализация:**
```bash
# .git/hooks/pre-merge-commit
MERGE_BRANCH=$(git log -1 --format=%s MERGE_HEAD 2>/dev/null | grep -oP "claude/\S+")
if [ -n "$MERGE_BRANCH" ]; then
  # Query task_board for branch tasks
  python3 scripts/check_merge_gate.py "$MERGE_BRANCH"
  # Exit non-zero to block merge
fi
```

**scripts/check_merge_gate.py:**
- Reads `data/task_board.json` (or calls MCP)
- Filters tasks where `branch == $MERGE_BRANCH` or commit on that branch
- Checks: all tasks `done_worktree`? Any `pending`/`in_progress`?
- Optional: check `merge_approved` field (new TaskBoard field)
- stdout message for agent, exit code 0 (allow) or 1 (block)

**TaskBoard расширение:**
- Новое поле `merge_approved: bool` (default: false)
- `vetka_task_board action=update task_id=X merge_approved=true` — user/QA approves
- Или автоматически: если task `done_worktree` > 24h без reject → auto-approve

**Уровни строгости:**
1. **Soft (рекомендуется):** warn но не блокирует (`exit 0` всегда, только stdout)
2. **Medium:** блокирует если есть pending tasks, warn на unapproved
3. **Strict:** блокирует всё без `merge_approved: true`

**Плюсы:** Защита от мусора в main, интеграция с TaskBoard lifecycle.
**Минусы:** Требует `check_merge_gate.py`, новое поле в TaskBoard, может раздражать при быстром workflow.

## Рекомендация

**Старт: Вариант A** (merge nudge) + **Вариант C soft** (merge gate warning). Оба — shell хуки, минимум кода.
**Эволюция: Вариант B** (REFLEX) + **Вариант C medium** (blocking gate).
Не нужны все одновременно — A→B замена, C дополняет любой из них.

## Файлы

| Вариант | Файл | Изменение |
|---------|------|-----------|
| A | `.claude/settings.json` | +1 PostToolUse hook |
| B | `data/reflex/tool_catalog.json` | +1 tool `merge_to_main` |
| B | `src/reflex/scoring.py` (или где scoring) | +branch_maturity signal |
| B | `src/mcp/tools/task_board_tools.py` | query done_worktree by branch |
| C | `.git/hooks/pre-merge-commit` | merge gate check |
| C | `scripts/check_merge_gate.py` | TaskBoard query + validation |
| C | `src/mcp/tools/task_board_tools.py` | +merge_approved field |
