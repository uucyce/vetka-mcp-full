# VETKA Multi-Agent — Инструкция для пользователя
**Версия:** 7.1 | **Дата:** 2026-04-07 (Phase 210 — Gemma Fleet operational: 19 ролей, worktrees созданы, CLAUDE.md regenerated)

---

## Модели: Opus vs Sonnet vs Haiku vs Qwen

Три уровня Claude + бесплатный Qwen. Haiku 4.5 = 3x дешевле Sonnet, быстрее output. Для шаблонных задач (import fix, SVG, pytest) — Haiku хватает с запасом.

| Роль | Модель | Клиент | Почему |
|------|--------|--------|--------|
| **Commander** | **Opus** | Claude Code | Стратегические решения, merge conflicts, координация |
| **Polaris** | Qwen3.6+ Free | **Opencode** | Капитан — координация opencode флота, WEATHER dispatch |
| **Zeta** | **Opus** | Claude Code | Инфра/архитектура, сложный debugging |
| **Alpha** | **Sonnet** | Claude Code | Единственный Sonnet — сложные engine фиксы, архитектурные решения |
| **Beta** | **Haiku** | Claude Code | FFmpeg pipelines, imports, шаблонные фиксы |
| **Gamma** | **Haiku** | Claude Code | UI wiring, SVG иконки, CSS — быстро и дёшево |
| **Delta** | **Haiku** | Claude Code | QA по чеклисту, pytest раны, code review |
| **Epsilon** | **Haiku** | Claude Code | Contract tests, верификация — аналогично Delta |
| **Lambda** | Qwen3.6+ Free | Opencode | QA3 — верификация через opencode |
| **Mu** | Qwen3.6+ Free | Opencode | QA4 — верификация через opencode |
| **Eta** | Sonnet | Claude Code | Инфра-помощник Zeta — шаблонные таски |
| **Theta** | Qwen3.6 Plus Free | **Opencode** | WEATHER Core — profile manager, universal prompt injection |
| **Iota** | Qwen3.6 Plus Free | **Opencode** | WEATHER Mediator — local model bridge, context packing |
| **Kappa** | Qwen3.6 Plus Free | **Opencode** | WEATHER Terminal — xterm.js, CLI agent integration |
| **Nu** | Mistral Vibe | **Vibe CLI** | Research Agent — free tier, recon + web research |
| **Mistral-1** | Mistral Vibe | **Vibe CLI** | WEATHER Agent 1 — free tier, 10-15 tasks/day |
| **Mistral-2** | Mistral Vibe | **Vibe CLI** | QA Agent 5 — free tier, 10-15 tasks/day |
| **Mistral-3** | Mistral Vibe | **Vibe CLI** | WEATHER Agent 2 — free tier, 10-15 tasks/day |
| **Codex** | GPT-4o | **Codex CLI** | Parallax & Multimedia Engineer — photo_parallax_playground |
| **Omicron** | gemma4:e4b (free) | **free-code** | Gemma Engine — engine-class задачи на локальной модели |
| **Pi** | gemma4:e2b (free) | **free-code** | Gemma Scout — автоматический recon, лёгкие задачи |
| **Rho** | gemma4:26b (free) | **free-code** | Gemma Sherpa — vision, web browsing, поддержка Sherpa |
| **Sigma** | gemma4:e4b (free) | **free-code** | Gemma QA — верификация, тесты через Gemma |

**Экономия:** 2 Opus + 1 Sonnet + 4 Haiku + 1 Sonnet (Eta) + 5 Qwen + 3 Mistral Vibe + 4 Gemma (free, локально) = максимальная пропускная способность.

---

## Быстрый старт: 3 команды

```bash
# 1. Запустить Claude Code агента (модель читается автоматически из agent_registry.yaml)
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Alpha cut-engine claude_code

# 1b. Запустить Gemma агента (Ollama, бесплатно — нужен LiteLLM + bridge, см. ниже)
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Omicron gemma-engine free_code

# 2. Запустить Qwen-агента через opencode (WEATHER роли) — с ролью для сигналов
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-core
VETKA_AGENT_ROLE=Theta opencode -m opencode/qwen3.6-plus-free

# 3. Посмотреть кто сейчас работает
vetka_task_board action=active_agents
```

---

## Команды запуска

### Claude Code — CUT домен (spawn_synapse.sh)

`spawn_synapse.sh` читает `model_tier` из `data/templates/agent_registry.yaml` автоматически — модель указывать не нужно.

```bash
# Alpha (Engine) — Sonnet
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Alpha cut-engine claude_code

# Beta (Media) — Haiku
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Beta cut-media claude_code

# Gamma (UX) — Haiku
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Gamma cut-ux claude_code

# Delta (QA) — Haiku
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Delta cut-qa claude_code

# Epsilon (QA2) — Haiku
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Epsilon cut-qa-2 claude_code

# Lambda (QA3) — Qwen via Opencode
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa-3 && opencode -m opencode/qwen3.6-plus-free

# Mu (QA4) — Qwen via Opencode
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa-4 && opencode -m opencode/qwen3.6-plus-free

# Eta (Harness 2) — Sonnet
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Eta harness-eta claude_code

# Zeta (Harness) — Opus
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Zeta harness claude_code

# Commander (Architect) — Opus
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Commander pedantic-bell claude_code
```

#### Fallback: ручной запуск (если spawn_synapse.sh недоступен)

```bash
# Alpha — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-engine && claude --dangerously-skip-permissions --model sonnet
# Beta — Haiku
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-media && claude --dangerously-skip-permissions --model haiku
# Gamma — Haiku
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-ux && claude --dangerously-skip-permissions --model haiku
# Delta — Haiku
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa && claude --dangerously-skip-permissions --model haiku
# Epsilon — Haiku
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa-2 && claude --dangerously-skip-permissions --model haiku
# Eta — Sonnet
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness-eta && claude --dangerously-skip-permissions --model sonnet
# Zeta — Opus
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/harness && claude --dangerously-skip-permissions
# Commander — Opus
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/pedantic-bell && claude --dangerously-skip-permissions
```

> **Когда повышать Haiku до Sonnet:** Если агент не справляется с задачей (3+ попытки, ошибки reasoning), временно повысьте через fallback-команду с `--model sonnet`. После задачи верните обратно.

### Opencode — Qwen3.6 Plus Free (WEATHER домен)

```bash
# Polaris (Captain) — Qwen via Opencode
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/captain && opencode -m opencode/qwen3.6-plus-free

# Theta (WEATHER Core) — Qwen
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-core && opencode -m opencode/qwen3.6-plus-free

# Iota (WEATHER Mediator) — Qwen
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-mediator && opencode -m opencode/qwen3.6-plus-free

# Kappa (WEATHER Terminal) — Qwen
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-terminal && opencode -m opencode/qwen3.6-plus-free
```

### Mistral Vibe CLI — Free Tier (WEATHER + QA)

```bash
# Mistral-1 (WEATHER Agent 1) — Free
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-mistral-1 && vibe

# Mistral-2 (QA Agent 5) — Free
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-qa-5 && vibe

# Mistral-3 (WEATHER Agent 2) — Free
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-mistral-2 && vibe
```

> **Mistral Vibe CLI:** Установить: `npm install -g @mistralai/vibe-cli` или `pip install mistral-vibe-cli`. Бесплатный лимит: ~10-15 задач/день на аккаунт.
> **Первое сообщение:** `vetka_session_init role=Mistral-1` (или Mistral-2, Mistral-3)

### Codex CLI — Parallax домен

```bash
# Codex (Parallax & Multimedia) — GPT-4o
cd ~/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex
codex
# Первое сообщение: vetka session init role=Codex
```

> **Важно:** Codex должен открываться из `photo_parallax_playground_codex` (git worktree), а НЕ из `photo_parallax_playground` (подпапка main). В подпапке main ветка `codex/parallax` недоступна — git блокирует checkout ветки, занятой другим worktree.

### Быстрое создание новой роли

Если нужен новый агент, не создавайте вручную — используйте скрипт:

```bash
scripts/release/add_role.sh --callsign NAME --domain DOMAIN --worktree WORKTREE \
  --tool-type TYPE --model-tier MODEL --role-title "TITLE"
```

Скрипт автоматически: добавит в registry, создаст branch+worktree, сгенерирует CLAUDE.md и AGENTS.md, обновит USER_GUIDE.

Подробнее: `docs/200_taskboard_forever/GUIDE_ROLE_INIT_AND_CREATION.md`

### Gemma Fleet — free_code (Ollama + LiteLLM + Bridge)

Gemma агенты работают локально через Ollama — бесплатно, без лимитов API. Требуют запущенных LiteLLM + bridge процессов.

#### Предварительно: запустить LiteLLM + bridge (один раз перед флотом)

```bash
# Terminal 1: LiteLLM proxy (переводит Anthropic→OpenAI→Ollama)
LITELLM_MASTER_KEY=sk-ollama /tmp/litellm_venv/bin/litellm \
  --model ollama/gemma4:e4b --port 4000 --drop_params

# Terminal 2: Gemma Bridge (XML tool call converter, порт 4001)
python3 ~/Documents/VETKA_Project/vetka_live_03/scripts/litellm_gemma_bridge.py --port 4001

# Проверка работы (ожидать: {"status": "ok"})
curl http://localhost:4001/health
```

> **Установка LiteLLM (один раз):**
> ```bash
> python3 -m venv /tmp/litellm_venv && /tmp/litellm_venv/bin/pip install litellm
> ```
> **Ollama модели (один раз):**
> ```bash
> ollama pull gemma4:e4b   # 4B параметров — основной
> ollama pull gemma4:e2b   # 2B параметров — быстрый scout
> ollama pull gemma4:26b   # 26B параметров — vision/sherpa
> ```

#### Запуск Gemma Fleet

```bash
# Omicron (Engine) — gemma4:e4b — engine-class задачи
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Omicron gemma-engine free_code

# Pi (Scout) — gemma4:e2b — автоматический recon, лёгкие задачи
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Pi gemma-scout free_code

# Rho (Sherpa) — gemma4:26b — vision, web browsing
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Rho gemma-sherpa free_code

# Sigma (QA) — gemma4:e4b — верификация, тесты
~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh Sigma gemma-qa free_code
```

> **Переменные окружения (опционально):**
> ```bash
> export GEMMA_BRIDGE_URL=http://localhost:4001   # default
> export FREE_CODE_BIN=~/Documents/VETKA_Project/free-code/cli-dev  # default
> ```
>
> **Worktrees уже созданы** (gemma-engine/scout/sherpa/qa готовы к запуску).

#### Fallback: ручной запуск Gemma агента

```bash
# Gemma — ручной запуск через free-code напрямую
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/gemma-engine
ANTHROPIC_BASE_URL=http://localhost:4001 ANTHROPIC_API_KEY=sk-ollama \
  ~/Documents/VETKA_Project/free-code/cli-dev \
  --dangerously-skip-permissions --model gemma4:e4b
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
| **Alpha** | `cut-engine` | Engine | Claude Code | **Sonnet** | Store, timeline, hotkeys, playback, Tauri |
| **Beta** | `cut-media` | Media | Claude Code | **Haiku** | Codecs, color, scopes, render, effects |
| **Gamma** | `cut-ux` | UX | Claude Code | **Haiku** | Panels, menus, layout, dockview |
| **Delta** | `cut-qa` | QA | Claude Code | **Haiku** | E2E тесты, TDD, FCP7 compliance |
| **Epsilon** | `cut-qa-2` | QA2 | Claude Code | **Haiku** | E2E тесты, дополнительная QA capacity |
| **Lambda** | `cut-qa-3` | QA3 | **Opencode** | Qwen3.6+ Free | QA верификация через opencode |
| **Mu** | `cut-qa-4` | QA4 | **Opencode** | Qwen3.6+ Free | QA верификация через opencode |
| **Zeta** | `harness` | Harness | Claude Code | **Opus** | Memory, pipeline, task_board, REFLEX |
| **Eta** | `harness-eta` | Harness | Claude Code | Sonnet | Zeta's partner — infra, tests, recon |
| **Commander** | `pedantic-bell` | Architect | Claude Code | **Opus** | Координация, merge, dispatch |
| **Polaris** | `captain` | Architect | **Opencode** | Qwen3.6+ Free | Капитан — координация, WEATHER dispatch |
| **Theta** | `weather-core` | WEATHER | **Opencode** | Qwen3.6+ Free | Profile manager, universal prompt injection |
| **Iota** | `weather-mediator` | WEATHER | **Opencode** | Qwen3.6+ Free | Local model mediator, context packing |
| **Kappa** | `weather-terminal` | WEATHER | **Opencode** | Qwen3.6+ Free | Terminal integration, CLI agents |
| **Nu** | `polaris-nu` | Research | **Vibe CLI** | Mistral Vibe | Research Agent — recon, web research, free tier |
| **Mistral-1** | `weather-mistral-1` | WEATHER | **Vibe CLI** | Mistral Vibe | WEATHER Agent 1 — free tier |
| **Mistral-2** | `cut-qa-5` | QA5 | **Vibe CLI** | Mistral Vibe | QA Agent 5 — free tier |
| **Mistral-3** | `weather-mistral-2` | WEATHER | **Vibe CLI** | Mistral Vibe | WEATHER Agent 2 — free tier |
| **Omicron** | `gemma-engine` | Gemma | **free-code** | gemma4:e4b (free) | Engine-class задачи на Gemma |
| **Pi** | `gemma-scout` | Gemma | **free-code** | gemma4:e2b (free) | Auto-recon scout, лёгкие задачи |
| **Rho** | `gemma-sherpa` | Gemma | **free-code** | gemma4:26b (free) | Vision, web, поддержка Sherpa |
| **Sigma** | `gemma-qa` | Gemma | **free-code** | gemma4:e4b (free) | QA верификация через Gemma |

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
mcp__vetka__vetka_session_init role=Polaris   # → Captain context (Opencode)
mcp__vetka__vetka_session_init role=Theta     # → WEATHER Core context
mcp__vetka__vetka_session_init role=Iota      # → WEATHER Mediator context
mcp__vetka__vetka_session_init role=Kappa     # → WEATHER Terminal context
mcp__vetka__vetka_session_init role=Mistral-1 # → WEATHER Agent 1 (Vibe CLI)
mcp__vetka__vetka_session_init role=Mistral-2 # → QA Agent 5 (Vibe CLI)
mcp__vetka__vetka_session_init role=Nu        # → Research Agent (Vibe CLI)
mcp__vetka__vetka_session_init role=Mistral-3 # → WEATHER Agent 2 (Vibe CLI)
mcp__vetka__vetka_session_init role=Omicron   # → Gemma engine context (free-code)
mcp__vetka__vetka_session_init role=Pi        # → Gemma scout context (free-code)
mcp__vetka__vetka_session_init role=Rho       # → Gemma sherpa context (free-code)
mcp__vetka__vetka_session_init role=Sigma     # → Gemma QA context (free-code)
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

## Signal Delivery — Уведомления в реальном времени

**Phase 204 (2026-04-04).** Commander отправляет `action=notify` → агент видит сообщение при следующем tool call. Без ручного обхода терминалов.

### Как работает

```
Commander: vetka_task_board action=notify target_role=Alpha message="..."
               ↓
         SQLite notifications + ~/.claude/signals/Alpha.json
               ↓
         PreToolUse hook (check_notifications.sh) — срабатывает перед любым tool call
               ↓
         Агент видит сообщение в разговоре → действует
```

**Signal file format** (`~/.claude/signals/{ROLE}.json`):
```json
[
  {"id": "notif_xxx", "from": "Commander", "message": "...", "ts": "ISO", "ntype": "custom"}
]
```

Файл читается атомарно и удаляется после прочтения (one-shot delivery).

### Настройка (один раз)

**Шаг 1:** Убедиться что hooks установлены во всех worktrees:
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
bash scripts/install_notification_hooks.sh
```

Ожидаемый результат:
```
[OK]   Alpha (cut-engine): PreToolUse hook installed
[OK]   Beta (cut-media): PreToolUse hook installed
...
[OK]   Eta (harness-eta): PreToolUse hook installed
Done: 7 installed, 0 skipped, 0 errors
```

Команда идемпотентна — повторный запуск ничего не сломает.

**Шаг 2:** Запустить UDS Daemon (автоматическая публикация событий):
```bash
bash scripts/start_uds_daemon.sh
```

Для macOS автостарт через launchd:
```bash
# Daemon стартует автоматически при входе в систему
launchctl load ~/Library/LaunchAgents/com.vetka.uds-daemon.plist
```

**Шаг 3:** Проверить что директория сигналов существует:
```bash
ls ~/.claude/signals/   # создаётся автоматически install_notification_hooks.sh
```

### Обновлённый workflow Commander

**Было (до Phase 204):**
1. Commander: `action=notify target_role=Alpha message="Готово, замерджи"`
2. Пользователь: переключается в терминал Alpha, пишет "проверь уведомления"
3. Alpha: `action=notifications` → читает → действует

**Стало (Phase 204+):**
1. Commander: `action=notify target_role=Alpha message="Готово, замерджи"`
2. Alpha: видит сообщение автоматически при следующем tool call

Больше не нужно вручную обходить 5-8 терминалов.

### Дополнительные сигналы

Кроме `action=notify` агент всё равно может проверить вручную:
```
vetka_task_board action=notifications role=Alpha
vetka_task_board action=ack_notifications role=Alpha
```

### Troubleshooting

**Агент не видит уведомления:**
```bash
# Проверить что hook установлен
cat .claude/settings.json | python3 -m json.tool | grep -A3 PreToolUse

# Проверить что signal file создаётся после notify
ls -la ~/.claude/signals/

# Запустить hook вручную для теста
bash scripts/check_notifications.sh Alpha
```

**Signal file не удаляется:**
```bash
# Временный файл застрял (race condition при параллельных запусках)
ls ~/.claude/signals/*.tmp 2>/dev/null
rm -f ~/.claude/signals/*.tmp
```

**Hook слишком медленный (>1сек):**
- `stat` на несуществующий файл: <1ms
- Чтение + python3 parse при наличии сигнала: ~30ms
- Если <1ms нужно абсолютно: заменить python3 на `jq` (если установлен)

### Opencode-агенты (Phase 205 prep)

Для Qwen/Opencode агентов (Lambda, Mu, Polaris, Theta, Iota, Kappa) используется universal signal dir:

```bash
# Запуск Opencode с переменной роли
VETKA_AGENT_ROLE=Lambda opencode -m opencode/qwen3.6-plus-free

# Wrapper check_opencode_signals.sh проверяет обе директории:
# 1. ~/.vetka/signals/{ROLE}.json  (universal, Opencode)
# 2. ~/.claude/signals/{ROLE}.json (Claude Code fallback)
```

Настройка через `PRETOOL_HOOK` (Opencode env hook):
```bash
export PRETOOL_HOOK="bash scripts/check_opencode_signals.sh"
export VETKA_AGENT_ROLE=Lambda
opencode -m opencode/qwen3.6-plus-free
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
| Engine/compute задачи на Gemma (бесплатно) | Omicron | gemma |
| Лёгкий recon, автосбор данных (бесплатно) | Pi | gemma |
| Vision, web browsing, Sherpa-support (бесплатно) | Rho | gemma |
| QA-верификация через Gemma (бесплатно) | Sigma | gemma |

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
| `data/templates/agent_registry.yaml` | Роли, домены, owned_paths, blocked_paths, model_tier |
| `~/Documents/VETKA_Project/vetka_live_03/scripts/spawn_synapse.sh` | Универсальный лаунчер — читает model_tier из registry |
| `.claude/worktrees/*/CLAUDE.md` | Per-worktree инструкции |
| `data/experience_reports/*.json` | Experience reports от агентов |
| `src/services/agent_registry.py` | Python loader для registry |
| `docs/200_taskboard_forever/ARCHITECTURE_AGENT_ECOSYSTEM.md` | Полная архитектура агентов |
| `docs/201ph_WEATHERE/ARCHITECTURE_WEATHER.md` | WEATHER архитектура |
| `docs/201ph_WEATHERE/RECON_WEATHER_BROWSER_2026-03-31.md` | WEATHER RECON |
| `docs/202ph_SHERPA/ARCHITECTURE_SHERPA.md` | Sherpa архитектура и roadmap |

---

## Типичный день с 15 агентами

```
Утро:
  1. Запусти Commander (Opus) → "vetka session init" → покажи борд
  2. Commander создаёт план на день, dispatch задачи с role=

Работа (CUT — Claude Code):
  3. Alpha (Sonnet) — сложные engine фиксы
  4. Beta, Gamma (Haiku) — шаблонные фиксы, wiring, SVG
  5. Delta, Epsilon (Haiku) — QA по чеклисту, pytest

Работа (WEATHER — Opencode/Qwen):
  6. Theta, Iota, Kappa — WEATHER core/mediator/terminal
  7. Lambda, Mu — QA верификация

Работа (Инфра):
  8. Zeta (Opus), Eta (Sonnet) — harness, memory, pipeline
  9. Polaris (Qwen) — координация opencode флота

Работа (Gemma Fleet — бесплатно, параллельно):
  10. Omicron (gemma4:e4b) — engine задачи через Ollama
  11. Pi (gemma4:e2b) — авто-recon, лёгкий сбор данных
  12. Rho (gemma4:26b) — vision/web задачи, поддержка Sherpa
  13. Sigma (gemma4:e4b) — QA верификация

Merge:
  10. Commander → "замерджь через task_board merge_request"
  11. Post-merge hook: digest + task promote

Вечер:
  12. Debrief Q1-Q3 при закрытии тасков → автоматически в CORTEX + ENGRAM
  13. STM snapshot сохраняется → следующая сессия начнёт с памятью
```

### Экономия лимитов (v5.0 vs v4.0)

| Было (v4.0) | Стало (v7.0) | Экономия |
|---|---|---|
| 2 Opus + 6 Sonnet | 2 Opus + 2 Sonnet + 4 Haiku | ~60% на CUT-агентах |
| Sonnet = $3/M input | Haiku = $0.80/M input | 3.75x дешевле per agent |
| Beta/Gamma/Delta/Epsilon на Sonnet | Те же на Haiku | Быстрее output, тот же QA gate |
| Нет Gemma агентов | 4 Gemma (Omicron/Pi/Rho/Sigma) локально | $0 — бесплатно через Ollama |
| Claude API для всех задач | Gemma берёт recon/scout/QA | -20-30% API calls на Claude |

---

## Escalation: когда Haiku не справляется

Признаки что нужен Sonnet:
- Агент зациклился (3+ попытки одного и того же)
- Задача требует multi-file архитектурного reasoning
- Merge conflict resolution (сложные)
- Новая фича с нуля (не fix/wiring)

Решение: временно повысить модель через fallback-запуск, после задачи вернуть.
```bash
# Временно Beta на Sonnet для сложной задачи (fallback с явной моделью)
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/cut-media && claude --dangerously-skip-permissions --model sonnet
```

---

## Создание новой роли (add_role.sh v2)

### Быстрый старт: добавить Mistral-4 (пример)

```bash
# 1️⃣ РЕГИСТРАЦИЯ роли в agent_registry.yaml
cd ~/Documents/VETKA_Project/vetka_live_03
bash scripts/add_role.sh Mistral-4 grok "WEATHER Agent 4"

# Скрипт автоматически:
# ✓ Проверит отсутствие дубликата (Mistral-4 ещё не существует)
# ✓ Вставит роль перед shared_zones: в YAML (не в конец файла!)
# ✓ Выполнит generate_agents_md.py (создаст role-specific CLAUDE.md)
# ✓ Выведет: ✅ Role Mistral-4 registered
```

### Проверка регистрации

```bash
# Убедиться что роль добавлена в реестр
cd ~/Documents/VETKA_Project/vetka_live_03
grep -A 3 "Mistral-4:" agent_registry.yaml

# Ожидаемый вывод:
# Mistral-4:
#   callsign: Mistral-4
#   agent_type: grok
#   description: WEATHER Agent 4
```

### Создание worktree для роли

```bash
# 2️⃣ СОЗДАТЬ изолированную среду (worktree) для Mistral-4
cd ~/Documents/VETKA_Project/vetka_live_03
git worktree add .claude/worktrees/weather-mistral-4 main

# Скрипт создаст:
# .claude/worktrees/weather-mistral-4/       ← новая среда
# .claude/worktrees/weather-mistral-4/CLAUDE.md  ← role-specific конфиг (~800 байт)
```

### Запуск агента в worktree

```bash
# 3️⃣ ЗАПУСТИТЬ Mistral-4 в его worktree
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-mistral-4

# Запуск через Mistral Vibe CLI (требует: vibe auth login)
vibe

# В первом сообщении (обязательно!):
vetka_session_init role=Mistral-4

# Агент загрузит контекст + получит свои задачи
```

### Полная последовательность команд (copy-paste)

```bash
#!/bin/bash
# Скрипт для добавления новой роли (пример: Mistral-4)

set -e  # выход при ошибке

PROJECT_ROOT=~/Documents/VETKA_Project/vetka_live_03
NEW_ROLE="Mistral-4"
AGENT_TYPE="grok"
DESCRIPTION="WEATHER Agent 4"

echo "🚀 Регистрация новой роли: $NEW_ROLE"
cd "$PROJECT_ROOT"

# 1. Добавить в реестр
bash scripts/add_role.sh "$NEW_ROLE" "$AGENT_TYPE" "$DESCRIPTION"
echo "✓ Роль зарегистрирована"

# 2. Проверка
echo "📋 Проверка в реестре:"
grep -A 2 "$NEW_ROLE:" agent_registry.yaml

# 3. Создать worktree
WORKTREE_PATH=".claude/worktrees/weather-mistral-4"
git worktree add "$WORKTREE_PATH" main
echo "✓ Worktree создан: $WORKTREE_PATH"

# 4. Информация для запуска
echo ""
echo "════════════════════════════════════════"
echo "✅ Роль готова к запуску!"
echo "════════════════════════════════════════"
echo ""
echo "Команда для старта:"
echo "  cd $PROJECT_ROOT/$WORKTREE_PATH && vibe"
echo ""
echo "Первое сообщение в agentе:"
echo "  vetka_session_init role=$NEW_ROLE"
echo ""
```

### Что делает add_role.sh v2

| Этап | Что происходит |
|------|---|
| **Валидация** | Проверка формата callsign `[A-Za-z0-9_-]+` |
| **Дубль-гард** | Если роль уже существует → exit 1 |
| **Вставка в YAML** | Перед `shared_zones:` (НЕ в конец файла!) |
| **generate_agents_md** | Создание role-specific CLAUDE.md (~800 байт) |
| **Проверка exit кода** | При ошибке generate_agents_md → скрипт падает |

### Структура agent_registry.yaml

```yaml
roles:
  Alpha:
    callsign: Alpha
    agent_type: opus
    description: Architect

  Mistral-1:
    callsign: Mistral-1
    agent_type: grok
    description: WEATHER Agent 1

  Mistral-4:  # ← НОВАЯ РОЛЬ, добавлена сюда
    callsign: Mistral-4
    agent_type: grok
    description: WEATHER Agent 4

shared_zones:
  task_board: /src/orchestration/task_board.py
  # ← add_role.sh вставляет ПЕРЕД этой строкой
```

### Ошибки и решения

```bash
# ❌ ERROR: Mistral-4 already exists
# Причина: роль уже в реестре
# Решение: используй другое имя или удали старую

# ❌ Callsign format error
# Причина: недопустимые символы (например: пробел, @, #)
# Решение: используй только [A-Za-z0-9_-]

# ❌ generate_agents_md failed
# Причина: ошибка в скрипте генерации
# Решение: проверь generate_agents_md.py, откати изменения в registry

# ❌ Worktree already exists
# Причина: .claude/worktrees/{role} уже создана
# Решение: либо используй существующий, либо удали старый
git worktree remove .claude/worktrees/weather-mistral-4
```

### Mistral агенты: где они регистрируются

✅ **БЫЛО (старое):** Mistral-1/2/3 в `external_agents:` секции — невидимы для AgentRegistry

❌ **ПОСЛЕ (2026-04-02):** Mistral-1/2/3 в `roles:` секции — видны всем агентам

```bash
# Проверить, что Mistral в roles (не в external_agents)
grep -A 5 "roles:" agent_registry.yaml | grep Mistral
# ✓ Mistral-1:
# ✓ Mistral-2:
# ✓ Mistral-3:
```

---

*"Каждый агент знает свою роль. Тебе нужно только сказать — что делать."*

---

## Sherpa — бесплатный разведчик для задач (Phase 202)

### Что это
Sherpa — **автономный recon-агент**, который обогащает pending-задачи исследованиями из бесплатных AI-сервисов (DeepSeek, Grok, Qwen, Claude Haiku, ChatGPT, Kimi). Sherpa **не пишет production код** — он готовит trail для настоящих агентов.

### Зачем
~30% сессии каждого агента уходит на recon (поиск файлов, изучение архитектуры, исследование подходов). Sherpa делает этот recon бесплатно и заранее. Результат: +30-50% throughput при тех же лимитах.

### Sherpa Commands

```bash
# First-time setup (login to AI services)
cd ~/Documents/VETKA_Project/vetka_live_03
python sherpa.py --setup

# Run full recon cycle (50 tasks, ~1 hour)
python sherpa.py --visible

# Run single task for testing
python sherpa.py --once --visible

# Dry run — see what would be processed
python sherpa.py --dry-run --once

# Run headless (background, no browser window)
python sherpa.py

# Use specific service only
python sherpa.py --service deepseek --visible
```

### What Sherpa Does

- Takes pending tasks from TaskBoard
- Searches codebase (ripgrep) for relevant files
- Sends task description + architecture docs + code snippets to free AI services (DeepSeek, etc.)
- Saves research response to docs/sherpa_recon/sherpa_{task_id}.md
- Updates task with recon_docs and implementation_hints
- Releases task back as pending (enriched) for coding agents

### Rules

- Only ONE Sherpa instance at a time (PID lock guard)
- Only Commanders launch Sherpa
- Config: config/sherpa.yaml
- Recon output: docs/sherpa_recon/
- Logs: logs/sherpa.log

### Как работает (pipeline)
```
TaskBoard (pending task)
    -> Sherpa claims task
      -> ripgrep searches codebase for relevant files
      -> Reads architecture_docs and recon_docs from task
      -> Builds prompt (task desc + docs + code snippets)
      -> Playwright opens DeepSeek
      -> fill() prompt into textarea
      -> Enter to send
      -> Wait for Copy button + text stability
      -> Extract response via clipboard
      -> Ollama summarizes key points
      -> Save to docs/sherpa_recon/sherpa_{task_id}.md
      -> Update task: recon_docs + implementation_hints
      -> Release task back to pending (enriched)
    -> Cooldown -> next task
```

### Кто запускает Sherpa

**Только один экземпляр одновременно.** Причины:
- Chromium (Playwright) = ~300-500MB RAM
- AI-сервисы блокируют параллельные сессии с одного аккаунта
- Два Sherpa на одном таске = конфликт claim

Запускает:
- **Пользователь** — вручную в терминале
- **Commander** — командой `python sherpa.py` в фоне
- **Guard:** PID lock file (`data/sherpa.pid`) не даст запустить второй экземпляр

> **Обычные агенты (Alpha, Beta, Gamma, Delta) НЕ запускают Sherpa.** Они пользуются его результатами — видят готовый recon в полях `recon_docs` и `implementation_hints` своих задач.

### Установка (один раз)

```bash
# 0. Перейти в проект (обязательно!)
cd ~/Documents/VETKA_Project/vetka_live_03

# 1. Зависимости
pip install httpx pyyaml playwright
playwright install chromium

# 2. Логин в сервисы (один раз, вручную)
python sherpa.py --setup
# Браузер откроется -> залогинься в каждый сервис -> Enter
# Сессии сохраняются в data/sherpa_profiles/
```

### Ротация аккаунтов

Для обхода лимитов можно добавить несколько аккаунтов одного сервиса:

```yaml
# В config/sherpa.yaml:
services:
  - name: grok
    profile_dir: data/sherpa_profiles/grok_1   # аккаунт 1
    enabled: true
  - name: grok
    profile_dir: data/sherpa_profiles/grok_2   # аккаунт 2
    enabled: true
```

Каждый аккаунт — отдельный `--setup`:
```bash
python sherpa.py --setup --service grok
# логин аккаунт 1, Enter
# потом меняем profile_dir на grok_2, снова --setup
```

Sherpa ротирует round-robin по всем enabled сервисам.

### Доступные сервисы

| # | Сервис | Лимиты | Cooldown | Заметки |
|---|--------|--------|----------|---------|
| 1 | **DeepSeek** | Безлимит | 60s | Основная рабочая лошадка |
| 2 | **Grok** | Очень большие | 90s | Хорошее качество |
| 3 | **Qwen** | Безлимит / очень большие | 60s | Не принимает .ts/.tsx |
| 4 | **Claude.ai** | Free Haiku | 180s | Консервативный cooldown |
| 5 | **ChatGPT** | Free tier | 120s | |
| 6 | **Kimi** | Хорошие | 60s | Режим "ok computer" для кода |
| 7 | **cto.new** | Playground | 300s | disabled по умолчанию, медленно |

### Что видят агенты после Sherpa

Когда Alpha/Beta/Gamma берут таск, который прошёл через Sherpa:

```
task.recon_docs = ["docs/sherpa_recon/sherpa_tb_12345.md"]
task.implementation_hints = """
[Sherpa Recon 2026-04-02]
- Modify src/services/timeline.py lines 120-145
- Use existing TimelineStore.addClip() pattern
- Risk: concurrent access from WebSocket handler
"""
```

Агент сразу видит файлы, подход и риски — пропускает 30% recon фазы.

### Файлы

| Файл | Назначение |
|------|-----------|
| `sherpa.py` | Основной скрипт (~500 строк) |
| `config/sherpa.yaml` | Сервисы, cooldowns, agent identity |
| `docs/sherpa_recon/` | Recon-отчёты (sherpa_{task_id}.md) |
| `data/sherpa_profiles/` | Сохранённые сессии браузера |
| `logs/sherpa.log` | Лог работы |
| `docs/202ph_SHERPA/SHERPA_CONCEPT.md` | Концепт-документ |
| `docs/202ph_SHERPA/ARCHITECTURE_SHERPA.md` | Архитектура и roadmap |

---

## Mistral Vibe CLI — Установка и настройка

### Установка
```bash
# npm
npm install -g @mistralai/vibe-cli

# или pip
pip install mistral-vibe-cli

# Авторизация
vibe auth login
# Следуй инструкциям → получи API ключ с https://console.mistral.ai/
```

### Что такое Vibe CLI
Mistral Vibe CLI — это AI coding agent от Mistral, аналог Claude Code. Работает с моделями Devstral 2 (123B) и Devstral Small 2 (24B). Бесплатный лимит: ~10-15 задач/день на аккаунт.

### Инструкции для Vibe агентов (обновлено 2026-04-02)

При запуске Vibe в worktree, агент получает роль двумя способами:

**Способ 1: Явная роль (РЕКОМЕНДУЕТСЯ)**
```bash
# В первом сообщении агенту:
vetka_session_init role=Mistral-1
# (или Mistral-2, Mistral-3)
```

**Способ 2: Автодетекция из worktree**
- Vibe читает .claude/worktrees/{имя} → определяет ветку → ищет в agent_registry.yaml
- Fallback если role= не указана

**Процесс работы:**
1. `vetka_session_init role=Mistral-1` → агент загружает контекст
2. Видит свою роль (Mistral-1), домен (WEATHER или QA), owned_paths
3. Берёт pending таск из task_board
4. Работает → git commit → помечает need_qa
5. Delta верифицирует → verified или needs_fix

### Лимиты Mistral Vibe

```
Бесплатный tier (Vibe CLI):
  - ~300-500 задач/месяц НА АККАУНТ
  - 3 роли Mistral (1/2/3) = ~900-1500 задач/месяц СУММАРНО
  - Cooldown между задачами: 30-60s

Если лимит исчерпан:
  - Добавить второй Mistral аккаунт (другой email)
  - Создать новую роль (например, Mistral-4)
  - Повернуть между аккаунтами вручную или через sherpa.py rotation
```

### Добавление второго Mistral аккаунта (если нужен больше лимит)

```bash
# 1. Создать новую роль
cd ~/Documents/VETKA_Project/vetka_live_03
bash scripts/add_role.sh Mistral-4 grok "WEATHER Agent 4 (extra account)"

# 2. Логин в новый аккаунт
vibe auth login
# → Браузер откроется → залогиньтесь с ДРУГОГО email-адреса
# → Получите новый API key

# 3. Запустить новую роль
git worktree add .claude/worktrees/weather-mistral-4 main
cd .claude/worktrees/weather-mistral-4
vibe
# → vetka_session_init role=Mistral-4
```
- Идеально для: QA раны, WEATHER tasks, простые фиксы, документация

---

## Captain Burnell — Sherpa Architect

Роль-одиночка. Создатель Sherpa (Phase 202). Подход: прототип сначала, документы потом.

### Запуск

```bash
cd ~/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/magical-burnell
claude
# первое сообщение:
vetka_session_init role=Burnell
```

### Зона ответственности

- sherpa.py — основной скрипт агента-разведчика
- config/sherpa.yaml — сервисы, профили, тайминги
- docs/202ph_SHERPA/ — архитектура, roadmap, recon отчёты
- Sherpa pipeline: TaskBoard -> Playwright -> AI services -> recon_docs
- Координация бесплатных AI сервисов (DeepSeek, Kimi, Arena, Mistral, Z.ai)

### Sherpa — быстрый старт

```bash
cd ~/Documents/VETKA_Project/vetka_live_03

# Первый раз — залогиниться в сервисы (вторичные gmail!)
python sherpa.py --setup

# Запуск на 50 тасков (видимый браузер)
python sherpa.py --visible

# Один таск для теста
python sherpa.py --once --visible

# Фоновый режим (headless)
python sherpa.py

# Сухой прогон (без отправки)
python sherpa.py --dry-run --once

# Проверить совместимость сервисов
python sherpa.py --probe

# Если Sherpa завис — удалить PID lock
rm data/sherpa.pid
```

### Ключевые файлы

| Файл | Что |
|------|-----|
| `sherpa.py` | Основной скрипт (~600 строк) |
| `config/sherpa.yaml` | 10 сервисов, профили, cooldown |
| `data/sherpa_profiles/` | Сохранённые сессии браузера |
| `data/sherpa_feedback.jsonl` | Автоматический лог (service, chars, time) |
| `data/sherpa.pid` | PID lock (удалить если Sherpa завис) |
| `docs/sherpa_recon/` | Результаты разведки по таскам |
| `logs/sherpa.log` | Логи агента |

### Правила

- Только ОДИН экземпляр Sherpa одновременно (PID guard)
- Только Commanders запускают Sherpa
- Только ВТОРИЧНЫЕ gmail аккаунты (не основной!)
- DeepSeek + Kimi = надёжные. Grok/ChatGPT = отключены (bot detection)
- Ответ < 5000 chars = неполный, Sherpa ждёт дольше
- После обогащения таск получает статус `recon_done`
- Один таб браузера — при смене сервиса старый закрывается

| **Burnell** | `magical-burnell` | engine | claude_code | opus | Captain Burnell / Sherpa Architect |

| **Wu** | `musing-wu` | harness | claude_code | haiku | Harness Guardian |
