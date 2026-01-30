# VETKA Phase 8.0 - Quick Start

## ✅ Чек-лист готовности

### 1. Установка моделей (5 минут)

```bash
# DeepSeek-V3.2 (основной, 6GB)
ollama pull deepseek-v3.2:7b

# HOPE-VL (hierarchical, 10GB)
ollama pull hope-vl:7b-instruct-q4_k_m

# Qwen2 (fallback, 4GB) - уже есть
ollama list | grep qwen2
```

### 2. Настройка .env (1 минута)

```bash
# Скопировать пример
cp .env.example .env

# Добавить API ключи (опционально)
# GROK_API_KEY=xai-...
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
```

### 3. Проверка импорта (30 секунд)

```python
python3 -c "
from src.agents.learner_initializer import LearnerInitializer, TaskComplexity
print('✅ Import OK')
LearnerInitializer.list_available()
"
```

## 🚀 Примеры использования

### Пример 1: Простой анализ (LOCAL only)

```python
from src.agents.learner_initializer import LearnerInitializer, TaskComplexity

# Qwen для быстрых задач
learner = LearnerInitializer.create_with_intelligent_routing(
    TaskComplexity.SIMPLE,
    memory_manager=memory,
    eval_agent=eval
)

# Результат: Qwen (4GB RAM, 25 tok/s)
```

### Пример 2: Граф-анализ (LOCAL DeepSeek)

```python
# DeepSeek для графов (sparse attention)
learner = LearnerInitializer.create_with_intelligent_routing(
    TaskComplexity.COMPLEX,
    memory_manager=memory,
    eval_agent=eval
)

# Результат: DeepSeek (6GB RAM, 30 tok/s)
```

### Пример 3: Гибридная пара (LOCAL + API)

```python
# DeepSeek (local) + Grok (API teacher)
pair = LearnerInitializer.create_hybrid_pair(
    memory_manager=memory,
    eval_agent=eval
)

local = pair['local']       # DeepSeek
teacher = pair['api_teacher']  # Grok (if API key set)

# API учит → Local применяет
```

### Пример 4: Автоопределение сложности

```python
from src.agents.learner_initializer import create_learner_for_task

# Автоматический выбор по описанию
learner = create_learner_for_task(
    task_description="Analyze large workflow graph with 500 nodes",
    memory_manager=memory,
    prefer_api=False  # Предпочитать локальные
)

# Авто-детект: > 500 слов → COMPLEX → DeepSeek
```

## 📊 Что использовать когда

| Сценарий | Сложность | Модель | RAM | Команда |
|----------|-----------|--------|-----|---------|
| Простые запросы | SIMPLE | Qwen | 4GB | `TaskComplexity.SIMPLE` |
| Workflow анализ | MEDIUM | DeepSeek | 6GB | `TaskComplexity.MEDIUM` |
| Граф-анализ | COMPLEX | DeepSeek | 6GB | `TaskComplexity.COMPLEX` |
| Vision + hierarchy | EXPERT | Grok/HOPE | 0GB/10GB | `TaskComplexity.EXPERT` |

## 🔧 Troubleshooting

### Проблема: модель не найдена

```bash
# Проверить доступные
ollama list

# Скачать недостающие
ollama pull deepseek-v3.2:7b
ollama pull hope-vl:7b-instruct-q4_k_m
```

### Проблема: API ключ не работает

```bash
# Проверить .env
cat .env | grep API_KEY

# Убедиться что файл загружен
python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GROK_API_KEY'))"
```

### Проблема: не хватает RAM

```bash
# Использовать только легкие модели
# Qwen: 4GB
# DeepSeek: 6GB
# Избегать HOPE (10GB) если RAM < 16GB
```

## 📈 Performance на M4 24GB

```
Qwen2-7B:        25 tok/s, 4GB RAM  ✅
DeepSeek-V3.2:   30 tok/s, 6GB RAM  ✅
HOPE-VL:         20 tok/s, 10GB RAM ✅

Одновременно:
- DeepSeek + Qwen = 10GB (OK)
- DeepSeek + HOPE = 16GB (OK)
- Все 3 модели = 20GB (tight, но OK)

Grok/Claude/GPT = 0GB (cloud, API)
```

## 🎯 Готово к работе!

```python
# Минимальный код для старта
from src.agents.learner_initializer import LearnerInitializer, TaskComplexity

# Создать learner
learner = LearnerInitializer.create_with_intelligent_routing(
    TaskComplexity.MEDIUM,
    memory_manager=memory,
    eval_agent=eval
)

# Использовать
result = learner.analyze_workflow(workflow_data)
```

---

**Phase 8.0 ready!** 🚀 Local speed + Cloud wisdom = VETKA hybrid intelligence
