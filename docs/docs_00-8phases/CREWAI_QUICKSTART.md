# 🤖 VETKA CrewAI Quick Start Guide

**Дата:** 5 октября 2025, 23:00  
**Статус:** ✅ WORKING - Протестировано и работает!

---

## ✅ ЧТО РАБОТАЕТ (ПРОВЕРЕНО!)

### **Установлено в venv:**
```bash
/Users/danilagulin/Documents/VETKA_Project/venv/bin/python

# Пакеты:
crewai==0.201.1
crewai-tools==0.75.0
autogen-agentchat==0.7.5
autogen-core==0.7.5
langchain-ollama==0.3.7
mem0ai==0.1.118
```

---

## 🚀 РАБОЧИЙ ПРИМЕР (test_vetka_crew.py)

**Путь:** `/Users/danilagulin/Documents/VETKA_Project/test_vetka_crew.py`

**Запуск:**
```bash
cd /Users/danilagulin/Documents/VETKA_Project
/Users/danilagulin/Documents/VETKA_Project/venv/bin/python test_vetka_crew.py
```

**Результат:** ✅ Агент успешно дал решение для CrossEncoder проблемы!

---

## 📝 МИНИМАЛЬНЫЙ КОД (РАБОТАЕТ!)

```python
#!/usr/bin/env python3
from crewai import Agent, Task, Crew, Process, LLM
from mem0 import Memory

# 1. LLM (КРИТИЧНО: префикс ollama/)
llm = LLM(
    model="ollama/deepseek-coder:6.7b",
    base_url="http://localhost:11434"
)

# 2. Memory (КРИТИЧНО: from_config!)
mem0_config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1:8b",
            "ollama_base_url": "http://localhost:11434"
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "embeddinggemma:300m",
            "ollama_base_url": "http://localhost:11434"
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "mem0"
        }
    }
}

memory = Memory.from_config(mem0_config)

# 3. Agent
developer = Agent(
    role='VETKA Senior Developer',
    goal='Fix bugs and implement features',
    backstory='Expert Python developer',
    llm=llm,
    verbose=True
)

# 4. Task
task = Task(
    description='Your task description here',
    agent=developer,
    expected_output='What you expect as result'
)

# 5. Crew
crew = Crew(
    agents=[developer],
    tasks=[task],
    process=Process.sequential,
    verbose=True
)

# 6. Run!
result = crew.kickoff()
print(result)

# 7. Save to memory (КРИТИЧНО: messages, не content!)
memory.add(
    messages=[{"role": "assistant", "content": str(result)}],
    user_id="danilagulin",
    metadata={"agent": "VETKA-Dev"}
)
```

---

## ⚠️ КРИТИЧНЫЕ ОШИБКИ (ИЗБЕГАТЬ!)

### ❌ НЕПРАВИЛЬНО:
```python
# 1. БЕЗ префикса ollama/
from langchain_ollama import ChatOllama
llm = ChatOllama(model="deepseek-coder:6.7b")
# ОШИБКА: LiteLLM не поймёт провайдера!

# 2. Дефолтная инициализация Memory
memory = Memory()
# ОШИБКА: Попытается использовать OpenAI API!

# 3. Неправильный API mem0
memory.add(content="text", user_id="...")
# ОШИБКА: add() не принимает content!
```

### ✅ ПРАВИЛЬНО:
```python
# 1. С префиксом ollama/
from crewai import LLM
llm = LLM(model="ollama/deepseek-coder:6.7b", base_url="http://localhost:11434")

# 2. С конфигом
memory = Memory.from_config(mem0_config)

# 3. Правильный API
memory.add(messages=[{"role": "assistant", "content": "text"}], user_id="...")
```

---

## 🎯 ДОСТУПНЫЕ OLLAMA МОДЕЛИ

```bash
# Для агентов (выбирай по задаче):
ollama/deepseek-coder:6.7b    # Лучший для кода
ollama/llama3.1:8b            # Универсальный
ollama/qwen2:7b               # Альтернативный
ollama/llama3.2:1b            # Быстрый легковес

# Embeddings (для mem0):
embeddinggemma:300m           # Основной
```

---

## 🔄 WORKFLOW PATTERNS

### **Pattern 1: Sequential (по очереди)**
```python
crew = Crew(
    agents=[pm, architect, dev, qa],
    tasks=[plan_task, design_task, code_task, test_task],
    process=Process.sequential  # Один за другим
)
```

### **Pattern 2: Hierarchical (с менеджером)**
```python
crew = Crew(
    agents=[dev, qa, ops],
    tasks=[code, test, deploy],
    process=Process.hierarchical,
    manager_llm=LLM(model="ollama/llama3.1:8b")  # PM управляет
)
```

---

## 🧠 MEMORY BEST PRACTICES

### **Сохранение:**
```python
memory.add(
    messages=[{
        "role": "assistant",
        "content": f"Task: {task_name}\nResult: {result}"
    }],
    user_id="danilagulin",
    metadata={
        "agent": "VETKA-Dev",
        "task_type": "debugging",
        "file": "mcp_wrapper.py",
        "timestamp": datetime.now().isoformat()
    }
)
```

### **Поиск:**
```python
results = memory.search(
    query="CrossEncoder device issue",
    user_id="danilagulin",
    limit=5
)

for r in results:
    print(r['memory'])
```

---

## 🐛 РЕШЁННЫЕ ПРОБЛЕМЫ

### **Проблема 1: "LLM Provider NOT provided"**
**Причина:** Нет префикса `ollama/`  
**Решение:** Используй `LLM(model="ollama/model-name")`

### **Проблема 2: "api_key must be set (OPENAI_API_KEY)"**
**Причина:** Дефолтная инициализация `Memory()`  
**Решение:** Используй `Memory.from_config(config)`

### **Проблема 3: "unexpected keyword argument 'content'"**
**Причина:** Неправильный API mem0  
**Решение:** Используй `messages=[{"role": "...", "content": "..."}]`

---

## 📊 УСПЕШНЫЙ ТЕСТ РЕЗУЛЬТАТ

```
🌳 VETKA Test v3
========================================
✅ LLM ready
✅ Memory ready
🚀 Running...

✨ Result:
[DeepSeek Coder предложил решение для CrossEncoder]

✅ Saved to memory
✅ Search found 1 results

🎉 ALL SYSTEMS WORKING!
```

---

## 🎯 СЛЕДУЮЩИЕ ШАГИ

1. ✅ CrewAI работает
2. ⏳ Применить решение агента к `mcp_wrapper_vetka_full.py`
3. ⏳ Создать role-based коллекции в Qdrant
4. ⏳ Создать полную команду из 7 агентов
5. ⏳ Запустить Self-Improvement Loop

---

## 🔗 ПОЛЕЗНЫЕ ССЫЛКИ

- CrewAI Docs: https://docs.crewai.com/
- mem0 Docs: https://docs.mem0.ai/
- Ollama Models: http://localhost:11434/api/tags

---

**🌳 VETKA Meta-Agent система готова к расширению!**
