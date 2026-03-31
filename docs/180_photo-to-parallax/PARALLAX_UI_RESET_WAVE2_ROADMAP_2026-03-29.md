# Parallax UI Reset Wave 2 Roadmap

Дата фиксации: `2026-03-29`
Статус: `operator-driven UI formalization after live review`

## 1. Purpose

Этот документ фиксирует только следующий UI-срез для `photo_parallax_playground` после:

- live operator review;
- handoff `HANDOFF_TO_FRESH_CHAT_UI_2026-03-29.md`;
- уже существующих `PARALLAX-UIR*` / `viewer-first` задач в TaskBoard;
- прямых визуальных референсов `DaVinci Resolve AI Depth Map` и `Airty Image Matting`.

Документ не расширяет scope backend/rendering.

Его задача уже более узкая:

- превратить последние замечания оператора в явный plan;
- разделить `already formalized`, `already implemented`, `still implicit`;
- задать следующие UI tasks без возврата к prototype noise.

## 2. Confirmed Inputs

### 2.1 Operator review, зафиксированный по факту

Подтверждено из текущего review и переданных референсов:

- секции должны читаться как заголовки, которые раскрываются по необходимости;
- инструменты cleanup/edit не должны висеть в полном составе до того, как оператор реально вошёл в соответствующий сценарий;
- monitor должен быть прямоугольным, без скругления кадра;
- слева сейчас слишком много controls, чей смысл неочевиден по отношению к картинке;
- object selection / brush path в текущем состоянии не даёт ясного ощущаемого workflow;
- цветные slider-heavy панели и крупные заголовки создают overload;
- нижняя зона экрана должна оставаться пригодной для будущей camera animation / keyframes, а не съедаться случайным layout gap.

### 2.2 Handoff, уже зафиксированный в worktree

Подтверждено в [HANDOFF_TO_FRESH_CHAT_UI_2026-03-29.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/photo_parallax_playground/HANDOFF_TO_FRESH_CHAT_UI_2026-03-29.md):

- workspace для актуального UI состояния:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/photo_parallax_playground`
  - branch `codex/parallax`
- `npm run build` passed;
- последние live checks делались через Playwright;
- уже выполнены:
  - compact right inspector behavior;
  - collapse-first pattern для `Depth / Extract / Camera`;
  - cleanup left rail;
  - первый pass по `Manual Cleanup` как tool picker;
- явно остались:
  - ещё один pass по `Manual Cleanup`;
  - compact accordion behavior для `Export`;
  - explicit portrait / square QA.

### 2.3 Already formalized TaskBoard tasks

Подтверждено в TaskBoard проекта `parallax`:

- `tb_1774699890_86927_1` — `Rebuild viewer-first playground baseline in App.tsx` — `done_worktree`
- `tb_1774701645_86927_1` — `Restore inspector and routing-assist layer in viewer-first UI` — `done_worktree`
- `tb_1774702138_86927_1` — `Polish depth mode into DaVinci-like B/W control surface` — `done_worktree`
- `tb_1774757118_86927_1` — `Let operator click missing objects into provisional candidates` — `done_worktree`
- `tb_1774765027_86927_1` — `Simplify viewer-first main path by compressing secondary controls` — `done_worktree`
- `tb_1774765213_86927_1` — `Reduce density in Inspector and Routing & Assist main operator layer` — `done_worktree`
- `tb_1774765701_86927_1` — `Make viewer-first labels more operator-readable and visibly different` — `done_worktree`
- `tb_1774767488_86927_1` — `PARALLAX-UIR7: remove default-screen prototype noise from viewer-first shell` — `done_worktree`
- `tb_1774767488_86927_4` — `PARALLAX-UIR10: demote or convert Inspector into lighter object manager` — `claimed`
- `tb_1774767508_86927_3` — `PARALLAX-UIR13: rebuild Advanced Cleanup as collapsible tool stack` — `pending`
- `tb_1774771182_33652_1` — `PARALLAX-UX: clarify camera move model and remove oversized camera header pills` — `pending`

## 3. What Is Still Not Fully Formalized

Следующие требования уже подтверждены review/handoff, но пока не выглядят закрытыми отдельным завершённым execution wave:

### 3.1 Monitor surface discipline

Требование:

- monitor должен быть frame-first, без rounded-image ощущения;
- portrait / square material не должен продуктово деградировать из-за layout assumptions.

Почему это ещё не закрыто:

- handoff прямо оставляет `portrait / square QA` как отдельный следующий шаг;
- в текущем playground layout stage still uses decorative shell behavior, а не strict monitor framing as canonical product rule.

### 3.2 Cleanup should become contextual, not parked

Требование:

- cleanup tools должны появляться своевременно;
- до реальной корректировки слоя не должно быть постоянной простыни rescue controls;
- cleanup должен читаться ближе к `Airty` tool logic, чем к debug toolbox.

Почему это ещё не закрыто:

- handoff сам фиксирует, что `Manual Cleanup still needs one more Resolve/Airy pass`;
- `tb_1774767508_86927_3` пока `pending`.

### 3.3 Export must behave like the same compact inspector language

Требование:

- `Export` не должен быть единственной always-open bulky section;
- actions должны оставаться видимыми, но summary/readout должен быть folded-first.

Почему это ещё не закрыто:

- handoff прямо выносит это в `Remaining Gaps`;
- отдельного `done` task по compact export behavior не видно в текущем UI slice.

### 3.4 Camera lane needs explicit pre-keyframe product framing

Требование:

- пока нет полноценной keyframe animation, UI должен честно говорить, что сейчас доступен safe move model;
- нижняя зона должна быть защищена как future camera timeline strip, а не случайно исчезать из layout;
- reuse mental model from CUT should be planned, not silently improvised.

Почему это ещё не закрыто:

- `tb_1774771182_33652_1` пока `pending`;
- в operator review явно поднят вопрос про keyframes и потерю нижнего пространства.

### 3.5 Object interaction path remains under-explained

Требование:

- оператор должен понимать, как выбрать объект, как его поправить, и почему те или иные controls относятся именно к нему;
- brush/object interaction должна ощущаться как controllable tool path, не как hidden debug surface.

Почему это ещё не закрыто:

- несмотря на `tb_1774757118_86927_1` (`done_worktree`), review всё ещё указывает, что object selection / brush path ощущается нерабочим или неясным;
- значит, execution был, но product comprehension issue remains.

## 4. Wave 2 Product Rules

Следующая волна должна подчиняться этим правилам:

1. Main path only:
   - `Import`
   - `Monitor`
   - `Effects Inspector`
   - `Object / Layer Manager`
   - `Export`

2. Fold-first:
   - любая secondary группа должна начинаться как collapsed summary;
   - full slider sheet показывается только по явному раскрытию.

3. Context before control:
   - cleanup/edit tools появляются после выбора объекта, режима или проблемы;
   - не допускается permanent wall of unrelated tools.

4. Honest camera language:
   - пока нет editable keyframes, UI не должен притворяться, что они уже есть;
   - но layout должен резервировать будущую нижнюю зону под animation strip.

5. No unexplained controls:
   - каждый control в main path должен иметь операторски читаемую связь с изображением или активным объектом.

## 5. Ordered Execution Slice

### Wave 2A. Monitor and shell discipline

Цель:

- убрать ощущение prototype frame;
- зафиксировать строгий прямоугольный monitor;
- проверить portrait / square without inspector displacement.

Deliverables:

- rectangular monitor surface;
- portrait / square QA checklist;
- stage shell no longer visually competes with image.

### Wave 2B. Finish compact inspector language

Цель:

- довести `Depth / Extract / Camera / Export` до одной accordion grammar;
- сохранить summary-first reading.

Deliverables:

- `Export` folded-first;
- consistent compact headers;
- no giant pills / placeholder-looking header actions.

### Wave 2C. Turn cleanup into contextual tool lane

Цель:

- превратить `Manual Cleanup` из parked rail section в event-driven lane;
- показывать edit/refine tools только в соответствующем сценарии.

Deliverables:

- no default full cleanup sheet;
- contextual open behavior by stage action / recommendation;
- Airty-like grouped tool stack.

### Wave 2D. Clarify object interaction

Цель:

- сделать selection / brush / object fix path продуктово понятным;
- объяснить связь tool -> object -> result.

Deliverables:

- clear selected-object state;
- visible object edit affordance;
- no hidden dependence on debug mental model.

### Wave 2E. Reserve bottom lane for future camera animation

Цель:

- не внедряя пока полноценный animation editor, вернуть нижней зоне product meaning;
- подготовить reuse path from CUT keyframe/timeline mental model.

Deliverables:

- bottom strip reserved in layout;
- explicit placeholder language for future camera keys;
- no accidental layout collapse.

## 6. Task Mapping For This Wave

### Already existing tasks that should be treated as active dependencies

- `tb_1774767488_86927_4` — lighter object manager
- `tb_1774767508_86927_3` — collapsible cleanup stack
- `tb_1774771182_33652_1` — camera move model clarification

### New tasks still needed after this roadmap formalization

- monitor shell / rectangular frame / portrait-square QA
- compact export accordion pass
- contextual cleanup reveal triggers
- bottom camera strip reservation
- object interaction comprehension pass

## 7. Scope Guard

В эту волну не входят:

- новые backend cleanup models;
- новые export formats;
- real animation/keyframe engine implementation;
- новые decorative panels;
- расширение debug surface.

Правильный результат этой волны:

- понятный product-readable UI;
- меньше always-visible controls;
- monitor remains primary;
- future function wiring can be attached onto a stable surface instead of another prototype layout.
