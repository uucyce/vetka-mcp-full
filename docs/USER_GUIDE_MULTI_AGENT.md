# VETKA Multi-Agent — Инструкция для пользователя
**Версия:** 4.0 | **Дата:** 2026-03-31 (Phase 201 — Opencode Qwen fleet)

---

## Модели: Opus vs Sonnet vs Qwen

Не все роли требуют Opus. Sonnet справляется с 90% задач. Qwen через opencode — бесплатный и быстрый.

| Роль | Модель | Клиент | Почему |
|------|--------|--------|--------|
| **Commander** | **Opus** | Claude Code | Стратегические решения, merge conflicts, координация |
| **Zeta** | **Opus** | Claude Code | Инфра/архитектура, сложный debugging |
| **Alpha** | Sonnet | Claude Code | Endpoints, ops, паттерны — формульная работа |
| **Beta** | Sonnet | Claude Code | FFmpeg pipelines, тесты — техничная но шаблонная |
| **Gamma** | Sonnet | Claude Code | UI компоненты, CSS, wiring — sweet spot Sonnet |
| **Delta** | Sonnet | Claude Code | Верификация, тест-раны — не требует глубокого reasoning |
| **Epsilon** | Sonnet | Claude Code | Contract tests — аналогично Delta |
| **Lambda** | Qwen3.6+ Free | Opencode | QA3 — верификация через opencode |
| **Mu** | Qwen3.6+ Free | Opencode | QA4 — верификация через opencode |
| **Eta** | Sonnet | Claude Code | Инфра-помощник Zeta — шаблонные таски |
| **Theta** | Qwen3.6 Plus Free | **Opencode** | WEATHER Core — profile manager, universal prompt injection |
| **Iota** | Qwen3.6 Plus Free | **Opencode** | WEATHER Mediator — local model bridge, context packing |
| **Kappa** | Qwen3.6 Plus Free | **Opencode** | WEATHER Terminal — xterm.js, CLI agent integration |

**Экономия:** Opus + Sonnet через Claude Code, Qwen через opencode (бесплатно). 2 Opus + 6 Sonnet + 3 Qwen = полный рабочий день без лимитов.

---

## Быстрый старт: 3 команды

```bash
# 1. Запустить агента в worktree (роль загрузится автоматически)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-engine
claude --dangerously-skip-permissions --model sonnet

# 2. Запустить Qwen-агента через opencode (WEATHER роли)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-core
opencode -m opencode/qwen3.6-plus-free

# 3. Посмотреть кто сейчас работает
vetka_task_board action=active_agents
```

---

## Команды запуска

### Claude Code — Sonnet-флот (CUT домен)

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

# Lambda (QA3) — Qwen via Opencode
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa-3 && opencode -m opencode/qwen3.6-plus-free

# Mu (QA4) — Qwen via Opencode
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa-4 && opencode -m opencode/qwen3.6-plus-free

# Eta (Harness 2) — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness-eta && claude --dangerously-skip-permissions --model sonnet

# Zeta (Harness) — Opus
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness && claude --dangerously-skip-permissions

# Commander (Architect) — Opus
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/pedantic-bell && claude --dangerously-skip-permissions
```

### Opencode — Qwen3.6 Plus Free (WEATHER домен)

```bash
# Theta (WEATHER Core) — Qwen
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-core && opencode -m opencode/qwen3.6-plus-free

# Iota (WEATHER Mediator) — Qwen
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-mediator && opencode -m opencode/qwen3.6-plus-free

# Kappa (WEATHER Terminal) — Qwen
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-terminal && opencode -m opencode/qwen3.6-plus-free
```

### Opencode — TUI режим (интерактивный)

```bash
# Просто зайти в worktree и запустить TUI
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-core
opencode
# В TUI: /model opencode/qwen3.6-plus-free
```

---

## Worktrees и роли

**Базовый путь:** `~/Documents/VETKA_Project/vetka_live_03` (далее `$VETKA`)

| Роль | Worktree | Домен | Клиент | Модель | Что делает |
|------|----------|-------|--------|--------|------------|
| **Alpha** | `cut-engine` | Engine | Claude Code | Sonnet | Store, timeline, hotkeys, playback, Tauri |
| **Beta** | `cut-media` | Media | Claude Code | Sonnet | Codecs, color, scopes, render, effects |
| **Gamma** | `cut-ux` | UX | Claude Code | Sonnet | Panels, menus, layout, dockview |
| **Delta** | `cut-qa` | QA | Claude Code | Sonnet | E2E тесты, TDD, FCP7 compliance |
| **Epsilon** | `cut-qa-2` | QA2 | Claude Code | Sonnet | E2E тесты, дополнительная QA capacity |
| **Lambda** | `cut-qa-3` | QA3 | **Opencode** | Qwen3.6+ Free | QA верификация через opencode |
| **Mu** | `cut-qa-4` | QA4 | **Opencode** | Qwen3.6+ Free | QA верификация через opencode |
| **Zeta** | `harness` | Harness | Claude Code | **Opus** | Memory, pipeline, task_board, REFLEX |
| **Eta** | `harness-eta` | Harness | Claude Code | Sonnet | Zeta's partner — infra, tests, recon |
| **Commander** | `pedantic-bell` | Architect | Claude Code | **Opus** | Координация, merge, dispatch |
| **Theta** | `weather-core` | WEATHER | **Opencode** | Qwen3.6+ Free | Profile manager, universal prompt injection |
| **Iota** | `weather-mediator` | WEATHER | **Opencode** | Qwen3.6+ Free | Local model mediator, context packing |
| **Kappa** | `weather-terminal` | WEATHER | **Opencode** | Qwen3.6+ Free | Terminal integration, CLI agents |

---

## Инициализация

Агент получает роль двумя путями (оба работают):
1. **`role=` в session_init** (рекомендуется) — прямая привязка, без угадывания
2. **Автодетекция по worktree** (fallback) — из worktree определяет branch → registry → role

### Первое сообщение (для любого агента)
```
vetka session init
```
Агент загрузит контекст проекта, task board, protocol status.

**Session init по ролям:**
```
mcp__vetka__vetka_session_init role=Alpha     # → Engine context
mcp__vetka__vetka_session_init role=Beta      # → Media context
mcp__vetka__vetka_session_init role=Gamma     # → UX context
mcp__vetka__vetka_session_init role=Delta     # → QA context
mcp__vetka__vetka_session_init role=Epsilon   # → QA2 context
mcp__vetka__vetka_session_init role=Lambda    # → QA3 context (Opencode)
mcp__vetka__vetka_session_init role=Mu        # → QA4 context (Opencode)
mcp__vetka__vetka_session_init role=Zeta      # → Harness context
mcp__vetka__vetka_session_init role=Eta       # → Harness2 context
mcp__vetka__vetka_session_init role=Theta     # → WEATHER Core context
mcp__vetka__vetka_session_init role=Iota      # → WEATHER Mediator context
mcp__vetka__vetka_session_init role=Kappa     # → WEATHER Terminal context
mcp__vetka__vetka_session_init role=Commander # → Architect context
```

`role=` даёт точную привязку к роли без branch detection fallback.

**Что возвращает session_init:**
- `role_context` — callsign, domain, branch, owned_paths, blocked_paths, workflow_hints
- `task_board_summary` — pending/in_progress/done counts + top tasks
- `predecessor_advice` — уроки от предыдущего агента этой роли
- `protocol_status` — checklist (session_init ✓, task_board ?, task claimed ?)

Это **универсальный контракт** — работает одинаково для Claude Code, Opencode, Codex, Cursor, MCC.

### Дать задачу из борда
```
Возьми задачу tb_1774980906_74494_1
```
или
```
Посмотри борд, возьми что-то по своему домену
```

### WEATHER таски (Qwen агенты)

| Task ID | Title | Роль |
|---------|-------|------|
| `tb_1774980906_74494_1` | WEATHER-201.1 Profile Manager | Theta |
| `tb_1774980908_74494_1` | WEATHER-201.2 Universal prompt injection | Theta |
| `tb_1774980913_74494_1` | WEATHER-201.3 TaskBoard UI sidebar | Gamma |
| `tb_1774980916_74494_1` | WEATHER-201.4 Terminal integration | Kappa |
| `tb_1774980919_74494_1` | WEATHER-201.5 Local model mediator | Iota |
| `tb_1774980923_74494_1` | WEATHER-201.6 Integration tests | Delta |

### Запустить Commander (архитектор-капитан)
```
vetka session init
```
Потом:
```
Вот задача: [описание]. Раздели на подзадачи по доменам,
создай таски с ролями (Alpha/Beta/Gamma/Delta) и dispatch.
```

### Попросить merge
```
Замерджь ветку claude/cut-engine в main
```

---

## Workflow patterns

### Простая задача (1 агент, < 30 мин)
```
Запусти нужный worktree → дай задачу → он сделает
```

### Параллельная работа (Claude Code + Opencode)
```
1. Запусти Commander (Claude Code) → "vetka session init" → план
2. Commander создаёт таски с role=
3. Запусти Qwen-агентов (Opencode) в WEATHER worktrees
4. Каждый: "vetka session init" → берёт задачу → работает
5. Когда все закончат → Commander мержит
```

### Dragon (автоматический pipeline)
```
В любом агенте: @dragon <задача>
```

---

## Таблица доменов

| Если задача про... | Роль | Domain |
|---|---|---|
| Store, timeline, playback, hotkeys, Tauri | Alpha | engine |
| Codecs, color, scopes, render, effects, LUT | Beta | media |
| Panels, menus, layout, dockview, workspace | Gamma | ux |
| Тесты, E2E, Playwright, compliance | Delta / Epsilon / Lambda / Mu | qa |
| Docs, merge, координация, архитектура | Commander | architect |
| REFLEX, pipeline, memory, инфра | Zeta / Eta | harness |
| WEATHER: profiles, universal prompt injection | Theta | weather |
| WEATHER: local model mediator, context packing | Iota | weather |
| WEATHER: terminal, CLI agents, xterm.js | Kappa | weather |

---

## Полезные команды

```bash
# Борд
vetka_task_board action=list project_id=CUT filter_status=pending
vetka_task_board action=active_agents
vetka_task_board action=summary

# Git worktrees
git worktree list
git log --oneline agent/theta-weather   # что сделал Theta
git diff main..agent/theta-weather      # что изменилось
```

---

## Где что лежит

| Файл | Назначение |
|---|---|
| `data/templates/agent_registry.yaml` | Роли, домены, owned_paths, blocked_paths |
| `.claude/worktrees/*/CLAUDE.md` | Per-worktree инструкции |
| `data/experience_reports/*.json` | Experience reports от агентов |
| `src/services/agent_registry.py` | Python loader для registry |
| `docs/200_taskboard_forever/ARCHITECTURE_AGENT_ECOSYSTEM.md` | Полная архитектура агентов |
| `docs/201ph_WEATHERE/ARCHITECTURE_WEATHER.md` | WEATHER архитектура |
| `docs/201ph_WEATHERE/RECON_WEATHER_BROWSER_2026-03-31.md` | WEATHER RECON |

---

## Типичный день с 11 агентами

```
Утро:
  1. Запусти Commander (Claude Code) → "vetka session init" → покажи борд
  2. Commander создаёт план на день, dispatch задачи с role=

Работа:
  3. CUT-агенты (Claude Code): Alpha, Beta, Gamma, Delta в своих worktrees
  4. WEATHER-агенты (Opencode): Theta, Iota, Kappa в своих worktrees
  5. Каждый: "vetka session init" → берёт задачу → работает
  6. Ты переключаешься между терминалами, отвечаешь на вопросы

Merge:
  7. Commander → "замерджь через task_board merge_request"
  8. Post-merge hook: digest + task promote

Вечер:
  9. Debrief Q1-Q3 при закрытии тасков → автоматически в CORTEX + ENGRAM
  10. STM snapshot сохраняется → следующая сессия начнёт с памятью
```

---

*"Каждый агент знает свою роль. Тебе нужно только сказать — что делать."*
