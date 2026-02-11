# Heartbeat Proactive Task Monitoring

**Рекомендуемая фаза:** 130
**Статус:** Частично (heartbeat_tick существует)
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов, VETKA Pulse concept

## Описание

Асинхронный цикл каждые 5 минут: проверка открытых задач, напоминания, мониторинг low-activation items.

## Текущее состояние

- heartbeat_tick() существует как tool
- Автоматический loop НЕ настроен
- Нет proactive escalation
- Нет интеграции с toast notifications

## Технические детали

- Qdrant filter: status=open + timestamp
- Socket.IO toast notifications
- Escalation на surprise > 0.6
- Auto-tier: lite/core/prime based on load
- 5-min interval async loop

## Шаги имплементации

1. Настроить background async loop на сервере
2. Добавить escalation rules (surprise threshold)
3. Интегрировать с Socket.IO для toast уведомлений
4. Добавить dashboard виджет для heartbeat status
5. Тестировать с реальными task board items

## Ожидаемый результат

Автономный мониторинг задач без ручного вмешательства
