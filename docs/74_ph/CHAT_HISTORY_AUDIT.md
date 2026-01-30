# Chat History System Architecture Audit
**Phase 74 — Разведка для фикса группового контекста**

---

## 🎯 Миссия Выполнена
Аудит системы сохранения/восстановления истории чатов. Найдены 3 ключевые проблемы + места для фиксов.

---

## 📍 Ключевые Файлы

| Файл | Строки | Назначение | Статус |
|------|--------|-----------|--------|
| `src/chat/chat_history_manager.py` | 1–280 | Менеджер персистентности чатов | ACTIVE |
| `src/api/handlers/handler_utils.py` | 48–92 | Контекст + сохранение (BUG!) | **CRITICAL** |
| `src/api/routes/chat_history_routes.py` | 1–291 | REST API для чатов | ACTIVE |
| `client/src/components/chat/ChatSidebar.tsx` | 1–208 | UI истории (нет rename) | INCOMPLETE |
| `data/chat_history.json` | — | Хранилище чатов | JSON |

---

## 🔴 ПРОБЛЕМА #1: Папки Блокированы (handler_utils.py:76)

```python
# handler_utils.py, line 76
if not os.path.isfile(filepath):           # ← БЛОКИРУЕТ ПАПКИ!
    result['error'] = f'File not found: {filepath}'
    return result
```

**Цепочка Сбоя:**
```
Пользователь кликает папку в 3D canvas
  ↓
FileCard.tsx → selectNode() → node_path="/path/to/folder"
  ↓
user_message_handler.py:142 → sync_get_rich_context(node_path)
  ↓
os.path.isfile("/path/to/folder") → False
  ↓
Возвращает {'error': 'File not found'}
  ↓
Агент получает пустой контекст
  ↓
Chat история НИКОГДА не создаётся
```

**Почему Происходит:** `os.path.isfile()` для папок возвращает `False`.

**Нужно Изменить:**
- ❌ МАРКЕР: Поменять логику на `os.path.isfile() OR os.path.isdir()`
- ❌ МАРКЕР: Для папок вернуть список файлов вместо содержимого

---

## 🔴 ПРОБЛЕМА #2: Нет Переименования Чатов

**Статус:** Функция не существует вообще.

**Где искали:**
- `ChatHistoryManager` — нет методов rename/update_name
- `chat_history_routes.py` — нет `PATCH /chats/{id}`
- `ChatSidebar.tsx` — только кнопка Delete (line 183–189), нет Edit

**Текущая UI:**
- Отображает только `chat.file_name` (read-only)
- Никакого способа изменить имя

**Нужно Добавить:**
1. ❌ МАРКЕР: `ChatHistoryManager.rename_chat(chat_id, new_name)` — chat_history_manager.py (после line 218)
2. ❌ МАРКЕР: `PATCH /api/chats/{chat_id}` endpoint — chat_history_routes.py (после line 203)
3. ❌ МАРКЕР: Edit UI кнопка/модаль — ChatSidebar.tsx (добавить рядом с Delete)

---

## 🟠 ПРОБЛЕМА #3: Группы Файлов Не Поддерживаются

**Текущая Архитектура:** 1 файл = 1 чат (жёсткая связь)

**Откуда Взялось:**
- `ChatHistoryManager.get_or_create_chat()` принимает ОДИН `file_path`
- Ищет существующий чат по точному пути
- Создаёт новый если не найден

**Что Нужно для Групп:**
1. ❌ МАРКЕР: Новое поле в schema: `context_type: "file" | "folder" | "group" | "topic"`
2. ❌ МАРКЕР: Новое поле: `items: [file_paths]` для групп файлов
3. ❌ МАРКЕР: Новое поле: `topic: str` для чатов без файлов (вместо `file_path: 'unknown'`)

---

## 📊 Текущая Структура Чата

```json
{
  "chats": {
    "UUID": {
      "id": "UUID",
      "file_path": "/abs/path/to/file.md",
      "file_name": "file.md",
      "created_at": "2026-01-06T...",
      "updated_at": "2026-01-06T...",
      "messages": [
        {
          "id": "UUID",
          "role": "user|assistant",
          "content": "text",
          "timestamp": "ISO8601",
          "metadata": {}
        }
      ]
    }
  }
}
```

**Проблема:** Предполагает 1:1 файл-к-чату. Нет поддержки папок, групп, тем.

---

## 🔵 Когда Создаётся История Чата

**Нормальный Flow (works):**
```
1. save_chat_message(node_path, message)  ← handler_utils.py:161
2. ChatHistoryManager.get_or_create_chat(normalized_path)
3. manager.add_message(chat_id, msg)
4. Сохраняет в chat_history.json
```

**С Папкой (broken):**
```
1. Папка блокирована на шаге sync_get_rich_context()
2. Message НИКОГДА не дошёл до save_chat_message()
3. История никогда не создалась
```

---

## 📍 Точки Интеграции Для Фикса

### 1️⃣ Fix Context Validation (handler_utils.py:76)
**Что:** Поддержать папки в `sync_get_rich_context()`
- Проверить `os.path.isdir()`
- Вернуть список файлов вместо одного файла
- Или вернуть aggregated context

### 2️⃣ Add Chat Rename (везде)
**что:** Добавить переименование
- Schema: добавить `display_name` (опциональное)
- Backend: новый метод в manager + endpoint
- Frontend: UI кнопка + модаль

### 3️⃣ Extend Schema (chat_history_manager.py)
**Что:** Поддержить разные типы контекста
- Добавить `context_type` поле
- Добавить `items` для групп
- Добавить `topic` для topic-based чатов

### 4️⃣ Group Context Tracking (message_utils.py)
**Что:** Сохранять pinned files в историю
- Текущий pinned files system отделён от истории
- Нужна интеграция: какие файлы были pinned когда был создан чат

---

## 📋 Специальные Пути

Эти пути НЕ нормализуются (используются как-есть):
- `'unknown'` — нет выбранного файла
- `'root'` — корень дерева
- `''` — пустая строка

Логика: `chat_history_manager.py` lines 82–88, 95–101

---

## 🎯 План для Opus (Phase 75)

```
STEP 1: Fix isfile() Block (handler_utils.py:76)
  [ ] Изменить условие на: if not (os.path.isfile(filepath) or os.path.isdir(filepath))
  [ ] Добавить logic для папок: os.path.isdir() → вернуть список файлов

STEP 2: Add Chat Rename (3 места)
  [ ] chat_history_manager.py: def rename_chat(chat_id, new_name)
  [ ] chat_history_routes.py: @router.patch("/chats/{chat_id}")
  [ ] ChatSidebar.tsx: Add edit button + modal

STEP 3: Extend Schema (chat_history_manager.py)
  [ ] _create_empty_history(): добавить context_type, items, topic поля
  [ ] get_or_create_chat(): поддержать разные типы контекста

STEP 4: Integrate Pinned Files (message_utils.py)
  [ ] Сохранять pinnedFileIds когда чат создан
  [ ] Восстанавливать pinned files при загрузке истории
```

---

## 📊 Таблица Сложности

| Фикс | Файлы | Сложность | Время | Блокеры |
|------|-------|-----------|-------|---------|
| Папки | 1 | Low | 15 мин | Нет |
| Rename | 3 | Low | 30 мин | Нет |
| Schema Extend | 1 | Med | 45 мин | Нет |
| Pinned Integration | 2 | Med | 60 мин | Нет |

**Итого:** ~2.5 часа на всё

---

## ✅ Общая Оценка

- **Корневая Причина:** `os.path.isfile()` блокирует папки на line 76
- **Сложность Fix:** Простая (2–3 line change)
- **Глубина Проблемы:** Архитектура нуждается в расширении для групп
- **Риск:** Низкий (изменения локализованы)
- **Готовность к Opus:** Да, все точки маркированы ❌

---

**Разведка завершена. Opus готов к фиксам!** 🚀
