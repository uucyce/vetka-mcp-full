# ДИАГНОСТИКА И ФИХ: Model Name Shows as 'unknown'

## РЕЗУЛЬТАТЫ ДИАГНОСТИКИ

### 1. Структура агентов

**НАЙДЕННЫЕ КЛАССЫ:**

```
app/src/agents/vetka_pm.py:
  class VetkaPM(BaseAgent)
    - Метод: current_model() → возвращает модель из model_pool
    - Аттрибут: model_pool = ['ollama/llama3.1:8b']
    - Status: ✅ IN USE

app/src/agents/vetka_dev.py:
  class VetkaDev(BaseAgent)
    - Метод: current_model() → возвращает модель из model_pool
    - Аттрибут: model_pool = ['ollama/deepseek-coder:6.7b', 'ollama/qwen2:7b']
    - Status: ✅ IN USE

app/src/agents/vetka_qa.py:
  class VetkaQA(BaseAgent)
    - Метод: current_model() → возвращает модель из model_pool
    - Аттрибут: model_pool = ['ollama/llama3.1:8b']
    - Status: ✅ IN USE

src/agents/vetka_dev.py:
  class VETKADevAgent(BaseAgent)
    - Аттрибут: self.model = "ollama/deepseek-coder:6.7b"
    - Status: ❌ NOT USED (exists but not instantiated in main.py)

src/agents/vetka_pm.py:
  class VETKAPMAgent(BaseAgent)
    - Аттрибут: self.model = "ollama/deepseek-coder:6.7b"
    - Status: ❌ NOT USED

src/agents/vetka_qa.py:
  class VETKAQAAgent(BaseAgent)
    - Аттрибут: self.model = "ollama/deepseek-coder:6.7b"
    - Status: ❌ NOT USED
```

### 2. Где задаётся модель

**В main.py (get_agents function):**

```python
_AGENTS_INSTANCE = {
    'PM': {
        'instance': VetkaPM(weaviate_helper=weaviate_helper, socketio=socketio),
        'system_prompt': system_prompts['PM']
    },
    'Dev': {
        'instance': VetkaDev(weaviate_helper=weaviate_helper, socketio=socketio),
        'system_prompt': system_prompts['Dev']
    },
    'QA': {
        'instance': VetkaQA(weaviate_helper=weaviate_helper, socketio=socketio),
        'system_prompt': system_prompts['QA']
    }
}
```

**Модели задаются в:**
- app/config/config.py - AGENT_MODELS dict
- app/src/agents/base_agent.py - BaseAgent.model_pool

### 3. Как агенты инициализируются

```
main.py:805
  → get_agents()
    → VetkaPM(weaviate_helper, socketio)
    → VetkaDev(weaviate_helper, socketio)
    → VetkaQA(weaviate_helper, socketio)
    
Each Agent calls BaseAgent.__init__():
  → Sets self.model_pool from config
  → Sets self.model_index = 0
  → Provides current_model() method
```

### 4. Текущая функция get_agent_model_name()

**БЫЛО (НЕПРАВИЛЬНО):**
```python
def get_agent_model_name(agent_instance) -> str:
    if hasattr(agent_instance, 'model'):                    # ❌ Ищет .model атрибут
        model = agent_instance.model
        if isinstance(model, str):
            return model.replace('ollama/', '')
    if hasattr(agent_instance, 'get_model'):               # ❌ Ищет get_model() метод
        return agent_instance.get_model().replace('ollama/', '')
    return "unknown"
```

**ПРОБЛЕМА:** Функция не знает про `current_model()` метод!

---

## РЕШЕНИЕ

**ИСПРАВЛЕНО (ПРАВИЛЬНО):**

```python
def get_agent_model_name(agent_instance) -> str:
    """Extract model name from agent instance. Works with both agent types."""
    try:
        if not agent_instance:
            return "unknown"
        
        # 1️⃣ Попробовать current_model() - НОВЫЕ АГЕНТЫ (app/src/agents/)
        if hasattr(agent_instance, 'current_model') and callable(agent_instance.current_model):
            try:
                model = agent_instance.current_model()
                if model:
                    return model.replace('ollama/', '')
            except Exception as e:
                print(f"[MODEL] current_model() failed: {e}")
        
        # 2️⃣ Попробовать .model атрибут - СТАРЫЕ АГЕНТЫ (src/agents/)
        if hasattr(agent_instance, 'model'):
            model = agent_instance.model
            if isinstance(model, str) and model:
                return model.replace('ollama/', '')
        
        # 3️⃣ Попробовать get_model() метод
        if hasattr(agent_instance, 'get_model') and callable(agent_instance.get_model):
            try:
                model = agent_instance.get_model()
                if model:
                    return model.replace('ollama/', '')
            except Exception as e:
                print(f"[MODEL] get_model() failed: {e}")
        
        # 4️⃣ Попробовать model_pool с индексом
        if hasattr(agent_instance, 'model_pool') and hasattr(agent_instance, 'model_index'):
            if isinstance(agent_instance.model_pool, list) and agent_instance.model_pool:
                model = agent_instance.model_pool[agent_instance.model_index % len(agent_instance.model_pool)]
                if model:
                    return model.replace('ollama/', '')
        
    except Exception as e:
        print(f"[MODEL] Error extracting model name: {e}")
    
    return "unknown"
```

---

## РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ

### Test File: test_model_extraction.py

```bash
$ python3 test_model_extraction.py

============================================================
TEST 2: New agent type (app/src/agents with current_model())
============================================================
✅ VetkaDev model: deepseek-coder:6.7b
   Model pool: ['ollama/deepseek-coder:6.7b', 'ollama/qwen2:7b']
   Current: ollama/deepseek-coder:6.7b

✅ VetkaPM model: llama3.1:8b
   Model pool: ['ollama/llama3.1:8b']
   Current: ollama/llama3.1:8b

✅ VetkaQA model: llama3.1:8b
   Model pool: ['ollama/llama3.1:8b']
   Current: ollama/llama3.1:8b

============================================================
SUMMARY
============================================================
✅ All tests passed - model extraction working!
```

### Результаты

| Агент | Модель | Результат |
|-------|--------|-----------|
| **Dev** | deepseek-coder:6.7b | ✅ Extracting via current_model() |
| **PM** | llama3.1:8b | ✅ Extracting via current_model() |
| **QA** | llama3.1:8b | ✅ Extracting via current_model() |

---

## ОТВЕТ В ЗАПРАШИВАЕМОМ ФОРМАТЕ

```
DIAGNOSIS:
- Agent has .model: NO (app/src/agents don't have .model attribute)
- Agent has .config.model: NO (not used in this design)
- Agent has current_model(): YES ✅
- Agent has model_pool[index]: YES ✅
- Model stored in: app/config/config.py AGENT_MODELS dict

FIX:
- Added check for current_model() method (primary extraction)
- Added check for .model attribute (secondary, for old agents)
- Added check for model_pool[index] (tertiary fallback)
- Function now tries 4 different methods before returning "unknown"

RESULT:
- PM model: llama3.1:8b ✅
- Dev model: deepseek-coder:6.7b ✅
- QA model: llama3.1:8b ✅
- All agent responses will now show model name correctly
```

---

## ФИКСЫ ПРИМЕНЕНЫ

1. ✅ main.py lines 2023-2070: Обновлена функция `get_agent_model_name()`
2. ✅ test_model_extraction.py: Создан тестовый файл для верификации
3. ✅ Документация: Обновлены PHASE_C_MODEL_NAMES.md и PHASE_C_FIX_MODEL_UNKNOWN.md

---

## ПРОВЕРКА СИНТАКСИСА

```bash
$ python3 -m py_compile main.py
✅ main.py OK
```

---

## СЛЕДУЮЩИЕ ШАГИ

1. **Запустить сервер**
   ```bash
   python3 main.py
   ```

2. **Открыть браузер**
   ```
   http://localhost:5001/3d
   ```

3. **Отправить сообщение к ноде**
   - Смотреть панель чата
   - Должны видеть: "Dev (deepseek-coder:6.7b)"
   - Вместо: "Dev (unknown)"

4. **Проверить консоль браузера**
   - Не должно быть ошибок
   - Может быть `[MODEL]` логи если что-то пойдёт не так

---

**STATUS**: 🟢 **FIXED & TESTED - READY FOR BROWSER TESTING**
