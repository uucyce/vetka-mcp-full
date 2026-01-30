# VETKA Phase 8.0 - Hybrid Learner Initializer

## 🎯 Суть гибридной архитектуры

**LOCAL (Ollama)** → Быстрый inference на M4 24GB (20-30 tok/s)
**API (Cloud)** → Обучение локальных моделей через distillation

### Почему гибрид?

- M4 24GB **отлично** для inference (DeepSeek 30 tok/s)
- M4 24GB **НЕ годится** для full fine-tune больших моделей
- **Решение**: Grok-4 учит → DeepSeek локально применяет → LoRA fine-tune на Unsloth (30 мин)

## 🤖 Доступные модели

### 🖥️  LOCAL (Ollama - для inference)

| Модель | RAM | Скорость | Лучше для | Особенности |
|--------|-----|----------|-----------|-------------|
| **DeepSeek-V3.2-7B** | 6GB | 30 tok/s | Simple, Medium, Complex | DSA/NSA sparse attention, граф-анализ |
| **HOPE-VL-7B** | 10GB | 20 tok/s | Complex, Expert | Hierarchical reasoning, vision, self-modifying |
| **Qwen2-7B** | 4GB | 25 tok/s | Simple, Medium | Быстрый fallback, надежный |

### ☁️  API (Cloud - для teaching)

| Модель | Скорость | Лучше для | Особенности |
|--------|----------|-----------|-------------|
| **Grok-4** | 100 tok/s | Complex, Expert | Лучшее reasoning, multimodal, teacher |
| **Claude 3.5** | 50 tok/s | Expert | Code/структуры |
| **GPT-4o-mini** | 80 tok/s | Medium, Complex | Быстрый, дешевый для distillation |

## 🚀 Установка

### 1. Установить зависимости

```bash
# Ollama (если еще нет)
brew install ollama

# Python пакеты
pip install ollama xai anthropic openai
```

### 2. Скачать локальные модели

```bash
# DeepSeek-V3.2-7B (основной)
ollama pull deepseek-v3.2:7b

# HOPE-VL-7B (hierarchical + vision)
ollama pull hope-vl:7b-instruct-q4_k_m

# Qwen2-7B (уже есть, fallback)
ollama pull qwen2:7b
```

### 3. Настроить API ключи

Создать `.env` (скопировать из `.env.example`):

```bash
# LOCAL
DEEPSEEK_MODEL=deepseek-v3.2:7b
HOPE_MODEL=hope-vl:7b-instruct-q4_k_m
QWEN_MODEL=qwen2:7b

# API (для teaching/distillation)
GROK_API_KEY=xai-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
```

## 💡 Использование

### Базовое: умный роутинг по сложности

```python
from src.agents.learner_initializer import LearnerInitializer, TaskComplexity

# Автоматический выбор модели по сложности
learner = LearnerInitializer.create_with_intelligent_routing(
    complexity=TaskComplexity.COMPLEX,
    memory_manager=memory,
    eval_agent=eval
)

# COMPLEX → попробует: deepseek → hope → grok
# Выберет первую доступную
```

### Упрощенное: из описания задачи

```python
from src.agents.learner_initializer import create_learner_for_task

# Автоматически определит сложность и выберет модель
learner = create_learner_for_task(
    task_description="Analyze workflow graph with 500 nodes and extract patterns",
    memory_manager=memory,
    eval_agent=eval,
    prefer_api=False  # Предпочитать локальные
)

# Авто-детект:
# - > 500 слов → COMPLEX
# - has_visual=True → EXPERT
# - < 100 слов → SIMPLE
```

### Гибридная пара: local + API teacher

```python
# Создать пару для distillation
pair = LearnerInitializer.create_hybrid_pair(
    memory_manager=memory,
    eval_agent=eval,
    local_model='deepseek',  # DeepSeek для inference
    api_teacher='grok'       # Grok для teaching
)

local_learner = pair['local']
api_teacher = pair['api_teacher']

# Workflow:
# 1. API teacher анализирует сложную задачу
# 2. Результаты → few-shot примеры для local
# 3. Периодический LoRA fine-tune через Unsloth
```

### Прямое создание конкретной модели

```python
# DeepSeek для быстрого inference
deepseek = LearnerInitializer.create_learner(
    'deepseek',
    memory_manager=memory
)

# Grok для сложного reasoning
grok = LearnerInitializer.create_learner(
    'grok',
    memory_manager=memory
)
```

## 🔄 Логика роутинга

### ROUTING_RULES

```python
SIMPLE (< 100 слов):
  Primary: qwen (fast local)
  Fallback: deepseek

MEDIUM (100-500 слов):
  Primary: deepseek (balanced)
  Fallback: qwen → gpt4o_mini

COMPLEX (> 500 слов + графы):
  Primary: deepseek (sparse attention)
  Fallback: hope → grok

EXPERT (visual + hierarchical):
  Primary: grok (API)
  Fallback: hope → claude
```

### Graceful degradation

```
Попытка 1: Primary модель
  ↓ (failed)
Попытка 2: Первый fallback
  ↓ (failed)
Попытка 3: Второй fallback
  ↓ (success)
✅ Используем доступную модель
```

## 🧠 Примеры сценариев

### Сценарий 1: Простой анализ (SIMPLE)

```python
# Задача: "Extract key points from workflow"
learner = LearnerInitializer.create_with_intelligent_routing(
    TaskComplexity.SIMPLE
)

# Результат: qwen (4GB RAM, 25 tok/s, локально)
```

### Сценарий 2: Граф-анализ (COMPLEX)

```python
# Задача: "Analyze dependency graph with 200 nodes, find bottlenecks"
learner = LearnerInitializer.create_with_intelligent_routing(
    TaskComplexity.COMPLEX,
    prefer_api=False  # Пытаться локально
)

# Результат: deepseek (sparse attention, локально)
# Fallback: hope → grok (если deepseek недоступен)
```

### Сценарий 3: Meta-learning (EXPERT)

```python
# Задача: "Self-improve based on visual workflow diagrams"
learner = LearnerInitializer.create_with_intelligent_routing(
    TaskComplexity.EXPERT,
    prefer_api=True  # Использовать API для best quality
)

# Результат: grok (cloud, 100 tok/s, multimodal)
# Fallback: hope → claude
```

### Сценарий 4: Distillation (гибрид)

```python
# 1. Создать пару
pair = LearnerInitializer.create_hybrid_pair()
local = pair['local']      # DeepSeek
teacher = pair['api_teacher']  # Grok

# 2. Teacher анализирует
teacher_result = teacher.analyze_workflow(workflow_data)

# 3. Local учится на примере
local.learn_from_example(teacher_result)

# 4. Периодический LoRA fine-tune
# unsloth_train(local, examples, epochs=3)  # 30 мин на M4
```

## 📊 График использования

```
┌─────────────────────────────────────────────────┐
│  ЗАДАЧА             │ МОДЕЛЬ     │ РАСХОД RAM  │
├─────────────────────────────────────────────────┤
│  Простые запросы    │ Qwen       │ 4GB         │
│  Средняя сложность  │ DeepSeek   │ 6GB         │
│  Граф-анализ        │ DeepSeek   │ 6GB         │
│  Visual reasoning   │ HOPE       │ 10GB        │
│  Teaching/Learning  │ Grok (API) │ 0GB (cloud) │
│  Distillation       │ Both       │ 6GB + API   │
└─────────────────────────────────────────────────┘

M4 24GB = спокойно держит DeepSeek + другие процессы
```

## 🔧 API интеграция (готова для main.py)

```python
# В main.py добавить endpoint
@app.route('/api/learner/route', methods=['POST'])
def route_learner():
    """Create learner with intelligent routing"""
    data = request.json

    task = data.get('task_description', '')
    complexity = data.get('complexity', 'medium')
    prefer_api = data.get('prefer_api', False)

    learner = LearnerInitializer.create_with_intelligent_routing(
        TaskComplexity(complexity),
        memory_manager=memory,
        eval_agent=eval_agent,
        prefer_api=prefer_api
    )

    return jsonify({
        'success': learner is not None,
        'model': learner.model_name if learner else None
    })
```

## 🎯 Преимущества гибрида

✅ **M4 не перегружается** - локальные модели для inference
✅ **Best quality** - API для сложных задач
✅ **Distillation** - API учит локальные модели
✅ **LoRA fine-tune** - Unsloth спокойно на 24GB (30 мин)
✅ **Graceful degradation** - всегда есть fallback
✅ **Умный роутинг** - автоматический выбор по сложности

## 🔐 Безопасность API ключей

```bash
# .env (НИКОГДА не коммитить!)
GROK_API_KEY=xai-...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# .gitignore
.env
*.key
```

## 📚 Дальнейшее развитие

- [ ] Автоматический distillation loop (API → local)
- [ ] LoRA fine-tune интеграция (Unsloth)
- [ ] Multi-model ensemble (voting)
- [ ] Cost tracking для API calls
- [ ] A/B testing между local и API

---

**VETKA Phase 8.0** - Hybrid Intelligence: Local Speed + Cloud Wisdom
