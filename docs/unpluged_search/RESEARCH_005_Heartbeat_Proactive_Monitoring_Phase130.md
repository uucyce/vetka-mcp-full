# Heartbeat: Проактивный мониторинг задач
## Рекомендуемая фаза: 130 | Приоритет: СРЕДНИЙ | Сложность: 4-6 часов

### Суть исследования
Async loop каждые 5 минут для проверки открытых задач, напоминаний, и элементов с низкой активацией.

### Текущее состояние
- ✅ heartbeat_tick() определён в MCP tools
- ✅ @titan auto-tiers (lite/core/prime) реализован
- ❌ Полноценный proactive monitoring не работает
- ❌ Нет escalation на высокий surprise

### Техническая спецификация
**Heartbeat Engine:**
- Interval: 5 минут (configurable)
- Qdrant filter: "status: open" + timestamp
- Socket.IO toast notifications
- Escalation при surprise > 0.6

**Функции:**
1. Проверка открытых задач в TaskBoard
2. Напоминания о stale items
3. Low-activation item surfacing
4. Auto-dispatch к Mycelium pipeline

**API:**
- GET /api/heartbeat/status
- POST /api/heartbeat/tick
- POST /api/heartbeat/configure

### Зависимости
- TaskBoard (существует)
- Qdrant (существует)
- Socket.IO (существует)

### Ожидаемый результат
- Автоматическое обнаружение забытых задач
- Proactive notifications
- Self-healing workflow

### Источник
Беседы агентов, VETKA Pulse concept
