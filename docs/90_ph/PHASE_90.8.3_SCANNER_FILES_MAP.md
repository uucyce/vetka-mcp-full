# PHASE 90.8.3 - КАРТА ФАЙЛОВ СКАНЕРОВ И ИНДЕКСИРОВАНИЯ QDRANT

**Дата:** 2026-01-23
**Статус:** ACTIVE
**Версия:** 1.0

---

## 📋 ОБЗОР

Полная карта всех файлов, связанных с:
- **Сканированием** файловой системы (scanner)
- **Отслеживанием** файлов в реальном времени (watcher)
- **Индексированием** в Qdrant (qdrant_updater)

---

## 🔧 ЯДРО: СИСТЕМА СКАНИРОВАНИЯ (SCANNERS)

### 1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/base_scanner.py`

**Назначение:** Абстрактный базовый класс для всех сканеров зависимостей
**Фаза:** 72.1 (Foundation)

**Ключевые классы:**
- `BaseScanner` - ABC для всех типов сканеров

**Ключевые функции:**
- `supported_extensions` - Set расширений файлов для сканирования
- `extract_dependencies()` - Извлечение зависимостей из содержимого файла
- `can_scan()` - Проверка, может ли сканер обработать файл
- `validate_content()` - Валидация содержимого перед сканированием
- `scan_file()` - Высокоуровневое сканирование с валидацией

**Зависимости импорта:**
```python
from .dependency import Dependency
from .exceptions import UnsupportedFileTypeError
```

---

### 2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/python_scanner.py`

**Назначение:** AST-based сканер зависимостей Python
**Фаза:** 72.3 (Python Scanner Implementation)

**Ключевые классы:**
- `PythonScanner(BaseScanner)` - Сканер Python-кода с AST парсингом
- `ExtractedImport` - Dataclass сырого импорта до разрешения

**Ключевые функции:**
- `extract_dependencies()` - Извлечение Python импортов и разрешение путей
- `_extract_imports_from_ast()` - Парсинг AST и сбор импортов
- `_resolve_import()` - Разрешение импорта к файловому пути
- `_find_type_checking_lines()` - Поиск TYPE_CHECKING блоков
- `_check_dynamic_import()` - Обнаружение динамических импортов
- `extract_imports_only()` - Извлечение сырых импортов без разрешения
- `get_statistics()` - Статистика сканера

**Зависимости импорта:**
```python
from .base_scanner import BaseScanner
from .dependency import Dependency, DependencyType
from .exceptions import ParseError
from .import_resolver import ImportResolver, ResolvedImport
from .known_packages import is_external_package
```

**Статистика:** 1,156 абсолютных импортов, 160 относительных, 4 динамических

---

### 3. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/local_scanner.py`

**Назначение:** Локальный сканер файловой системы для индексирования содержимого
**Фаза:** 12

**Ключевые классы:**
- `LocalScanner` - Сканер локальных директорий
- `ScannedFile` - Dataclass отсканированного файла с метаданными

**Ключевые функции:**
- `scan()` - Generator для итерации по файлам
- `_scan_file()` - Сканирование одного файла
- `_read_content()` - Чтение содержимого файла с поддержкой энкодингов
- `get_stats()` - Статистика сканирования

**Поддерживаемые расширения:**
```python
.md, .txt, .py, .js, .ts, .jsx, .tsx, .json, .yaml, .yml, .html, .css,
.scss, .sh, .bash, .zsh, .sql, .graphql, .xml, .csv, .ini, .cfg, .conf,
.env, .rst, .org, .wiki
```

**Исключённые директории:**
```python
.git, .svn, .hg, node_modules, __pycache__, .venv, venv, env,
dist, build, .idea, .vscode, .DS_Store, vendor, target
```

---

### 4. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/local_project_scanner.py`

**Назначение:** Сканер локального проекта для создания данных формата Phase 9
**Фаза:** 9

**Ключевые классы:**
- `LocalProjectScanner` - Сканер проектной структуры

**Ключевые функции:**
- `scan()` - Сканирование директории и возврат Phase 9 formatted data
- `_walk_safe()` - Безопасное обхождение дерева с защитой от symlinks
- `_should_ignore()` - Проверка игнорирования пути
- `_detect_lang()` - Обнаружение языка по расширению
- `_is_test()` - Проверка, является ли файл тестом

**Защита:** Лимиты файлов, директорий, глубины и защита от symlinks (Haiku bug #6)

---

### 5. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/known_packages.py`

**Назначение:** База известных внешних пакетов для фильтрации при сканировании

**Функции:**
- `is_external_package()` - Проверка, является ли пакет внешним

---

## 👀 СИСТЕМА ОТСЛЕЖИВАНИЯ: WATCHER

### 6. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py`

**Назначение:** Мониторинг файловой системы в реальном времени с помощью watchdog
**Фаза:** 90.3

**Ключевые классы:**
- `VetkaFileHandler(FileSystemEventHandler)` - Обработчик событий с debouncing (400ms)
- `AdaptiveScanner` - Адаптивная частота сканирования на основе активности
- `VetkaFileWatcher` - Главный класс наблюдателя

**Ключевые функции (VetkaFileWatcher):**
- `add_directory()` - Добавить директорию в список отслеживания
- `remove_directory()` - Удалить директорию из отслеживания
- `_on_file_change()` - Обработчик события изменения файла
- `_emit()` - Thread-safe Socket.IO emit
- `_get_qdrant_client()` - Ленивое получение клиента Qdrant (Phase 90.7)
- `_save_state()` - Сохранение состояния отслеживания
- `load_state()` - Восстановление состояния при запуске
- `stop_all()` - Остановка всех наблюдателей
- `add_browser_directory()` - Отслеживание виртуальных директорий из браузера
- `get_status()` - Получение статуса наблюдателя

**Функции (AdaptiveScanner):**
- `get_scan_interval()` - Интервал сканирования на основе heat score
- `update_heat()` - Обновление heat score на события
- `decay_all()` - Затухание heat scores

**Интеграция с Qdrant:**
```python
from src.scanners.qdrant_updater import handle_watcher_event
```

**Синглтон:**
```python
def get_watcher(socketio, qdrant_client, use_emit_queue) -> VetkaFileWatcher
```

**Поддерживаемые расширения:**
```python
.py, .js, .ts, .jsx, .tsx, .json, .yaml, .yml, .md, .txt, .html, .css,
.scss, .sql, .sh, .java, .go, .rs, .rb, .php, .c, .cpp, .h, .swift,
.kt, .scala, .vue, .svelte
```

---

## 📦 ОБНОВЛЕНИЕ QDRANT

### 7. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/qdrant_updater.py`

**Назначение:** Эффективное инкрементальное обновление Qdrant на основе событий FS
**Фаза:** 54

**Ключевые классы:**
- `QdrantIncrementalUpdater` - Инкрементальное обновление с hash-сравнением

**Ключевые функции:**
- `update_file()` - Обновление одного файла (с проверкой изменений)
- `batch_update()` - Batch обновление нескольких файлов
- `soft_delete()` - Мягкое удаление (маркировка как удалено)
- `hard_delete()` - Полное удаление из Qdrant
- `cleanup_deleted()` - Удаление старых мягко-удалённых файлов
- `scan_directory()` - Сканирование директории и индексирование (Phase 90.6)
- `request_stop()` - Запрос остановки сканирования (Phase 83)
- `reset_stop()` - Сброс флага остановки
- `is_stop_requested()` - Проверка флага остановки
- `get_stats()` - Статистика обновления

**Интеграция:**
```python
def handle_watcher_event(event, qdrant_client) -> bool
def get_qdrant_updater(qdrant_client, collection_name) -> QdrantIncrementalUpdater
```

**Особенности:**
- Hash-based change detection (только изменённые файлы)
- Content hash сравнение перед переиндексацией
- Soft delete support
- Batch upsert для эффективности
- Stop flag для прерывания сканирования (Phase 83)
- Unified scan_directory для Manual Scan и Watchdog (Phase 90.6)

---

## 🔌 API И ИНТЕГРАЦИЯ

### 8. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py`

**Назначение:** FastAPI маршруты для управления watcher
**Фаза:** 54.3

**Endpoints:**
- `POST /api/watcher/add` - Добавить директорию на мониторинг
- `POST /api/watcher/add-from-browser` - Добавить файлы из браузера
- `POST /api/watcher/remove` - Удалить директорию
- `GET /api/watcher/status` - Статус наблюдателя
- `GET /api/watcher/heat` - Heat scores адаптивного сканера

**Зависимости импорта:**
```python
from src.scanners.file_watcher import get_watcher
from src.scanners.qdrant_updater import get_qdrant_updater
```

**Pydantic Models:**
- `AddWatchRequest` - Запрос добавления директории
- `RemoveWatchRequest` - Запрос удаления
- `BrowserFileInfo` - Информация файла из браузера
- `AddFromBrowserRequest` - Запрос добавления файлов из браузера

---

### 9. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py`

**Назначение:** Production Qdrant клиент для VETKA с Triple Write atomicity
**Фаза:** 7.2

**Ключевые классы:**
- `QdrantVetkaClient` - Главный клиент для работы с Qdrant
- `VetkaTreeNode` - Иерархический узел в VetkaTree
- `VetkaChangeLogEntry` - Запись аудита для ChangeLog

**Collections:**
```python
'tree': 'VetkaTree'         # Иерархическое хранилище
'leaf': 'VetkaLeaf'         # Детали
'changelog': 'VetkaChangeLog'  # Аудит
'trash': 'VetkaTrash'       # Deleted (Phase 77)
```

**Vector Size:** 768

---

### 10. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/utils/qdrant_utils.py`

**Назначение:** Утилиты для работы с Qdrant (host, port, URL)
**Фаза:** 38.1

**Ключевые функции:**
- `get_qdrant_host()` - Auto-detect хоста (env, localhost, docker)
- `get_qdrant_port()` - Получение порта (default 6333)
- `get_qdrant_url()` - Полный URL (http://host:port)

---

## 🔍 ИМПОРТЁРЫ И ЗАВИСИМОСТИ

### 11. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py`

**Назначение:** Production FastAPI приложение
**Фаза:** 39.8

**Инициализация сканеров/watcher при запуске:**
```python
from src.initialization import initialize_all_components
```

**Компоненты:**
- `qdrant_manager` - Менеджер Qdrant
- `memory_manager` - Менеджер памяти с qdrant_client
- Инициализирует все компоненты в lifespan

---

### 12. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/files_routes.py`

**Назначение:** API маршруты для работы с файлами

**Интеграция:**
```python
from src.scanners.file_watcher import get_watcher
```

---

### 13. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/semantic_routes.py`

**Назначение:** API маршруты семантического поиска

**Интеграция:**
```python
from src.utils.qdrant_utils import get_qdrant_url
```

---

### 14. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py`

**Назначение:** Debug маршруты

**Интеграция:**
Использует компоненты инициализации

---

### 15. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/tree_routes.py`

**Назначение:** API маршруты для работы с VetkaTree

**Интеграция:**
Использует Qdrant клиент

---

## 📝 ДОПОЛНИТЕЛЬНЫЕ ФАЙЛЫ

### 16. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scan_81_ph_to_qdrant.py`

**Назначение:** Скрипт сканирования фазы 81 и индексирования в Qdrant

**Интеграция:**
```python
from src.scanners.qdrant_updater import QdrantIncrementalUpdater
```

---

### 17. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_auto_retry.py`

**Назначение:** Auto-retry логика для операций с Qdrant

**Интеграция:**
Обёртка для надёжности операций Qdrant

---

### 18. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/watcher_state.json`

**Назначение:** Сохранённое состояние наблюдателя

**Содержимое:**
```json
{
  "watched_dirs": ["path1", "path2"],
  "heat_scores": {"dir": 0.5},
  "saved_at": 1234567890
}
```

---

## 🔗 ГРАФ ЗАВИСИМОСТЕЙ

```
main.py (инициализация)
  ├─> initialize_all_components()
  │   └─> components_init.py
  │       ├─> get_qdrant_manager()
  │       ├─> get_memory_manager()
  │       └─> VetkaMemory.qdrant_client
  │
  ├─> watcher_routes.py
  │   ├─> get_watcher() [singleton]
  │   │   ├─> VetkaFileWatcher
  │   │   │   ├─> VetkaFileHandler (debounce 400ms)
  │   │   │   ├─> AdaptiveScanner
  │   │   │   └─> handle_watcher_event()
  │   │   │       └─> get_qdrant_updater() [singleton]
  │   │   │           └─> QdrantIncrementalUpdater
  │   │   │               ├─> hash-based change detection
  │   │   │               ├─> batch_update()
  │   │   │               └─> scan_directory()
  │   │   │
  │   │   └─> _get_qdrant_client() [Phase 90.7]
  │   │       ├─> get_qdrant_manager().client
  │   │       ├─> get_memory_manager().qdrant_client
  │   │       └─> get_qdrant_client() [singleton]
  │   │
  │   └─> get_qdrant_updater()
  │
  ├─> files_routes.py
  │   └─> get_watcher()
  │
  ├─> semantic_routes.py
  │   └─> get_qdrant_url()
  │       ├─> get_qdrant_host()
  │       └─> get_qdrant_port()
  │
  └─> debug_routes.py
      └─> components initialization
```

---

## 🎯 ПОТОКИ ДАННЫХ

### Поток 1: Real-Time Watcher (Watchdog Event → Qdrant)
```
FileSystem Event (fs.Event)
  ↓
VetkaFileHandler.on_any_event()
  ↓ [debounce 400ms]
VetkaFileHandler._process_batch()
  ↓
VetkaFileWatcher._on_file_change()
  ├─> Update heat scores
  ├─> Emit Socket.IO events
  └─> handle_watcher_event()
      ↓
      QdrantIncrementalUpdater
      ├─> Check content hash
      ├─> Read file
      ├─> Generate embedding
      └─> Upsert to Qdrant
```

### Поток 2: Manual Directory Scan (LocalScanner → Qdrant)
```
scan_directory(path)
  ↓
LocalScanner.scan()
  ↓ [for each file]
QdrantIncrementalUpdater.update_file()
  ├─> Check hash
  ├─> Generate embedding
  └─> Upsert to Qdrant
```

### Поток 3: Python Dependency Scanner (PythonScanner)
```
extract_dependencies(file_content)
  ↓
PythonScanner._extract_imports_from_ast()
  ├─> Parse with ast module
  └─> Detect TYPE_CHECKING, dynamic imports
  ↓
PythonScanner._resolve_import()
  ├─> Use ImportResolver
  └─> Match to file paths
  ↓
Create Dependency objects
```

---

## ⚙️ КОНФИГУРАЦИЯ

### Qdrant Connection (env variables)
- `QDRANT_HOST` - Host (default: 127.0.0.1)
- `QDRANT_PORT` - Port (default: 6333)

### Watcher Configuration
- Debounce: 400ms
- Max scan interval: 300s (холодные директории)
- Min scan interval: 5s (горячие директории)
- Decay factor: 0.95 (hourly)

### Scanner Limits (in config/design_system.py)
- `max_files` - Максимум файлов для сканирования
- `max_depth` - Максимальная глубина директорий
- `max_directories` - Максимум директорий
- `max_items_per_dir` - Макс элементов в директории

---

## 📊 СТАТИСТИКА

### Python Scanner (из audit)
- **Абсолютных импортов:** 1,156
- **Относительных импортов:** 160
- **Динамических импортов:** 4
- **Условных импортов (TYPE_CHECKING):** 3

### LocalScanner
- Max file size: 1MB per file
- Default max files: 10,000

### Qdrant Updater
- Vector size: 768 (embeddings)
- Content preview: 500 chars
- Delete cleanup: 24 hours default

---

## 🚀 ФАЗОВЫЕ МАРКЕРЫ

| Фаза | Компонент | Описание |
|------|-----------|---------|
| 7.2 | qdrant_client.py | Triple Write atomicity |
| 9 | local_project_scanner.py | Phase 9 format data |
| 12 | local_scanner.py | Local FS scanning |
| 38.1 | qdrant_utils.py | Auto-detect host/port |
| 39.8 | main.py | FastAPI production |
| 54 | qdrant_updater.py | Incremental updates |
| 54.3 | watcher_routes.py | API endpoints |
| 72.1 | base_scanner.py | ABC foundation |
| 72.3 | python_scanner.py | AST-based Python |
| 77 | (trash) | Trash collection |
| 80.15 | file_watcher.py | Queue-based emit |
| 80.17 | file_watcher.py | Lazy Qdrant client |
| 80.20 | file_watcher.py | Async emit fix |
| 83 | qdrant_updater.py | Stop mechanism |
| 90.3 | file_watcher.py | Qdrant retry logic |
| 90.6 | qdrant_updater.py | Unified scan_directory |
| 90.7 | file_watcher.py | Multi-source fallback |

---

## ✅ ЗАВЕРШЕНО

Карта включает:
- ✅ Все файлы сканеров (scanner directory)
- ✅ Watcher и реал-тайм интеграция
- ✅ Qdrant updater логика
- ✅ API маршруты и интеграция
- ✅ Зависимости импорта для каждого файла
- ✅ Ключевые функции и классы
- ✅ Потоки данных и архитектура
- ✅ Фазовые маркеры
- ✅ Конфигурация и лимиты

**Документ актуален для Phase 90.8.3**
