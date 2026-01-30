# PHASE 90.8.1 - ПОЛНЫЙ РЕЕСТР API ENDPOINTS И МАРШРУТОВ

**Статус:** ACTIVE
**Дата:** 2026-01-23
**Фаза:** 90.8.1
**Описание:** Полный реестр всех API endpoint определений в VETKA с указанием префиксов маршрутизаторов и методов HTTP.

---

## Краткая статистика

| Метрика | Значение |
|---------|----------|
| **Всего файлов маршрутов** | 20 |
| **Всего endpoint'ов** | 137+ |
| **Зарегистрировано маршрутов в __init__.py** | 19 |
| **Не зарегистрировано** | 1 (approval_routes.py) |

---

## Реестр маршрутов по файлам

### 1. config_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | config_routes.py |
| **Префикс** | `/api` |
| **Tags** | config |
| **Статус** | ACTIVE (Phase 39.2) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/config` | Получить конфигурацию |
| POST | `/config` | Обновить конфигурацию |
| GET | `/mentions` | Получить доступные упоминания |
| GET | `/models/available` | Получить доступные модели |
| GET | `/tools/available` | Получить доступные инструменты |
| GET | `/reactions` | Получить доступные реакции |
| POST | `/tools/execute` | Выполнить инструмент |
| GET | `/keys/status` | Статус API ключей |
| POST | `/keys/add` | Добавить API ключ |
| POST | `/keys/detect` | Обнаружить API ключи |
| POST | `/keys/add-smart` | Умное добавление ключей |
| GET | `/keys/validate` | Валидировать ключи |
| GET | `/keys` | Получить все ключи |
| GET | `/agents/status` | Статус агентов |
| GET | `/models` | Получить модели |
| GET | `/models/categories` | Получить категории моделей |

---

### 2. metrics_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | metrics_routes.py |
| **Префикс** | `/api/metrics` |
| **Tags** | metrics |
| **Статус** | ACTIVE (Phase 39.2) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/dashboard` | Дашборд метрик |
| GET | `/timeline/{workflow_id}` | Временная шкала workflow |
| GET | `/agents` | Метрики агентов |
| GET | `/models` | Метрики моделей |
| GET | `/providers` | Метрики провайдеров |
| GET | `/feedback` | Метрики обратной связи |

---

### 3. files_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | files_routes.py |
| **Префикс** | `/api/files` |
| **Tags** | files |
| **Статус** | ACTIVE (Phase 54.6) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| POST | `/read` | Прочитать содержимое файла |
| POST | `/save` | Сохранить файл |
| GET | `/raw` | Получить сырое содержимое файла |
| POST | `/resolve-path` | Разрешить путь файла (drag & drop) |
| POST | `/open-in-finder` | Открыть файл в Finder |

---

### 4. tree_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | tree_routes.py |
| **Префикс** | `/api/tree` |
| **Tags** | tree |
| **Статус** | ACTIVE (Phase 39.3) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/data` | Главные данные дерева (FAN layout) |
| POST | `/clear-semantic-cache` | Очистить семантический кэш |
| GET | `/export/blender` | Экспортировать в Blender |
| POST | `/clear-knowledge-cache` | Очистить кэш графа знаний |

---

### 5. eval_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | eval_routes.py |
| **Префикс** | `/api/eval` |
| **Tags** | eval |
| **Статус** | ACTIVE (Phase 39.4) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| POST | `/score` | Оценить вывод агента |
| POST | `/score/with-retry` | Оценить с автоматическим повтором |
| GET | `/history` | История оценок |
| GET | `/stats` | Статистика оценок |
| POST | `/feedback/submit` | Отправить обратную связь |

---

### 6. semantic_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | semantic_routes.py |
| **Префикс** | `/api` |
| **Tags** | semantic |
| **Статус** | ACTIVE (Phase 68) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/semantic-tags/search` | Поиск по семантическим тегам |
| GET | `/semantic-tags/available` | Доступные семантические теги |
| GET | `/file/{file_id}/auto-tags` | Автотеги для файла |
| GET | `/search/semantic` | Универсальный семантический поиск |
| POST | `/search/weaviate` | Гибридный поиск Weaviate |
| GET | `/search/hybrid` | Гибридный поиск с RRF fusion |
| GET | `/search/hybrid/stats` | Статистика гибридного поиска |
| POST | `/scanner/rescan` | Переканировать файлы |
| POST | `/scanner/stop` | Остановить сканер |
| GET | `/scanner/status` | Статус сканера |
| DELETE | `/scanner/clear-all` | Очистить всё |

---

### 7. chat_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | chat_routes.py |
| **Префикс** | `/api` |
| **Tags** | chat |
| **Статус** | ACTIVE (Phase 39.5) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/chat/history` | История чатов для узла |
| POST | `/chat/clear-history` | Очистить историю чатов |
| POST | `/chat` | **ГЛАВНЫЙ CHAT ENDPOINT** |

---

### 8. chat_history_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | chat_history_routes.py |
| **Префикс** | `/api` |
| **Tags** | chat-history |
| **Статус** | ACTIVE (Phase 50) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/chats` | Список всех чатов (для sidebar) |
| GET | `/chats/{chat_id}` | Получить чат с сообщениями |
| POST | `/chats/{chat_id}/messages` | Добавить сообщение |
| DELETE | `/chats/{chat_id}` | Удалить чат |
| PATCH | `/chats/{chat_id}` | Обновить чат |
| GET | `/chats/file/{file_path:path}` | Чаты для файла |
| GET | `/chats/search/{query}` | Поиск сообщений |
| POST | `/chats` | Создать чат |
| GET | `/chats/{chat_id}/export` | Экспортировать чат |

---

### 9. knowledge_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | knowledge_routes.py |
| **Префикс** | `/api` |
| **Tags** | knowledge |
| **Статус** | ACTIVE (Phase 39.5) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| POST | `/knowledge-graph/build` | Построить граф знаний |
| GET | `/knowledge-graph/for-tag` | Граф знаний для тега |
| POST | `/arc/suggest` | Сгенерировать ARC suggestions |
| GET | `/arc/status` | Статус ARC Solver |
| POST | `/qdrant/deduplicate` | Удалить дубликаты Qdrant |
| POST | `/branch/create` | Создать ветку |
| POST | `/branch/context` | Контекст ветки |
| POST | `/vetka/create` | Создать VETKA дерево |
| GET | `/messages/counts` | Подсчёт сообщений |

---

### 10. ocr_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | ocr_routes.py |
| **Префикс** | `/api/ocr` |
| **Tags** | ocr |
| **Статус** | ACTIVE (Phase 39.6) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/status` | Статус OCR процессора |
| POST | `/reset` | Сбросить OCR процессор |
| POST | `/cache/clear` | Очистить OCR кэш |
| POST | `/process` | Обработать изображение/PDF |

---

### 11. file_ops_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | file_ops_routes.py |
| **Префикс** | `/api/file` |
| **Tags** | file_ops |
| **Статус** | ACTIVE (Phase 39.6) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| POST | `/show-in-finder` | Показать файл в Finder |

---

### 12. triple_write_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | triple_write_routes.py |
| **Префикс** | `/api/triple-write` |
| **Tags** | triple-write |
| **Статус** | ACTIVE (Phase 39.6) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/stats` | Статистика Triple Write |
| POST | `/cleanup` | Очистить данные оценок |
| POST | `/reindex` | Переиндексировать файлы |

---

### 13. workflow_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | workflow_routes.py |
| **Префикс** | `/api/workflow` |
| **Tags** | workflow |
| **Статус** | ACTIVE (Phase 39.6) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/history` | История workflow |
| GET | `/stats` | Статистика workflow |
| GET | `/{workflow_id}` | Деталь workflow |

---

### 14. embeddings_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | embeddings_routes.py |
| **Префикс** | `/api/embeddings` |
| **Tags** | embeddings |
| **Статус** | ACTIVE (Phase 39.6) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| POST | `/project` | Проецировать embeddings в 3D |
| POST | `/project-vetka` | Проецировать в VETKA 3D формат |
| POST | `/cluster` | Вычислить кластеры |

---

### 15. health_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | health_routes.py |
| **Префикс** | `/api` |
| **Tags** | health |
| **Статус** | ACTIVE (Phase 43) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/health/deep` | Глубокая проверка здоровья |
| GET | `/health/ready` | Kubernetes readiness probe |
| GET | `/health/live` | Kubernetes liveness probe |
| GET | `/metrics` | Метрики (health_routes) |
| GET | `/metrics/requests` | Метрики запросов |
| GET | `/metrics/llm` | Метрики LLM |
| GET | `/health/debug` | Отладка здоровья |

---

### 16. watcher_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | watcher_routes.py |
| **Префикс** | `/api/watcher` |
| **Tags** | watcher |
| **Статус** | ACTIVE (Phase 54.3) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| POST | `/add` | Добавить директорию в watch list |
| POST | `/remove` | Удалить из watch list |
| GET | `/status` | Статус watcher |
| GET | `/heat` | Scores адаптивного сканера |
| POST | `/add-from-browser` | Добавить файлы из браузера |
| POST | `/stop-all` | Остановить все watchers |
| POST | `/index-file` | Индексировать файл |
| DELETE | `/cleanup-browser-files` | Очистить браузер файлы |

---

### 17. model_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | model_routes.py |
| **Префикс** | `/api/models` |
| **Tags** | models |
| **Статус** | ACTIVE (Phase 56) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `` | Получить все модели |
| GET | `/available` | Доступные модели |
| GET | `/local` | Локальные модели |
| GET | `/free` | Бесплатные модели |
| GET | `/favorites` | Избранные модели |
| GET | `/recent` | Недавние модели |
| POST | `/favorites/{model_id}` | Добавить в избранные |
| DELETE | `/favorites/{model_id}` | Удалить из избранных |
| POST | `/keys` | Добавить ключ модели |
| DELETE | `/keys/{provider}` | Удалить ключ провайдера |
| GET | `/select` | Выбрать модель |
| POST | `/health/{model_id}` | Проверка здоровья модели |
| GET | `/mcp-agents` | MCP агенты |

---

### 18. group_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | group_routes.py |
| **Префикс** | `/api/groups` |
| **Tags** | groups |
| **Статус** | ACTIVE (Phase 56) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `` | Получить все группы |
| POST | `` | Создать группу |
| GET | `/{group_id}` | Получить группу |
| POST | `/{group_id}/participants` | Добавить участника |
| DELETE | `/{group_id}/participants/{agent_id}` | Удалить участника |
| PATCH | `/{group_id}/participants/{agent_id}/model` | Изменить модель участника |
| PATCH | `/{group_id}/participants/{agent_id}/role` | Изменить роль участника |
| GET | `/{group_id}/messages` | Сообщения группы |
| POST | `/{group_id}/messages` | Отправить сообщение |
| POST | `/{group_id}/tasks` | Создать задачу |
| POST | `/{group_id}/models/add-direct` | Добавить модель напрямую |

---

### 19. debug_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | debug_routes.py |
| **Префикс** | `/api/debug` |
| **Tags** | debug |
| **Статус** | ACTIVE (Phase 80.3) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/inspect` | Полное состояние дерева |
| GET | `/formulas` | Формулы и значения layout |
| GET | `/tree-state` | Быстрая проверка здоровья |
| GET | `/recent-errors` | Последние N ошибок |
| GET | `/logs` | Логи |
| GET | `/modes` | Состояния режимов (blend) |
| GET | `/agent-info` | Информация агента |
| POST | `/camera-focus` | Управление 3D камерой |
| GET | `/chat-context` | Контекст чата (внутренние агенты) |
| POST | `/team-message` | Сообщение команде |
| GET | `/team-messages` | Сообщения команды |
| GET | `/team-agents` | Агенты команды |
| GET | `/mcp/pending/{agent_id}` | Ожидающие MCP |
| POST | `/mcp/respond/{agent_id}` | Ответить на MCP |
| GET | `/mcp/groups` | MCP группы |
| GET | `/mcp/groups/{group_id}/messages` | Сообщения MCP группы |
| POST | `/mcp/groups/{group_id}/send` | Отправить в MCP группу |
| GET | `/mcp/mentions/{agent_id}` | Упоминания |
| POST | `/mcp/notify` | Уведомление |

---

### 20. mcp_console_routes.py

| Параметр | Значение |
|----------|----------|
| **Файл** | mcp_console_routes.py |
| **Префикс** | `/api/mcp-console` |
| **Tags** | mcp-console |
| **Статус** | ACTIVE (Phase 80.41) |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| POST | `/log` | Логировать MCP запрос/ответ |
| GET | `/history` | Получить недавние логи |
| POST | `/save` | Сохранить логи |
| DELETE | `/clear` | Очистить историю |
| GET | `/stats` | Статистика логов |

---

### 21. approval_routes.py (НЕ ЗАРЕГИСТРИРОВАН в __init__.py)

| Параметр | Значение |
|----------|----------|
| **Файл** | approval_routes.py |
| **Префикс** | `/api/approvals` |
| **Tags** | approvals |
| **Статус** | ACTIVE (Phase 55) |
| **ПРИМЕЧАНИЕ** | Этот маршрут НЕ импортирован в __init__.py |

| HTTP Method | Endpoint | Описание |
|------------|----------|----------|
| GET | `/pending` | Получить ожидающие одобрения |
| GET | `/{request_id}` | Получить запрос одобрения |
| POST | `/{request_id}/approve` | Одобрить запрос |
| POST | `/{request_id}/reject` | Отклонить запрос |
| DELETE | `/cleanup` | Очистить одобрения |

---

## Анализ и выводы

### Зарегистрированные маршруты (19)
- ✅ config_routes
- ✅ metrics_routes
- ✅ files_routes
- ✅ tree_routes
- ✅ eval_routes
- ✅ semantic_routes
- ✅ chat_routes
- ✅ chat_history_routes
- ✅ knowledge_routes
- ✅ ocr_routes
- ✅ file_ops_routes
- ✅ triple_write_routes
- ✅ workflow_routes
- ✅ embeddings_routes
- ✅ health_routes
- ✅ watcher_routes
- ✅ model_routes
- ✅ group_routes
- ✅ debug_routes

### Незарегистрированные маршруты (1)
- ❌ **approval_routes** (`/api/approvals`) - Требует добавления в __init__.py

### Распределение endpoint'ов по префиксам

| Префикс | Количество endpoints | Файлы |
|---------|--------|-------|
| `/api` | 36 | config, semantic, chat, chat_history, knowledge, health |
| `/api/metrics` | 6 | metrics |
| `/api/files` | 5 | files |
| `/api/tree` | 4 | tree |
| `/api/eval` | 5 | eval |
| `/api/ocr` | 4 | ocr |
| `/api/file` | 1 | file_ops |
| `/api/triple-write` | 3 | triple_write |
| `/api/workflow` | 3 | workflow |
| `/api/embeddings` | 3 | embeddings |
| `/api/watcher` | 8 | watcher |
| `/api/models` | 13 | model |
| `/api/groups` | 11 | group |
| `/api/debug` | 19 | debug |
| `/api/mcp-console` | 5 | mcp_console |
| `/api/approvals` | 5 | approval (не зарегистрирован) |

---

## Рекомендации

1. **Добавить approval_routes в регистрацию** - Файл существует но не импортируется в __init__.py
2. **Документирование API** - Рекомендуется использовать FastAPI автоматическую документацию (`/docs`)
3. **Аутентификация** - approval_routes использует HTTPBearer, рекомендуется применить ко всем sensitive endpoints
4. **Группировка endpoints** - Рассмотреть консолидацию с префиксом `/api/*` (текущее состояние хорошее)

---

**Сгенерировано:** 2026-01-23
**Фаза:** 90.8.1
