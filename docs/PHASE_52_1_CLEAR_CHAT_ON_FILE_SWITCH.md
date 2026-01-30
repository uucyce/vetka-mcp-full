# Phase 52.1: Clear Chat on File Switch

## ПРОБЛЕМА
При переключении между файлами в 3D-дереве чат сохранял сообщения предыдущего файла, создавая путаницу в контексте диалога.

## РЕШЕНИЕ

### 1. Новый useEffect в ChatPanel (client/src/components/chat/ChatPanel.tsx:153-197)

```tsx
// Phase 52.1: Clear chat when file selection changes
useEffect(() => {
  if (selectedNode) {
    console.log(`[ChatPanel] File changed to: ${selectedNode.path}`);

    // Clear current messages
    clearChat();

    // Try to load history for this file if it exists
    const chatId = selectedNode.path; // Use file path as chat ID

    fetch(`/api/chats/${encodeURIComponent(chatId)}`)
      .then(response => {
        if (response.ok) {
          return response.json();
        }
        return null;
      })
      .then(data => {
        if (data && data.messages) {
          console.log(`[ChatPanel] Loaded ${data.messages.length} messages for ${selectedNode.name}`);

          // Add all messages from the chat history
          for (const msg of data.messages) {
            addChatMessage({
              id: msg.id || crypto.randomUUID(),
              role: msg.role,
              content: msg.content,
              agent: msg.agent,
              type: msg.role === 'user' ? 'text' : 'text',
              timestamp: msg.timestamp || new Date().toISOString(),
            });
          }
        } else {
          console.log(`[ChatPanel] No history found for ${selectedNode.name}, starting fresh`);
        }
      })
      .catch(error => {
        console.log(`[ChatPanel] No history for ${selectedNode.name}:`, error.message);
      });
  }
}, [selectedNode?.path, clearChat, addChatMessage]);
```

## ПОВЕДЕНИЕ

### Сценарий 1: Переключение между файлами без истории
1. Пользователь кликает на файл A → чат очищается
2. Пользователь пишет сообщения для файла A
3. Пользователь кликает на файл B → чат очищается
4. Чат для файла B пустой (fresh start)

### Сценарий 2: Переключение между файлами с историей
1. Файл A имеет сохраненную историю в `/api/chats/path/to/fileA`
2. Пользователь кликает на файл A → загружается история A
3. Пользователь кликает на файл B → чат очищается и загружается история B (если есть)
4. Возврат к файлу A → снова загружается история A

### Сценарий 3: Ошибки загрузки
- Если API возвращает 404 → чат остается пустым (silent fallback)
- Если API возвращает ошибку → чат остается пустым, ошибка логируется

## ТЕХНИЧЕСКИЕ ДЕТАЛИ

### Триггеры очистки
- **Dependency**: `selectedNode?.path` — очистка происходит только при изменении пути
- **Избегание дублирования**: `.path` предотвращает повторную загрузку при ререндере того же узла

### API взаимодействие
- **Endpoint**: `GET /api/chats/:chatId`
- **chatId**: используется `selectedNode.path` (например, `src/agents/dev_agent.py`)
- **Response**: `{ messages: ChatMessage[] }`

### Zustand actions
- `clearChat()` — очищает `chatMessages` в store
- `addChatMessage(msg)` — добавляет сообщение в `chatMessages`

## СВЯЗАННЫЕ КОМПОНЕНТЫ

- **FileCard** (client/src/components/canvas/FileCard.tsx) — вызывает `selectNode(id)` при клике
- **useStore** (client/src/store/useStore.ts) — управляет `selectedId` и `chatMessages`
- **ChatHistoryManager** (src/chat/chat_history_manager.py) — бэкенд для `/api/chats/:chatId`

## ЛОГИ

### Успешная загрузка истории
```
[ChatPanel] File changed to: src/agents/dev_agent.py
[ChatPanel] Loaded 5 messages for dev_agent.py
```

### Файл без истории
```
[ChatPanel] File changed to: src/utils/new_file.py
[ChatPanel] No history found for new_file.py, starting fresh
```

### Ошибка API
```
[ChatPanel] File changed to: src/broken.py
[ChatPanel] No history for broken.py: Failed to fetch
```

## ДАЛЬНЕЙШИЕ УЛУЧШЕНИЯ (опционально)

1. **Кэширование истории** — сохранять загруженные чаты в памяти для мгновенного переключения
2. **Индикатор загрузки** — показывать спиннер при загрузке истории
3. **Сохранение несохраненных сообщений** — предупреждать, если есть несохраненный контекст
4. **Группировка по директориям** — чаты на уровне папки, а не только файла

## СТАТУС
✅ **РЕАЛИЗОВАНО** — Phase 52.1 Complete
- Чат очищается при смене файла
- История загружается автоматически
- Плавная UX без конфликтов контекста
