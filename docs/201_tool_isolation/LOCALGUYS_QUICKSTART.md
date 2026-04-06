# Localguys — Локальные AI помощники для VETKA

Твои бесплатные AI работники. Работают без интернета, без API ключей, без лимитов.
Ollama крутит модели на твоём Mac, они берут задачи с доски и делают.

Все команды ниже запускаются из терминала в папке проекта:
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
```

---

## Перед началом — проверка

Открой терминал и проверь что всё запущено:

```bash
# Ollama работает?
curl -s http://localhost:11434/api/tags | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Ollama OK: {len(d[\"models\"])} моделей')"

# VETKA API работает?
curl -s http://localhost:5001/api/health | python3 -c "import json,sys; print('API OK' if json.load(sys.stdin).get('status')=='healthy' else 'API DOWN')"
```

Если Ollama не запущен: `ollama serve` (оставь терминал открытым)
Если API не запущен: запусти VETKA сервер

---

## 1. Посмотреть что есть — статус

```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/ollama_orchestrator.py --status
```

Покажет: какие модели загружены, сколько задач ждут.

---

## 2. Одна задача — простой режим

Берёт одну задачу с доски, прогоняет через модель, сохраняет результат:

```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/ollama_orchestrator.py --model qwen2.5:7b
```

Хочешь сначала посмотреть что будет, без выполнения:
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/ollama_orchestrator.py --dry-run
```

---

## 3. Полный pipeline — задача через 6 шагов

Модели работают как команда: один разведывает, другой планирует, третий кодит, четвёртый проверяет.

### Шаг 1: Создай run для задачи
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/localguys.py run g3 --task СЮДА_ID_ЗАДАЧИ
```

Например:
```bash
python3 scripts/localguys.py run g3 --task tb_1774312325_43
```

Запомни `run_id` из вывода (будет что-то вроде `lg_run_abc123`).

### Шаг 2: Запусти выполнение
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/localguys_executor.py --run-id СЮДА_RUN_ID
```

Например:
```bash
python3 scripts/localguys_executor.py --run-id lg_run_abc123
```

Увидишь как шаги выполняются один за другим (~2-3 минуты):
```
[1/6] Step: recon    | Model: qwen2.5:7b   | 8s
[2/6] Step: plan     | Model: qwen3:8b     | 18s
[3/6] Step: execute  | Model: qwen2.5:7b   | 11s
[4/6] Step: verify   | Model: deepseek-r1  | 24s
[5/6] Step: review   | Model: deepseek-r1  | 24s
[6/6] Step: finalize | Model: qwen2.5:7b   | 14s
Run completed!
```

### Шаг 3: Проверь результат
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/localguys.py status --task СЮДА_ID_ЗАДАЧИ
```

---

## 4. Разбить сложную задачу на простые (DECOMPOSER)

Это главная фишка. Берёт любую сложную задачу и разбивает на 3-7 маленьких,
которые локальные модели точно потянут.

### Шаг 1: Создай run
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/localguys.py run g3 --task СЮДА_ID_СЛОЖНОЙ_ЗАДАЧИ
```

### Шаг 2: Запусти decompose
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/localguys_executor.py --run-id СЮДА_RUN_ID --method decompose
```

За 41 секунду:
1. qwen2.5:7b анализирует задачу
2. qwen3:8b разбивает на подзадачи
3. Подзадачи автоматически появляются на доске

Потом каждую подзадачу можно выполнить:
```bash
# Подзадачи уже на доске с пометкой [AUTO]
# Запусти pipeline для каждой:
python3 scripts/localguys.py run g3 --task tb_CHILD_ID
python3 scripts/localguys_executor.py --run-id lg_run_XXX
```

---

## 5. Автопилот — 24/7 без присмотра

Запускаешь и уходишь. Модель сама берёт задачи, делает, отчитывается:

```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/ollama_orchestrator.py --loop --model qwen2.5:7b --interval 300
```

`--interval 300` = проверяет доску каждые 5 минут. Если нашёл задачу — делает.
Если нет — ждёт. Ctrl+C чтобы остановить.

Для конкретного проекта:
```bash
cd ~/Documents/VETKA_Project/vetka_live_03
python3 scripts/ollama_orchestrator.py --loop --model qwen2.5:7b --project CUT
```

---

## 6. Мониторинг — Event Bus daemon

Чтобы видеть что происходит в реальном времени:

```bash
cd ~/Documents/VETKA_Project/vetka_live_03

# Запустить демон (работает в фоне)
python3 scripts/uds_daemon.py --daemon

# Проверить работает ли
python3 scripts/uds_daemon.py --status

# Остановить
python3 scripts/uds_daemon.py --stop
```

---

## Какие модели для чего

| Кто | Модель | Скорость | Для чего |
|-----|--------|----------|----------|
| Разведчик | qwen2.5:7b | ~8 сек | Анализ задачи, сбор фактов |
| Архитектор | qwen3:8b | ~18 сек | Планирование, разбиение на подзадачи |
| Кодер | qwen2.5:7b | ~11 сек | Написание кода |
| Проверяющий | deepseek-r1:8b | ~24 сек | Ревью кода, поиск ошибок |
| Быстрые решения | phi4-mini | ~3 сек | Простые да/нет ответы |

---

## Сколько времени занимает

| Что | Шагов | Время |
|-----|-------|-------|
| Простая задача (одна модель) | 1 | ~10-20 сек |
| Полный pipeline (g3) | 6 | ~2-3 мин |
| Разбиение сложной задачи | 3 | ~41 сек |
| Потом каждая подзадача | 6 | ~2-3 мин |

---

## Артефакты — где лежат результаты

После каждого run результаты сохраняются:
```
~/Documents/VETKA_Project/vetka_live_03/artifacts/mcc_local/
    TASK_ID/
        RUN_ID/
            facts.json          — что нашёл разведчик
            plan.json           — план архитектора
            patch.diff          — код от кодера
            test_output.txt     — результат проверки
            review.json         — ревью
            final_report.json   — итоговый отчёт
```

---

## Если что-то не работает

**"Ollama не отвечает"** — запусти `ollama serve` в отдельном терминале

**"Task board list failed"** — запусти VETKA API сервер

**"No suitable pending tasks"** — на доске нет задач для локальных моделей.
Создай задачу через Claude Code или MCC

**"Claim failed 403"** — задача заблокирована для локальных моделей
(в ней `allowed_tools: ["claude_code"]`). Выбери другую

**"Signal advance failed: invalid role"** — некритичная ошибка, задача всё равно выполнится

---

## Шпаргалка — копируй и вставляй

```bash
# Перейти в проект
cd ~/Documents/VETKA_Project/vetka_live_03

# Статус
python3 scripts/ollama_orchestrator.py --status

# Одна задача
python3 scripts/ollama_orchestrator.py --model qwen2.5:7b

# Полный pipeline
python3 scripts/localguys.py run g3 --task ID_ЗАДАЧИ
python3 scripts/localguys_executor.py --run-id RUN_ID

# Разбить сложную на простые
python3 scripts/localguys.py run g3 --task ID_ЗАДАЧИ
python3 scripts/localguys_executor.py --run-id RUN_ID --method decompose

# Автопилот
python3 scripts/ollama_orchestrator.py --loop --model qwen2.5:7b --interval 300

# Мониторинг
python3 scripts/uds_daemon.py --daemon
python3 scripts/uds_daemon.py --status
```
