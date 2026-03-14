# Grok Research — Phase 154: Mycelium Simplification

**Источник:** @x-ai/grok-4.1-fast (24109 знаков)
**Дата:** 2026-02-17

---

## Ключевые решения

### 1. UX Pattern: Figma-like drill-down
- Double-click на ноду = вход внутрь (expand animation)
- Breadcrumb = навигация и индикатор уровня
- Footer = 3 primary actions (фиксированных для уровня)
- Context menu (right-click / gear) = скрытые действия

### 2. Transition: Expand Animation (300ms)
- Нода раскрывается на весь экран, внутри sub-DAG
- Лучше чем zoom (не dizzy), slide (теряет spatial), fade (нет nesting feeling)
- ReactFlow: node bounds scaling + Framer Motion easing
- Breadcrumb + partial fade out сохраняют контекст

### 3. Свёртка кнопок (из Грока, уточнено)

| Состояние | Action 1 | Action 2 | Action 3 | В ⚙ popup | Автоматически | Убрано |
|-----------|----------|----------|----------|-----------|---------------|--------|
| FIRST RUN | Select Folder | Enter URL | Describe Text | API keys (modal) | Auto-scan, validate | Всё остальное |
| ROADMAP | Launch | Ask Architect | Add Task | Filter (dropdown), Stats (popup), Edit DAG (modal) | Auto-roadmap, save, heartbeat | New/Save/Dispatch/Export |
| ЗАДАЧА | Launch | Edit | Back | Team (dropdown), Validate (Ctrl+V) | Auto-assign team/template, undo | LIVE/Execute dupes, Captain button |
| ИСПОЛНЕНИЕ | Pause | Cancel | Back | Log export (dropdown) | Heartbeat, stats, timer | Edit/Preset (locked while running) |
| РЕЗУЛЬТАТ | Accept | Redo | Back | Diff export (popup), Verifier details (Ctrl+D) | Stats, verdict, merge on Accept | Validate/Generate (already done) |

### 4. Playground: один на проект
- Fixed name: `<project>-playground` (e.g., "vetka-playground")
- Git worktree: `git worktree add vetka-playground main`
- Quota: check size before agent writes (soft 80% warn, hard block)
- Delete: UI button in ⚙ → `git worktree remove` + confirm
- Remote: `git push <remote> <playground-branch>` или rsync
- Cleanup: `git worktree prune` + `git gc` post-merge

### 5. Wireframe Layout (общий для всех уровней)
```
+--- BREADCRUMB (top) -----------------------------------------------+
| Project > Roadmap > Task: add dark mode > Running...                |
+--------------------------------------------------------------------+
|                                                                     |
| [Compact Chat]                              [Compact Stats]         |
|    (top-left)                                  (top-right)          |
|                                                                     |
|                     DAG CANVAS (center, 70%)                        |
|                                                                     |
|                                                                     |
|                                                                     |
|                                                    [Compact Tasks]  |
|                                                      (bottom-right) |
+--------------------------------------------------------------------+
| [Action 1]              [Action 2]              [Action 3]          |
+--- FOOTER (bottom) ------------------------------------------------+
```

---

## Полный текст research

(см. чат VETKA от 2026-02-17, 24109 знаков)
