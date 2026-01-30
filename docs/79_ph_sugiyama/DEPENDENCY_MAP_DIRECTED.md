# 🗺️ DEPENDENCY MAP: DIRECTED MODE

**Фокус:** Структура папок, иерархия глубин, формулы расстояний
**Mode:** `?mode=directory` (default)
**Визуализация:** Вертикальное дерево по структуре папок

---

## 🔄 DATA FLOW

```
VETKA PROJECT (disk)
    ↓
[rescan_project.py:402-406]
    parent_folder = os.path.dirname(rel_path)
    ↓
[Qdrant: vetka_elisya collection]
    payload: {path, name, parent_folder, depth, ...}
    ↓
[tree_routes.py:119-247] BUILD HIERARCHY
    folders = {}  ← структура папок
    files_by_folder = {}  ← файлы по папкам
    ↓
[fan_layout.py:334-642] CALCULATE POSITIONS
    Y = depth * Y_PER_DEPTH  ← ГЛАВНАЯ ФОРМУЛА
    X = sin(angle_rad) * adaptive_length
    ↓
[tree_routes.py:287-415] BUILD NODES & EDGES
    nodes = [root, folders, files]
    edges = [parent → child]
    ↓
[API Response] mode='directory'
    ↓
[Client/Canvas] 3D Visualization
```

---

## 📊 LAYER STRUCTURE: DIRECTED MODE

```
DEPTH 0 (ROOT):
┌─────────────────┐
│  VETKA (y=0)    │
└─────────────────┘
        ↓

DEPTH 1 (Top folders):
┌───────────┐  ┌───────────┐  ┌──────────┐
│ src       │  │ client    │  │ docs     │
│ (y=200)   │  │ (y=200)   │  │ (y=200)  │
└───────────┘  └───────────┘  └──────────┘
    ↓              ↓

DEPTH 2 (Subfolders):
┌─────────┐  ┌──────────┐  ┌────────┐
│api      │  │scanners  │  │layout  │
│(y=400)  │  │(y=400)   │  │(y=400) │
└─────────┘  └──────────┘  └────────┘
    ↓

DEPTH 3 (Sub-subfolders):
┌────────────┐  ┌──────────┐  ┌────────────┐
│handlers    │  │middleware│  │routes      │
│(y=600)     │  │(y=600)   │  │(y=600)     │
└────────────┘  └──────────┘  └────────────┘
    ↓

FILES (y = folder_y + FILE_SPACING offset):
📄 __init__.py (y≈600)
📄 utils.py (y≈600)
📄 models.py (y≈600)
```

---

## 🧮 CORE FORMULAS (DIRECTED MODE)

### Formula 1: Y-Position по глубине

**Файл:** `fan_layout.py:459`
**Формула:**
```
folder_y = depth * Y_PER_DEPTH
```

**Где:**
- `depth`: уровень папки (0=root, 1=src, 2=api, 3=handlers)
- `Y_PER_DEPTH`: расстояние между уровнями (адаптивное)

**Вычисление Y_PER_DEPTH:**
```python
# fan_layout.py:137-162
available_height = screen_height * 0.6  # 60% экрана
Y_PER_DEPTH = available_height / max(1, max_depth)
# Constraints: 80px ≤ Y_PER_DEPTH ≤ 200px
```

**Примеры:**
- max_depth=3 → Y_PER_DEPTH = (1080*0.6)/3 = 216px
- max_depth=6 → Y_PER_DEPTH = (1080*0.6)/6 = 108px
- max_depth=10 → Y_PER_DEPTH = (1080*0.6)/10 = 64.8px → зажимается до 80px min

---

### Formula 2: X-Position (Fan spread)

**Файл:** `fan_layout.py:443-491`
**Формула:**
```
folder_x = parent_x + sin(angle_rad) * adaptive_length
```

**Где:**
- `parent_x`: X родительской папки
- `angle_rad`: угол раскрытия (в радианах)
- `adaptive_length`: длина ветки (зависит от содержимого)

**Вычисление adaptive_length:**
```python
# fan_layout.py:25-82
density_factor = 1.0 + (files_count * 0.02)  # +2% за каждый файл
depth_decay = max(0.4, 1.0 - (depth / (max_depth + 1)))  # мин 40%
adaptive_length = BASE_RADIUS * density_factor * depth_decay
# BASE_RADIUS = 150px
```

**Примеры:**
- depth=0, files=0 → length = 150 * 1.0 * 1.0 = 150px
- depth=1, files=5 → length = 150 * 1.1 * 0.833 = 137px
- depth=5, files=20 → length = 150 * 1.4 * 0.4 = 84px

---

### Formula 3: Dynamic Fan Angle

**Файл:** `fan_layout.py:242-285`
**Формула:**
```
spread_factor = 1.0 - (depth / (max_depth + 1))
adaptive_max_angle = max(MIN_SPREAD, MAX_SPREAD * spread_factor)
# MIN_SPREAD = 45°
# MAX_SPREAD = 180°
```

**Результаты:**
- depth=0 (root): angle = 180° (максимальный раскрыв)
- depth=2: angle = max(45, 180 * 0.5) = 90°
- depth=5: angle = max(45, 180 * 0.2) = 45° (минимальный)

---

### Formula 4: File Spacing (в папке)

**Файл:** `fan_layout.py:113-135, 495-542`
**Формула:**
```
available = branch_length * 0.7
FILE_SPACING = available / files_count
# Constraints: 25px ≤ FILE_SPACING ≤ 50px

y_offset = (i - mid_index) * FILE_SPACING
file_y = folder_y + y_offset
```

**Примеры:**
- 1 файл в папке: y_offset = 0 → file_y = folder_y (**НАЛОЖЕНИЕ!**)
- 3 файла: FILE_SPACING ≈ 40px
  - файл 0: y_offset = -40px
  - файл 1: y_offset = 0px
  - файл 2: y_offset = +40px

---

### Formula 5: Anti-Gravity Repulsion

**Файл:** `fan_layout.py:168-240`
**Назначение:** Предотвратить наложение папок на одном depth-уровне

**Алгоритм:**
```python
for each pair of folders at same depth:
    distance = sqrt((xb - xa)² + (yb - ya)²)
    if distance < min_distance (150px):
        calculate repulsion force
        push folders apart
# Итеративно: 10 проходов
```

**Результат:** Папки на одном уровне равномерно распределены по X

---

## 🔗 FILE-TO-CODE MAPPING

### File: rescan_project.py

**Строка 402-406:** Вычисление parent_folder

```python
rel_path = os.path.relpath(file_path, PROJECT_ROOT)
depth = len(rel_path.split(os.sep))
parent_folder = os.path.dirname(rel_path)  # ← КЛЮЧ
```

**Результат:**
- `/Users/.../src/api/handlers/utils.py`
  - rel_path = `src/api/handlers/utils.py`
  - depth = 4
  - parent_folder = `src/api/handlers`
  - payload в Qdrant: `{path: ..., parent_folder: "src/api/handlers", depth: 4}`

---

### File: tree_routes.py

**Строка 119-247:** Построение иерархии

```python
# STEP 1: Прочитать из Qdrant (line 119-139)
all_files = scroll(collection_name='vetka_elisya')

# STEP 2: Группировать по parent_folder (line 167-246)
folders = {}
files_by_folder = {}

for point in all_files:
    parent_folder = point.payload['parent_folder']

    # Создать иерархию папок (line 229-245)
    parts = parent_folder.split('/')
    for i in range(len(parts)):
        folder_path = '/'.join(parts[:i+1])
        parent_path = '/'.join(parts[:i]) if i > 0 else None

        folders[folder_path] = {
            'path': folder_path,
            'name': parts[i],
            'parent_path': parent_path,
            'depth': i,
            'children': [...]
        }
```

**Результат:** Словарь папок с иерархией

---

### File: fan_layout.py

**Строка 334-642:** Главный алгоритм позиционирования

```python
def calculate_directory_fan_layout(folders, files_by_folder, ...):
    # STEP 1: Анализ датасета (line 390-416)
    max_depth = max(f['depth'] for f in folders.values())
    max_files_per_folder = max(len(files_by_folder[fp]) for fp in folders)

    # STEP 2: Адаптивные параметры (line 408-415)
    BRANCH_LENGTH = calculate_branch_length(max_depth, ...)
    Y_PER_DEPTH = calculate_layer_height_vertical(max_depth, ...)

    # STEP 3: Рекурсивный layout (line 423-491)
    def layout_subtree(folder_path, parent_x, parent_y, parent_angle, depth):
        folder_y = depth * Y_PER_DEPTH
        folder_x = parent_x + sin(angle_rad) * adaptive_length
        positions[folder_path] = {'x': folder_x, 'y': folder_y}

        # Рекурсивно: дети
        for child in folder['children']:
            layout_subtree(child, folder_x, folder_y, child_angle, depth+1)

        # Файлы
        for i, file in enumerate(files_by_folder[folder_path]):
            file_y = folder_y + (i - mid_index) * FILE_SPACING
            positions[file_id] = {'x': file_x, 'y': file_y}

    # STEP 4: Anti-gravity (line 564-640)
    calculate_static_repulsion(branches_by_depth, positions, ...)

    return positions
```

---

### File: tree_routes.py (response building)

**Строка 287-415:** Построение response

```python
# Line 291-300: Root node
nodes.append({
    'id': 'main_tree_root',
    'type': 'root',
    'name': 'VETKA',
    'visual_hints': {
        'layout_hint': {'expected_x': 0, 'expected_y': 0, 'expected_z': 0}
    }
})

# Line 308-341: Folder nodes
for folder_path, folder in folders.items():
    folder_id = f"folder_{hash(folder_path)}"
    pos = positions[folder_path]  # ← ИЗ fan_layout

    nodes.append({
        'id': folder_id,
        'type': 'branch',
        'name': folder['name'],
        'visual_hints': {
            'layout_hint': {
                'expected_x': pos['x'],
                'expected_y': pos['y']  # ← DIRECTED Y
            }
        }
    })

    edges.append({'from': parent_id, 'to': folder_id, 'semantics': 'contains'})

# Line 344-390: File nodes
for folder_path, folder_files in files_by_folder.items():
    for file_data in folder_files:
        pos = positions[file_data['id']]

        nodes.append({
            'id': file_data['id'],
            'type': 'leaf',
            'name': file_data['name'],
            'visual_hints': {
                'layout_hint': {
                    'expected_x': pos['x'],
                    'expected_y': pos['y']  # ← DIRECTED Y
                }
            }
        })

        edges.append({'from': folder_id, 'to': file_id, 'semantics': 'contains'})
```

---

## 🎨 CONSTANTS & PARAMETERS

| Константа | Значение | Файл | Строка |
|-----------|----------|------|--------|
| MIN_SPREAD | 45° | fan_layout.py | 19 |
| MAX_SPREAD | 180° | fan_layout.py | 20 |
| BASE_RADIUS | 150px | fan_layout.py | 21 |
| DEPTH_DECAY_FLOOR | 0.4 | fan_layout.py | 22 |
| FILE_SPACING | 25-50px | fan_layout.py | 134 |
| Y_PER_DEPTH | 80-200px | fan_layout.py | 161 |
| min_distance (repulsion) | 200px | fan_layout.py | 606 |

---

## 🧪 VERIFICATION POINTS

### ✅ Check 1: parent_folder correctness

```bash
curl -s "http://localhost:5001/api/tree/data?mode=directory" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); \
    files=[n for n in d['tree']['nodes'] if n['type']=='leaf']; \
    print('Sample files:'); \
    [print(f['name'], '→', f['parent_id'][:20]) for f in files[:3]]"
```

**Expected:** parent_id соответствует папке файла

---

### ✅ Check 2: Y-coordinates by depth

```bash
curl -s "http://localhost:5001/api/tree/data?mode=directory" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); \
    folders=[n for n in d['tree']['nodes'] if n['type']=='branch']; \
    for f in sorted(folders, key=lambda x: x['visual_hints']['layout_hint']['expected_y']): \
      y=f['visual_hints']['layout_hint']['expected_y']; \
      print(f'{f[\"name\"]:20} y={y:.0f}')"
```

**Expected:** Y растет по 200px (или other Y_PER_DEPTH)

---

### ✅ Check 3: Folder separation

```bash
# Два файла на depth=1 должны быть разделены X
curl ... | python3 -c "...get folders at depth 1...; \
  print(f'Folder 1 x={x1}, Folder 2 x={x2}'); \
  assert abs(x2-x1) > 150, 'Too close!'"
```

---

## 📝 KNOWN ISSUES (DIRECTED MODE)

### Issue 1: Single-file folders

**Проблема:** Когда в папке один файл (e.g., `__init__.py`), файл накладывается на папку
**Причина:** `mid_index = 0`, `y_offset = 0`, `file_y = folder_y`
**Статус:** ⚠️ ОТКРЫТО (Маркер B в аудите)

### Issue 2: Deep trees become narrow

**Проблема:** На depth=10 папки очень узкие (MIN_SPREAD=45°)
**Причина:** `adaptive_max_angle` падает с глубиной
**Статус:** ⚠️ ДИЗАЙН (не критичное)

### Issue 3: Anti-gravity не учитывает файлы

**Проблема:** Файлы не отталкиваются друг от друга
**Причина:** Repulsion только для папок (branches_by_depth)
**Статус:** 🟡 УЛУЧШЕНИЕ (не ломает функциональность)

---

## 🎯 DEPENDENCIES SUMMARY

```
rescan_project.py
    └─→ parent_folder = os.path.dirname(rel_path)
        └─→ Qdrant payload['parent_folder']
            └─→ tree_routes.py (read from Qdrant)
                └─→ build folder hierarchy (lines 167-246)
                    └─→ fan_layout.py (calculate positions)
                        ├─→ Y = depth * Y_PER_DEPTH
                        ├─→ X = sin(angle) * adaptive_length
                        └─→ Anti-gravity repulsion
                            └─→ tree_routes.py (build nodes/edges)
                                └─→ API Response (mode='directory')
                                    └─→ Client 3D Canvas
```

---

**Конец DIRECTED MODE документации.** ✅

Полная иерархия папок, все формулы, все зависимости. Режим готов к изучению и отладке.
