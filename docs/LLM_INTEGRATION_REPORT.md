# 📋 РЕЗУЛЬТАТЫ ШАГа 1: ПОИСК СУЩЕСТВУЮЩЕГО LLM ИНТЕРФЕЙСА

**Статус**: ✅ ЗАВЕРШЕНО  
**Дата**: 25 December 2025

---

## 🔍 ВЫВОДЫ ИЗ АНАЛИЗА

### 1. СТРУКТУРА ПРОЕКТА

```
vetka_live_03/
├── src/               ← Визуализер (Phase 11)
│   ├── main.py        ← CLI для визуализации
│   └── ...
│
└── app/               ← ✅ ОСНОВНОЕ ПРИЛОЖЕНИЕ (Flask + Socket.IO)
    ├── main.py        ← (НЕ СУЩЕСТВУЕТ - нужно создать!)
    ├── config/
    │   └── config.py   ← ✅ Конфиг с моделями
    ├── src/
    │   └── agents/
    │       ├── base_agent.py      ← ✅ BaseAgent с call_llm()
    │       ├── vetka_pm.py        ← PM агент
    │       ├── vetka_dev.py       ← Dev агент
    │       └── vetka_qa.py        ← QA агент
    └── blueprints/    ← REST API routes
```

### 2. СУЩЕСТВУЮЩИЙ LLM ИНТЕРФЕЙС

**Файл**: `app/src/agents/base_agent.py`  
**Класс**: `BaseAgent`  
**Метод**: `call_llm(prompt: str, task_type: str, max_tokens: int, retries: int) -> str`

#### Сигнатура:
```python
def call_llm(self, prompt: str, task_type: str = 'default', max_tokens: int = None, retries: int = 3) -> str:
    """Call LLM with rotation and fallback"""
```

#### Поддерживаемые провайдеры:
1. **Ollama** (локально) - строка 109
   ```python
   response = requests.post(
       f"{OLLAMA_URL}/api/generate",
       json={'model': model_name, 'prompt': prompt, 'options': {'num_predict': max_tokens}},
       timeout=30
   )
   return response.json()['response']
   ```

2. **OpenRouter** (облако) - строка 119
   ```python
   response = requests.post(
       "https://openrouter.ai/api/v1/chat/completions",
       headers={"Authorization": f"Bearer {key}", ...},
       json={"model": model_name, "messages": [...], "max_tokens": max_tokens},
       timeout=60
   )
   return response.json()['choices'][0]['message']['content']
   ```

#### Модели по конфигу (app/config/config.py):
```python
AGENT_MODELS = {
    'VETKA-PM': ['ollama/llama3.1:8b'],
    'VETKA-Architect': ['ollama/qwen2:7b', 'ollama/llama3.1:8b'],
    'VETKA-Dev': ['ollama/deepseek-coder:6.7b', 'ollama/qwen2:7b'],
    'VETKA-QA': ['ollama/llama3.1:8b'],
}

MODEL_TIERS = {
    'premium': [Claude 3.5, GPT-4 Turbo via OpenRouter],
    'mid': [DeepSeek, Llama 3.1 70B via OpenRouter],
    'local': [DeepSeek-Coder 6.7B, Llama 3.1 8B, Qwen 2 7B via Ollama],
}
```

### 3. КАК ТЕКУЩИЕ АГЕНТЫ РАБОТАЮТ

**Пример**: `app/src/agents/vetka_pm.py`
```python
class VetkaPM(BaseAgent):
    def handle_task(self, task: str, context: Dict) -> str:
        prompt = f"""As PM: {task}
        Context: {context}"""
        
        # ✅ РЕАЛЬНЫЙ LLM ВЫЗОВ!
        response = self.call_llm(prompt, task_type='default')
        
        # Сохранить в Weaviate
        self.whelper.upsert_node(...)
        
        return response
```

**Текущее состояние**:
- ✅ Агенты существуют (PM, Dev, QA, Architect, Ops, Visual)
- ✅ Каждый имеет BaseAgent.call_llm()
- ✅ Функция поддерживает Ollama И OpenRouter
- ✅ Есть fallback и rotation между моделями

### 4. ЧТО ОТСУТСТВУЕТ

**Проблема**: Flask сервер с Socket.IO НЕ РЕАЛИЗОВАН в app/

**Требуется**:
- ❌ app/main.py (Flask app с Socket.IO) - НУЖНО СОЗДАТЬ
- ❌ route для обработки user_message
- ❌ интеграция BaseAgent в Socket.IO handler
- ❌ возврат ответов через Socket.IO

---

## 🛠️ РЕШЕНИЕ

### ОПЦИЯ A: БЫСТРО (используй существующие BaseAgent)

1. **Создай app/main.py** с Flask + Socket.IO
2. **Инстанцируй агентов** (PM, Dev, QA)
3. **В handle_user_message()** вызови `agent.call_llm()`
4. **Отправь результат** через `emit('agent_message', ...)`

**Код для app/main.py**:
```python
from flask import Flask, request
from flask_socketio import SocketIO, emit
from src.agents.vetka_pm import VetkaPM
from src.agents.vetka_dev import VetkaDev
from src.agents.vetka_qa import VetkaQA
from src.memory.weaviate_helper import WeaviateHelper
from config.config import OLLAMA_URL, WEAVIATE_URL

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vetka_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Инициализировать помощники
weaviate = WeaviateHelper(WEAVIATE_URL)

# Инициализировать агентов
agents = {
    'PM': VetkaPM(weaviate_helper=weaviate, socketio=socketio),
    'Dev': VetkaDev(weaviate_helper=weaviate, socketio=socketio),
    'QA': VetkaQA(weaviate_helper=weaviate, socketio=socketio),
}

@socketio.on('user_message')
def handle_user_message(data):
    """Handle user message and invoke all agents"""
    text = data.get('text', '')
    node_path = data.get('node_path', 'unknown')
    node_id = data.get('node_id', 'root')
    
    # ✅ Получить контекст файла
    # (из Elisya или директно)
    file_context = {...}  # ТВОЙ контекст
    
    # ✅ Вызвать каждого агента
    for agent_name, agent in agents.items():
        prompt = f"""
        Context: {file_context}
        User question: {text}
        File: {node_path}
        
        Provide detailed analysis."""
        
        # ✅ РЕАЛЬНЫЙ LLM ВЫЗОВ!
        response = agent.call_llm(
            prompt=prompt,
            task_type='feature_implementation',  # или другой
            max_tokens=500
        )
        
        # Отправить ответ клиенту
        emit('agent_message', {
            'agent': agent_name,
            'text': response,  # ← РЕАЛЬНЫЙ ответ!
            'node_id': node_id,
            'timestamp': time.time()
        })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
```

### ОПЦИЯ B: ЛУЧШЕ (создай специализированный метод)

Добавь в `app/src/agents/base_agent.py`:

```python
def generate_agent_response(self, 
                           user_query: str,
                           file_context: Dict,
                           node_path: str,
                           system_prompt: str) -> str:
    """
    Generate response for chat interface
    
    Args:
        user_query: Вопрос пользователя
        file_context: Контекст файла {'summary': '...', 'key_lines': [...]}
        node_path: Путь файла
        system_prompt: Системный промпт для роли (PM/Dev/QA)
    
    Returns:
        str: Сгенерированный ответ
    """
    
    # Построить контекст для LLM
    context_text = f"""
File: {node_path}
Summary: {file_context.get('summary', 'N/A')}

Relevant code:
{chr(10).join(file_context.get('key_lines', ['(no specific lines)'])[:10])}
"""
    
    # Построить промпт
    prompt = f"""{system_prompt}

Context:
{context_text}

User question: {user_query}

Provide your analysis:"""
    
    # ✅ ВЫЗВАТЬ LLM
    response = self.call_llm(
        prompt=prompt,
        task_type='feature_implementation',
        max_tokens=500
    )
    
    return response
```

И используй в handler:

```python
for agent_name, agent in agents.items():
    response = agent.generate_agent_response(
        user_query=text,
        file_context=file_context,
        node_path=node_path,
        system_prompt=AGENT_PROMPTS[agent_name]
    )
    
    emit('agent_message', {
        'agent': agent_name,
        'text': response,
        ...
    })
```

---

## ✅ ТРЕБОВАНИЯ ДЛЯ УСПЕХА

### 1. Убедись что Ollama работает:
```bash
# Проверить что Ollama запущена
curl http://localhost:11434/api/tags

# Должны быть модели:
ollama list

# Если нет нужных моделей - загрузить:
ollama pull llama3.1:8b
ollama pull qwen2:7b
ollama pull deepseek-coder:6.7b
```

### 2. Установить зависимости в app/:
```bash
cd app/
pip install -r requirements.txt
# или
pip install flask flask-socketio requests numpy
```

### 3. Переменные окружения (app/.env):
```
WEAVIATE_URL=http://localhost:8080
OLLAMA_URL=http://localhost:11434
FLASK_PORT=5001
EMBEDDING_MODEL=embeddinggemma:300m
```

---

## 🎯 РЕКОМЕНДАЦИЯ

**ИСПОЛЬЗУЙ ОПЦИЮ B** - она чище и переиспользуемо:

1. Добавь `generate_agent_response()` в BaseAgent
2. Создай app/main.py с Socket.IO сервером
3. Инстанцируй PM, Dev, QA агентов
4. В handle_user_message() используй их generate_agent_response()
5. Отправь ответы через emit()

**Результат**: Реальные LLM ответы, не hardcoded f-strings! ✅

---

## 📊 ИТОГОВАЯ ТАБЛИЦА

| Компонент | Статус | Файл | Метод |
|-----------|--------|------|-------|
| **BaseAgent** | ✅ Существует | app/src/agents/base_agent.py | call_llm() |
| **call_llm()** | ✅ Полно | base_agent.py:109-140 | requests.post() |
| **Ollama** | ✅ Поддерживается | base_agent.py:109 | /api/generate |
| **OpenRouter** | ✅ Поддерживается | base_agent.py:119 | /chat/completions |
| **Model routing** | ✅ Есть | config.py | AGENT_MODELS, TASK_ROUTING |
| **Flask сервер** | ❌ НУЖНО СОЗДАТЬ | app/main.py | Socket.IO |
| **Socket.IO handler** | ❌ НУЖНО СОЗДАТЬ | app/main.py | @socketio.on() |
| **Интеграция агентов** | ❌ НУЖНО СОЗДАТЬ | app/main.py | agents dict |

---

## 🚀 СЛЕДУЮЩИЙ ШАГ

**Готов переходить на ШАГ 2: ПЕРЕПИСАТЬ handle_user_message?**

Я создам:
1. ✅ app/main.py с Flask + Socket.IO
2. ✅ Инициализацией PM, Dev, QA агентов
3. ✅ Переписанный handle_user_message с реальными LLM вызовами
4. ✅ Исправление node_id фильтрации в frontend

Или хочешь что-то изменить перед тем как продолжить?
