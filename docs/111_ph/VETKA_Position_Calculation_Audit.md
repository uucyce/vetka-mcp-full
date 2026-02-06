# 🔍 VETKA: Полный аудит вычисления позиций узлов

## 📋 Сводка: Все места где вычисляются/перезаписываются позиции

---

## 1. BACKEND (Python)

### 1.1 fan_layout.py - Основной layout алгоритм

| Строка | Код | Описание |
|--------|-----|----------|
| 501 | `folder_y = parent_y + Y_PER_DEPTH` | **КЛЮЧЕВАЯ**: Дети ВЫШЕ родителей (Y растет вверх) |
| 504-507 | `positions[folder_path] = {'x': folder_x, 'y': folder_y, ...}` | Сохранение позиции папки |
| 562 | `file_x = folder_x + math.sin(angle_rad) * file_dist` | X позиция файла |
| 572-576 | `file_y = (y_weight_time * y_time_component) + ...` | Y позиция файла (time + knowledge blend) |
| 587-598 | `positions[file_data['id']] = {'x': file_x, 'y': file_y, ...}` | Сохранение позиции файла |
| 718-726 | `positions[node_id]['y'] = min_y` / `max_y` | Применение floor/ceiling ограничений |
| 278-279 | `pos_a['x'] -= nx * push * 0.5` | Anti-gravity repulsion (только X) |
| 686 | `positions[file_id]['x'] += dx` | Сдвиг файлов при repulsion |

**Параметры:**
- `Y_PER_DEPTH` = 80-200px (адаптивно)
- `MIN_Y_FLOOR` = 20 (минимальная Y)
- `MAX_Y_CEILING` = 5000 (максимальная Y)

### 1.2 tree_routes.py - API endpoint

| Строка | Код | Описание |
|--------|-----|----------|
| 405-413 | `recalculate_depth(folder_path, current_depth)` | **ПЕРЕСЧЕТ DEPTH после layout!** |
| 496-500 | `'expected_x': pos.get('x', 0), 'expected_y': pos.get('y', 0)` | Позиции папок в visual_hints |
| 546-550 | `'expected_x': pos.get('x', 0), 'expected_y': pos.get('y', 0)` | Позиции файлов в visual_hints |
| 687-691 | `'expected_x': chat_x, 'expected_y': chat_y` | Позиции чатов в visual_hints |
| 739 | `update_artifact_positions(artifact_nodes, chat_nodes)` | Позиции артефактов |

**⚠️ КРИТИЧЕСКАЯ ПРОБЛЕМА:**
```python
# Строки 405-413: depth пересчитывается ПОСЛЕ того как layout рассчитан!
def recalculate_depth(folder_path, current_depth):
    folders[folder_path]['depth'] = current_depth  # ← Меняет depth!
```

Это значит что `depth` в API ответе может отличаться от того, что использовалось в layout!

---

## 2. FRONTEND (TypeScript)

### 2.1 useTreeData.ts - Загрузка данных

| Строка | Код | Описание |
|--------|-----|----------|
| 73 | `convertApiResponse(vetkaResponse)` | Конвертация API → TreeNode |
| 92-96 | `position = {x: apiChatNode.visual_hints.layout_hint.expected_x, ...}` | Извлечение позиции чата |
| 129-137 | `invalidCount = nodeArray.filter(...)` | Подсчет "invalid" нод |
| 140 | `needsLayout = invalidRatio > (config.FALLBACK_THRESHOLD ?? 0.5)` | Решение о fallback |
| 149-155 | `node.position = {x: semanticPos.x, y: semanticPos.y, ...}` | Semantic fallback |
| 161-163 | `console.warn(...Layout fallback DISABLED...)` | **Fallback отключен (Phase 111)** |
| 167 | `setNodesFromRecord(allNodes)` | Сохранение в store |
| 184 | `calculateSimpleLayout(treeNodes)` | Fallback для legacy API |

**⚠️ ПРОБЛЕМА: Проверка "invalid" нод:**
```typescript
// Строки 129-137
const invalidCount = nodeArray.filter((n) => {
  const isZeroPosition = n.position.x === 0 && n.position.y === 0 && n.position.z === 0;
  const isRootNode = n.depth === 0 || !n.parentId;
  return isZeroPosition && !isRootNode;  // ← Проверяет position, а не visual_hints!
}).length;
```

**Но где копирование из `visual_hints.layout_hint` в `node.position`?**

Это происходит в `convertApiResponse()` - который мы не видим в файлах!

### 2.2 layout.ts - Fallback layout

| Строка | Код | Описание |
|--------|-----|----------|
| 38 | `const y = node.depth * LEVEL_HEIGHT;` | **ПЕРЕЗАПИСЬ Y!** (LEVEL_HEIGHT = 20) |
| 41-44 | `return { ...node, position: { x, y, z } }` | Полная перезапись position |

```typescript
// Эта функция ПОЛНОСТЬЮ перезаписывает position!
export function calculateSimpleLayout(nodes: TreeNode[]): TreeNode[] {
  // ...
  const positioned = nodes.map(node => {
    // ...
    const y = node.depth * LEVEL_HEIGHT;  // ← 20 * depth (совсем другая формула!)
    return {
      ...node,
      position: { x, y, z }  // ← Backend Y теряется!
    };
  });
}
```

### 2.3 useStore.ts - Store операции

| Строка | Код | Описание |
|--------|-----|----------|
| 202-205 | `setNodes: (nodesList) => set({...})` | Установка нод (с пересчетом rootPath) |
| 207-210 | `setNodesFromRecord: (nodes) => set({...})` | Установка нод из Record |
| 232-240 | `updateNodePosition: (id, position) => set(...)` | Обновление позиции одной ноды |
| 243-293 | `moveNodeWithChildren: (id, newPosition) => set(...)` | Перемещение с детьми |
| 248-252 | `const delta = {x: newPosition.x - node.position.x, ...}` | Вычисление delta |
| 276-288 | `updatedNodes[childId].position.x += delta.x` | Применение delta к детям |

---

## 3. ПОРЯДОК ВЫПОЛНЕНИЯ

```
1. Backend: fan_layout.py
   ├── calculate_directory_fan_layout()
   │   ├── layout_subtree() → positions[folder_path] = {x, y}
   │   ├── layout_subtree() → positions[file_id] = {x, y, z}
   │   ├── calculate_static_repulsion() → меняет X
   │   └── floor/ceiling → меняет Y если выходит за bounds
   │
   └── Возвращает: positions dict

2. Backend: tree_routes.py
   ├── calculate_directory_fan_layout() → positions
   ├── recalculate_depth() ← **МЕНЯЕТ depth после layout!**
   │
   ├── Build folder nodes:
   │   └── visual_hints.layout_hint = {expected_x, expected_y, expected_z}
   │
   ├── Build file nodes:
   │   └── visual_hints.layout_hint = {expected_x, expected_y, expected_z}
   │
   └── Return JSON with visual_hints

3. Frontend: useTreeData.ts
   ├── fetchTreeData() → API response
   ├── convertApiResponse() ← **ГДЕ-ТО ЗДЕСЬ копируется visual_hints → position**
   │
   ├── Check "invalid" nodes:
   │   └── Смотрит на node.position (а не visual_hints!)
   │
   ├── (Fallback отключен в Phase 111)
   │
   └── setNodesFromRecord(allNodes) → сохраняет в Zustand

4. Frontend: TreeRenderer (Three.js)
   └── Использует node.position для рендера
```

---

## 4. ГДЕ ПРОИСХОДИТ ПЕРЕЗАПИСЬ?

### Вариант A: convertApiResponse не копирует visual_hints

```typescript
// Предполагаемая проблема в apiConverter.ts:
function convertApiResponse(response) {
  const nodes = {};
  response.tree.nodes.forEach(apiNode => {
    nodes[apiNode.id] = {
      id: apiNode.id,
      name: apiNode.name,
      // ❌ Забыли скопировать visual_hints.layout_hint в position!
      position: { x: 0, y: 0, z: 0 },  // ← Всегда нули!
      // ...
    };
  });
}
```

### Вариант B: Проверка invalidCount некорректна

```typescript
// Строка 129-137 useTreeData.ts:
const invalidCount = nodeArray.filter((n) => {
  const isZeroPosition = n.position.x === 0 && n.position.y === 0 && n.position.z === 0;
  // ...
  return isZeroPosition && !isRootNode;
}).length;

// Если convertApiResponse не скопировал позиции,
// то ВСЕ ноды будут с (0,0,0) → invalidCount = 100%
// → needsLayout = true (но fallback отключен в Phase 111)
```

### Вариант C: Legacy API path

```typescript
// Строки 170-194 useTreeData.ts:
} else if (response.nodes) {
  // Legacy API format
  const treeNodes = response.nodes.map(...convertLegacyNode...);
  const positioned = calculateSimpleLayout(treeNodes);  // ← FALLBACK!
  setNodes(positioned);
}
```

Если API возвращает `response.nodes` вместо `response.tree.nodes`,
то срабатывает legacy path с `calculateSimpleLayout`!

---

## 5. ПОЧЕМУ 7 НОД → СТАРОЕ ДЕРЕВО?

### Гипотеза 1: API возвращает разные форматы

```python
# Иногда API возвращает:
{
  "tree": { "nodes": [...], "edges": [...] },  # ← Новый формат
  "chat_nodes": [...]
}

# А иногда (после ошибки или кеша):
{
  "nodes": [...],  # ← Legacy формат!
  "edges": [...]
}
```

Если `response.tree` отсутствует, срабатывает legacy path с fallback layout!

### Гипотеза 2: DevPanel config меняется

```typescript
// Строка 122: const config = getDevPanelConfig();
// Если config.FALLBACK_THRESHOLD меняется динамически,
// то needsLayout может меняться между рендерами!
```

### Гипотеза 3: WebSocket/SSE обновления

```typescript
// Возможно есть WebSocket handler который обновляет позиции?
// Нужно проверить socket handlers!
```

### Гипотеза 4: Hot reload / HMR

```typescript
// При hot reload React remounts компоненты
// → useTreeData заново вызывается
// → API может вернуть кешированный/устаревший ответ
```

---

## 6. ЧТО НУЖНО ПРОВЕРИТЬ

### 6.1 Добавить логирование

```typescript
// В useTreeData.ts после строки 73:
const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);

// Добавить:
console.log('[DEBUG] API nodes count:', response.tree.nodes?.length);
console.log('[DEBUG] Converted nodes count:', Object.keys(convertedNodes).length);
console.log('[DEBUG] First node:', response.tree.nodes?.[0]);
console.log('[DEBUG] First converted:', convertedNodes[Object.keys(convertedNodes)[0]]);

// Проверить есть ли visual_hints:
const firstNode = response.tree.nodes?.[0];
console.log('[DEBUG] visual_hints:', firstNode?.visual_hints);
console.log('[DEBUG] layout_hint:', firstNode?.visual_hints?.layout_hint);
```

### 6.2 Проверить convertApiResponse

Найти файл `apiConverter.ts` и проверить:

```typescript
// Должно быть что-то вроде:
function convertApiNode(apiNode): TreeNode {
  return {
    id: apiNode.id,
    // ...
    position: {
      x: apiNode.visual_hints?.layout_hint?.expected_x ?? 0,
      y: apiNode.visual_hints?.layout_hint?.expected_y ?? 0,
      z: apiNode.visual_hints?.layout_hint?.expected_z ?? 0,
    },
    // ...
  };
}
```

### 6.3 Проверить API response format

```bash
# В браузере DevTools → Network → /api/tree/data
# Посмотреть что реально возвращает API
```

---

## 7. БЫСТРЫЙ ФИКС

### Если проблема в convertApiResponse:

```typescript
// Временный фикс в useTreeData.ts (строки 64-73):
if (response.tree) {
  // New VETKA API format
  
  // FIX: Копируем visual_hints в position если position пустой
  response.tree.nodes = response.tree.nodes.map(node => {
    if (node.visual_hints?.layout_hint) {
      return {
        ...node,
        position: {
          x: node.visual_hints.layout_hint.expected_x ?? node.position?.x ?? 0,
          y: node.visual_hints.layout_hint.expected_y ?? node.position?.y ?? 0,
          z: node.visual_hints.layout_hint.expected_z ?? node.position?.z ?? 0,
        }
      };
    }
    return node;
  });
  
  const vetkaResponse: VetkaApiResponse = {
    tree: {
      nodes: response.tree.nodes,
      edges: response.tree.edges || [],
    },
  };
  // ...
}
```

---

## 8. ИТОГО: Сколько мест вычисляют позиции?

| # | Файл | Функция | Строки | Тип |
|---|------|---------|--------|-----|
| 1 | fan_layout.py | `layout_subtree()` | 501, 504-507 | Backend - папки |
| 2 | fan_layout.py | `layout_subtree()` | 562, 572-576, 587-598 | Backend - файлы |
| 3 | fan_layout.py | `calculate_static_repulsion()` | 278-279, 686 | Backend - repulsion |
| 4 | fan_layout.py | floor/ceiling | 718-726 | Backend - ограничения |
| 5 | tree_routes.py | `recalculate_depth()` | 405-413 | Backend - depth (влияет на fallback!) |
| 6 | tree_routes.py | build folder nodes | 496-500 | Backend - visual_hints папок |
| 7 | tree_routes.py | build file nodes | 546-550 | Backend - visual_hints файлов |
| 8 | tree_routes.py | build chat nodes | 687-691 | Backend - visual_hints чатов |
| 9 | useTreeData.ts | semantic fallback | 149-155 | Frontend - semantic |
| 10 | layout.ts | `calculateSimpleLayout()` | 38, 41-44 | Frontend - fallback (ОТКЛЮЧЕН) |
| 11 | useStore.ts | `updateNodePosition()` | 232-240 | Frontend - drag |
| 12 | useStore.ts | `moveNodeWithChildren()` | 248-252, 276-288 | Frontend - drag с детьми |

**Всего: 12 мест** (4 в backend, 8 во frontend, но fallback отключен)

---

## 9. РЕКОМЕНДАЦИИ

1. **Проверить `apiConverter.ts`** - там скорее всего баг с копированием visual_hints
2. **Добавить логирование** в useTreeData.ts для отладки
3. **Убедиться что API всегда возвращает `response.tree`** а не `response.nodes`
4. **Проверить DevPanel config** - возможно там динамические изменения
5. **Проверить WebSocket handlers** - возможно есть обновления позиций
