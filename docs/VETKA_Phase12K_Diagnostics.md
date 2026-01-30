# PHASE 12K DIAGNOSTIC GUIDE
**Текущий статус:** Визуализация сломана (sed + бесконечные линии)  
**Дата:** 19 декабря 2025

---

## ПРОБЛЕМА #1: Превью файлов (Sprite вместо BoxGeometry)

### Симптомы:
- Вместо карточек файлов — маленькие едва заметные синие квадратики
- Файлы почти невидимые на визуализации
- Текст и превью не отображаются

### Корневая причина:
```bash
# Кто-то запустил это:
sed -i 's/Sprite/BoxGeometry/g' tree_renderer.py
```

**Проблема:** `THREE.Sprite` (2D карточка на плоскости) заменена на `THREE.BoxGeometry` (3D куб), но:
1. `BoxGeometry` требует параметры `(width, height, depth)`, не `material`
2. Это создаёт ошибку в конструкторе
3. Карточки не рендерятся корректно

### Решение:

#### ШАГ 1: Найти неправильный код в tree_renderer.py

```python
# ❌ НЕПРАВИЛЬНО (после sed):
new THREE.BoxGeometry(material)

# ✅ ПРАВИЛЬНО (нужно вернуть):
new THREE.Sprite(material)
```

#### ШАГ 2: Правильная реализация файловой карточки

```python
def create_file_card(file, position):
    """Создание карточки файла (Sprite + CanvasTexture)"""
    
    file_type = get_file_type(file.name)
    dims = get_card_dimensions(file_type)
    
    # 1. Canvas для текстуры
    canvas = document.createElement('canvas')
    canvas.width = dims.canvasW
    canvas.height = dims.canvasH
    ctx = canvas.getContext('2d')
    
    # 2. Отрисовка содержимого
    draw_card_by_type(ctx, file, file_type, dims)
    
    # 3. ⚠️ ТЕКСТУРА ИЗ CANVAS
    texture = THREE.CanvasTexture(canvas)
    texture.needsUpdate = True
    
    # 4. ⚠️ SpriteMaterial (НЕ BoxGeometry!)
    material = THREE.SpriteMaterial({
        'map': texture,
        'transparent': True
    })
    
    # 5. ⚠️ Sprite (НЕ Mesh!)
    sprite = THREE.Sprite(material)
    sprite.scale.set(dims.width, dims.height, 1)
    sprite.position.copy(position)
    
    # 6. Данные для клика
    sprite.userData = {
        'type': 'file',
        'fileId': file.id,
        'fileName': file.name,
        'fileData': file
    }
    
    return sprite
```

#### ШАГ 3: Проверить синтаксис tree_renderer.py

Открыть файл и найти все строки где используется "BoxGeometry" в контексте карточек.

---

## ПРОБЛЕМА #2: Синтаксическая ошибка (строка ~1321)

### Симптомы:
```
SyntaxError: Invalid or unexpected token
3d:1321
```

### Диагностика:

```bash
# 1. Проверить файл на битые символы
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
file src/visualizer/tree_renderer.py

# 2. Поискать проблемные строки
python3 -m py_compile src/visualizer/tree_renderer.py

# 3. Результат покажет точную ошибку
```

### Возможные причины:

1. **Emoji в коде** (sed может повредить)
   ```python
   # ❌ Возможно:
   const BRANCH_COLORS = {
       'memory': 0x8B4513,    // 🪵 Коричневый
   ```
   - Emoji после `//` комментария может сломать парсер

2. **Битая кавычка или скобка**
   ```python
   # ❌ Возможно:
   sprite.scale.set(dims.width, dims.height, 1)  // закрывающая скобка потеряна
   ```

3. **Неправильное экранирование**
   ```python
   # ❌ Возможно:
   path = "src\visualizer\tree.js"  # Windows backslash в Linux
   ```

### Решение:

#### Вариант 1: Восстановить из backup

```bash
# Если есть git история:
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
git log --oneline src/visualizer/tree_renderer.py

# Вернуть к последней хорошей версии:
git checkout HEAD~1 src/visualizer/tree_renderer.py
```

#### Вариант 2: Ручное исправление

```bash
# 1. Открыть файл в редакторе
nano src/visualizer/tree_renderer.py

# 2. Перейти на строку 1321 (Ctrl+G в nano)

# 3. Проверить синтаксис вокруг этой строки

# 4. Удалить битые символы/emoji

# 5. Сохранить (Ctrl+O, Enter, Ctrl+X в nano)
```

#### Вариант 3: Очистить от emoji

```python
# Скрипт для удаления emoji
import re

def remove_emoji(text):
    emoji_pattern = re.compile("["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

with open('src/visualizer/tree_renderer.py', 'r', encoding='utf-8') as f:
    content = f.read()

clean_content = remove_emoji(content)

with open('src/visualizer/tree_renderer.py', 'w', encoding='utf-8') as f:
    f.write(clean_content)

print("✅ Emoji removed")
```

---

## ПРОБЛЕМА #3: Бесконечные линии

### Симптомы:
- Линии между узлами выходят в бесконечность
- Камера "тянется" за линиями вне экрана
- X/Y координаты становятся очень большие (10000+)

### Вероятные причины:

#### 1. Неправильная нормализация в Phase 4

```python
# ❌ НЕПРАВИЛЬНО:
theta = math.radians(node.angle)
x = math.sin(theta) * radius
# Если radius слишком большой → x может быть > 1000

# ✅ ПРАВИЛЬНО:
theta = math.radians(node.angle)
radius = BASE_RADIUS + node.radius_offset * RADIUS_VARIATION
# BASE_RADIUS = 100 (нормальный размер)
# RADIUS_VARIATION = 0.2 (небольшое изменение)
x = math.sin(theta) * radius
# Результат: x ∈ [-150, 150]
```

#### 2. Отсутствие bounds checking

```python
# ❌ НЕПРАВИЛЬНО:
node.x = startX + nodeIndex * NODE_SPACING
# Если NODE_SPACING = 1000 → может выйти за границы

# ✅ ПРАВИЛЬНО:
# Нормализовать X в пределах видимости
max_spread = 400  # не больше 400 от центра
x = max(-max_spread, min(max_spread, x))
```

#### 3. Неправильное преобразование углов

```python
# ❌ НЕПРАВИЛЬНО:
angle_deg = barycenter_position  # 0-1 от barycenter
theta = math.radians(angle_deg * 360)  # может быть > 360°

# ✅ ПРАВИЛЬНО:
angle_deg = -MAX_ANGLE + (nodeIndex / len(layer)) * 2 * MAX_ANGLE
# MAX_ANGLE = 60° → range [-60°, +60°]
theta = math.radians(angle_deg)
```

#### 4. Отсутствие нормализации при рёбрах

```python
# ❌ НЕПРАВИЛЬНО (при отрисовке edges):
curve = new THREE.CatmullRomCurve3([start, midpoint, end])
// Если start/end в бесконечности → curve выходит за границы

# ✅ ПРАВИЛЬНО:
// Проверить что start и end в нормальных координатах
if (Math.abs(start.x) > 1000 || Math.abs(start.y) > 1000) {
    console.warn('Invalid start position:', start)
    return null
}
```

### Диагностика:

```python
# Добавить логирование позиций
def phase4_coordinate_assignment(self, ordered_layers):
    positions = {}
    
    for layer_idx, layer in ordered_layers.items():
        for node in layer:
            x = math.sin(math.radians(node.angle)) * radius
            y = layer_idx * LAYER_HEIGHT
            z = self.get_duplicate_z(node)
            
            # ⚠️ ЛОГИРОВАНИЕ:
            if abs(x) > 1000 or abs(y) > 1000:
                print(f"🔴 ABNORMAL: {node.id}")
                print(f"   x={x}, y={y}, z={z}")
                print(f"   angle={node.angle}, radius={radius}")
            
            positions[node.id] = {'x': x, 'y': y, 'z': z}
    
    return positions
```

### Решение:

#### ШАГ 1: Добавить bounds checking

```python
def clamp(value, min_val, max_val):
    """Ограничить значение в диапазон"""
    return max(min_val, min(max_val, value))

# В Phase 4:
x = clamp(x, -MAX_X, MAX_X)
y = clamp(y, 0, MAX_Y)
z = clamp(z, -MAX_Z, MAX_Z)
```

#### ШАГ 2: Нормализовать angles

```python
# Убедиться что angles в [-MAX_ANGLE, +MAX_ANGLE]
def normalize_angles(layer):
    MAX_ANGLE = 60  # degrees
    
    for i, node in enumerate(layer):
        # Ограничить в диапазон
        node.angle = clamp(node.angle, -MAX_ANGLE, MAX_ANGLE)
        
        # Распределить равномерно если выходит за границы
        if abs(node.angle) > MAX_ANGLE:
            node.angle = -MAX_ANGLE + (i / len(layer)) * 2 * MAX_ANGLE
    
    return layer
```

#### ШАГ 3: Проверить radius

```python
# BASE_RADIUS должен быть разумным
BASE_RADIUS = 100  # типичное значение
RADIUS_VARIATION = 0.2  # только 20% вариации

# Результат: radius ∈ [80, 120]
```

#### ШАГ 4: Validation перед рендерингом

```javascript
// В JavaScript, перед добавлением в сцену:
if (!isValidPosition(position)) {
    console.error('Invalid position:', position)
    return null
}

function isValidPosition(pos) {
    const MAX_COORD = 500
    return Math.abs(pos.x) < MAX_COORD &&
           Math.abs(pos.y) < MAX_COORD &&
           Math.abs(pos.z) < MAX_COORD
}
```

---

## ЧЕКЛИСТ ДИАГНОСТИКИ

```
PROBLEM #1: Sprite вместо BoxGeometry
──────────────────────────────────────────────
[ ] Открыть src/visualizer/tree_renderer.py
[ ] Найти все строки с "BoxGeometry" в контексте карточек
[ ] Заменить на "Sprite"
[ ] Проверить использование CanvasTexture
[ ] Тест: карточки видны на экране?

PROBLEM #2: Синтаксическая ошибка
──────────────────────────────────────────────
[ ] Запустить: python3 -m py_compile src/visualizer/tree_renderer.py
[ ] Найти точную строку ошибки
[ ] Поискать emoji / битые символы
[ ] Проверить скобки и кавычки
[ ] Восстановить из backup если нужно
[ ] Тест: файл парсится без ошибок?

PROBLEM #3: Бесконечные линии
──────────────────────────────────────────────
[ ] Добавить логирование позиций
[ ] Проверить что angles в [-60°, +60°]
[ ] Проверить что radius в [80, 120]
[ ] Добавить bounds checking (x, y, z)
[ ] Нормализовать перед рендерингом
[ ] Тест: линии остаются в видимой области?

ПОСЛЕ ВСЕХ ФИКСОВ:
──────────────────────────────────────────────
[ ] python3 src/main.py
[ ] open http://localhost:5001/3d
[ ] Проверить что нет ошибок в консоли (F12)
[ ] Проверить что карточки видны
[ ] Проверить что линии (edges) нормальные
[ ] Проверить что можно крутить камерой (OrbitControls)
[ ] Закоммитить: git add . && git commit -m "Phase 12K: Fix visualization"
```

---

## БЫСТРАЯ ПРОВЕРКА

```bash
# 1. Проверить синтаксис
python3 -m py_compile src/visualizer/tree_renderer.py

# 2. Если ошибка — сразу видно где
# 3. Исправить проблему
# 4. Запустить снова
# 5. Если OK — можно запускать Flask

python3 src/main.py
# Если в консоли нет ошибок → можно открывать браузер
open http://localhost:5001/3d
```

---

## КАК ПРОВЕРИТЬ КООРДИНАТЫ

Добавить в JavaScript консоль браузера (F12):

```javascript
// Посмотреть первые 10 позиций
console.table(
    Array.from(positions.entries())
        .slice(0, 10)
        .map(([id, pos]) => ({
            id: id.substring(0, 20),
            x: pos.x.toFixed(2),
            y: pos.y.toFixed(2),
            z: pos.z.toFixed(2),
            layer: pos.layer
        }))
)

// Проверить макс/мин значения
const allX = Array.from(positions.values()).map(p => p.x)
console.log('X range:', Math.min(...allX), '→', Math.max(...allX))

// Если X > 500 → проблема!
```

---

**Следующий шаг:** Пришли лог консоли браузера + вывод ошибки при компиляции.
