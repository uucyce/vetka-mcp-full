# Handoff To Fresh Chat: Parallax UI / Stage Objects

Дата фиксации: `2026-03-29`
Обновлено: `2026-03-29 15:35 MSK`
Workspace: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground`
Branch: `main`
HEAD: `3978f989ec0bfaf4ecba45303df70e06abf7d474`

## Что уже в main

Текущее состояние уже не в worktree и не в merge-ветке. Всё ниже уже находится в `main`.

Ключевые UI-коммиты:
- `8ceac771` — убран fake camera tray placeholder
- `4a7fcae4` — исправлен portrait-safe / non-16:9 fit
- `a40aecd34` — `Manual Cleanup` переведён в contextual tool activation
- `3978f989e` — object/layer entry перенесён на stage

Связанные TaskBoard-задачи:
- `tb_1774785732_69159_1` -> `done_main`
- `tb_1774785131_69159_1` -> `done_main`
- `tb_1774774661_74594_3` -> `done_main`
- `tb_1774774662_74594_1` -> `done_main`

## Что именно сделано по UI

### 1. Viewer-first shell

- fake timeline/camera tray удалён
- монитор больше не имеет скруглённых углов
- `Depth / Extract / Camera` остаются compact operator sections
- `Export` живёт в правой рабочей зоне и не висит полностью раскрытым

### 2. Manual Cleanup

- cleanup hidden until needed
- left rail теперь только активирует rescue tool
- активный rescue tool открывается как contextual panel рядом с viewer
- `silhouette` path открывает `Algorithmic Matte`

### 3. Object selection moved onto stage

Сейчас на `hover-politsia` и аналогичных samples visible plates рисуются как интерактивные frame overlays прямо на preview.

Что уже работает:
- stage object boxes видимы в обычном `composite` preview
- box можно выбрать прямо на сцене
- у выбранного объекта появляются stage actions:
  - `inspect layer`
  - `silhouette`
- guide boxes больше не purely decorative entry

Это было подтверждено live через Playwright:
- object boxes существуют в DOM на stage
- selection state меняется
- `silhouette` открывает contextual matte panel

## Что ещё не завершено

Главный незакрытый gap уже не про layout, а про object authority.

Сейчас всё ещё не доведено до конца:
- выбрать кошку/объект на сцене и промоутить в реальный отдельный слой как прямое действие
- уйти от bbox-first semantics к silhouette/depth-first object editing
- связать candidate placement / draft plates с настоящим object-to-layer pipeline
- сделать human-in-the-loop path вида:
  - click object
  - mark as object/layer
  - run silhouette/depth cleanup for this object
  - commit/export as real plate

## Что проверено

### Build

- `npm run build` passed после последнего stage-object patch

### Live QA

Использовался только disciplined server flow:
- `npm run dev:clean`
- `npm run dev:stop`

Проверено:
- `http://127.0.0.1:14350/?sample=hover-politsia&debug=1&fresh=uir114-stage*`

Факты live QA:
- stage object boxes видны в normal preview
- `stage-shell` имеет `border-radius: 0px`
- object selection и `silhouette` path отрабатывают

Примечание:
- Playwright обычным locator click местами капризничал из-за overlay stacking, но DOM-triggered click подтвердил, что UI logic работает
- после этого pointer stack был дополнительно упрощён через `pointer-events: none` у badge

## Где смотреть в коде

Файлы:
- [src/App.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx)
- [src/index.css](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/index.css)
- [PARALLAX_UI_OPERATOR_ROADMAP_2026-03-29.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/docs/180_photo-to-parallax/PARALLAX_UI_OPERATOR_ROADMAP_2026-03-29.md)

Ключевые зоны в `App.tsx`:
- stage object selection helpers
- stage rendering block around object overlays
- cleanup contextual panel rendering

Ключевые зоны в `index.css`:
- `.stage-shell`
- `.stage-object-plane`
- `.stage-object-box`
- `.stage-object-hit`
- `.stage-object-actions`
- `.group-guide-box`

## Технический контекст merge/infra

- Последний рабочий commit уже push’нут в `origin/main`
- `vetka_git_commit` и TaskBoard auto-commit по-прежнему иногда ломаются на digest-wrapper, а не на самих UI-изменениях
- для последнего шага использовался scoped fallback:
  - `git add src/App.tsx src/index.css`
  - `git commit ... [task:tb_1774774662_74594_1]`
  - push в `main`
  - затем task закрыт вручную через TaskBoard по `commit_hash`

Это важно помнить, чтобы новый чат не тратил время на ложный поиск “ошибки UI”, когда реально падает infra-обвязка commit flow.

## Следующий лучший шаг

Если продолжать из нового чата, самый рациональный следующий шаг:

`object -> layer authority`

То есть:
- не возвращаться к микрополировке layout
- не рисовать fake camera/timeline reserve
- не раздувать left rail снова
- идти в backend-assisted object flow:
  - выбрать объект прямо на сцене
  - промоутить его в отдельный слой
  - использовать silhouette/depth cleanup для конкретного выбранного объекта
  - уменьшить зависимость от draft bbox semantics

## Что не надо делать

- не возвращать fake camera tray
- не возвращать rounded-card monitor
- не прятать object selection обратно в left rail
- не делать cleanup снова длинной технической простынёй
- не смешивать следующий object/backend шаг с новой декоративной UI-полировкой
