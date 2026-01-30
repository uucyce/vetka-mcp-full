# АУДИТ: Viewport Context Integration Points
**Phase 70 — Точки интеграции для viewport-aware context**

> Дата: 2026-01-19
> Статус: ТОЛЬКО АУДИТ - БЕЗ ИЗМЕНЕНИЙ
> Автор: Claude Code

---

## ✅ 1. CAMERA

### 1.1 Определение Camera

| Параметр | Значение |
|----------|----------|
| **Файл** | `client/src/App.tsx:464-470` |
| **Тип** | `PerspectiveCamera` (via `@react-three/fiber`) |
| **FOV** | 60° |
| **Near** | 0.1 |
| **Far** | 10000 (extended for large trees) |
| **Initial Position** | `[0, 500, 1000]` |
| **Target** | `[0, 200, 0]` (OrbitControls) |

### 1.2 Доступ к Camera

```typescript
// ✅ Способ 1: useThree() hook (в Canvas children)
import { useThree } from '@react-three/fiber';

const { camera } = useThree();
// camera.position: Vector3
// camera.quaternion: Quaternion
// camera.fov: number
// camera.getWorldDirection(v: Vector3): Vector3
```

**Пример использования:**
- `CameraController.tsx:31` — получает camera через `useThree()`
- `FileCard.tsx:206` — расстояние до camera: `camera.position.distanceTo(nodePos)`
- `useDrag3D.ts:35` — направление camera: `camera.getWorldDirection(...).negate()`

### 1.3 OrbitControls

| Параметр | Значение |
|----------|----------|
| **Файл** | `client/src/App.tsx:478-493` |
| **Тип** | `OrbitControls` from `@react-three/drei` |
| **Минимальное расстояние** | 50 (close inspection) |
| **Максимальное расстояние** | 5000 (forest view) |
| **Damping** | enableDamping, factor=0.05 |
| **Зум** | enabled, speed=1.2 |

### 1.4 Глобальная ссылка на OrbitControls

```typescript
// App.tsx:482
(window as any).__orbitControls = controls;

// CameraController.tsx:160-166 — используется для синхронизации
const controls = window.__orbitControls;
if (controls) {
  controls.enabled = false; // Отключить во время анимации
  controls.minDistance = 10;
  controls.target.copy(targetPos);
  controls.enabled = true; // Включить после анимации
}
```

**Доступ из других компонентов:**
```typescript
const controls = (window as any).__orbitControls;
if (controls) {
  console.log('Current position:', controls.object.position);
  console.log('Current target:', controls.target);
  console.log('Current distance:', controls.getDistance());
}
```

---

## ✅ 2. NODE POSITIONS

### 2.1 Структура данных

**Файл:** `client/src/store/useStore.ts:7-25`

```typescript
export interface TreeNode {
  id: string;
  path: string;
  name: string;
  type: 'file' | 'folder';
  backendType: VetkaNodeType;
  depth: number;
  parentId: string | null;

  // *** MAIN POSITIONS ***
  position: { x: number; y: number; z: number };

  // Optional semantic position
  semanticPosition?: {
    x: number;
    y: number;
    z: number;
    knowledgeLevel: number;
  };

  color: string;
  extension?: string;
  children?: string[];
}
```

### 2.2 Хранилище позиций

| Параметр | Значение |
|----------|----------|
| **Store** | `useStore()` (Zustand) |
| **Поле** | `nodes: Record<string, TreeNode>` |
| **Тип позиции** | `{ x: number; y: number; z: number }` |
| **Обновление** | `updateNodePosition(id: string, position: {x, y, z})` |

### 2.3 Пример структуры Node

```typescript
// Один узел из store.nodes
{
  id: "file-123",
  path: "/root/src/components/App.tsx",
  name: "App.tsx",
  type: "file",
  depth: 3,
  parentId: "folder-456",

  // ✅ ПОЗИЦИЯ В 3D ПРОСТРАНСТВЕ
  position: {
    x: 125.4,
    y: 340.2,
    z: 89.7
  },

  color: "#3498db",
  extension: "tsx"
}
```

### 2.4 Получение всех nodes с позициями

```typescript
import { useStore } from '../../store/useStore';

// ✅ Способ 1: Get all nodes as array
const nodes = useStore((s) => Object.values(s.nodes));

// ✅ Способ 2: Get nodes record directly
const nodesRecord = useStore((s) => s.nodes);

// ✅ Способ 3: Get specific node
const nodeById = useStore((s) => s.nodes['file-123']);

// Пример получения всех позиций:
const allPositions = Object.entries(store.nodes).map(([id, node]) => ({
  id,
  position: node.position,
  path: node.path
}));
```

### 2.5 Отрисовка nodes в Canvas

**Файл:** `client/src/App.tsx:503-517`

```typescript
{nodes.map((node) => (
  <FileCard
    key={node.id}
    id={node.id}
    name={node.name}
    path={node.path}
    type={node.type}

    // ✅ ПОЗИЦИЯ ПЕРЕДАЕТСЯ СЮДА
    position={[node.position.x, node.position.y, node.position.z]}

    isSelected={selectedId === node.id}
    isHighlighted={highlightedId === node.id}
    onClick={() => selectNode(node.id)}
    children={node.children}
    depth={node.depth}
  />
))}
```

---

## ✅ 3. STORES

### 3.1 Основные stores

| Store | Путь | Назначение |
|-------|------|-----------|
| **useStore** | `client/src/store/useStore.ts` | Основное дерево + chat + camera |
| **chatTreeStore** | `client/src/store/chatTreeStore.ts` | Chat nodes как часть дерева |
| **roleStore** | `client/src/store/roleStore.ts` | Роли агентов |

### 3.2 useStore — главный store

**Файл:** `client/src/store/useStore.ts:56-133`

```typescript
interface TreeState {
  // *** TREE DATA ***
  nodes: Record<string, TreeNode>;
  edges: TreeEdge[];
  rootPath: string | null;

  // *** SELECTION & HIGHLIGHTING ***
  selectedId: string | null;
  hoveredId: string | null;
  highlightedId: string | null;        // Legacy single
  highlightedIds: Set<string>;         // Phase 69: Multi-highlight

  // *** CHAT DATA ***
  chatMessages: ChatMessage[];
  currentWorkflow: WorkflowStatus | null;
  isTyping: boolean;
  streamingContent: string;
  conversationId: string | null;

  // *** CAMERA ***
  cameraCommand: CameraCommand | null;

  // *** PINNED FILES (Phase 61) ***
  pinnedFileIds: string[];

  // *** UI STATE ***
  isLoading: boolean;
  error: string | null;
  isSocketConnected: boolean;
  isDraggingAny: boolean;
  grabMode: boolean;                  // Phase 65: Blender-style movement

  // ... methods
}
```

### 3.3 Pinned Files — структура

| Параметр | Значение |
|----------|----------|
| **Store** | `useStore()` |
| **Поле** | `pinnedFileIds: string[]` |
| **Тип** | Array of node IDs (strings) |
| **Получение** | `useStore((s) => s.pinnedFileIds)` |
| **Действия** | `togglePinFile()`, `pinSubtree()`, `pinNodeSmart()`, `clearPinnedFiles()` |

**Пример:**
```typescript
// ChatPanel.tsx:43
const pinnedFileIds = useStore((s) => s.pinnedFileIds);
const nodes = useStore((s) => s.nodes);

// Получить полные объекты pinned файлов
const pinnedNodes = pinnedFileIds
  .map(id => nodes[id])
  .filter(Boolean);
```

### 3.4 Methods в useStore

```typescript
// Nodes
setNodes(nodes: TreeNode[]) → Record<string, TreeNode>
setNodesFromRecord(nodes: Record<string, TreeNode>)
updateNodePosition(id: string, position: {x, y, z})
addNode(node: TreeNode)
removeNode(id: string)

// Selection
selectNode(id: string | null)
hoverNode(id: string | null)
highlightNode(id: string | null)
highlightNodes(ids: string[])        // Phase 69: Multi-highlight
clearHighlights()

// Pinned Files
togglePinFile(nodeId: string)
pinSubtree(rootId: string)
pinNodeSmart(nodeId: string)          // File: toggle, Folder: subtree
clearPinnedFiles()

// Chat
addChatMessage(msg: ChatMessage)
updateChatMessage(id: string, updates: Partial<ChatMessage>)
clearChat()

// Camera
setCameraCommand(command: CameraCommand | null)

// UI
setLoading(loading: boolean)
setError(error: string | null)
setSocketConnected(connected: boolean)
setDraggingAny(dragging: boolean)
setGrabMode(enabled: boolean)
```

---

## ✅ 4. MESSAGE SENDING

### 4.1 Функция sendMessage

**Файл:** `client/src/hooks/useSocket.ts:1019-1054`

```typescript
const sendMessage = useCallback(
  (message: string, nodePath?: string, modelId?: string) => {
    if (!socketRef.current?.connected) return;

    // ✅ ПОЛУЧИТЬ PINNED FILES ИЗ STORE
    const pinnedFileIds = useStore.getState().pinnedFileIds;
    const nodes = useStore.getState().nodes;

    // Преобразовать IDs в объекты
    const pinnedFiles = pinnedFileIds
      .map(id => nodes[id])
      .filter(Boolean)
      .map(node => ({
        id: node.id,
        path: node.path,
        name: node.name,
        type: node.type,
      }));

    // ✅ EMIT TO BACKEND
    socketRef.current.emit('user_message', {
      text: message,                    // Текст сообщения
      node_path: nodePath || 'unknown', // Текущий файл
      node_id: 'root',                  // ID узла
      model: modelId,                   // Модель (опционально)
      pinned_files: pinnedFiles.length > 0 ? pinnedFiles : undefined,
    });
  },
  []
);
```

### 4.2 Текущие параметры emit

| Параметр | Тип | Источник | Описание |
|----------|-----|---------|---------|
| `text` | string | ChatPanel input | Текст сообщения |
| `node_path` | string | selectedNode.path | Путь текущего узла |
| `node_id` | string | hardcoded 'root' | ID узла (обычно 'root') |
| `model` | string? | selectedModel | ID выбранной модели |
| `pinned_files` | PinnedFile[] | useStore.pinnedFileIds | Закрепленные файлы (Phase 61) |

**Структура PinnedFile:**
```typescript
{
  id: string;
  path: string;
  name: string;
  type: 'file' | 'folder';
}
```

### 4.3 Куда вызывается sendMessage

**Файл:** `client/src/components/chat/ChatPanel.tsx`

```typescript
const { sendMessage, isConnected, ... } = useSocket();

// В обработчике отправки сообщения:
const handleSendMessage = useCallback((userMessage: string) => {
  const selectedNode = useStore((s) => s.selectedId ? s.nodes[s.selectedId] : null);
  const selectedModel = /* ... */;

  sendMessage(
    userMessage,
    selectedNode?.path,
    selectedModel
  );
}, [sendMessage]);
```

### 4.4 Рекомендация: Добавить viewport_nodes

**Где добавить:**
1. **В sendMessage callback** — после получения pinnedFiles (строка ~1032)
2. **В emit объект** — как новый параметр наряду с `pinned_files`

**Структура viewport_nodes:**
```typescript
// Структура: массив узлов в текущем view
viewport_nodes: Array<{
  id: string;
  position: { x: number; y: number; z: number };
  path: string;
  type: 'file' | 'folder';
  distance_to_camera?: number;  // опционально
}>

// Пример:
viewport_nodes: allNodes
  .filter(node => isInViewFrustum(node.position, camera))
  .map(node => ({
    id: node.id,
    position: node.position,
    path: node.path,
    type: node.type,
    distance_to_camera: camera.position.distanceTo(
      new Vector3(node.position.x, node.position.y, node.position.z)
    )
  }))
```

---

## ✅ 5. VISIBILITY & FRUSTUM

### 5.1 Существующие механизмы

| Механизм | Статус | Файл | Описание |
|----------|--------|------|---------|
| **LOD System** | ✅ ЕСТЬ | `FileCard.tsx:9-28` | Google Maps style 10 уровней детализации |
| **Frustum culling** | ❌ НЕТ | — | Не реализовано |
| **Visibility check** | ⚠️ ЧАСТИЧНОЕ | `FileCard.tsx:206-240` | Только дистанция до camera |

### 5.2 LOD система (существующая)

**Файл:** `client/src/components/canvas/FileCard.tsx:9-28`

```typescript
// LOD 0 (distance > 300): Tiny dot
// LOD 1 (distance 200-300): Small shape
// LOD 2 (distance 150-200): Shape + name
// LOD 3 (distance 100-150): Clear shape + name
// LOD 4 (distance 70-100): Larger card + name
// LOD 5 (distance 50-70): Mini preview starts
// LOD 6 (distance 35-50): Mini preview full
// LOD 7 (distance 20-35): Large preview
// LOD 8 (distance 10-20): Full preview
// LOD 9 (distance < 10): Ultra close + extras
```

**Использование:**
```typescript
// FileCard.tsx:206-240
const dist = camera.position.distanceTo(
  new THREE.Vector3(node.position.x, node.position.y, node.position.z)
);

let lodLevel = 0;
if (dist > 300) lodLevel = 0;
else if (dist > 200) lodLevel = 1;
// ... etc
```

### 5.3 Информация о camera frustum

```typescript
// Получить camera frustum:
const camera = useThree().camera;
const frustum = new THREE.Frustum();
frustum.setFromProjectionMatrix(
  new THREE.Matrix4().multiplyMatrices(
    camera.projectionMatrix,
    camera.matrixWorldInverse
  )
);

// Проверить, содержится ли точка в frustum:
const point = new THREE.Vector3(node.position.x, node.position.y, node.position.z);
const isVisible = frustum.containsPoint(point);
```

### 5.4 Distance calculation (существующее)

```typescript
// FileCard.tsx:206
const dist = camera.position.distanceTo(
  new THREE.Vector3(
    node.position.x,
    node.position.y,
    node.position.z
  )
);
```

---

## ✅ 6. CAMERA CONTROLLER

### 6.1 Обзор

**Файл:** `client/src/components/canvas/CameraController.tsx`

**Назначение:** Анимирует камеру при фокусировке на узел + синхронизирует с OrbitControls

### 6.2 Camera Command Structure

```typescript
// useStore.ts:50-54
export interface CameraCommand {
  target: string;           // Имя файла или путь
  zoom: 'close' | 'medium' | 'far';
  highlight: boolean;
}
```

### 6.3 Поток выполнения

```
1. Другой компонент вызывает:
   useStore.getState().setCameraCommand({
     target: 'main.py',
     zoom: 'medium',
     highlight: true
   })

2. CameraController ловит изменение (useEffect)

3. CameraController находит узел по имени/пути

4. Вычисляет целевую позицию камеры

5. Отключает OrbitControls

6. Анимирует камеру (quaternion slerp + position lerp)

7. При завершении:
   - Включает OrbitControls
   - Синхронизирует target
   - Переключает chat context (selectNode)
```

### 6.4 Ключевые параметры

| Параметр | Значение |
|----------|----------|
| **Дистанция (close)** | 20 units |
| **Дистанция (medium)** | 30 units |
| **Дистанция (far)** | 45 units |
| **Vertical offset** | +3 units (look down) |
| **Approarch direction** | Z+ axis (frontal) |
| **Animation speed** | 2.5s (progress = delta * 0.4) |
| **Easing** | Ease-in-out (quadratic) |

---

## 📊 7. DATA FLOW DIAGRAM

### 7.1 Отправка сообщения с контекстом

```
ChatPanel (user types message)
    ↓
ChatPanel.handleSendMessage()
    ├─ Get selectedNode from store
    ├─ Get pinnedFileIds from store
    ├─ Get selectedModel from state
    └─ Call useSocket.sendMessage(text, nodePath, modelId)
         ↓
    useSocket.sendMessage()
         ├─ Get pinnedFileIds from store.pinnedFileIds
         ├─ Get nodes from store.nodes
         ├─ Transform to PinnedFile[] array
         └─ emit('user_message', {
              text,
              node_path,
              node_id,
              model,
              pinned_files,
              // *** NEW: viewport_nodes ***
            })
              ↓
    Backend receives event
```

### 7.2 Фокусировка камеры

```
Component (e.g., MentionPopup)
    ↓
setCameraCommand({ target, zoom, highlight })
    ↓
useStore updates cameraCommand state
    ↓
CameraController useEffect detects change
    ├─ Find node by path/name
    ├─ Disable OrbitControls
    ├─ Setup animation frame callback
    └─ useFrame hook runs each frame
         ├─ Interpolate position (lerp)
         ├─ Interpolate rotation (slerp)
         ├─ Update camera
         ├─ Check if done
         ├─ Re-enable OrbitControls
         └─ selectNode() → switch chat context
```

---

## 🔧 8. INTEGRATION POINTS SUMMARY

### 8.1 Точки для viewport_nodes интеграции

| Точка | Файл | Строка | Рекомендация |
|-------|------|--------|--------------|
| **1** | `useSocket.ts` | 1032-1053 | Добавить viewport_nodes перед emit |
| **2** | `CameraController.tsx` | 30-47 | Может выполнять getVisibleNodes() |
| **3** | `FileCard.tsx` | 206-240 | Уже вычисляет distance — переиспользовать |
| **4** | `App.tsx` | 464-518 | Can be wrapper to get camera + frustum info |

### 8.2 Помощные функции (для реализации)

```typescript
// Функция 1: Получить видимые узлы
function getVisibleNodes(nodes: TreeNode[], camera: PerspectiveCamera): TreeNode[] {
  const frustum = new THREE.Frustum();
  frustum.setFromProjectionMatrix(
    new THREE.Matrix4().multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    )
  );

  return Object.values(nodes).filter(node => {
    const point = new THREE.Vector3(node.position.x, node.position.y, node.position.z);
    return frustum.containsPoint(point);
  });
}

// Функция 2: Транформировать в viewport_nodes
function toViewportNodes(visibleNodes: TreeNode[], camera: PerspectiveCamera) {
  return visibleNodes.map(node => ({
    id: node.id,
    position: node.position,
    path: node.path,
    type: node.type,
    distance_to_camera: camera.position.distanceTo(
      new THREE.Vector3(node.position.x, node.position.y, node.position.z)
    )
  }));
}
```

---

## 📋 9. РЕКОМЕНДАЦИИ ДЛЯ РЕАЛИЗАЦИИ

### 9.1 Фаза 1: Preparation (0 часов — только аудит)
- ✅ Идентифицировать все integration points — DONE
- ✅ Документировать существующие механизмы — DONE
- ✅ Понять data flow — DONE

### 9.2 Фаза 2: Backend Setup (если нужно)
1. Обновить `user_message` event handler в backend
2. Добавить поле `viewport_nodes` в schema
3. Добавить валидацию для `viewport_nodes`
4. Обновить context assembly для использования `viewport_nodes`

### 9.3 Фаза 3: Frontend Implementation
1. **Создать helper функцию** в `client/src/utils/viewport.ts`:
   ```typescript
   export function getViewportNodes(
     nodes: Record<string, TreeNode>,
     camera: THREE.PerspectiveCamera
   ): ViewportNode[]
   ```

2. **Обновить sendMessage** в `client/src/hooks/useSocket.ts`:
   - Получить camera из где-нибудь (context или ref)
   - Вычислить viewport_nodes
   - Добавить в emit объект

3. **Оптимизация** (опционально):
   - Кэширование frustum
   - Дебаунсинг частых вызовов
   - LOD-aware filtering

### 9.4 Оценка сложности

| Компонент | Сложность | Время (est) |
|-----------|-----------|------------|
| **Helper функции** | Easy | 1 час |
| **Интеграция в sendMessage** | Medium | 2 часа |
| **Получение camera reference** | Medium | 1-2 часа |
| **Backend интеграция** | Medium | 2-3 часа |
| **Тестирование** | Easy | 1 час |
| **Оптимизация** | Hard | 2-4 часа |
| **ИТОГО** | — | **9-14 часов** |

---

## 🎯 10. KEY FINDINGS

### 10.1 ✅ Что уже есть

1. **Camera access** — легко получить через `useThree()`
2. **Node positions** — все узлы имеют `position: {x, y, z}`
3. **Store система** — Zustand, легко получать состояние
4. **Message sending** — уже передает `pinned_files`
5. **LOD система** — уже вычисляет distance
6. **Camera animation** — CameraController готов к sync

### 10.2 ⚠️ Вызовы

1. **Camera не доступна в useSocket** — нужен context или ref
2. **Frustum culling не реализован** — потребуется добавить
3. **No global viewport manager** — нужно создать utility функцию
4. **Distance дважды вычисляется** — в FileCard и в sendMessage (оптимизировать)

### 10.3 💡 Рекомендованный подход

```
Шаг 1: Создать context для camera
  → CameraProvider в App.tsx
  → useCamera() hook для доступа

Шаг 2: Создать viewport utility
  → getVisibleNodes(nodes, camera)
  → getViewportNodes(nodes, camera)

Шаг 3: Обновить sendMessage
  → Использовать useCamera() для получения camera
  → Вычислить viewport_nodes
  → Добавить в emit

Шаг 4: Оптимизировать
  → Кэшировать frustum между frames
  → Дебаунс вызовов sendMessage
```

---

## 📁 11. FILE LOCATIONS REFERENCE

| Файл | Назначение | Ключевые строки |
|------|-----------|-----------------|
| `App.tsx` | Canvas setup, OrbitControls | 464-518 |
| `CameraController.tsx` | Camera animation | 30-240 |
| `FileCard.tsx` | Node rendering, LOD, distance | 1-500 |
| `ChatPanel.tsx` | Chat UI, message sending | 1-600 |
| `useSocket.ts` | Socket events, sendMessage | 1019-1054 |
| `useStore.ts` | Zustand store | 135-310 |
| `useDrag3D.ts` | 3D interaction | 1-80 |
| `TreeEdges.tsx` | Edge rendering | 1-60 |
| `types/chat.ts` | Type definitions | 1-80 |
| `types/treeNodes.ts` | TreeNode types | 1-45 |

---

## ✅ ЗАКЛЮЧЕНИЕ

**Аудит завершен. Все integration points идентифицированы.**

Viewport-aware context может быть успешно интегрирован через:
1. Создание camera context/utility для доступа
2. Создание viewport utility функций
3. Обновление sendMessage для передачи viewport_nodes
4. Минимальные изменения в существующем коде

**Не требуется перестройка архитектуры.**

---

**Дата аудита:** 2026-01-19
**Версия проекта:** Phase 69.2 (Scanner→Qdrant chain fix)
**Статус:** AUDIT ONLY - NO CHANGES MADE
