# Group Chat Persistence - Phase 81

## Обзор

Добавлена персистентность для групповых чатов в VETKA. Группы и сообщения теперь сохраняются в JSON и восстанавливаются при перезапуске сервера.

## Изменения

### 1. Файл: `src/services/group_chat_manager.py`

#### Добавленные импорты:
- `json` - для сериализации/десериализации
- `os` - для работы с файловой системой
- `Path` - для работы с путями

#### Новые методы:

**`save_to_json()`** - Сохранение всех групп в JSON файл
- Формат: `data/groups.json`
- Атомарная запись через временный файл
- Вызывается автоматически при:
  - Создании группы
  - Отправке сообщения
  - Добавлении участника
  - Удалении участника

**`load_from_json()`** - Загрузка групп из JSON при старте
- Восстанавливает объекты `Group`, `GroupParticipant`, `GroupMessage`
- Восстанавливает связи agent-group
- Восстанавливает LRU-порядок по `last_activity`

#### Константа:
```python
GROUPS_FILE = Path("data/groups.json")
```

### 2. Файл: `main.py`

Добавлена загрузка сохраненных групп при инициализации:

```python
# Load saved groups from JSON
await manager.load_from_json()
```

## Структура JSON

```json
{
  "groups": {
    "group_id": {
      "id": "uuid",
      "name": "Group Name",
      "description": "...",
      "admin_id": "@admin",
      "participants": {
        "@agent_id": {
          "agent_id": "@agent_id",
          "model_id": "model-name",
          "role": "admin|worker|reviewer|observer",
          "display_name": "Display Name",
          "permissions": ["read", "write"]
        }
      },
      "messages": [
        {
          "id": "msg_uuid",
          "group_id": "group_id",
          "sender_id": "@sender",
          "content": "Message text",
          "mentions": ["@mentioned_agent"],
          "message_type": "chat|task|artifact|system",
          "metadata": {},
          "created_at": "2026-01-21T19:18:41.708827"
        }
      ],
      "shared_context": {},
      "project_id": null,
      "created_at": "2026-01-21T19:18:41.706447",
      "last_activity": "2026-01-21T19:18:41.709279"
    }
  },
  "saved_at": "2026-01-21T19:18:41.709290"
}
```

## Особенности реализации

### Атомарная запись
Используется паттерн "write to temp, then rename" для предотвращения повреждения данных при сбое:

```python
temp_file = self.GROUPS_FILE.with_suffix('.tmp')
with open(temp_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
temp_file.replace(self.GROUPS_FILE)
```

### Потокобезопасность
Все операции чтения/записи защищены асинхронным локом:

```python
async with self._lock:
    # операции с self._groups
```

### Ограничение памяти
Сохраняется только до `MAX_MESSAGES_PER_GROUP = 1000` сообщений на группу (deque с maxlen).

### LRU-восстановление
При загрузке группы сортируются по `last_activity` для корректной работы LRU-механизма очистки.

## Тестирование

Скрипт `test_group_persistence.py` демонстрирует:
1. Создание группы с участниками
2. Отправку сообщений
3. Автоматическое сохранение
4. Загрузку в новый экземпляр менеджера
5. Проверку восстановленных данных

Запуск теста:
```bash
python test_group_persistence.py
```

## Обратная совместимость

- Если файл `data/groups.json` не существует, система работает как раньше (in-memory)
- Старые группы автоматически сохранятся при первом изменении
- При ошибке загрузки логируется warning, система продолжает работу с пустым состоянием

## Производительность

- Сохранение выполняется асинхронно с минимальной блокировкой
- JSON-файл компактный (1-2KB для типичной группы с сообщениями)
- При большом количестве групп (>100) работает LRU-очистка

## Следующие шаги

Возможные улучшения (по необходимости):
- [ ] Версионирование формата JSON
- [ ] Миграция на SQLite для больших объемов
- [ ] Инкрементальное сохранение (только измененные группы)
- [ ] Сжатие старых сообщений
- [ ] Экспорт/импорт групп

---

**Дата реализации:** 2026-01-21
**Фаза:** Phase 81
**Статус:** ✅ Реализовано и протестировано
