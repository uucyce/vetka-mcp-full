# VETKA Multi-Agent — Инструкция для пользователя
**Версия:** 3.0 | **Дата:** 2026-03-29 (Phase 200 — Sonnet fleet update)

---

## Модели: Opus vs Sonnet

Не все роли требуют Opus. Sonnet справляется с 90% задач и его лимит практически неисчерпаем.

| Роль | Модель | Почему |
|------|--------|--------|
| **Commander** | **Opus** | Стратегические решения, merge conflicts, координация |
| **Zeta** | **Opus** | Инфра/архитектура, сложный debugging |
| **Alpha** | Sonnet | Endpoints, ops, паттерны — формульная работа |
| **Beta** | Sonnet | FFmpeg pipelines, тесты — техничная но шаблонная |
| **Gamma** | Sonnet | UI компоненты, CSS, wiring — sweet spot Sonnet |
| **Delta** | Sonnet | Верификация, тест-раны — не требует глубокого reasoning |
| **Epsilon** | Sonnet | Contract tests — аналогично Delta |
| **Eta** | Sonnet | Инфра-помощник Zeta — шаблонные таски |

**Экономия:** ~3x по Opus лимиту. 7 Opus агентов выжигают лимит за 2-3 часа. 2 Opus + 6 Sonnet — хватает на полный рабочий день.

---

## Быстрый старт: 3 команды

```bash
# 1. Запустить агента в worktree (роль загрузится автоматически)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-engine
claude --dangerously-skip-permissions --model sonnet

# 2. Перегенерировать CLAUDE.md для всех ролей (после merge/experience reports)
cd ~/Documents/VETKA_Project/vetka_live_03
.venv/bin/python -m src.tools.generate_claude_md --all

# 3. Посмотреть кто сейчас работает
# (в любом агенте)
vetka_task_board action=active_agents
```

---

## Команды запуска

### Sonnet-флот (рекомендуемый — экономит Opus лимит)

```bash
# Alpha (Engine) — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-engine && claude --dangerously-skip-permissions --model sonnet

# Beta (Media) — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-media && claude --dangerously-skip-permissions --model sonnet

# Gamma (UX) — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-ux && claude --dangerously-skip-permissions --model sonnet

# Delta (QA) — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa && claude --dangerously-skip-permissions --model sonnet

# Epsilon (QA2) — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa-2 && claude --dangerously-skip-permissions --model sonnet

# Eta (Harness 2) — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness-eta && claude --dangerously-skip-permissions --model sonnet

# Zeta (Harness) — Opus (нужен для инфра-решений)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness && claude --dangerously-skip-permissions

# Commander (Architect) — Opus (координация, merge)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/pedantic-bell && claude --dangerously-skip-permissions
```

### Полный Opus-флот (когда лимиты не проблема)

```bash
# Alpha (Engine)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-engine && claude --dangerously-skip-permissions

# Beta (Media)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-media && claude --dangerously-skip-permissions

# Gamma (UX)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-ux && claude --dangerously-skip-permissions

# Delta (QA)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa && claude --dangerously-skip-permissions

# Epsilon (QA2)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa-2 && claude --dangerously-skip-permissions

# Zeta (Harness)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness && claude --dangerously-skip-permissions

# Eta (Harness 2)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness-eta && claude --dangerously-skip-permissions

# Commander (Architect)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/pedantic-bell && claude --dangerously-skip-permissions
```

---

## Worktrees и роли

**Базовый путь:** `~/Documents/VETKA_Project/vetka_live_03` (далее `$VETKA`)

| Роль | Worktree | Домен | Модель | Что делает |
|------|----------|-------|--------|------------|
| **Alpha** | `cut-engine` | Engine | Sonnet | Store, timeline, hotkeys, playback, Tauri |
| **Beta** | `cut-media` | Media | Sonnet | Codecs, color, scopes, render, effects |
| **Gamma** | `cut-ux` | UX | Sonnet | Panels, menus, layout, dockview |
| **Delta** | `cut-qa` | QA | Sonnet | E2E тесты, TDD, FCP7 compliance |
| **Epsilon** | `cut-qa-2` | QA2 | Sonnet | E2E тесты, дополнительная QA capacity |
| **Zeta** | `harness` | Harness | **Opus** | Memory, pipeline, task_board, REFLEX |
| **Eta** | `harness-eta` | Harness | Sonnet | Zeta's partner — infra, tests, recon |
| **Commander** | `pedantic-bell` | Architect | **Opus** | Координация, merge, dispatch |






Агент получает роль двумя путями (оба работают):
1. **`role=` в session_init** (рекомендуется) — прямая привязка, без угадывания
2. **Автодетекция по worktree** (fallback) — из `.claude/worktrees/<name>/` определяет branch → registry → role

**CLAUDE.md теперь тонкий маршрутизатор** (~10 строк, Phase 197): только identity + ссылка на session_init.
Все данные (owned_paths, predecessor advice, key docs) приходят динамически через `session_init → role_context`.

---

## Что говорить агенту

### Первое сообщение (для любого агента)
```
vetka session init
```
Агент загрузит контекст проекта, task board, protocol status.

**Session init по ролям** (Phase 198 — рекомендуемый способ):
```
# Агент сам передаёт role= при инициализации:
mcp__vetka__vetka_session_init role=Alpha    # → Engine context
mcp__vetka__vetka_session_init role=Beta     # → Media context
mcp__vetka__vetka_session_init role=Gamma    # → UX context
mcp__vetka__vetka_session_init role=Delta    # → QA context
mcp__vetka__vetka_session_init role=Zeta     # → Harness context
mcp__vetka__vetka_session_init role=Eta      # → Harness2 context
mcp__vetka__vetka_session_init role=Commander # → Architect context
```

`role=` даёт точную привязку к роли без branch detection fallback.
Если `role=` не указан — система определит роль по worktree branch (старый путь, работает).

**Что возвращает session_init:**
- `role_context` — callsign, domain, branch, owned_paths, blocked_paths, workflow_hints
- `task_board_summary` — pending/in_progress/done counts + top tasks
- `predecessor_advice` — уроки от предыдущего агента этой роли
- `engram_learnings` — hot patterns из ENGRAM L1 (danger, architecture)
- `reflex_recommendations` — top-3 tool recommendations
- `protocol_status` — checklist (session_init ✓, task_board ?, task claimed ?)

Это **универсальный контракт** — работает одинаково для Claude Code, Codex, Gemini, Cursor, MCC.

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
| REFLEX, pipeline, memory, инфра | Zeta / Eta | harness |

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
  1. Запусти Commander → "vetka session init" → покажи борд
  2. Commander создаёт план на день, dispatch задачи с role=

Работа:
  3. Открой 4-5 терминалов → запусти агентов в worktrees
  4. Каждый: "vetka session init" → берёт задачу → работает
  5. Ты переключаешься между терминалами, отвечаешь на вопросы
  6. Делегируй рутину Sonnet-агентам (98% лимита не используется!)

Merge:
  7. Commander → "замерджь Alpha через task_board merge_request"
  8. Post-merge hook автоматически: digest + CLAUDE.md regen + task promote

Вечер:
  9. Debrief Q1-Q3 при закрытии тасков → автоматически в CORTEX + ENGRAM
  10. STM snapshot сохраняется → следующая сессия начнёт с памятью
```

**Phase 198 improvements:**
- CLAUDE.md regen автоматический (post-merge hook), не надо вручную
- Debrief → память: прямой pipeline, без .md файлов
- Sonnet-агенты: 23 агента = 4% лимита. Используй их для рекона и простых фиксов
- Token efficiency: session_init -55%, CLAUDE.md -93%, task claim -87%

---

*"Каждый агент знает свою роль. Тебе нужно только сказать — что делать."*
