# 🔬 VETKA DAG Layout: Анализ проблем и готовые решения

## 📸 Проблема (со скриншота)

Все папки (`context`, `interfaces`, `services`, `utils` и т.д.) находятся на **одном уровне Y** - нет вертикальной иерархии. Дерево выглядит плоским, хотя backend правильно рассчитывает Y позиции.

---

## 🎯 Корневая причина найдена!

### Дублирующий код layout (3 места!)

```
┌─────────────────────────────────────────────────────────────────┐
│  PLACE 1: fan_layout.py (backend) - ПРАВИЛЬНЫЙ                  │
│  folder_y = parent_y + Y_PER_DEPTH  ← дети ВЫШЕ родителей       │
├─────────────────────────────────────────────────────────────────┤
│  PLACE 2: layout.ts (frontend) - ПЕРЕЗАПИСЫВАЕТ!                │
│  y = node.depth * LEVEL_HEIGHT  ← другое поведение!             │
├─────────────────────────────────────────────────────────────────┤
│  PLACE 3: useTreeData.ts - ТРИГГЕРИТ fallback!                  │
│  calculateSimpleLayout() вызывается если invalidRatio > 0.5     │
└─────────────────────────────────────────────────────────────────┘
```

### 🔴 Критический баг в useTreeData.ts (строки 118-161)

```typescript
// MARKER_109_DEVPANEL: Threshold-based fallback for layout
const config = getDevPanelConfig();
const nodeArray = Object.values(allNodes);
const totalNodes = nodeArray.length;

// MARKER_111_FIX: Count nodes with TRULY invalid positions
// Y=0 is VALID for root nodes! Only count as invalid if ALL coords are exactly 0
// AND it's not a root node (depth > 0 or has parent)
const invalidCount = nodeArray.filter(
  (n) => {
    const isZeroPosition = n.position.x === 0 && n.position.y === 0 && n.position.z === 0;
    const isRootNode = n.depth === 0 || !n.parentId;
    // Root nodes with (0,0,0) are VALID - they should be at origin
    // Only non-root nodes with (0,0,0) are invalid
    return isZeroPosition && !isRootNode;
  }
).length;

const invalidRatio = totalNodes > 0 ? invalidCount / totalNodes : 0;
const needsLayout = invalidRatio > (config.FALLBACK_THRESHOLD ?? 0.5);  // ← 50% порог!

// ⚠️ ВОТ ЗДЕСЬ ПРОИСХОДИТ ПЕРЕЗАПИСЬ!
if (needsLayout) {
  console.log(`[useTreeData] Layout fallback triggered: ${invalidCount}/${totalNodes} nodes invalid...`);
  const positioned = calculateSimpleLayout(Object.values(allNodes));  // ← ПЕРЕЗАПИСЬ!
  setNodes(positioned);
} else {
  setNodesFromRecord(allNodes);  // ← Используем backend позиции
}
```

### 🔴 Критический баг в layout.ts (строки 14-48)

```typescript
export function calculateSimpleLayout(nodes: TreeNode[]): TreeNode[] {
  const byDepth: Record<number, TreeNode[]> = {};
  nodes.forEach(node => {
    const d = node.depth;
    if (!byDepth[d]) byDepth[d] = [];
    byDepth[d].push(node);
  });

  // ...

  const positioned = nodes.map(node => {
    // ...
    const y = node.depth * LEVEL_HEIGHT;  // ← ВОТ! Перезаписывает Y из backend!
    // ...
    return {
      ...node,
      position: { x, y, z }  // ← Y теряется!
    };
  });

  return positioned;
}
```

---

## 🔧 Почему правки в backend не помогают

### Поток данных:

```
Backend (fan_layout.py)
    ↓
    folder_y = parent_y + Y_PER_DEPTH  ← Правильно: 0, 200, 400...
    ↓
API Response (tree_routes.py)
    ↓
    visual_hints.layout_hint.expected_y = positions[folder_path]['y']
    ↓
Frontend (useTreeData.ts)
    ↓
    convertApiResponse() → nodes с position.y из backend
    ↓
    ⚠️ ПРОВЕРКА: invalidRatio > 0.5 ?
    ↓
    ┌─────────────────┐    ┌─────────────────┐
    │  ДА (>50%)      │    │  НЕТ (<50%)     │
    │                 │    │                 │
    │ calculateSimple │    │ setNodesFromRec │
    │ Layout()        │    │ ord(allNodes)   │
    │ ↓               │    │ ↓               │
    │ y = depth * 20  │    │ Сохраняем       │
    │ (ПЕРЕЗАПИСЬ!)   │    │ backend Y!      │
    └─────────────────┘    └─────────────────┘
```

### Проблема 1: Неправильная проверка "invalid" nodes

```typescript
// Сейчас: считаем invalid если (0,0,0) и не root
const isZeroPosition = n.position.x === 0 && n.position.y === 0 && n.position.z === 0;
return isZeroPosition && !isRootNode;

// НО: backend может вернуть Y=0 для root, Y=200 для depth=1 и т.д.
// Если ВСЕ ноды имеют правильные Y от backend, но некоторые X=0 или Z=0,
// они НЕ считаются invalid - это правильно.

// ПРОБЛЕМА: если backend вернул Y=0 для root (правильно),
// а другие ноды тоже имеют Y=0 (неправильно - баг в backend),
// то они НЕ считаются invalid потому что Y=0!
```

### Проблема 2: Порог 50% слишком высокий

```typescript
const needsLayout = invalidRatio > (config.FALLBACK_THRESHOLD ?? 0.5);
// Если 40% нод "invalid" - fallback НЕ срабатывает
// Но если backend вернул плохие позиции для 60% нод - fallback сработает
// и ПЕРЕЗАПИШЕТ ВСЕ позиции, включая хорошие!
```

---

## ✅ Готовое решение (3 шага)

### Шаг 1: Исправить calculateSimpleLayout (layout.ts)

```typescript
// src/utils/layout.ts
// MARKER_111_FIX: НЕ перезаписывать Y если он уже задан backend'ом

export function calculateSimpleLayout(nodes: TreeNode[]): TreeNode[] {
  const byDepth: Record<number, TreeNode[]> = {};
  
  // Разделяем ноды: те что НУЖДАЮТСЯ в layout и те что УЖЕ имеют позиции
  const needsLayout: TreeNode[] = [];
  const hasPosition: TreeNode[] = [];
  
  nodes.forEach(node => {
    const pos = node.position;
    // Считаем что позиция "валидна" если Y > 0 (не на земле) или это root
    const isValid = pos.y > 0 || node.depth === 0 || !node.parentId;
    
    if (isValid && (pos.x !== 0 || pos.y !== 0 || pos.z !== 0)) {
      hasPosition.push(node);  // Уже есть позиция от backend
    } else {
      needsLayout.push(node);  // Нужен fallback layout
    }
  });
  
  // Layout только для тех кто нуждается
  needsLayout.forEach(node => {
    const d = node.depth;
    if (!byDepth[d]) byDepth[d] = [];
    byDepth[d].push(node);
  });

  // Сортируем siblings
  Object.keys(byDepth).forEach(depth => {
    byDepth[Number(depth)].sort((a, b) => {
      if (a.parentId === b.parentId) {
        return a.name.localeCompare(b.name);
      }
      return (a.parentId || '').localeCompare(b.parentId || '');
    });
  });

  // Вычисляем позиции ТОЛЬКО для needsLayout
  const fallbackPositioned = needsLayout.map(node => {
    const siblings = byDepth[node.depth];
    const index = siblings.indexOf(node);
    const count = siblings.length;

    const totalWidth = (count - 1) * HORIZONTAL_SPREAD;
    const x = -totalWidth / 2 + index * HORIZONTAL_SPREAD;
    const y = node.depth * LEVEL_HEIGHT;  // Только для fallback!
    const z = 0;

    return {
      ...node,
      position: { x, y, z }
    };
  });

  // Возвращаем ВСЕ ноды: hasPosition (с backend Y) + fallbackPositioned
  return [...hasPosition, ...fallbackPositioned];
}
```

### Шаг 2: Исправить проверку в useTreeData.ts

```typescript
// src/hooks/useTreeData.ts
// MARKER_111_FIX: Улучшенная проверка invalid nodes

const invalidCount = nodeArray.filter((n) => {
  const pos = n.position;
  
  // Ноды с позицией от backend имеют visual_hints.layout_hint
  const hasBackendPosition = 
    n.visualHints?.layoutHint?.expectedY !== undefined ||
    (pos.y > 0 && pos.y !== n.depth * 20);  // Y не равен fallback формуле
  
  // Root может быть в (0,0,0) - это нормально
  const isRootNode = n.depth === 0 || !n.parentId;
  
  // Invalid если: нет backend позиции И не root И на земле (Y=0)
  return !hasBackendPosition && !isRootNode && pos.y === 0;
}).length;

// Понижаем порог до 20%
const needsLayout = invalidCount > 0 && (invalidCount / totalNodes) > 0.2;

// ИЛИ ещё лучше - вообще убрать fallback для directory mode!
// Backend уже делает layout, зачем frontend его перезаписывает?
```

### Шаг 3: Убрать fallback полностью для directory mode (РЕКОМЕНДУЕТСЯ)

```typescript
// src/hooks/useTreeData.ts
// MARKER_111_NO_FALLBACK: Для directory mode используем ТОЛЬКО backend layout

if (response.tree) {
  const vetkaResponse: VetkaApiResponse = {
    tree: {
      nodes: response.tree.nodes,
      edges: response.tree.edges || [],
    },
  };

  const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
  
  // ... chat nodes processing ...

  const allNodes = { ...convertedNodes };
  chatTreeNodes.forEach((chatNode) => {
    allNodes[chatNode.id] = chatNode;
  });

  // ⚠️ УБИРАЕМ fallback - backend уже сделал layout!
  // const needsLayout = ...
  // if (needsLayout) { calculateSimpleLayout(...) }
  
  // Просто используем позиции от backend
  setNodesFromRecord(allNodes);
  setEdges([...edges, ...chatEdges]);
}
```

---

## 🌲 Готовые формулы для красивого DAG (Sugiyama-style)

### Формула 1: Вертикальное позиционирование (Y-ось)

```python
# fan_layout.py - уже реализовано, но проверьте:

def calculate_layer_height_vertical(max_depth: int, screen_height: int = 1080) -> float:
    """
    Адаптивная высота слоя в зависимости от глубины дерева.
    """
    available_height = screen_height * 0.6  # 60% экрана для дерева
    layer_height = available_height / max(1, max_depth)
    
    # Ограничения: мин 80px, макс 200px
    return max(80, min(200, layer_height))

# Использование:
Y_PER_DEPTH = calculate_layer_height_vertical(max_depth, screen_height)
folder_y = parent_y + Y_PER_DEPTH  # Дети ВЫШЕ родителей
```

### Формула 2: Горизонтальный разброс (X-ось) - Fan Layout

```python
import math

def layout_subtree(folder_path: str, parent_x: float, parent_y: float,
                   parent_angle: float, depth: int) -> None:
    """
    Рекурсивный fan layout - дети разбросаны веером.
    """
    folder = folders.get(folder_path)
    if not folder:
        return

    branch_params = calculate_adaptive_branch_params(
        folder_path, files_by_folder, depth, max_depth
    )
    adaptive_length = branch_params['length']

    angle_rad = math.radians(parent_angle)
    
    if depth == 0:
        # Root в центре
        folder_x, folder_y = 0, 0
    else:
        # X = parent_x + горизонтальный offset от угла
        # Y = parent_y + фиксированный шаг вверх
        folder_x = parent_x + math.sin(angle_rad) * adaptive_length
        folder_y = parent_y + Y_PER_DEPTH

    positions[folder_path] = {
        'x': folder_x,
        'y': folder_y,
        'angle': parent_angle
    }

    # Разбрасываем детей веером
    children = folder['children']
    if children and len(children) > 1:
        n_children = len(children)
        dynamic_fan_angle = calculate_dynamic_angle_spread(depth, max_depth, n_children)
        
        start_angle = parent_angle - dynamic_fan_angle / 2
        angle_step = dynamic_fan_angle / max(n_children - 1, 1)
        
        for i, child_path in enumerate(children):
            child_angle = start_angle + i * angle_step
            layout_subtree(child_path, folder_x, folder_y, child_angle, depth + 1)
```

### Формула 3: Sugiyama Layer Assignment (для Knowledge Mode DAG)

```python
# Для Knowledge Mode - топологическая сортировка + layer assignment

def sugiyama_layer_assignment(nodes: List[Node], edges: List[Edge]) -> Dict[str, int]:
    """
    Assign layers to nodes in DAG for Sugiyama layout.
    Returns: node_id -> layer_number (0 = bottom, N = top)
    """
    from collections import defaultdict, deque
    
    # Build adjacency list and in-degree
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    
    for edge in edges:
        graph[edge.source].append(edge.target)
        in_degree[edge.target] += 1
    
    # Topological sort with layer assignment
    layers = {}
    current_layer = 0
    queue = deque()
    
    # Start with nodes that have no incoming edges (roots)
    for node in nodes:
        if in_degree[node.id] == 0:
            queue.append(node.id)
            layers[node.id] = current_layer
    
    # BFS layer by layer
    while queue:
        layer_size = len(queue)
        next_queue = deque()
        
        for _ in range(layer_size):
            node_id = queue.popleft()
            
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    # Assign to NEXT layer (children above parents)
                    layers[neighbor] = current_layer + 1
                    next_queue.append(neighbor)
        
        queue = next_queue
        current_layer += 1
    
    return layers

# Position calculation
def calculate_sugiyama_positions(layers: Dict[str, int], 
                                  nodes_per_layer: Dict[int, List[str]],
                                  y_per_layer: float = 150) -> Dict[str, Position]:
    """
    Calculate X,Y positions from layer assignment.
    """
    positions = {}
    
    for layer_num, node_ids in nodes_per_layer.items():
        y = layer_num * y_per_layer
        n_nodes = len(node_ids)
        
        # Center nodes in layer
        total_width = (n_nodes - 1) * 100  # 100px spacing
        start_x = -total_width / 2
        
        for i, node_id in enumerate(sorted(node_ids)):
            x = start_x + i * 100
            positions[node_id] = Position(x=x, y=y, z=0)
    
    return positions
```

### Формула 4: Crossing Reduction (Barycenter Method)

```python
def minimize_crossings_barycenter(layers: Dict[int, List[str]], 
                                   edges: List[Edge]) -> Dict[int, List[str]]:
    """
    Reorder nodes within layers to minimize edge crossings.
    Uses barycenter heuristic.
    """
    from collections import defaultdict
    
    # Build edge mappings
    incoming = defaultdict(list)  # node -> list of source nodes
    outgoing = defaultdict(list)  # node -> list of target nodes
    
    for edge in edges:
        incoming[edge.target].append(edge.source)
        outgoing[edge.source].append(edge.target)
    
    # Process layers from bottom to top
    sorted_layers = {}
    
    for layer_num in sorted(layers.keys()):
        nodes = layers[layer_num]
        
        if layer_num == 0:
            # Bottom layer - sort alphabetically or by some other criteria
            sorted_layers[layer_num] = sorted(nodes)
        else:
            # Calculate barycenter for each node
            # Barycenter = average position of incoming neighbors
            node_barycenters = {}
            
            for node_id in nodes:
                sources = incoming.get(node_id, [])
                if sources:
                    # Get positions of sources from previous layer
                    prev_layer = sorted_layers[layer_num - 1]
                    positions = [prev_layer.index(s) for s in sources if s in prev_layer]
                    if positions:
                        node_barycenters[node_id] = sum(positions) / len(positions)
                    else:
                        node_barycenters[node_id] = float('inf')
                else:
                    node_barycenters[node_id] = float('inf')
            
            # Sort by barycenter
            sorted_layers[layer_num] = sorted(nodes, key=lambda n: node_barycenters[n])
    
    return sorted_layers
```

### Формула 5: Anti-Gravity (Repulsion) для предотвращения наложений

```python
def apply_repulsion(positions: Dict[str, Position], 
                    min_distance: float = 150,
                    iterations: int = 10) -> Dict[str, Position]:
    """
    Apply repulsion forces to prevent node overlapping.
    """
    import math
    
    pos_dict = {k: {'x': v.x, 'y': v.y} for k, v in positions.items()}
    
    for _ in range(iterations):
        for node_a in pos_dict:
            for node_b in pos_dict:
                if node_a >= node_b:
                    continue
                
                pos_a = pos_dict[node_a]
                pos_b = pos_dict[node_b]
                
                dx = pos_b['x'] - pos_a['x']
                dy = pos_b['y'] - pos_a['y']
                distance = math.sqrt(dx**2 + dy**2)
                
                if 0 < distance < min_distance:
                    # Push apart
                    overlap = min_distance - distance
                    push = overlap * 0.5
                    
                    if distance > 0:
                        nx = dx / distance
                        ny = dy / distance
                    else:
                        nx, ny = 1.0, 0.0
                    
                    pos_a['x'] -= nx * push
                    pos_b['x'] += nx * push
                    # Y stays fixed to maintain layer structure
    
    return {k: Position(x=v['x'], y=v['y'], z=0) for k, v in pos_dict.items()}
```

---

## 📋 Чеклист исправлений

### Немедленные действия:

- [ ] **1. Проверить что backend возвращает Y позиции**
  ```python
  # В tree_routes.py добавить логирование:
  print(f"[DEBUG] Folder {folder_path}: depth={folder['depth']}, y={pos.get('y', 'MISSING')}")
  ```

- [ ] **2. Проверить что frontend получает Y позиции**
  ```typescript
  // В useTreeData.ts добавить:
  console.log('[DEBUG] First folder node:', convertedNodes[Object.keys(convertedNodes)[0]]);
  ```

- [ ] **3. Убрать или исправить fallback**
  - Вариант A: Убрать fallback полностью (рекомендуется)
  - Вариант B: Исправить calculateSimpleLayout чтобы не перезаписывал backend Y

- [ ] **4. Проверить convertApiResponse**
  ```typescript
  // Убедиться что Y копируется из visual_hints.layout_hint.expected_y
  position: {
    x: apiNode.visual_hints?.layout_hint?.expected_x ?? 0,
    y: apiNode.visual_hints?.layout_hint?.expected_y ?? 0,  // ← ВАЖНО!
    z: apiNode.visual_hints?.layout_hint?.expected_z ?? 0,
  }
  ```

---

## 🎯 Итоговая рекомендация

**Самое простое и надёжное решение:**

1. Backend (`fan_layout.py`) уже делает правильный layout
2. Убрать `calculateSimpleLayout` fallback из frontend
3. Использовать backend позиции напрямую

```typescript
// В useTreeData.ts - максимально простой вариант:
const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
setNodesFromRecord(convertedNodes);
setEdges(edges);
// Всё! Fallback не нужен.
```

Если нужен fallback для edge cases (например, legacy API) - используйте исправленную версию из Шага 1.
