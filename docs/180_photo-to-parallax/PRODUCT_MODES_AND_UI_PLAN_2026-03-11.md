# Product Modes And UI Plan

Дата: `2026-03-11`

## 1. Почему меняем план

После просмотра первых preview подтверждено:

- авто-depth split часто режет сцену по локальным depth-градиентам, а не по смысловым объектам;
- `3-layer` улучшает часть кейсов, но без ручного контроля всё ещё ошибается в object grouping;
- проблема не только в количестве слоёв, а в том, как сцена группируется в foreground / midground / background.

Поэтому следующий roadmap должен идти не по линии "ещё одна модель depth", а по линии трёх пользовательских режимов:

- `Auto Base`
- `Manual Pro`
- `AI Assist`

## 2. Product Modes

## 2.1 Auto Base

Цель:

- быстрый one-click baseline;
- хороший default для простых сцен;
- предсказуемый deterministic output.

Состав:

- `depth`
- `conditional SAM 2`
- `subject_rgba`
- `clean_plate`
- `overscan`
- routing:
  - `two_layer`
  - `safe_two_layer`
  - `three_layer`

Ограничение:

- Auto Base не должен пытаться "понимать сцену" глубже, чем это можно сделать устойчиво.

## 2.2 Manual Pro

Цель:

- дать пользователю контроль там, где автомат ошибается;
- исправлять object grouping, а не только mask edges.

Главная идея:

- пользователь правит не "маску вообще", а смысловые отношения:
  - это ближе
  - это дальше
  - это держать вместе
  - это не делить
  - это защитить

Manual Pro должен стать основным quality path для сложных кадров.

## 2.3 AI Assist

Цель:

- давать умные предложения поверх Manual Pro;
- помогать группировать объекты semantically;
- не ломать deterministic base path.

Правильная роль:

- `Qwen2.5-VL` или другой VLM как semantic judge / grouping suggester;
- generation of region hints / layer suggestions / JSON reasoning;
- compare gate against base result.

Неправильная роль:

- не выпускать final mask без compare gate;
- не объявлять VLM depth backend;
- не подменять собой ручную правку.

## 3. Что делать с V-JEPA

На текущем этапе `V-JEPA` не нужен для программно заданного motion.

Причина:

- motion у нас deterministic и задаётся явно;
- `V-JEPA` не делает object boundary segmentation как нужный нам core capability;
- для single-image grouping он не даёт очевидного первого выигрыша по сравнению с:
  - `SAM 2`
  - `manual hints`
  - `Qwen2.5-VL`

Значит текущее решение:

- не ставить `V-JEPA` в ближайший roadmap;
- оставить его только как future R&D для sequence/video understanding, если появится настоящий multi-frame mode.

## 4. Первые UI Controls

Порядок важен. Сначала нужны контролы, которые реально исправляют текущие ошибки.

### Wave 1. Depth and Preview

- `B/W Depth Preview`
- `Near`
- `Far`
- `Gamma`
- `Auto Contrast`
- `Invert Depth`

Это нужно для ручной отстройки depth remap.

### Wave 2. Layer Selection

- `Target Depth`
- `Range`
- `Foreground Bias`
- `Background Bias`
- `Merge Nearby Regions`

Это нужно, чтобы не резать один объект на случайные половины.

### Wave 3. Manual Hints

- `Closer Brush`
- `Farther Brush`
- `Protect Brush`
- `Same Layer / Merge Group`
- `Erase Hint`

Это уже ядро `Manual Pro`.

### Wave 3.5. Algorithmic Matte

- `Click Seed`
- `Grow / Shrink Matte`
- `Edge Snap`
- `Protect Edge`
- `Depth Matte View`
- `RGB Matte View`
- `Transparent Mask Overlay`

Это отдельный режим, ближе к roto / quick mask в Photoshop и After Effects: пользователь или агент кликает по области, а система алгоритмически выращивает matte по краям и показывает её в двух представлениях.

### Wave 4. Cleanup

- `Softness`
- `Expand / Shrink`
- `Filter`
- `Alpha Refine`
- `Edge Feather`

Это нужно против жёстких границ и compositing artifacts.

### Wave 5. Motion

- `Mode`
  - `2-layer`
  - `safe 2-layer`
  - `3-layer`
- `Motion Type`
- `Speed`
- `Duration`
- `Amplitude`

### Wave 6. AI Assist

- `Suggest Layer Groups`
- `Interpret Hints`
- `Semantic Check`
- `Accept Suggestion`
- `Compare With Base`

## 5. Roadmap Order

### Step 1. Manual Pro foundation

- depth B/W preview in UI;
- layer routing visible in UI;
- manual hint editor:
  - closer
  - farther
  - protect

### Step 2. Grouping controls

- `merge same layer`
- region-level grouping instead of pure pixel split;
- keep-object-together heuristics.

### Step 3. Compare workflow

- compare `auto / manual / ai assist`;
- compare `manual / ai / blend`;
- save chosen mode and chosen layer grouping.

### Step 4. AI Assist

- prototype `Qwen2.5-VL` as grouping suggester;
- JSON output only;
- suggestions must be accept/reject, not auto-apply.

### Step 5. Policy

- canonical product policy:
  - when to stay in `Auto Base`
  - when to escalate to `Manual Pro`
  - when to offer `AI Assist`

## 6. Immediate next implementation step

Следующий правильный шаг:

- не трогать `V-JEPA`;
- не тюнить ещё один auto-depth backend;
- сделать в sandbox первый `Manual Pro UI`:
  - `B/W Depth Preview`
  - `Target Depth`
  - `Range`
  - `Closer/Farther/Protect` hint tools
  - mode switch: `auto / safe / 3-layer`

Это даст самый быстрый рост качества на реальных кадрах.
