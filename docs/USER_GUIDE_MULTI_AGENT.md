# VETKA Multi-Agent — Инструкция для пользователя
**Версия:** 1.0 | **Дата:** 2026-03-22

---

## Быстрый старт: 3 команды

```bash
# 1. Запустить агента в worktree (роль загрузится автоматически)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-engine
claude

# 2. Перегенерировать CLAUDE.md для всех ролей (после merge/experience reports)
cd ~/Documents/VETKA_Project/vetka_live_03
.venv/bin/python -m src.tools.generate_claude_md --all

# 3. Посмотреть кто сейчас работает
# (в любом агенте)
vetka_task_board action=active_agents
```

---

## Worktrees и роли

| Команда терминала | Роль | Домен | Что делает |
|---|---|---|---|
| `cd .claude/worktrees/cut-engine && claude` | **Alpha** | Engine | Store, timeline, hotkeys, playback, Tauri |
| `cd .claude/worktrees/cut-media && claude` | **Beta** | Media | Codecs, color, scopes, render, effects |
| `cd .claude/worktrees/cut-ux && claude` | **Gamma** | UX | Panels, menus, layout, dockview |
| `cd .claude/worktrees/cut-qa && claude` | **Delta** | QA | E2E тесты, TDD, FCP7 compliance |
| `cd .claude/worktrees/pedantic-bell && claude` | **Commander** | Architect | Координация, merge, dispatch |
| `cd ~/Documents/VETKA_Project/vetka_live_03 && claude` | **Sigma/Zeta/...** | Cross-cutting | Инфра, REFLEX, pipeline |

Агент **автоматически** получает роль из `.claude/worktrees/<name>/CLAUDE.md`.
Ничего передавать не нужно — он уже знает свои файлы, ограничения и predecessor advice.

---

## Что говорить агенту

### Первое сообщение (для любого агента)
```
vetka session init
```
Агент загрузит контекст проекта, task board, protocol status.

### Дать задачу из борда
```
Возьми задачу tb_1774153652_5
```
или
```
Посмотри борд, возьми что-то по своему домену
```

### Запустить Commander (архитектор-капитан)
```
vetka session init
```
Потом:
```
Вот задача: [описание]. Раздели на подзадачи по доменам,
создай таски с ролями (Alpha/Beta/Gamma/Delta) и dispatch.
```

### Попросить Commander сделать master plan
```
Нужно сделать [большая фича/рефакторинг]. Сделай мастер-план:
- Разбей на sous-chefs (параллельные агенты)
- Определи зависимости между волнами
- Создай таски на борде
```

### Попросить merge
```
Замерджь ветку claude/cut-engine в main
```
Commander знает merge ritual (pre-check → merge → vite build → promote).

### Обновить CLAUDE.md после сессии
```
Перегенерируй CLAUDE.md для всех ролей
```
или вручную:
```bash
.venv/bin/python -m src.tools.generate_claude_md --all
```

---

## Workflow patterns — когда что использовать

### Простая задача (1 агент, < 30 мин)
```
Запусти нужный worktree → дай задачу → он сделает
```
Пример: "Почини баг в timeline playback" → запускаешь Alpha.

### Параллельная работа (4-5 агентов)
```
1. Запусти Commander (main или pedantic-bell)
2. "Вот фича X. Раздели на домены, создай таски, dispatch"
3. Commander создаёт таски с role=Alpha/Beta/Gamma/Delta
4. Открой 4 терминала, запусти агентов в worktrees
5. Каждый скажет "vetka session init" → увидит свои таски → возьмёт
6. Когда все закончат → Commander мержит
```

### Dragon (автоматический pipeline)
```
В любом агенте: @dragon <задача>
```
Dragon сам выберет тир (Bronze/Silver/Gold) и прогонит через
scout → architect → researcher → coder → verifier.

### Sous-Chef pattern (cross-cutting инфра)
```
Commander на main:
"Сделай мастер-план для REFLEX Emotions.
Волна 1: SC-A (core) + SC-B (тесты) параллельно.
Волна 2: SC-C (wiring) после SC-A."
```
Commander запускает sous-chefs как background agents в изолированных worktrees.

---

## Роли при создании задач

Когда **ты сам** создаёшь задачу или просишь Commander:

### CUT-доменная задача → указывай роль
```
Создай задачу: "Fix timeline playback stutter"
  role=Alpha domain=engine
  allowed_paths=["client/src/store/useTimelineInstanceStore.ts"]
```

### Cross-cutting задача → без роли
```
Создай задачу: "Add REFLEX Emotions core"
  project_id=vetka
  (role и domain пустые — любой агент может взять)
```

### Не знаешь какая роль → оставь пустой
```
Создай задачу: "Improve color rendering"
  (агент сам определит роль при claim через registry)
```

### Таблица доменов
| Если задача про... | Роль | Domain |
|---|---|---|
| Store, timeline, playback, hotkeys, Tauri | Alpha | engine |
| Codecs, color, scopes, render, effects, LUT | Beta | media |
| Panels, menus, layout, dockview, workspace | Gamma | ux |
| Тесты, E2E, Playwright, compliance | Delta | qa |
| Docs, merge, координация, архитектура | Commander | architect |
| REFLEX, pipeline, memory, инфра | (пусто) | (пусто) |

---

## Полезные команды для агентов

```
# Борд
vetka_task_board action=list project_id=CUT filter_status=pending
vetka_task_board action=active_agents
vetka_task_board action=summary

# Генератор CLAUDE.md
.venv/bin/python -m src.tools.generate_claude_md --all           # все роли
.venv/bin/python -m src.tools.generate_claude_md --role Alpha    # одна роль
.venv/bin/python -m src.tools.generate_claude_md --role Alpha --dry-run  # preview

# Git worktrees
git worktree list                    # кто где
git log --oneline claude/cut-engine  # что сделал Alpha
git diff main..claude/cut-engine     # что изменилось
```

---

## Где что лежит

| Файл | Назначение |
|---|---|
| `data/templates/agent_registry.yaml` | Роли, домены, owned_paths, blocked_paths |
| `data/templates/claude_md_template.j2` | Шаблон CLAUDE.md для генератора |
| `.claude/worktrees/*/CLAUDE.md` | Per-worktree инструкции (auto-generated) |
| `data/experience_reports/*.json` | Experience reports от агентов |
| `src/services/agent_registry.py` | Python loader для registry |
| `src/services/experience_report.py` | ExperienceReportStore |
| `src/tools/generate_claude_md.py` | Генератор CLAUDE.md |
| `docs/192_task_SQLite/ARCHITECTURE_ZETA_AGENT_INIT_SYSTEM.md` | Архитектура системы |

---

## Типичный день с 6 агентами

```
Утро:
  1. .venv/bin/python -m src.tools.generate_claude_md --all
  2. Запусти Commander → "vetka session init, покажи борд"
  3. Commander создаёт план на день, dispatch задачи

Работа:
  4. Открой 4-5 терминалов → запусти агентов в worktrees
  5. Каждый: "vetka session init" → берёт задачу → работает
  6. Ты переключаешься между терминалами, отвечаешь на вопросы

Merge:
  7. Commander → "замерджь Alpha" → merge ritual → promote
  8. Повтори для Beta/Gamma/Delta

Вечер:
  9. Protocol Guard напомнит агентам написать experience report
  10. Перегенерируй CLAUDE.md → свежий predecessor advice на завтра
```

---

*"Каждый агент знает свою роль. Тебе нужно только сказать — что делать."*
