# Phase 113.3: Session 4 — Z-Time Label Gravity + localStorage Discovery

**Date:** 2026-02-06
**Commander:** Claude Opus 4.6
**Duration:** ~3 часа
**Result:** Z-gravity откатан. Найден и устранён критический баг localStorage. Phase 113.1 savePositions/loadPositions отключены.
**Stable commit:** `e5b7bf08` (Phase 113.1+113.2)

---

## 1. ХРОНОЛОГИЯ СЕССИИ

### 1.1 Подход: Z-Time Label Gravity
**Идея (от Grok):** Физически сдвигать папки по оси Z в зависимости от `max_modified_time`. Свежие папки "всплывают" ближе к камере → LOD автоматически показывает их лейблы.

| Версия | Изменение | Результат |
|--------|-----------|-----------|
| **v1** | `MAX_LIFT=50`, линейная формула | Z-offset слишком мал для LOD (камера на Z=1000, дистанции 100-8000) |
| **v2** | `MAX_LIFT=400`, 4 нелинейных тира freshness | Файлы остались на Z=0, папки улетели → "веер" связей |
| **v3** | Per-branch Z (root folder определяет Z для всего поддерева) | Z-направление инвертировано (negative Z = дальше от камеры) |
| **v3.1** | Flip signs (positive Z = ближе к камере) | Фундаментальная проблема: вложенная иерархия Users→...→vetka_live_03→{client,src} нарушает пространственную когерентность |

### 1.2 Почему Z-gravity принципиально не работает
```
Users (depth=0) → danilagulin (depth=1) → Documents (depth=2)
→ VETKA_Project (depth=3) → vetka_live_03 (depth=4)
→ {client(depth=5), src(depth=5), docs(depth=5)}
```

**Дилемма:** Если двигать папки по Z индивидуально — дети отрываются от родителей. Если двигать branch целиком (root определяет Z) — все глубокие папки (client, src) получают Z от "Users" (depth=0), что бессмысленно.

**Вердикт:** Неразрешимое нарушение пространственной логики дерева.

### 1.3 Откат и обнаружение localStorage бага
1. `git checkout -- src/api/routes/tree_routes.py client/src/store/useStore.ts client/src/utils/apiConverter.ts` — код откатан
2. **Визуальные артефакты сохранились!** Дерево продолжало показывать "веер"
3. Аудит (5 haiku scouts): ВСЕ исходники CLEAN
4. Очистили `/Library/WebKit/vetka/WebsiteData/LocalStorage/` — **пустая директория-маркер!**
5. **НАХОДКА:** Реальный localStorage в SQLite: `/Library/WebKit/vetka/WebsiteData/Default/{hash}/LocalStorage/localstorage.sqlite3`
6. Ключ `vetka_node_positions` = **329 КБ** корраптированных Z-позиций от экспериментов
7. Удалён через `DELETE FROM ItemTable WHERE key = 'vetka_node_positions'`
8. Дерево восстановилось!

### 1.4 Повторная корраптация
После восстановления Phase 113.1 (`savePositions`) автоматически записала текущие позиции обратно → **485 КБ** нового кэша.
Решение: отключены `savePositions()` и `loadPositions()`.

---

## 2. PHASE 113.1 — PERSISTENT SPATIAL MEMORY

### 2.1 Как работает
```
[Drag end] → FileCard.tsx:890 → savePositions()
                                    ├── localStorage.setItem('vetka_node_positions', JSON.stringify(payload))
                                    └── socket.emit('save_positions', payload) [debounce 500ms]
                                            └── data/node_positions.json (backend)

[Tree load] → useTreeData.ts:170 → loadPositions()
                                        └── localStorage.getItem('vetka_node_positions')
                                            └── Override ALL node positions from API
```

### 2.2 Проблемы обнаруженные в этой сессии

| Проблема | Критичность | Описание |
|----------|-------------|----------|
| **Автосохранение корраптирует** | CRITICAL | Любой баг в позициях автоматически персистится и восстанавливается при каждом reload |
| **localStorage путь неочевиден** | HIGH | WebKit хранит данные в `Default/{hash}/LocalStorage/localstorage.sqlite3`, не в очевидном `LocalStorage/` |
| **Нет UI-контроля** | HIGH | Пользователь не может включить/отключить persistence, нет кнопки "сбросить позиции" |
| **Backend sync невидим** | MEDIUM | socket.emit('save_positions') тихо пишет в `data/node_positions.json` без UI |
| **Override ALL** | MEDIUM | `loadPositions()` перезаписывает ВСЕ позиции из API, даже если дерево изменилось |

### 2.3 Текущий статус
- `loadPositions()` в useTreeData.ts:170 — **ЗАКОММЕНТИРОВАН**
- `savePositions()` в FileCard.tsx:890 — **ЗАКОММЕНТИРОВАН**
- localStorage: очищен (485KB удалено)
- `data/node_positions.json`: не существует

### 2.4 Рекомендация: DevPanel Toggle
Нужен рычажок в DevPanel:
```
[✓] Persistent Spatial Memory (Phase 113.1)
    [Reset saved positions]
```
- Toggle включает/отключает savePositions + loadPositions
- Кнопка Reset очищает localStorage + backend file
- В будущем — перенести в пользовательский Settings UI

---

## 3. ИЗМЕНЕНИЯ В ФАЙЛАХ (текущее состояние)

| Файл | Изменение | Статус |
|------|-----------|--------|
| `src/api/routes/tree_routes.py` | VETKA root `expected_y: -80` (вместо 0) | ACTIVE |
| `client/src/hooks/useTreeData.ts:170` | `loadPositions()` закомментирован | ACTIVE |
| `client/src/components/canvas/FileCard.tsx:890` | `savePositions()` закомментирован | ACTIVE |
| `client/src/store/useStore.ts` | Без изменений (функции остались, просто не вызываются) | CLEAN |

---

## 4. ГИПОТЕЗЫ ДЛЯ PHASE 113.3 (следующая сессия)

### Гипотеза A: Nth-Label с LOD-корреляцией ⭐ РЕКОМЕНДОВАНА
**Идея:** Показывать каждую N-ю табличку, где N коррелирует с LOD-уровнем. На дальнем плане — каждая 8-я, на среднем — каждая 4-я, на крупном — каждая 2-я, на ближнем — все.

**Принцип:**
```
LOD distance range → Skip factor
> 2500              → show every 8th label (odd indices: 1, 9, 17...)
1500-2500           → show every 4th label (odd: 1, 5, 9, 13...)
800-1500            → show every 2nd label (odd: 1, 3, 5, 7...)
400-800             → show every label
< 400               → show all labels + file labels
```

**Преимущества:**
- Нет физического перемещения нод (Z не меняется)
- Нет стейта / scoring loop / useFrame overhead
- Чистая LOD-логика в FileCard.tsx (1 condition)
- Всегда примерно равное количество табличек на экране
- Начиная с нечётных — распределение равномерное по дереву
- Простая реализация: `if (folderIndex % skipFactor !== 0) hide`

**Открытые вопросы:**
- Как определить `folderIndex`? По порядку в sibling-группе? По алфавиту? По depth-first traverse order?
- Нужна ли приоритизация (свежие папки получают index 1)?
- Как обрабатывать pinned/highlighted — всегда показывать?

### Гипотеза B: Virtual Z-Score (LOD threshold modification)
**Идея:** Не двигать ноды физически, а модифицировать `importance` score в LOD формуле на основе freshness.

```typescript
// FileCard.tsx:1195
const timeBoost = freshnessFactor * 0.3; // 0..0.3
const importance = depthScore * 0.5 + sizeScore * 0.5 + timeBoost;
// Labels visible when: importance * MAX_DISTANCE(8000) > distToCamera
```

**Преимущества:** Не ломает позиции, использует существующую LOD систему.
**Риски:** Нужен `freshnessFactor` от бэкенда → apiConverter mapping → тот же путь что Z-gravity.

### Гипотеза C: Canvas-Baked Labels
**Идея:** Рендерить имя папки прямо на текстуру карточки (Canvas2D → Texture). Убрать Html overlays.

**Преимущества:** Нет DOM overhead, LOD нативный через Three.js distance.
**Риски:** Сложная реализация, потеря CSS-стилизации, размытие на близких дистанциях.

### Гипотеза D: Troika 3D Text (SDF)
**Идея:** Использовать troika-three-text для SDF-рендеринга текста прямо в 3D сцене.

**Преимущества:** Pixel-perfect на любом зуме, нативная LOD, нет DOM.
**Риски:** Новая зависимость, сложная интеграция с R3F, нет HTML-rich formatting.

---

## 5. РЕКОМЕНДАЦИИ

### Ближайшие действия
1. **DevPanel Toggle для Phase 113.1** — рычажок on/off для Persistent Spatial Memory + кнопка Reset
2. **Nth-Label (Гипотеза A)** — реализовать в следующей сессии как основной подход для 113.3
3. **Коммит текущих изменений** — зафиксировать отключение 113.1 save/load + VETKA y:-80

### Уроки сессии
1. **Phase 113.1 (Persistent Spatial Memory) — двусторонний меч:** полезна для drag-and-drop, но смертельна при багах в layout-коде. Нужен UI-контроль.
2. **WebKit localStorage != очевидный путь:** Tauri хранит данные в `Default/{hash}/LocalStorage/localstorage.sqlite3`, не в `LocalStorage/` директории.
3. **Z-axis manipulation несовместим с иерархическим деревом:** Физические координаты нельзя менять для отдельных нод без нарушения parent-child связей.
4. **Всегда проверять ВСЕ persistence layers:** git rollback недостаточен, когда есть localStorage + backend JSON + Qdrant.

---

*Session 4 complete. Дерево восстановлено. Ready for Phase 113.3 v5: Nth-Label approach.*
