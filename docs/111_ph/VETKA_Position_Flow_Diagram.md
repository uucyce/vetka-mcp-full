# 🌊 VETKA: Диаграмма потока позиций

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    BACKEND (Python)                                      │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  fan_layout.py  │────→│ tree_routes.py  │────→│   JSON API      │
│   (layout)      │     │  (response)     │     │   Response      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. layout_subtree()                    4. recalculate_depth()         7. JSON Response   │
│    folder_y = parent_y + Y_PER_DEPTH      (МЕНЯЕТ depth!)             {                  │
│    positions[folder_path] = {x, y}          │                           tree: {          │
│                                           5. Build folder nodes           nodes: [{     │
│ 2. layout_subtree() for files               visual_hints: {                 visual_hints│
│    file_y = time/knowledge blend              layout_hint: {                  layout_hint│
│    positions[file_id] = {x, y, z}               expected_x,                     expected_│
│                                                 expected_y, →───────────────────expected_│
│ 3. Anti-gravity repulsion                       expected_z                   y: 200      │
│    positions[folder]['x'] += dx             }                              }]            │
│    positions[file]['x'] += dx             }                               }              │
│                                         6. Build file nodes                              │
│                                           (same structure)                               │
│                                         }                                                │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼ HTTP GET /api/tree/data
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND (TypeScript)                                  │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   fetchTreeData │────→│ useTreeData.ts  │────→│  convertApiResp │────→│   Zustand Store │
│   (API call)    │     │   (hook)        │     │  (converter)    │     │  (useStore.ts)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                       │                       │
                                ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ 8. Получаем response         10. Проверка invalid      12. setNodesFromRecord()          │
│    if (response.tree) {         const invalidCount =      nodes: {                       │
│                                 nodeArray.filter(n =>       [id]: {                       │
│ 9. convertApiResponse()         n.position.x === 0 &&         position: {x, y, z} ←───────┼
│    (ГДЕ-ТО ЗДЕСЬ                    && n.position.y === 0    }                            │
│     копируется                                            }                               │
│     visual_hints → position)                                                              │
│                              11. Fallback ОТКЛЮЧЕН                                       │
│                                  if (needsLayout) {                                        │
│                                    // НЕ ВЫПОЛНЯЕТСЯ!                                      │
│                                  }                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              TreeRenderer (Three.js)                                     │
│                                                                                          │
│  node.position.x ──→ mesh.position.x                                                     │
│  node.position.y ──→ mesh.position.y    ←── РЕНДЕРИТСЯ ЭТО!                              │
│  node.position.z ──→ mesh.position.z                                                     │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### Проблема 1: recalculate_depth ПОСЛЕ layout

```python
# tree_routes.py строки 405-413
def recalculate_depth(folder_path, current_depth):
    folders[folder_path]['depth'] = current_depth  # ← МЕНЯЕТ depth!

# Это вызывается ПОСЛЕ calculate_directory_fan_layout()!
# Но fallback layout в frontend использует depth!
```

**Последствие:** Если backend depth != frontend depth → разные Y позиции!

### Проблема 2: Непонятно где копируется visual_hints

```typescript
// useTreeData.ts строка 73
const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);

// convertApiResponse НЕ ВИДЕН в загруженных файлах!
// Возможно там баг - не копирует visual_hints.layout_hint в position
```

### Проблема 3: Проверка invalidCount смотрит на position

```typescript
// useTreeData.ts строки 129-137
const invalidCount = nodeArray.filter((n) => {
  const isZeroPosition = n.position.x === 0 && n.position.y === 0;
  // ...
}).length;

// Если convertApiResponse не скопировал visual_hints,
// то position = {0,0,0} для ВСЕХ нод!
```

---

## ✅ ЧТО РАБОТАЕТ ПРАВИЛЬНО

1. ✅ Backend layout (fan_layout.py) - правильно считает Y
2. ✅ Backend возвращает visual_hints с expected_x/y/z
3. ✅ Fallback layout ОТКЛЮЧЕН в Phase 111
4. ✅ setNodesFromRecord сохраняет ноды без изменений

---

## ❌ ЧТО СЛОМАНО

1. ❌ Возможно convertApiResponse не копирует visual_hints → position
2. ❌ recalculate_depth меняет depth после layout
3. ❌ Проверка invalidCount некорректна (смотрит на position вместо visual_hints)

---

## 🔧 БЫСТРЫЙ ДИАГНОСТИЧЕСКИЙ ФИКС

Добавь в useTreeData.ts (после строки 73):

```typescript
const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);

// === ДИАГНОСТИКА ===
const firstApiNode = response.tree.nodes?.[0];
const firstConvertedId = Object.keys(convertedNodes)[0];
const firstConverted = convertedNodes[firstConvertedId];

console.log('[DIAG] API node visual_hints:', firstApiNode?.visual_hints);
console.log('[DIAG] Converted node position:', firstConverted?.position);
console.log('[DIAG] Match:', 
  firstApiNode?.visual_hints?.layout_hint?.expected_y === firstConverted?.position?.y
);

// Если false - баг в convertApiResponse!
// === КОНЕЦ ДИАГНОСТИКИ ===
```

---

## 🎯 ВЕРОЯТНАЯ ПРИЧИНА "7 НОД → СТАРОЕ ДЕРЕВО"

```
┌─────────────────────────────────────────────────────────────────┐
│  СЦЕНАРИЙ: API иногда возвращает legacy формат                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Первый запрос: API работает нормально                       │
│     → response.tree.nodes (новый формат)                        │
│     → convertApiResponse копирует (или нет?) visual_hints       │
│     → 7 нод отображаются                                        │
│                                                                 │
│  2. Второй запрос: API возвращает ошибку/кеш/другой формат      │
│     → response.nodes (legacy формат!)                           │
│     → Срабатывает else if (response.nodes)                      │
│     → calculateSimpleLayout() - FALLBACK!                       │
│     → Старое дерево с Y = depth * 20                            │
│                                                                 │
│  3. ИЛИ: Hot reload / HMR                                       │
│     → Компонент remounts                                        │
│     → useTreeData вызывается заново                             │
│     → API возвращает кешированный ответ                         │
│     → Legacy формат → fallback layout                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 ЧЕКЛИСТ ДЛЯ ПОИСКА БАГА

- [ ] Найти файл `apiConverter.ts` и проверить `convertApiResponse()`
- [ ] Добавить логирование в useTreeData.ts (см. выше)
- [ ] Проверить Network tab в DevTools - что реально возвращает API
- [ ] Проверить есть ли WebSocket handlers которые обновляют позиции
- [ ] Проверить DevPanel config - не меняется ли динамически
- [ ] Убедиться что API всегда возвращает `response.tree` а не `response.nodes`
