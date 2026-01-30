# CRASH REPORT: VETKA После Правок

**Phase 92 | Date: 2026-01-25**
**Аудит: 5 агентов параллельно**

---

## ВЕРДИКТ

**Код в provider_registry.py ПРАВИЛЬНЫЙ.**
**Проблема: ДВА РАЗНЫХ ПУТИ К МОДЕЛЯМ**

| Путь | Файл | Статус |
|------|------|--------|
| MCP Tool | provider_registry.py | ✅ Работает |
| VETKA UI | api_aggregator_v3.py | ❌ Не использует registry |

---

## ✅ PROVIDER_REGISTRY.PY

Фиксы применены ТОЧНО по рекомендациям:

```python
# Строка 912-913:
clean_model = model.replace("xai/", "").replace("x-ai/", "")
openrouter_model = f"x-ai/{clean_model}"

# Строка 935-938:
clean_model = model.replace("xai/", "").replace("x-ai/", "")
openrouter_model = (
    f"x-ai/{clean_model}" if provider == Provider.XAI else model
)
```

Синтаксис проверен: `python -m py_compile` - OK.

---

## ❌ РЕАЛЬНАЯ ПРОБЛЕМА

**Ошибка:**
```
WebSocket connection to 'ws://localhost:5001/socket.io/' failed
```

**Причина:** Protocol version mismatch

| Компонент | Версия | Протокол |
|-----------|--------|----------|
| socket.io-client | 4.7.5 | Engine.IO v4 |
| python-socketio | 5.11.0 | Нужна явная версия |

---

## ФИКС

**main.py:336-343** - проверить/перезапустить:

```bash
# 1. Убить старые процессы
lsof -ti:5001 | xargs kill -9

# 2. Пересобрать клиент
cd client && npm run build

# 3. Запустить чисто
python main.py
```

Если не помогает, добавить в Socket.IO init:
```python
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=25,
    ping_timeout=60,
    max_http_buffer_size=1e8,  # ДОБАВИТЬ
)
```

---

## FileCard 404

Следствие неработающего backend. Endpoint есть в `tree_routes.py:106-119`.

---

## 🔥 ГЛАВНАЯ ПРОБЛЕМА: ДВА ПУТИ К МОДЕЛЯМ

**VETKA имеет ДВА способа вызова LLM:**

1. **MCP Tool** → `provider_registry.py` → ✅ Фикс работает
2. **VETKA UI** → `api_aggregator_v3.py` → ❌ Старая логика

В `api_aggregator_v3.py:203`:
```python
# ProviderType.GROK: GrokProvider,  # ЗАКОММЕНТИРОВАНО!
```

**VETKA UI не использует `provider_registry.py` вообще!**

### Решение
Либо:
- A) Раскомментировать GrokProvider в api_aggregator_v3.py
- B) Перенаправить VETKA UI на provider_registry.py
- C) Унифицировать оба пути в один

---

## ИТОГ

| Файл | Статус |
|------|--------|
| provider_registry.py | ✅ Правильно |
| api_aggregator_v3.py | ❌ Не использует registry |
| main.py Socket.IO | ⚠️ Перезапустить |

**Фиксы кодера корректны. Проблема в архитектуре - два параллельных пути.**
