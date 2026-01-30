# VETKA Phase 14 FINAL Part 2: Добавить Интерактивность (Anti-Gravity + Drag-and-Drop)
**Для:** Claude Code  
**Дата:** 20 декабря 2025  
**После:** Phase 1 (адаптивные формулы масштабирования)  
**Сложность:** Выше среднего  
**Время:** ~15-20 минут

---

## 🎯 ЧТО МЫ ДЕЛАЕМ И ПОЧЕМУ

### Текущее состояние (ПОСЛЕ Phase 1):
✅ Дерево масштабируется адаптивно (LAYER_HEIGHT, LAYER_SPACING, FILE_SPACING)  
✅ Папки правильно распределены  
✅ Файлы не перекрываются  
❌ **НО:** Дерево статичное! User не может ничего двигать

### Что добавляем (Phase 2):
```python
# ИНТЕРАКТИВНОСТЬ:
# 1. User может CLICK на ветку (папка/файл)
# 2. User может DRAG ветку мышкой
# 3. Соседние ветки АВТОМАТИЧЕСКИ ОТТАЛКИВАЮТСЯ
# 4. Структура СОХРАНЯЕТСЯ (Y остаётся фиксированным)
# 5. Всё выглядит ЖИВЫМ и РЕАГИРУЮЩИМ на действия
```

### Результат (Phase 2):
- ✅ Дерево адаптивное + интерактивное
- ✅ User может исследовать дерево вручную
- ✅ Естественное поведение (как живая система)
- ✅ Phase 15 можно добавлять более сложную интерактивность

---

## 🔍 ГДЕ НАХОДИТСЯ КОД

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py`

**Секция:** `# ════════════════════════════════════════════════════════════════ # STEP 4: Serialize to JSON for frontend # ════════════════════════════════════════════════════════════════`

**ИЛИ** (если это в frontend): `frontend/templates/index.html` → JavaScript функции для drag-and-drop

---

## 📝 ЧТО МЕНЯТЬ

### ВАРИАНТ A: Backend Python (main.py)

Если интерактивность должна быть на frontend (Three.js), то нужно:

1. **Добавить в backend:**
   - Функции collision detection + repulsion (на Python)
   - WebSocket endpoint для отправки обновлённых позиций при drag

2. **Добавить в frontend:**
   - Mouse event listeners (mousedown, mousemove, mouseup)
   - Drag-and-drop logic (Three.js Raycaster)
   - Визуальная обратная связь (selection highlight)

### ВАРИАНТ B: Frontend JavaScript (index.html)

Проще и быстрее для первой версии!

---

## 💾 ГОТОВЫЙ КОД (ВАРИАНТ B - Frontend)

Добавь ЭТО в `index.html` (в `<script>` секцию где создаётся Three.js сцена):

```javascript
// ═══════════════════════════════════════════════════════════════════
// PHASE 2: INTERACTIVE DRAG-AND-DROP + ANTI-GRAVITY REPULSION
// ═══════════════════════════════════════════════════════════════════

import * as THREE from 'three';

// ─────────────────────────────────────────────────────────────────
// ANTI-GRAVITY FORMULAS (от Грока)
// ─────────────────────────────────────────────────────────────────

/**
 * FORMULA 1: File Collision Detection
 * 
 * Проверяет пересекаются ли файловые колонки двух папок
 */
function file_column_bounds(folder_x, file_card_width = 60, margin = 20) {
    const half_width = file_card_width / 2 + margin;
    return {
        x_min: folder_x - half_width,
        x_max: folder_x + half_width
    };
}

function check_file_collision(folder_a_x, folder_b_x, file_card_width = 60, min_gap = 20) {
    const bounds_a = file_column_bounds(folder_a_x, file_card_width, min_gap / 2);
    const bounds_b = file_column_bounds(folder_b_x, file_card_width, min_gap / 2);
    
    // Нет пересечения если один полностью слева или справа
    const no_overlap = (bounds_a.x_max < bounds_b.x_min || 
                        bounds_b.x_max < bounds_a.x_min);
    return !no_overlap;
}

/**
 * FORMULA 2: Interactive Dragging Repulsion
 * 
 * Вычисляет силу отталкивания (inverse-square law)
 * Используется при drag-and-drop
 */
function calculate_repulsion_force(moved_x, neighbor_x, k = 150, min_dist = 100, max_dist = 400) {
    let distance = Math.abs(moved_x - neighbor_x);
    
    // Если слишком далеко, не отталкиваем
    if (distance >= max_dist) {
        return 0;
    }
    
    // Если слишком близко, берём минимум (avoid infinity)
    if (distance <= min_dist) {
        distance = min_dist;
    }
    
    // Направление: +1 если сосед слева, -1 если справа
    const direction = neighbor_x < moved_x ? 1 : -1;
    
    // Inverse-square force: F = k / distance²
    const force = direction * (k / (distance * distance));
    return force;
}

/**
 * FORMULA 3: Group Anti-Gravity (AABB Bounding Box)
 * 
 * Проверяет пересекаются ли группы файлов, вычисляет раздвижение
 */
function file_group_bounds(folder_pos, files_count, file_spacing = 40, file_card_height = 50, margin = 20) {
    const half_width = file_card_height / 2 + margin;
    const y_extent = files_count > 1 ? (files_count - 1) * file_spacing / 2 : 0;
    
    return {
        x_min: folder_pos.x - half_width,
        x_max: folder_pos.x + half_width,
        y_min: folder_pos.y,
        y_max: folder_pos.y + y_extent * 2
    };
}

function group_repulsion_force(group_a, group_b) {
    // Вычислить overlap по X и Y
    const overlap_x = Math.min(group_a.x_max, group_b.x_max) - 
                      Math.max(group_a.x_min, group_b.x_min);
    const overlap_y = Math.min(group_a.y_max, group_b.y_max) - 
                      Math.max(group_a.y_min, group_b.y_min);
    
    // Если нет пересечения по обеим осям - нет конфликта
    if (overlap_x <= 0 || overlap_y <= 0) {
        return 0;
    }
    
    // Возвращаем силу раздвижения (каждая сторона на половину overlap)
    return overlap_x / 2;
}

// ─────────────────────────────────────────────────────────────────
// DRAG-AND-DROP STATE MANAGEMENT
// ─────────────────────────────────────────────────────────────────

const dragState = {
    isDragging: false,
    draggedNode: null,
    dragStartX: 0,
    dragStartY: 0,
    offsetX: 0,
    offsetY: 0,
    velocity: {}  // {node_id: vx} для плавного движения
};

// ─────────────────────────────────────────────────────────────────
// INTERACTION FUNCTIONS
// ─────────────────────────────────────────────────────────────────

/**
 * Получить ближайшие узлы в радиусе (для оптимизации)
 */
function getNearbyNodes(nodes, center_x, radius = 400) {
    return nodes.filter(node => {
        return Math.abs(node.position.x - center_x) < radius;
    });
}

/**
 * Применить repulsion forces при drag-and-drop
 */
function apply_dragging_repulsion(
    moved_node,
    nearby_nodes,
    positions_map,
    damping = 0.5
) {
    const velocity = dragState.velocity;
    
    for (const neighbor of nearby_nodes) {
        if (neighbor.id === moved_node.id) continue;  // Skip self
        
        const nid = neighbor.id;
        const old_x = positions_map[nid].x;
        
        // Вычислить силу отталкивания
        const force = calculate_repulsion_force(moved_node.position.x, old_x);
        
        // Velocity-based integration (Verlet-like)
        let v = velocity[nid] || 0;
        v = (v + force) * damping;  // Damping для плавности
        
        const new_x = old_x + v;
        
        positions_map[nid].x = new_x;
        neighbor.position.x = new_x;
        velocity[nid] = v;
    }
}

/**
 * Обновить позиции после drag
 */
function updateNodePosition(node, new_x, new_y) {
    node.position.x = new_x;
    node.position.y = new_y;
    
    // Обновить children (файлы если это папка)
    if (node.children && node.children.length > 0) {
        node.children.forEach((child, idx) => {
            child.position.x = new_x;  // Файлы следуют за папкой по X
            // Y остаётся фиксированным (из FORMULA FILE_SPACING)
        });
    }
}

/**
 * Обработать начало drag (mousedown)
 */
function onDragStart(event, node, camera, renderer) {
    dragState.isDragging = true;
    dragState.draggedNode = node;
    
    // Перевести позицию мыши в мир Three.js
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    
    mouse.x = (event.clientX / renderer.domElement.clientWidth) * 2 - 1;
    mouse.y = -(event.clientY / renderer.domElement.clientHeight) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);
    
    dragState.dragStartX = mouse.x;
    dragState.dragStartY = mouse.y;
    
    // Визуальная обратная связь: выделить узел
    node.material.emissive.setHex(0x444444);  // Потемнить
    
    console.log(`[DRAG] Started dragging node: ${node.name}`);
}

/**
 * Обработать movement (mousemove) во время drag
 */
function onDragMove(event, nodes, camera, renderer) {
    if (!dragState.isDragging || !dragState.draggedNode) return;
    
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    
    mouse.x = (event.clientX / renderer.domElement.clientWidth) * 2 - 1;
    mouse.y = -(event.clientY / renderer.domElement.clientHeight) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);
    
    // Вычислить новую позицию
    const delta_x = (mouse.x - dragState.dragStartX) * 1000;  // Scale for world coords
    const new_x = dragState.draggedNode.position.x + delta_x;
    const new_y = dragState.draggedNode.position.y;  // Y остаётся ФИКСИРОВАННЫМ!
    
    // Обновить позицию перемещаемого узла
    updateNodePosition(dragState.draggedNode, new_x, new_y);
    
    // Применить repulsion для соседних узлов
    const nearby = getNearbyNodes(nodes, new_x, 400);
    const positions_map = {};
    nodes.forEach(n => {
        positions_map[n.id] = { x: n.position.x, y: n.position.y };
    });
    
    apply_dragging_repulsion(
        dragState.draggedNode,
        nearby,
        positions_map,
        damping = 0.5
    );
    
    // Обновить позиции всех узлов в Three.js
    Object.entries(positions_map).forEach(([node_id, pos]) => {
        const node = nodes.find(n => n.id === node_id);
        if (node) {
            node.position.x = pos.x;
            node.position.y = pos.y;
        }
    });
    
    dragState.dragStartX = mouse.x;  // Update start для следующего движения
}

/**
 * Обработать конец drag (mouseup)
 */
function onDragEnd(event) {
    if (!dragState.isDragging) return;
    
    const node = dragState.draggedNode;
    
    // Восстановить визуальное состояние
    node.material.emissive.setHex(0x000000);  // Вернуть нормальный цвет
    
    dragState.isDragging = false;
    dragState.draggedNode = null;
    dragState.velocity = {};  // Очистить velocity для следующего drag
    
    console.log(`[DRAG] Finished dragging, velocity cleared`);
}

// ─────────────────────────────────────────────────────────────────
// ATTACH EVENT LISTENERS (вызвать в main scene setup)
// ─────────────────────────────────────────────────────────────────

function setupDragAndDrop(scene, camera, renderer) {
    // Получить все узлы из сцены
    const nodes = [];
    scene.traverse(obj => {
        if (obj.userData && obj.userData.type === 'node') {
            obj.id = obj.userData.id;
            nodes.push(obj);
        }
    });
    
    // Mousedown: начать drag
    renderer.domElement.addEventListener('mousedown', (event) => {
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2(
            (event.clientX / renderer.domElement.clientWidth) * 2 - 1,
            -(event.clientY / renderer.domElement.clientHeight) * 2 + 1
        );
        
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(nodes, false);
        
        if (intersects.length > 0) {
            const selected = intersects[0].object;
            onDragStart(event, selected, camera, renderer);
        }
    });
    
    // Mousemove: обновить позицию при drag
    renderer.domElement.addEventListener('mousemove', (event) => {
        if (dragState.isDragging) {
            onDragMove(event, nodes, camera, renderer);
        }
    });
    
    // Mouseup: завершить drag
    document.addEventListener('mouseup', onDragEnd);
    
    console.log('[INTERACTIVE] Drag-and-drop setup complete');
}

// ─────────────────────────────────────────────────────────────────
// EXPORT FUNCTIONS
// ─────────────────────────────────────────────────────────────────

export {
    setupDragAndDrop,
    calculate_repulsion_force,
    check_file_collision,
    group_repulsion_force,
    getNearbyNodes
};
```

---

## 📋 ШАГ-ЗА-ШАГОМ ИНТЕГРАЦИЯ

### ШАГ 1: Найти где рендерится сцена

В файле `index.html` (или `main.js` if separate) найди примерно:

```javascript
// Где-то там:
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(...);
const renderer = new THREE.WebGLRenderer(...);

// И rendering loop:
function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}
animate();
```

### ШАГ 2: После создания сцены добавить

```javascript
// Импортировать функции
import { setupDragAndDrop } from './interactive.js';  // Или скопировать код выше

// После создания scene, camera, renderer:
setupDragAndDrop(scene, camera, renderer);

console.log('[SETUP] Interactive drag-and-drop enabled!');
```

### ШАГ 3: Убедиться что все узлы имеют userData

В коде где создаются node meshes:

```javascript
// ДОЛЖНО БЫТЬ ТАК:
const nodeMesh = new THREE.Mesh(geometry, material);
nodeMesh.userData = {
    type: 'node',  // ← ВАЖНО! Используется в setupDragAndDrop
    id: node.id,   // ← ВАЖНО! Уникальный ID
    nodeData: node // ← Опционально: данные узла
};
scene.add(nodeMesh);
```

---

## ✅ CHECKLIST

- [ ] **Найти файл:** `index.html` (или где создаётся Three.js сцена)
- [ ] **Найти код:** Где создаётся `scene`, `camera`, `renderer`
- [ ] **Добавить код:** Скопировать весь JAVASCRIPT КОД выше (от `import * as THREE` до `export`)
- [ ] **Вызвать setup:** `setupDragAndDrop(scene, camera, renderer);`
- [ ] **Убедиться:** Все node meshes имеют `userData.type = 'node'` и `userData.id`
- [ ] **Сохранить:** Ctrl+S
- [ ] **Перезагрузить браузер:** F5 (или Cmd+Shift+R для hard refresh)
- [ ] **Открыть консоль:** F12 → Console tab
- [ ] **Проверить логи:**
  ```
  [INTERACTIVE] Drag-and-drop setup complete
  ```
- [ ] **Тест драга:**
  - Click на ветку/папку в 3D дереве
  - Потянуть мышкой
  - Соседние ветки должны **ОТТАЛКИВАТЬСЯ**!
  - Отпустить → movement плавно затухает (damping)

---

## 🎮 ОЖИДАЕМОЕ ПОВЕДЕНИЕ

### Что должно происходить:

**ДРАГА:**
```
User клик на папка A → папка A выделяется (потемнеет)
User тащит влево → папка A движется влево
→ Папка B (соседняя) АВТОМАТИЧЕСКИ отталкивается вправо
→ Всё выглядит ЖИВЫМ и РЕАГИРУЮЩИМ

User отпускает мышку:
→ Выделение исчезает
→ Папка A и B медленно стабилизируются (damping)
→ Velocity обнуляется для следующего drag
```

### В консоли должны быть логи:
```
[SETUP] Interactive drag-and-drop enabled!
[DRAG] Started dragging node: folder_xyz
[DRAG] Finished dragging, velocity cleared
```

---

## ⚙️ FINE-TUNING (если нужно настроить)

### Параметры repulsion:
```javascript
// В calculate_repulsion_force():
k = 150          // Сила отталкивания (↑ сильнее, ↓ слабее)
min_dist = 100   // Минимальное расстояние (ближе = сильнее)
max_dist = 400   // На сколько далеко действует (↑ дальше, ↓ ближе)
```

### Параметры damping (плавность):
```javascript
// В apply_dragging_repulsion():
damping = 0.5    // 0.3 = быстро затухает
                 // 0.5 = нормально (РЕКОМЕНДУЕМО)
                 // 0.7 = медленно затухает (дольше движется)
```

### Чувствительность drag:
```javascript
// В onDragMove():
const delta_x = (mouse.x - dragState.dragStartX) * 1000;
                                                    ↑
                                            ↑ чувствительность
                                    1000 = нормально
                                     500 = медленнее
                                    2000 = быстрее
```

---

## 🚀 ИТОГО

**БЫЛО (Phase 1):**  
✅ Адаптивный static layout

**СТАНЕТ (Phase 2):**  
✅ Адаптивный + интерактивный layout  
✅ Живое дерево с anti-gravity  
✅ User может исследовать вручную

**NEXT (Phase 15):**  
🔜 Более сложная интерактивность (zoom, rotate, special modes)

---

**Готово! Просто скопируй JavaScript КОД и вызови setupDragAndDrop()!** 🎮
