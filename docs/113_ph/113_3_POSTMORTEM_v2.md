# Phase 113.3: Labels Championship — POSTMORTEM v2

**Date:** 2026-02-06
**Status:** ROLLED BACK (all 3 versions)
**Commander:** Claude Opus 4.6
**Result:** Код откачен до коммита `e5b7bf08` (Phase 113.1+113.2)

---

## Что было сделано (3 версии за сессию)

### v1: Scoring Engine + Top-N Selection
**Подход:** Отдельный scoring loop в useFrame (200ms), Map со скорами, selectTopLabels → Zustand store → FileCard prop showLabel.

**Файлы:**
- NEW `labelScoring.ts` (~120 строк, 6 функций)
- `lod.ts` (+1 строка: export smoothstep)
- `useStore.ts` (+8 строк: selectedLabelIds + setSelectedLabels)
- `App.tsx` (+38 строк: scoring loop, hysteresis, top-N, store update)
- `FileCard.tsx` (+17 строк: showLabel prop, hard filter, jitterZ)

**Что пошло не так:**
1. **Stale closure bug** — `selectedLabelIds` из React hook внутри useFrame callback = ВСЕГДА пустой массив. `arraysEqual(topLabels, [])` = false каждый цикл → `setSelectedLabels()` каждые 200ms → бесконечный цикл re-render → **тормоза**.
2. **Stale pinnedFileIds/highlightedIds** — те же closure проблемы, pinned файлы не бустились.
3. **Adaptive min=15** — слишком много label'ов на overview.
4. **Html DOM overhead** — каждый `<Html>` = реальный div. 30 div'ов с CSS transform каждый frame = CPU death.

### v2: Hotfix (useStore.getState() inside useFrame)
**Подход:** Заменил hook selectors на `useStore.getState()` внутри useFrame. Снизил adaptive min до 5.

**Что пошло не так:**
1. Stale closure починен, но **всё равно тормоза** — scoring loop + Map creation + sort каждые 200ms.
2. Labels всё равно показывались все/перекрывались — formulas давали всем папкам высокие scores.
3. Комп грелся — overhead от scoring + Html DOM.

### v3: Pure LOD-Based (убрал весь scoring)
**Подход:** Убрал scoring engine полностью. Label visibility = чистая функция от lodLevel + depth. Никаких Map, store updates, extra loops.

```
depth 0 (root): always → LOD ≥ 0
depth 1: LOD ≥ 2 (distance < 1500)
depth 2: LOD ≥ 4 (distance < 400)
depth 3+: LOD ≥ 6 (distance < 100)
```

**Что пошло не так:**
1. **Label'ы не появлялись кроме root** — пороги оказались слишком строгими для реального layout дерева.
2. LOD = f(distance, screen_position). На overview камера далеко → LOD 0-1 для depth-1 папок. Даже LOD ≥ 2 не достигается для большинства depth-1 папок.
3. Проблема в том что **LOD считается от РАССТОЯНИЯ камеры до конкретного узла**, а не от "zoom level" в целом. Узлы далеко от центра экрана получают низкий LOD (foveated spot) даже при близком зуме.
4. Фактически на любом реальном зуме depth-1 папки на краях экрана имели LOD 1-2, что = "скрыть label".

---

## Корневые причины неудачи

### 1. Html labels — архитектурно неправильный подход для 2000+ нод
`<Html>` из @react-three/drei = DOM элемент поверх canvas. Каждый Html:
- Создаёт div в реальном DOM
- Пересчитывает CSS transform каждый frame (project 3D→2D)
- Участвует в DOM layout (reflow/repaint)
- НЕ масштабируется: 30 Html = ок, 100 Html = тормоза

**Google Maps решает это иначе:** label'ы рендерятся в CANVAS (как текстуры), не как DOM элементы. Они ЧАСТЬ растрового изображения, не отдельные HTML элементы.

### 2. Scoring loop в useFrame — ненужная сложность
Добавление второго прохода по всем нодам каждые 200ms (для scoring) ПОВЕРХ существующего frustum+LOD прохода — удвоение работы. Map creation, sort, hysteresis — всё это allocation pressure на GC.

### 3. Zustand + useFrame = несовместимы
React hooks (useStore selectors) создают closure. useFrame callback захватывает эти closure variables при mount. Когда store обновляется, useFrame callback НЕ видит новые значения. Это фундаментальная несовместимость React и imperative animation loop.

Решение `useStore.getState()` работает, но создаёт другую проблему — store updates из useFrame вызывают React re-render, который re-creates useFrame callback, который снова вызывает store update...

### 4. LOD != Importance
LOD (Level of Detail) = расстояние + позиция на экране. Это про РЕНДЕРИНГ (сколько деталей рисовать).
Importance = семантическая важность (тип, глубина, размер, активность). Это про ИНФОРМАЦИЮ (что показывать).

Привязать label visibility к LOD — ошибка, потому что:
- Папка может быть далеко (LOD 1) но ВАЖНА (root depth-1)
- Папка может быть близко (LOD 8) но НЕВАЖНА (пустая depth-5)

---

## Что стоит делать (рекомендации для следующей попытки)

### Подход 1: Canvas-baked label'ы (рекомендуемый)
Вместо Html label'ов — рисовать текст прямо на текстуре карточки (canvas). Это уже работает для файлов (имена видны на карточках). Нужно расширить на папки:
- Папки уже имеют серую текстуру
- Добавить имя папки на эту текстуру (ctx.fillText)
- Размер шрифта зависит от LOD
- **Ноль DOM overhead** — всё в canvas/WebGL

### Подход 2: Troika 3D Text
`troika-three-text` — рендерит текст как 3D geometry (SDF shaders). Масштабируется до тысяч label'ов. Нет DOM. Но новая зависимость.

### Подход 3: Простая формула без engine
Если оставить Html label'ы — максимально простая формула БЕЗ scoring engine:
```
Показывать label если:
  depth === 0 (root — всегда)
  ИЛИ (depth <= 2 И children.length > 10 И distToCamera < 500)
  ИЛИ (isPinned)
```
Никаких Map, scoring loop, store updates, hysteresis. Просто if/else внутри FileCard IIFE.

### Подход 4: MGC/CAM интеграция
Использовать существующие системы VETKA:
- **MGC** (Multi-Generation Cache): уже считает "hot" ноды
- **CAM** (Context-Aware Memory): знает какие файлы активны
- Вместо своего scoring — запросить у CAM: "какие 20 нод сейчас самые важные?"
- Обновлять раз в 2-5 секунд (не каждые 200ms)

### Подход 5: Гибрид — текстура + hover Html
- Имена на текстурах (canvas-baked) — видны всегда, масштабируются с LOD
- При hover — показать Html tooltip с деталями
- Hover = 1 Html element = ноль overhead

---

## Файлы созданные за сессию (сохранены для истории)

| Файл | Статус | Содержание |
|------|--------|------------|
| `docs/113_ph/113_3_IMPLEMENTATION_PLAN.md` | Сохранён | Детальный план v1 |
| `docs/113_ph/113_3_RAILROAD_MAP.md` | Сохранён | Маркера для имплементации |
| `docs/113_ph/113_3_POSTMORTEM_v2.md` | Сохранён | Этот документ |
| `client/src/utils/labelScoring.ts` | **НЕ удалён** | Scoring engine (не используется) |

### labelScoring.ts — решение
Файл `labelScoring.ts` остался на диске но НЕ импортируется нигде. Он содержит рабочие функции (computeLabelScore, selectTopLabels, goldenAngleJitterZ, applyHysteresis). Можно удалить или оставить для будущего использования.

---

## Уроки

1. **Простота > сложность.** Scoring engine с 6 функциями, hysteresis, golden angle — overcomplicated. Начинать надо с 3 строк if/else.

2. **Canvas > DOM.** Html labels не масштабируются. Для 2000+ нод нужен canvas-baked или SDF text.

3. **useFrame и React state — масло и вода.** Не класть React state updates в useFrame. Либо всё в refs, либо всё в React.

4. **Тестировать на РЕАЛЬНЫХ данных.** Скриншоты от пользователя показали то, что код-ревью не показал. Агенты-анализаторы скриншотов говорили "работает" когда это было неправда.

5. **Recon правильный, имплементация неправильная.** 9 Haiku + 3 Sonnet дали точные маркера. Проблема не в разведке, а в архитектурном решении (Html + scoring loop + Zustand).

---

## Состояние после отката

- Код: `e5b7bf08` (Phase 113.1+113.2)
- Build: SUCCESS
- Label'ы: оригинальное поведение (все folder labels через Html + distance threshold)
- Производительность: восстановлена
- Файл `labelScoring.ts` на диске (не импортируется)

---

**NEXT:** Phase 113.3 attempt 3 — canvas-baked labels или Troika 3D Text. Без Html, без scoring engine, без Zustand в useFrame.
