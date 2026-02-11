# VETKA ROADMAP: Фокус на Будущее
## Дата: 10 февраля 2026 | Начало: Phase 130

---

## VISION

VETKA эволюционирует от **инструмента 3D визуализации** в **полноценную AI-driven knowledge architecture platform** с поддержкой:
- Автономных multi-agent workflows
- Иммерсивной 3D навигации
- Self-improving code quality
- Cross-platform (web + desktop + VR)
- Offline-first архитектуры

---

## WAVE 1: КАЧЕСТВО И НАДЁЖНОСТЬ (Phase 130)
> Цель: Устранить критические gaps, повысить quality gate

```
Phase 130.1  Artifact Approval Gate ────────── КРИТИЧЕСКИЙ
             ├─ 3-level approval (auto/agent/user)
             ├─ DevPanel integration
             └─ 3D camera fly-to на approve request

Phase 130.2  Ralf-Loop Full Cycle ─────────── ВЫСОКИЙ
             ├─ Complete iteration controller
             ├─ LearnerAgent creation
             └─ Termination conditions (score>0.9)

Phase 130.3  Artifact Reactions + CAM ──────── СРЕДНИЙ (quick win)
             ├─ POST /api/cam/reaction
             ├─ Weight boost logic
             └─ Qdrant metadata persistence

Phase 130.4  MCP Server Split ──────────────── ВЫСОКИЙ
             ├─ MCP-UI / MCP-Pipeline / MCP-Files
             ├─ HTTP transport per server
             └─ Shared state via Qdrant
```

**Ожидаемый результат Wave 1:** Quality gate для артефактов, +30-50% code quality, масштабируемый MCP

---

## WAVE 2: ПОИСК И ПАМЯТЬ (Phase 131)
> Цель: Значительно улучшить поиск и управление памятью

```
Phase 131.1  Hybrid Search (RRF) ──────────── ВЫСОКИЙ
             ├─ BM25 keyword indexing
             ├─ RRF fusion algorithm (k=60)
             └─ UI toggle: semantic/keyword/hybrid

Phase 131.2  MGC Hierarchical Memory ──────── ВЫСОКИЙ
             ├─ GenerationalCache class
             ├─ RAM → Qdrant → Disk cascade
             └─ MemoryProxy rate limiting

Phase 131.3  ENGRAM Integration ───────────── СРЕДНИЙ
             ├─ O(1) lookup table
             ├─ CAM surprise filter (<0.5)
             └─ JARVIS-memory compression

Phase 131.4  Multi-Model Council ──────────── СРЕДНИЙ
             ├─ Task type classifier
             ├─ Auto-routing by task
             └─ Parallel council execution

Phase 131.5  BMAD Task Workflow ───────────── СРЕДНИЙ
             ├─ Auto git branch per task
             ├─ Auto-PR creation
             └─ EvalAgent merge decisions
```

**Ожидаемый результат Wave 2:** Гибридный поиск, 30-40% экономия токенов, изолированные task branches

---

## WAVE 3: КОМПРЕССИЯ И ПЕРСОНАЛИЗАЦИЯ (Phase 132)
> Цель: Глубокая компрессия и персонализированный UX

```
Phase 132.1  ELISION 2.0 ─────────────────── ВЫСОКИЙ
             ├─ Semantic compression algorithm (stub → real)
             ├─ Per-tree dictionaries (BPE)
             ├─ CAM-surprise key-scene detection
             └─ Target: 60-70% compression

Phase 132.2  User Memory System ───────────── СРЕДНИЙ
             ├─ User profile в Qdrant
             ├─ Preference extraction
             └─ Cross-session persistence

Phase 132.3  Memory Sync Protocol ─────────── СРЕДНИЙ
             ├─ Snapshot + Diff algorithm
             ├─ Trash layer (90-day recovery)
             └─ Hostess curation dialog
```

**Ожидаемый результат Wave 3:** +20-30% компрессия, персонализация, безопасное управление памятью

---

## WAVE 4: ВИЗУАЛИЗАЦИЯ 2.0 (Phase 133)
> Цель: Новые способы навигации и визуализации

```
Phase 133.1  Matryoshka Clustering ────────── ВЫСОКИЙ
             ├─ HDBSCAN clustering
             ├─ Progressive unfolding
             ├─ Semantic zoom
             └─ Temporal navigation slider

Phase 133.2  Chat as Tree ─────────────────── СРЕДНИЙ
             ├─ Sugiyama DAG для chat history
             ├─ User bubbles + artifact branches
             └─ Knowledge level scoring

Phase 133.3  Unified Search UI ────────────── СРЕДНИЙ
             ├─ Browser-style address bar
             ├─ Query type auto-detection
             └─ Context tree creation

Phase 133.4  Tauri Desktop (начало) ──────── СТРАТЕГИЧЕСКИЙ
             ├─ Tauri project init
             ├─ API layer adaptation
             └─ WGPU rendering setup
```

**Ожидаемый результат Wave 4:** -15-20% cognitive load, новые UX паттерны, начало desktop version

---

## WAVE 5: МАСШТАБ И ГОЛОС (Phase 134-135)
> Цель: Производительность на больших данных, voice-first

```
Phase 134    Large-Scale Optimization ────── ВЫСОКИЙ
             ├─ Octree spatial partitioning
             ├─ InstancedMesh rendering
             ├─ Progressive WebSocket streaming
             └─ Memory pressure auto-culling

Phase 134    Voice Chat & TTS ─────────────── СРЕДНИЙ
             ├─ TTS engine integration
             ├─ STT input (Whisper)
             ├─ Voice UI с waveforms
             └─ Emotional voice modulation

Phase 135    Spatial Memory Palace ─────────── СРЕДНИЙ
             ├─ Method of Loci adaptation
             ├─ Custom spatial clusters
             ├─ Temporal navigation
             └─ 300+ lines JS implementation

Phase 135    Auto-Research Mode ────────────── СРЕДНИЙ
             ├─ Background research scheduler
             ├─ Topic monitoring
             └─ Auto-report generation

Phase 135    Collaborative Editing ─────────── СРЕДНИЙ
             ├─ WebSocket multi-user
             ├─ CRDT for graph ops
             └─ User presence tracking
```

**Ожидаемый результат Wave 5:** 60 FPS для 100k+ nodes, voice interaction, collaborative workflows

---

## WAVE 6: HORIZON (Phase 136-137+)
> Цель: Стратегические features для market differentiation

```
Phase 136    JARVIS Unified Agent
Phase 136    WebGPU Migration (2x perf)
Phase 136    Silence Council Mode
Phase 136    PWA Offline Mode

Phase 137    WebXR VR/AR (Vision Pro, Quest)
Phase 137    Quantum Memory Compression
Phase 137    Emotion-Aware Agents
Phase 137    Advanced KG Data Structures
```

---

## TIMELINE ESTIMATION

```
                    2026
         Feb    Mar    Apr    May    Jun    Jul
         ├──────┼──────┼──────┼──────┼──────┤
Wave 1   ████░░                              Phase 130
Wave 2         ████░░                        Phase 131
Wave 3               ████░░                  Phase 132
Wave 4                     ████░░            Phase 133
Wave 5                           ████████░░  Phase 134-135
Wave 6                                 ──→   Phase 136+
```

*Оценка: ~1 фаза = 1-2 недели при текущем темпе разработки*

---

## KEY METRICS TO TRACK

| Метрика | Текущее | Цель (Phase 135) |
|---------|---------|------------------|
| 3D FPS (10k nodes) | ~40 FPS | 60 FPS |
| Search quality | Semantic only | Hybrid RRF |
| Code quality (EvalAgent) | 70-80% | 90%+ |
| Token compression | 23-43% | 60-70% |
| Max viewable nodes | ~10k | 100k+ |
| Test coverage | 40% | 80%+ |
| MCP concurrent clients | 1 | 10+ |
| Offline capability | None | Full PWA |

---

## ПРИНЦИПЫ ROADMAP

1. **Quality First** — Approval gate и Ralf-loop ПЕРЕД новыми фичами
2. **Incremental** — Каждая wave самодостаточна и deployable
3. **Research-Driven** — Все решения основаны на исследованиях
4. **Performance Budget** — 60 FPS на M4 Pro как non-negotiable
5. **No Breaking Changes** — Каждая фаза обратно совместима
6. **Constitution** — Все изменения следуют 6 принципам VETKA

---

*Этот roadmap — живой документ. Обновляйте по мере продвижения по фазам.*
