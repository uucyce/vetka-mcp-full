# 🔬 VETKA Phase 111: Position Calculation Audit Report

**Дата:** 2026-02-04
**Методология:** Haiku scouts (9) → Sonnet verification (3) → Opus synthesis
**Статус:** ЗАВЕРШЁН

---

## 📊 EXECUTIVE SUMMARY

### Исследовано: 12 мест вычисления позиций
### Найдено критических проблем: 1 (вместо 3)
### Мёртвый код обнаружен: 1 место

**Главный вывод:** Изначальные гипотезы о 3 критических проблемах были **частично неверны**. Sonnet верификация опровергла 2 из 3 находок.

---

## 🎯 ВЕРИФИЦИРОВАННЫЕ ФАКТЫ

### ✅ ПОДТВЕРЖДЕНО: apiConverter fallback на (0,0,0)

**Файл:** `client/src/utils/apiConverter.ts:60-101`

```typescript
const visualHints = apiNode.visual_hints || {
  layout_hint: { expected_x: 0, expected_y: 0, expected_z: 0 },  // ← FALLBACK
  color: DEFAULT_COLORS[backendType]
};
const layoutHint = visualHints.layout_hint || { expected_x: 0, expected_y: 0, expected_z: 0 };

position: {
  x: layoutHint.expected_x ?? 0,  // ← Nullish coalescing
  y: layoutHint.expected_y ?? 0,
  z: layoutHint.expected_z ?? 0,
}
```

**Поведение:** Если backend не отправляет `visual_hints.layout_hint`, позиция **тихо** становится (0,0,0).

**Риск:** СРЕДНИЙ - backend должен всегда отправлять layout_hint, но при ошибках позиции теряются без предупреждения.

---

### ❌ ОПРОВЕРГНУТО: recalculate_depth ПОСЛЕ layout

**Haiku scout утверждал:** `recalculate_depth()` вызывается ПОСЛЕ `calculate_directory_fan_layout()`.

**Sonnet верификация:** НЕВЕРНО. Порядок операций в `tree_routes.py`:

```
Строка 412-413: recalculate_depth()      ← СНАЧАЛА (STEP 2.7)
Строка 434-439: calculate_fan_layout()   ← ПОТОМ (STEP 3)
```

**Вывод:** Depth корректно пересчитывается ДО fan_layout. Это НЕ проблема.

---

### ❌ ОПРОВЕРГНУТО: Legacy API path вызывает fallback

**Haiku scouts утверждали:** При `response.nodes` срабатывает `calculateSimpleLayout()` с формулой `Y = depth × 20`.

**Sonnet верификация:** Legacy path НЕДОСТИЖИМ (dead code).

**Доказательства:**

1. **Backend ВСЕГДА возвращает `response.tree`:**
```python
# tree_routes.py:754-777
response = {
    'format': 'vetka-v1.4',
    'tree': { ... },  # ← ВСЕГДА присутствует
}
```

2. **Даже при ошибках backend возвращает tree:**
```python
# tree_routes.py:784
return {'error': str(e), 'tree': {'nodes': [], 'edges': []}}
```

3. **Frontend early return при ошибках:**
```typescript
// useTreeData.ts:52-60
if (!response.success) {
  setError(...);
  return;  // ← НЕ достигает else if (response.nodes)
}
```

4. **Условие else if (response.nodes) НЕДОСТИЖИМО:**
```typescript
if (response.tree) {           // ← ВСЕГДА true
  // Process v1.4 format
} else if (response.nodes) {   // ← НИКОГДА не выполнится (dead code)
  calculateSimpleLayout(...)   // ← Мёртвый код
}
```

**Рекомендация:** Удалить строки 170-194 в useTreeData.ts (мёртвый код).

---

## 📐 АРХИТЕКТУРА ПОТОКА ПОЗИЦИЙ (ВЕРИФИЦИРОВАННАЯ)

```
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. tree_routes.py:412  →  recalculate_depth()                  │
│                              │                                   │
│                              ▼                                   │
│  2. tree_routes.py:434  →  calculate_directory_fan_layout()     │
│                              │                                   │
│                              ├── folder_y = parent_y + Y_PER_DEPTH│
│                              │   (Y_PER_DEPTH ∈ [80, 200]px)     │
│                              │                                   │
│                              └── file_y = time×0.5 + knowledge×0.5│
│                                                                  │
│  3. tree_routes.py:496  →  visual_hints.layout_hint.expected_y  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼  HTTP GET /api/tree/data
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  4. useTreeData.ts:73   →  convertApiResponse(vetkaResponse)    │
│                              │                                   │
│                              ▼                                   │
│  5. apiConverter.ts:83  →  position = {                         │
│                               x: layoutHint.expected_x ?? 0,     │
│                               y: layoutHint.expected_y ?? 0,    │ ← РИСК!
│                               z: layoutHint.expected_z ?? 0,     │
│                             }                                    │
│                                                                  │
│  6. useTreeData.ts:167  →  setNodesFromRecord(allNodes)         │
│                                                                  │
│  [DEAD CODE] useTreeData.ts:170-194 → calculateSimpleLayout()   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RUNTIME (WebSocket)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  7. useSocket.ts:628    →  socket.on('node_moved')              │
│                              updateNodePosition(path, position)  │
│                                                                  │
│  8. useSocket.ts:633    →  socket.on('layout_changed')          │
│                              Object.entries(positions).forEach() │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 НОВЫЕ ГИПОТЕЗЫ: Почему "7 нод → старое дерево"?

После опровержения изначальных гипотез, остаются:

### Гипотеза H1: Backend не отправляет visual_hints для некоторых нод

```typescript
// Если apiNode.visual_hints === undefined:
const layoutHint = visualHints.layout_hint || { expected_x: 0, ... };
// → position = (0,0,0) для этих нод
```

**Проверка:** Добавить логирование в convertApiNode:
```typescript
if (!apiNode.visual_hints?.layout_hint) {
  console.warn(`[apiConverter] Node ${apiNode.id} missing layout_hint!`);
}
```

### Гипотеза H2: WebSocket layout_changed перезаписывает позиции

```typescript
socket.on('layout_changed', (data) => {
  Object.entries(data.positions).forEach(([path, pos]) => {
    updateNodePosition(path, pos);  // ← Может отправлять неправильные позиции?
  });
});
```

**Проверка:** Добавить логирование в useSocket.ts:
```typescript
socket.on('layout_changed', (data) => {
  console.log('[socket] layout_changed positions:', data.positions);
  // ...
});
```

### Гипотеза H3: Cache inconsistency

Frontend или backend кеширует старые позиции и возвращает их при повторных запросах.

**Проверка:** Проверить Network tab - сравнить API response при первом и повторном запросах.

### Гипотеза H4: React re-render сбрасывает позиции

Zustand store может сбрасываться при определённых условиях (HMR, strict mode double-render).

**Проверка:** Добавить логирование в useStore.ts:
```typescript
setNodesFromRecord: (nodes) => {
  console.log('[store] setNodesFromRecord called, nodes:', Object.keys(nodes).length);
  // ...
}
```

---

## 📋 РЕКОМЕНДОВАННЫЕ ДЕЙСТВИЯ

### Приоритет 1: Диагностика

1. **Добавить логирование в apiConverter.ts:**
```typescript
// Строка 60 (начало convertApiNode)
console.log(`[apiConverter] Converting node ${apiNode.id}:`, {
  has_visual_hints: !!apiNode.visual_hints,
  has_layout_hint: !!apiNode.visual_hints?.layout_hint,
  expected_y: apiNode.visual_hints?.layout_hint?.expected_y
});
```

2. **Добавить логирование в useSocket.ts (строка 628):**
```typescript
socket.on('node_moved', (data) => {
  console.log('[socket] node_moved:', data);
  updateNodePosition(data.path, data.position);
});
```

### Приоритет 2: Cleanup

1. **Удалить мёртвый код в useTreeData.ts:170-194** (legacy path недостижим)

### Приоритет 3: Защита от (0,0,0)

1. **Добавить warning в apiConverter.ts:**
```typescript
if (layoutHint.expected_x === 0 && layoutHint.expected_y === 0 && layoutHint.expected_z === 0) {
  console.warn(`[apiConverter] Node ${apiNode.id} has (0,0,0) position - possibly missing layout!`);
}
```

---

## 📊 СТАТИСТИКА РАЗВЕДКИ

| Метрика | Значение |
|---------|----------|
| Haiku scouts отправлено | 9 |
| Sonnet верификаторов | 3 |
| Изначальных гипотез | 3 |
| Подтверждённых гипотез | 1 (33%) |
| Опровергнутых гипотез | 2 (67%) |
| Мёртвого кода найдено | 25 строк |
| Новых гипотез сгенерировано | 4 |

---

## 🏁 ЗАКЛЮЧЕНИЕ

Методология "Haiku разведка → Sonnet верификация" показала свою эффективность: **67% изначальных гипотез были неверны** и были отсеяны до фазы реализации.

**Оставшаяся проблема:** apiConverter fallback на (0,0,0) при отсутствии visual_hints.

**Следующий шаг:** Добавить диагностическое логирование и найти причину отсутствия visual_hints для некоторых нод.

---

*Документ сгенерирован: 2026-02-04*
*Архитектор: Claude Opus 4.5*
