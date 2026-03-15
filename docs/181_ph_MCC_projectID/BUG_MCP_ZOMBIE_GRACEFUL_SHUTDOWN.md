# BUG: MCP Zombie Processes — Graceful Shutdown

**Status:** RECON COMPLETE, FIXES NEEDED
**Severity:** MEDIUM (causes stale session_init, port conflicts)
**Phase:** 181.6
**Date:** 2026-03-15
**Related:** BUG_SESSION_INIT_JSON_NAMESPACE.md (zombies were root cause)

---

## Problem Statement

MCP bridge и Mycelium создают **зомби-процессы** при закрытии чатов:
- 24 `vetka_mcp_bridge.py` зомби обнаружено одновременно
- 4 `mycelium_mcp_server.py` зомби
- Результат: session_init загружает старый код, порт 8082 конфликтует

**Причина:** Claude Code/Desktop запускают новый MCP process на каждый чат, но при закрытии чата SIGHUP/SIGTERM не всегда корректно завершает asyncio loop.

---

## Recon Summary (Хайку скауты)

### vetka_mcp_bridge.py — Штурмовой Мост

| Элемент | Статус | Строки |
|---------|--------|--------|
| Signal handlers (SIGINT/SIGTERM) | ✅ | 2530-2532, 2568-2569 |
| `graceful_shutdown()` | ✅ | 2534-2559 |
| HTTP client cleanup | ✅ | 2557 |
| MCP actors cleanup | ✅ | 2540-2545 |
| `finally` блок | ✅ | main() |

**Вердикт:** Bridge сам по себе ОК. Зомби появляются из-за Claude Code — он порождает процесс через `disclaimer` wrapper и при закрытии чата может не послать signal.

### mycelium_mcp_server.py — Грибница

| Элемент | Статус | Строки |
|---------|--------|--------|
| Signal handlers (SIGINT/SIGTERM) | ✅ | 991-992 |
| `_graceful_shutdown()` | ✅ | 958-983 |
| Pipeline task cancellation | ✅ | 961-967 (5s timeout) |
| WebSocket broadcaster stop | ✅ | 970-972 |
| HTTP client close | ✅ | 975-977 |
| Pipeline state persist | ✅ | 980-981 |
| `asyncio.wait(FIRST_COMPLETED)` | ✅ | 1010-1013 |

**Вердикт:** Shutdown логика написана правильно, НО есть 6 проблемных мест.

---

## Найденные проблемы (MARKER_181.6.x)

### MARKER_181.6.4: Pipeline infinite loop ignores cancel
**Файл:** `mycelium_mcp_server.py` строка 610
**Проблема:** `asyncio.create_task(_run())` запускает pipeline в fire-and-forget. Если pipeline содержит `while True` (retry loop в agent_pipeline), `task.cancel()` может не сработать если код в sync-блоке.
**Severity:** MEDIUM
**Fix:** Добавить `asyncio.wait_for(task, timeout=10)` в `_graceful_shutdown`

### MARKER_181.6.5: WebSocket wait_closed может зависнуть
**Файл:** `mycelium_ws_server.py` строки 64-70
**Проблема:** Если WS клиент не отключился, `wait_closed()` может ждать бесконечно.
**Severity:** LOW (уже есть `self._server.close()` перед `wait_closed()`)
**Fix:** Добавить `asyncio.wait_for(self._server.wait_closed(), timeout=3)`

### MARKER_181.6.8: SSE heartbeat while True loop
**Файл:** `vetka_mcp_server.py` строка 467-469
```python
while True:
    await asyncio.sleep(30)
    yield {"event": "ping", "data": ""}
```
**Проблема:** SSE генератор никогда не завершится при SIGTERM. `asyncio.sleep(30)` может быть cancelled, но только если event loop обработает cancel ДО начала следующего yield.
**Severity:** HIGH
**Fix:** Проверять `_shutdown_event.is_set()` в цикле

### MARKER_181.6.9: Uvicorn не получает shutdown signal
**Файл:** `vetka_mcp_server.py` строка 578
**Проблема:** `await server_instance.serve()` — synchronous wait без timeout. Активные HTTP соединения могут блокировать завершение.
**Severity:** HIGH
**Fix:** `server_instance.should_exit = True` в signal handler

### MARKER_181.6.10: Нет atexit для crash recovery
**Проблема:** `kill -9` обходит все signal handlers и finally блоки. Pipeline state может потеряться.
**Severity:** LOW
**Fix:** `atexit.register()` для критичных файловых операций (pipeline state JSON)

### MARKER_181.6.11: HTTP aclose() без timeout
**Файл:** `mycelium_http_client.py` строка 49-54
**Проблема:** `await http_client.aclose()` может ждать бесконечно если соединение зависло.
**Severity:** MEDIUM
**Fix:** `asyncio.wait_for(client.aclose(), timeout=3)`

---

## SIGHUP — Главный виновник зомби

**Проблема:** Когда терминал закрывается, система посылает `SIGHUP`. Но:

1. `mycelium_mcp_server.py` НЕ обрабатывает SIGHUP (только SIGINT/SIGTERM)
2. `vetka_mcp_bridge.py` НЕ обрабатывает SIGHUP (только SIGINT/SIGTERM)
3. Python по умолчанию ИГНОРИРУЕТ SIGHUP если процесс detached (nohup-like)

**Fix (MARKER_181.6.12):** Добавить в оба сервера:
```python
signal.signal(signal.SIGHUP, _signal_handler)  # Terminal close
```

---

## Implementation Plan

### Phase 181.6 Tasks

| Task | File | Change | Time | Priority |
|------|------|--------|------|----------|
| **181.6.A** | mycelium_mcp_server.py | Add SIGHUP handler (line 992) | 2m | P0 |
| **181.6.B** | vetka_mcp_bridge.py | Add SIGHUP handler (line 2569) | 2m | P0 |
| **181.6.C** | mycelium_mcp_server.py | Pipeline cancel timeout (line 965) | 5m | P1 |
| **181.6.D** | mycelium_ws_server.py | wait_closed timeout | 3m | P2 |
| **181.6.E** | vetka_mcp_server.py | SSE loop shutdown check | 5m | P1 |
| **181.6.F** | vetka_mcp_server.py | Uvicorn graceful exit | 5m | P1 |
| **181.6.G** | mycelium_http_client.py | aclose() timeout | 3m | P2 |
| **181.6.H** | Both servers | atexit.register for state | 5m | P2 |

**P0 = сразу (5 мин), P1 = следующий спринт, P2 = когда руки дойдут**

---

## Quick Fix (P0 — 5 минут)

### Добавить SIGHUP в оба сервера:

**mycelium_mcp_server.py** (после строки 992):
```python
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGHUP, _signal_handler)  # MARKER_181.6.12: Terminal close
```

**vetka_mcp_bridge.py** (после строки 2569):
```python
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)  # MARKER_181.6.12: Terminal close
```

### Cleanup скрипт (добавить в .bashrc/.zshrc):
```bash
alias mcp-cleanup='pkill -9 -f vetka_mcp_bridge; pkill -9 -f mycelium_mcp_server; echo "MCP zombies killed"'
```

---

## Prevention: Auto-cleanup

### Option A: PID файл
Каждый MCP процесс пишет свой PID в `data/mcp_pids/`. При старте проверяет и убивает старые.

### Option B: Unix socket lock
Использовать `fcntl.flock()` на файле — второй процесс с тем же lock-файлом гарантированно завершит первый.

### Option C: Watchdog
Отдельный lightweight скрипт, который мониторит MCP процессы и убивает зависшие (>1h без activity).

---

## Status Tracker

- [ ] **181.6.A** — SIGHUP handler: mycelium
- [ ] **181.6.B** — SIGHUP handler: bridge
- [ ] **181.6.C** — Pipeline cancel timeout
- [ ] **181.6.D** — WS wait_closed timeout
- [ ] **181.6.E** — SSE loop shutdown check
- [ ] **181.6.F** — Uvicorn graceful exit
- [ ] **181.6.G** — HTTP aclose timeout
- [ ] **181.6.H** — atexit state persistence
- [ ] **181.6.12** — SIGHUP (main fix for zombies)
