# Phase 52.4: Camera Positioning + OrbitControls Sync + Context Switch

## ПРОБЛЕМЫ PHASE 52.3 → РЕШЕНИЯ PHASE 52.4

### 1. ❌ Камера показывала node "боком" после анимации

**Причина**: OrbitControls продолжал влиять на камеру после `camera.lookAt()`, поворачивая её обратно к старому target.

**Решение**: Синхронизация OrbitControls.target с позицией node

```tsx
// Phase 52.4: CRITICAL - Sync OrbitControls target
const controls = window.__orbitControls;
if (controls) {
  controls.target.copy(nodePosition);
  controls.update();
  console.log('[CameraController] OrbitControls target updated');
}
```

**Файлы**:
- `CameraController.tsx:170-176` — OrbitControls sync after animation
- `App.tsx:77-82` — Store OrbitControls ref in window

---

### 2. ❌ Zoom недостаточно близкий

**Было**: `close: 8, medium: 15, far: 25`
**Проблема**: При Y=882, Z=8 — камера слишком далеко от node

**Стало**: `close: 5, medium: 12, far: 20`

```tsx
// Phase 52.4: Closer zoom distances for better view
const zoomDistances = {
  close: 5,   // БЫЛО: 8
  medium: 12, // БЫЛО: 15
  far: 20     // БЫЛО: 25
};
```

**Результат**: Node крупнее, легче рассмотреть детали

---

### 3. ❌ Камера была выше node (не фронтально)

**Было**:
```tsx
targetPos = new THREE.Vector3(
  nodePos.x,
  nodePos.y + distance * 0.25,  // Выше node
  nodePos.z + distance
);
```

**Стало**:
```tsx
// Phase 52.4: TRUE frontal view - camera at same Y level
targetPos = new THREE.Vector3(
  nodePos.x,      // Same X (centered)
  nodePos.y,      // Same Y level (NOT above!)
  nodePos.z + distance  // In front on Z axis
);
```

**Результат**: Камера точно на уровне node, фронтальный вид

---

### 4. ❌ Не было переключения контекста чата при camera_focus

**Проблема**: Hostess отправляет `camera_focus` → камера летит → но чат остаётся для старого файла

**Решение**: Context switch после анимации

```tsx
// Animation complete
if (anim.progress >= 0.99) {
  // ... position camera ...

  // Phase 52.4: Switch chat context to focused node
  selectNode(anim.nodeId);
  console.log('[CameraController] Context switched to node:', anim.nodeId);
}
```

**Flow**:
1. Hostess: "покажи main.py"
2. Camera flies to main.py
3. ✅ `selectNode(main.py_id)` вызывается
4. ✅ ChatPanel's `useEffect` загружает историю main.py
5. ✅ Чат показывает правильный контекст

---

### 5. ✅ NEW: Клик на пустоту очищает чат

**Решение**: `onPointerMissed` в Canvas

```tsx
// App.tsx
const handleCanvasClick = () => {
  console.log('[App] Click on empty space - clearing selection');
  selectNode(null);
  // Chat will be cleared by ChatPanel's useEffect
};

<Canvas onPointerMissed={handleCanvasClick}>
```

**ChatPanel update**:
```tsx
useEffect(() => {
  // Phase 52.4: If no node selected, clear chat
  if (!selectedNode) {
    console.log('[ChatPanel] No node selected - clearing chat');
    clearChat();
    return;
  }

  // ... load chat for selected node ...
}, [selectedNode?.path]);
```

**Результат**: Клик на пустоту → node deselected → чат очищается

---

## ТЕХНИЧЕСКИЕ ДЕТАЛИ

### OrbitControls Synchronization

**Problem**: OrbitControls имеет собственный `target` (точка вращения). Если не обновить, камера "отскакивает" обратно.

**Solution**: Store ref globally, update target after animation

```tsx
// 1. Store ref in App.tsx
<OrbitControls
  ref={(controls) => {
    if (controls) {
      (window as any).__orbitControls = controls;
    }
  }}
/>

// 2. Update in CameraController after animation
const controls = window.__orbitControls;
if (controls) {
  controls.target.copy(nodePosition);
  controls.update();
}
```

**Why it works**:
- OrbitControls rotates around `target`
- After camera animation, `target` points to new node
- User can smoothly rotate around new node

---

### Camera Position Math

**Phase 52.4 Formula**:
```
nodePos = (x, y, z)  // Node position in 3D
distance = zoom === 'close' ? 5 : zoom === 'medium' ? 12 : 20

cameraPos = (
  nodePos.x,            // Same X
  nodePos.y,            // Same Y (frontal, not above)
  nodePos.z + distance  // In front on Z
)

camera.lookAt(nodePos)
```

**Visual**:
```
       NODE (x, y, z)
         🟦
         ↑
         | lookAt
         |
    📷 CAMERA (x, y, z+distance)
```

**No angle offset** — pure frontal view

---

### Animation Improvements

**Speed**: Changed from variable to fixed 1.5s

```tsx
// БЫЛО: Зависело от progress
const speed = 2.0;
animationProgress.current += delta * speed;

// СТАЛО: Фиксированная скорость (1.5s total)
anim.progress = Math.min(anim.progress + delta * 0.66, 1);
```

**Why**: Predictable timing, consistent UX

---

### Context Switch Flow

```
1. camera_focus command → CameraController
2. Animation starts
3. Camera flies to node
4. Animation completes (progress >= 0.99)
5. selectNode(nodeId) ✅
6. ChatPanel useEffect triggers
7. Loads chat history for new node ✅
```

**Before Phase 52.4**:
- Camera focuses ✅
- Chat context stays old ❌

**After Phase 52.4**:
- Camera focuses ✅
- Chat context switches ✅

---

## VALIDATION

### Test Cases

1. **Camera Focus from Chat History**
   ```
   ✅ Click chat in sidebar
   ✅ Camera flies to node (frontal view)
   ✅ Node at same Y level as camera
   ✅ Close zoom (5 units)
   ✅ After animation: can rotate around node
   ```

2. **Hostess camera_focus + Context Switch**
   ```
   User: "покажи main.py"
   ✅ Camera flies to main.py
   ✅ main.py is selected
   ✅ Chat loads main.py history
   ✅ Context switched correctly
   ```

3. **Click on Empty Space**
   ```
   ✅ Click on empty 3D space
   ✅ Node is deselected (selectedNode = null)
   ✅ Chat is cleared
   ✅ No errors in console
   ```

4. **OrbitControls After Animation**
   ```
   ✅ Camera completes animation
   ✅ Can rotate camera around node
   ✅ Node stays centered
   ✅ No "snap back" to old position
   ```

5. **Zoom Levels**
   ```
   ✅ close: 5 units from node
   ✅ medium: 12 units from node
   ✅ far: 20 units from node
   ✅ All frontal (not side angle)
   ```

---

## LOGS

### Successful Camera Focus + Context Switch
```
[CameraController] Processing command: {target: "main.py", zoom: "close", highlight: true}
[CameraController] Found by filename: main.py
[CameraController] Node: main.py
[CameraController] Node position: Vector3(1222.8, 882, -2.8)
[CameraController] Target camera position: Vector3(1222.8, 882, 2.2)
[CameraController] Animation complete
[CameraController] OrbitControls target updated to: Vector3(1222.8, 882, -2.8)
[CameraController] Context switched to node: main_py_id
[ChatPanel] File changed to: /Users/.../main.py
[ChatPanel] Found chat for main.py, loading messages...
[ChatPanel] Loaded 3 messages for main.py
```

### Click on Empty Space
```
[App] Click on empty space - clearing selection
[ChatPanel] No node selected - clearing chat
```

---

## FILES CHANGED

### Modified Files
- ✅ `client/src/components/canvas/CameraController.tsx`
  - OrbitControls sync after animation (lines 170-176)
  - Context switch on complete (lines 178-180)
  - Closer zoom distances: 5, 12, 20 (lines 110-114)
  - True frontal view (lines 118-123)
  - Faster animation speed: 1.5s (line 150)

- ✅ `client/src/App.tsx`
  - OrbitControls ref storage (lines 77-82)
  - onPointerMissed handler (line 79)
  - handleCanvasClick to deselect (lines 30-35)

- ✅ `client/src/components/chat/ChatPanel.tsx`
  - Handle null selectedNode (lines 171-176)
  - Clear chat on deselection

### New Documentation
- ✅ `docs/PHASE_52_4_CAMERA_POSITIONING.md`

---

## BEFORE/AFTER COMPARISON

### Camera Angle
```
BEFORE:
  Camera at (x, y+2, z+8)
  Looking down at node
  Side/angle view ❌

AFTER:
  Camera at (x, y, z+5)
  Same Y level as node
  Pure frontal view ✅
```

### OrbitControls
```
BEFORE:
  Animation completes
  Camera.lookAt(node)
  OrbitControls.target = old position
  → Camera "snaps back" ❌

AFTER:
  Animation completes
  Camera.lookAt(node)
  OrbitControls.target = node position
  → Can rotate around node ✅
```

### Context Switch
```
BEFORE:
  Hostess: "покажи main.py"
  Camera flies to main.py ✅
  Chat still shows old file ❌

AFTER:
  Hostess: "покажи main.py"
  Camera flies to main.py ✅
  Chat loads main.py history ✅
```

### Deselection
```
BEFORE:
  Click empty space
  Nothing happens ❌

AFTER:
  Click empty space
  Node deselected ✅
  Chat cleared ✅
```

---

## ДАЛЬНЕЙШИЕ УЛУЧШЕНИЯ (опционально)

1. **Disable OrbitControls During Animation**
   - Prevent user rotation while animating
   - Re-enable after complete

2. **Smooth OrbitControls Target Transition**
   - Animate target change along with camera
   - Even smoother experience

3. **Camera Bookmarks**
   - Save favorite viewpoints
   - Quick jump to saved positions

4. **Multi-Node Focus**
   - Frame multiple nodes in view
   - Calculate optimal camera position

5. **Adaptive Zoom**
   - Adjust distance based on node depth
   - Larger zoom for root, closer for leaves

---

## СТАТУС
✅ **IMPLEMENTED** — Phase 52.4 Complete
- OrbitControls synchronization
- True frontal camera view
- Closer zoom distances (5, 12, 20)
- Context switch on camera focus
- Deselection on empty click
- Faster animation (1.5s)

## NEXT PHASE
Phase 53: Agent context enhancement with CAM + chat history
