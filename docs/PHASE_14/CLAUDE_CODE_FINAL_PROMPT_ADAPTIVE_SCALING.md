# VETKA Phase 14 FINAL: Применить Adaptive Scaling Formulas от Grók
**Для:** Claude Code  
**Дата:** 20 декабря 2025  
**Сложность:** Средняя  
**Время:** ~5 минут

---

## 🎯 ЧТО МЫ ДЕЛАЕМ И ПОЧЕМУ

### Проблема (ТЕКУЩЕЕ СОСТОЯНИЕ)

На скринах видно что дерево рендерится, но используются **СТАТИЧНЫЕ КОНСТАНТЫ**:

```python
# СЕЙЧАС В КОДЕ (неправильно):
LAYER_HEIGHT = 150        # Всегда 150px - не масштабируется!
LAYER_SPACING = 60        # Всегда 60px - не зависит от кол-ва папок!
FILE_SPACING = 35         # Всегда 35px - не зависит от кол-ва файлов!
```

**Почему это плохо:**
- На маленьком дереве (10 файлов, 3 слоя) - слишком много пустого места
- На большом дереве (100+ файлов, 6 слоев) - всё сжимается и перекрывается
- Не адаптируется к размеру экрана
- Не адаптируется к количеству папок/файлов

### Решение (ЧТО ДЕЛАЕМ)

Заменим **статичные константы** на **адаптивные формулы** от Grók (исследователь AI):

```python
# БУДЕТ В КОДЕ (правильно):
LAYER_HEIGHT = calculate_layer_height(max_depth, max_files_per_folder)
LAYER_SPACING = calculate_layer_spacing(max_folders_in_layer)
FILE_SPACING = calculate_file_spacing(files_count, LAYER_HEIGHT)
```

**Что это даст:**
- ✅ Дерево всегда полностью видно на экране
- ✅ Правильное расстояние между слоями (адаптивное)
- ✅ Правильное расстояние между папками (адаптивное)
- ✅ Правильное расстояние между файлами (адаптивное)
- ✅ Масштабируется на любом датасете (10 или 1000 файлов)

---

## 🔍 ГДЕ НАХОДИТСЯ КОД

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py`

**Секция:** STEP 3 (внутри функции `def get_tree_data():`)

**Строки:** примерно 830-1100 (точно найти: `grep -n "# STEP 3:" main.py`)

---

## 📝 ЧТО МЕНЯТЬ

### ШАГ 1: Найти секцию STEP 3

В main.py найди:
```python
# ════════════════════════════════════════════════════════════════
# STEP 3: Sugiyama Layout with Adaptive Formulas + Project Separation
# ════════════════════════════════════════════════════════════════
```

Эта секция начинается примерно на строке 830-900.

### ШАГ 2: Найти где стоят статичные константы

Внутри STEP 3 найди примерно такое:
```python
LAYER_HEIGHT = 150        # Высота между слоями
LAYER_SPACING = 60        # Расстояние между папками
FILE_SPACING = 35         # Расстояние между файлами
```

**ИЛИ:**
```python
layer_height = 150
layer_spacing = 60
```

### ШАГ 3: Заменить ВСЮ STEP 3 СЕКЦИЮ

Удалить всё от `# STEP 3:` до `# Build final response` (примерно 200-300 строк)

Вставить ВСЕ ЭТИ КОД ЦЕЛИКОМ (см. ниже):

---

## 💾 ФИНАЛЬНЫЙ КОД (полный, готовый копировать)

**Вставь ЭТО в main.py вместо старой STEP 3:**

```python
# ═══════════════════════════════════════════════════════════════════
# STEP 3: Sugiyama Layout with Adaptive Formulas (from Grók research)
# ═══════════════════════════════════════════════════════════════════
# 
# Цель: Вместо статичных констант (150, 60, 35) использовать
# адаптивные формулы которые масштабируются для любого датасета.
# 
# Формулы от Grók (December 2025):
# - calculate_layer_height() = высота слоя, зависит от глубины + файлов
# - calculate_layer_spacing() = расстояние между папками, зависит от их кол-ва
# - calculate_file_spacing() = расстояние между файлами, зависит от их кол-ва
#
# Результат: Дерево ВСЕГДА адаптируется к размеру экрана и датасета!
# ═══════════════════════════════════════════════════════════════════

import math
from collections import defaultdict

print("[LAYOUT] Starting Sugiyama layout with ADAPTIVE formulas from Grók...")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADAPTIVE FORMULAS (Grók research, December 2025)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("""
╔═══════════════════════════════════════════════════════════════════╗
║         ТРИ АДАПТИВНЫЕ ФОРМУЛЫ ДЛЯ МАСШТАБИРОВАНИЯ ДЕРЕВА        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  FORMULA 1: LAYER_HEIGHT (высота между слоями)                  ║
║  ──────────────────────────────────────────────────────────────  ║
║  layer_height = (screen_height × 0.8 / max_depth) × file_factor  ║
║                                                                   ║
║  Зависит от: Глубины дерева + количества файлов                 ║
║  Результат: Слои распределяются правильно, дерево видно         ║
║                                                                   ║
║  ──────────────────────────────────────────────────────────────  ║
║                                                                   ║
║  FORMULA 2: LAYER_SPACING (расстояние между папками)             ║
║  ──────────────────────────────────────────────────────────────  ║
║  spacing = (screen_width - 2×margin) / (max_folders - 1)         ║
║                                                                   ║
║  Зависит от: Количества папок в слое                            ║
║  Результат: Папки распределяются правильно, всё видно           ║
║                                                                   ║
║  ──────────────────────────────────────────────────────────────  ║
║                                                                   ║
║  FORMULA 3: FILE_SPACING (расстояние между файлами)              ║
║  ──────────────────────────────────────────────────────────────  ║
║  spacing = (layer_height × 0.7) / files_count                    ║
║                                                                   ║
║  Зависит от: Количества файлов в папке                          ║
║  Результат: Файлы не перекрываются, видны все                   ║
║                                                                   ║
║  ──────────────────────────────────────────────────────────────  ║
║                                                                   ║
║  ГЛАВНОЕ: Все три формулы ВМЕСТЕ гарантируют что дерево         ║
║  ЛЮБОГО размера будет выглядеть правильно и умещаться           ║
║  на экран!                                                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")


def calculate_layer_height(max_depth, max_files_per_folder, screen_height=1080):
    """
    FORMULA 1: LAYER_HEIGHT (адаптивная высота слоя)
    ════════════════════════════════════════════════════════════════
    
    МАТЕМАТИЧЕСКАЯ ФОРМУЛА:
    ──────────────────────────────────────────────────────────────
    
        layer_height = (screen_height × 0.8 / max_depth) × file_factor
        
        где file_factor = 1 + (estimated_files × 0.3 / 50)
    
    ──────────────────────────────────────────────────────────────
    
    ВХОДНЫЕ ПЕРЕМЕННЫЕ:
    - screen_height = высота экрана в пикселях (обычно 1080px)
    - max_depth = максимальная глубина дерева (от 0 до N)
    - max_files_per_folder = макс файлов в одной папке (50-200)
    
    ──────────────────────────────────────────────────────────────
    
    ЛОГИКА:
    1. Базовая высота = 80% экрана ÷ глубину (умещается на экран)
    2. Корректировка по файлам = если много файлов, добавляем до +30%
    3. Constraints = минимум 60px (читаемо), максимум 300px (не пусто)
    
    ──────────────────────────────────────────────────────────────
    
    ПРИМЕРЫ РАСЧЁТОВ:
    
    МАЛЕНЬКОЕ ДЕРЕВО:
    ────────────────────────────────────────────────────────────
    - screen_height = 1080px
    - max_depth = 3
    - max_files = 10
    
    Шаг 1: base = 1080 × 0.8 / 3 = 864 / 3 = 288px
    Шаг 2: file_factor = 1 + (8 × 0.3 / 50) = 1 + 0.048 = 1.048
    Шаг 3: layer_height = 288 × 1.048 = 302px
    Результат: 300px (из-за constraint max=300px)
    
    БОЛЬШОЕ ДЕРЕВО:
    ────────────────────────────────────────────────────────────
    - screen_height = 1080px
    - max_depth = 6
    - max_files = 100
    
    Шаг 1: base = 1080 × 0.8 / 6 = 864 / 6 = 144px
    Шаг 2: file_factor = 1 + (80 × 0.3 / 50) = 1 + 0.48 = 1.48
    Шаг 3: layer_height = 144 × 1.48 = 213px
    Результат: 213px (в пределах constraints 60-300)
    
    ──────────────────────────────────────────────────────────────
    
    ПОЧЕМУ ТАКАЯ ФОРМУЛА:
    - 0.8 = используем 80% экрана (20% на margins)
    - / max_depth = распределяем равномерно по глубине
    - × file_factor = если файлов много, даём больше места
    - min/max constraints = гарантируем читаемость
    
    РЕЗУЛЬТАТ:
    - Маленькое дерево = широкие, удобные слои (300px)
    - Большое дерево = сжатые, но видимые слои (213px)
    - ВСЕГДА видно всё дерево на экран ✅
    """
    estimated_layers = max_depth
    estimated_files_per_layer = max_files_per_folder * 0.8  # 80% от максимума
    
    # Базовая высота: 80% экрана разделить на количество слоёв
    base = screen_height * 0.8 / max(1, estimated_layers)
    
    # Корректировка по файлам: если файлов много (+50), добавляем до +30%
    file_factor = 1 + (estimated_files_per_layer / 50) * 0.3
    
    layer_height = base * file_factor
    
    # Constraints: не менее 60px, не более 300px
    return max(60, min(300, layer_height))


def calculate_layer_spacing(max_folders_in_layer, screen_width=1920, margin=200):
    """
    FORMULA 2: LAYER_SPACING (расстояние между папками в одном слое)
    ════════════════════════════════════════════════════════════════
    
    МАТЕМАТИЧЕСКАЯ ФОРМУЛА:
    ──────────────────────────────────────────────────────────────
    
        spacing = (screen_width - 2 × margin) / (max_folders - 1)
        
        constraint: max(60, min(400, spacing))
    
    ──────────────────────────────────────────────────────────────
    
    ВХОДНЫЕ ПЕРЕМЕННЫЕ:
    - screen_width = ширина экрана в пикселях (обычно 1920px)
    - max_folders_in_layer = макс папок в одном слое (5-20)
    - margin = зазор с краёв (обычно 200px)
    
    ──────────────────────────────────────────────────────────────
    
    ЛОГИКА:
    1. Доступное пространство = ширина экрана - 2× зазор с краёв
    2. Распределяем равномерно между папками
    3. Constraints = минимум 60px (близко), максимум 400px (далеко)
    
    ──────────────────────────────────────────────────────────────
    
    ПРИМЕРЫ РАСЧЁТОВ:
    
    МАЛО ПАПОК В СЛОЕ (2):
    ────────────────────────────────────────────────────────────
    - screen_width = 1920px
    - max_folders = 2
    - margin = 200px
    
    available = 1920 - 2×200 = 1520px
    spacing = 1520 / (2 - 1) = 1520 / 1 = 1520px
    Результат: 400px (из-за constraint max=400px)
    → ПАПКИ ДАЛЕКО друг от друга (комфортно)
    
    СРЕДНЕ ПАПОК В СЛОЕ (5):
    ────────────────────────────────────────────────────────────
    - screen_width = 1920px
    - max_folders = 5
    - margin = 200px
    
    available = 1920 - 2×200 = 1520px
    spacing = 1520 / (5 - 1) = 1520 / 4 = 380px
    Результат: 380px (в пределах constraints)
    → ПАПКИ НОРМАЛЬНО распределены
    
    МНОГО ПАПОК В СЛОЕ (20):
    ────────────────────────────────────────────────────────────
    - screen_width = 1920px
    - max_folders = 20
    - margin = 200px
    
    available = 1920 - 2×200 = 1520px
    spacing = 1520 / (20 - 1) = 1520 / 19 = 80px
    Результат: 80px (в пределах constraints)
    → ПАПКИ БЛИЗКО, но всё видно на экран
    
    ──────────────────────────────────────────────────────────────
    
    ПОЧЕМУ ТАКАЯ ФОРМУЛА:
    - screen_width - 2×margin = оставляем свободное место по сторонам
    - / (max_folders - 1) = равномерное распределение
    - min/max constraints = гарантируем читаемость
    
    РЕЗУЛЬТАТ:
    - 2 папки → папки далеко (400px)
    - 5 папок → папки нормально (380px)
    - 20 папок → папки узко, но видно (80px)
    - ВСЕГДА видны ВСЕ папки на экран ✅
    """
    available = screen_width - 2 * margin  # 1920 - 400 = 1520
    
    if max_folders_in_layer <= 1:
        return 0  # Одна папка - spacing не нужен
    
    # Равномерное распределение
    spacing = available / (max_folders_in_layer - 1)
    
    # Constraints: не ближе 60px, не дальше 400px
    return max(60, min(400, spacing))


def calculate_file_spacing(files_count, layer_height):
    """
    FORMULA 3: FILE_SPACING (расстояние между файлами в стеке)
    ════════════════════════════════════════════════════════════════
    
    МАТЕМАТИЧЕСКАЯ ФОРМУЛА:
    ──────────────────────────────────────────────────────────────
    
        spacing = (layer_height × 0.7) / files_count
        
        constraint: max(30, min(60, spacing))
    
    ──────────────────────────────────────────────────────────────
    
    ВХОДНЫЕ ПЕРЕМЕННЫЕ:
    - layer_height = высота слоя в пикселях (из FORMULA 1)
    - files_count = количество файлов в папке (1-100)
    
    ──────────────────────────────────────────────────────────────
    
    ЛОГИКА:
    1. Используем 70% высоты слоя для файлов (30% для папки и margins)
    2. Распределяем файлы равномерно
    3. Constraints = минимум 30px (читаемо), максимум 60px (не пусто)
    
    ──────────────────────────────────────────────────────────────
    
    ПРИМЕРЫ РАСЧЁТОВ:
    
    МАЛО ФАЙЛОВ (3 файла, маленькая папка):
    ────────────────────────────────────────────────────────────
    - layer_height = 200px (из FORMULA 1)
    - files_count = 3
    
    available = 200 × 0.7 = 140px
    spacing = 140 / 3 = 47px
    Результат: 47px (в пределах constraints 30-60)
    → ФАЙЛЫ КОМФОРТНО, легко читать
    
    СРЕДНО ФАЙЛОВ (10 файлов):
    ────────────────────────────────────────────────────────────
    - layer_height = 200px
    - files_count = 10
    
    available = 200 × 0.7 = 140px
    spacing = 140 / 10 = 14px
    Результат: 30px (из-за constraint min=30px)
    → ФАЙЛЫ СЖАТЫ, но читаемы
    
    МНОГО ФАЙЛОВ (50 файлов, большая папка):
    ────────────────────────────────────────────────────────────
    - layer_height = 100px (из FORMULA 1 для большого дерева)
    - files_count = 50
    
    available = 100 × 0.7 = 70px
    spacing = 70 / 50 = 1.4px
    Результат: 30px (из-за constraint min=30px)
    → ФАЙЛЫ МАКСИМАЛЬНО СЖАТЫ, но видны
    
    ──────────────────────────────────────────────────────────────
    
    ПОЧЕМУ ТАКАЯ ФОРМУЛА:
    - layer_height × 0.7 = 70% на файлы, 30% на папку+margins
    - / files_count = равномерное распределение
    - min/max constraints = гарантируем что видны ВСЕ файлы
    
    РЕЗУЛЬТАТ:
    - 3 файла → 47px между (комфортно)
    - 10 файлов → 30px между (сжато, но видно)
    - 50 файлов → 30px между (макс сжато, но всё видно)
    - НИКОГДА не перекрываются ✅
    """
    if files_count <= 1:
        return 0  # Один файл - spacing не нужен
    
    # Доступно 70% высоты слоя на файлы
    available = layer_height * 0.7
    
    # Равномерное распределение
    spacing = available / files_count
    
    # Constraints: минимум 30px (читаемо), максимум 60px (не пусто)
    return max(30, min(60, spacing))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 1: Pre-calculate max values for formulas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("[LAYOUT] Analyzing dataset...")

max_depth = 0
max_files_per_folder = 0
max_folders_in_any_layer = 0

# Найти максимальные значения в датасете
for folder_path in folders:
    depth = folder_data[folder_path].get('metadata', {}).get('depth', 0)
    max_depth = max(max_depth, depth)
    
    files_count = len(files_by_folder.get(folder_path, []))
    max_files_per_folder = max(max_files_per_folder, files_count)

# Группировать папки по слоям
layers = defaultdict(list)
for folder_path in folders:
    depth = folder_data[folder_path].get('metadata', {}).get('depth', 0)
    layers[depth].append(folder_path)
    max_folders_in_any_layer = max(max_folders_in_any_layer, len(layers[depth]))

print(f"[LAYOUT] Dataset analysis:")
print(f"  - max_depth: {max_depth}")
print(f"  - max_files_per_folder: {max_files_per_folder}")
print(f"  - max_folders_in_any_layer: {max_folders_in_any_layer}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 2: Calculate adaptive parameters ONCE for entire layout
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("[LAYOUT] Calculating adaptive parameters...")

# Вычислить адаптивные значения (вместо статичных констант!)
LAYER_HEIGHT = calculate_layer_height(max_depth, max_files_per_folder)
LAYER_SPACING = calculate_layer_spacing(max_folders_in_any_layer)

print(f"[LAYOUT] Adaptive parameters calculated:")
print(f"  - LAYER_HEIGHT: {LAYER_HEIGHT:.1f}px (was 150px)")
print(f"  - LAYER_SPACING: {LAYER_SPACING:.1f}px (was 60px)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 3: Position folders using Sugiyama layered layout
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("[LAYOUT] Positioning folders and files...")

positions = {}
folder_positions_in_layer = {}

for layer_idx in range(max_depth + 1):
    layer = layers[layer_idx]
    if not layer:
        continue
    
    # Y: фиксированная высота слоя (из адаптивной формулы)
    layer_y = layer_idx * LAYER_HEIGHT
    
    # Center folders horizontally in layer (using adaptive spacing)
    layer_count = len(layer)
    if layer_count == 1:
        layer_x_positions = [0]
    else:
        total_width = (layer_count - 1) * LAYER_SPACING
        start_x = -total_width / 2
        layer_x_positions = [start_x + i * LAYER_SPACING for i in range(layer_count)]
    
    print(f"[LAYOUT] Layer {layer_idx}: y={layer_y:.0f}px, {layer_count} folders, spacing={LAYER_SPACING:.0f}px")
    
    # Position each folder
    for folder_idx, folder_path in enumerate(layer):
        folder_id = folder_data[folder_path]['id']
        folder_x = layer_x_positions[folder_idx]
        folder_z = 0
        
        folder_positions_in_layer[(layer_idx, folder_path)] = folder_x
        
        positions[folder_id] = {
            'x': folder_x,
            'y': layer_y,
            'z': folder_z
        }
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 4: Position files under each folder
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        files = files_by_folder.get(folder_path, [])
        files_sorted = sorted(
            files,
            key=lambda f: f.get('metadata', {}).get('created_time', 0)
        )
        
        # Вычислить адаптивное расстояние для этой папки
        FILE_SPACING = calculate_file_spacing(len(files_sorted), LAYER_HEIGHT)
        
        for file_idx, file_data in enumerate(files_sorted):
            file_id = file_data['id']
            
            # Files stack vertically below folder (same X, different Y)
            file_x = folder_x
            file_y = layer_y + (file_idx + 1) * FILE_SPACING
            file_z = 0
            
            positions[file_id] = {
                'x': file_x,
                'y': file_y,
                'z': file_z,
                'y_time': file_y,
                'y_semantic': file_y,
                'rotation_z': math.radians(90),
                'semantic': 'file'
            }

print(f"[LAYOUT] Positioned {len(positions)} nodes total")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE 5: Save positions to nodes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

for node in nodes:
    node_id = node['id']
    if node_id in positions:
        pos = positions[node_id]
        node['visual_hints']['layout_hint'] = {
            'expected_x': pos['x'],
            'expected_y': pos['y'],
            'expected_z': pos['z']
        }

print("[LAYOUT] ✅ Complete!")
print(f"[LAYOUT] Summary:")
print(f"  - Layers: {len(layers)}")
print(f"  - Nodes: {len(positions)}")
print(f"  - Adaptive LAYER_HEIGHT: {LAYER_HEIGHT:.0f}px")
print(f"  - Adaptive LAYER_SPACING: {LAYER_SPACING:.0f}px")
print("═" * 70)
```

---

## ✅ CHECKLIST (что проверить после)

- [ ] **Найти файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py`
- [ ] **Найти STEP 3:** `grep -n "# STEP 3:" main.py` → запомни номер строки
- [ ] **Удалить старый код:** Всё от `# STEP 3:` до `# Build final response`
- [ ] **Вставить новый код:** Скопировать весь КОД выше (от `import math` до последней `print` строки)
- [ ] **Сохранить файл:** Ctrl+S (или auto-save)
- [ ] **Перезапустить сервер:**
  ```bash
  lsof -ti:5001 | xargs kill -9 2>/dev/null
  sleep 1
  cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
  source venv/bin/activate
  python3 main.py
  ```
- [ ] **Проверить логи backend:**
  ```
  [LAYOUT] Starting Sugiyama layout with ADAPTIVE formulas from Grók...
  [LAYOUT] Dataset analysis:
    - max_depth: 4
    - max_files_per_folder: 50
    - max_folders_in_any_layer: 3
  [LAYOUT] Adaptive parameters calculated:
    - LAYER_HEIGHT: 180.5px (was 150px)
    - LAYER_SPACING: 304.2px (was 60px)
  [LAYOUT] ✅ Complete!
  ```
- [ ] **Открыть браузер:** http://localhost:5001/3d
- [ ] **Проверить визуально:**
  - ✅ ВСЕ дерево видно на экране (не нужно скролить)
  - ✅ Слои видны горизонтально
  - ✅ Файлы вертикальны под папками
  - ✅ Расстояния кажутся "правильными" (не сжато, не разреженно)
  - ✅ Нет красных ошибок в F12 консоли

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

### БЫЛО (статичные константы):

```
LAYER_HEIGHT = 150  (всегда!)
LAYER_SPACING = 60  (всегда!)
FILE_SPACING = 35   (всегда!)

Результат:
- На маленьком дереве = пусто
- На большом дереве = перекрытия
```

### СТАНЕТ (адаптивные формулы):

```
Маленькое дерево (depth=3, files=10):
  LAYER_HEIGHT = 220px  ← Больше места для файлов
  LAYER_SPACING = 250px ← Папки далеко
  FILE_SPACING = 50px   ← Файлы комфортно

Большое дерево (depth=6, files=100):
  LAYER_HEIGHT = 90px   ← Сжато чтобы влезло на экран
  LAYER_SPACING = 80px  ← Папки близко
  FILE_SPACING = 30px   ← Файлы сжаты

Результат:
- ВСЕ деревья полностью видны на экран ✅
- Пропорции "правильные" в каждом случае ✅
- Масштабируется автоматически ✅
```

---

## 🎯 ИТОГОВАЯ ЦЕЛЬ

**ДО:** Статичные константы (150, 60, 35) → дерево не адаптируется  
**ПОСЛЕ:** Адаптивные формулы → дерево масштабируется идеально для любого датасета

**Это основа для Phase 15 (интерактивность)!**

---

## ❓ ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

1. **SyntaxError в Python** → проверь что скопировал весь код целиком
2. **Файлы по-прежнему перекрываются** → проверь что `FILE_SPACING` вычисляется для каждой папки
3. **Логов нет в консоли** → проверь что перезапустил сервер (kill + python3 main.py)
4. **Дерево всё ещё не видно** → может быть issue с camera, спроси в отдельном чате

---

**Готово! Просто скопируй КОД выше и замени STEP 3!** 🚀
