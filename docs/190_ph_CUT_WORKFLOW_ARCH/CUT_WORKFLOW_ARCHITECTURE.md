# Phase 190: CUT Workflow Architecture
# Logger → PULSE → Montage Pipeline

**Author:** Danila + Opus
**Date:** 2026-03-17
**Status:** DRAFT — open questions marked with `[?]`

---

## 1. Overview

CUT editor follows a professional post-production workflow:

```
IMPORT → LOGGER → PULSE → MONTAGE → EXPORT
```

Each stage feeds the next. No stage can be skipped (but can be minimal/automatic).

---

## 2. Monitor Architecture

### 2.1 Two Monitors, Two Purposes

```
┌──────────────────────┐  ┌──────────────────────┐
│    SOURCE MONITOR     │  │   PROGRAM MONITOR     │
│                       │  │                       │
│  Shows: selected clip │  │  Shows: active        │
│  from Project Bin     │  │  timeline playback    │
│                       │  │                       │
│  Context:             │  │  Context:             │
│  + Project DAG (MCC)  │  │  + Timeline DAG       │
│    vertical ↑         │  │    horizontal →       │
│    (script structure) │  │    (edit sequence)    │
│                       │  │                       │
│  Tabs: Inspector,     │  │  Tabs: Inspector,     │
│  Script, DAG          │  │  Script, DAG          │
└──────────────────────┘  └──────────────────────┘
```

**Routing rules:**
- Click clip in Project Bin → Source Monitor shows that clip
- Double-click clip → loads into Source Monitor for IN/OUT marking
- Timeline playhead moves → Program Monitor updates
- Source and Program NEVER show the same feed (unless user explicitly links them)

### 2.2 Project DAG (Source Monitor side)

Direction: **bottom → up** (MCC tree structure)

```
         cut_3 (latest)
           ↑
         cut_2
           ↑
         cut_1 (first assembly)
           ↑
     ┌─────┼─────┐
   Scene1  Scene2  Scene3    ← Logger output
     ↑      ↑       ↑
   clips   clips   clips     ← Raw material
```

Origin: extracted from script/scenario OR inversely — material → AI generates script → script grows DAG.

### 2.3 Timeline DAG (Program Monitor side)

Direction: **left → right** (horizontal, time-based)

Shows the active timeline as a DAG where each node = clip/segment with connections showing edit decisions.

---

## 3. Timeline Architecture

### 3.1 Multi-Timeline Display

**Base mode: 2 parallel timelines visible simultaneously**

```
┌─────────────────────────────────────────────────────┐
│ TIMELINE 1 (active) ★                               │
│ ▓▓▓▓▓│▓▓▓▓▓▓▓│▓▓▓│▓▓▓▓▓▓▓▓▓│▓▓▓▓│▓▓▓▓▓▓          │
│ Sc1   │ Sc2    │Sc3│  Sc4     │Sc5 │ Sc6            │
├─────────────────────────────────────────────────────┤
│ TIMELINE 2 (AI variant / previous version)          │
│ ░░░░░│░░░░░░░░░│░░░░░│░░░░░│░░░░░░░░               │
│ Sc1   │  Sc2     │ Sc3  │Sc4 │  Sc5                 │
└─────────────────────────────────────────────────────┘
```

**Rules:**
- Active timeline (★) → routed to Program Monitor
- Both timelines scroll together (synced playhead)
- Click on Timeline 2 → it becomes active (★ moves)
- Each timeline = a `cut_N` version in Project DAG

### 3.2 Tabs for 3+ Timelines

When more than 2 timelines exist:
- 2 are always visible in parallel view
- Others accessible via tabs above the timeline area
- Drag tab → swap into one of the two visible slots
- Tab shows: `cut_1 (Logger)` / `cut_2 (PULSE)` / `cut_3 (Manual)` etc.

### 3.3 Timeline Versioning

Each version is a `cut_N` node in the Project DAG (MCC):

| Version | Source | Description |
|---------|--------|-------------|
| `cut_1` | Logger | First assembly — clips laid out by scenes |
| `cut_2` | PULSE | AI-refined — best takes selected per scene |
| `cut_3` | Manual | Editor's adjustments to cut_2 |
| `cut_N` | Any | Each save/branch creates new version |

**No destructive edits.** Every change = new cut_N. Previous versions always accessible.

---

## 4. Workflow Stages

### 4.1 LOGGER (Stage 1 — before PULSE)

**What:** Organize raw material into scenes. This is the film Logger's role — the person who catalogs footage.

**Two modes:**

#### Mode A: Scripted (script → material)
```
INPUT:  Script/scenario document + raw clips
FLOW:   Script parsed → scenes identified →
        clips matched to scenes (auto + manual)
OUTPUT: Scene bins populated, DAG shows script structure
```

1. User imports/writes script in Script panel
2. Script parser extracts scenes (scene headings, descriptions)
3. AI suggests clip-to-scene assignments based on:
   - Transcript matching (speech ↔ dialogue)
   - Visual matching (location, characters) [?]
   - Metadata (slate info, file naming conventions) [?]
4. User reviews, drags clips between scenes, confirms

#### Mode B: Documentary (material → script)
```
INPUT:  Raw clips (no script)
FLOW:   AI analyzes material → generates script/structure →
        script grows DAG
OUTPUT: Auto-generated script + scene bins + DAG
```

1. User imports clips (already done — import pipeline)
2. AI analyzes all clips: transcripts, visual content, audio
3. AI proposes scene structure + draft script
4. User edits script → DAG updates accordingly
5. Iterative: edit script ↔ reorganize clips

#### Logger Output
- Each clip tagged with scene assignment
- Scene bins in Project panel
- Project DAG (MCC) reflects scene hierarchy
- `cut_1` timeline = first assembly (scenes in script order)

### 4.2 PULSE (Stage 2 — per-scene analysis)

**Prerequisite:** Logger has assigned clips to scenes.

**What:** PULSE analyzes each scene individually, not the whole project blindly.

Per scene, PULSE evaluates:
- Best takes (performance quality, technical quality)
- Key moments / highlights (favorite markers)
- Audio quality ranking
- Emotional beats (from transcript + audio tone)
- Rhythm/pacing suggestions

**Output:**
- Ranked clips per scene (with scores + reasons)
- Suggested IN/OUT points per clip
- Favorite time markers on best moments
- `cut_2` timeline = AI-refined assembly

### 4.3 MONTAGE (Stage 3 — transparent, not black box)

**Key principle: NO BLACK BOX.**

AI montage suggestions are NOT a floating panel with an "Apply" button.
Instead:

1. AI generates alternative timeline → visible as `cut_N` (parallel timeline)
2. Editor sees BOTH timelines simultaneously
3. Can compare clip-by-clip: "why did AI choose this take?"
4. Can cherry-pick: drag a clip from AI timeline to editor's timeline
5. Can accept whole AI timeline as new base

**Montage modes** (from 185.3, still valid):
- **Favorites Cut** — uses only clips with favorite markers
- **Script Cut** — follows script order strictly
- **Music Cut** — cuts on beat/rhythm markers

Each mode creates a new `cut_N` visible as parallel timeline.

---

## 5. Data Flow Summary

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  IMPORT  │────→│  LOGGER  │────→│  PULSE   │────→│ MONTAGE  │
│          │     │          │     │          │     │          │
│ Raw clips│     │ Clips →  │     │ Per-scene│     │ Alt      │
│ metadata │     │ Scenes   │     │ analysis │     │ timelines│
│ proxies  │     │ Script   │     │ Rankings │     │ cut_N    │
│          │     │ DAG seed │     │ Favorites│     │ versions │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                │                 │
                      ▼                ▼                 ▼
                   cut_1            cut_2             cut_N
                 (assembly)      (AI-refined)      (variants)
                      │                │                 │
                      └────────┬───────┘                 │
                               │                         │
                         Project DAG (MCC)               │
                         vertical ↑                      │
                         all versions visible ───────────┘
```

---

## 6. Open Questions [?]

1. **Logger clip matching:** What signals beyond transcript? Vision API for location matching? Slate/clapperboard detection?
2. **Scene granularity:** Is a "scene" always a script scene, or can it be a beat/section within a scene?
3. **PULSE scope:** Does PULSE need Logger output, or can it run independently on any set of clips? (Recommendation: require Logger, even minimal auto-log)
4. **Timeline diff view:** When comparing two timelines, show per-clip diff (what changed, what's new, what's removed)?
5. **Collaborative Logger:** Can multiple people log simultaneously (multi-agent)?
6. **cut_N storage:** Each version = full timeline copy? Or delta from previous? (Affects DAG node size)

---

## 7. Related Tasks

| Task ID | Title | Status | Dependency |
|---------|-------|--------|------------|
| tb_1773714867_26 | BUG: Source vs Program Monitor | pending | — |
| tb_1773714871_27 | BUG: Playhead jumps to start | pending | — |
| tb_1773714876_28 | ARCH: Multi-timeline parallel display | pending | this doc |
| tb_1773714882_29 | ARCH: Logger stage | pending | this doc |
| tb_1773616872_32 | 185.2: Montage Suggestions Panel | **ON HOLD** | Logger + Multi-timeline first |
| tb_1773616876_33 | 185.3: Auto-Montage Modes | pending | rethink per this doc |

---

## 8. Implementation Priority

```
Phase 1: Fix bugs (P1)
  → Source vs Program Monitor routing
  → Playhead play-from-current-position

Phase 2: Multi-timeline foundation (P2)
  → 2 parallel timelines visible
  → cut_N versioning in Project DAG
  → Tabs for 3+ timelines

Phase 3: Logger (P2)
  → Script parser + scene extraction
  → Clip-to-scene assignment (manual + AI assist)
  → cut_1 auto-assembly

Phase 4: PULSE per-scene (P3)
  → PULSE receives scene boundaries from Logger
  → Per-scene ranking + favorites
  → cut_2 generation as parallel timeline

Phase 5: Transparent Montage (P3)
  → Montage modes generate cut_N as new timeline
  → Timeline comparison/diff view
  → Cherry-pick between timelines
```
