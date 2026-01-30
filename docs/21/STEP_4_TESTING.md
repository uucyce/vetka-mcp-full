# Phase 21-A: Step 4 - Тестирование

**Дата:** 2025-12-28

## Тесты

| # | Тест | Статус | Примечание |
|---|------|--------|------------|
| 1 | Клик на файл → artifact panel | ⏳ | attachFileClickHandlers() |
| 2 | View artifact в чате | ⏳ | openArtifactModal() |
| 3 | Кнопка << toggle | ⏳ | toggleArtifactFromChat() |
| 4 | Socket.IO open_artifact | ⏳ | window.openArtifact() |
| 5 | Approval View Diff | ⏳ | Phase 20 integration |

## Как тестировать

### Тест 1: Клик на файл
1. Открыть VETKA в браузере
2. Найти файл в tree view
3. Кликнуть один раз → должен открыться artifact panel
4. Двойной клик → должен открыться Finder

### Тест 2: View artifact в чате
1. Отправить сообщение агенту
2. Дождаться ответа с артефактом
3. Кликнуть "📄 View artifact" → должен открыться artifact panel

### Тест 3: Кнопка << toggle
1. Найти кнопку `<<` рядом с чатом
2. Кликнуть → панель должна открыться
3. Кликнуть `>>` → панель должна закрыться

### Тест 4: Socket.IO
В консоли браузера:
```javascript
socket.emit('open_artifact', {
    path: 'test.py',
    content: 'print("hello")',
    type: 'code'
});
```
Панель должна открыться с кодом.

### Тест 5: Approval View Diff
1. Дождаться approval request
2. Кликнуть "View Diff"
3. Artifact panel должен показать diff

## Результат

⏳ Ожидание тестирования в браузере

---

**Примечание:** Удалённый файл `app/frontend/static/js/artifact_panel.js` НЕ влияет на функционал, так как Flask использует `frontend/static/`.
