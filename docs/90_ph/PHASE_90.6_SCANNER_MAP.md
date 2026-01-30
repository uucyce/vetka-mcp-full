# VETKA Scanner Архитектура и Интеграция

## Phase 90.5-90.6: Исправление Scanner и Унификация

### 1. ОБЗОР АРХИТЕКТУРЫ

Сканер в VETKA имеет двухслойную архитектуру:

#### A. Поток данных для ручного сканирования (Manual Scan via API)

```
POST /api/watcher/add → watcher_routes.py::add_watch_directory()
    ↓
get_watcher() [получить singleton VetkaFileWatcher]
    ↓
watcher.add_directory(path) [создать Observer для watchdog]
    ↓
get_qdrant_updater(qdrant_client) [получить singleton QdrantIncrementalUpdater]
    ↓
updater.scan_directory(path) ← MARKER_90.6: Унифицированный метод
    ↓
for each file: update_file(file_path)
    ↓
_file_changed() [проверка хеша SHA256]
    ↓
_get_embedding() [генерация вектора через EmbeddingService]
    ↓
qdrant_client.upsert() → UUID5(file_path) как детерминированный ID
    ↓
Response: {success, indexed_count, message}
```

#### B. Поток данных для реал-тайм мониторинга (Watchdog)

```
Событие файловой системы (create/modify/delete)
    ↓
VetkaFileHandler.on_any_event()
    ↓
debounce (400ms) → _process_batch() [группировка событий]
    ↓
VetkaFileWatcher._on_file_change() [коллбэк]
    ↓
handle_watcher_event(event, qdrant_client) ← MARKER_90.3: Retry logic
    ↓
updater.update_file() ← ТЕ ЖЕ логика что в Manual Scan!
    ↓
Socket.IO emit (node_updated, node_added, node_removed)
```

#### C. Поток данных для браузерных сканирований (Browser Scanner)

```
Browser FileSystem API → файлы с виртуальными путями
    ↓
POST /api/watcher/add-from-browser
    ↓
for each file: create PointStruct
    ↓
path = "browser://rootName/relative/path"
    ↓
qdrant_client.upsert() → UUID5(virtual_path)
    ↓
watcher.add_browser_directory() [отслеживание виртуальной директории]
```

---

### 2. КЛЮЧЕВЫЕ ФАЙЛЫ И ИХ РОЛИ

#### `/src/scanners/qdrant_updater.py` - Основной обновляющик (MARKER_90.6)

**Класс: `QdrantIncrementalUpdater`**
- **Цель**: Инкрементальное обновление Qdrant на основе изменений файлов
- **Ключевые методы**:
  - `update_file(file_path)` → Обновить один файл (с проверкой хеша)
  - `batch_update(file_paths)` → Обновить множество файлов
  - `scan_directory(path, skip_dirs)` → **MARKER_90.6** - Унифицированное сканирование директории
  - `soft_delete(file_path)` → Мягкое удаление (пометить как deleted)
  - `hard_delete(file_path)` → Полное удаление из Qdrant
  - `cleanup_deleted(older_than_hours)` → Очистка старых удаленных файлов

- **Детали детерминированного ID**:
  ```python
  point_id = uuid.uuid5(uuid.NAMESPACE_DNS, file_path).int & 0x7FFFFFFFFFFFFFFF
  # Результат: всегда одинаковый ID для одного пути
  # Позволяет upsert() правильно работать (обновить, если существует)
  ```

- **Проверка изменений** (`_file_changed()`):
  ```python
  1. Вычислить SHA256 хеш текущего файла
  2. Получить old_hash из существующей точки в Qdrant
  3. Сравнить: new_hash == old_hash?
  4. False → пропустить (повысить skipped_count)
  5. True → переиндексировать с новым embedding
  ```

- **Статистика**:
  - `updated_count` - переиндексировано файлов
  - `skipped_count` - пропущено (без изменений)
  - `deleted_count` - удалено
  - `error_count` - ошибок при обработке

---

#### `/src/scanners/file_watcher.py` - Мониторинг файловой системы (Phase 90.3)

**Класс: `VetkaFileWatcher`**
- **Цель**: Управление Watchdog Observer'ами и трансляция событий
- **Ключевые методы**:
  - `add_directory(path, recursive)` → Добавить директорию на слежение
  - `remove_directory(path)` → Удалить из слежения
  - `_on_file_change(event)` → Обработка события (основной коллбэк)
  - `get_status()` → Статус всех наблюдаемых директорий

- **Phase 90.3 - Retry Logic for Qdrant**:
  ```python
  qdrant_client = self._get_qdrant_client()  # Попытка 1
  if not qdrant_client:
      time.sleep(2)  # Подождать 2 сек
      qdrant_client = self._get_qdrant_client()  # Попытка 2

  if qdrant_client:
      handle_watcher_event(event, qdrant_client)
      print("✅ Indexed to Qdrant")
  else:
      print("⚠️ SKIPPED (Qdrant unavailable after retry)")
      # TODO Phase 90.4: Queue for retry
  ```

- **Phase 80.17 - Lazy Fetch Qdrant Client**:
  ```python
  # Проблема: Watcher создается ДО подключения Qdrant
  # Решение: Получить client в момент события, не при инициализации
  from src.initialization.components_init import get_qdrant_manager
  manager = get_qdrant_manager()
  client = manager.client  # Свежий экземпляр каждый раз
  ```

**Класс: `VetkaFileHandler`**
- **Цель**: Дебаунсирование и группировка событий
- **Параметр**: `debounce_ms = 400` (по умолчанию)
- **Детали**:
  - Накапливает события в `pending[path]` список
  - После 400ms без новых событий → вызвать `_process_batch()`
  - Если 10+ событий за раз → `event_type = 'bulk_update'` (git checkout, npm install)
  - Иначе → используется последний event_type

**Класс: `AdaptiveScanner`**
- **Цель**: Адаптивная частота сканирования на основе активности
- **Heat Score**: 0.0 (холодно, сканировать редко) → 1.0 (горячо, сканировать часто)
- **Интервал сканирования**:
  - Heat 1.0 (горячо) → 5 секунд
  - Heat 0.0 (холодно) → 300 секунд (5 минут)

---

#### `/src/api/routes/watcher_routes.py` - REST API (MARKER_90.5.0, 90.5.1, 90.6)

**Эндпоинт: `POST /api/watcher/add`**
- **Параметры**: `path`, `recursive` (опционально, default: True)
- **MARKER_90.5.0_FIX - Получение Qdrant Client** (3 попытки):
  ```python
  # Попытка 1: app.state.qdrant_manager
  qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
  if qdrant_manager and qdrant_manager.is_ready():
      qdrant_client = qdrant_manager.client

  # Попытка 2: memory_manager.qdrant_client ← ЭТО РАБОТАЕТ (per Kimi K2)
  if not qdrant_client:
      memory_manager = getattr(request.app.state, 'memory_manager', None)
      if memory_manager and hasattr(memory_manager, 'qdrant_client'):
          qdrant_client = memory_manager.qdrant_client

  # Попытка 3: singleton из components_init
  if not qdrant_client:
      from src.memory.qdrant_client import get_qdrant_client
      qdrant_client = get_qdrant_client()
  ```

- **MARKER_90.5.1_FIX - Rescan Already Watching Directory**:
  ```python
  # Проблема: add_directory() возвращает False если уже наблюдаем
  # Решение: Явно проверить статус ДО вызова add_directory
  already_watching = path in watcher.watched_dirs
  success = watcher.add_directory(path, recursive)

  # Сканировать если: (новая директория) OR (уже наблюдаем, но пользователь явно запросил)
  should_scan = success or already_watching
  ```

- **MARKER_90.6 - Unified scan_directory()**:
  ```python
  # Вместо дублирования логики в разных местах → используем один метод
  updater = get_qdrant_updater(qdrant_client=qdrant_client)
  updater.reset_stop()  # Очистить stop флаг
  updater.updated_count = 0
  updater.skipped_count = 0

  indexed_count = updater.scan_directory(path)  # Единая реализация!
  print(f"Scan complete: {indexed_count} indexed, {updater.skipped_count} skipped")
  ```

- **Ответ**:
  ```json
  {
    "success": true,
    "watching": ["/path/to/scan", ...],
    "indexed_count": 15,
    "message": "Now watching: /path/to/scan (15 files indexed)"
  }
  ```

**Эндпоинт: `GET /api/watcher/status`**
- Возвращает: `watching`, `count`, `heat_scores`, `observers_active`

**Эндпоинт: `GET /api/watcher/heat`**
- Возвращает: `scores` (dict path→heat), `intervals` (dict path→seconds)

**Эндпоинт: `POST /api/watcher/remove`**
- Удалить директорию из слежения (не удаляет из Qdrant)

**Эндпоинт: `POST /api/watcher/add-from-browser`**
- Индексировать файлы, полученные из браузерного File System API
- Пути формируются как: `browser://rootName/relative/path`

**Эндпоинт: `POST /api/watcher/index-file`**
- Индексировать один файл по его реальному пути на диске

**Эндпоинт: `DELETE /api/watcher/cleanup-browser-files`**
- Удалить все виртуальные `browser://` файлы из Qdrant

---

#### `/src/scanners/local_scanner.py` - Утилита для обхода директорий

- **Цель**: Предоставить функции для обхода файловой системы
- **Используется**: В `scan_directory()` для получения файлов

---

#### `/data/watcher_state.json` - Состояние наблюдателя

```json
{
  "watched_dirs": ["/path/1", "/path/2"],
  "heat_scores": {
    "/path/1": 0.8,
    "/path/2": 0.2
  },
  "saved_at": 1705977600
}
```

- **Цель**: Восстановление наблюдаемых директорий при перезагрузке
- **Загружается**: При инициализации `VetkaFileWatcher`

---

### 3. ИСПРАВЛЕНИЯ BUGS (Phase 90.5.x - 90.6)

#### Bug 90.5.0 - Multi-source Qdrant Client Retrieval

**Проблема**: `qdrant_manager` часто равен None, что приводит к пропуску индексирования

**Решение**: Попытаться получить client из 3 источников подряд:
1. `request.app.state.qdrant_manager.client`
2. `request.app.state.memory_manager.qdrant_client` ← **Это работает!**
3. `get_qdrant_client()` singleton

**Файл**: `/src/api/routes/watcher_routes.py` линии 109-140

---

#### Bug 90.5.1 - Already Watching Rescan Skip

**Проблема**:
```python
if path in watcher.watched_dirs:
    return False  # add_directory() пропускает повторное добавление
# → Сканирование не происходит, даже если пользователь явно запросил
```

**Решение**:
```python
already_watching = path in watcher.watched_dirs  # Проверить ДО add_directory()
success = watcher.add_directory(path)
should_scan = success or already_watching  # Сканировать в обоих случаях
```

**Файл**: `/src/api/routes/watcher_routes.py` линии 145-155

**Улучшенное сообщение**:
```python
if success:
    message = f"Now watching: {path} ({indexed_count} files indexed)"
elif already_watching:
    message = f"Rescanned (already watching): {path} ({indexed_count} files indexed)"
else:
    message = f"Failed to watch: {path}"
```

---

#### Bug 90.6 - Unified scan_directory() Method

**Проблема**: Логика сканирования дублировалась в нескольких местах

**Решение**: Единый метод `QdrantIncrementalUpdater.scan_directory(path)`

**Реализация**:
```python
def scan_directory(self, path: str, skip_dirs: Optional[List[str]] = None) -> int:
    """
    MARKER_90.6: Унифицированный метод для Manual Scan и Watchdog.
    Использует update_file() для каждого файла (обработка проверки хеша).
    """
    import os

    if skip_dirs is None:
        skip_dirs = ['node_modules', '__pycache__', 'venv', '.venv',
                    'dist', 'build', '.git', '.idea', '.vscode']

    indexed_count = 0

    for root, dirs, files in os.walk(path):
        if self._stop_requested:
            print("[QdrantUpdater] Stop requested - aborting")
            break

        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip_dirs]

        for filename in files:
            if filename.startswith('.'):
                continue

            file_path = Path(os.path.join(root, filename))

            # Использовать update_file() - это обрабатывает все детали
            if self.update_file(file_path):
                indexed_count += 1

    return indexed_count
```

**Ключевое преимущество**: `update_file()` уже содержит логику проверки хеша, поэтому неизмененные файлы пропускаются автоматически

**Файл**: `/src/scanners/qdrant_updater.py` линии 528-573

---

### 4. КАК ИСПОЛЬЗОВАТЬ

#### 4.1 Сканировать директорию через REST API

```bash
curl -X POST http://localhost:5002/api/watcher/add \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/danilagulin/Documents/VETKA_Project", "recursive": true}'
```

**Ответ**:
```json
{
  "success": true,
  "watching": ["/Users/danilagulin/Documents/VETKA_Project"],
  "indexed_count": 142,
  "message": "Now watching: /Users/danilagulin/Documents/VETKA_Project (142 files indexed)"
}
```

#### 4.2 Пересканировать существующую наблюдаемую директорию

```bash
# Тот же эндпоинт - система автоматически распознает, что директория уже наблюдается
curl -X POST http://localhost:5002/api/watcher/add \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/danilagulin/Documents/VETKA_Project"}'
```

**Ответ**:
```json
{
  "success": true,
  "watching": ["/Users/danilagulin/Documents/VETKA_Project"],
  "indexed_count": 8,
  "message": "Rescanned (already watching): /Users/danilagulin/Documents/VETKA_Project (8 files indexed)"
}
```

Обратите внимание: `indexed_count: 8` - потому что 8 файлов изменилось, остальные 134 были пропущены (неизменены).

#### 4.3 Проверить статус наблюдателя

```bash
curl http://localhost:5002/api/watcher/status
```

**Ответ**:
```json
{
  "watching": ["/Users/danilagulin/Documents/VETKA_Project"],
  "count": 1,
  "heat_scores": {
    "/Users/danilagulin/Documents/VETKA_Project": 0.65
  },
  "observers_active": 1
}
```

#### 4.4 Получить Heat Scores (частота сканирования)

```bash
curl http://localhost:5002/api/watcher/heat
```

**Ответ**:
```json
{
  "scores": {
    "/Users/danilagulin/Documents/VETKA_Project": 0.65
  },
  "intervals": {
    "/Users/danilagulin/Documents/VETKA_Project": 140
  }
}
```

Heat 0.65 → интервал 140 сек (сканировать каждые 2-3 минуты)

#### 4.5 Остановить наблюдение за директорией

```bash
curl -X POST http://localhost:5002/api/watcher/remove \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/danilagulin/Documents/VETKA_Project"}'
```

---

### 5. ПРЕДОТВРАЩЕНИЕ ДУПЛИКАТОВ

#### Детерминированный UUID5

```python
point_id = uuid.uuid5(uuid.NAMESPACE_DNS, file_path).int & 0x7FFFFFFFFFFFFFFF
```

**Свойства**:
- **Детерминированность**: Одинаковый path → одинаковый ID всегда
- **Коллизия-безопасность**: Разные пути → разные IDs (99.99...%)
- **Воспроизводимость**: Не требует генератора случайных чисел

#### Qdrant Upsert

```python
self.client.upsert(
    collection_name=self.collection_name,
    points=[point]  # PointStruct с id, vector, payload
)
```

**Поведение**:
- Если point.id существует → обновить vector и payload
- Если point.id не существует → вставить новую точку
- **Результат**: Никогда не будет дубликатов

#### Hash-Based Change Detection

```python
new_hash = hashlib.sha256(file_content).hexdigest()
old_hash = existing_point.payload.get('content_hash', '')

if new_hash == old_hash:
    # Пропустить переиндексирование
    self.skipped_count += 1
    return False
else:
    # Переиндексировать с новым embedding
    return self.update_file(file_path)
```

**Результат**: Большие сканирования работают очень быстро (пропуск неизменяемых файлов)

---

### 6. МАРКЕРЫ В КОДЕ

| Маркер | Файл | Назначение |
|--------|------|-----------|
| `MARKER_90.6` | `qdrant_updater.py:528-573` | Унифицированный `scan_directory()` |
| `MARKER_90.5.1_FIX` | `watcher_routes.py:145-155` | Rescan already watching directory |
| `MARKER_90.5.0_FIX` | `watcher_routes.py:109-140` | Multi-source Qdrant client |
| `MARKER_90.3` | `file_watcher.py:384-404` | Retry logic for Qdrant |
| `MARKER_80.17` | `file_watcher.py:487-518` | Lazy fetch Qdrant client |
| `MARKER_80.20` | `file_watcher.py:440-485` | Fix async emit from sync context |
| `MARKER_80.15` | `file_watcher.py:265-438` | Queue-based emit for thread safety |

---

### 7. БУДУЩИЕ УЛУЧШЕНИЯ (из анализа Grok)

- [ ] **Retry Queue** - Очередь переиндексирования для файлов с ошибками
  - Файлы, которые не удалось индексировать → в очередь
  - Периодическая переиндексация (каждые N минут)
  - Экспоненциальная задержка (первая попытка через 1 сек, вторая через 2 сек, etc)

- [ ] **FileProcessor Class Extraction** - Выделить логику обработки файлов
  - Текущая реализация: все в `update_file()`
  - Предложение: Создать отдельный класс `FileProcessor` с методами:
    - `process_python_file()`
    - `process_markdown_file()`
    - `process_json_file()`
  - Позволит кастомизировать индексирование по типам файлов

- [ ] **Background Retry Handler Thread** - Фоновый поток для переиндексирования
  - Текущее: Синхронная обработка в эндпоинтах и обработчиках
  - Предложение: Отдельный поток, который обрабатывает очередь переиндексирования
  - Улучшит отзывчивость API (не блокировать пользователя)

- [ ] **Batch Size Optimization** - Оптимизировать размер батчей
  - Текущее: `batch_update()` обновляет ВСЕ файлы одним batches
  - Предложение: Разбить на пакеты (например, по 100 файлов)
  - Позволит обрабатывать огромные директории без перегрузки памяти

- [ ] **Priority Scheduling** - Приоритетная очередь индексирования
  - Текущее: Все файлы обрабатываются в порядке `os.walk()`
  - Предложение: Приоритизировать по расширению (.py → .js → .md → бинарные)
  - Результат: Важные файлы индексируются быстрее

---

### 8. СТАТИСТИКА И МЕТРИКИ

#### Пример вывода логов

```
[QdrantUpdater] Updated: main.py
[QdrantUpdater] Skipped (unchanged): config.py
[QdrantUpdater] Skipped (unchanged): utils.py
[QdrantUpdater] Updated: README.md
[QdrantUpdater] Directory scan complete: 8 files indexed from /Users/danilagulin/Documents/VETKA_Project

[Watcher] modified: /Users/danilagulin/Documents/VETKA_Project/src/main.py
[Watcher] Phase 90.3: Lazy fetched qdrant_client from components_init
[Watcher] ✅ Indexed to Qdrant: /Users/danilagulin/Documents/VETKA_Project/src/main.py
[Watcher] Emitted node_updated: /Users/danilagulin/Documents/VETKA_Project/src/main.py
```

#### Получение статистики

```python
from src.scanners.qdrant_updater import get_qdrant_updater

updater = get_qdrant_updater()
stats = updater.get_stats()
print(stats)
# {
#   'updated_count': 8,
#   'skipped_count': 134,
#   'deleted_count': 0,
#   'error_count': 0,
#   'collection': 'vetka_elisya',
#   'stop_requested': False
# }
```

---

### 9. ИНСТРУМЕНТИРОВАНИЕ И ОТЛАДКА

#### Включить расширенное логирование

```python
# В коде перед сканированием:
import logging
logging.basicConfig(level=logging.DEBUG)

updater = get_qdrant_updater(qdrant_client=client)
updater.reset_stop()
indexed = updater.scan_directory("/path/to/scan")
stats = updater.get_stats()
print(f"Stats: {stats}")
```

#### Мониторить Qdrant в реальном времени

```bash
# Terminal 1: Запустить VETKA
python main.py

# Terminal 2: Проверить количество точек в коллекции
python -c "
from qdrant_client import QdrantClient
client = QdrantClient('localhost', port=6333)
info = client.get_collection('vetka_elisya')
print(f'Points in collection: {info.points_count}')
"
```

#### Отследить события в браузере

```javascript
// В браузерной консоли:
socket.on('directory_scanned', (data) => {
  console.log('Directory scanned:', data);
  // {path: "/path", files_count: 142, root_name: "vetka_live_03"}
});

socket.on('node_updated', (data) => {
  console.log('File updated:', data.path);
});

socket.on('tree_bulk_update', (data) => {
  console.log('Bulk update detected:', data.count, 'events');
});
```

---

### 10. ИНТЕГРАЦИЯ С ДРУГИМИ КОМПОНЕНТАМИ

#### Как Scanner интегрируется с Tree Router

```
Scanner (qdrant_updater) создает PointStruct в Qdrant
    ↓
TreeRouter.get_vector_space() запрашивает точки из Qdrant
    ↓
TreeRouter строит 3D дерево на основе embeddings
    ↓
Frontend отображает сканированные файлы в 3D пространстве
```

**Ключевое поле**: `payload['type'] = 'scanned_file'`
- TreeRouter ищет точки с этим типом
- Использует payload метаданные для построения структуры

#### Как Scanner интегрируется с MCP Bridge

```
Scanner индексирует локальные файлы в Qdrant
    ↓
MCP Bridge предоставляет инструменты для поиска через Qdrant
    ↓
Grok/Claude могут искать файлы семантически
```

---

### 11. ПРОИЗВОДИТЕЛЬНОСТЬ И ОПТИМИЗАЦИЯ

#### Benchmark (примерно)

| Операция | Время | Примечание |
|----------|-------|-----------|
| Сканирование 100 файлов (новых) | 2-3 сек | Включает embedding |
| Пересканирование 100 файлов (10 изменено) | 500ms | Пропускаются 90 неизменяемых |
| Добавить директорию на наблюдение | <100ms | Только создание Observer |
| Watchdog событие → Qdrant upsert | 200-400ms | Debouncing + embedding |

#### Оптимизация памяти

- **Не загружать весь файл в память**: Читать первые 8000 символов для embedding
- **Не хранить весь контент в Qdrant**: Хранить preview (500 символов)
- **Batch операции**: Собрать множество файлов перед upsert

#### Оптимизация CPU

- **Debouncing (400ms)**: Предотвратить переиндексирование каждого события
- **Hash-based skipping**: Не переиндексировать неизменяемые файлы
- **Parallel embeddings**: (TODO Phase 90.4) Использовать многопроцессность

---

### Итоговая диаграмма взаимодействия

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                    │
│ (3D Tree Viewer, File List)                                │
└────────────────────┬──────────────────────────────────────┘
                     │
         Socket.IO Events (directory_scanned, node_updated)
                     │
┌────────────────────▼──────────────────────────────────────┐
│ BACKEND - FastAPI Routes                                   │
│ POST /api/watcher/add                                      │
│ GET /api/watcher/status                                    │
│ DELETE /api/watcher/cleanup-browser-files                  │
└────────────────────┬──────────────────────────────────────┘
                     │
         Логика маршрутизации (watcher_routes.py)
                     │
    ┌────────────────┴────────────────┬──────────────────┐
    │                                 │                  │
┌───▼─────────────────┐   ┌──────────▼────────┐   ┌─────▼──────────────┐
│ VetkaFileWatcher    │   │ QdrantUpdater     │   │ Qdrant Client      │
│ (file_watcher.py)   │   │ (qdrant_updater)  │   │ (Vector DB)        │
│                     │   │                    │   │                    │
│ • Observer creation │   │ • scan_directory   │   │ • upsert points    │
│ • Event debouncing  │   │ • update_file      │   │ • hash comparison  │
│ • Heat tracking     │   │ • _file_changed    │   │ • embedding store  │
│ • Socket.IO emit    │   │ • _get_embedding   │   │                    │
└─────────────────────┘   └────────────────────┘   └────────────────────┘
    │                              │                      │
    │    Watchdog Events           │   Embedding          │
    │    (create/modify/delete)    │   Generation         │
    │                              │   (EmbeddingService) │
    └──────────────────────────────┴──────────────────────┘
            │
    ┌───────▼────────┐
    │ File System    │
    │ Changes        │
    └────────────────┘
```

---

### Итоги

**Phase 90.5-90.6** объединяет все компоненты сканирования в единую, чистую архитектуру:

1. **Унификация**: Одна логика (`scan_directory()`) для ручного и реал-тайм сканирования
2. **Надежность**: Multi-source Qdrant client retrieval + retry logic
3. **Эффективность**: Hash-based change detection предотвращает переиндексирование
4. **Масштабируемость**: Batch operations и adaptive frequency scaling

Система готова к интеграции в production и будущим улучшениям (retry queue, parallel processing, priority scheduling).
