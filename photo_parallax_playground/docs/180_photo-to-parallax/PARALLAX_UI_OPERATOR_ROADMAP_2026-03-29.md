# PARALLAX UI Operator Roadmap

Дата фиксации: `2026-03-29`
Обновлено: `2026-03-29 15:35 MSK`
Ветка: `main`
Workspace: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground`

## Источники фактов

- Handoff: `HANDOFF_TO_FRESH_CHAT_UI_2026-03-29.md`
- Playground UI: `src/App.tsx`
- Playground styles: `src/index.css`
- Product roadmap baseline: `docs/180_photo-to-parallax/PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md`
- Visual refs used in recon:
  - DaVinci Resolve depth-map inspector
  - Aiarty image matting workspace

## Что уже сделано

- Playground переведён в viewer-first layout.
- Основной монитор оставлен в центре.
- `Depth / Extract / Camera` перенесены в нижний рабочий dock.
- `Manual Cleanup` уже перестал быть одной длинной простынёй и начал работать как picker/helper path.
- `Export` уже переехал в правую рабочую зону, а не остаётся отдельным внешним блоком.
- `Export` переведён в compact accordion pattern и больше не висит полностью раскрытым по умолчанию.
- `Debug Snapshot` убран из default layout.

Подтверждение:
- `HANDOFF_TO_FRESH_CHAT_UI_2026-03-29.md`
- TaskBoard commits:
  - `9b4d3db5f` — `PARALLAX-UIR11.2`
  - `3cbcfe2c7` — `PARALLAX-UIR11.5`

## Подтверждённые проблемы текущего UI

### 1. Слишком много одновременно видимых инструментов

Сейчас в `src/App.tsx` левая колонка при `debugOpen` всё ещё может показывать:
- `Focus Proxy`
- `Guided Hints`
- `Stage Tools`
- `Algorithmic Matte`
- `Hint Brushes`
- `Merge Groups`
- `AI Assist`

Это подтверждает, что интерфейс остаётся model-centric, а не operator-centric.

### 2. Рабочие инструменты слабо привязаны к текущему контексту сцены

В коде stage-инструменты переключаются через `stageTool`, но сами панели настроек всё равно живут отдельно и разворачиваются как самостоятельные секции, а не появляются по действию внутри stage.

Ключевые состояния:
- `stageTool`
- `brushMode`
- `groupMode`
- `matteSeedMode`
- `guidedHintsVisible`
- `aiAssistVisible`

### 3. Реальное объектное редактирование пока ещё bbox-first

Теперь stage уже даёт прямой вход в object selection, но silhouette/depth-driven correction всё ещё открывается как следующий шаг после выбора объекта, а не как полноценный object-native editing model.

Подтверждено:
- stage object boxes теперь выбираются прямо на preview
- action `silhouette` открывает `Algorithmic Matte`
- но реальная object promotion и silhouette-first layer authoring ещё не доведены до backend authority

### 4. Нижняя рабочая зона пока не стала реальным timeline/keyframe workspace

Сейчас `workflow-dock` всё ещё занят четырьмя карточками:
- `Depth`
- `Isolate`
- `Camera`
- `Export`

После operator review fake tray был убран, потому что он не был ни CUT-derived, ни кликабельным. Реальный camera timeline/keyframe path остаётся отдельной будущей задачей.

### 5. Слишком много вторичных метрик и бейджей в главном viewer

Сейчас вокруг stage видимы:
- верхний `metric-strip`
- `stage-badges`
- `stage-footer`

Это добавляет служебный шум поверх главного viewer.

### 6. Object/layer editing не оформлен как ясный direct manipulation flow

По коду есть:
- `hint-editor-surface`
- pointer-обработчики для `brush`, `group`, `matte`
- overlay planes для hints, groups, matte, AI

Но пользовательский feedback указывает, что объектный выбор и кисть сейчас не читаются как понятное действие. Проблема подтверждается структурно: direct manipulation уже существует в коде, но интерфейс не даёт явного иерархического входа в этот режим.

## Целевой UI-принцип

Главный принцип следующей итерации:

- viewer first
- section headers first
- controls on demand
- tool appears only after entering the corresponding stage
- no decorative cards around the image
- no orphan controls without visible relation to image result

Референсное поведение:

- DaVinci: параметры depth/effects свернуты в headers и не висят все сразу
- Aiarty: инструмент появляется как активный рабочий режим поверх изображения, а не как постоянный список всех возможных настроек

## Рабочая модель экрана

### A. Viewer

Viewer должен оставаться главным прямоугольным экраном:
- без скруглённых углов
- без тяжёлой карточной подачи
- с минимальным служебным оверлеем

### B. Left Rail

Left rail должен отвечать только за:
- source / sample
- route / stage entry
- objects / layers list
- context actions

Из left rail нужно убрать постоянные “technical tool sheets”.

### C. Right / Bottom Operator Panels

Inspector-панели должны жить как сворачиваемые operator sections:
- `Depth`
- `Extract`
- `Camera`
- `Export`

Каждая секция:
- по умолчанию свернута
- показывает короткий summary
- разворачивается только по намерению

### D. Context Tools

Manual cleanup и layer refinement должны жить как contextual tools:
- активируются из конкретного действия
- не висят постоянно до начала реальной правки
- показывают только controls активного инструмента

## Фаза UI-R11. Operator Cleanup

### Цель

Сделать playground понятным операторским UI, где сначала ясен workflow, а уже потом появляются инструменты.

### UI-R11.1 Viewer de-cardification

- статус: `частично выполнено`
- основной viewer уже не выглядит как тяжёлая круглая карточка
- stage shell остаётся слегка смягчённым (`8px`), но не полностью neutral-screen
- служебный шум ещё можно сократить дальше

### UI-R11.2 Section-first inspector

- статус: `выполнено`
- `Export` приведён к collapsed pattern
- section summary rows стандартизированы
- always-open bulk controls убраны из default state

### UI-R11.3 Contextual cleanup tools

- статус: `выполнено`
- cleanup hidden until needed
- active tool показывается рядом с viewer
- rail больше не держит `Focus Proxy`, `Matte`, `Hint Brushes`, `Merge Groups` как постоянные большие панели

Подтверждение:
- commit `a40aecd34`
- task `tb_1774774661_74594_3`

### UI-R11.4 Object/layer entry clarity

- статус: `выполнено`
- visible plates показываются как stage object boxes прямо на preview
- stage box стал явной точкой входа в selection
- у выбранного объекта на сцене появляются прямые actions:
  - `inspect layer`
  - `silhouette`
- guide boxes больше не purely decorative
- object entry больше не спрятан за left-rail interpretation

Подтверждение:
- commit `3978f989e`
- task `tb_1774774662_74594_1`

### UI-R11.5 Camera keyframe tray

- статус: `отменено как fake placeholder`
- временный tray был убран после operator review
- следующий корректный шаг здесь: не рисовать reserve, а заводить реальный CUT-derived camera timeline/keyframe flow

Подтверждение:
- commit `8ceac771`
- task `tb_1774785732_69159_1`

### UI-R11.6 Viewport QA

- статус: `частично выполнено`
- wide QA пройдена на `hover-politsia`
- square QA пройдена на `drone-portrait`
- monitor остался главным элементом сцены
- в текущей `SAMPLE_LIBRARY` нет true portrait asset, поэтому отдельная portrait QA остаётся открытой

Дополнение:
- responsive non-16:9 fit path уже исправлен
- narrow override `width: 100% !important` убран из `.stage-shell`

Подтверждение:
- commit `4a7fcae4`
- task `tb_1774785131_69159_1`

## Dev Server Discipline

После повторяющихся runaway `vite` процессов зафиксировано новое правило рабочего цикла:

- использовать только `npm run dev:clean` для live checks
- использовать только `npm run dev:stop` для гарантированной остановки
- не плодить ручные порты `14347/14348/14349/14351`
- стандартный dev port для playground: `14350`

Подтверждение в коде:
- `package.json`
- `scripts/dev-server-stop.sh`

## Что не делать

- не добавлять новые декоративные панели
- не добавлять новые неочевидные режимы без прямой связи с изображением
- не возвращать card-heavy layout
- не смешивать debug/UI-polish и backend-feature work в одну задачу

## Критерии завершения ближайшего UI-прохода

- пользователь видит ясную route model: source -> depth/extract -> object cleanup -> camera -> export
- viewer прямоугольный и доминирующий
- `Export` и operator sections не висят полностью раскрытыми
- cleanup tools появляются только при соответствующем действии
- внизу не должно быть fake timeline UI без реальной функции
- UI можно воспринимать как понятную оболочку, к которой остаётся прикручивать функции

## Следующий логичный шаг

Следующий подтверждённый шаг уже не про layout-polish, а про object/backend flow:

- selectable object on stage -> promote into real layer
- silhouette/depth-driven correction should attach to the selected object, not to a generic rescue sheet
- candidate placement and draft plates should evolve from bbox-first drafting toward silhouette-first object handling

Почему именно он:
- UI shell уже достаточно расчищен
- stage selection уже появился
- главный remaining gap теперь между stage selection и реальным отдельным слоем
