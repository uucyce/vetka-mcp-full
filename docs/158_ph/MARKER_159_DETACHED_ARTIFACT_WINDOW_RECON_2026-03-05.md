# MARKER_159_DETACHED_ARTIFACT_WINDOW_RECON_2026-03-05

Date: 2026-03-05  
Scope: Recon only (no feature changes) for detached Artifact Media Window behavior in Phase 159.

## Goal of Recon
Проверить цепочку `artifact UI -> frontend invoke -> tauri command -> new window` и ответить:
1. Был ли реально сделан detached Tauri window для media artifact.
2. Почему в пользовательском UX окно все еще ведет себя как встроенное.
3. Где именно разрыв: не реализовано / не подключено / runtime mismatch.

---

## MARKER_159.RECON.1 — Текущее окно артефакта по умолчанию встроено (embedded)
Evidence:
- `App` всегда рендерит `ArtifactWindow` внутри основного React-дерева: `client/src/App.tsx:882-894`.
- `ArtifactWindow` рендерится через `FloatingWindow` (`react-rnd`) и физически живет внутри main webview: `client/src/components/artifact/FloatingWindow.tsx:55-76`.

Conclusion:
- Базовый режим действительно embedded. Если двигать/минимизировать основное окно, embedded artifact исчезает вместе с ним. Это ожидаемое поведение для текущего default-path.

---

## MARKER_159.RECON.2 — Detached Tauri window код действительно реализован
Evidence (backend):
- Команда открытия: `open_artifact_media_window`: `client/src-tauri/src/commands.rs:117-177`.
- Команда закрытия: `close_artifact_media_window`: `client/src-tauri/src/commands.rs:181-197`.
- Команды зарегистрированы в invoke handler: `client/src-tauri/src/main.rs:60-62`.

Evidence (frontend):
- Invoke-обертки: `openArtifactMediaWindow/closeArtifactMediaWindow` в `client/src/config/tauri.ts:239-279`.
- Отдельный route `/artifact-media` подключен: `client/src/main.tsx:33-35`.
- Standalone-экран существует: `client/src/ArtifactMediaStandalone.tsx:65-75`.

Conclusion:
- Detached path в коде есть и формально собран end-to-end.

---

## MARKER_159.RECON.3 — Разрыв UX: fullscreen кнопка не переключает в detached режим
Evidence:
- Fullscreen в плеере в embedded режиме идет в `setWindowFullscreen(next, "main")`: `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:431-441`.
- Открытие detached окна привязано к отдельной toolbar-кнопке `onDetach` (иконка ExternalLink), а не к fullscreen кнопке плеера:
  - `client/src/components/artifact/Toolbar.tsx:204-207`
  - `client/src/components/artifact/ArtifactPanel.tsx:1616`

Conclusion:
- Пользователь, нажимающий fullscreen в плеере, не получает detached media window автоматически.
- Поэтому визуально остается ощущение, что "fullscreen не тот" и artifact остается внутри main.

---

## MARKER_159.RECON.4 — Возможный runtime mismatch: Rust-команды требуют перезапуск Tauri
Evidence:
- Команды detached окна добавлены в Rust (`commands.rs`, `main.rs`) и вызываются через invoke.
- Если Tauri runtime не перезапущен после Rust-изменений, frontend может уже показывать кнопку detach, но invoke-команда будет отсутствовать в живом backend процессе.
- В `tauri.ts` при ошибке только `console.warn`, без UI-ошибки: `client/src/config/tauri.ts:259-260`, `276-277`.

Conclusion:
- Если не было полного рестарта Tauri app после внедрения Rust command handler, detached path мог "молча" не сработать.
- Пользователь при этом видит embedded окно и считает, что функция не реализована.

---

## MARKER_159.RECON.5 — Тесты подтверждают wiring строками, но не runtime поведение окон
Evidence:
- `tests/phase159/test_phase159_media_window_open_close_contract.py:11-23` проверяет наличие строк в файлах.
- `tests/phase159/test_phase159_video_player_fullscreen_mode_priority.py:11-19` фиксирует, что fullscreen path содержит `setWindowFullscreen(next, "main")`.

Conclusion:
- Текущие тесты — контрактные/статические, не проверяют фактическое появление второго Tauri окна в рантайме и не ловят сценарий "кнопка есть, runtime handler не активен".

---

## Root Cause Summary
1. **Архитектурно:** default artifact UI по-прежнему embedded (это нормально, так и заложено).
2. **UX-разрыв:** fullscreen кнопка плеера не переводит в detached-mode; detached — отдельная кнопка.
3. **Операционный риск:** при отсутствии рестарта Tauri после Rust-изменений detached invoke может не работать, а UI не показывает явную ошибку.
4. **Тестовый гэп:** нет runtime E2E-проверки "detached window реально открылось и живет независимо".

---

## What Was Implemented But “Went Wrong” in Perception
Implemented:
- Полный кодовый путь для detached media window (backend+frontend+route+standalone).

Went wrong:
- Пользовательский сценарий ожидал detached/fullscreen от fullscreen-кнопки плеера.
- Реализация требует отдельного действия (detach icon), и это неочевидно.
- Возможен runtime mismatch без рестарта Tauri, что делает функцию визуально "как будто не реализована".

---

## Recon Verdict
- Detached окно **сделано в коде**.
- В текущем UX/рантайме оно **не стало основным fullscreen путем**, поэтому воспринимается как "не работает".
- Перед следующим шагом имплементации нужно либо:
  1. сделать fullscreen-кнопку маршрутом в detached окно + native fullscreen,
  2. либо явно пометить/усилить detach UX и добавить runtime fail-notice.
