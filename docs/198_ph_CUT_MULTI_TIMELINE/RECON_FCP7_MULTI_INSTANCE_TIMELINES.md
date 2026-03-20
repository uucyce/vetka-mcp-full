# RECON: FCP7 Multi-Instance Timelines for VETKA CUT

**Phase:** 198 — CUT Multi-Timeline Architecture
**Date:** 2026-03-20
**Author:** Opus + Данила
**Reviewed by:** GPT (independent review 2026-03-20)
**Status:** Architecture Decision — reviewed, contracts added
**Updates:** VETKA_CUT_Interface_Architecture_v1.docx § 1 (Design Philosophy), § 9 (Panel Sync)

---

## 1. Vision: FCP7 Reborn

> "FCP7 forever" — Данила Гулин

Final Cut Pro 7.0.3 — объективно лучшая архитектура монтажного ПО.
Apple убила её в FCPX ради "простоты". Мы возрождаем.

### Что делало FCP7 гениальным

| Свойство | FCP7 | Premiere | FCPX | **VETKA CUT** |
|----------|------|----------|------|---------------|
| Каждое окно — независимый объект | ✅ | ❌ (singleton timeline) | ❌ | ✅ |
| Два таймлайна проигрываются одновременно | ✅ | ❌ | ❌ | ✅ (Phase 2) |
| Скроллинг неактивного таймлайна | ✅ | ✅ | ❌ | ✅ |
| Встраивание внешних окон в workspace | ✅ (через OS X) | ❌ | ❌ | ✅ (dockview + Tauri) |
| Панели свободно отстёгиваются | ✅ | Частично | ❌ | ✅ (dockview float) |
| Серый профессиональный дизайн | ✅ | Тёмный | Белый → серый | ✅ (FCP7 skin — Phase 3) |

### Долгосрочная цель

**Phase 3: FCP7 Skin** — полное воспроизведение цветовой палитры и стиля FCP7.
Серые панели, серые кнопки, зелёная волна — только за это мы выйдем в топ.
Плюс наши функции (PULSE, DAG, Story Space 3D) = лидер рынка.

---

## 2. Проблема: Singleton Store

Текущее состояние `useCutEditorStore`:

```
lanes: TimelineLane[]        ← ОДНИ на всех
markers: TimeMarker[]        ← ОДНИ
currentTime: number          ← ОДИН плейхед
zoom: number                 ← ОДИН зум
scrollLeft: number           ← ОДИН скролл
```

TimelineTrackView читает напрямую из глобального store **без props**.
Если создать 2 инстанса — оба покажут одно и то же.

TimelineTabBar переключает `activeTimelineTabIndex` → backend перезагружает данные в store.
Это **не multi-instance** — это **tab switching с перезагрузкой**.

---

## 3. Архитектура: Multi-Instance с Shared Playback Focus

### ❌ НЕ snapshot (хардкод, мёртвые панели)
### ✅ Полноценные живые экземпляры

Каждый таймлайн — **полностью интерактивный**. Разница с "активным" — только в транспорте.

### TimelineInstance — единица хранения

> **Design rule (GPT review):** NO Set<> в serializable state.
> Все коллекции — `string[]` или `Record<string, boolean>`.
> Set ломает persistence, JSON.stringify, Zustand devtools, project save.

```typescript
interface TimelineInstance {
  id: string                    // 'tl_cut-00', 'tl_cut-01-v02'
  label: string                 // 'Cut 00 — Assembly'
  version: number               // auto-increment
  mode: 'manual' | 'favorites' | 'script' | 'music'
  parentId?: string             // от какого таймлайна порождён
  createdAt: number

  // === DATA (загружается с backend) ===
  lanes: TimelineLane[]
  // markers НЕТ — единый пул в store.markers[], фильтр через getMarkersForTimeline() §3.1
  waveforms: WaveformItem[]
  thumbnails: ThumbnailItem[]
  duration: number

  // === VIEW STATE (локальный, не на backend) ===
  scrollX: number               // горизонтальная прокрутка
  scrollY: number               // вертикальная (если дорожек много)
  zoom: number                  // px/sec
  trackHeight: number           // высота дорожки

  // === PLAYBACK STATE ===
  playheadPosition: number      // текущая позиция (для скрабинга)
  isPlaying: boolean            // Phase 2: разрешить нескольким
  markIn: number | null
  markOut: number | null

  // === SELECTION (string[], NOT Set) ===
  selectedClipIds: string[]     // ← was Set<string>
  hoveredClipId: string | null

  // === LANE STATE (Record, NOT Set) ===
  mutedLanes: Record<string, boolean>    // ← was Set<string>
  soloLanes: Record<string, boolean>
  lockedLanes: Record<string, boolean>
  targetedLanes: Record<string, boolean>

  // === FOCUS HISTORY ===
  lastFocusedAt: number         // timestamp — для close fallback (см. §3.2)
}
```

### §3.1 Маркеры: Unified Model (НЕ три бункера)

> **Full spec:** `CUT_MOMENT_DOCTRINE.md` — M/MM/F/N hotkeys, moment boundary detection, PULSE integration.
> Момент = не секунда, а шот (cut-to-cut / pause-to-pause / beat-to-beat).

> **ANTI-PATTERN (Premiere model):** TimelineMarker / SourceMarker / ClipMarker — три типа, три хранилища.
> Это стандартная колея. VETKA НЕ идёт этим путём.

**VETKA model:** Один тип `TimeMarker`, одно хранилище, поле `kind` + scope fields.

```typescript
// ЕДИНЫЙ тип — все маркеры проекта
type TimeMarker = {
  marker_id: string
  kind: MarkerKind              // ← решает всё
  timeline_id?: string          // на каком таймлайне (если привязан)
  media_path?: string           // к какому исходнику (если привязан)
  start_sec: number
  end_sec: number
  // ... PULSE enrichment: energy, pendulum, camelot_key, sync_strength
}
```

**11 видов маркеров CUT (see CUT_MOMENT_DOCTRINE.md for full spec):**

| Kind | Hotkey | Название | Scope | Кто ставит |
|------|--------|----------|-------|-----------|
| `moment` | **M** | Marker на максималках (auto-detect boundaries) | timeline | Юзер |
| `favorite` | **F** | Favorite Moment | source | Юзер |
| `negative` | **N** | Negative Moment (исключить) | source | Юзер |
| `comment` | **MM** | Comment on Moment (с текстом) | timeline | Юзер |
| `cam` | — | CAM memory | auto | Система |
| `insight` | — | AI insight | auto | PULSE |
| `chat` | — | Chat marker | timeline | Юзер |
| `bpm_audio` | — | Audio BPM | source | PULSE |
| `bpm_visual` | — | Visual BPM | source | PULSE |
| `bpm_script` | — | Script BPM | timeline | PULSE |
| `sync_point` | — | Sync (жирный, 2-3 BPM совпали) | timeline | PULSE |

> ⚠️ `moment` и `negative` — **НЕТ В КОДЕ**, нужно добавить.
> M = auto-detect moment boundaries (cut/pause/beat), NOT point marker.
> MM = comment (double-press M opens text input on detected moment).

**Scope логика:**
- `source` scope: маркер привязан к `media_path` + позиции в исходнике. Виден на ВСЕХ таймлайнах где есть этот клип.
- `timeline` scope: маркер привязан к `timeline_id` + позиции в секвенции. Виден только на этом таймлайне.
- BPM маркеры: вычислены из source, но **проецируются** на timeline через позицию клипа.

**Multi-instance: НЕ копируем маркеры в каждый instance.**

```typescript
interface CutEditorStore {
  // Единый пул маркеров проекта (NOT per-timeline)
  markers: TimeMarker[]

  // Computed getter — маркеры релевантные для таймлайна
  getMarkersForTimeline(timelineId: string): TimeMarker[] {
    return this.markers.filter(m =>
      m.timeline_id === timelineId ||                    // timeline-scoped
      isSourceMarkerOnTimeline(m, timelineId)            // source-scoped → проекция
    )
  }
}
```

Favorite поставленный в source monitor → виден на ВСЕХ таймлайнах с этим клипом.
Comment поставленный на таймлайне → виден только на этом таймлайне.
Sync point → вычислен для конкретного таймлайна, привязан к нему.

### §3.2 Close Fallback — что происходит при закрытии active timeline

```
CONTRACT: Active Timeline Close Fallback

When active timeline panel is closed:
1. Find most recently focused remaining timeline (by lastFocusedAt)
2. If found → setActiveTimeline(that.id)
3. If no timelines remain → activeTimelineId = '' (empty state)
4. Program Monitor → shows empty/black
5. Transport controls → disabled

Implementation: removeTimeline(id) handles this internally.
Never leave activeTimelineId pointing to a deleted instance.
```

### Store — верхний уровень

> **Design rule (GPT review):** `timelines` runtime = `Map<string, TimelineInstance>`.
> For project save/load: serialize as `Record<string, TimelineInstance>` (plain object).
> Hydration: `Object.entries(saved) → new Map()`. One-liner, no pain.

```typescript
interface CutEditorStore {
  // === MULTI-INSTANCE ===
  timelines: Map<string, TimelineInstance>    // runtime: Map for O(1) lookup
  activeTimelineId: string       // кто получает Space/Play/transport

  // === GLOBAL (не per-timeline) ===
  focusedPanel: PanelType | null
  activeTool: ToolType           // global OK (GPT confirmed)
  snapEnabled: boolean           // global OK
  linkedSelection: boolean       // global OK
  projectFramerate: number
  timecodeFormat: 'smpte' | 'milliseconds'
  dropFrame: boolean
  startTimecode: string
  audioSampleRate: number
  audioBitDepth: number

  // === SOURCE MONITOR (отдельный от timeline) ===
  sourceMediaPath: string | null
  sourceMarkIn: number | null
  sourceMarkOut: number | null

  // === MARKERS (unified pool — see §3.1) ===
  markers: TimeMarker[]                          // ALL project markers, single pool
  getMarkersForTimeline(id: string): TimeMarker[] // computed filter

  // === PROJECT ===
  sandboxRoot: string | null
  projectId: string | null

  // === ACTIONS ===
  createTimeline(opts: CreateTimelineOpts): string   // returns new id
  removeTimeline(id: string): void                   // handles close fallback
  setActiveTimeline(id: string): void                // updates lastFocusedAt
  getTimeline(id: string): TimelineInstance | undefined
  updateTimeline(id: string, partial: Partial<TimelineInstance>): void

  // === SERIALIZATION ===
  serializeTimelines(): Record<string, TimelineInstance>  // for project save
  hydrateTimelines(data: Record<string, TimelineInstance>): void  // for project load

  // Transport — ТОЛЬКО для activeTimelineId
  play(): void
  pause(): void
  togglePlay(): void
  seek(time: number): void
  setPlaybackRate(rate: number): void
  shuttle(direction: 'forward' | 'backward'): void   // JKL
}
```

### Как компонент читает данные

```tsx
// TimelineTrackView.tsx — НОВЫЙ API
interface TimelineTrackViewProps {
  timelineId: string
}

function TimelineTrackView({ timelineId }: TimelineTrackViewProps) {
  const instance = useCutEditorStore(s => s.timelines.get(timelineId))
  const isActive = useCutEditorStore(s => s.activeTimelineId === timelineId)

  if (!instance) return null

  const { lanes, markers, zoom, scrollX, playheadPosition } = instance

  // Рендерим ПОЛНЫЙ интерактивный таймлайн
  // Единственная разница: плейхед ярче у active
  return (
    <div
      onClick={() => setActiveTimeline(timelineId)}
      className={isActive ? 'timeline-active' : 'timeline-inactive'}
    >
      {/* Полный рендер: ruler, lanes, clips, markers, playhead */}
      {/* Мышь: скролл, зум, scrub — всё работает всегда */}
      {/* Только клавиши Space/JKL → идут в active */}
    </div>
  )
}
```

### Визуальная разница Active vs Inactive

| Аспект | Active | Inactive |
|--------|--------|----------|
| Плейхед | Белый, яркий, с треугольником | Серый (#666), тонкий |
| Header панели | Подсвечен (accent color) | Обычный |
| Мышь: scrub | ✅ двигает плейхед | ✅ двигает плейхед |
| Мышь: scroll/zoom | ✅ | ✅ |
| Мышь: clip drag | ✅ | ✅ |
| Клавиша Space | ✅ Play/Pause | ❌ (идёт в active) |
| Клавиши JKL | ✅ Shuttle | ❌ (идёт в active) |
| Program Monitor | Показывает этот | — |

Важно: **неактивный таймлайн полностью живой**. Монтажёр может крутить его, искать следующий кусок, пока в активном идёт проигрывание. Как в FCP7.

---

## 4. Dockview Integration

Каждый таймлайн = отдельная dockview panel:

```typescript
dockviewApi.addPanel({
  id: `timeline-${timelineId}`,
  component: 'timeline',
  params: { timelineId },
  title: instance.label
})
```

Пользователь может:
- **Tab** — несколько таймлайнов в одной группе (как сейчас TimelineTabBar)
- **Split** — перетащить таб на край → side-by-side (вертикально или горизонтально)
- **Float** — вытащить в отдельное окно (Tauri multi-window в будущем)
- **Dock** — прикрепить куда угодно в layout

TimelineTabBar **удаляется**. Dockview native tabs полностью заменяют его.

---

## 5. Загрузка данных

```
createTimeline('tl_cut-01')
  ↓ store: timelines.set('tl_cut-01', { lanes: [], ... loading })
  ↓ dockview: addPanel({ params: { timelineId: 'tl_cut-01' } })
  ↓ backend: GET /api/cut/timeline/tl_cut-01
  ↓ response: { lanes, markers, waveforms, duration }
  ↓ store: updateTimeline('tl_cut-01', { lanes, markers, ... })
  ↓ UI: TimelineTrackView re-renders with data
```

Бэкенд **не знает** про "активный" таймлайн — это чисто фронтенд-концепция.
Бэкенд хранит данные каждого таймлайна отдельно и отдаёт по ID.

---

## 6. Phase 2: Одновременное проигрывание (FCP7 Level)

Архитектура **уже готова** к этому. Каждый instance имеет свой `isPlaying`.

Phase 1 ограничение (одна строчка):
```typescript
play() {
  // Phase 1: stop all others
  for (const [id, tl] of this.timelines) {
    if (id !== this.activeTimelineId) tl.isPlaying = false
  }
  this.timelines.get(this.activeTimelineId)!.isPlaying = true
}
```

Phase 2: убрать `for` loop. Каждый таймлайн может играть независимо.
Program Monitor показывает active, но Second Monitor (если есть) может показывать другой.

---

## 7. Phase 3: FCP7 Skin

Отдельная тема для дизайна. Ключевые элементы:

- **Цвет фона панелей:** #4A4A4A (серый, не чёрный)
- **Цвет кнопок:** #6B6B6B с 1px border #555
- **Timeline background:** #2D2D2D
- **Clip blocks:** градиент серый → тёмно-серый
- **Волна аудио:** зелёная (#00CC00)
- **Текст:** белый на сером
- **Разделители:** тёмные линии 1px
- **Без скруглений** — все углы прямые (FCP7 стиль)
- **Toolbar:** кнопки в ряд с чёткими иконками

Это будет **тема** в нашей системе тем (skin switcher).

---

## 8. План миграции

### Step 1: Store Refactor (0 UI)
- Создать `TimelineInstance` интерфейс
- Заменить плоские поля на `timelines: Map<string, TimelineInstance>`
- `activeTimelineId` вместо `activeTimelineTabIndex`
- Все текущие actions обновить: `setZoom(z)` → `updateTimeline(activeId, { zoom: z })`
- Backward-compatible: при загрузке создаём один instance из текущих данных

### Step 2: TimelineTrackView → props-driven
- Добавить `timelineId` prop
- Читать из `timelines.get(timelineId)` вместо плоских полей
- Все дочерние компоненты (TimeRuler, clip rendering) передают через props/context
- Active vs Inactive стилизация

### Step 3: Dockview wiring
- Каждый таймлайн = `addPanel({ component: 'timeline', params: { timelineId } })`
- `onDidActivePanelChange` → `setActiveTimeline()`
- Drag/split/float работает нативно

### Step 4: Cleanup
- Удалить `TimelineTabBar.tsx`
- Удалить `parallelTimelineTabIndex` + `swapParallelTimeline()`
- Удалить `timelineTabs[]` + `activeTimelineTabIndex`
- Удалить MARKER_W5.2 код

### Step 5: Backend alignment
- Убедиться что каждый timeline_id имеет свои lanes/markers на бэкенде
- API: `GET /api/cut/timeline/{id}` возвращает полный набор данных
- API: `POST /api/cut/timeline` создаёт новый (с опцией clone from parent)

---

## 9. Связь с Architecture Doc v1

Этот документ **расширяет** следующие секции VETKA_CUT_Interface_Architecture_v1.docx:

- **§ 1 Design Philosophy** — добавлен принцип "каждый таймлайн = независимый живой объект"
- **§ 2 Panel Catalog** → Timeline panel теперь multi-instance
- **§ 9 Panel Synchronization** → уточнено: transport sync только с active timeline; scroll/zoom/scrub — независимы per-instance

---

## 10. Контракты и инварианты (GPT review items)

### C1: No Set<> in serializable state
All collections use `string[]` or `Record<string, boolean>`.
**Enforced in:** TimelineInstance interface, code review.

### C2: Unified marker pool (NOT three buckets)
All markers live in ONE `store.markers[]` array. No per-instance copies.
`getMarkersForTimeline(id)` filters by `timeline_id` match OR source-scope projection.
Favorite on source → visible on ALL timelines containing that clip.
Comment on timeline → visible only on that timeline.
**Test:** add favorite in source monitor → appears on every timeline with that media.
**Test:** add comment on timeline A → does NOT appear on timeline B.
**Anti-pattern:** NEVER store markers inside TimelineInstance. Single source of truth.

### C3: Active timeline close fallback
`removeTimeline(id)` MUST activate the most recently focused remaining timeline.
If no timelines remain, `activeTimelineId = ''` and transport disabled.
**Test:** close the only open timeline → Program Monitor shows black, Space does nothing.

### C4: Serialization round-trip
`hydrateTimelines(serializeTimelines())` MUST produce identical state.
Map ↔ Record conversion is lossless.
**Test:** save → load → diff = empty.

### C5: Active edits contract
Only the ACTIVE timeline receives keyboard-driven edits (blade, ripple delete, paste).
Mouse-driven edits (clip drag, trim) work in ANY timeline (active or inactive).
**Rationale:** монтажёр может крутить неактивный таймлайн мышью, но клавиши всегда идут в активный. Как в FCP7.

### C6: Global vs per-instance boundary
| Field | Scope | Rationale |
|-------|-------|-----------|
| activeTool | Global | Tool applies to whichever panel has mouse focus |
| snapEnabled | Global | Snap behavior is project-wide preference |
| linkedSelection | Global | Link behavior is project-wide preference |
| zoom, scrollX/Y, playhead | Per-instance | Each timeline navigates independently |
| selectedClipIds | Per-instance | Selection is local to timeline |
| mutedLanes, soloLanes | Per-instance | Lane state is per-sequence |

---

## 11. Маркеры в коде

Новые маркеры для этой работы:
- `MARKER_198.1` — TimelineInstance interface в store
- `MARKER_198.2` — TimelineTrackView props-driven refactor
- `MARKER_198.3` — Dockview multi-timeline wiring
- `MARKER_198.4` — TimelineTabBar deletion
- `MARKER_198.5` — Backend multi-timeline API
- `MARKER_198.6` — FCP7 Skin theme (Phase 3, отложено)
