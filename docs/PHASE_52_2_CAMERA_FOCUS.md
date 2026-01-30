# Phase 52.2: Camera Focus on Chat History Select + Hostess Camera Tool

## ЦЕЛЬ

При выборе чата из истории (sidebar) — автоматически перемещать 3D камеру к соответствующему файлу в дереве.

## РЕАЛИЗАЦИЯ

### 1. CameraController Component (NEW)

**File**: `client/src/components/canvas/CameraController.tsx`

Новый React Three Fiber компонент для обработки команд камеры из store:

```tsx
export function CameraController() {
  const { camera } = useThree();
  const cameraCommand = useStore((state) => state.cameraCommand);
  const setCameraCommand = useStore((state) => state.setCameraCommand);

  // Listen for camera commands from store
  useEffect(() => {
    if (!cameraCommand) return;

    // Find node by path
    const node = findNodeByPath(cameraCommand.target);

    // Select and highlight
    selectNode(node.id);
    if (cameraCommand.highlight) {
      highlightNode(node.id);
      setTimeout(() => highlightNode(null), 2000);
    }

    // Calculate camera position based on zoom
    const zoomDistances = {
      close: 15,
      medium: 25,
      far: 40
    };

    // Animate camera
    targetPosition = nodePos + offset;
    targetLookAt = nodePos;
    startAnimation();
  }, [cameraCommand]);

  // Smooth animation in useFrame
  useFrame((_, delta) => {
    if (isAnimating) {
      camera.position.lerp(targetPosition, eased * 0.1);
      camera.lookAt(targetLookAt);
    }
  });
}
```

**Features**:
- ✅ Smooth ease-in-out camera animation
- ✅ Three zoom levels: close (15), medium (25), far (40)
- ✅ Auto-highlight target for 2 seconds
- ✅ Auto-select node in store
- ✅ Clears command after processing

---

### 2. Chat History Selection Trigger

**File**: `client/src/components/chat/ChatPanel.tsx:148-158`

Updated `handleSelectChat` to trigger camera focus:

```tsx
const handleSelectChat = async (chatId: string, filePath: string, fileName: string) => {
  // ... existing: load chat history ...

  // Phase 52.2: Focus camera on the file
  if (filePath) {
    console.log(`[ChatPanel] Requesting camera focus on: ${filePath}`);

    setCameraCommand({
      target: filePath,
      zoom: 'close',
      highlight: true
    });
  }
}
```

**Flow**:
1. User clicks chat in sidebar
2. Chat history loads (existing)
3. Camera command is set in store
4. CameraController picks up command
5. Camera smoothly flies to file
6. File is highlighted for 2s

---

### 3. Integration with App Canvas

**File**: `client/src/App.tsx:88`

Added CameraController to the Canvas:

```tsx
<Canvas>
  <OrbitControls />

  {/* Phase 52.2: Camera controller for smooth focus animations */}
  <CameraController />

  <TreeEdges />
  {nodes.map(node => <FileCard ... />)}
</Canvas>
```

---

## STORE INTEGRATION

### CameraCommand Type

```tsx
interface CameraCommand {
  target: string;      // File path to focus on
  zoom: 'close' | 'medium' | 'far';
  highlight: boolean;  // Whether to highlight target
}
```

### Store Actions

- `setCameraCommand(command)` — triggers camera animation
- Command is automatically cleared after processing
- Used by: ChatPanel, Socket handlers (future: Hostess camera_focus)

---

## USER FLOW

### Scenario 1: Click chat in sidebar
```
1. User opens chat sidebar (History icon)
2. User clicks on "dev_agent.py" chat
3. ✅ Chat messages load in panel
4. ✅ Camera smoothly flies to dev_agent.py node in 3D tree
5. ✅ dev_agent.py is highlighted (glow effect)
6. ✅ Node is selected (can view in artifact panel)
7. After 2s: highlight fades
```

### Scenario 2: Hostess says "show me X" (future)
```
1. User: "show me the API routes"
2. Hostess detects camera_focus intent
3. Backend emits 'camera_control' event
4. useSocket sets cameraCommand in store
5. ✅ Camera flies to API routes file
6. ✅ File is highlighted
```

---

## TECHNICAL DETAILS

### Camera Animation Math

**Position Calculation**:
```tsx
const offset = new THREE.Vector3(
  distance * 0.3,  // Right
  distance * 0.4,  // Above
  distance * 0.8   // In front
);

cameraPosition = nodePosition + offset;
```

**Zoom Distances**:
- **Close**: 15 units — for inspecting single file
- **Medium**: 25 units — for viewing file + nearby context
- **Far**: 40 units — for seeing branch/folder structure

**Easing Function** (ease-in-out):
```tsx
const eased = t < 0.5
  ? 2 * t * t
  : -1 + (4 - 2 * t) * t;
```

### Animation Loop

1. **Setup** (useEffect):
   - Find target node by path
   - Calculate target position + lookAt
   - Start animation flag

2. **Frame Update** (useFrame):
   - Interpolate camera position (lerp)
   - Update camera lookAt
   - Stop when progress >= 0.99

3. **Cleanup**:
   - Clear camera command from store
   - Reset animation state

---

## SOCKET INTEGRATION (Existing)

**File**: `client/src/hooks/useSocket.ts:193-204`

Already handles `camera_control` events from backend:

```tsx
socket.on('camera_control', (data) => {
  if (data.action === 'focus') {
    const command: CameraCommand = {
      target: data.target,
      zoom: data.zoom as 'close' | 'medium' | 'far',
      highlight: data.highlight,
    };
    setCameraCommand(command);
  }
});
```

**Backend Trigger** (user_message_handler.py:845-852):
```python
# When Hostess calls camera_focus tool
await sio.emit('camera_control', {
    'action': 'focus',
    'target': file_path,
    'zoom': 'close',
    'highlight': True
})
```

---

## VALIDATION

### Test Cases

1. **Chat Selection → Camera Focus**
   ```
   ✅ Click chat in sidebar
   ✅ Camera flies to file smoothly
   ✅ File is highlighted (glow)
   ✅ File is selected in store
   ✅ Can view file content in artifact panel
   ```

2. **Multiple Chat Switches**
   ```
   ✅ Click chat A → camera to A
   ✅ Click chat B → camera to B
   ✅ No animation conflicts
   ✅ Each animation completes smoothly
   ```

3. **Zoom Levels**
   ```
   ✅ close: camera at 15 units from file
   ✅ medium: camera at 25 units
   ✅ far: camera at 40 units
   ```

4. **Highlight Timeout**
   ```
   ✅ Highlight appears on focus
   ✅ Highlight fades after 2 seconds
   ✅ Can be interrupted by new selection
   ```

---

## LOGS

### Successful Camera Focus
```
[ChatPanel] Loaded chat dev_agent.py with 5 messages
[ChatPanel] Requesting camera focus on: src/agents/dev_agent.py
[CameraController] Processing command: {target: "src/agents/dev_agent.py", zoom: "close", highlight: true}
[CameraController] Animating to: dev_agent.py Vector3(45, 120, 230)
[CameraController] Animation complete
```

### Node Not Found
```
[CameraController] Processing command: {target: "unknown/file.py", zoom: "close"}
[CameraController] Node not found: unknown/file.py
```

---

## FILES CHANGED

### New Files
- ✅ `client/src/components/canvas/CameraController.tsx` — Camera animation logic

### Modified Files
- ✅ `client/src/App.tsx` — Added CameraController to Canvas
- ✅ `client/src/components/chat/ChatPanel.tsx` — Camera focus on chat select

### Existing Integration
- ✅ `client/src/hooks/useSocket.ts` — Socket handler for camera_control (no changes needed)
- ✅ `src/api/handlers/user_message_handler.py` — Hostess camera_focus tool (no changes needed)

---

## ДАЛЬНЕЙШИЕ УЛУЧШЕНИЯ (опционально)

1. **OrbitControls Coordination**
   - Temporarily disable OrbitControls during animation
   - Re-enable after animation complete

2. **Camera Trails**
   - Show motion trail during camera movement
   - Particle effects from source to destination

3. **Multi-target Focus**
   - Focus on multiple files simultaneously
   - Camera position that shows all targets

4. **Bookmark Positions**
   - Save favorite camera positions
   - Quick jump to bookmarked views

5. **Smooth OrbitControls Target Update**
   - Update OrbitControls.target along with camera
   - Maintain smooth rotation pivot

---

## СТАТУС
✅ **IMPLEMENTED** — Phase 52.2 Complete
- Camera focus on chat history selection
- Smooth camera animations with easing
- Node selection + highlighting
- Ready for Hostess camera_focus integration

## NEXT PHASE
Phase 53: Enhanced agent context awareness using chat history + CAM insights
