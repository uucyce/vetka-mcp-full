# CUT Data Model
# Структура данных DAG Project

**Date:** 2026-03-18
**Basis:** CUT_TARGET_ARCHITECTURE.md
**Audience:** Разработчики, архитектор данных
**Status:** DRAFT v0.1 — MVP scope

---

## Канонический принцип

> **In CUT, the project is stored as a graph of narrative, semantic, and media nodes.**
> **Timelines are queries and projections over that graph.**

Everything in CUT is a node or an edge.
Timeline is not separate storage; it is a projection/query over the graph.

---

## 1. Верхнеуровневая схема

```
Project
  ├── Script Spine (SceneChunk nodes)
  ├── Lore Graph (Character / Location / Object nodes)
  ├── Media Graph (SourceFile / Media nodes)
  ├── Analysis Layer (AI annotations)
  └── Timeline Projections (ClipUsage paths)
```

```
              ┌────────────┐
              │  Project   │
              └─────┬──────┘
                    │ contains
                    ▼
              ┌────────────┐        links_to        ┌────────────┐
              │ SceneChunk │───────────────────────►│ LoreNode   │
              └─────┬──────┘                        └────────────┘
                    │ has_media
                    ▼
              ┌────────────┐        derived_from    ┌────────────┐
              │ MediaNode  │───────────────────────►│ SourceFile │
              └─────┬──────┘                        └────────────┘
                    │ selected_into
                    ▼
              ┌────────────┐
              │ Timeline   │
              └─────┬──────┘
                    │ contains
                    ▼
              ┌────────────┐
              │ ClipUsage  │
              └────────────┘
```

---

## 2. Node Types (7 основных + 3 специальных)

### 2.1 ProjectNode

Корень проекта.

```
ProjectNode
  project_id          : uuid
  title               : string
  created_at          : timestamp
  updated_at          : timestamp
  settings            : json
  default_view        : "dag" | "timeline"
  active_timeline_id  : uuid | null
```

### 2.2 ScriptChunkNode

Главная единица драматургии. Центральный узел DAG.

```
ScriptChunkNode
  chunk_id            : string        // SCN_01, SCN_02...
  script_text         : string
  scene_heading       : string | null // "INT. CAFE - DAY"
  chunk_type          : "scene" | "paragraph" | "reconstructed" | "improvised"
  start_sec_est       : float         // from page-timer (1 page = 60 sec)
  duration_sec_est    : float
  confidence          : float 0..1
  draft_group_id      : string | null // groups variants of same scene
  chronology_index    : int           // order in spine
  bpm_symbolic        : float         // Layer A: rule-based event density
  bpm_semantic        : float | null  // Layer B: JEPA energy spike
  dramatic_function   : string | null
  pendulum_hint       : float -1..1
```

### 2.3 LoreNode

Персонажи, локации, объекты, темы.

```
LoreNode
  lore_id             : uuid
  lore_type           : "character" | "location" | "object" | "theme" | "motif"
  name                : string
  description         : string
  notes               : string
  tags                : string[]
  generation_refs     : string[]      // image refs / prompt refs for AI generation
  relationships_summary : string
```

### 2.4 MediaNode

Логическая монтажная сущность (не обязательно целый файл).

```
MediaNode
  media_id            : uuid
  media_type          : "video" | "audio" | "image" | "generated_video" | "transcript_segment"
  source_file_id      : uuid
  in_tc               : timecode
  out_tc              : timecode
  duration_sec        : float
  transcript_text     : string | null
  waveform_ref        : string | null
  thumbnail_ref       : string | null
  is_generated        : bool
  shot_scale_auto     : "CU" | "MCU" | "MS" | "WS" | "EWS" | null
  shot_scale_manual   : "CU" | "MCU" | "MS" | "WS" | "EWS" | null
  shot_scale_final    : computed (manual if exists, else auto)
  shot_scale_confidence : float 0..1
```

**Важно:** MediaNode ≠ SourceFile. Один SourceFile может содержать несколько MediaNodes (дубли, сегменты, ADR-куски).

### 2.5 SourceFileNode

Физический исходник на диске.

```
SourceFileNode
  source_file_id      : uuid
  path                : string
  file_name           : string
  file_type           : string
  codec               : string
  resolution          : string        // "1920x1080"
  fps                 : float
  audio_channels      : int
  file_hash           : string
  created_at          : timestamp
  imported_at         : timestamp
```

### 2.6 TimelineNode

Линейная развёртка DAG. Каждый timeline = путь через Multiverse.

```
TimelineNode
  timeline_id         : uuid
  timeline_type       : "logger" | "pulse_rough" | "editor" | "final"
  title               : string        // "project_cut-02"
  based_on_timeline_id : uuid | null
  branch_path_signature : string      // hash of chosen SCN path
  created_by          : "user" | "pulse" | "logger"
  created_at          : timestamp
  locked              : bool
```

### 2.7 ClipUsageNode

Использование MediaNode на конкретном Timeline. Timeline не копирует — ссылается.

```
ClipUsageNode
  clip_usage_id       : uuid
  timeline_id         : uuid
  media_id            : uuid
  script_chunk_id     : string | null // SCN_XX this clip serves
  track_type          : "video" | "audio" | "script"
  track_index         : int           // V1=0, V2=1, A1=0, A2=1...
  start_sec_timeline  : float
  end_sec_timeline    : float
  source_in           : timecode
  source_out          : timecode
  transition_in       : string | null
  transition_out      : string | null
  selection_reason    : string | null // "pulse_best_take" | "user_manual" | "logger_auto"
```

### 2.8 AnalysisNode (специальный)

Результаты AI/Logger/PULSE. **Не перетирать — хранить историю.**

```
AnalysisNode
  analysis_id         : uuid
  target_node_id      : uuid          // any node
  analysis_type       : "shot_scale" | "object_detection" | "character_match" | "bpm" | "similarity"
  model_name          : string        // "qwen_local", "jepa_vision", "whisper"
  confidence          : float 0..1
  payload_json        : json          // {label: "MS", objects: [...], ...}
  created_at          : timestamp
```

**Принцип:** Один MediaNode может иметь несколько AnalysisNodes от разных моделей.
Это даёт: трассируемость, сравнение моделей, обучение на правках редактора.

### 2.9 MarkerNode (специальный)

```
MarkerNode
  marker_id           : uuid
  marker_type         : "standard" | "favorite_positive" | "favorite_negative" | "note" | "pulse_scene"
  attached_to_node_id : uuid          // MediaNode or SceneChunk
  timecode            : timecode
  text                : string | null
  created_by          : "user" | "pulse"
  color               : string | null
```

### 2.10 FeedbackEvent (специальный — learning loop)

```
FeedbackEvent
  feedback_id         : uuid
  actor               : "user"
  target_node_id      : uuid
  target_type         : "media" | "scene" | "lore" | "analysis"
  action              : "accept" | "reject" | "relabel" | "re-link"
  previous_value      : json
  new_value           : json
  reason_text         : string | null
  created_at          : timestamp
```

Даёт: дообучение, ranking preferences, better PULSE decisions.

---

## 3. Edge Types (9 основных)

### Structural
| Edge | From | To | Meaning |
|------|------|----|---------|
| `contains` | Project | Timeline, SceneChunk, SourceFile | Ownership |

### Narrative (Script Spine)
| Edge | From | To | Meaning |
|------|------|----|---------|
| `next_scene` | SceneChunk | SceneChunk | Spine order (SCN_01 → SCN_02) |
| `branches_to` | SceneChunk | SceneChunk | Multiverse split (SCN_02 → SCN_02A, SCN_02B) |
| `merges_into` | SceneChunk | SceneChunk | Branches rejoin (SCN_02A, SCN_02B → SCN_03) |

### Semantic
| Edge | From | To | Meaning |
|------|------|----|---------|
| `mentions` | SceneChunk | LoreNode | Script references character/location |
| `relates_to` | LoreNode | LoreNode | Character relationships, location links |

### Media
| Edge | From | To | Meaning |
|------|------|----|---------|
| `has_media` | SceneChunk | MediaNode | Clips belonging to scene |
| `derived_from` | MediaNode | SourceFileNode | Physical file source |
| `similar_to` | MediaNode | MediaNode | Semantic/visual similarity |

### Timeline
| Edge | From | To | Meaning |
|------|------|----|---------|
| `selected_into` | MediaNode | TimelineNode | Clip used in this cut (via ClipUsageNode) |

---

## 4. Multiverse DAG на уровне данных

```
SCN_01
  │ next_scene
  ▼
SCN_02
  ├── branches_to ──► SCN_02A (Draft 1)
  ├── branches_to ──► SCN_02B (Draft 2)
  └── branches_to ──► SCN_02C (Improvised)
                         │
                         └── merges_into ──► SCN_03
```

Timeline хранит **путь, не копию**:
```
Timeline cut_01:
  path = [SCN_01, SCN_02B, SCN_03, SCN_04_V2, SCN_05]
```

---

## 5. Пример: SCN_02 со всеми связями

```
SceneChunkNode: SCN_02
  scene_heading: "INT. CAFE - EVENING"
  start_sec_est: 70
  chunk_type: "scene"
  │
  ├── next_scene ──────► SCN_03
  ├── branches_to ─────► SCN_02A (draft 1, classic)
  ├── branches_to ─────► SCN_02B (draft 2, rewritten)
  │
  ├── mentions ────────► ANNA (character)
  ├── mentions ────────► MARK (character)
  ├── mentions ────────► CAFE (location)
  │
  ├── has_media ───────► TAKE_A_01 (video, camera A, take 1)
  ├── has_media ───────► TAKE_B_01 (video, camera B, take 1)
  ├── has_media ───────► ADR_02 (audio, ADR)
  ├── has_media ───────► MUSIC_CUE_02 (audio, music)
  │
  ├── analyzed_by ─────► Analysis #1 (shot_scale, qwen, MS, 0.82)
  ├── analyzed_by ─────► Analysis #2 (objects, yolo, [cup, table], 0.91)
  │
  └── markers ─────────► Marker #1 (favorite_positive, user, tc=01:12:05)
```

---

## 6. MVP Minimum (Phase 1-2)

### MVP Node Types (обязательные)
- ProjectNode
- ScriptChunkNode
- LoreNode
- SourceFileNode
- MediaNode
- TimelineNode
- ClipUsageNode
- MarkerNode

### MVP Edge Types (обязательные)
- contains
- next_scene
- branches_to
- merges_into
- mentions
- has_media
- derived_from
- selected_into
- similar_to

### Отложенные на Phase 3+
- AnalysisNode (пока shot_scale хранится в MediaNode напрямую)
- FeedbackEvent (пока нет learning loop)
- VariantNode (пока branches_to покрывает)

---

## 7. ER-схема (минимальная)

```
Project
├── ScriptChunkNode*
├── LoreNode*
├── SourceFileNode*
├── MediaNode*
├── TimelineNode*
├── MarkerNode*
└── AnalysisNode*

ScriptChunkNode
├── mentions ─────────► LoreNode
├── has_media ────────► MediaNode
├── next_scene ───────► ScriptChunkNode
├── branches_to ──────► ScriptChunkNode
└── merges_into ──────► ScriptChunkNode

MediaNode
├── derived_from ─────► SourceFileNode
├── similar_to ───────► MediaNode
└── analyzed_by ──────► AnalysisNode

TimelineNode
└── contains ─────────► ClipUsageNode

ClipUsageNode
├── uses ─────────────► MediaNode
└── refers_to ────────► ScriptChunkNode
```
