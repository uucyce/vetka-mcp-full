# Parallax Product UI Reset Project

Дата фиксации: `2026-03-29`
Статус: `canonical product pivot after operator review`

## 1. Purpose

Этот документ фиксирует новый продуктовый разворот для `photo_parallax_playground` после прямого operator review по живому UI.

Его задача:

- перевести playground от research-prototype surface к product-readable surface;
- зафиксировать, что главный критерий теперь не "сколько controls доступно", а "понимает ли их человек, который умеет работать в pro apps";
- дать новый execution plan для следующих UI волн.

Этот документ не заменяет:

- `PARALLAX_ROADMAP_RC1_COMPLETION_AND_LAYERED_BAKEOFF_2026-03-19.md`
- `PARALLAX_OBJECT_CENTRIC_PARALLAX_ARCHITECTURE_2026-03-28.md`
- `PARALLAX_PLAYGROUND_UI_REFACTOR_PROJECT_2026-03-28.md`
- `PARALLAX_PLAYGROUND_CONTROL_RECON_2026-03-29.md`

Он добавляет поверх них product-level correction.

## 2. Factual Trigger

На `2026-03-29` оператор дал детальный review по live screen и референсам близких программ.

Подтверждённые замечания:

- `Import` должен быть простым списком source files, ближе к `Project / Media Pool`, а не карточечной витриной как primary interaction.
- `Depth` должен мыслиться по модели `DaVinci Resolve AI Depth Map`.
- нижний `Inspector` в текущем виде воспринимается как лишняя панель, если в нём нельзя напрямую делать понятные object edits.
- `Scene Plan` должен быть коротким readable list/checklist, а не тяжёлой многослойной панелью.
- `Advanced Cleanup` в текущем виде непонятен оператору.
- `Extract` сейчас не даёт понятного результата на языке человека.
- `Camera` не даёт ожидаемых pro controls:
  - нет понятного camera language
  - нет focal-length thinking
  - нет obvious keyframe/move model
- `Guided Hints`, `Hint Brushes`, `Layer Guides`, `AI Assist`, `Debug Snapshot` воспринимаются как prototype noise.
- многие menus/blocks не сворачиваются и создают wall-of-controls.
- все изображения тянутся в `16:9`, даже когда source был portrait, и это продуктово ломает просмотр.

Это не вкусовой комментарий.

Это фактический сигнал, что current UI still speaks internal prototype language instead of professional operator language.

## 3. New Product Principle

Главный принцип следующего этапа:

- playground должен стать понятным человеку, который знает `After Effects`, `Cinema 4D`, `Premiere`, `DaVinci Resolve`, `Ableton`, even if that человек не знает внутренние VETKA contracts.

Из этого следует:

- internal naming не может быть главным языком интерфейса;
- `human in the loop` означает не просто наличие ручных controls, а то, что оператор понимает:
  - что делает control
  - где он находится
  - когда его трогать
  - к чему он относится

## 4. Reference Mental Models

Новый UI direction должен брать mental models из трёх типов software.

### 4.1 Import = CUT / Media Pool style

Для `Import` правильный референс:

- простой список файлов / shots / assets;
- secondary metadata рядом;
- без тяжёлого emphasis на sample cards как основной surface.

### 4.2 Depth = Resolve AI Depth Map style

Для `Depth` правильный референс:

- B/W preview как primary truth surface;
- near/far/gamma как first-line controls;
- isolate specific depth как отдельная collapsible group;
- advanced/finesse как folded sections, а не всё сразу.

### 4.3 Cleanup / Matting = focused image-matting tools

Для isolate/refine behavior правильный референс:

- правый tool stack с collapsible sections;
- `Edit`
- `Area Select`
- `Refinement`
- concise model selection
- minimal visible controls until section is opened.

Дополнительная backend note для будущего cleanup lane:

- cleanup stack должен оставаться backend-pluggable;
- на текущем этапе это не выбор стека, а only design constraint;
- когда дойдём до comparative recon, стоит оставить место для candidate backends вроде:
  - `SAM 2 + PyMatting`
  - `BiRefNet`
  - `RMBG`
- эти варианты пока считаются только кандидатами для будущего bakeoff, не принятой архитектурой.

## 5. What Must Change

Из operator review прямо следует следующий change list.

### 5.1 Collapse Prototype Noise

С первого экрана должны исчезнуть как always-open blocks:

- `Guided Hints`
- `Stage Tools`
- `Hint Brushes`
- `Layer Guides`
- `AI Assist`
- `Debug Snapshot`

Они могут существовать только как:

- folded tools
- advanced side stack
- or hidden debug

### 5.2 Depth Must Become The Clearest Block

`Depth` должен быть одним из самых понятных блоков в продукте.

На первом слое там должны быть только:

- preview toggle / depth preview
- `Near`
- `Far`
- `Gamma`
- maybe `Invert`

Второй слой:

- isolate specific depth
- finesse / softness
- advanced

### 5.3 Scene Plan Must Shrink

`Scene Plan` должен перестать быть pseudo-dashboard.

Правильная форма:

- concise route summary
- concise risk summary
- short checklist / next action

Неправильная форма:

- dense control surface
- wall of summaries
- duplication of Inspector state

### 5.4 Inspector Must Earn Its Screen Space

`Inspector` не может оставаться отдельной тяжёлой нижней панелью только ради чтения.

Он должен стать одним из двух:

1. compact object strip with direct edits
2. folded object manager / object list

Если ни того, ни другого не получается, его экранный вес должен быть сильно уменьшен.

### 5.5 Portrait Assets Must Fit Correctly

Viewport должен уважать source aspect ratio.

Текущий `16:9`-first behavior для portrait assets продуктово неприемлем.

Правильный direction:

- fit entire source first
- then apply parallax framing inside a respectful stage
- not crop away the shot by default

## 6. New Invariants

После этого reset нельзя терять следующие продуктовые инварианты:

- `Import` must feel like source selection, not a marketing gallery
- `Depth` must feel like a real depth tool
- `Scene Plan` must feel like a short plan, not a wall
- `Inspector` must either edit or get smaller
- all secondary tool groups must be collapsible
- portrait sources must be fully visible by default
- debug must not occupy default operator attention

## 7. New Ordered Execution

Следующие UI волны теперь должны идти в таком порядке:

1. `UIR7 Product Reset Shell`
   - убрать remaining proto-noise from default screen
   - demote debug and advanced stacks harder

2. `UIR8 Resolve-Like Depth`
   - rebuild `Depth` around Resolve mental model
   - collapsed sections for isolate/finesse/advanced

3. `UIR9 Import Simplification`
   - replace sample-card emphasis with source list / source browser behavior

4. `UIR10 Inspector Demotion Or Conversion`
   - either compact editable object strip
   - or folded object manager

5. `UIR11 Scene Plan Reduction`
   - convert to short route/risk/next-action list

6. `UIR12 Portrait-Safe Stage`
   - fix fit behavior for non-16:9 sources

7. `UIR13 Cleanup Tool Stack`
   - collapse and regroup `Advanced Cleanup`
   - matting-style hierarchy
   - сохранить место для будущего backend switcher / model selector without committing to one stack now

## 8. Immediate Tasks To Create

Из этого документа напрямую следуют следующие tasks:

1. `PARALLAX-UIR7`
   - remove default-screen prototype noise

2. `PARALLAX-UIR8`
   - rebuild Depth card from Resolve reference

3. `PARALLAX-UIR9`
   - simplify Import into source-list mental model

4. `PARALLAX-UIR10`
   - reduce or convert Inspector

5. `PARALLAX-UIR11`
   - shrink Scene Plan into concise list

6. `PARALLAX-UIR12`
   - fix portrait/stage fit behavior

7. `PARALLAX-UIR13`
   - rebuild Advanced Cleanup as collapsible tool stack
   - keep cleanup stack ready for future comparative matting backends

## 9. Relationship To Existing Architecture

Этот product reset не отменяет object-centric architecture.

Наоборот:

- `scene routing + object-centric cleanup + lightweight human steering` остаются верными;
- меняется не архитектурный смысл, а operator-facing shape;
- UI должен перестать выглядеть как internal lab around a correct architecture.

## 10. Practical Reading

Коротко:

- архитектура идёт в правильную сторону;
- UI language and information hierarchy пока нет;
- следующий этап должен чинить именно это;
- успех следующего этапа измеряется не количеством controls, а тем, чувствуется ли экран как инструмент уровня familiar pro apps.
