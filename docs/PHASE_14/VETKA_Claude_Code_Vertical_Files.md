# VETKA Phase 14: Vertical File Stacking in Sugiyama Layout
**Цель:** Повернуть файлы с горизонтального размещения (X-распределение) на вертикальное (Y-распределение по времени)

---

## 🎯 Задача (SHORT & FOCUSED)

**Текущее состояние:**
- Папки расположены радиально веером ✅
- Файлы расположены горизонтально вдоль X ❌
- Файлы одной папки занимают одну горизонтальную линию

**Требуется:**
- Файлы одной папки → вертикальная стопка вдоль Y ✅
- Y-ось = время создания (старые внизу, новые вверху) ✅
- X остаётся рядом с папкой (X ≈ X_папки) ✅
- Вращение Sprite на 90° для вертикального текста ✅

---

## 📂 Где менять код

**Файл:** `main.py`  
**Функция:** `get_tree_data()` → блок "Position files"  
**Примерно строки:** 900-950 (ищи по "folder_files" и "file positioning")

---

## 🔄 Текущий код (неправильный)

```python
# ❌ НЕПРАВИЛЬНО: файлы горизонтально
for file_idx, file_data in enumerate(folder_files):
    # Какая-то формула с angle_rad и распределением по X
    file_x = folder_x + math.sin(angle_rad) * offset  # горизонтально!
    file_y = folder_y
    ...
```

---

## ✅ Правильный код

```python
# ✅ ПРАВИЛЬНО: файлы вертикально по Y (по времени)

FILE_SPACING = 40  # расстояние между файлами по Y (пиксели)

if folder_files:
    # Шаг 1: Сортировать файлы по времени создания (старые→новые)
    folder_files_sorted = sorted(
        folder_files,
        key=lambda f: f.get('metadata', {}).get('created_time', 0)
    )
    n_files = len(folder_files_sorted)
    
    # Шаг 2: Для каждого файла рассчитать вертикальную позицию
    for file_idx, file_data in enumerate(folder_files_sorted):
        
        # Y: РАСПРЕДЕЛЕНИЕ ПО ВРЕМЕНИ
        # Центрируем стопку вокруг Y папки
        # Старые файлы внизу (меньше Y), новые вверху (больше Y)
        mid_index = (n_files - 1) / 2.0
        y_offset = (file_idx - mid_index) * FILE_SPACING
        file_y = folder_y + y_offset
        
        # X: РЯДОМ С ПАПКОЙ (вертикальная стопка, НЕ распределение)
        # ВСЕ файлы одной папки имеют одинаковый X
        file_x = folder_x  # КЛЮЧ: X = X папки, не распределяем!
        
        # Z: НАСЛАИВАНИЕ (новые файлы впереди)
        file_z = file_idx * 2
        
        # Rotation: 90° для вертикальной ориентации текста
        rotation_z_rad = math.radians(90)
        
        # Сохранить позицию в visual_hints
        position_dict = {
            'id': file_data['id'],
            'x': file_x,
            'y': file_y,
            'z': file_z,
            'rotation_z': rotation_z_rad,
            'layer': layer_idx
        }
        
        positions[file_data['id']] = position_dict
```

---

## 🔍 Что это делает

```
ДО (горизонтальное):
  файл1 файл2 файл3 файл4 файл5
  └─────────────────────────── папка

ПОСЛЕ (вертикальное):
  файл5 (новый, Y=+80)    ← вверху (новые)
  файл4 (Y=+40)
  папка (Y=0)             ← центр
  файл3 (Y=-40)
  файл2 (Y=-80)
  файл1 (старый, Y=-120)  ← внизу (старые)
  
  Все на X = X_папки (вертикальная линия)
```

---

## 🧪 Проверка результата

После редакции запусти диагностику:

```bash
curl -s http://localhost:5001/api/tree/data > /tmp/check.json && python3 << 'EOF'
import json
from collections import defaultdict

with open('/tmp/check.json') as f:
    data = json.load(f)
    nodes = data['tree']['nodes']
    files = [n for n in nodes if n.get('type') == 'leaf']
    
    by_parent = defaultdict(list)
    for f in files:
        by_parent[f['parent_id']].append(f)
    
    # Самая большая папка
    parent_id, parent_files = max(by_parent.items(), key=lambda x: len(x[1]))
    parent = next(n for n in nodes if n['id'] == parent_id)
    
    x_vals = []
    y_vals = []
    for f in parent_files:
        hint = f['visual_hints']['layout_hint']
        x_vals.append(hint['expected_x'])
        y_vals.append(hint['expected_y'])
    
    x_span = max(x_vals) - min(x_vals)
    y_span = max(y_vals) - min(y_vals)
    
    print(f"📁 {parent['name']} ({len(parent_files)} файлов)")
    print(f"X-размах: {x_span:.1f}px (должно быть ~0) {'✅' if x_span < 1 else '❌'}")
    print(f"Y-размах: {y_span:.1f}px (должно быть >100) {'✅' if y_span > 100 else '❌'}")
    
    if x_span < 1 and y_span > 100:
        print("\n✅ ПРАВИЛЬНО! Вертикальная стопка по времени")
EOF
```

**Ожидаемый результат:**
```
📁 docs (51 файлов)
X-размах: 0.0px (должно быть ~0) ✅
Y-размах: 1750.0px (должно быть >100) ✅

✅ ПРАВИЛЬНО! Вертикальная стопка по времени
```

---

## 📋 Checklist

- [ ] Найти блок позиционирования файлов в `main.py` (~строка 900-950)
- [ ] Заменить на правильный код (вертикальный Y, X = X_папки)
- [ ] Убедиться что `sorted()` по `created_time`
- [ ] `FILE_SPACING = 40` установлен
- [ ] Сохранить `rotation_z_rad = math.radians(90)`
- [ ] Перезапустить сервер
- [ ] Запустить диагностику
- [ ] Открыть браузер, очистить кэш (Cmd+Shift+R), загрузить `/3d?layout=sugiyama`
- [ ] Проверить что файлы вертикально стоят рядом с папками

---

## 🚀 После исправления

В браузере должно быть:
- ✅ Папки в радиальном веере (разные X)
- ✅ Файлы под папками вертикально (одинаковый X)
- ✅ Y-ось = время (старые внизу, новые вверху)
- ✅ Читаемая структура: папка → файлы под ней

---

**Это часть Phase 14 - Orthogonal Sugiyama с vertical file stacking.**
