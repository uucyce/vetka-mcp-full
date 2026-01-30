# Grok Research: Anti-Gravity & Collision Avoidance для Interactive VETKA Tree
**Проект:** VETKA (Visual Enhanced Tree Knowledge Architecture)  
**Дата:** 20 декабря 2025  
**Задача:** Найти формулы для anti-gravity и collision avoidance между файлами/ветками

---

## 📋 КОНТЕКСТ

Мы используем **Sugiyama layered layout** с:
- Y-ось: слои (по глубине), файлы распределяются вертикально по времени
- X-ось: папки в одном слое распределены центрировано
- Z-ось: только для rotation (поворота ветки)

**Уже есть формулы от Грока (декабрь 2025):**
- `LAYER_HEIGHT = screen_height * 0.8 / max_depth * file_factor`
- `LAYER_SPACING = (screen_width - margin) / (max_folders - 1)`
- `FILE_SPACING = layer_height * 0.7 / files_count`

**Проблема:** Это статические формулы. Когда пользователь хочет **двигать ветки вручную** (drag-and-drop), нужны **динамические formulas** для:
1. Предотвращения пересечений файлов из разных папок
2. Отталкивания других веток/файлов при dragging
3. Сохранения "очевидности" структуры

---

## 🎯 ТРЕБОВАНИЕ 1: Minimum Spacing между файлами в разных колонках

### Проблема:
```
Папка A    Папка B
  file1      file1
  file2      file2
  file3      file3

Если X_A и X_B близко, то file1_A может визуально слиться с file1_B
(особенно если карточка файла широкая ~50px)
```

### Входные данные:
- `folder_x_a`, `folder_x_b` = X-позиции двух папок
- `file_card_width` = ширина карточки файла (~50-80px)
- `min_visual_gap` = минимальный зазор визуально (~10px)

### Выходное требование:
```
Карточки файлов не должны касаться друг друга.
Расстояние между краями карточек >= min_visual_gap (обычно 10-20px)
```

### Формула (что ищем):
```python
def check_file_collision(folder_x_a, folder_x_b, file_card_width, min_gap=10):
    """
    Проверить пересекаются ли файловые колонки двух папок
    
    Картинка:
    
    Папка A (center X_A)     Папка B (center X_B)
    ├─ file [X_A-W/2, X_A+W/2]  ├─ file [X_B-W/2, X_B+W/2]
    
    Distance между их центрами: abs(X_A - X_B)
    Минимальное расстояние чтобы не касались: 
        min_distance = file_card_width + min_gap
    """
    distance = abs(folder_x_b - folder_x_a)
    min_distance = file_card_width + min_gap
    
    if distance < min_distance:
        return True  # Collision detected
    return False

def calculate_repulsion_force(folder_x_a, folder_x_b, file_card_width, min_gap=10):
    """
    Вычислить, на сколько надо раздвинуть две папки чтобы файлы не касались
    
    Возвращает сдвиг по X для каждой папки (в противоположные стороны)
    """
    distance = abs(folder_x_b - folder_x_a)
    min_distance = file_card_width + min_gap
    
    if distance >= min_distance:
        return 0  # No repulsion needed
    
    # Нужно раздвинуть на эту разницу
    overlap = min_distance - distance
    # Каждая папка сдвигается на половину overlap
    return overlap / 2
```

**Вопрос для Grok:**
- Это правильная формула для collision detection?
- Есть ли более сложная (с учетом высоты файлов, не только ширины)?
- Нужно ли учитывать наклон ветки (Z rotation)?

---

## 🎯 ТРЕБОВАНИЕ 2: Interactive Dragging с Repulsion Forces

### Проблема:
```
User тащит ветку A за один из узлов.
Близлежащие ветки B, C, D должны отталкиваться, сохраняя структуру.

         →→ Drag
    B   A   C
    |\ /|  /|
    | X | / |   ← A движется, B, C, D отталкиваются?
    |/ \| \  |
    D   E   F
```

### Входные данные:
- `moved_node_x_new` = новая X позиция перемещаемого узла
- `nearby_nodes` = ближайшие соседи (в радиусе, например 200px)
- `min_distance` = минимальное расстояние между узлами

### Выходное требование:
```
1. Moved node движется в новую позицию
2. Соседние nodes плавно отталкиваются (не резко)
3. Отталкивание пропорционально расстоянию (ближе = сильнее)
4. Плавное, не создаёт рывков
```

### Формулы (что ищем):

```python
def calculate_repulsion_force_interactive(moved_x, nearby_node_x, min_distance=100, max_distance=300):
    """
    Сила отталкивания between moved node и соседом.
    
    Классическая модель из force-directed layouts:
    
    F = k * (moved_x - nearby_x) / distance^2
    
    Где:
    - k = repulsion coefficient (обычно 50-200)
    - distance = |moved_x - nearby_x|
    - Если distance < min_distance: сильное отталкивание
    - Если distance > max_distance: отталкивание = 0
    """
    distance = abs(moved_x - nearby_node_x)
    
    # Если уже далеко, не отталкиваем
    if distance > max_distance:
        return 0
    
    # Если очень близко, максимальное отталкивание
    if distance < min_distance:
        distance = min_distance  # Avoid division by zero
    
    # Repulsion coefficient
    k = 100  # Можно настраивать
    
    # Сила пропорциональна расстоянию к moved node
    direction = 1 if nearby_node_x < moved_x else -1  # Отталкивается в сторону
    force = direction * k / (distance * distance)
    
    return force

def update_nearby_nodes_positions(moved_node_x, moved_node_x_new, nearby_nodes, positions):
    """
    Обновить позиции nearby nodes когда user тащит moved_node
    
    Алгоритм:
    1. Вычислить смещение: delta_x = moved_node_x_new - moved_node_x
    2. Для каждого соседа:
       - Вычислить repulsion force
       - Новая позиция: neighbor_x_new = neighbor_x + repulsion_force * damping
    3. Проверить collision с другими соседями (iterative relaxation)
    """
    delta_x = moved_node_x_new - moved_node_x
    damping = 0.5  # Сила отталкивания уменьшается в 2 раза (плавнее)
    
    for neighbor in nearby_nodes:
        neighbor_x_old = positions[neighbor['id']]['x']
        
        # Calculate repulsion
        repulsion = calculate_repulsion_force_interactive(
            moved_node_x_new,
            neighbor_x_old,
            min_distance=100,
            max_distance=300
        )
        
        # Apply damping and update
        neighbor_x_new = neighbor_x_old + repulsion * damping
        positions[neighbor['id']]['x'] = neighbor_x_new
    
    # Optional: iterative relaxation for N iterations to settle
    for iteration in range(3):
        for i, neighbor_i in enumerate(nearby_nodes):
            for neighbor_j in nearby_nodes[i+1:]:
                # Check collision between neighbor_i and neighbor_j
                # Apply repulsion between them (not involving moved_node)
                pass
```

**Вопрос для Grok:**
- Это правильная модель repulsion forces?
- Есть ли более эффективная (с velocity, не только position)?
- Как выбрать правильные значения k (repulsion coefficient) и damping?
- Нужна ли iterative relaxation или одного прохода достаточно?

---

## 🎯 ТРЕБОВАНИЕ 3: Anti-Gravity между группами файлов

### Проблема:
```
Внутри одной папки есть 20 файлов - они группируются вертикально.
Соседние папки (их файлы) не должны смешиваться с этой группой.

Например:
Папка A     Папка B
(20 files)  (5 files)

Группа A занимает большое Y-пространство.
Группа B не должна "залезать" в это пространство.
```

### Входные данные:
- `folder_a_files_count` = 20
- `folder_b_files_count` = 5
- `file_spacing` = 30px (расстояние между файлами)
- `file_card_height` = 50px

### Выходное требование:
```
Каждая группа файлов занимает свою Y-область.
Области не пересекаются (с margin).
Размер области = file_spacing * files_count + file_card_height
```

### Формула (что ищем):

```python
def calculate_group_bounding_box(folder_x, folder_y, files_count, file_spacing, file_card_height=50):
    """
    Вычислить "коробку" занимаемую группой файлов.
    
    Картинка:
    
    Папка центр: (folder_x, folder_y)
    
    ┌─────────────────┐  ← y_min = folder_y
    │  file 1         │
    │  file 2         │
    │  file 3         │
    │  ...            │
    │  file N         │
    └─────────────────┘  ← y_max = folder_y + files_count * file_spacing
    
    x_min = folder_x - file_card_width/2
    x_max = folder_x + file_card_width/2
    """
    file_card_width = 50  # Обычная ширина
    
    x_min = folder_x - file_card_width / 2
    x_max = folder_x + file_card_width / 2
    
    y_min = folder_y
    y_max = folder_y + files_count * file_spacing
    
    return {
        'x_min': x_min, 'x_max': x_max,
        'y_min': y_min, 'y_max': y_max,
        'width': x_max - x_min,
        'height': y_max - y_min
    }

def check_group_collision(group_a, group_b, margin=10):
    """
    Проверить пересекаются ли две группы файлов
    (с учётом margin)
    """
    # AABB collision detection
    collision_x = (group_a['x_max'] + margin >= group_b['x_min'] and 
                   group_a['x_min'] - margin <= group_b['x_max'])
    
    collision_y = (group_a['y_max'] + margin >= group_b['y_min'] and 
                   group_a['y_min'] - margin <= group_b['y_max'])
    
    return collision_x and collision_y

def calculate_group_repulsion(group_a, group_b, folder_a, folder_b, margin=10):
    """
    Вычислить, на сколько раздвинуть две группы.
    
    Если они пересекаются, раздвигаем по X (не по Y, Y фиксирована слоями!)
    """
    if not check_group_collision(group_a, group_b, margin):
        return 0  # No repulsion needed
    
    # Overlap по X
    overlap_x = min(group_a['x_max'], group_b['x_max']) - max(group_a['x_min'], group_b['x_min'])
    
    if overlap_x > 0:
        # Раздвигаем на половину overlap
        return overlap_x / 2
    
    return 0
```

**Вопрос для Grok:**
- Правильный AABB (axis-aligned bounding box) подход?
- Надо ли учитывать Z rotation (наклон ветки)?
- Как рассчитать оптимальное margin между группами?

---

## 📊 СВОДНАЯ ТАБЛИЦА

| Что | Входные данные | Формула | Выход |
|-----|---|---|---|
| **File collision** | `X_A, X_B, file_width` | `distance > file_width + gap` | Boolean |
| **Repulsion force** | `moved_x, neighbor_x` | `k / distance^2` | Force (float) |
| **Group bbox** | `folder_x, files_count, spacing` | AABB coords | Rect |
| **Group collision** | `group_a, group_b` | AABB intersection | Boolean |

---

## 🎓 BACKGROUND

### Классические алгоритмы для reference:
1. **Force-directed (Fruchterman-Reingold)** - используется в D3, Gephi
2. **AABB Collision Detection** - стандарт в игровых engines
3. **Repulsion (inverse-square law)** - как в физике (гравитация)
4. **Damping & Velocity Verlet** - для плавных анимаций

### Почему это нужно:
- **File collision** = визуальная читаемость (макушки не касаются)
- **Interactive repulsion** = естественное ощущение при drag-and-drop
- **Anti-gravity** = структура не распадается при манипуляции

---

## 🎯 ИТОГОВЫЕ ВОПРОСЫ ДЛЯ GROK

1. **Для File Collision:**
   - Правильна ли моя формула проверки пересечения?
   - Надо ли учитывать height файловой карточки или только width?

2. **Для Interactive Repulsion:**
   - Какие оптимальные значения k (100-200?) и damping (0.3-0.7?)?
   - Нужна ли iterative relaxation (N итераций) или одного прохода достаточно?
   - Как избежать "качаний" (oscillations) при dragging?

3. **Для Anti-Gravity Groups:**
   - AABB - правильный выбор или better approach?
   - Как вычислить optimal margin между группами файлов?
   - Нужно ли пересчитывать bounding boxes каждый frame или можно кэшировать?

4. **General:**
   - Есть ли unified formula для всех трёх случаев (file/interactive/group)?
   - Какие performance considerations?
   - Как интегрировать с Sugiyama layered layout (чтобы не ломали слои)?

---

## 📝 ФОРМАТ ОТВЕТА

Grok, дай ответ как:

```markdown
## 1. File Collision Detection

### Recommended Formula:
[формула]

### Implementation:
[Python код]

### Constraints:
- k_repulsion = 100-200
- damping = 0.3-0.7
- ...

---

## 2. Interactive Dragging Repulsion

### Recommended:
[формула]

### Implementation:
[Python код]

---

## 3. Group Anti-Gravity

### Recommended:
[формула]

### Implementation:
[Python код]

---

## Unified Approach

Можно ли это объединить в одну систему?
```

---

**Grok, твой ответ будет основой для Phase 14 Final: Interactive VETKA!** 🚀
