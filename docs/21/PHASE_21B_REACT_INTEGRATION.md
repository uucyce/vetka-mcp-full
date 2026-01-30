# Phase 21-B: React Artifact Panel Integration (v2)

**Дата:** 2025-12-28
**Статус:** Ready for Testing
**Подход:** Hybrid (React для файлов, Vanilla для артефактов чата)

## Архитектура

### Гибридный подход
Вместо полной замены vanilla JS на React, используется **гибридный режим**:

| Сценарий | Режим | Компонент |
|----------|-------|-----------|
| Клик на файл в дереве | **React Panel** | iframe + ?file= параметр |
| Артефакт из чата | **Vanilla JS** | div#artifact-content |
| Toggle << кнопка | **Vanilla JS** | div#artifact-content |

### Почему не PostMessage?
PostMessage не работает между разными origins (localhost:8080 → localhost:5173).
Решение: используем URL параметр `?file=` для передачи пути файла.

## Изменения в tree_renderer.py

### 1. HTML - добавлен iframe (рядом с vanilla div)

```html
<div id="artifact-panel" class="artifact-panel hidden">
    <div class="artifact-header">...</div>

    <!-- Vanilla mode (for chat artifacts) -->
    <div class="artifact-content" id="artifact-content">
        <!-- Content rendered by vanilla JS -->
    </div>

    <!-- React mode (for file viewing) - Phase 21-B -->
    <iframe
        id="artifact-panel-iframe"
        src="about:blank"
        class="artifact-iframe hidden"
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
    ></iframe>

    <div class="artifact-footer">...</div>
</div>
```

### 2. JS - новые функции переключения режимов

```javascript
const REACT_PANEL_URL = 'http://localhost:5173';

// Switch to React Panel mode
function showReactPanel(filePath) {
    contentDiv.style.display = 'none';
    iframe.style.display = 'block';
    iframe.src = REACT_PANEL_URL + '?file=' + encodeURIComponent(filePath);
}

// Switch to Vanilla mode
function showVanillaPanel() {
    iframe.style.display = 'none';
    iframe.src = 'about:blank';
    contentDiv.style.display = 'block';
}
```

### 3. loadFileToArtifact() - теперь использует React Panel

```javascript
async function loadFileToArtifact(relPath) {
    // Show panel
    panel.classList.remove('hidden');

    // Use React Panel for file viewing
    showReactPanel(relPath);

    // Hide vanilla footer (React Panel has its own)
    footer.style.display = 'none';
}
```

### 4. showArtifactPanel() - остаётся vanilla

```javascript
function showArtifactPanel(content, type, agent, nodeId, nodePath) {
    // Switch to vanilla mode
    showVanillaPanel();

    // Render content in vanilla div
    contentDiv.innerHTML = '...';

    // Show vanilla footer
    footer.style.display = 'flex';
}
```

### 5. closeArtifactPanel() - очищает оба режима

```javascript
function closeArtifactPanel() {
    // Hide panel
    panel.style.display = 'none';

    // Reset React iframe
    iframe.src = 'about:blank';

    // Restore vanilla visibility
    contentDiv.style.display = 'block';
    footer.style.display = 'flex';
}
```

## Тестирование

### Требования
1. React Panel dev server: `cd app/artifact-panel && npm run dev`
2. VETKA server: `python main.py`

### Тест-кейсы

| # | Тест | Ожидаемый результат |
|---|------|---------------------|
| 1 | Клик на файл в дереве | Открывается React Panel в iframe |
| 2 | "📄 View artifact" в чате | Открывается vanilla panel |
| 3 | Закрыть панель | Оба режима сбрасываются |
| 4 | Переключение файл→артефакт | Корректная смена режима |

### Консольные тесты

```javascript
// Тест 1: Открыть файл в React Panel
loadFileToArtifact('src/main.py');

// Тест 2: Проверить iframe
document.getElementById('artifact-panel-iframe').src;
// Должно быть: http://localhost:5173?file=src/main.py

// Тест 3: Открыть артефакт (vanilla)
showArtifactPanel('print("hello")', 'code', 'Dev');

// Тест 4: Закрыть
closeArtifactPanel();
```

## Откат

```bash
git checkout src/visualizer/tree_renderer.py
```

## Следующие шаги

1. **Production build**: `cd app/artifact-panel && npm run build`
2. **Настройка URL**: Заменить `localhost:5173` на production path
3. **Интеграция Flask**: Добавить статический роут для React Panel build
