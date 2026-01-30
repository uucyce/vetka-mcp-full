# 🔍 ГЛУБОКИЙ АНАЛИЗ ПРОБЛЕМ СИСТЕМЫ ЧАТА АГЕНТОВ VETKA

**Дата**: 25 December 2025  
**Статус**: ДИАГНОСТИКА ЗАВЕРШЕНА  
**Критичность**: ВЫСОКАЯ 🔴

---

## ЧАСТЬ 1: ГЕНЕРАЦИЯ ОТВЕТОВ АГЕНТОВ

### Обработчик user_message (main.py:1900-2000)

**Полный код:**
```python
@socketio.on('user_message')
def handle_user_message(data):
    """
    ✅ TASK 2: Handle user message with Elisya context integration
    Reads file content and provides agents with relevant context
    """
    client_id = request.sid[:8]
    text = data.get('text', '').strip()
    node_id = data.get('node_id', 'root')
    node_path = data.get('node_path', 'unknown')

    print(f"\n[SOCKET] 📨 User message from {client_id}: {text[:50]}... (node: {node_path})")

    if not text:
        emit('agent_error', {'error': 'Empty message'})
        return

    # ✅ TASK 2: Get file content with Elisya filtering
    print(f"[Elisya] Reading context for {node_path}...")
    file_context = get_file_context_with_elisya(node_path, semantic_query=text)

    if file_context.get('error'):
        print(f"[Elisya] ⚠️  {file_context['error']}")
        context_summary = f"(File not accessible: {file_context['error']})"
        file_available = False
    else:
        print(f"[Elisya] ✅ Got context: {file_context['summary']}")
        file_available = True

        # Build context summary for agents
        context_lines = file_context['key_lines']
        if context_lines:
            context_summary = "\n\nRelevant code lines:\n" + "\n".join(context_lines[:5])
        else:
            context_summary = f"\n\n{file_context['summary']}"

    # ✅ TASK 2: Send agent responses WITH context
    import time

    agents_config = {
        'PM': {'delay': 0.5, 'role': 'Project Manager analyzing requirements'},
        'Dev': {'delay': 1.0, 'role': 'Developer implementing solution'},
        'QA': {'delay': 1.5, 'role': 'QA ensuring quality'}
    }

    for agent_name, agent_config in agents_config.items():
        time.sleep(agent_config['delay'])

        # Generate response with context
        role = agent_config['role']

        if not file_available:
            response = f"I'm {role} for {node_path}.\n\nNote: {context_summary}\n\nI can help you with general guidance on this topic."
        else:
            # File found - detailed response with context
            if agent_name == 'PM':
                response = f"""Got it! I'm {role} on {node_path}.

User question: {text}
File summary: {file_context['summary']}
{context_summary}

As PM: I see the structure of this file. Let me analyze the impact of your request..."""

            elif agent_name == 'Dev':
                response = f"""I'm {role} for {node_path}.

Your question: {text}
File info: {file_context['summary']}
{context_summary}

As Developer: I can see the code structure. Here's how I would approach this..."""

            else:  # QA
                response = f"""I'm {role} for {node_path}.

Testing aspect: {text}
File: {file_context['summary']}
{context_summary}

As QA: I would ensure these aspects pass tests..."""

        print(f"[Agent] {agent_name}: Sending response about {node_path}...")

        # ✅ TASK 3: Detect response type and check if should use artifact panel
        response_type = detect_response_type(response)
        force_artifact = len(response) > 800

        emit('agent_message', {
            'agent': agent_name,
            'text': response,
            'node_id': node_id,
            'node_path': node_path,
            'timestamp': time.time(),
            'context_provided': file_available,
            'response_type': response_type,
            'force_artifact': force_artifact
        })

        print(f"[SOCKET] 📤 Sent {agent_name} response (type={response_type}, artifact={force_artifact})")
```

### 🔍 АНАЛИЗ:

| Критерий | Результат | Строка |
|----------|-----------|--------|
| **Elisya вызывается** | ✅ ДА | 1920 |
| **Контекст передаётся агентам** | ✅ ДА | 1928-1936 |
| **LLM вызывается** | ❌ НЕТ | N/A |
| **Ответы hardcoded** | ✅ ДА (f-strings) | 1960-1990 |

### 🔴 ПРОБЛЕМА #1: HARDCODED RESPONSES

**Описание:**
Ответы агентов генерируются **статичными шаблонами f-strings**, а не через LLM:

```python
# ❌ НЕПРАВИЛЬНО: Статичный шаблон
if agent_name == 'PM':
    response = f"""Got it! I'm {role} on {node_path}.
    User question: {text}
    ...
    As PM: I see the structure of this file. Let me analyze the impact..."""
```

**Почему это проблема:**
- ✅ Elisya **читает** файл и получает контекст
- ✅ Контекст **содержит** relevant code lines
- ❌ Контекст **НЕ ИСПОЛЬЗУЕТСЯ** для генерации ответа
- ❌ Ответы всегда одинаковые ("I see the structure...", "Here's how I would approach...")
- ❌ Нет LLM для интеллектуальной генерации

**Результат для пользователя:**
Видит заглушки с текстом файла, но агенты не анализируют код реально.

---

## ЧАСТЬ 2: ОТОБРАЖЕНИЕ СООБЩЕНИЙ

### renderMessages() (tree_renderer.py:4376-4450)

**Полный код:**
```javascript
function renderMessages() {
    const container = document.getElementById('chat-messages');
    const filtered = selectedNodeId
        ? chatMessages.filter(m => m.node_id === selectedNodeId)
        : chatMessages.slice(-10);

    if (filtered.length === 0) {
        container.innerHTML = '<div>💭 No messages yet...</div>';
        return;
    }

    // Иконки для агентов
    const agentIcons = {
        'PM': '💼',
        'Dev': '💻',
        'QA': '✅',
        'ARC': '🏗️',
        'Human': '👤',
        'System': '⚙️'
    };

    container.innerHTML = filtered.map(msg => {
        const agentClass = msg.agent.replace(/ /g, '_');
        const icon = agentIcons[msg.agent] || '💬';
        
        let html = '<div class="msg ' + agentClass + '">';
        html += '<div class="msg-header">';
        html += '<span class="msg-agent">';
        html += '<span class="msg-agent-icon">' + icon + '</span>';
        html += '<span class="msg-agent-name">' + msg.agent + '</span>';
        html += '</span>';
        html += '<span class="msg-time">' + formatTime(msg.timestamp) + '</span>';
        html += '</div>';
        html += '<div class="msg-content">' + escapeHtml(msg.content) + '</div>';
        if (msg.delegated_to) html += '<div class="msg-delegation">🔀 Delegated to ' + msg.delegated_to + '</div>';
        if (msg.artifacts?.length) html += '<div class="msg-artifacts">' + msg.artifacts.map(a => '<span class="artifact">📎 ' + a + '</span>').join('') + '</div>';
        if (msg.status && msg.status !== 'done') html += '<div class="msg-status">' + msg.status + '</div>';
        html += '</div>';
        return html;
    }).join('');
    
    container.scrollTop = container.scrollHeight;
}
```

### 🔍 АНАЛИЗ:

| Критерий | Результат | Строка |
|----------|-----------|--------|
| **Фильтрация по агентам** | ❌ НЕТ | 4379-4381 |
| **innerHTML перезапись** | ✅ ДА | 4397 |
| **Все сообщения отображаются** | ✅ ДА | все |

### 🔴 ПРОБЛЕМА #2: НЕТ ФИЛЬТРАЦИИ

**Описание:**
`renderMessages()` НЕ фильтрует сообщения по агентам. Все сообщения из `chatMessages` отображаются.

**Почему кажется что виден только PM:**

```javascript
const filtered = selectedNodeId
    ? chatMessages.filter(m => m.node_id === selectedNodeId)  // ← Только по node_id!
    : chatMessages.slice(-10);                                // ← Не по агентам!
```

**Причина видимости только PM:**
1. PM отправляется ПЕРВЫМ (delay: 0.5 сек)
2. Dev отправляется вторым (delay: 1.0 сек)
3. QA отправляется третьим (delay: 1.5 сек)
4. **Но** в `chatMessages.push()` в listener'е (линия 2086) сообщение добавляется с node_id из текущей ноды
5. Если `selectedNodeId !== node_id`, сообщение НЕ ФИЛЬТРУЕТСЯ и может быть невидимо

**Проверка в консоли браузера:**
```javascript
console.log(chatMessages); // Покажет ВСЕ 3 сообщения
console.log(filtered);      // Покажет только ОТФИЛЬТРОВАННЫЕ по node_id
```

---

## ЧАСТЬ 3: SOCKET.IO LISTENER

### agent_message listener (tree_renderer.py:2068-2122)

**Полный код:**
```javascript
socket.on('agent_message', (data) => {
    console.log('[SOCKET-RX] 📨 Received agent_message:', data);
    console.log('[SOCKET-RX] Agent:', data.agent, 'Text length:', data.text?.length);

    const agent = data.agent || 'System';
    const text = data.text || data.message || '';
    const nodeId = data.node_id || selectedNodeId || 'root';
    const nodePath = data.node_path;

    console.log('[CHAT] Adding message to chatMessages array (current length:', chatMessages.length + ')');

    // Add to chat messages
    chatMessages.push({
        id: 'msg_' + Date.now(),
        node_id: nodeId,
        agent: agent,
        content: text,
        timestamp: data.timestamp || new Date().toISOString(),
        status: 'done'
    });

    console.log('[CHAT] Message added. New length:', chatMessages.length);

    // ✅ TASK 3b: Check if artifact panel should be opened
    const metadata = {
        type: data.response_type || 'text',
        force_artifact: data.force_artifact || false
    };

    if (shouldOpenArtifactPanel(text, metadata)) {
        console.log('[ARTIFACT] ✅ Opening panel for long/code response');
        showArtifactPanel(text, metadata.type, agent, nodeId, nodePath);
        
        // Update last message to show shortened version with link
        chatMessages[chatMessages.length - 1].content =
            text.substring(0, 200) + '...\\n\\n[See artifact panel →]';
    }

    console.log('[CHAT] Calling renderMessages()...');
    renderMessages();
    console.log('[CHAT] renderMessages() completed');
    console.log('[Chat] Agent ' + agent + ': ' + text.substring(0, 50));
});
```

### 🔍 АНАЛИЗ:

| Критерий | Результат | Строка |
|----------|-----------|--------|
| **Добавление в массив** | ✅ ДА | 2086 |
| **Вызов renderMessages** | ✅ ДА | 2115 |
| **Фильтрация** | ❌ НЕТ | N/A |

### 🔴 ПРОБЛЕМА #3: NODE_ID НЕСООТВЕТСТВИЕ

**Описание:**
Когда backend отправляет сообщение, он использует `node_id` из frontend запроса:

```python
emit('agent_message', {
    'agent': agent_name,
    'text': response,
    'node_id': node_id,  # ← node_id из запроса
    ...
})
```

Но в listener'е, если `selectedNodeId` изменился:

```javascript
const nodeId = data.node_id || selectedNodeId || 'root';
chatMessages.push({
    node_id: nodeId,  // ← nodeId из сообщения (старая нода)
    ...
});
```

Затем в `renderMessages()`:

```javascript
const filtered = selectedNodeId
    ? chatMessages.filter(m => m.node_id === selectedNodeId)  // ← Новая нода!
    : chatMessages.slice(-10);
```

**Результат:**
Если пользователь кликнул на другую ноду между отправкой PM (0.5s) и QA (1.5s), то:
- ✅ PM видна (node_id совпадает)
- ❌ Dev невидна (node_id не совпадает)
- ❌ QA невидна (node_id не совпадает)

---

## ЧАСТЬ 4: LLM ВЫЗОВЫ

### Поиск в main.py:

**Найдено:**
```python
# Строка 76: Ollama в списке зависимостей
'ollama',

# Строка 147: OrchestratorWithElisya импортируется
from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya as AgentOrchestrator

# Строка 156: AgentOrchestrator параллельный
from src.orchestration.agent_orchestrator_parallel import AgentOrchestrator

# Строка 168: get_file_context_with_elisya ВЫЗЫВАЕТСЯ
file_context = get_file_context_with_elisya(node_path, semantic_query=text)

# Строка 1966: "Got it!" hardcoded string
response = f"""Got it! I'm {role} on {node_path}...
```

### 🔍 АНАЛИЗ LLM ИНТЕГРАЦИИ:

| Компонент | Статус | Примечание |
|-----------|--------|-----------|
| **Ollama установлена** | ✅ | В requirements |
| **Orchestrator загружен** | ✅ | Есть fallback chain |
| **LLM вызовается в user_message** | ❌ | Нет вызова LLM! |
| **Elisya фильтрует контекст** | ✅ | Работает (simple keyword filter) |
| **Ответы агентов из LLM** | ❌ | Hardcoded f-strings |

### 🔴 ПРОБЛЕМА #4: LLM НЕ ИНТЕГРИРОВАНА В USER_MESSAGE

**Описание:**
Хотя `OrchestratorWithElisya` импортирована, она **НЕ ИСПОЛЬЗУЕТСЯ** в `handle_user_message`:

```python
def handle_user_message(data):
    file_context = get_file_context_with_elisya(...)  # ✅ Читает контекст
    
    # ❌ НЕ ВЫЗЫВАЕТ:
    # orchestrator.execute_workflow()
    # orchestrator.generate_response()
    # llm.complete()
    
    # Вместо этого генерирует ответ f-strings:
    response = f"""Got it! I'm {role}..."""  # ❌ Hardcoded!
```

**Где используется Orchestrator:**
```python
# В handle_start_workflow() (строка 2100+) - но НЕ в user_message!
orchestrator = get_orchestrator()
result = orchestrator.execute_full_workflow_streaming(feature, workflow_id)
```

---

## 🎯 ИТОГОВЫЙ ДИАГНОЗ

### 1. ПОЧЕМУ ЗАГЛУШКИ ВМЕСТО РЕАЛЬНЫХ ОТВЕТОВ

**Главная причина (Строка 1960-1990 main.py):**
```python
# ❌ НЕПРАВИЛЬНО:
if agent_name == 'PM':
    response = f"""Got it! I'm {role} on {node_path}.
    User question: {text}
    File summary: {file_context['summary']}
    {context_summary}
    
    As PM: I see the structure of this file. Let me analyze..."""  # ← Заглушка!
```

**Почему это произошло:**
1. Elisya интегрирована в `handle_user_message()` ✅
2. Контекст файла читается успешно ✅
3. **НО** нет вызова LLM для генерации реального ответа на основе контекста ❌
4. Вместо этого код генерирует статичные шаблоны с переменными
5. Результат: "I see the structure" звучит как реальный анализ, но это просто шаблон

### 2. ПОЧЕМУ ВИДЕН ТОЛЬКО PM

**Причина #1: Delay между отправками (строка 1945)**
```python
for agent_name, agent_config in agents_config.items():
    time.sleep(agent_config['delay'])  # PM: 0.5s, Dev: 1.0s, QA: 1.5s
```

**Причина #2: Node ID несоответствие (строка 2086, 2115)**
```javascript
const nodeId = data.node_id || selectedNodeId || 'root';  // Может быть старая нода
chatMessages.push({node_id: nodeId, ...});

// Later:
const filtered = chatMessages.filter(m => m.node_id === selectedNodeId);  // Новая нода!
```

**Сценарий:**
1. Пользователь кликает на "file.py" (node_id = "file.py")
2. Пишет сообщение и отправляет
3. Backend начинает отправлять ответы:
   - PM отправляется (0.5s) с node_id = "file.py" ✅ Видна
4. **Пользователь кликает на другую ноду "config.json"** ⚠️
5. Dev отправляется (1.0s) но с node_id = "file.py" ❌ Невидна (фильтруется)
6. QA отправляется (1.5s) но с node_id = "file.py" ❌ Невидна (фильтруется)

---

## 📋 РЕКОМЕНДАЦИИ ДЛЯ ИСПРАВЛЕНИЯ

### 1. ИНТЕГРИРОВАТЬ LLM В handle_user_message

**Текущее состояние:**
```python
def handle_user_message(data):
    file_context = get_file_context_with_elisya(...)  # ✅ Получает контекст
    # ❌ Не использует LLM
    response = f"""Got it! I'm {role}..."""  # ❌ Hardcoded
```

**Должно быть:**
```python
def handle_user_message(data):
    file_context = get_file_context_with_elisya(...)  # ✅ Получает контекст
    
    for agent_name in ['PM', 'Dev', 'QA']:
        # ✅ Использовать LLM для генерации ответа
        orchestrator = get_orchestrator()
        response = orchestrator.generate_agent_response(
            agent=agent_name,
            user_query=text,
            file_context=file_context,
            node_path=node_path
        )
        emit('agent_message', {
            'agent': agent_name,
            'text': response,  # ← Реальный ответ от LLM!
            ...
        })
```

### 2. ИСПРАВИТЬ NODE_ID НЕСООТВЕТСТВИЕ

**Опция A: Отправить правильный node_id от backend**
```python
# Важно: Использовать ТЕКУЩИЙ selectedNodeId из frontend
emit('agent_message', {
    'node_id': data.get('node_id'),  # ← Использовать node_id из запроса
    ...
})
```

**Опция B: Не фильтровать по node_id в listener'е**
```javascript
// Не добавлять node_id к сообщению, или всегда использовать selectedNodeId
chatMessages.push({
    // node_id: nodeId,  // ← Убрать или всегда использовать текущую
    agent: agent,
    content: text,
    ...
});
```

### 3. УЛУЧШИТЬ ELISYA ФИЛЬТРАЦИЮ

**Текущая реализация (main.py:168-240):**
```python
# Simple keyword-based filtering
keywords = semantic_query.lower().split()
for i, line in enumerate(lines):
    if any(keyword in line_lower for keyword in keywords):
        key_lines.append(f"Line {i+1}: {line.strip()}")
```

**Должна быть:**
- Использовать NLP для семантического поиска (не просто keyword matching)
- Использовать embeddings для поиска по смыслу
- Учитывать контекст (функции, классы, документация)

### 4. УБРАТЬ DELAYS МЕЖДУ ОТПРАВКАМИ

**Текущее:**
```python
time.sleep(agent_config['delay'])  # Разные delays → асинхронность
```

**Должно быть:**
```python
# Отправить ВСЕ ответы одновременно или в быстрой последовательности
# Чтобы все три сообщения попали в одну "батч-отправку"
for agent_name in agents_config:
    response = generate_response(agent_name, ...)
    emit_queue.append({'agent': agent_name, 'text': response})

# Отправить все сразу
for msg in emit_queue:
    emit('agent_message', msg)
```

---

## 📊 SUMMARY TABLE

| Проблема | Причина | Следствие | Строка |
|----------|---------|-----------|--------|
| **Заглушки** | Hardcoded f-strings вместо LLM | Агенты не анализируют контекст | 1960-1990 |
| **Только PM видна** | Delays + node_id фильтрация | Dev/QA фильтруются по node_id | 1945 + 2086 |
| **Elisya не используется** | LLM не вызывается в user_message | Контекст игнорируется | 1920 |
| **Нет real responses** | Orchestrator импортирован но не используется | Всегда одинаковые ответы | 147 vs 1960 |

---

**Статус**: 🔴 КРИТИЧНО  
**Приоритет**: 🔴 URGENT  
**Сложность исправления**: 🟡 СРЕДНЯЯ (2-4 часа)
