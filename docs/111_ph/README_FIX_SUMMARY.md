# VETKA Layout Fix - Краткое резюме

## 🚨 Проблема (найдена!)

Все папки на скриншоте на одном уровне Y - нет вертикальной иерархии.

### Причина: Дублирующий код layout в 3 местах!

```
Backend (fan_layout.py)        Frontend (layout.ts)           Frontend (useTreeData.ts)
    │                                │                                │
    ▼                                ▼                                ▼
folder_y = parent_y +          y = node.depth *              if (invalidRatio > 0.5)
           Y_PER_DEPTH                  LEVEL_HEIGHT                 calculateSimpleLayout()
    │                                │                                │
    │                                │                                ▼
    │                                │                         ПЕРЕЗАПИСЫВАЕТ ВСЕ Y!
    │                                │                         (даже правильные)
    └────────────────────────────────┴────────────────────────────────┘
                              ↓
                    ВИЗУАЛИЗАЦИЯ ПЛОСКАЯ
```

## ✅ Решение

### Вариант 1: Убрать fallback (РЕКОМЕНДУЕТСЯ)

Backend уже делает правильный layout - зачем frontend его перезаписывает?

```typescript
// useTreeData.ts - убрать fallback
const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
setNodesFromRecord(convertedNodes);  // ← Просто используем backend позиции
setEdges(edges);
// Всё! Fallback не нужен.
```

### Вариант 2: Исправить fallback

Если нужен fallback для legacy API:

```typescript
// layout.ts - не перезаписывать backend Y
function hasBackendPosition(node): boolean {
  // Проверяем что Y пришёл от backend (не fallback формула)
  const fallbackY = node.depth * LEVEL_HEIGHT;
  return node.position.y > 0 && Math.abs(node.position.y - fallbackY) > 1;
}

// Layout ТОЛЬКО для нод без backend позиций
const withBackend = nodes.filter(hasBackendPosition);
const needsLayout = nodes.filter(n => !hasBackendPosition(n));
return [...withBackend, ...calculateSimpleLayout(needsLayout)];
```

## 📁 Готовые файлы для копирования

| Файл | Описание |
|------|----------|
| `vetka_dag_layout_fixed.py` | Python модуль с Sugiyama layout для Knowledge Mode |
| `layout_fixed.ts` | Исправленный layout.ts для frontend |
| `useTreeData_fixed.ts` | Исправленный useTreeData.ts |

## 🔧 Быстрый фикс (5 минут)

### Шаг 1: Проверить логи

```typescript
// В useTreeData.ts добавить:
console.log('[DEBUG] First 3 nodes:', nodeArray.slice(0, 3).map(n => ({
  id: n.id,
  depth: n.depth,
  y: n.position.y,
  hasBackend: n.position.y > 0 && n.position.y !== n.depth * 20
})));
```

### Шаг 2: Убрать fallback

```typescript
// В useTreeData.ts найти:
if (needsLayout) {
  const positioned = calculateSimpleLayout(Object.values(allNodes));
  setNodes(positioned);
} else {
  setNodesFromRecord(allNodes);
}

// Заменить на:
setNodesFromRecord(allNodes);  // ← Всегда используем backend позиции
```

### Шаг 3: Перезагрузить

```bash
# Backend перезапуск НЕ нужен - он работает правильно!
# Перезагрузить только frontend
npm run dev
```

## 🎯 Ожидаемый результат

```
До (плоское):                    После (иерархия):
                                  
  context                          📄 file_d (y=600)
  interfaces                          │
  services    ← все на y=0         📄 file_c (y=450)
  utils                               │
  models                           📄 file_b (y=300)
  ...                                 │
                                   📄 file_a (y=150)
                                      │
                                     ═╧═ root (y=0)
```

## 📚 Готовые формулы DAG

В файле `vetka_dag_layout_fixed.py`:

1. **Sugiyama Layer Assignment** - топологическая сортировка
2. **Barycenter Crossing Reduction** - минимизация пересечений
3. **Anti-Gravity Repulsion** - предотвращение наложений
4. **Adaptive Fan Layout** - для Directory Mode

## ⚡ Проверка

После фикса в консоли должно быть:
```
[useTreeData] Using backend positions directly
[DEBUG] Folder positions: {root: y=0, src: y=150, utils: y=300, ...}
```

А не:
```
[useTreeData] Layout fallback triggered: 1500/2218 nodes invalid
```
