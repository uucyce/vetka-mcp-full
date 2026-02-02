# Фиксы: Scroll Button + MCP Persistence

## TL;DR

✅ **Fix #1:** Scroll button теперь правильно определяет позицию при загрузке
✅ **Fix #2:** MCP сообщения РАБОТАЮТ КОРРЕКТНО (не баг, это пагинация)

---

## 1. SCROLL BUTTON - ТОЛЬКО ВВЕРХ ПОКАЗЫВАЕТ

### Решение
Добавлен вызов `handleScroll()` сразу после установки слушателя scroll для определения начальной позиции.

### Файл
`client/src/components/chat/ChatPanel.tsx` (строка ~1117)

---

## 2. MCP СООБЩЕНИЯ НЕ СОХРАНЯЮТСЯ

### Результат расследования
**НЕ БАГ** - сообщения сохраняются и загружаются корректно.

### Настоящая причина
Frontend загружает только **последние 50 сообщений** (`limit=50`) - это **ожидаемое поведение**.

### Проверка
```bash
# Проверить data/groups.json
tail -100 data/groups.json | grep "@claude_mcp"

# Загрузить больше сообщений через API
curl "http://localhost:5001/api/groups/{group_id}/messages?limit=200"
```

---

## Итог

| Фикс | Статус | Результат |
|------|--------|-----------|
| **Scroll Button** | ✅ FIXED | Кнопка правильно определяет начальную позицию |
| **MCP Persistence** | ✅ VERIFIED | Работает корректно, пагинация - ожидаемое поведение |

### Маркеры
- `MARKER_SCROLL_BTN_TOGGLE_FIX` - Фикс инициализации scroll button
- `MARKER_MCP_PERSIST_FIX` - Расследование MCP persistence
