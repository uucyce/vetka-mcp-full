# VETKA × Sugiyama: Математика без пересечений веток
**Для:** Grok Research  
**Задача:** Найти формулы для расстояний между узлами в Radial Sugiyama, которые **гарантируют отсутствие пересечений** веток при вертикальном размещении файлов

---

## 🎯 Задача

В иерархической визуализации дерева нужно расставить папки и файлы так, чтобы:

1. **Папки** расположены радиально веером от родителя
2. **Файлы** расположены вертикально по Y (старые внизу, новые вверху)
3. **Ветки (рёбра) не пересекаются** между собой
4. **Максимальная длина пути** определяет общую высоту дерева

---

## 📐 Геометрия и параметры

### Исходные параметры:

```
LAYER_HEIGHT = 80px          # Расстояние между уровнями глубины
BRANCH_BASE_LENGTH = 120px   # Базовая длина ветки на глубине 0
BRANCH_DEPTH_MULT = 60px     # Дополнительная длина на каждый уровень глубины

MAX_ANGLE_SPREAD = 90°       # Максимальный угол развёртки веера
FILE_SPACING = 40px          # Расстояние между файлами по Y
RADIAL_GAP = 20px            # Минимальное расстояние между соседними ветками
```

### Расчёт длины ветки по глубине:

```
BranchLength(depth) = BRANCH_BASE_LENGTH + depth * BRANCH_DEPTH_MULT

Пример:
- Глубина 0 (root → Documents): 120px
- Глубина 1 (Documents → VETKA_Project): 120 + 60 = 180px
- Глубина 2 (VETKA_Project → docs): 120 + 120 = 240px
```

---

## 🔄 Распределение углов без пересечений

### Проблема пересечения веток

Если папки расположены под одним родителем углами θ₁, θ₂, ... θₙ, то ветки могут пересечься если соседние углы слишком близко.

**Условие отсутствия пересечения:**

```
Δθ (угол между соседними ветками) ≥ θ_min_safe(n_siblings)

где θ_min_safe зависит от:
- Длины веток (длинные ветки требуют больший угловой зазор)
- Количества соседних папок (n_siblings)
- Максимального радиуса файлов под папкой
```

### Адаптивное распределение углов (Adaptive Fan-Out)

Для n соседних папок:

```
Δθ (adaptive) = MIN_ANGLE_GAP + k * BranchLength / RADIAL_MULTIPLIER

где:
- MIN_ANGLE_GAP ≈ 15° (минимальный угловой зазор между соседями)
- k ≈ 0.05 (коэффициент масштабирования)
- BranchLength = длина ветки родителя
- RADIAL_MULTIPLIER ≈ 500 (масштабный коэффициент)

Пример:
  BranchLength = 180px
  Δθ = 15° + 0.05 * 180 / 500 = 15° + 0.018° ≈ 15°

  Для 6 соседних папок:
  Углы: -45°, -30°, -15°, 0°, +15°, +30°, +45° (распределены по 15°)
  Total spread = 90° (укладывается в MAX_ANGLE_SPREAD)
```

**Формула позиции папки (folder):**

```
angle_parent_to_child = (parent_angle) + 
                        (child_index - n_children/2) * Δθ(adaptive)

x = parent_x + cos(angle) * BranchLength(depth)
y = parent_y + sin(angle) * BranchLength(depth) * Y_COMPRESSION

где Y_COMPRESSION ≈ 0.3 (сжатие вертикальной составляющей)
```

---

## 📏 Ограничение радиуса файловой облака

Под каждой папкой расположено облако файлов (вертикальная стопка). Это облако занимает пространство.

### Радиус файловой облака:

```
FileCloudRadius(n_files) = 
    if n_files ≤ 10:
        FILE_RADIUS_SMALL = 30px
    elif n_files ≤ 30:
        FILE_RADIUS_MED = 50px
    else:
        FILE_RADIUS_LARGE = 70px

File Y-extent = (n_files - 1) * FILE_SPACING / 2
File Y-spread = FILE_Y_EXTENT (от -extent до +extent относительно папки Y)
```

### Условие безпересечения с соседней веткой:

Две ветки (parent → folder₁) и (parent → folder₂) **не пересекаются**, если:

```
distance_between_endpoints ≥ 
    FileCloudRadius(files_in_folder1) + 
    FileCloudRadius(files_in_folder2) + 
    SAFETY_MARGIN

distance = ||pos_folder1 - pos_folder2||

SAFETY_MARGIN = 40px (безопасный зазор)
```

---

## 🌳 Максимальный путь и распределение по высоте

Максимальная глубина дерева определяет общую высоту.

### Расчёт максимального пути:

```
MaxDepth = max(depth всех листьев)

TotalHeight = sum of all LAYER_HEIGHT from 0 to MaxDepth
            = MaxDepth * LAYER_HEIGHT
            = MaxDepth * 80px

Пример:
- MaxDepth = 4 (root → L1 → L2 → L3 → L4)
- TotalHeight = 4 * 80 = 320px
```

### Сдвиг папки вниз по иерархии (Y-offset):

Папки, которые находятся на **одном уровне глубины**, имеют одинаковый Y:

```
y_folder = root_y + depth * LAYER_HEIGHT

depth = 0: y = 0
depth = 1: y = 80
depth = 2: y = 160
depth = 3: y = 240
depth = 4: y = 320
```

**Файлы распределяются вокруг Y папки:**

```
y_file = y_folder + (file_index - mid_index) * FILE_SPACING

file_index = 0 (старейший): y = y_folder - (n_files-1)/2 * 40
file_index = n-1 (новейший): y = y_folder + (n_files-1)/2 * 40
```

---

## ⚖️ Балансирование угловой развёртки и высоты

### Проблема: узкий веер vs широкое дерево

Если веер слишком узкий (MAX_ANGLE_SPREAD < 90°), а у папки много детей, то некоторые дети не поместятся.

**Решение: многоуровневые веера**

Если n_children > max_children_per_spread:
```
max_children_per_spread = floor(MAX_ANGLE_SPREAD / MIN_ANGLE_GAP)
                        = floor(90 / 15) = 6 детей

Если папка имеет 8 детей → 2 слоя (4 на первом, 4 на втором):
- Слой 1 (дети 0-3): углы от -30° до +30°
- Слой 2 (дети 4-7): углы от -30° до +30° (но с немного большей длиной)

Или: использовать спиральное распределение (NOT в XY plane, а в угловой координате θ)
```

---

## 📊 Итоговые формулы для реализации

### Папка (folder):

```python
def position_folder(parent_pos, folder_index, n_siblings, depth):
    # Угол ветки
    angle_per_sibling = adaptive_angle_gap(depth, n_siblings)
    angle = parent_pos.angle + (folder_index - n_siblings/2) * angle_per_sibling
    
    # Длина ветки
    branch_len = BRANCH_BASE_LENGTH + depth * BRANCH_DEPTH_MULT
    
    # Позиция папки
    x = parent_pos.x + cos(angle) * branch_len
    y = parent_pos.y + sin(angle) * branch_len * 0.3  # Y compression
    z = 0
    
    return {
        'x': x, 'y': y, 'z': z,
        'angle': angle,  # сохранить для детей
        'depth': depth
    }

def adaptive_angle_gap(depth, n_siblings):
    branch_len = BRANCH_BASE_LENGTH + depth * BRANCH_DEPTH_MULT
    delta_theta = MIN_ANGLE_GAP + 0.05 * branch_len / 500
    return min(delta_theta, MAX_ANGLE_SPREAD / n_siblings)
```

### Файл (leaf):

```python
def position_file(folder_pos, file_index, n_files):
    # Y распределение по времени
    mid_index = (n_files - 1) / 2
    y_offset = (file_index - mid_index) * FILE_SPACING
    
    # X, Z рядом с папкой (вертикальная стопка)
    x = folder_pos['x']  # X = X папки
    y = folder_pos['y'] + y_offset
    z = file_index * Z_LAYER  # наслаивание
    
    # Rotation для вертикальной ориентации
    rotation_z = 90°  # текст вертикально
    
    return {
        'x': x, 'y': y, 'z': z,
        'rotation_z': rotation_z
    }
```

---

## 🔍 Проверка отсутствия пересечений

Для каждой пары веток (parent → child₁, parent → child₂):

```python
def check_no_intersection(child1_pos, child2_pos, files1, files2):
    # Радиусы облаков файлов
    r1 = file_cloud_radius(len(files1))
    r2 = file_cloud_radius(len(files2))
    
    # Расстояние между концами веток (папками)
    distance = euclidean(child1_pos, child2_pos)
    
    # Проверка
    min_distance = r1 + r2 + SAFETY_MARGIN
    assert distance >= min_distance, f"Intersection! {distance} < {min_distance}"
```

---

## 📌 Итого

**Ключевые формулы:**

| Элемент | Формула | Примечание |
|---------|---------|-----------|
| **Угол между детьми** | Δθ = 15° + 0.05 × L / 500 | L = длина ветки |
| **Длина ветки** | L = 120 + depth × 60 | в пикселях |
| **Y папки** | y = root_y + depth × 80 | слой дерева |
| **Y файла** | y = y_folder + (idx - mid) × 40 | по времени |
| **X папки** | x = px + cos(θ) × L | полярные координаты |
| **Радиус облака файлов** | R = 30 + 20 × min(n/10, 3) | растёт с кол-во файлов |

**Результат:**
- ✅ Папки в радиальном веере (no angular intersections)
- ✅ Файлы вертикальной стопкой (Y = время)
- ✅ Безпересечение веток (distance check)
- ✅ Максимальный путь определяет высоту

---

**Готово к реализации в Claude Code!** 🚀
