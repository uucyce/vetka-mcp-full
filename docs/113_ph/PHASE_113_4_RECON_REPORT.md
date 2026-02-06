# Phase 113.4: Nth-LOD Labels — Единый отчёт разведки и верификации

**Дата:** 2026-02-06
**Командир:** Claude Opus 4.6
**Разведка:** 9 Хайку (4 пакета) | **Верификация:** 3 Соннета

---

## EXECUTIVE SUMMARY

Обнаружена критическая развилка: Грок предложил Approach A (Nth-Label skipFactor по modulo), но в проекте уже существует написанный `labelScoring.ts` (216 строк, 0 импортов) -- Approach B (score-based top-N).

**Вердикт всех 3 Соннетов: APPROACH B (score-based) -- ОСНОВНОЙ.**
**Approach A -- DEFER до Phase 113.5+ как опциональная оптимизация.**

---

## 1. РАЗВЕДКА: МАРКЕРЫ (9 Хайку)

### FileCard.tsx (Scout #1)
- **LOD логика лейблов:** строки 1188-1269 (importance = depth*0.5 + size*0.5)
- **Visibility threshold:** `importance * MAX_DISTANCE(8000) > distToCamera`
- **Label render:** `<Html>` из @react-three/drei (DOM overlay)
- **distToCamera:** `camera.position.distanceTo()` (строка 1193)
- **savePositions:** закомментирован строка 890
- **skipFactor:** НЕТ
- **Siblings доступ:** НЕТ -- FileCard не знает свой index среди братьев

### useTreeData.ts + useStore.ts (Batch A)
- **loadPositions():** закомментирован строка 171
- **parentId:** есть в TreeNode -- можно находить siblings
- **pinnedFileIds[]:** в store -- override для skip
- **Сортировка siblings:** НЕ реализована
- **nodes:** `Record<string, TreeNode>` -- поиск siblings через parentId O(N)
- **savePositions/loadPositions:** в store строки 419-499, disabled

### tree_routes.py + apiConverter.ts (Batch B)
- **modified_time:** ЕСТЬ в backend (строка 543), НЕ конвертируется в frontend!
- **created_time:** аггрегируется для папок (min по файлам, строки 376-398)
- **y:-80 offset:** для root node (строка 468)
- **indexInSiblings:** НЕ существует нигде
- **children:** через edges в backend, НЕ через массив

### DevPanel + labelScoring.ts (Batch C)
- **labelScoring.ts:** 216 строк, 6 функций, 0 импортов (мёртвый код!)
  - `computeLabelScore(node, isPinned, isHighlighted)` → 0-1
  - `selectTopLabels(scores, pinnedIds, visibleCount, zoomLevel)` → adaptive top 5-30
  - `applyHysteresis(current, prev, threshold)` → anti-flicker
  - `goldenAngleJitterZ(rank, total)` → anti-overlap ±0.8 Z
  - `arraysEqual(a, b)` → store churn guard
- **DevPanel:** toggles через localStorage + custom events
- **devConfig.ts:** interface + DEFAULT_CONFIG + get/save/reset

### Scene3D + 113.3 report (Batch D)
- **FrustumCulledNodes:** App.tsx строки 49-132, useFrame каждые 200ms
- **FileCard итерация:** строки 112-129, 13 props, lodLevel от parent
- **Batch LOD:** `calculateAdaptiveLODWithFloor` в frustum loop
- **Z-gravity:** ЗАКРЫТ -- фундаментально несовместимо с иерархией
- **Гипотеза A (Nth-Label):** рекомендована отчётом 113.3, НО без siblingIndex

---

## 2. ВЕРИФИКАЦИЯ: ВЕРДИКТЫ (3 Соннета)

### Sonnet V1: Архитектурный аудит

**Вердикт: Approach B (score-based) -- ОСНОВНОЙ**

| Критерий | A (Nth-Label) | B (Score-based) | Победитель |
|----------|---------------|-----------------|------------|
| Семантическая точность | Низкая | Высокая | **B** |
| siblingIndex | НЕТ (нужен backend) | Не нужен | **B** |
| Код | Не написан | 216 строк ГОТОВО | **B** |
| Pinned/search override | Доп. логика | Встроено | **B** |
| Расширяемость | Сложно | Plug-in design | **B** |
| Performance | ~0ms | ~0.4ms (budget 2ms) | A (но несущественно) |
| UX предсказуемость | Странная | Логичная | **B** |

**Insertion point для labelScoring:** App.tsx строка 86 (после LOD calc, внутри frustum for loop).

### Sonnet V2: Data Flow аудит

**Все 6 маркеров ПОДТВЕРЖДЕНЫ:**
1. ✅ siblings НЕ передаются в FileCard
2. ✅ modified_time есть в backend, НЕ конвертируется
3. ✅ (частично) children через edges, НЕ через массив (в legacy формате есть)
4. ✅ indexInSiblings НЕ существует нигде
5. ✅ parentId есть в TreeNode
6. ✅ siblings можно находить через parentId (O(N))

**Рекомендация: siblings вычислять в App.tsx batch loop (useMemo), НЕ в FileCard.**
- App.tsx batch: O(N) predcompute + O(1) lookup
- FileCard: O(N×N) при каждом re-render -- НЕПРИЕМЛЕМО

### Sonnet V3: Risk + DevPanel аудит

**КРИТИЧЕСКИЕ РИСКИ:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| R1: Persistence Corruption | CRITICAL | DevPanel toggle ОБЯЗАТЕЛЕН перед Phase 113.4 |
| R2: State Churn Loop | HIGH | arraysEqual() guard + useShallow |
| R4: Dead Code (0 imports) | HIGH | Интегрировать с feature flag |

**DevPanel insertion points:**
- Строка 341: Section "Persistence Control" (Phase 113.1 toggle)
- Строка ~360: Section "Label Management" (Phase 113.4 toggle)
- Строка ~380: "Reset Saved Positions" button

**Feature flag: ОБЯЗАТЕЛЕН (ENABLE_LABEL_SCORING: boolean, default: false)**

**Rollback procedure:**
- Scenario A (FPS drop): DevPanel → disable flag
- Scenario B (corruption): Reset Positions button + hard refresh
- Scenario C (z-fighting): Tune jitterZ amplitude
- Scenario D (memory leak): git revert commit

---

## 3. ПЛАН ИМПЛЕМЕНТАЦИИ

### Порядок (safe-first):

1. **devConfig.ts** (+2 поля: ENABLE_PERSISTENT_POSITIONS, ENABLE_LABEL_SCORING)
2. **DevPanel.tsx** (+40 строк: 2 секции + Reset button)
3. **useStore.ts** (+4 строки: selectedLabelIds + setSelectedLabels)
4. **App.tsx** (+30 строк: scoring loop интеграция в FrustumCulledNodes)
5. **FileCard.tsx** (+5 строк: showLabel prop + guard + arePropsEqual)
6. **Тест:** disabled flag → enabled → zoom/pan/search → FPS check
7. **Коммит**

### Файлы и изменения:

| File | Action | Lines |
|------|--------|-------|
| `client/src/utils/devConfig.ts` | MODIFY | +6 (interface + defaults) |
| `client/src/components/panels/DevPanel.tsx` | MODIFY | +40 (2 sections + button) |
| `client/src/store/useStore.ts` | MODIFY | +4 (state + action) |
| `client/src/App.tsx` | MODIFY | +30 (scoring in frustum loop) |
| `client/src/components/canvas/FileCard.tsx` | MODIFY | +5 (showLabel prop) |
| `client/src/utils/labelScoring.ts` | EXISTS (216 lines) | 0 changes |

**Total:** ~85 новых строк, 0 новых файлов, 0 новых зависимостей.

---

## 4. ВОПРОСЫ ДЛЯ ГРОКА

1. Согласен с приоритетом B (score-based) над A (Nth-Label)?
2. Веса формулы: typeBoost*0.4 + depthScore*0.3 + sizeScore*0.2 + searchBoost*0.1 -- адекватны?
3. Adaptive top-N cap: max(5, min(30, floor(visibleCount*0.04 + zoomLevel*1.5))) -- правильный?
4. goldenAngleJitterZ: sin(rank * 2.39996) * (0.3 + rank/total * 0.5) -- оптимально?
5. Нужен ли modified_time в формуле? Сейчас его нет в apiConverter.

---

*Report compiled from 9 Haiku scouts + 3 Sonnet verifiers. Ready for Grok review, then implementation.*
