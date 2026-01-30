# Phase 69.3: UnifiedSearchBar Deep Audit

## Дата: 2026-01-19
## Статус: AUDIT COMPLETE — Ready for Implementation

---

## EXECUTIVE SUMMARY

Поиск РАБОТАЕТ, но с критическими пробелами:
1. **Metadata не передаётся** — `created_time`, `modified_time` = 0, `size` отсутствует
2. **Filter UI отсутствует** — кнопка была убрана/потеряна
3. **Display неполный** — не показывает size/date в списке результатов

---

## ПРОБЛЕМЫ НАЙДЕНЫ

### [CRITICAL-1] Metadata Lost in Pipeline

**Путь данных:**
```
Qdrant payload → hybrid_search.py → rrf_fusion.py → search_handlers.py → Frontend
                     ↓                    ↓
              Теряется metadata      Теряется metadata
```

**Файлы для исправления:**
| Файл | Функция | Строки | Проблема |
|------|---------|--------|----------|
| `src/search/hybrid_search.py` | `_semantic_search()` | 320-362 | Не извлекает metadata из Qdrant |
| `src/search/rrf_fusion.py` | `normalize_results()` | 79-89 | Не копирует metadata fields |

### [CRITICAL-2] Size Never Indexed

**Проблема:** `size` не хранится в Qdrant payload при индексации.

**Файлы для исправления:**
| Файл | Функция | Что добавить |
|------|---------|-------------|
| `src/scanners/qdrant_updater.py` | `update_file()` | `'size': stat.st_size` в metadata |

### [UX-1] Filter Button Missing

**Было:** Dropdown с date/name/size/type фильтрами
**Сейчас:** Только Sort dropdown, Filter кнопка исчезла

**Файл:** `client/src/components/search/UnifiedSearchBar.tsx`

### [UX-2] Results Display Incomplete

**Finder показывает:** Name | Size | Kind | Date Last Opened
**VETKA показывает:** Name | Path | Relevance%

**Нужно добавить:**
- Size (форматированный: KB/MB)
- Modified date (локализованный)
- Type icon справа при sort by type

---

## МАРКЕРЫ ДЛЯ РЕАЛИЗАЦИИ

### [MARKER-A] Backend: Fix Metadata Pipeline

```python
# src/search/hybrid_search.py:320-362
# В _semantic_search() после получения результатов:
for r in results:
    r['created_time'] = r.get('created_time') or r.get('_raw', {}).get('created_time', 0)
    r['modified_time'] = r.get('modified_time') or r.get('_raw', {}).get('modified_time', 0)
    r['size'] = r.get('size') or r.get('_raw', {}).get('size', 0)
```

```python
# src/search/rrf_fusion.py:79-89
# В normalize_results() добавить:
normalized.append({
    'id': doc_id,
    'score': float(score),
    'source': source,
    'path': result.get('path', ''),
    'name': result.get('name', ''),
    'content': result.get('content', ''),
    'created_time': result.get('created_time', 0),  # ← ADD
    'modified_time': result.get('modified_time', 0),  # ← ADD
    'size': result.get('size', 0),  # ← ADD
    '_raw': result
})
```

### [MARKER-B] Indexer: Add Size to Payload

```python
# src/scanners/qdrant_updater.py в update_file() около строки 230:
metadata = {
    'type': 'scanned_file',
    'source': 'incremental_updater',
    'path': str(file_path),
    'name': file_path.name,
    'extension': file_path.suffix.lower(),
    'size_bytes': stat.st_size,  # ← RENAME from size_bytes to size
    'size': stat.st_size,  # ← ADD для совместимости
    'modified_time': stat.st_mtime,
    'created_time': created_time,  # ← ADD (birthtime or ctime)
    ...
}
```

### [MARKER-C] Frontend: Add Filter Button

```typescript
// UnifiedSearchBar.tsx около строки 850
// После Sort button, добавить Filter button с dropdown:
// - By Type: All | Code | Docs | Config | Data
// - By Path: Contains input
// - By Date: Today | Week | Month | All
```

### [MARKER-D] Frontend: Enhance Results Display

```typescript
// UnifiedSearchBar.tsx строки 959-981
// Добавить отображение size и date в resultRight:

{/* Size display */}
<span style={{ color: '#555', fontSize: '10px', minWidth: '50px', textAlign: 'right' }}>
  {result.size ? formatBytes(result.size) : ''}
</span>

{/* Date display */}
<span style={{ color: '#555', fontSize: '10px', minWidth: '70px', textAlign: 'right' }}>
  {result.modified_time ? formatDate(result.modified_time) : ''}
</span>
```

### [MARKER-E] Frontend: Widen Search Container

```typescript
// UnifiedSearchBar.tsx около строки 720
// Изменить ширину контейнера:
maxWidth: '420px',  // было 350px
minWidth: '320px',  // было 280px
```

---

## СТИЛИСТИКА (Batman/Nolan + IKEA)

### Цвета (сохранить):
- Background: `#0f0f0f`, `#1a1a1a`
- Borders: `#333`, `#444`
- Text: `#ccc` (primary), `#888` (secondary), `#555` (tertiary)
- Accent: `#666` (hover), `#888` (active)

### Размеры (оптимизировать):
- Font: 11px (name), 10px (path, meta)
- Padding: 6px (compact), 8px (normal)
- Gap: 6px между элементами
- Border-radius: 3px (buttons), 4px (containers)

### Анимации:
- Transition: 0.15s ease
- Hover: opacity или background change
- No bouncing, no sliding

---

## ПРИМЕРЫ UI

### Текущий Result Item:
```
[icon] filename.py                    87%
       /path/to/file
```

### Улучшенный Result Item (Finder-style):
```
[icon] filename.py          12.5KB  Jan 19  87%
       /path/to/file
```

### Filter Dropdown:
```
┌─────────────────────┐
│ Type                │
│ ○ All               │
│ ○ Code (.py .ts .js)│
│ ○ Docs (.md .txt)   │
│ ○ Config (.json .yml│
├─────────────────────┤
│ Date                │
│ ○ Any time          │
│ ○ Today             │
│ ○ This week         │
│ ○ This month        │
└─────────────────────┘
```

---

## ПРИОРИТЕТЫ

| # | Маркер | Описание | Сложность | Влияние |
|---|--------|----------|-----------|---------|
| 1 | MARKER-A | Fix metadata pipeline | Low | 🔴 Critical |
| 2 | MARKER-B | Add size to indexer | Low | 🔴 Critical |
| 3 | MARKER-D | Enhance results display | Medium | 🟡 High |
| 4 | MARKER-E | Widen container | Low | 🟡 High |
| 5 | MARKER-C | Add filter UI | Medium | 🟢 Medium |

---

## CHECKLIST

```
[ ] MARKER-A: Backend metadata pipeline
[ ] MARKER-B: Indexer adds size
[ ] MARKER-C: Filter button UI
[ ] MARKER-D: Results display (size, date)
[ ] MARKER-E: Wider container
[ ] Re-index files to populate size
[ ] Test search shows metadata
[ ] Test filter works
```

---

## ДОПОЛНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ

### Найденные проблемы (не относящиеся к поиску):
1. **WebSocket reconnect** — React StrictMode double-mount (dev only, не критично)
2. **borderColor style warning** — CSS shorthand conflict (косметика)
3. **Performance violations** — RAF handlers >50ms (оптимизация позже)

### Архитектурные улучшения (будущее):
1. **Faceted search** — фильтры по extension, path prefix
2. **Search history** — последние запросы
3. **Saved searches** — закладки на частые запросы
4. **Fuzzy matching** — опечатки в filename

---

## ГОТОВ К РЕАЛИЗАЦИИ

Audit завершён. Все проблемы идентифицированы, маркеры расставлены.
Ожидаю подтверждения на Phase 69.4 Implementation.
