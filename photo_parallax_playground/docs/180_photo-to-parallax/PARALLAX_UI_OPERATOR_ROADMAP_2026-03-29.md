# PARALLAX UI Operator Roadmap

Дата фиксации: `2026-03-29`
Обновлено: `2026-03-29 14:35 MSK`
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
- Под монитором добавлен отдельный `camera key tray`, который резервирует нижнюю рабочую зону под future camera animation workspace.
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

### 3. Монитор визуально оформлен как карточка, а не как изображение

В `src/index.css` у `.stage-shell` сейчас `border-radius: 8px`.
У `.focus-frame` есть `border-radius: 28px`.

Viewer уже заметно ближе к прямоугольному экрану, чем в раннем состоянии, но визуальное ощущение card-shell ещё не убрано до конца.

### 4. Нижняя рабочая зона не работает как timeline/keyframe tray

Сейчас `workflow-dock` всё ещё занят четырьмя карточками:
- `Depth`
- `Isolate`
- `Camera`
- `Export`

Под монитором уже появился отдельный `camera key tray`, но это пока layout-reserve/readout, а не реальный keyframe editor.

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

- оставить cleanup hidden until needed
- показывать active tool only
- не держать `Focus Proxy`, `Matte`, `Hint Brushes`, `Merge Groups` как независимые большие панели

### UI-R11.4 Object/layer entry clarity

- сделать явный вход в object/layer mode
- визуально связать object selection со stage
- отделить object list от raw technical controls

### UI-R11.5 Camera keyframe tray

- статус: `выполнено как layout reserve`
- нижнее пространство теперь используется как `camera key tray`
- не внедрён весь CUT, но взят его пространственный принцип:
  - горизонтальная рабочая полоса
  - keyframe-ready future layout
  - clear room under monitor

### UI-R11.6 Viewport QA

- статус: `частично выполнено`
- wide QA пройдена на `hover-politsia`
- square QA пройдена на `drone-portrait`
- monitor остался главным элементом сцены
- в текущей `SAMPLE_LIBRARY` нет true portrait asset, поэтому отдельная portrait QA остаётся открытой

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
- внизу есть ясное пространство под future camera keys
- UI можно воспринимать как понятную оболочку, к которой остаётся прикручивать функции

## Следующий логичный UI-шаг

Следующий подтверждённый шаг из board и из текущего состояния:

- `PARALLAX-UIR12: fix portrait-safe stage fit and non-16:9 source framing`

Почему именно он:
- square уже проверен и выявлен как важный layout case
- true portrait asset ещё отсутствует, но сам fit/non-16:9 path остаётся открытым
- после `UIR11.5` следующий главный риск — чтобы monitor оставался доминирующим не только на wide, но и на non-16:9 sources
