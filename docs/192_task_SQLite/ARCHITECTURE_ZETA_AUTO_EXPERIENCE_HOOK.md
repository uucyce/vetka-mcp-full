# Architecture: Auto-Experience Hook (Session End Persistence)
**Phase:** 195+ (Agent Infrastructure — Zeta)
**Date:** 2026-03-22
**Author:** Opus (Zeta)
**Status:** ARCHITECTURE → ready for implementation

---

## Problem Statement

Агент завершает сессию → опыт умирает с контекстным окном.

Существующие механизмы:
- Protocol Guard **напоминает** про experience report (warn) — но agent может проигнорировать
- Sigma's D5 Auto-debrief **триггерит** при закрытии последнего таска фазы — но не при конце сессии
- CLAUDE.md Generator **читает** experience reports — но нужен кто-то, кто их запишет

**Gap:** Нет автоматического сохранения passive signals при закрытии терминала.

---

## Solution: Claude Code `stop` Hook

Claude Code поддерживает hooks — shell команды на lifecycle events.
Hook на `stop` event = скрипт запускается **автоматически** при каждом `/exit`, Ctrl+C, или таймауте.

```
Agent работает
  → CORTEX собирает passive signals (tool success/fail, timing)
  → Session tracker фиксирует (tasks_completed, files_touched)
  → Agent закрывает терминал (/exit или Ctrl+C)
  → HOOK FIRES: auto_experience_save.py
    → Читает session tracker state
    → Читает CORTEX feedback за сессию
    → Определяет role из текущей ветки (agent_registry)
    → Сохраняет ExperienceReport в data/experience_reports/
    → Следующий session_init → CLAUDE.md Generator → predecessor advice
```

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                  DURING SESSION                          │
│                                                         │
│  Session Tracker          CORTEX Feedback                │
│  ┌──────────────┐        ┌──────────────┐               │
│  │ tasks_completed: 3   │ feedback_log: │               │
│  │ files_edited: {..}   │  tool_id: X   │               │
│  │ files_read: {..}     │  success: T/F │               │
│  │ edit_count: 12       │  useful: T/F  │               │
│  │ search_count: 8      │  exec_ms: 150 │               │
│  └──────┬───────┘        └──────┬───────┘               │
│         │                       │                        │
│         └───────────┬───────────┘                        │
│                     │                                    │
│  ON SESSION END     ▼                                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  auto_experience_save.py (hook script)            │   │
│  │                                                    │   │
│  │  1. Detect role from git branch → AgentRegistry   │   │
│  │  2. Read session_tracker state (tasks, files)     │   │
│  │  3. Read CORTEX feedback_log (last N entries)     │   │
│  │  4. Compute metrics (success_rate, top_tools)     │   │
│  │  5. Build ExperienceReport                        │   │
│  │  6. store.submit(report)                          │   │
│  │  7. Print summary to terminal                     │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  NEXT SESSION           ▼                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  session_init → role_context → experience_digest  │   │
│  │  CLAUDE.md Generator → predecessor_advice         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Hook Configuration

```json
// settings.json (project-level or user-level)
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": ".venv/bin/python -m src.tools.auto_experience_save"
      }
    ]
  }
}
```

### Report Structure (auto-generated)

```json
{
  "session_id": "auto-20260322-074500-cut-engine",
  "agent_callsign": "Alpha",
  "domain": "engine",
  "branch": "claude/cut-engine",
  "timestamp": "2026-03-22T07:45:00Z",
  "auto_generated": true,

  "tasks_completed": ["tb_001", "tb_002"],
  "files_touched": ["useTimelineInstanceStore.ts", "TimelineTrackView.tsx"],

  "lessons_learned": [],
  "recommendations": [],
  "bugs_found": [],

  "metrics": {
    "commits": 3,
    "tasks_completed": 2,
    "files_read": 15,
    "files_edited": 5,
    "searches": 8,
    "session_duration_seconds": 3600
  },

  "reflex_summary": {
    "total_calls": 42,
    "success_rate": 0.85,
    "top_tools": [
      {"tool": "Read", "calls": 15, "success_rate": 1.0},
      {"tool": "Edit", "calls": 5, "success_rate": 1.0}
    ],
    "failed_tools": [
      {"tool": "vetka_read_file", "calls": 3, "success_rate": 0.0}
    ]
  }
}
```

**Note:** `lessons_learned`, `recommendations`, `bugs_found` остаются пустыми
в auto-mode. Они заполняются только если agent вызвал D5 debrief (Sigma's) или
написал report вручную. Passive signals (metrics, reflex_summary, files_touched)
— самое ценное и они собираются автоматически.

### What Gets Persisted vs What Dies

| Data | Persisted? | How |
|------|-----------|-----|
| Tasks completed | YES | session_tracker → report |
| Files touched | YES | session_tracker → report |
| Tool success rates | YES | CORTEX → report.reflex_summary |
| Failed tools | YES | CORTEX → report.failed_tools |
| Timing | YES | session_tracker → report.metrics |
| Agent's reasoning | NO | Dies with context window |
| Agent's discoveries | ONLY IF debrief triggered | D5 auto-debrief |
| Predecessor advice | ONLY IF manually written | experience report |

---

## Edge Cases

### 1. Session with no task completions
Script still runs → saves empty report with metrics only.
Useful: we see "agent started but did nothing" — could indicate confusion or blocked state.

### 2. Multiple sessions same branch same day
`session_id` includes timestamp → no overwrite. `get_latest_for_role()` returns newest.

### 3. Not in a role-specific branch (main)
Script detects `main` → callsign = "" or "unknown". Still saves report.
Cross-cutting work (like Zeta/Sigma) gets captured too.

### 4. Hook fails (Python error, missing deps)
Hook failure must NOT block terminal exit. Use try/except at top level,
print error to stderr but exit 0.

### 5. Very short session (< 1 min)
Don't save if no meaningful work happened (0 tasks completed AND 0 files edited AND 0 searches).

---

## Constraints

1. **Hook must be fast** — < 2 seconds. No LLM calls, no network requests (except local file writes)
2. **Hook must not block exit** — exit code 0 always, errors to stderr
3. **Zero new dependencies** — uses existing ExperienceReportStore, AgentRegistry, session_tracker
4. **Backward compatible** — if hook not configured, everything works as before
5. **No secrets** — report contains file paths and tool names, not code content

---

*"The best experience report is one the agent never had to write."*
