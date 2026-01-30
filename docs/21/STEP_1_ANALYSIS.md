# Phase 21-A: Step 1 - Анализ дублирования

**Дата:** 2025-12-28

## Файлы artifact_panel.js

| Файл | Строк | Функции | Используется |
|------|-------|---------|--------------|
| `frontend/static/js/artifact_panel.js` | 809 | 22 | Flask static_folder |
| `app/frontend/static/js/artifact_panel.js` | 219 | 6 | НЕ используется (old) |

### frontend/static/js/artifact_panel.js (НОВЫЙ - Phase 17-M)
```
attachFileClickHandlers()
openArtifactFromFile()
renderFileContent()
updateArtifactFooter()
initArtifactToolbar()
enableToolbarButtons()
toggleEditMode()
downloadArtifactContent()
toggleSearchBar()
highlightMatches()
clearHighlights()
navigateMatch()
refreshArtifactContent()
openCurrentFileExternal()
closeArtifactPanel()
toggleArtifactFullScreen()
initArtifactKeyboardShortcuts()
showToast()
escapeHtml()
openArtifact()
handleArtifactMessage()
sendArtifactMessage()

window.* exports:
- window.openArtifact
- window.openArtifactFromFile
- window.closeArtifactPanel
- window.closeArtifact (alias)
- window.toggleArtifactFullScreen
- window.attachFileClickHandlers
- window.sendArtifactMessage
- window.handleArtifactMessage
```

### app/frontend/static/js/artifact_panel.js (СТАРЫЙ)
```
openArtifact()
addHistoryRings()
closeArtifact()
sendArtifactMessage()
handleArtifactMessage()
escapeHtml()

window.* exports:
- window.openArtifact
- window.closeArtifact
- window.sendArtifactMessage
```

## Inline JS в tree_renderer.py

| Параметр | Значение |
|----------|----------|
| Начало скрипта | Строка 1905 |
| Конец скрипта | ~Строка 7800 |
| Всего строк inline JS | ~5896 |
| Функций (всего) | 189 |
| Artifact-функций | ~20 |

### Artifact-функции в tree_renderer.py (inline):
```javascript
shouldOpenArtifactPanel() - line 2287
openArtifactModal() - line 2300
showArtifactPanel() - line 2337
closeArtifactPanel() - line 2409
toggleArtifactFullScreen() - line 2431
createArtifactInTree() - line 2437
loadFileToArtifact() - line 2487
renderArtifactContent() - line 2554
updateArtifactFooter() - line 2584
saveArtifact() - line 2653
copyArtifact() - line 2700
downloadArtifact() - line 2710
refreshArtifact() - line 2726
toggleArtifactSearch() - line 2749
closeArtifactSearch() - line 2777
searchInArtifact() - line 2783
showArtifactToast() - line 2872
editArtifact() - line 2922
testArtifactPanel() - line 2928
toggleArtifactFromChat() - line 2971
VETKAArtifactPanel (object) - line 2994
```

## Flask конфигурация

```python
# main.py line 621
static_folder='frontend/static'
```

**Вывод:** Flask использует `frontend/static/`, а НЕ `app/frontend/static/`.
Старый файл `app/frontend/static/js/artifact_panel.js` НЕ используется.

## Проблемы найденные при анализе

### 1. Дублирование файлов
- `app/frontend/static/js/artifact_panel.js` - мёртвый код (219 строк)
- `frontend/static/js/artifact_panel.js` - активный код (809 строк)

### 2. Дублирование функций
Одинаковые функции определены в ДВУХ местах:
- `closeArtifactPanel()` - в artifact_panel.js И в tree_renderer.py
- `toggleArtifactFullScreen()` - в artifact_panel.js И в tree_renderer.py
- `showToast()` / `showArtifactToast()` - разные реализации
- `updateArtifactFooter()` - разные реализации

### 3. Огромный inline скрипт
- ~5896 строк JavaScript внутри Python файла
- 189 функций, из них ~20 artifact-связанных
- Сложно поддерживать и тестировать

### 4. Конфликтующие exports
- tree_renderer.py: `window.VETKAArtifactPanel`, `window.resetArtifactPanel`
- artifact_panel.js: `window.openArtifact`, `window.closeArtifactPanel`
- Могут перезаписывать друг друга

## Рекомендации

1. **УДАЛИТЬ:** `app/frontend/static/js/artifact_panel.js` (мёртвый код)
2. **ОСТАВИТЬ:** `frontend/static/js/artifact_panel.js` (809 строк)
3. **ПОСТЕПЕННО:** Вынести artifact-функции из tree_renderer.py
4. **НЕ ТРОГАТЬ:** Остальные 169 функций в tree_renderer.py

## Следующий шаг
Создать план рефакторинга в STEP_2_PLAN.md
