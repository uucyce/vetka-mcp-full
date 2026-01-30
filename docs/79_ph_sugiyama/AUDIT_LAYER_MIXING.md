# 🔍 AUDIT: Layer Mixing - Directed vs Knowledge Mode

**Дата:** 2026-01-21
**Статус:** РАЗВЕДКА (без исправлений)
**Уровень:** КРИТИЧЕСКИЙ - смешение двух слоев в одном эндпоинте

---

## 📋 EXECUTIVE SUMMARY

Обнаружено **смешение двух режимов на уровне API**, которое приводит к искажению визуализации:

- **DIRECTED MODE** (режим папок): `src/api → handlers, middleware, routes`
- **KNOWLEDGE MODE** (режим тегов): семантические кластеры независимо от структуры папок

**Проблема:** API параметр `mode` существует, но **не используется для выбора алгоритма позиционирования**.
Вместо этого **всегда** используется DIRECTED layout от `fan_layout.py`, даже когда должен быть KNOWLEDGE.

---

## 🎯 ROOT CAUSE ANALYSIS

### 📍 Маркер 1: tree_routes.py:78-82 - Параметр режима декларирован, но проигнорирован

```python
# tree_routes.py: 78-82
@router.get("/data")
async def get_tree_data(
    mode: str = Query("directory", description="Layout mode: directory, semantic, or both"),
    request: Request = None
):
```

✅ Параметр `mode` принимается
❌ **НЕ ИСПОЛЬЗУЕТСЯ** для условного выбора алгоритма

### 📍 Маркер 2: tree_routes.py:266-271 - Всегда используется DIRECTED layout

```python
# tree_routes.py: 266-271
positions, root_folders, BRANCH_LENGTH, FAN_ANGLE, Y_PER_DEPTH = calculate_directory_fan_layout(
    folders=folders,
    files_by_folder=files_by_folder,
    all_files=[],
    socketio_instance=None  # No socketio in FastAPI context
)
```

⚠️ **ЖЕСТКИЙ КОД** - независимо от `mode`, всегда вызывает `calculate_directory_fan_layout`.
❌ Когда `mode='semantic'` - должен вызывать `build_knowledge_graph_from_qdrant` или `calculate_knowledge_layout`.

### 📍 Маркер 3: tree_routes.py:400 - Mode в response, но координаты уже неправильные

```python
# tree_routes.py: 400
response = {
    ...
    'mode': mode,  # ← Возвращает режим, но позиции уже вычислены в DIRECTED!
    'tree': {
        ...
        'nodes': nodes,  # ← Все позиции из fan_layout (DIRECTED)
        'edges': edges   # ← Все edges из DIRECTED логики
    }
}
```

Клиент смотрит на `response['mode']` но **координаты узлов уже зафиксированы** в режиме DIRECTED.

---

## 🧬 DATA FLOW ISSUE

### Текущий (НЕПРАВИЛЬНЫЙ) поток:

```
USER REQUEST: ?mode=semantic
    ↓
API get_tree_data(mode="semantic")
    ↓
[🔴 IGNORED] mode параметр не проверяется
    ↓
calculate_directory_fan_layout()  ← ВСЕ файлы по структуре папок
    ↓
positions = {
    'src': (0, 0),
    'src/api': (50, 100),     ← Y по глубине папки (depth-based)
    'src/api/handlers': (100, 200),
    ...
}
    ↓
response['mode'] = "semantic"  ← ЛОЖ! Режим не matching координаты
response['tree']['nodes'] = [узлы с координатами DIRECTED]
```

### Правильный поток (ТРЕБУЕТСЯ):

```
USER REQUEST: ?mode=semantic
    ↓
API get_tree_data(mode="semantic")
    ↓
IF mode == "semantic":
    build_knowledge_graph_from_qdrant()  ← Семантические кластеры
    positions = {
        'tag_1': (x1, y1),  ← Y по knowledge_level, не по папкам
        'tag_2': (x2, y2),
        ...
    }
ELIF mode == "directory":
    calculate_directory_fan_layout()     ← Структура папок
    positions = {
        'src': (0, 0),  ← Y по глубине папки
        ...
    }
```

---

## 📊 LAYER DEFINITIONS

### ⭕ DIRECTED MODE (Папки)

**Источник:** `fan_layout.py:calculate_directory_fan_layout()`
**Координаты основаны на:**
- X: горизонтальный FAN (углы, fan spread)
- Y: **ГЛУБИНА ПАПКИ** × Y_PER_DEPTH (line 459)

```python
# fan_layout.py: 459
folder_y = depth * Y_PER_DEPTH  # Y = [0, 200, 400, 600, ...] по depth
```

**Структура:** `VETKA (root, y=0)` → `src (depth=1, y=200)` → `api (depth=2, y=400)` → ...

**РЕБРА:** `parent_id → child_id` (папка содержит подпапку)

---

### 🌐 KNOWLEDGE MODE (Теги)

**Источник:** `knowledge_layout.py:build_knowledge_graph_from_qdrant()`
**Координаты основаны на:**
- X, Y, Z: семантическое позиционирование (similarity-based)
- Y: **KNOWLEDGE LEVEL** файла, не глубина папки
- Кластеры: группы по semantic similarity, независимо от структуры папок

**Структура:** Теги (intake, API utils, Models, ...) → Файлы группированы семантически

**РЕБРА:** Semantic edges (prerequisite, similarity, contains)

---

## 🚨 СИМПТОМЫ СМЕШЕНИЯ

### На UI видишь:

1. **Две папки в одной точке:** `VETKA (root)` и `src (depth=1)` близко, потому что Y разница = 200px (небольшая)
2. **Ветки идут от `__init__.py`:** вероятно Z-fighting (наложение узлов)
3. **Структура похожа на Knowledge Mode, но координаты от Directed:** смешение логик

### Причины:

- Folder node at `y=200` (depth=1)
- File `__init__.py` in folder also at `y=200` (из-за вычисления в строке 519)
- На визуальном уровне файл и папка накладываются

```python
# fan_layout.py: 517-519
mid_index = (n_files - 1) / 2.0
y_offset = (i - mid_index) * FILE_SPACING
file_y = folder_y + y_offset  # ← Если n_files=1, то y_offset=0!
```

**Коментарий:** Когда в папке один файл, `y_offset=0`, поэтому файл точно на Y папки.

---

## 📝 KEY FORMULA DETECTION

### Formula 1: DIRECTED Y-Position (fan_layout.py)

```python
# Line 459
folder_y = depth * Y_PER_DEPTH
```

**Где:** `Y_PER_DEPTH = calculate_layer_height_vertical(max_depth, screen_height)`
**Результат:** Y зависит от глубины папки

---

### Formula 2: KNOWLEDGE Level (knowledge_layout.py:207-234)

```python
# knowledge_layout.py: 207-234
def compute_knowledge_level_enhanced(centrality_score, rrf_score, max_centrality):
    centrality_normalized = 1.0 - (centrality_score / (max_centrality + 1e-8))
    sigmoid = 1.0 / (1.0 + math.exp(-10 * (centrality_normalized - 0.5)))
    rrf_boost = rrf_score * 0.15
    kl = 0.1 + (sigmoid * 0.75) + rrf_boost
    return max(0.1, min(1.0, kl))
```

**Где:** `kl` ∈ [0.1, 1.0] (не связано с глубиной папки!)
**Результат:** Y должна быть основана на KL, не на depth

---

### Formula 3: File Spacing ADAPTIVE (knowledge_layout.py:242-293)

```python
# knowledge_layout.py: 277
file_spacing = BASE_FILE_SPACING * count_factor * variance_factor * kl_factor * depth_factor
```

**Факторы:**
- `count_factor`: зависит от кол-во файлов в кластере
- `variance_factor`: семантическое разнообразие
- `kl_factor`: разброс knowledge levels
- `depth_factor`: глубина (но в KNOWLEDGE mode, не папка-глубина!)

---

## 🔧 INTERFACE MAPPING

### API Response Format (tree_routes.py:397-415)

```python
response = {
    'format': 'vetka-v1.4',
    'source': 'qdrant',
    'mode': mode,                    # ← ПРОБЛЕМА: не matching позиции
    'tree': {
        'id': root_id,
        'name': 'VETKA',
        'nodes': nodes,              # ← Все с координатами DIRECTED
        'edges': edges,              # ← Все edges DIRECTED
        'metadata': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'total_files': len([n for n in nodes if n['type'] == 'leaf']),
            'total_folders': len(folders)
        }
    }
}
```

**Узел (Node) структура:**
```python
# Line 317-335 (Folder node)
{
    'id': folder_id,
    'type': 'branch',
    'name': folder['name'],
    'parent_id': parent_id,
    'metadata': {...},
    'visual_hints': {
        'layout_hint': {
            'expected_x': pos.get('x', 0),    # ← Из positions dict
            'expected_y': pos.get('y', 0),    # ← DIRECTED Y (depth-based)
            'expected_z': 0
        },
        'color': '#8B4513'
    }
}
```

---

## 🧭 LAYER SEPARATION REQUIREMENTS

### ✅ DIRECTED Mode должен:

1. **Читать:** `folders` dict (структура папок)
2. **Вычислять:** Y = depth × Y_PER_DEPTH
3. **Выносить:** edges как `parent_folder → child_folder`
4. **Файлы:** стекируются вертикально в папке (FILE_SPACING)

### ✅ KNOWLEDGE Mode должен:

1. **Читать:** семантические теги из embeddings
2. **Вычислять:** Y = KNOWLEDGE_LEVEL файла (не папка-глубина!)
3. **Выносить:** edges как семантические связи (similarity, prerequisite)
4. **Файлы:** группируются по кластерам (не по папкам)

---

## 🎨 VISUAL DIFFERENTIATION

**DIRECTED Mode координаты:**
```
VETKA (y=0)
  src (y=200)
    api (y=400)
      handlers (y=600)
      middleware (y=600)
```

**KNOWLEDGE Mode координаты:**
```
Tag: "API Utilities" (y=0.8, KL=0.8)
  ├─ file_1.py (y=0.75, KL=0.75)
  └─ file_2.py (y=0.82, KL=0.82)

Tag: "Data Models" (y=0.5, KL=0.5)
  └─ models.py (y=0.48, KL=0.48)
```

---

## 📌 ACTION MARKERS FOR CODER

### ⚠️ КРИТИЧЕСКИЙ Маркер A: tree_routes.py:78-420

**ПРОБЛЕМА:** API параметр `mode` декларирован но не используется

**МЕСТО:** `get_tree_data()` функция

**ЧТО ИСПРАВИТЬ:**
```python
# ТЕКУЩЕЕ (НЕПРАВИЛЬНОЕ):
@router.get("/data")
async def get_tree_data(mode: str = Query("directory", ...)):
    ...
    positions = calculate_directory_fan_layout(...)  # ← Всегда DIRECTED!
    ...
    response['mode'] = mode  # ← Лож

# ТРЕБУЕТСЯ:
@router.get("/data")
async def get_tree_data(mode: str = Query("directory", ...)):
    ...
    if mode == "knowledge":
        from src.layout.knowledge_layout import build_knowledge_graph_from_qdrant
        kg_data = build_knowledge_graph_from_qdrant(...)
        positions = kg_data['positions']  # ← KNOWLEDGE позиции
    elif mode == "directory":
        positions = calculate_directory_fan_layout(...)
    elif mode == "both":
        # Оба режима в одном response
        ...
    ...
    response['mode'] = mode  # ← Правда
```

**Строки для изменения:** 109-271, 400

---

### ⚠️ КРИТИЧЕСКИЙ Маркер B: fan_layout.py:513-519

**ПРОБЛЕМА:** Файлы с одним элементом получают Y папки (наложение)

**МЕСТО:** `layout_subtree()` → File positioning

**ТЕКУЩЕЕ:**
```python
# Line 517-519
mid_index = (n_files - 1) / 2.0
y_offset = (i - mid_index) * FILE_SPACING
file_y = folder_y + y_offset  # ← Когда n_files=1, y_offset=0!
```

**ПРОБЛЕМА:** `n_files=1` → `mid_index=0` → `y_offset=(0-0)*spacing=0` → `file_y = folder_y`

**ТРЕБУЕТСЯ ФОРМУЛА:** Гарантировать минимальный offset

---

### ⚠️ ИНФОРМАЦИОННЫЙ Маркер C: knowledge_layout.py:207-234

**ФОРМУЛА:** `compute_knowledge_level_enhanced()` - это Y основа для KNOWLEDGE mode

**ИСПОЛЬЗУЕТСЯ:** в режиме, когда файлы позиционируются по KL, а не по папкам

**КРИТИЧНО:** Убедиться, что позиции используют `knowledge_level`, а не `depth`

---

## 📐 DEVELOPMENT HISTORY RECONSTRUCTION

### Vanilla версия (ДО):

- Обе формулы (DIRECTED и KNOWLEDGE) были в одном файле
- Вероятно, была ошибка в переключении режимов
- Вероятно, Y-координаты путались между depth и KL

### React версия (СЕЙЧАС):

- Формулы разделены: `fan_layout.py` (DIRECTED) vs `knowledge_layout.py` (KNOWLEDGE)
- **ОДНАко:** API не переключается между ними!
- `tree_routes.py` всегда использует DIRECTED

### Требуется (БУДУЩЕЕ):

- Условное применение формул в зависимости от `mode`
- Отдельные node/edge structures для каждого режима
- Frontend переключатель режимов (UI toggle)

---

## 🧪 VERIFICATION CHECKLIST

- [ ] `mode` параметр используется в `get_tree_data()`?
- [ ] Есть условия `if mode == "knowledge"` vs `elif mode == "directory"`?
- [ ] `calculate_directory_fan_layout()` вызывается только при `mode != "knowledge"`?
- [ ] `build_knowledge_graph_from_qdrant()` возвращает координаты по KL, не по depth?
- [ ] Node positions в response matching режиму?
- [ ] Edge структура (semantics) соответствует режиму?
- [ ] UI получает и обрабатывает режим правильно?

---

## 📚 RELATED FILES

- `src/api/routes/tree_routes.py` - API layer (ТОЧКА ВХОДА)
- `src/layout/fan_layout.py` - DIRECTED Mode formulas
- `src/layout/knowledge_layout.py` - KNOWLEDGE Mode formulas
- `client/src/components/canvas/TreeEdges.tsx` - Визуализация (клиент)
- `scripts/rescan_project.py` - parent_folder вычисление (line 402-406)

---

## 🎯 NEXT STEPS FOR CODER

1. **Разделить логику:** Добавить условие на режим в `get_tree_data()`
2. **Привести координаты:** Убедиться, что каждый режим возвращает правильные Y
3. **Тестировать:** `?mode=directory` vs `?mode=knowledge`
4. **UI:** Добавить переключатель режимов на фронтенде
5. **Документировать:** Обновить API docs с двумя режимами

---

**Конец аудита. Маркеры готовы для кодера. Режимы разделены, стратегия ясна.** ✅
