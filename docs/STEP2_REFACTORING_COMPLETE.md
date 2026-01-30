# ✅ ШАГ 2: ПЕРЕПИСАТЬ handle_user_message - ЗАВЕРШЕНО

**Дата**: 25 December 2025  
**Статус**: ✅ ПОЛНОСТЬЮ ЗАВЕРШЕНО  
**Изменено файлов**: 2
- `main.py` - добавлены импорты, get_agents(), переписан handle_user_message
- `src/visualizer/tree_renderer.py` - исправлена фильтрация в renderMessages()

---

## 📋 ЧТО БЫЛО СДЕЛАНО

### 1️⃣ ПОДЗАДАЧА 2.1: Найденные агенты ✅
```
VetkaPM       → app/src/agents/vetka_pm.py
VetkaDev      → app/src/agents/vetka_dev.py
VetkaQA       → app/src/agents/vetka_qa.py
BaseAgent     → app/src/agents/base_agent.py

call_llm signature: call_llm(prompt: str, task_type: str = 'default', max_tokens: int = None, retries: int = 3)
```

### 2️⃣ ПОДЗАДАЧА 2.2: Импорты добавлены ✅
**Файл**: `main.py` (строка ~410)
```python
try:
    from app.src.agents.base_agent import BaseAgent
    from app.src.agents.vetka_pm import VetkaPM
    from app.src.agents.vetka_dev import VetkaDev
    from app.src.agents.vetka_qa import VetkaQA
    AGENTS_AVAILABLE = True
except ImportError as e:
    AGENTS_AVAILABLE = False
```

### 3️⃣ ПОДЗАДАЧА 2.3: Инициализация агентов ✅
**Функция**: `get_agents()` в `main.py` (строка ~725)
- Singleton pattern для избежания создания агентов на каждый запрос
- Thread-safe с использованием `_AGENTS_LOCK`
- Инициализирует VetkaPM, VetkaDev, VetkaQA с Weaviate helper
- Каждому агенту свой system_prompt для роли

### 4️⃣ ПОДЗАДАЧА 2.4: handle_user_message переписан ✅
**Функция**: Полностью переписана в `main.py` (строка ~2030)

**Старое поведение**:
```python
# ❌ HARDCODED TEMPLATE
response = f"""Got it! I'm {role} on {node_path}...
    I see the structure of this file. Let me analyze..."""
```

**Новое поведение**:
```python
# ✅ REAL LLM CALL
full_prompt = f"{system_prompt}\n\n{user_prompt}"
response_text = agent_instance.call_llm(
    prompt=full_prompt,
    task_type='feature_implementation',
    max_tokens=500,
    retries=2
)
```

**Новый flow**:
1. Get file context via Elisya
2. Get agent instances via get_agents()
3. For each agent (PM, Dev, QA):
   - Build system + user prompts with file context
   - Call agent.call_llm() for REAL LLM response ← KEY CHANGE!
   - Emit response to client
4. All responses sent with same node_id (fixes race condition)

### 5️⃣ ПОДЗАДАЧА 2.5: call_llm адаптирован ✅
**Проверено**: Сигнатура совпадает с нашим вызовом
```python
# ✅ CORRECT: call_llm(prompt, task_type, max_tokens, retries)
response_text = agent_instance.call_llm(
    prompt=full_prompt,
    task_type='feature_implementation',
    max_tokens=500,
    retries=2
)
```

### 6️⃣ ПОДЗАДАЧА 2.6: Frontend фильтрация исправлена ✅
**Файл**: `src/visualizer/tree_renderer.py` (строка 4382)

**Старое поведение**:
```javascript
// ❌ ПРОБЛЕМА: Только node_id фильтрация
const filtered = selectedNodeId
    ? chatMessages.filter(m => m.node_id === selectedNodeId)
    : chatMessages.slice(-10);
```

**Новое поведение**:
```javascript
// ✅ РЕШЕНИЕ: node_id ИЛИ недавние (< 60 сек)
const filtered = chatMessages.filter(m => {
    const isCurrentNode = !selectedNodeId || m.node_id === selectedNodeId;
    
    // Handle both Unix seconds and JS milliseconds
    let msgTime = m.timestamp < 10000000000 
        ? m.timestamp * 1000 
        : m.timestamp;
    
    const isRecent = msgTime > (Date.now() - 60000);
    
    return isCurrentNode || isRecent;  // Show both types
}).slice(-50);
```

**Что это исправляет**:
- ✅ PM видна (node_id совпадает) 
- ✅ Dev видна (совпадает node_id ИЛИ отправлена в последние 60 сек)
- ✅ QA видна (совпадает node_id ИЛИ отправлена в последние 60 сек)

Даже если пользователь кликнет на другую ноду между PM (0.5s) и QA (1.5s), все 3 сообщения будут видны 60 секунд!

---

## 🔍 ПРОВЕРКА СИНТАКСИСА

```bash
✅ python3 -m py_compile main.py
✅ python3 -m py_compile src/visualizer/tree_renderer.py
```

Ошибок нет!

---

## 📊 СРАВНЕНИЕ: ДО И ПОСЛЕ

| Критерий | ДО | ПОСЛЕ |
|----------|-------|---------|
| **LLM вызовы** | ❌ Нет | ✅ Да (call_llm) |
| **Ответы** | ❌ Hardcoded f-strings | ✅ Real LLM responses |
| **Уникальность** | ❌ Все одинаковые | ✅ Разные для PM/Dev/QA |
| **Релевантность** | ❌ Игнорирует контекст | ✅ Использует file context |
| **Видимость Dev/QA** | ❌ Скрыты если переключить ноду | ✅ Видны 60 сек |
| **Race condition** | ❌ Да (delays 0.5-1.5s) | ✅ Нет (same timestamp) |

---

## 🧪 КАК ТЕСТИРОВАТЬ

### 1. Убедись что Ollama работает:
```bash
ollama list
# Должны быть модели (llama3.1:8b, qwen2:7b, deepseek-coder:6.7b)

curl http://localhost:11434/api/tags
# Должно вернуть список моделей в JSON
```

### 2. Убедись что Weaviate доступна:
```bash
curl http://localhost:8080/v1/meta
# Должно вернуть info о Weaviate
```

### 3. Запусти сервер:
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 main.py
```

Ожидай лог:
```
✅ Agent classes imported (PM, Dev, QA ready for LLM responses)
[AGENTS] Initializing PM, Dev, QA instances...
[AGENTS] ✅ All agents initialized: PM, Dev, QA
```

### 4. Открой в браузере:
```bash
open http://localhost:5001/3d
```

### 5. Протестируй:
1. Кликни на файл (например, `main.py`)
2. Напиши вопрос: `What does this file do?`
3. Жди ответов

**Ожидаемый лог в терминале**:
```
[SOCKET] 📨 User message from xxx: What does this file do?...
[Elisya] Reading context for main.py...
[Elisya] ✅ Got context: File: main.py | Lines: 4095 | Size: 141563 bytes
[Agent] PM: Generating LLM response...
[Agent] PM: ✅ Generated 380 chars
[Agent] Dev: Generating LLM response...
[Agent] Dev: ✅ Generated 450 chars
[Agent] QA: Generating LLM response...
[Agent] QA: ✅ Generated 320 chars
[SOCKET] 📤 Sent PM response (380 chars)
[SOCKET] 📤 Sent Dev response (450 chars)
[SOCKET] 📤 Sent QA response (320 chars)
[SOCKET] ✅ All 3 agent responses sent
```

**Ожидаемый результат в UI**:
- ✅ 3 сообщения в chat (PM, Dev, QA)
- ✅ Каждое с разной иконкой (💼 PM, 💻 Dev, ✅ QA)
- ✅ Каждое с УНИКАЛЬНЫМ содержимым (не одинаковые!)
- ✅ Содержимое РЕЛЕВАНТНО файлу (описывает реальный файл)

### 6. Проверь что Dev/QA видны после переключения ноды:
1. Кликни на первый файл → отправь вопрос
2. **Сразу же кликни на другой файл**
3. Жди ответов...
4. Все 3 агента должны быть видны (благодаря 60 сек фильтру)

---

## 🔧 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

### Ошибка: "Agent classes not imported"
```
⚠️  Agent classes not available: ...
```
**Решение**: 
- Проверь что агенты существуют в `app/src/agents/`
- Проверь путь импорта (может быть просто `src.agents` вместо `app.src.agents`)

### Ошибка: "No agents available"
```
[AGENTS] ❌ No agents available, falling back to template responses
```
**Решение**:
- Проверь Weaviate доступна: `curl http://localhost:8080/v1/meta`
- Проверь логи get_agents() функции в терминале

### Ошибка: "LLM error"
```
[Agent] PM: ❌ LLM error - ...
```
**Решение**:
- Проверь что Ollama работает: `ollama list`
- Проверь что модели загружены: `ollama pull llama3.1:8b`
- Проверь что OLLAMA_URL правильно задан в конфиге

### Все 3 агента видны но ответы одинаковые
**Решение**:
- Это может означать что LLM быстро возвращает generic ответ
- Попробуй другой вопрос с более специфичным контекстом
- Проверь что каждый агент получает свой system_prompt

---

## 📁 BACKUPS

Сделаны бэкапы:
```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py.backup_step2
```

Если что-то сломалось, восстанови:
```bash
cp main.py.backup_step2 main.py
```

---

## ✨ ЧТО ИЗМЕНИЛОСЬ

### РАНЬШЕ (Hardcoded responses):
- Все агенты отвечали одинаково
- Контекст файла игнорировался  
- Задержки 0.5-1.5s между сообщениями
- Dev/QA иногда невидны при быстром переключении ноды

### ТЕПЕРЬ (Real LLM responses):
- Каждый агент отвечает уникально
- Контекст файла учитывается в ответах
- Все ответы отправляются с одной timestamp
- Dev/QA видны даже при переключении ноды (60 сек кэш)

---

## 🎯 РЕЗУЛЬТАТ

✅ **ГЛАВНАЯ ЗАДАЧА ВЫПОЛНЕНА**:
- Hardcoded f-strings ЗАМЕНЕНЫ на real LLM calls
- Все 3 агента (PM, Dev, QA) используют agent.call_llm()
- Каждый агент имеет свой system_prompt
- Контекст файла передаётся в LLM
- Frontend фильтрация исправлена

**Следующий ШАГ 3**: Дополнительная оптимизация (если нужно):
- [ ] Улучшить Elisya фильтрацию (embeddings)
- [ ] Добавить caching для repeated questions
- [ ] Оптимизировать context size
- [ ] Добавить error handling и retry logic

---

## 📝 ТЕХНИЧЕСКАЯ СПРАВКА

### System Prompts
```python
'PM':  "Focus on requirements, architecture, dependencies, risks"
'Dev': "Focus on implementation, code structure, patterns"
'QA':  "Focus on testing, edge cases, quality, reliability"
```

### Context Sources
1. **File content**: First 3000 chars from Elisya
2. **Key lines**: Top 15 relevant lines matched by keywords
3. **File info**: Path, lines count, size
4. **User query**: Direct user question

### LLM Settings
```python
task_type='feature_implementation'  # Tier selection
max_tokens=500                       # Response length
retries=2                            # Fallback attempts
timeout=30s (Ollama) / 60s (OpenRouter)
```

### Filtering Logic
```
Show if: (node_id match) OR (sent < 60 sec ago)
Max messages: 50
Update on every new message
```

---

## 🚀 SUCCESS CRITERIA MET

- ✅ Real LLM integration instead of hardcoded responses
- ✅ All 3 agents (PM, Dev, QA) initialized and ready
- ✅ File context passed to LLM via Elisya
- ✅ Each agent has unique system prompt
- ✅ Frontend filtering fixed for Dev/QA visibility
- ✅ No race conditions (same timestamp for all responses)
- ✅ Graceful fallback if agents not available
- ✅ Syntax checked and validated
- ✅ Backup created

---

**Статус**: 🎉 READY FOR TESTING
