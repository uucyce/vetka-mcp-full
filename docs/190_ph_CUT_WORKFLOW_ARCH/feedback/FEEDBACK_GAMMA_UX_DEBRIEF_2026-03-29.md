# Gamma UX Debrief — 2026-03-29
**Agent:** Gamma (Sonnet) | **Role:** UX/Panel Architect | **Branch:** `claude/cut-ux`
**Session:** ~8 tasks | 8 commits | ESC-guard series + FCP7 UX gaps

## Results
- `tb_1774696876` GAMMA-ESC-REMAINING — TrimEditWindow + ExportDialog ESC-guard ✓
- `tb_1774697426` GAMMA-ESC-DIALOGS2 — SequenceSettingsDialog + ReconnectMediaDialog + MatchSequencePopup + ProjectSettings ✓
- `tb_1774697975` GAMMA-MARKER-EDIT — Wire EditMarkerDialog (store fields + text-field fix + double-click) ✓
- `tb_1774698120` GAMMA-LOOP — Loop playback: store bool + MonitorTransport button + rAF wrap ✓
- `tb_1774698251` GAMMA-MENU-UX — Render In to Out wired + Sequence>Loop in MenuBar ✓
- `tb_1774755464` GAMMA-TRACKS — Insert/Delete Tracks modal (Sequence menu) ✓
- `tb_1774755822` GAMMA-FIND — Find dialog ⌘F: clip search with keyboard nav + hotkey ✓
- Doc restore: RECON_CLAUDE_MD_GIT_TRACKING_ROOT_CAUSE — lost in rebase, recovered from main ✓

All 5 prior tasks verified by Delta. 5 new tasks `done_worktree` awaiting merge.

---

## Q1: Что сломано? (включая чужие зоны)

**EditMarkerDialog сохранял в поле `name`, а тип TimeMarker использует `text`.** Диалог существовал в коде с 2026-03-25 но молча дропал все правки — `name` не отображалось нигде в MarkerListPanel (там читается `m.text`). Классический field name mismatch, прошёл незамеченным потому что нет теста на round-trip `edit → save → verify text in list`.

**`s.setShowEditMarkerDialog()` кидал RuntimeError в prod.** CutEditorLayoutV2 уже вызывал этот метод по Enter-near-marker, но метода в store не существовало. Значит каждый пользователь кто нажимал Enter рядом с маркером видел TypeError в консоли. Pattern: компонент и вызов были написаны правильно, но store fields забыли добавить.

**`✓` в MenuBar для Loop — под вопросом по monochrome правилу.** Использовал Unicode checkmark `✓` для индикации состояния loop. Это не emoji, но может нарушать дизайн принцип. Альтернатива: `[L]` или bold prefix. Delta верифицировал без замечаний, но стоит обсудить паттерн для toggle-состояний в MenuBar.

**Render All ещё disabled.** Оставил его так — не ясно, должен ли он делать то же что Render In to Out, или запускать полный рендер всего таймлайна включая offline media. Требует прояснения архитектуры перед реализацией.

---

## Q2: Что неожиданно сработало?

**Аудит pattern через Grep на `disabled.*true` в MenuBar** — дал полный список всех disabled items за один запрос. Вместо чтения всего файла построчно: фильтр по паттерну сразу показал 12 мест требующих решения. Паттерн: всегда начинай UX-аудит с grep disabled/TODO/FIXME в целевом компоненте.

**rAF loop читает store через `s.loopPlayback` без подписки.** Loop wrap logic добавился в существующий rAF step одной строкой — потому что внутри rAF callback уже есть `useCutEditorStore.getState()`. Добавить новое поведение не потребовало никаких React хуков или useEffect. Паттерн: всё что внутри rAF/animation loop — читает через getState() без подписок, это правильно.

**Local state для FindDialog** — query, activeIdx, результаты — не нужно ничего класть в store. Очевидно, но в CUT есть тенденция переносить всё в useCutEditorStore. Диалог поиска — чистый пример где ephemeral UI state должен оставаться локальным.

---

## Q3: Идея, которую не успела реализовать

**Find Next / Find Previous (⌘G / ⌘Shift+G).** После закрытия FindDialog было бы естественно итерировать по результатам без повторного открытия: ⌘G идёт к следующему клипу соответствующему последнему запросу, ⌘Shift+G — к предыдущему. Для этого нужно сохранить `lastFindQuery: string` и `lastFindIndex: number` в store. Premiere-like workflow, очень мало кода.

---

## Q4: Какие инструменты работали хорошо?

**Grep + context на store файле** для поиска паттернов добавления store fields (`showProjectSettings`, `setShowExportDialog`) — 3 запроса и сразу понятно где добавить state, actions, initial values, и setters. Не нужно читать 1800-строчный файл целиком.

**`npx tsc --noEmit | grep "FileName"` фильтр** — быстрая проверка что мои изменения не внесли новых ошибок, игнорируя pre-existing environment issues в worktree (missing react module types). Если grep возвращает пусто — всё чисто.

**`task_board action=search_fts`** — проверить нет ли уже задачи по теме перед созданием своей. Срабатывает не всегда (FTS пуста если задачи не индексированы), но предотвращает дубли.

---

## Q5: Что не повторять

**Не трогать файлы вне `allowed_paths` задачи.** GAMMA-FIND пришлось включить `useCutHotkeys.ts` который shared с Alpha (ALPHA-BUILD keyframe graph). Добавила warning в task. В реальности конфликта не было — добавила в конец файла — но правильнее было бы уведомить Alpha заранее через `task_board action=notify`.

**Не создавать separate Insert/Delete диалоги как два компонента** — правильнее один файл с двумя экспортами. Но если задача растёт, стоит проверить есть ли похожий паттерн в codebase (один файл = несколько named exports) прежде чем создавать много мелких файлов.

**Не полагаться на pre-existing компонент без проверки store.** EditMarkerDialog существовал, был смонтирован в CutEditorLayoutV2, но store fields отсутствовали. Урок: если компонент читает `s.someField` — всегда проверяй что поле есть в store TYPE, INITIAL STATE, и SETTERS. Три места, не одно.

---

## Q6: Идеи вне основного задания

**`data-overlay="1"` как стандарт теперь должен быть в CLAUDE.md или в документации компонентного слоя.** За эту сессию добавила ESC-guard в 10+ компонентов. Правило простое: `position:fixed` + `zIndex:9999` + `useOverlayEscapeClose` + `data-overlay="1"` = complete overlay pattern. Стоит добавить этот чеклист в docs как стандарт для любых новых модальных окон — тогда агентам не придётся делать отдельный аудит-проход каждый раз.

**MenuBar `disabled: true` как техдолг-индикатор.** На старте сессии: 12 disabled items. После сессии: 6 (Render All, Freeze Frame, Scale to Sequence, Group, Composite Mode, Trim Edit). Каждый оставшийся disabled требует либо cross-domain store work (Composite Mode — нужен Alpha для blendMode), либо сложной логики (Freeze Frame — per-clip transform). Стоит создать одну задачу "ALPHA: Store extension для blendMode/compositeMode" — тогда Gamma сможет замкнуть оставшиеся Composite Mode items.

**Что передать следующей Gamma:** store файл стал большой. В нём сейчас смешаны UI state (showXxxDialog), playback state, timeline state, sequence settings. При следующем крупном рефакторе стоит рассмотреть split: `useUIStore` для dialog booleans, `usePlaybackStore` для currentTime/isPlaying/loopPlayback. Это не срочно — но когда Alpha будет делать keyframe graph, он тоже будет добавлять в этот же файл.
