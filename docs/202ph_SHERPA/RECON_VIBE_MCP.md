# RECON: Vibe/Windsurf MCP — почему Mistral-1 стартует без инструментов

**Автор:** Agent Eta (harness-eta)
**Дата:** 2026-04-03
**Задача:** tb_1775164913_23358_1
**Статус:** RESOLVED — root cause найден, fix задокументирован

---

## Root Cause

**`~/.vibe/config.toml` строка 24:**
```toml
mcp_servers = []
```

Vibe читает MCP-серверы из **`~/.vibe/config.toml`**. Секция `mcp_servers` — пустой массив. Vetka MCP-сервер туда не добавлен → при запуске Vibe показывает "0 MCP servers" → `vetka_task_board` и `vetka_session_init` недоступны.

---

## Анализ конфигурационных файлов

| Файл | Читается? | MCP vetka | Статус |
|------|-----------|-----------|--------|
| `~/.vibe/config.toml` | ✅ Vibe читает | ❌ `mcp_servers = []` | **ROOT CAUSE** |
| `opencode.json` (проект) | ❌ Vibe игнорирует | ✅ полный конфиг | не используется |
| `.claude/settings.json` | ❌ только Claude Code | — | не применимо |
| `~/.vibe/vibe_config.json` | ✅ skills config | ❌ нет MCP | только скиллы |
| `~/.vibe/VIBE.md` | 📄 документация | Python-fallback | старый подход |
| `.windsurfrules` | ❌ не найден | — | не существует |

### Что уже есть в проекте

`opencode.json` содержит правильный конфиг vetka, но в OpenCode-формате (Vibe его не читает):
```json
"mcp": {
  "vetka": {
    "type": "local",
    "command": ["python", ".../src/mcp/vetka_mcp_bridge.py"],
    "enabled": true,
    "environment": {
      "VETKA_API_URL": "http://localhost:5001",
      "PYTHONPATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
    }
  }
}
```

### AGENTS.md в weather-mistral-1

Содержит корректную Init-секцию:
```
1. vetka_session_init role=Mistral-1
2. vetka_task_board action=list ...
```

Но без MCP-сервера эти инструкции мертвы — инструменты недоступны независимо от того, что написано в AGENTS.md.

---

## Диагностика симптомов

**Что делает агент при старте без MCP:**
1. `vetka_task_board` → `Unknown tool` — инструмент не зарегистрирован
2. `vetka_session_init` → недоступен
3. Агент читает AGENTS.md через `cat`/`ls`, делает `git log`, `git status`
4. Объявляет "Ready" без реального доступа к таскборду
5. Работает вслепую — не видит задачи, не может коммитить через vetka_git_commit

---

## Fix: добавить vetka MCP в ~/.vibe/config.toml

### Шаг 1: Добавить MCP-сервер в config.toml

Открыть `~/.vibe/config.toml` и заменить:
```toml
mcp_servers = []
```
На:
```toml
[[mcp_servers]]
name = "vetka"
command = ["python", "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"]
enabled = true

[mcp_servers.environment]
VETKA_API_URL = "http://localhost:5001"
PYTHONPATH = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
```

> **Примечание:** Точный синтаксис зависит от версии Vibe CLI. Если `[[mcp_servers]]` не работает — проверить документацию `vibe mcp --help` или попробовать inline формат: `mcp_servers = [{name="vetka", command=["python", "..."]}]`

### Шаг 2: Перезапустить Vibe

```bash
# Проверить что bridge запустился
pgrep -f vetka_mcp_bridge.py

# Перезапустить Vibe в worktree Mistral-1
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/.claude/worktrees/weather-mistral-1
vibe
```

### Шаг 3: Верифицировать

При старте агент должен увидеть:
```
MCP servers: 1 (vetka)
Available tools: vetka_session_init, vetka_task_board, vetka_git_commit, ...
```

---

## Альтернатива: Fallback через Python-скрипт

Если MCP в Vibe нельзя настроить глобально — добавить в `AGENTS.md` Mistral-1 секцию Python-fallback:

```bash
# Если vetka_session_init недоступен как MCP-инструмент:
python -c "
import asyncio, sys
sys.path.insert(0, '/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')
from src.mcp.tools.session_tools import vetka_session_init
result = asyncio.run(vetka_session_init(user_id='danila', role='Mistral-1'))
print(result)
"
```

Но это временный костыль — правильное решение только через MCP.

---

## Сравнение: Claude Code vs Vibe MCP Config

| | Claude Code | Vibe/Windsurf |
|--|-------------|---------------|
| MCP config | `.claude/settings.json` → `mcpServers` | `~/.vibe/config.toml` → `mcp_servers` |
| Format | JSON | TOML |
| Scope | per-project или global | global (один файл) |
| Auto-load | ✅ на старте | ✅ на старте (если настроен) |
| Current state | ❌ пустой mcpServers | ❌ пустой mcp_servers |

> **Любопытно:** У Claude Code тоже пустой `mcpServers` в settings.json — MCP подключается через Claude Desktop или через другой механизм (вероятно через `~/.config/claude/settings.json` или через MCC harness).

---

## Action Items

| # | Действие | Кто | Статус |
|---|----------|-----|--------|
| 1 | Добавить vetka MCP в `~/.vibe/config.toml` | Commander/User (ручной шаг) | ⏳ |
| 2 | Обновить AGENTS.md weather-mistral-1 — добавить fallback секцию | Eta | ✅ Done |
| 3 | Верифицировать Mistral-1 после фикса | Commander | ⏳ |

---

*Recon by Agent Eta | tb_1775164913_23358_1 | 2026-04-03*
