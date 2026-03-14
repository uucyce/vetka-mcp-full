# Phase 179 — PULSE Conductor: Cinema Symphony Engine

> **Vision:** PULSE = дирижёр трёх ритмов. Не параллельный энкодер, а центральный интерпретатор.
> **Source:** `docs/VETKA_JEPA_Architecture_v2.docx`, `docs/pulse_conductor_flow_v2.svg`
> **Date:** 2026-03-13 | **Author:** Данила Гулин + Claude Opus 4.6

---

## 0. Контекст: что уже построено

### CUT Backend (Phase 170-173) ✅
| Компонент | Файл | Статус |
|-----------|------|--------|
| Timeline ops (ripple, insert, overwrite, split) | `cut_routes.py` | ✅ Done |
| Undo/Redo (100 levels, persistence) | `cut_undo_redo.py` | ✅ Done |
| Scene detection (histogram chi-squared) | `cut_scene_detector.py` | ✅ Done (но только гистограммы) |
| Montage ranker (5 signals) | `cut_montage_ranker.py` | ✅ Done (но без PULSE signals) |
| Timeline events (SocketIO + WS) | `cut_timeline_events.py` | ✅ Done |
| Proxy worker (FFmpeg transcode) | `cut_proxy_worker.py` | ✅ Done |
| Music sync contract | `cut_routes.py` Phase 171 | ✅ Done |
| Scene graph | `SceneGraph.tsx` | ✅ Done |

### JEPA Infrastructure ✅
| Компонент | Файл | Статус |
|-----------|------|--------|
| JEPA Runtime (text embeddings + whitening) | `jepa_runtime.py` | ✅ Working |
| V-JEPA Integrator (video/audio extraction) | `jepa_integrator.py` | ✅ Working |
| JEPA HTTP Server (port 8099) | `jepa_http_server.py` | ✅ Working |
| MCC JEPA Adapter (fallback chain) | `mcc_jepa_adapter.py` | ✅ Working |
| JEPA → Qdrant storage | `jepa_to_qdrant.py` | ✅ Working |

### PULSE v0.1 (Standalone)
| Компонент | Статус |
|-----------|--------|
| BPM/key/Camelot estimation | MVP в `pulse/` |
| Scale inference (windowed) | Spec ready |
| Genre/Scale CSV matrix | ✅ Есть (`scale-genge-numbers.csv`) |
| Gesture synth | MVP |

### Что НЕ СВЯЗАНО (gaps)
1. Scene detector не использует V-JEPA latent space
2. Montage ranker не получает PULSE rhythm/mood signals
3. PULSE не подключён к CUT pipeline
4. DAG VETKA не работает как "партитура"
5. Нет Camelot path planning для последовательности сцен
6. Нет energy critics (LeCun)

---

## 1. Архитектура: Conductor Flow

```
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ Script/Brief │  │Video Material │  │Audio (if any)│
│ Narrative BPM│  │Visual BPM    │  │Sound BPM     │
│ Pendulum     │  │V-JEPA2       │  │librosa       │
│ min ↔ maj    │  │In-frame move │  │Key+downbeats │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └────────────┬────┴────────────────┘
                    ▼
         ┌───────────────────┐
         │  PULSE (conductor)│
         │ Camelot ↔ Itten   │
         │ Scale → Cinema    │
         └────────┬──────────┘
                  ▼
         ┌───────────────────┐
         │  Score (partition) │
         │ camelot_key + scale│
         │ pendulum + energy  │
         │ dramatic_function  │
         └────────┬──────────┘
                  ▼
         ┌───────────────────┐
         │ DAG = orchestral   │
         │   score            │
         │ Nodes=instruments  │
         │ Edges=Camelot harm │
         └──┬─────┬─────┬────┘
            ▼     ▼     ▼
      ┌────────┐┌────┐┌──────┐
      │Music   ││Cut ││Color │
      │select  ││place││grade│
      │Camelot ││beats││Itten│
      └────────┘└────┘└──────┘
                  ▼
         Finished film = symphony
```

---

## 2. Sprints: от ядра к периферии

### Гармонизация с другими фазами

| Фаза | Статус | Зависимости с 179 |
|------|--------|-------------------|
| **173 CUT backend** | ✅ Done (6/6) | 179 расширяет montage_ranker + scene_detector |
| **173 CUT frontend** | 15 pending tasks | Параллельно с 179. Codex делает UI, 179 добавляет PULSE endpoints |
| **176 MCC Sprint** | In Progress | Независимо. MCC infra не блокирует PULSE |
| **170 Scene Graph** | Partial | 179.S2 добавляет Camelot edges в scene graph |
| **152 Stats** | Wave 2 pending | Независимо |
| **177 LiteRT** | 2 pending tasks | 179 может использовать LiteRT для V-JEPA inference |

### Delegation Map (corrected 2026-03-14)

> **NOTE:** Dragon Silver (MYCELIUM pipeline) НЕ ИСПОЛЬЗУЕТСЯ — Codex ещё допиливает MYCELIUM (Phase 176).
> Все backend задачи на Opus. Grok research через пользователя (промпт → relay).

| Agent | Зона | Tasks | Фокус Phase 179 |
|-------|------|-------|-----------------|
| **Opus (я)** | Весь backend Python | 16 tasks | Conductor core, critics, V-JEPA, endpoints, CSV loader, tests |
| **Codex** | Frontend .tsx | 6 tasks | PulseOverlay, CamelotWheel, Pendulum, EnergyCritics, UndoHistory, IttenAdvisor |
| **Grok (через user)** | Research validation | 2 tasks | Scale→Genre validation on films, energy critics validation |
| **Haiku scouts** | Code audit recon | 3 tasks | PULSE hooks, V-JEPA API, CSV inventory (via Agent tool) |

---

### Sprint 0: Recon (Grok + Haiku scouts)
> **Длительность:** 1 день | **Кто:** Grok (research) + Haiku (code audit)

| # | Task | Agent | Deliverable |
|---|------|-------|-------------|
| 179.0A | Validate Scale→Genre matrix on 10 real films | Grok | Confirmation/corrections to `pulse_cinema_matrix.csv` |
| 179.0B | Audit existing PULSE code paths in `extractor_registry.py` | Haiku scout | Map of all PULSE hooks + their current status |
| 179.0C | Check V-JEPA2 prediction error API availability | Haiku scout | Can we get prediction_error curve from existing `jepa_integrator.py`? |
| 179.0D | Inventory existing Camelot/Itten data in `pulse/docs/` CSVs | Haiku scout | Structured summary of available data |

---

### Sprint 1: PULSE Conductor Core (Opus + Dragon)
> **Длительность:** 2-3 дня | **Кто:** Opus (architect + core), Dragon Silver (helpers)
> **Зависимости:** Sprint 0 recon complete
> **Цель:** `pulse_conductor.py` принимает 3 BPM → выдаёт Score

| # | Task | Agent | File | Priority |
|---|------|-------|------|----------|
| 179.1 | `pulse_cinema_matrix.py` — Load & query Scale→Cinema→Drama→Pendulum→Counterpoint→Itten from CSV | Dragon Silver | `src/services/pulse_cinema_matrix.py` | P0 |
| 179.2 | `pulse_conductor.py` — Central conductor: accepts 3 BPM signals → produces Score per scene | Opus | `src/services/pulse_conductor.py` | P0 |
| 179.3 | `camelot_path_planner.py` — Path through Camelot wheel for scene sequence, validates pendulum balance | Opus | `src/services/camelot_path_planner.py` | P0 |
| 179.4 | Wire PULSE Score into `cut_montage_ranker.py` — add `rhythm_confidence` (6th signal) + `mood_alignment` (7th signal) | Opus | `src/services/cut_montage_ranker.py` | P0 |
| 179.5 | `script_rhythm_analyzer.py` — Parse script/brief → dramatic_function + pendulum_position per scene | Dragon Silver | `src/services/script_rhythm_analyzer.py` | P1 |
| 179.6 | REST endpoints: `POST /api/cut/pulse/analyze`, `GET /api/cut/pulse/score/{scene_id}`, `GET /api/cut/pulse/camelot-path` | Opus | `src/api/routes/cut_routes.py` | P0 |
| 179.7 | Tests Sprint 1 | Sonnet | `tests/phase179/test_pulse_conductor.py` | P0 |

**Score dataclass (output of conductor):**
```python
@dataclass
class PulseScore:
    scene_id: str
    camelot_key: str        # e.g. "8A" (Am)
    scale: str              # e.g. "aeolian"
    pendulum_position: float  # -1.0 (minor) to +1.0 (major)
    energy_profile: str     # "low→building→peak→release"
    dramatic_function: str  # "Rising tension", "Catharsis", etc.
    counterpoint_pair: str  # "ionian" (for contrast)
    visual_bpm: float       # from V-JEPA or FFmpeg
    narrative_bpm: float    # from script analysis
    sound_bpm: float | None # from librosa (if audio exists)
    itten_palette: list[str]  # ["Yellow-Green", "Blue"]
    confidence: float       # 0.0-1.0
```

---

### Sprint 2: V-JEPA + Energy Critics (Opus + Grok)
> **Длительность:** 2-3 дня | **Кто:** Opus (critics), Grok (validation)
> **Зависимости:** Sprint 1 conductor core
> **Цель:** V-JEPA prediction error → visual BPM. Energy critics для оптимизации монтажа.

| # | Task | Agent | File | Priority |
|---|------|-------|------|----------|
| 179.8 | `vjepa2_bpm_extractor.py` — Extract prediction error curve from V-JEPA2 → convert to visual BPM + peaks | Opus | `src/services/vjepa2_bpm_extractor.py` | P1 |
| 179.9 | Upgrade `cut_scene_detector.py` — hybrid mode: histogram + V-JEPA latent distance (fallback to histogram if JEPA unavailable) | Opus | `src/services/cut_scene_detector.py` | P1 |
| 179.10 | `energy_critics.py` — 5 LeCun-style energy functions (Music-Scene Sync, Pendulum Balance, Camelot Proximity, Script-Visual Match, Energy Contour) | Opus | `src/services/energy_critics.py` | P1 |
| 179.11 | `counterpoint_detector.py` — Detect sync vs counterpoint in scene-music pairing (alignment field in DAG) | Dragon Silver | `src/services/counterpoint_detector.py` | P2 |
| 179.12 | Validate energy critics on 3 real film sequences (Grok research) | Grok | `docs/179_ph_PULSE_CONDUCTOR/GROK_VALIDATION_ENERGY_CRITICS.md` | P1 |
| 179.13 | Tests Sprint 2 | Sonnet | `tests/phase179/test_energy_critics.py` | P1 |

**Energy function interface:**
```python
class EnergyFunction(Protocol):
    def compute(self, state: TimelineState, score: PulseScore) -> float:
        """Lower energy = better. 0.0 = perfect, 1.0 = worst."""
        ...
```

---

### Sprint 3: CUT Integration + Frontend (Opus + Codex)
> **Длительность:** 3-4 дня | **Кто:** Opus (backend wiring), Codex (frontend)
> **Зависимости:** Sprint 1+2 backend, Phase 173 frontend basics
> **Цель:** PULSE visible in CUT editor UI

| # | Task | Agent | File | Priority |
|---|------|-------|------|----------|
| 179.14 | Wire PULSE Score into scene graph edges — Camelot harmony as edge weight | Opus | `src/api/routes/cut_routes.py` | P1 |
| 179.15 | PULSE timeline overlay — visual BPM curve + beat markers on timeline | Codex | `client/src/components/cut/PulseOverlay.tsx` | P1 |
| 179.16 | Camelot wheel mini-view — current scene position on wheel, path visualization | Codex | `client/src/components/cut/CamelotWheel.tsx` | P2 |
| 179.17 | Pendulum indicator — min↔maj balance for current sequence | Codex | `client/src/components/cut/PendulumIndicator.tsx` | P2 |
| 179.18 | Energy critic scores panel — show 5 critic scores for current edit | Codex | `client/src/components/cut/EnergyCritics.tsx` | P2 |
| 179.19 | Undo History panel (Premiere-style) — scrollable list, click-to-jump | Codex | `client/src/components/cut/UndoHistory.tsx` | P1 |
| 179.20 | Tests Sprint 3 | Sonnet | `tests/phase179/test_pulse_integration.py` | P1 |

---

### Sprint 4: Itten Color + Polish (Dragon + Codex)
> **Длительность:** 2 дня | **Кто:** Dragon Silver (backend), Codex (frontend)
> **Зависимости:** Sprint 3
> **Цель:** Цветокоррекция по scale + polish. **ЭКСПЕРИМЕНТАЛЬНЫЙ** — может быть отложен.

| # | Task | Agent | File | Priority |
|---|------|-------|------|----------|
| 179.21 | `itten_grading_advisor.py` — Scale → Itten vertex colors → LUT suggestion | Dragon Silver | `src/services/itten_grading_advisor.py` | P2 |
| 179.22 | Color grading suggestion panel in CUT UI | Codex | `client/src/components/cut/IttenAdvisor.tsx` | P3 |
| 179.23 | Music selection advisor — filter library by Camelot proximity to scene | Dragon Silver | `src/services/music_advisor.py` | P2 |
| 179.24 | ISI (Interval Spread Index) metric — experimental | Dragon Silver | `src/services/pulse_cinema_matrix.py` | P3 |
| 179.25 | Full integration test: import media → PULSE analyze → auto-score → cuts on beats → export | Opus + Sonnet | `tests/phase179/test_full_pipeline.py` | P1 |

---

## 3. Зависимости и параллельность

```
Sprint 0 (Recon) ──────────────────────────────── 1 день
    │
    ▼
Sprint 1 (Conductor Core) ─────────────────────── 2-3 дня
    │                    ║
    │    ┌───────────────╨──────────────────┐
    │    │ Phase 173 Frontend (Codex)       │
    │    │ параллельно: timeline UI,        │
    │    │ undo UI, clip ops, audio engine  │
    │    └──────────────────────────────────┘
    ▼
Sprint 2 (V-JEPA + Critics) ───────────────────── 2-3 дня
    │
    ▼
Sprint 3 (CUT Integration + Frontend) ─────────── 3-4 дня
    │         ↑ needs 173 frontend basics done
    ▼
Sprint 4 (Itten + Polish) ─────────────────────── 2 дня [EXPERIMENTAL]
```

**Критический путь:** Sprint 0 → 1 → 2 → 3
**Параллельный поток:** Phase 173 frontend (Codex) runs alongside Sprints 1-2

---

## 4. Файлы: что создаётся

### Новые файлы (backend)
| File | Sprint | Lines (est) | Author |
|------|--------|-------------|--------|
| `src/services/pulse_cinema_matrix.py` | S1 | ~200 | Dragon Silver |
| `src/services/pulse_conductor.py` | S1 | ~350 | Opus |
| `src/services/camelot_path_planner.py` | S1 | ~250 | Opus |
| `src/services/script_rhythm_analyzer.py` | S1 | ~200 | Dragon Silver |
| `src/services/vjepa2_bpm_extractor.py` | S2 | ~250 | Opus |
| `src/services/energy_critics.py` | S2 | ~300 | Opus |
| `src/services/counterpoint_detector.py` | S2 | ~150 | Dragon Silver |
| `src/services/itten_grading_advisor.py` | S4 | ~180 | Dragon Silver |
| `src/services/music_advisor.py` | S4 | ~150 | Dragon Silver |
| `data/pulse_cinema_matrix.csv` | S1 | ~50 rows | Grok → manual review |

### Модифицируемые файлы
| File | Sprint | Change |
|------|--------|--------|
| `src/services/cut_montage_ranker.py` | S1 | +2 signals (rhythm, mood) |
| `src/services/cut_scene_detector.py` | S2 | +V-JEPA hybrid mode |
| `src/api/routes/cut_routes.py` | S1+S2+S3 | +PULSE endpoints |

### Новые файлы (frontend) — Codex
| File | Sprint | Author |
|------|--------|--------|
| `client/src/components/cut/PulseOverlay.tsx` | S3 | Codex |
| `client/src/components/cut/CamelotWheel.tsx` | S3 | Codex |
| `client/src/components/cut/PendulumIndicator.tsx` | S3 | Codex |
| `client/src/components/cut/EnergyCritics.tsx` | S3 | Codex |
| `client/src/components/cut/UndoHistory.tsx` | S3 | Codex |
| `client/src/components/cut/IttenAdvisor.tsx` | S4 | Codex |

### Тесты
| File | Sprint |
|------|--------|
| `tests/phase179/test_pulse_cinema_matrix.py` | S1 |
| `tests/phase179/test_pulse_conductor.py` | S1 |
| `tests/phase179/test_camelot_path.py` | S1 |
| `tests/phase179/test_energy_critics.py` | S2 |
| `tests/phase179/test_vjepa_bpm.py` | S2 |
| `tests/phase179/test_pulse_integration.py` | S3 |
| `tests/phase179/test_full_pipeline.py` | S4 |

---

## 5. Метрики успеха

| Metric | Target | Как измерить |
|--------|--------|-------------|
| PULSE Score generation time | < 2s per scene | Benchmark on 10-scene project |
| Energy critic agreement with human editor | > 60% | Grok validates on 3 films |
| V-JEPA scene detection accuracy vs histogram | +15% better boundaries | A/B test on varied content |
| Montage ranker improvement with PULSE signals | measurably better ranking | Before/after on same material |
| Camelot path coherence | No jumps > ±3 keys without flag | Automatic validation |

---

## 6. Риски и mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| V-JEPA2 not available locally | No visual BPM | Fallback to FFmpeg histogram (already works) |
| Scale→Genre matrix too speculative | Bad suggestions | Start with P0 only (BPM + Camelot path), defer genre/color mapping |
| PULSE standalone app not integrated | No sound BPM | librosa fallback in extractor_registry (already exists) |
| Itten color grading not validated | Misleading LUTs | Mark as EXPERIMENTAL, never auto-apply |
| Too many new modules | Complexity explosion | Each module is standalone with clear interface (PulseScore dataclass) |

---

## 7. Открытые вопросы (перенесены из Architecture v2)

1. **ISI hypothesis** — requires validation on real films (Sprint 4, P3)
2. **Reverse mapping color → scale** — deferred to future phase
3. **Reconstruction without script** — PULSE from material only (documentary mode), Sprint 2+ feature
4. **Formula evolution** — the matrix is a tool, not a law. Counterpoint is always allowed.
