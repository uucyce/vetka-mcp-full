# VETKA User Test Guide — Phase 150
## Как запустить первую задачу и получить результат
**Updated: 2026-02-15**

---

## Предварительные условия

### 1. Запуск бэкенда
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python main.py
```
Бэкенд стартует на `http://localhost:5001`. Логи покажут загрузку MCP tools и Qdrant connection.

### 2. Запуск фронтенда
```bash
cd ~/Documents/VETKA_Project/vetka_live_03/client
npm run dev
```
Фронтенд стартует на `http://localhost:5173` (Vite).

### 3. Проверка здоровья
```bash
curl http://localhost:5001/api/health
```
Должен вернуть `{"status": "ok"}`.

---

## ПУТЬ 1: Быстрый тест через LeagueTester (2 минуты)

Самый быстрый способ проверить что pipeline работает.

### Шаги:
1. Открой фронтенд → **MCC** (Mycelium Command Center)
2. Внизу найди **DevPanel** (панель инструментов)
3. Перейди на вкладку **Test**
4. Нажми одну из 6 кнопок:
   - 🟢 **Dragon Bronze** — быстрый, дешёвый (Qwen Flash)
   - 🟡 **Dragon Silver** — стандартный (Qwen3-coder + GLM verifier)
   - 🔴 **Dragon Gold** — лучшее качество (Qwen-235b verifier)

### Что произойдёт:
1. Pipeline запустится с тестовой задачей: *"Add toggleBookmark to useStore.ts"*
2. `auto_write=False` — файлы НЕ будут записаны на диск (безопасно)
3. В течение 30-120 секунд увидишь результат:
   - ✅ **pass** — pipeline прошёл, код сгенерирован
   - ❌ **fail** — что-то пошло не так (ошибка покажется)
4. Статистика: subtasks, LLM calls, duration

### Где смотреть прогресс:
- Вкладка **Activity** в DevPanel — live лог pipeline событий
- Вкладка **Stats** — агрегированная статистика после завершения

---

## ПУТЬ 2: Задача через чат с @dragon (5 минут)

### Шаги:
1. Открой MCC → **чат** (основная область)
2. Напиши сообщение:
   ```
   @dragon добавь кнопку лайк в ChatPanel
   ```
3. Появится **prompt выбора**:
   - `1d` — сейчас + Dragon (немедленный запуск)
   - `2d` — в очередь + Dragon (через TaskBoard)
   - `1t` / `2t` — то же для Titan
4. Ответь `1d` для немедленного запуска

### Что произойдёт:
1. **Doctor** триажит задачу (оценивает сложность, переформулирует на English)
2. **Scout** сканирует кодовую базу, находит файлы, ставит маркеры
3. **Architect** разбивает на подзадачи
4. **Researcher** (Grok) ищет документацию
5. **Coder** пишет код (с FC loop — читает реальные файлы)
6. **Verifier** проверяет качество
7. При неудаче — retry с фидбеком, при повторной неудаче — эскалация

### Где смотреть:
- **Чат**: pipeline стримит прогресс в реальном времени
- **Activity**: подробный лог каждого шага
- **Board**: задача появится со статусом running → done/failed

### Результат:
- Файлы будут записаны в рабочую директорию
- В чате появится отчёт с кодом, вердиктом верификатора, confidence

---

## ПУТЬ 3: Workflow через DAG Editor (10 минут)

Полный pipeline через визуальный редактор workflow.

### Шаг 1: Включи Edit Mode
1. Открой MCC → переключись на **DAG View** (вкладка или кнопка визуализации)
2. Нажми кнопку **✎ edit** в тулбаре → станет "✎ editing"

### Шаг 2: Создай workflow (вариант А — AI Generate)
1. Нажми **✦ Generate**
2. Введи описание: *"Add bookmark feature to chat with store integration"*
3. AI Architect сгенерирует workflow → ноды появятся на канвасе
4. Нажми **Save** → дай имя: *"Bookmark Feature"*

### Шаг 2 alt: Создай workflow (вариант Б — ручной)
1. Правый клик на канвас → **Add node** → **Agent** (это будет Scout)
2. Правый клик → **Add node** → **Agent** (Architect)
3. Правый клик → **Add node** → **Agent** (Coder)
4. Правый клик → **Add node** → **Agent** (Verifier)
5. Соедини: Scout → Architect → Coder → Verifier (drag от порта к порту)
6. **Save** → имя: *"Simple Pipeline"*

### Шаг 2 alt2: Загрузи готовый BMAD template
1. Нажми **Load ▾** → выбери *"BMAD Workflow"* (предустановленный)
2. Или нажми **↓ Import** → загрузи `data/templates/bmad_workflow.json`

### Шаг 3: Validate
1. Нажми **Validate ✓**
2. Должно показать: *"Valid (0 warnings)"*
3. Если ошибки — исправь связи между нодами

### Шаг 4: Execute
1. Нажми **▶ Execute**
2. Workflow сохранится и конвертируется в задачи TaskBoard
3. Root-задачи (без зависимостей) запустятся параллельно (max 3)

### Где смотреть:
- **Board**: задачи появятся со статусами
- **Activity**: live прогресс pipeline
- **DAG View**: ноды будут менять статус (streaming events `dag_node_update`)

---

## ПУТЬ 4: Import n8n workflow (3 минуты)

### Шаги:
1. Включи Edit Mode (✎)
2. Нажми **↓ Import**
3. Выбери JSON файл с n8n workflow (или ComfyUI)
4. Формат определится автоматически
5. Ноды появятся на канвасе → **Save** → **Execute**

### Export обратно:
1. Нажми **↑ Export ▾**
2. Выбери формат: **n8n JSON** или **ComfyUI JSON**
3. Файл скачается

---

## Heartbeat — автоматическое сканирование чата

### Как включить:
1. В шапке MCC найди **HeartbeatChip** (серая метка "Heartbeat off")
2. **Левый клик** → включится (станет teal, покажет таймер)
3. **Правый клик** → настройки интервала (в секундах)
   - 60 = каждую минуту
   - 300 = каждые 5 минут

### Что делает:
- Каждые N секунд сканирует чат на `@dragon` / `@doctor` команды
- Автоматически создаёт задачи и запускает pipeline
- Не нужно ждать ответа — write-and-forget

---

## Stats Panel — мониторинг производительности

### Вкладка Stats в DevPanel:
- **Running Tasks** — текущие запущенные задачи с elapsed time
- **Summary** — Total Runs, Success %, Avg Confidence, Avg Duration
- **Token Breakdown** — input vs output tokens per run
- **Per-Preset Bars** — сравнение Dragon Bronze vs Silver vs Gold

⚠️ Данные появляются ТОЛЬКО после реальных запусков pipeline. Если ещё ничего не запускал → *"No pipeline runs yet"*.

---

## Playground — изолированная песочница

### Текущий статус UI:
- **PlaygroundBadge** в шапке показывает количество активных playgrounds
- Dropdown: список с ID, возрастом, задачей
- Кнопка ✕ для уничтожения playground

### Создание playground (через API/MCP, пока нет UI):
```bash
# Через REST API:
curl -X POST http://localhost:5001/api/debug/playground/create \
  -H "Content-Type: application/json" \
  -d '{"task": "Add bookmark feature", "preset": "dragon_silver"}'

# Через MCP (в Claude Code):
# mycelium_playground_create(task="Add bookmark feature")
```

### Review и Promote (через API):
```bash
# Посмотреть изменения:
curl http://localhost:5001/api/debug/playground/{pg_id}/review

# Промоутить в main:
curl -X POST http://localhost:5001/api/debug/playground/{pg_id}/promote

# Отклонить:
curl -X POST http://localhost:5001/api/debug/playground/{pg_id}/reject
```

---

## Troubleshooting

### Pipeline не запускается
1. Проверь `curl http://localhost:5001/api/health`
2. Проверь что Qdrant запущен (нужен для semantic search)
3. Проверь API ключи в `.env` (OpenRouter, Tavily)

### Stats пустые
- Запусти хотя бы один LeagueTester test → данные появятся

### DAG Editor пустой
- Убедись что Edit Mode включен (✎)
- Попробуй Load → BMAD Workflow
- Или Generate → описание задачи

### Heartbeat не работает
- Проверь что включён (тeal цвет)
- Должны быть сообщения с `@dragon` в чате

### Playground не создаётся
- Max 5 одновременно → уничтожь старые через PlaygroundBadge
- Проверь что git worktree доступен: `git worktree list`

---

## Recommended Test Sequence (Первый запуск)

1. ✅ Запусти бэкенд + фронтенд
2. ✅ **LeagueTester** → Dragon Bronze (быстрый sanity check, ~30 сек)
3. ✅ **Stats** → убедись что данные появились
4. ✅ **@dragon** в чате → простая задача → `1d`
5. ✅ **Activity** → наблюдай live прогресс
6. ✅ **DAG Editor** → Generate → описание → Execute
7. ✅ **Import** n8n JSON → Execute
8. ✅ **Heartbeat** → включи → напиши @dragon задачу → подожди tick

---

*Written by Opus Commander | Phase 150 | 2026-02-15*
