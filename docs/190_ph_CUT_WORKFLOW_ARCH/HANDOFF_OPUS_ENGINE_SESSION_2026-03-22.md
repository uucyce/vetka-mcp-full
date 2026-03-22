# HANDOFF: Opus Engine Session 2026-03-22
**Agent:** OPUS-ALPHA-2 (Claude Code, claude/cut-engine)
**Session:** 12 задач, 141+ тестов
**Branch:** `claude/cut-engine` — все коммиты здесь, Commander мерджит на main

---

## ЗАДАНИЕ ОТ КОМАНДИРА (вход в сессию)

### Общий контекст
Wave 5: Precision Editing — превратить CUT в инструмент где монтажёр ЧУВСТВУЕТ профессиональную точность. Эталон: FCP7 Ch.33, Ch.44, Ch.45-46, Ch.50, Ch.51.

### Наставление от Alpha-1 (предшественник)
> "Не трогай useCutEditorStore для timeline data — используй useTimelineInstanceStore.updateTimeline(). Добавь onProjectStateRefresh → re-snapshot."

### P0 задача от Commander
Three-Point Editing (tb_1774124212_1): FCP7 Ch.36 — Source IN/OUT + Sequence IN/OUT → auto-fourth-point. Comma (,) = Insert. Period (.) = Overwrite. Backend endpoints insert/overwrite УЖЕ ЕСТЬ — wire frontend. Без этого CUT = drag-and-drop, а не NLE.

### Правила
- Все коммиты на `claude/cut-engine`, НЕ на main
- `vetka_task_board action=complete branch=claude/cut-engine`
- Commander мерджит после review
- Ownership: useCutEditorStore, useTimelineInstanceStore, useCutHotkeys, TimelineTrackView, CutEditorLayoutV2

---

## ЧТО СДЕЛАНО (12 задач)

### Фаза 1: Editable Timecode (`ae505e6a`, 38 тестов)
- `TimecodeField.tsx`: click-to-edit SMPTE HH:MM:SS:FF
- `formatTimecode()`: 23.976/24/25/29.97df/30/50/59.94/60
- `parseTimecodeInput()`: absolute, relative (+/-), partial (FCP7-style 1419→00:00:14:19)
- Drop-frame semicolon separator для 29.97/59.94
- Интегрирован в MonitorTransport (Source + Program) и TimelineTrackView (над ruler)
- Frame step теперь использует projectFramerate вместо hardcoded 25

### Фаза 2: Slip/Slide/Ripple/Roll (`35d36e3c`, 12 тестов)
- `activeTool` расширен: 'slip'|'slide'|'ripple'|'roll'
- `source_in` field добавлен в TimelineClip для slip editing
- ClipDragMode расширен: slip/slide/ripple_left/ripple_right/roll
- Полная drag-логика: slip=двигать контент, slide=между соседями, ripple=edge+shift, roll=edit point
- Визуальный overlay: +/- frames во время drag
- Hotkeys: Premiere (Y/U/B/N), FCP7 (S/D/R/Shift+R)

### Фаза 3: Three-Point Editing — P0 (`40f02ced`, 12 тестов)
- `useThreePointEdit.ts`: resolveThreePointEdit() авто-вычисляет 4-ю точку
- Sequence IN/OUT takes precedence (FCP7 rule)
- Backtracking: set seq OUT → auto-calc seq IN
- Comma (,) = Insert via backend `insert_at`, Period (.) = Overwrite via `overwrite_at`
- Post-edit: playhead moves to end, sequence marks cleared
- Заменил local-only insert/overwrite в CutEditorLayoutV2

### Фаза 4: Match Frame + Q toggle (`44fc6c82`, 12 тестов)
- F key: find clip at playhead → load source in Source Monitor → seek to source-relative time (accounting for source_in offset)
- Q key: toggle focus Source↔Program
- Wired in MonitorTransport (button) и CutEditorLayoutV2 (hotkey)

### Фаза 5: Store Migration Phase 1 (`52954b60`, 11 тестов)
- `effective*` variables в TimelineTrackView: читают из instance store когда multi-instance, иначе singleton
- Redirected: lanes, waveforms, zoom, scrollLeft, trackHeight, currentTime, markIn, markOut
- `onProjectStateRefresh()` в useTimelineInstanceStore: синхронизирует backend data в active instance
- CutStandalone: wired instanceRefresh рядом с editorSetLanes
- View state (zoom, scroll, playhead) НЕ перезаписывается при refresh

### Фаза 6: JKL Progressive Shuttle (`b9d066b6`, 23 теста)
- J: reverse ramp 0→-1→-2→-4→-8 (каждый press ускоряет)
- L: forward ramp 0→1→2→4→8
- Нажатие в противоположном направлении сначала тормозит
- K: stop (pause + reset shuttle)
- rAF loop в CutEditorLayoutV2: drives seek() при shuttleSpeed ≠ 0 и ≠ 1
- Заменяет старый ±5s seek-on-press

### Фаза 7: Wire all missing hotkey handlers (`5f4e5bd8`, 11 тестов)
- **100% hotkey coverage** — все CutHotkeyAction имеют рабочий handler
- undo/redo: wired к backend POST /cut/undo + /cut/redo
- rippleDelete: remove clip + shift subsequent clips left
- nudgeLeft/Right: ±1 frame (projectFramerate-aware)
- addMarker (M) / addComment (Shift+M): via backend API
- cyclePlaybackRate: 0.5x→1x→2x→4x
- importMedia (Cmd+I): dispatch cut:import-media event
- sceneDetect (Cmd+D): POST /cut/scene-detect-and-apply

### Фаза 8: Tauri Desktop Build (`46355e31`)
- `tauri.cut.conf.json`: VETKA CUT, identifier ai.vetka.cut
- Window opens `/cut` route → CutStandalone directly
- CSP includes media-src для video playback
- **VETKA CUT_0.1.0_aarch64.dmg — 17MB**
- npm scripts: `tauri:build:cut` / `tauri:dev:cut`

### Фаза 9: Import Media Fix (`a1d2bfea`, 11 тестов)
- Bug 1: Event name mismatch — hotkey dispatched 'cut:import-media', ProjectPanel listened for 'cut:trigger-import'
- Bug 2: File picker → folder picker (webkitdirectory) для NLE import
- Bug 3: Stale projectId в refreshProjectState closure — direct fetch с correct pid

### Фаза 10: Tool State Machine Visual (`511f1ffb`, 13 тестов)
- TimelineToolbar: active tool indicator (label + shortcut + color)
- Clip cursor: dynamic per-tool (selection=grab, razor=crosshair, trim=resize)
- Removed hardcoded `cursor:'grab'` from CLIP_STYLE

### Фаза 11: Duplicate Transport Bar Fix (`6724812f`, 10 тестов)
- Root cause: corrupt dockview layouts в localStorage с duplicate panel IDs
- 3-layer defense: cleanup on mount + validate before restore + refuse to save corrupt

### Фаза 12: Ruler Labels Fix (`5c894d95`)
- Root cause: containerWidth не реактивный (fallback 800px → ruler обрывался на ~12s)
- Fix: ResizeObserver на containerRef → reactive state
- Бонус: ruler contrast bumped (#999→#bbb, ticks #555→#666, font 10px JetBrains Mono)

---

## АРХИТЕКТУРНЫЕ РЕШЕНИЯ

1. **Three-Point Edit**: sequence marks take precedence over source marks (FCP7 rule)
2. **Store migration**: Phase 1 = reads only, writes stay on singleton. Zero breakage.
3. **JKL shuttle**: rAF loop for speeds ≠ 1, video element handles normal 1x playback
4. **Tauri CUT**: dedicated config, window opens /cut route directly, 17MB DMG
5. **Dockview dedup**: 3-layer guard prevents corrupt layouts from persisting

## ЧТО ОСТАЛОСЬ / РЕКОМЕНДАЦИИ

- **Store migration Phase 2**: redirect writes через useTimelineInstanceStore
- **Source/Program video split**: оба монитора ещё на одном activeMediaPath (known)
- **Browser upload**: /cut/import-files endpoint есть, но browser FileList не даёт paths
- **Tauri sidecar**: Python backend нужно запускать отдельно, не bundled в .app
- **E2E тесты**: Playwright specs для 3PT / JKL / Match Frame workflow

---

*"12 задач. 141 тест. Ноль регрессий. CUT теперь NLE."*
