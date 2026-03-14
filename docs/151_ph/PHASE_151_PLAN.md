# PHASE 151 — UX Overhaul: "Grandma Can Run Mycelium"
## From Developer Tool to Product People Love
**Date: 2026-02-15 | Updated: 2026-02-15 (Post-Grok + Audit)**

---

## Philosophy

> Три вопроса: **КТО** (team), **ГДЕ** (sandbox), **КОГДА** (heartbeat).
> Три шага: выбери → настрой → запусти.
> Одна панель — два режима: **compact** (в DAG) ↔ **expanded** (полный экран).
> Никаких правых кликов для базовых операций.

---

## LOCKED DESIGN DECISIONS (Grok Research + Opus Synthesis)

### 1. Unified Control Bar → **Option B: Integrated Header**
Самый простой и всегда видимый. Как Cursor model selector.
```
┌───────────────────────────────────────────────────────────────────────────┐
│ MCC  [◇ Dragon Silver ▾]  [📂 ~/vetka ▾ (+)]  [⏱ Off ▾]  [🔑 Polza ▾ ($0.12)]  ●LIVE  [3t 1r 2d]  [▶ Execute] │
└───────────────────────────────────────────────────────────────────────────┘
```
- **Tabs остаются** (MCC / STATS / ARCHITECT / BALANCE) — но STATS, ARCHITECT, BALANCE это тоже zoom-панели
- **WorkflowToolbar** — сливается с header (Save/Execute уходят наверх, edit-only кнопки остаются в canvas)
- **Убираем:** отдельные stream toggle, WatcherMicroStatus, разрозненные chips

### 2. Edge Routing → **Option B: `step` + dagre tuning**
Ортогональные прямые линии. Без тяжёлого ELK.
```
Current (smoothstep): ranksep=80, nodesep=50 → U-turns, roundabouts
New (step):           ranksep=120, nodesep=80, edgesep=20 → clean orthogonal
```
- Edge type: `smoothstep` → `step` (xyflow built-in orthogonal)
- connectionLineType: `step` (preview while dragging)
- dagre config: `ranksep: 120`, `nodesep: 80` (больше дыхания)
- rankdir: `'BT'` — оставляем (VETKA tree metaphor, корень внизу)
- Файлы: `dagLayout.ts` (config), `DAGView.tsx` (edgeTypes)

### 3. Playground ↔ Workflow → **Option C: Workspace (1 Playground = N Workflows)**
VS Code workspace model. Один sandbox = рабочее пространство с несколькими workflow/командами.
- Default: один `~/mycelium-workspace` (не пугает новичка)
- Power users: могут создать больше
- Dropdown показывает workflows внутри playground
- **Но:** при первом запуске playground создаётся автоматически (прозрачно)

### 4. Stats → **Per-Agent + User Feedback Blend**
```
success_rate = 0.7 * verifier_self + 0.3 * user_feedback (approve/reject)
```
- Horizontal agent cards (Scout / Architect / Researcher / Coder / Verifier)
- Sparkline timeline per agent
- Weak link heatmap (red <70%)
- Architect hook: `if coder_rate < 0.6 → suggest swap model`

### 5. Panel = Zoom → **Same component, `mode` prop**
- `<ArchitectChat mode="compact" />` — в DAG right panel (300px height, last 5 msgs)
- `<ArchitectChat mode="expanded" />` — full tab (flex:1, full chat history + input)
- State через Zustand — один и тот же чат, два layout
- Expand button `↗` → переключает tab, compact→expanded
- Аналогично для Stats и Balance

### 6. Node Creation → **Double-click canvas → search popover**
ComfyUI pattern. Lowest learning curve.
- Double-click на пустое место → popup с поиском (7 типов: Task, Agent, Condition, Parallel, Loop, Transform, Group)
- Fuzzy search (fzf-style) по названию
- "+" кнопка (zoom controls) тоже открывает этот popup
- Right-click context menu остаётся как fallback для power users
- editMode = ON by default

### 7. Heartbeat → **Left-click dropdown**
```
⏱ [Every 30min ▾]  ← Click →
┌──────────────────────────────┐
│ ● Start  /  ⏸ Pause          │
├──────────────────────────────┤
│  10 min  ○                   │
│  30 min  ●                   │
│  1 hour  ○                   │
│  4 hours ○                   │
│  12 hours ○                  │
│  1 day   ○                   │
│  1 week  ○                   │
│  Custom: [___] min           │
├──────────────────────────────┤
│ Next: 12:34 (14m)            │
│ Dispatched: 5 │ Last: OK     │
└──────────────────────────────┘
```
- Left-click → popover (Radix-style)
- Human labels (не секунды!)
- Start/Stop toggle внутри dropdown
- Не блокирует ручной dispatch

---

## CURRENT STATE (Audit Results)

| Component | File | Lines | Key Issue |
|-----------|------|-------|-----------|
| DAG edges | `dagLayout.ts` | 343 | `smoothstep`, ranksep=80, nodesep=50 → roundabouts |
| DAG view | `DAGView.tsx` | 390 | editMode=false by default, no double-click |
| Toolbar | `WorkflowToolbar.tsx` | 518 | 15 buttons hidden behind editMode, Save invisible |
| MCC header | `MyceliumCommandCenter.tsx` | 749 | Scattered chips, no unified bar |
| Heartbeat | `HeartbeatChip.tsx` | 165 | Right-click for interval, raw seconds |
| Context menu | `DAGContextMenu.tsx` | 210 | 7 node types, only via right-click |
| Editor hook | `useDAGEditor.ts` | 382 | editMode=false default, MAX_HISTORY=50 |
| Store | `useMCCStore.ts` | 340 | activePreset='dragon_silver', no playground link |
| Stats | `PipelineStats.tsx` | 405 | Vertical bars, self-assessment only |
| Architect chat | `ArchitectChat.tsx` | 442 | Separate from DAG panel, not same component |
| Balance | `BalancesPanel.tsx` | 333 | Full tab only, no compact mode |

---

## WAVES (Execution Order)

### Wave 0 — Grok Research ✅ DONE
- Research delivered: wireframes, patterns, recommendations for all 10 points
- Decisions locked (see above)

### Wave 1 — Critical UX Fixes (2-3 days)
**"Убрать все showstoppers — чтобы человек мог кликнуть и получить результат"**

| ID | Task | What to Change | Files | Est |
|----|------|----------------|-------|-----|
| **151.1** | Heartbeat → dropdown | Remove right-click. Left-click → popover. Presets: 10m/30m/1h/4h/12h/1d/1w. Start/Stop inside. | `HeartbeatChip.tsx` → rewrite to `HeartbeatDropdown.tsx` | S |
| **151.2** | Edge routing fix | `smoothstep` → `step`. ranksep: 80→120, nodesep: 50→80. connectionLineType: `step`. | `dagLayout.ts` (config), `DAGView.tsx` (edge type) | S |
| **151.3** | editMode ON + node picker | Default editMode=true. Double-click canvas → `NodePicker.tsx` (search popup, 7 types). | `useMCCStore.ts`, `DAGView.tsx`, new `NodePicker.tsx` | M |
| **151.4** | Connection handles visible | Handles always visible (not hover-only). Green/red drag preview. | `DAGView.tsx` (handle styles), CSS | S |

**Wave 1 acceptance test:** Открыл MCC → видишь DAG → double-click → добавил node → drag handle → connection → ✅

### Wave 2 — Unified Control Bar (2-3 days)
**"КТО-ГДЕ-КОГДА-КЛЮЧ всегда видны в header"**

| ID | Task | What to Change | Files | Est |
|----|------|----------------|-------|-----|
| **151.5** | Unified header bar | 4 dropdowns: [Team▾] [Sandbox▾(+)] [Heartbeat▾] [Key▾($)] + [▶Execute] + ●LIVE + [Nt Nr Nd]. Merge HeartbeatDropdown+PlaygroundBadge+PresetDropdown into one bar. | `MyceliumCommandCenter.tsx` header section (lines 410-516) | L |
| **151.6** | Toolbar merge | Save/Execute → header. Edit-only buttons (Validate, Generate, Import, Export, Undo, Redo) → compact toolbar stays in canvas. | `WorkflowToolbar.tsx`, `MyceliumCommandCenter.tsx` | M |
| **151.7** | Cleanup duplicates | Remove: WatcherMicroStatus, separate stream toggle. Stream → auto-visible during pipeline run. | `MyceliumCommandCenter.tsx` | S |

**Wave 2 acceptance test:** Header shows [Team▾] [Sandbox▾] [⏱▾] [Key▾] [Execute] → все 3 вопроса отвечены в одной строке

### Wave 3 — Panel = Zoom (2-3 days)
**"Один чат, два размера. Одна Stats, два размера."**

| ID | Task | What to Change | Files | Est |
|----|------|----------------|-------|-----|
| **151.8** | Chat: compact ↔ expanded | ArchitectChat: add `mode` prop ("compact"/"expanded"). Compact = DAG right panel (300px, 5 msgs). Expanded = full tab. Same Zustand state. Expand button ↗. | `ArchitectChat.tsx` (+mode), `MCCDetailPanel.tsx`, `DevPanel.tsx` | L |
| **151.9** | Stats: compact ↔ expanded | PipelineStats: compact = agent health summary in right panel. Expanded = full STATS tab. Same data. | `PipelineStats.tsx` (+mode), `MCCDetailPanel.tsx` | M |
| **151.10** | Balance: mini-preview | Show selected key + remaining balance in header dropdown. Full → BALANCE tab. | `BalancesPanel.tsx` (+compact), header integration | S |

**Wave 3 acceptance test:** Click ↗ on chat in DAG → same chat opens as full tab → back = same messages

### Wave 4 — Stats v2 (3-4 days)
**"Видеть кто тормозит, менять слабое звено"**

| ID | Task | What to Change | Files | Est |
|----|------|----------------|-------|-----|
| **151.11** | Per-agent metrics (backend) | Add per-agent stats to pipeline: scout_duration, coder_retries, verifier_confidence, researcher_tokens. Emit in pipeline_stats dict. | `agent_pipeline.py` (+per-agent tracking) | M |
| **151.12** | User feedback → stats | `result_status` (applied/rejected) → weighted into success_rate. Formula: `0.7 * verifier + 0.3 * user`. | `task_board.py` (+feedback integration), `PipelineStats.tsx` | M |
| **151.13** | Stats dashboard v2 | Horizontal agent cards. Per-agent: name, model, success%, duration, retries. Weak link highlight (red <70%). Sparkline timeline. Per-team comparison. | `PipelineStats.tsx` (full rewrite) | L |
| **151.14** | Architect reads stats | Architect prompt injection: "Coder (qwen3) success 42% — consider upgrading". Auto-suggest model swap. | `agent_pipeline.py` (+stats injection into architect context) | M |

**Wave 4 acceptance test:** Run 3 tasks → Stats shows per-agent cards → see Coder at 42% (red) → Architect suggests swap

### Wave 5 — Onboarding + Polish (2-3 days)
**"Бабушка нажала 3 кнопки и запустила"**

| ID | Task | What to Change | Files | Est |
|----|------|----------------|-------|-----|
| **151.15** | Onboarding spotlight | 4 steps: Key → Team → Sandbox → Task. Non-modal overlays. Glow pulse on target. Progress dots. localStorage persistence. Re-trigger from Help. | New `OnboardingOverlay.tsx`, `useOnboarding.ts` | L |
| **151.16** | Contextual tooltips | Hover hints for every control ("Pick team preset", "Create sandbox"). Fade after 3 views. During pipeline: "Watch Activity tab". | Tooltip system across all components | M |
| **151.17** | Visual consistency | Unified button styles (Primary/Secondary/Ghost). Lucide icons. Design tokens CSS vars. Audit all components. | `globals.css` (+tokens), all `*.tsx` | M |
| **151.18** | Playground ↔ Workflow | 1 Playground = N Workflows (workspace model). Auto-create on first run. Dropdown shows workflows. | `useMCCStore.ts`, `PlaygroundBadge.tsx` → `SandboxDropdown.tsx`, backend | L |

**Wave 5 acceptance test:** New user opens MCC → onboarding guides through 4 steps → first task runs → user understands flow

---

## WHAT NOT TO CHANGE

1. **Nolan palette** — grayscale identity (#111→#fff, accent teal #4ecdc4)
2. **3-column layout** — left TaskList / center DAG / right Detail (proven)
3. **Bottom-to-Top flow** — VETKA tree metaphor (root at bottom)
4. **xyflow/React Flow** — mature, well-supported
5. **dagre layout engine** — lighter than ELK, sufficient with tuning
6. **Backend architecture** — changes mostly frontend + stats collection
7. **Monospace font** — code tool identity

---

## FULL FILE MAP

### Wave 1 (Touch)
```
MODIFY  client/src/components/mcc/HeartbeatChip.tsx    → rewrite to HeartbeatDropdown
MODIFY  client/src/utils/dagLayout.ts                   → step edges, ranksep/nodesep
MODIFY  client/src/components/mcc/DAGView.tsx            → editMode, dblclick, handles
MODIFY  client/src/store/useMCCStore.ts                  → editMode default true
CREATE  client/src/components/mcc/NodePicker.tsx          → search popup for node creation
```

### Wave 2 (Touch)
```
MODIFY  client/src/components/mcc/MyceliumCommandCenter.tsx  → unified header bar
MODIFY  client/src/components/mcc/WorkflowToolbar.tsx        → slim down, merge to header
DELETE  client/src/components/mcc/HeartbeatChip.tsx           → replaced by dropdown in header
MODIFY  client/src/components/mcc/PlaygroundBadge.tsx         → merge into SandboxDropdown
```

### Wave 3 (Touch)
```
MODIFY  client/src/components/panels/ArchitectChat.tsx   → +mode prop (compact/expanded)
MODIFY  client/src/components/panels/PipelineStats.tsx   → +mode prop
MODIFY  client/src/components/panels/BalancesPanel.tsx   → +compact mode
MODIFY  client/src/components/panels/MCCDetailPanel.tsx  → embed compact panels
MODIFY  client/src/components/panels/DevPanel.tsx        → tabs → zoom targets
```

### Wave 4 (Touch)
```
MODIFY  src/orchestration/agent_pipeline.py              → per-agent stats collection
MODIFY  src/orchestration/task_board.py                  → feedback → stats blend
MODIFY  client/src/components/panels/PipelineStats.tsx   → full rewrite v2
MODIFY  data/templates/pipeline_prompts.json             → architect stats awareness
```

### Wave 5 (Touch)
```
CREATE  client/src/components/mcc/OnboardingOverlay.tsx  → spotlight onboarding
CREATE  client/src/hooks/useOnboarding.ts                → state machine (4 steps)
CREATE  client/src/styles/tokens.css                     → design tokens
MODIFY  client/src/styles/globals.css                    → import tokens
MODIFY  client/src/store/useMCCStore.ts                  → playground↔workflow mapping
```

---

## CURSOR BRIEF FORMAT

Каждая Wave получает один Cursor Brief документ:
```
docs/151_ph/CURSOR_BRIEF_WAVE_1.md  — HeartbeatDropdown + Edges + NodePicker + Handles
docs/151_ph/CURSOR_BRIEF_WAVE_2.md  — Unified Header Bar
docs/151_ph/CURSOR_BRIEF_WAVE_3.md  — Panel Zoom Architecture
docs/151_ph/CURSOR_BRIEF_WAVE_4_FRONTEND.md  — Stats v2 UI
docs/151_ph/CURSOR_BRIEF_WAVE_5.md  — Onboarding + Polish
```
Backend tasks (151.11, 151.12, 151.14) → Opus делает сам.

---

## SUCCESS CRITERIA

After Phase 151, a new user should:
1. ✅ Open MCC → see 4-step onboarding (Key → Team → Sandbox → Task)
2. ✅ Header: [Team▾] [Sandbox▾] [⏱Heartbeat▾] [Key▾] [▶Execute] — всё видно
3. ✅ Double-click canvas → add node → drag connection → clean straight edges
4. ✅ Left-click Heartbeat → human intervals (10min..1week)
5. ✅ View per-agent stats → see weak link (Coder 42% red)
6. ✅ Chat with Architect in DAG → expand ↗ → same chat full screen
7. ✅ Never need right-click for basic operations
8. ✅ Stats reflect user feedback (approve/reject affects success rate)
9. ✅ First task runs in ≤3 clicks after onboarding

---

## TIMELINE

| Wave | Days | Depends On | Deliverable |
|------|------|------------|-------------|
| Wave 0 | ✅ DONE | — | Grok research + design decisions |
| Wave 1 | 2-3 | Wave 0 | Edges, Heartbeat, NodePicker, Handles |
| Wave 2 | 2-3 | Wave 1 | Unified Header |
| Wave 3 | 2-3 | Wave 2 | Panel Zoom |
| Wave 4 | 3-4 | Wave 1 (backend can start parallel) | Stats v2 |
| Wave 5 | 2-3 | Wave 2+3 | Onboarding + Polish |
| **TOTAL** | **~14-18 days** | | |

**Parallel:** Wave 4 backend (151.11-151.12) can start during Wave 1 frontend.

---

*Phase 151 Plan — Opus Commander | 2026-02-15*
*Grok Research: DONE | Design Decisions: LOCKED | Next: Wave 1 Cursor Briefs*
