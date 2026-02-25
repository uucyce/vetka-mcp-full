# MCC Architecture Diagram

## Status and Canonical Plan
- This document remains the UX/flow diagram reference.
- Canonical implementation plan moved to:
  - `docs/155_ph/CODEX_UNIFIED_DAG_MASTER_PLAN.md`
- If any mismatch exists, implementation priority follows the master plan file above.

## User Flow (Step-by-Step)

```
┌────────────────────────────────────────────────────────────────┐
│                        USER OPENS MCC                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  IS firstTime?                                                 │
│  localStorage.get('mcc_onboarding_completed') === null?        │
└────────────────────────────────────────────────────────────────┘
         │                           │
        YES                          NO
         │                           │
         ▼                           ▼
┌──────────────────┐      ┌─────────────────────────────────────┐
│ Show Onboarding  │      │ Skip to Step 1 or                   │
│ Tooltip 1/5      │      │ last wizard step                    │
└──────────────────┘      └─────────────────────────────────────┘
         │                           │
         └───────────┬───────────────┘
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                    STEP 1: LAUNCH                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  🚀 New Project                                          │  │
│  │  How would you like to start?                            │  │
│  │                                                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │   📁     │  │   🔗     │  │   ✨     │               │  │
│  │  │  Select  │  │   Clone  │  │  Create  │               │  │
│  │  │  Folder  │  │    Git   │  │   New    │               │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  │                                                          │  │
│  │  [Continue →]                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  FOOTER: [Select Folder] [Clone Git] [Create New]              │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                   STEP 2: PLAYGROUND                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  🗺️ Setup Workspace                     1→[2]→3→4→5     │  │
│  │  Choose your playground                                  │  │
│  │                                                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │   🆕     │  │   📋     │  │   ▶️     │               │  │
│  │  │   New    │  │   Copy   │  │ Continue │               │  │
│  │  │Playground│  │ Existing │  │ Current  │               │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  │                                                          │  │
│  │  [← Back]  [Continue →]                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  FOOTER: [← Back] [Select Playground] [Continue →]             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    STEP 3: KEYS                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  🔑 Configure Keys                      1→2→[3]→4→5     │  │
│  │  Set up your AI providers                                │  │
│  │                                                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │   🔑     │  │   ➕     │  │   🖥️     │               │  │
│  │  │  Use     │  │   Add    │  │  Local   │               │  │
│  │  │ Existing │  │   New    │  │  Model   │               │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  │                                                          │  │
│  │  [← Back]  [Continue →]                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  FOOTER: [← Back] [Use Existing] [Continue →]                  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    initMCC() called
                    Project initialized
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                   STEP 4: DAG (Architecture)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Breadcrumb: Project Name                                │  │
│  │  Step Indicator: 1→2→3→[4]→5                            │  │
│  │                                                          │  │
│  │  ┌──────────┐     ┌──────────┐     ┌──────────┐        │  │
│  │  │ 🎨       │────→│ ⚙️       │────→│ 🗄️       │        │  │
│  │  │Frontend  │     │ Backend  │     │Database  │        │  │
│  │  │Module    │     │ Module   │     │ Module   │        │  │
│  │  └──────────┘     └──────────┘     └──────────┘        │  │
│  │       │                │                │               │  │
│  │       └────────────────┴────────────────┘               │  │
│  │                      │                                  │  │
│  │           double-click to drill                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────┐                    ┌──────────┐                  │
│  │💬 Chat   │                    │📊 Stats  │                  │
│  │(draggable│                    │(draggable│                  │
│  └──────────┘                    └──────────┘                  │
│                                                                 │
│  FOOTER: [Create Task] [Ask Architect] [Execute ▶]             │
│            ↑              ↑               ↑                     │
│      On selected      Opens chat    Run selected               │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Double-click "Backend Module"
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    ZOOM LEVEL 1: Tasks                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Breadcrumb: Project > Backend                             │  │
│  │  Zoom: 200%                                              │  │
│  │                                                          │  │
│  │  ┌──────────┐     ┌──────────┐     ┌──────────┐        │  │
│  │  │TASK-001  │────→│TASK-002  │────→│TASK-003  │        │  │
│  │  │[PENDING] │     │[RUNNING] │     │[DONE]    │        │  │
│  │  │API Setup │     │Auth      │     │Database  │        │  │
│  │  └──────────┘     └──────────┘     └──────────┘        │  │
│  │       │                │                │               │  │
│  │       └────────────────┴────────────────┘               │  │
│  │                      │                                  │  │
│  │           double-click task for workflow                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────┐                    ┌──────────┐                  │
│  │💬 Chat   │                    │📊 Stats  │                  │
│  │(draggable│                    │(draggable│                  │
│  └──────────┘                    └──────────┘                  │
│                                                                 │
│  FOOTER: [Launch Task] [Edit Task] [← Back]                    │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Double-click "TASK-002"
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    ZOOM LEVEL 2: Workflow                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Breadcrumb: Project > Backend > TASK-002                │  │
│  │  Zoom: 400%                                              │  │
│  │                                                          │  │
│  │              ┌─────────┐                                 │  │
│  │              │ 🕵️      │                                 │  │
│  │              │Scout    │──┐                              │  │
│  │              │@folder  │  │                              │  │
│  │              └─────────┘  │     ┌─────────┐              │  │
│  │                           └────→│ 👨‍💻     │              │  │
│  │                                 │Architect│──────┐       │  │
│  │                                 │@plan    │      │       │  │
│  │                                 └─────────┘      ▼       │  │
│  │                                        ┌─────────┐       │  │
│  │                                        │ 💻      │       │  │
│  │                                        │Coder    │       │  │
│  │                                        │@qwen3   │       │  │
│  │                                        └─────────┘       │  │
│  │                                              │           │  │
│  │                                              ▼           │  │
│  │                                        ┌─────────┐       │  │
│  │                                        │ ✅      │       │  │
│  │                                        │Verifier │       │  │
│  │                                        │@glm4    │       │  │
│  │                                        └─────────┘       │  │
│  │                                              │           │  │
│  │                                              ▼           │  │
│  │                                        ┌─────────┐       │  │
│  │                                        │ 📄      │       │  │
│  │                                        │Artifact │       │  │
│  │                                        │Output   │       │  │
│  │                                        └─────────┘       │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────┐                    ┌──────────┐                  │
│  │💬 Chat   │                    │📊 Stats  │                  │
│  │(draggable│                    │(draggable│                  │
│  └──────────┘                    └──────────┘                  │
│                                                                 │
│  FOOTER: [▶ Run] [⏸ Pause] [← Back]                            │
│            ↑        ↑          ↑                               │
│      Start     Stop/Pause  Zoom out                            │
└────────────────────────────────────────────────────────────────┘
```

## Component Hierarchy

```
MyceliumCommandCenter
│
├── WizardContainer (Steps 1-3)
│   ├── StepLaunch
│   ├── StepPlayground  
│   └── StepKeys
│
├── UnifiedDAGView (Step 4-5)
│   ├── ReactFlow
│   │   ├── ArchitectureNode (Level 0)
│   │   ├── TaskNode (Level 1)
│   │   ├── AgentNode (Level 2)
│   │   └── ArtifactNode (Level 2)
│   └── CameraController
│
├── Floating Layer
│   ├── MiniChat (draggable)
│   ├── MiniStats (draggable)
│   └── MiniTasks (draggable)
│
├── FooterActionBar (3 buttons)
│   └── Context-aware buttons
│
└── Breadcrumb + StepIndicator
```

## State Machine

```
┌──────────┐
│  START   │
└────┬─────┘
     │
     ▼
┌─────────────────────────────────────┐
│ Step 1: Launch                      │
│ - Show 3 options (folder/git/new)   │
│ - On complete → Step 2              │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ Step 2: Playground                  │
│ - Show 3 options (new/copy/cont)    │
│ - On complete → Step 3              │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ Step 3: Keys                        │
│ - Show 3 options (existing/new/     │
│   local)                            │
│ - On complete → initMCC() → Step 4  │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ Step 4: DAG (Architecture)          │
│ - Show unified DAG at level 0       │
│ - Zoom: 100%                        │
│ - On node double-click → Level 1    │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ Zoom Level 1: Tasks                 │
│ - Zoom: 200%                        │
│ - Show tasks of selected module     │
│ - On task double-click → Level 2    │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ Zoom Level 2: Workflow              │
│ - Zoom: 400%                        │
│ - Show agent execution graph        │
│ - On Esc → Level 1                  │
└─────────────────────────────────────┘
```

## Data Flow

```
User Action
     │
     ▼
┌──────────────────────────────────────────────────┐
│ MCCState (Zustand)                               │
│  - wizardStep: 1|2|3|4|5                        │
│  - currentLevel: 0|1|2                          │
│  - focusedNodeId: string|null                   │
│  - camera: {x, y, zoom}                         │
└────────┬─────────────────────────────────────────┘
         │
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ WizardContainer│ │ UnifiedDAGView │ │ FooterActionBar│
│ (steps 1-3)    │ │ (steps 4-5)    │ │ (context)      │
└────────────────┘ └────────────────┘ └────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
    3 options         DAG canvas           3 buttons
    per step          (zoomable)           per level
```

## Key Design Decisions

### 1. Why Wizard Instead of Tabs?
- **Tabs** = "Where am I?" confusion
- **Wizard** = "I'm on step X of 5" clarity
- Progressive disclosure reduces cognitive load

### 2. Why Zoom Instead of Navigation?
- **Navigation** = context switch, loss of spatial awareness
- **Zoom** = "I'm still here, just closer"
- Visual continuity maintains mental model

### 3. Why Exactly 3 Buttons?
- **Miller's Law**: 7±2 items in working memory
- **Hick's Law**: More choices = slower decision
- **Grandma Test**: "I see 3 things, I pick 1"

### 4. Why Draggable Windows?
- User controls their workspace
- Position persistence = personalization
- No fixed layout = works on any screen size

---

**END OF DIAGRAM**
