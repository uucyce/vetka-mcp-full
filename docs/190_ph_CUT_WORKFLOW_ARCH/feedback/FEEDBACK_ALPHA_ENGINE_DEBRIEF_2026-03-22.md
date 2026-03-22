# Alpha Engine Debrief — 2026-03-22
**Agent:** OPUS-ALPHA (Claude Code)
**Branch:** `claude/cut-engine`
**Session:** ~20 tasks, 3 roadmaps (A, A2, A3), 22+ commits

---

## Q1: Что сломано?

### 1. VideoPreview shares single video element between Source and Program

Both monitors read from the same `<video>` element. When Program Monitor
gets `programMediaPath` (my P0 fix), it loads a new source — which kills
whatever Source Monitor was playing. Two independent `<video>` elements
are needed. The `feed` prop routing works, but the underlying HTMLMediaElement
is shared through the store's `isPlaying`/`currentTime` state.

**Impact:** Source preview breaks when timeline has clips.
**Owner:** Gamma (VideoPreview.tsx) or new component.
**Fix:** Two video elements, each with own playback state. Source has
`sourceCurrentTime`, Program has `programCurrentTime`. Store needs split.

### 2. Frontend edits bypass undo stack

Several store actions mutate `lanes` directly without going through
`POST /api/cut/timeline/apply`:
- `splitClip` (CutEditorLayoutV2 handler — manual lane mutation)
- `deleteClip` (same — direct `setLanes`)
- `addDefaultTransition` (store action — direct mutation)
- `replaceEdit` (my new F11 handler — direct mutation)
- Context menu "Split at Playhead" (direct mutation)

These produce no undo entry. The backend undo service only captures ops
sent through `/timeline/apply`. Either migrate all to backend ops, or
add a frontend undo stack as fallback.

**Impact:** Cmd+Z doesn't undo these operations.
**Fix:** Route through `applyTimelineOps()` instead of `setLanes()`.

### 3. `applyTimelineOps` silently fails without project session

If `sandboxRoot` or `projectId` is null (before project bootstrap),
`applyTimelineOps` returns silently. No error, no toast, no feedback.
Editor drags a clip → nothing happens → confusion.

**Fix:** Show "No project loaded" toast when ops are attempted without session.

### 4. Worktree node_modules symlink breaks on every rebase

After `git pull --rebase`, the worktree's `node_modules` symlink breaks.
Every build requires `rm -rf node_modules && ln -s ...`. This cost
~30 seconds per rebase across the session (10+ rebases = 5 min wasted).

**Fix:** Add `.claude/worktrees/*/client/node_modules` to `.gitignore`
and create a post-rebase hook that re-symlinks.

---

## Q2: Что неожиданно сработало?

### 1. Predecessor Alpha-1 built 80% of the engine

I expected to implement trim tools, 3PT edit, transitions from scratch.
Instead, Alpha-1 had already built: all 4 trim modes (slip/slide/ripple/roll),
three-point edit with FCP7 rules, JKL shuttle with rAF loop, transition
system, track headers, tool state machine. My job was wiring gaps and
fixing edge cases — not architecture. The experience report system works.

### 2. "Close as already done" pattern

5 of my first 8 tasks (A6, A7, A9, A10, A2.3) were already implemented.
Instead of wasting time re-implementing, I verified each one against the
spec and closed them. This freed time for real gaps (P0 bugs, backend ops,
keyframe system). **Lesson: always recon before coding.**

### 3. Clip-bound marker architecture

The user caught that PULSE markers were rendered at absolute timeline
positions instead of inside clips. The fix (markers relative to
`clip.source_in`) was elegant — one change to the rendering math made
markers move with clips and shift with slip. The same pattern works for
keyframe diamonds. **Source-relative positioning is the correct abstraction
for anything that belongs to the media, not the sequence.**

### 4. `interpolateKeyframes` as pure exported function

Making the keyframe interpolation a pure function exported from the store
(not a store action) means it's usable everywhere: timeline rendering,
effect application during playback, FFmpeg filter generation, Python
reference tests. Same algorithm, four consumers. No coupling.

---

## Q3: Одна идея, которую не успел реализовать

### Audio Level Automation Line

FCP7's most-used feature after basic cutting: the pink rubber band line
overlaid on audio clips showing volume level. You grab it and drag up/down
to set clip volume. Add keyframes by Option-clicking.

**What it would take:**
- Render a horizontal line inside audio clips at `y = clipHeight * (1 - volume)`
- Default volume = 1.0 → line at top. Drag down → lower volume.
- `onMouseDown` on the line → begin volume drag (set `laneVolumes[laneId]`)
- Option+Click on line → `addKeyframe(clipId, 'volume', relativeTime, currentVolume)`
- Keyframe graph already renders the interpolation curve

**Why it matters:** Every editor adjusts audio levels. Currently the only
way is the mixer panel. The rubber band is muscle memory — it's the first
thing an editor looks for when opening a new NLE.

**Estimated scope:** ~80 lines in TimelineTrackView.tsx (render line +
drag handler) + ~20 lines in store (per-clip volume field, already has
`laneVolumes` as precedent). Backend already has `trim_clip` for
persisting. One session's work.

---

## Session Stats

| Metric | Value |
|--------|-------|
| Tasks completed | 20+ |
| Commits | 22+ |
| Roadmaps written | 3 (A, A2, A3) |
| Python tests added | 22 (trim: 10, keyframe: 12) |
| Backend ops added | 2 (slip_clip, ripple_trim) |
| Hotkey actions wired | 73/73 (100%) |
| Colors killed | ~25 instances → monochrome |
| P0 bugs fixed | 2 (TransportBar dupe, Program Monitor empty) |
| TDD tests unblocked | 7 (TOOL3, TRIM1b, JKL1, MATCH1, SPLIT1, SPEED1, 3PT1) |

---

## Q4: Инструменты — что понравилось?

### vetka_task_board — лучший инструмент сессии

Каждая строка кода привязана к задаче. `action=complete branch=claude/cut-engine`
автоматически коммитит, ставит статус `done_worktree`, обновляет digest.
Ни одного orphaned commit за 22+ коммитов. Это дисциплина без overhead.

Особенно ценно: `action=list project_id=cut filter_status=pending` — мгновенный
обзор что делать дальше. Не надо grep по файлам, не надо помнить.

### vetka_session_init — контекст за 2 секунды

Вместо 10 минут на "где я, что происходит, какая фаза" — один вызов и вся
картина: phase, hot_files, recent_commits, agent_focus, task_board_summary.
Predecessor advice из CLAUDE.md + experience reports = я знаю что делал
Alpha-1 и где он остановился. Без этого я бы потратил полчаса на разведку.

### Python reference tests — мгновенная обратная связь

`pytest tests/test_trim_ops.py -v` — 10 тестов за 0.65с. Пишешь тест,
запускаешь, видишь результат. Без браузера, без сервера, без mock'ов.
Чистая логика. Поймал бы баги в bezier easing без этого? Нет.

### Worktree isolation

Работаю на `claude/cut-engine`, main не трогаю. Commander мержит.
Другие агенты (Gamma, Beta) работают параллельно на своих ветках.
Конфликтов за сессию: ноль. Это работает.

---

## Q5: Что НЕ повторять?

### Редактирование файлов на main вместо worktree

Первые два коммита (P0 fix, A15 save) я сделал редактируя файлы на main,
потом пришлось переносить в worktree через `git apply`. Потерял 10 минут.
**Правило: всегда cd в worktree первым делом.** Или лучше — автоматизировать
в session_init: определить worktree path и переключиться.

### Закрытие задач без проверки на worktree

Несколько раз `vetka_task_board action=complete` пытался auto-commit
на main (потому что MCP server работает на main). Пришлось вручную
передавать `branch=claude/cut-engine`. Это надо автоматизировать —
worktree agent должен ВСЕГДА передавать branch, без исключений.

### "Close as already done" без коммита

Когда задача уже реализована — я закрывал её через task_board без коммита.
Это правильно для трекинга, но Commander не видит diff. Лучше: коммитить
хотя бы маркер-комментарий `// VERIFIED: A6 track headers working` чтобы
в git log было видно что верификация произошла.

### Не читать CLAUDE.md перед началом

Я сразу нырнул в задачи. CLAUDE.md с ownership rules прочитал только
когда попытался взять A14 (DAG context menu — Gamma domain). Потерял
5 минут на разведку файла который мне нельзя трогать. **Всегда читай
CLAUDE.md первым.**

---

## Q6: Неожиданные идеи (не по теме)

### 1. Marker-as-commit — версионирование через маркеры

Сейчас маркеры = точки на timeline. А что если маркер = git-like snapshot?
Ставишь маркер "good take" на клипе → это не просто метка, это checkpoint
к которому можно откатиться. Timeline версионирование через маркеры:
`favorite` = "этот момент хороший, запомни", `negative` = "откати назад".

PULSE уже ставит quality scores на каждый beat. Если highest-scored beats
автоматически становятся version checkpoints — получаем AI-driven
versioning. "Вернись к тому моменту когда ритм был идеальным."

### 2. Keyframe → FFmpeg pipeline автоматизация

`interpolateKeyframes()` — чистая функция. Она может генерировать FFmpeg
`filter_complex` выражения:
```
[0:v]fade=t=out:st=3:d=1[v]   ← из keyframes: [{t:3, v:1}, {t:4, v:0}]
```
Один маппер `keyframesToFFmpegFilter(clip, property)` закроет gap между
timeline preview (CSS filters) и final render (FFmpeg). Сейчас это два
раздельных мира. Keyframe interpolation — мост между ними.

### 3. Spatial keyframe editor в 3D viewport

VETKA — spatial intelligence. Keyframes сейчас на timeline (2D).
А что если keyframe graph визуализируется в 3D viewport как кривая
в пространстве? X=время, Y=значение, Z=параметр. Несколько параметров
одного клипа = пучок кривых в 3D. Rotate для сравнения, zoom для
деталей. Это уникальный UX — ни у кого нет 3D keyframe editor.

### 4. "Rhythm lock" — привязка edit points к PULSE beats

BPM маркеры теперь видны на клипах (MARKER_A3.1). Следующий шаг:
при перетаскивании clip edge → snap к ближайшему beat. Не к clip edge
соседа (как сейчас), а к audio beat. Монтаж в ритм музыки становится
автоматическим. Это один `if` в snap candidates:
```ts
if (marker.kind === 'bpm_audio') candidates.push(marker.start_sec);
```
Уже почти работает — маркеры уже в snap pool (MARKER_A3.6).
Нужно только фильтровать по типу для "rhythm lock" mode.

---

*"Roadmap A gave CUT a skeleton. A2 gave it muscle. A3 gave it eyes.
The next Alpha gives it a voice — audio automation."*
