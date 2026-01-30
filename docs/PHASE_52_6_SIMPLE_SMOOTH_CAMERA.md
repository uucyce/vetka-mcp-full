# Phase 52.6: Simple Smooth Camera Movement

## ПРОБЛЕМА

После Phase 52.5 с 3-фазной анимацией камеры пользователь жаловался:

1. **Резкие боковые рывки**: "сбивает в бок резко после выполнения команды"
2. **Подлет в упор + отдаление**: "в упор подлетаем к ноду и потом отдаляемся"
3. **Ненужное отдаление**: "резко выходить на общий план (даже если был на нем)"

**Главный запрос пользователя**:
> "Нам надо 'подлети туда' - камера там где была (если уже была на общем) плавно полдлетает **в одно движение** к объекту, мягко по началу и конку движения камеры."

**Ключевые слова**:
- **В одно движение** (in ONE movement)
- **Плавно** (smoothly)
- **Мягко по началу и конку** (soft at beginning and end)
- Без рывков, без лишних фаз

---

## РЕШЕНИЕ: Упрощение до Direct Movement

### Что было удалено

```tsx
// ❌ УДАЛЕНО: Сложная 3-фазная анимация
phase: 'pullback' | 'approach' | 'pushin'
pullbackPos, approachPos, finalPos
Complex phase transitions
Distance checks (< 30, < 50)
Midpoint calculations
```

### Что осталось

```tsx
// ✅ ПРОСТАЯ анимация
{
  active: boolean
  startPos: THREE.Vector3      // Откуда летим
  targetPos: THREE.Vector3     // Куда летим
  lookAt: THREE.Vector3        // На что смотрим
  progress: number             // 0 → 1
  nodeId: string
}
```

---

## КОД

### 1. Простое позиционирование (фронтально)

```tsx
// Phase 52.6: Simple frontal positioning
const finalDistance = cameraCommand.zoom === 'close' ? 12
                    : cameraCommand.zoom === 'medium' ? 20 : 35;

// Камера прямо перед node, немного выше
const targetPos = new THREE.Vector3(
  nodePos.x,
  nodePos.y + 3,  // Slightly above for better angle
  nodePos.z + finalDistance
);
```

**Визуализация**:
```
       NODE (x, y, z)
         🟦
         ↑
         | lookAt
         |
    📷 CAMERA (x, y+3, z+12)
```

**Фронтальный вид** — камера всегда прямо перед файлом, на одном X, немного выше по Y, отодвинута по Z.

---

### 2. Простая анимация (один lerp)

```tsx
// Simple smooth animation
useFrame((_, delta) => {
  if (!animationRef.current?.active) return;

  const anim = animationRef.current;

  // Progress speed (2.0s total animation)
  anim.progress = Math.min(anim.progress + delta * 0.5, 1);

  const t = anim.progress;

  // Ease-in-out interpolation
  const eased = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

  // ⭐ ГЛАВНОЕ: Simple direct interpolation from start to target
  const currentPos = new THREE.Vector3().lerpVectors(
    anim.startPos,
    anim.targetPos,
    eased
  );

  // Update camera position and lookAt
  camera.position.copy(currentPos);
  camera.lookAt(anim.lookAt);

  // Animation complete
  if (anim.progress >= 0.99) {
    // ... final positioning and cleanup ...
  }
});
```

**Ключевые моменты**:
- **Один `lerpVectors`** — прямая интерполяция от старой позиции к новой
- **Ease-in-out** — мягкое начало и конец (quadratic easing)
- **2.0s длительность** — `progress + delta * 0.5`
- **Нет фаз** — никаких pullback/approach/pushin

---

### 3. Ease-in-out формула

```tsx
// Quadratic ease-in-out
const eased = t < 0.5
  ? 2 * t * t              // Ease-in (first half)
  : -1 + (4 - 2 * t) * t;  // Ease-out (second half)
```

**График**:
```
Position
    ^
    |           ___---
    |       _--
    |    _-
    | _--
    -------------------> Time
    0    0.5    1

    Медленный старт → ускорение → замедление → плавная остановка
```

---

## ДИСТАНЦИИ

### Phase 52.6 Zoom Distances

```tsx
close:  12   // Крупный план файла
medium: 20   // Файл + ближайший контекст
far:    35   // Ветка дерева
```

**Сравнение с предыдущими версиями**:

| Phase | Close | Medium | Far |
|-------|-------|--------|-----|
| 52.3  | 8     | 15     | 25  |
| 52.4  | 5     | 12     | 20  |
| 52.5  | 8     | 15     | 25  |
| **52.6** | **12** | **20** | **35** |

**Почему 12 для close?**
- Не слишком близко (избегаем "в упор")
- Не слишком далеко (хорошо видно детали)
- Комфортная дистанция для рассмотрения файла

---

## РАЗНИЦА С PHASE 52.5

### Phase 52.5 (3-phase)

```tsx
// ❌ Сложная логика с тремя фазами
if (distance < 50) {
  // Skip pullback if already far
}

// Phase 1: Pullback (25% времени)
pullbackPos = midpoint + Vector3(0, 20, 30)

// Phase 2: Approach (45% времени)
approachPos = nodePos + Vector3(0, 8, 40)

// Phase 3: Push-in (30% времени)
finalPos = nodePos + finalDistance

// Transitions between phases
if (phase === 'pullback' && phaseProgress >= 1) {
  phase = 'approach'
  phaseProgress = 0
}
```

**Результат**: Рывки при переходах между фазами, ненужное отдаление, боковое смещение.

---

### Phase 52.6 (direct)

```tsx
// ✅ Простая прямая анимация
startPos = camera.position.clone()
targetPos = nodePos + Vector3(0, 3, finalDistance)

// One smooth lerp from start to target
currentPos = lerpVectors(startPos, targetPos, eased)
```

**Результат**: Плавное движение в одно движение, мягкое начало и конец, никаких рывков.

---

## ТЕХНИЧЕСКИЕ ДЕТАЛИ

### Node Search (без изменений)

```tsx
// Phase 52.6: Helper to find node by path or name
const findNode = (target: string) => {
  // 1. Exact path match
  // 2. Filename match (main.py → /full/path/main.py)
  // 3. Partial path match (docs/file.md → /full/path/docs/file.md)
};
```

Поиск node работает как в Phase 52.3-52.5.

---

### OrbitControls Sync (без изменений)

```tsx
// Animation complete
if (anim.progress >= 0.99) {
  // Sync OrbitControls
  const controls = window.__orbitControls;
  if (controls) {
    controls.target.copy(anim.lookAt);
    controls.update();
  }

  // Switch chat context
  selectNode(anim.nodeId);

  // Stop animation
  animationRef.current = null;
}
```

Синхронизация OrbitControls и переключение контекста чата остались без изменений.

---

## USER FLOW

### Сценарий 1: Клик на чат в истории

```
1. User clicks on "main.py" chat in sidebar
2. ChatPanel → setCameraCommand({target: "main.py", zoom: "close"})
3. CameraController finds node
4. ✅ Camera smoothly flies FROM current position TO (nodeX, nodeY+3, nodeZ+12)
5. ✅ Single lerp animation, 2.0s duration
6. ✅ Ease-in-out (soft start and end)
7. ✅ No jerking, no side movement
8. ✅ Arrives at comfortable distance (12 units)
9. OrbitControls synced, context switched
```

---

### Сценарий 2: Hostess "покажи X"

```
1. User: "покажи main.py"
2. Hostess → camera_focus tool → backend emits 'camera_control'
3. useSocket → setCameraCommand({target: "main.py", zoom: "close"})
4. ✅ Same smooth direct movement as Scenario 1
5. ✅ No pullback, no approach phases
6. ✅ Just smooth fly to target
```

---

## VALIDATION

### Проверки

1. **Плавность движения**
   ```
   ✅ Камера летит плавно без рывков
   ✅ Мягкое начало (ease-in)
   ✅ Мягкий конец (ease-out)
   ```

2. **Фронтальный вид**
   ```
   ✅ Камера всегда прямо перед файлом
   ✅ Никаких боковых углов
   ✅ NodeX = CameraX (centered)
   ```

3. **Нет "в упор + отдаление"**
   ```
   ✅ Финальная дистанция = 12 (комфортно)
   ✅ Никаких дополнительных движений после прибытия
   ✅ Камера останавливается в целевой позиции
   ```

4. **Нет лишнего отдаления**
   ```
   ✅ Если уже на общем плане → летит напрямую к файлу
   ✅ Если близко к файлу → летит напрямую к другому файлу
   ✅ Никаких ненужных pullback фаз
   ```

5. **OrbitControls после анимации**
   ```
   ✅ Можно вращать камеру вокруг файла
   ✅ Файл остаётся в центре
   ✅ Никаких "отскоков" назад
   ```

---

## LOGS

### Успешный переход между файлами

```
[ChatPanel] Requesting camera focus on: main.py
[CameraController] Processing command: {target: "main.py", zoom: "close", highlight: true}
[CameraController] Found by filename: main.py
[CameraController] Simple animation:
  Node: main.py
  Node position: Vector3(1222.8, 882, -2.8)
  Target camera: Vector3(1222.8, 885, 9.2)
  Distance: 12
[CameraController] Animation complete
[CameraController] OrbitControls synced
[CameraController] Context switched to: main_py_id
```

**Ключевое**: `Target camera: Vector3(1222.8, 885, 9.2)`
- Same X as node (фронтально)
- Y + 3 (немного выше)
- Z + 12 (комфортная дистанция)

---

## FILES CHANGED

### Modified Files

- ✅ `client/src/components/canvas/CameraController.tsx`
  - Removed 3-phase animation logic (~200 lines)
  - Simplified to direct lerp animation (~80 lines)
  - Updated zoom distances: 12, 20, 35
  - Frontal positioning: (x, y+3, z+distance)
  - Single animation state (no phases)

### Documentation

- ✅ `docs/PHASE_52_6_SIMPLE_SMOOTH_CAMERA.md`

---

## BEFORE/AFTER

### Animation Complexity

```
BEFORE (Phase 52.5):
  3 phases × 3 positions × transition logic
  = ~200 lines of animation code
  = Jerky transitions between phases

AFTER (Phase 52.6):
  1 lerp × ease-in-out curve
  = ~30 lines of animation code
  = Smooth single movement
```

### User Experience

```
BEFORE:
  1. Camera pulls back (резко)
  2. Camera approaches (сбоку)
  3. Camera pushes in (в упор)
  4. Camera backs away (отдаляется)
  → "сбивает в бок резко"

AFTER:
  1. Camera smoothly flies to target (плавно)
  → "в одно движение к объекту, мягко"
```

---

## ЦИТАТА ПОЛЬЗОВАТЕЛЯ

> "Нам надо 'подлети туда' - камера там где была (если уже была на общем) плавно полдлетает **в одно движение** к объекту, мягко по началу и конку движения камеры."

**Phase 52.6 реализует именно это**:
- ✅ "подлети туда" — direct lerp to target
- ✅ "в одно движение" — single animation phase
- ✅ "плавно" — smooth interpolation
- ✅ "мягко по началу и конку" — ease-in-out curve

---

## СТАТУС

✅ **IMPLEMENTED** — Phase 52.6 Complete
- Simple direct camera movement (no 3-phase)
- Smooth ease-in-out animation
- Frontal positioning (анфас)
- Comfortable distances (12, 20, 35)
- No jerking, no side angles
- No unnecessary pullback/approach phases

---

## NEXT PHASE

Phase 53: Enhanced agent context awareness with CAM + chat history integration

---

## ДОПОЛНИТЕЛЬНО: Vanilla Reference

Пользователь упомянул: **"На ваниле мы это сделали каким-то чудом с первого раза"**

Phase 52.6 возвращается к простоте "vanilla" подхода:
- Один lerp
- Ease-in-out
- Прямое движение
- Без лишних фаз

**Complexity is the enemy of smooth animation.**
