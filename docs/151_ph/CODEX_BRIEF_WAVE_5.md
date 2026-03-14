# CODEX BRIEF — Wave 5: Onboarding + Polish
## Phase 151 | Tasks 151.13, 151.15, 151.16, 151.17, 151.18
**Depends on: Wave 3 + Opus Wave 4 (backend stats)**

---

## OVERVIEW

Final polish wave. Onboarding for new users, Stats v2 UI, visual consistency.

**After Wave 5:** New user opens MCC → 4-step onboarding → runs first task → sees per-agent stats → everything looks uniform.

---

## 151.13 — Stats Dashboard v2 (Full Rewrite)

### Problem
Current PipelineStats (405 lines) shows:
- Vertical bar chart (Recharts) in horizontal space — wastes real estate
- Only verifier self-assessment — no user feedback
- No per-agent breakdown — can't find weak link
- Useless for both human and Architect

### What to Build

**Full rewrite of `PipelineStats.tsx`.**

Backend now provides (from Opus 151.11):
```typescript
interface AgentStats {
  calls: number;
  tokens_in: number;
  tokens_out: number;
  duration_s: number;
  success_count: number;
  fail_count: number;
  retries?: number;
}

// In task.stats:
agent_stats: Record<string, AgentStats>;  // role → stats
adjusted_success: number;                  // 0-1, blended with user feedback
```

### Layout — Horizontal Agent Cards

```
Team: Dragon Silver ─────────────── Weak Link: Coder (42%) 🔥 ──────
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ SCOUT    │ │ ARCHITECT│ │RESEARCHER│ │  CODER   │ │ VERIFIER │
│ ■■■■□ 85%│ │ ■■■■■ 92%│ │ ■■■■□ 80%│ │ ■■□□□ 42%│ │ ■■■■□ 78%│
│ 2.1s avg │ │ 1.8s avg │ │ 3.2s avg │ │ 8.5s avg │ │ 1.2s avg │
│ 12 calls │ │ 8 calls  │ │ 10 calls │ │ 15 calls │ │ 12 calls │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

Each card:
- Agent role name (bold)
- Success bar (horizontal CSS bar, not Recharts): green >70%, yellow 50-70%, red <50%
- Average duration per call
- Total calls
- Background tint: red if <60% (weak link highlight)

Below cards:
- **Team Comparison** (if multiple presets used): side-by-side success rates
- **Timeline** (optional): last 10 runs as small sparkline dots (● green, ○ red)

### Data Flow
```
useMCCStore.tasks → filter tasks with stats → aggregate agent_stats per role → render cards
```

### Compact mode (from 151.9)
Show only: `Runs: N | Success: N% | Weak: {role}` in 2x2 grid.

---

## 151.15 — Onboarding Spotlight

### What to Build

Non-modal 4-step onboarding that guides first-time user through setup.

**New files:**
- `client/src/components/mcc/OnboardingOverlay.tsx` (~200 lines)
- `client/src/hooks/useOnboarding.ts` (~60 lines)

### State Machine

```typescript
// useOnboarding.ts
interface OnboardingState {
  step: 0 | 1 | 2 | 3 | 4;  // 0 = not started, 4 = complete
  completed: boolean;
  dismissed: boolean;
}

function useOnboarding() {
  // Load from localStorage('vetka_onboarding')
  // Auto-start if not completed
  // advance() → step++
  // dismiss() → hide overlay
  // reset() → restart from step 0
}
```

### Steps

| Step | Target Element | Message |
|------|---------------|---------|
| 1 | KeyDropdown (header) | "Select your API key to get started" |
| 2 | PresetDropdown (header) | "Choose your team: Dragon Silver is recommended" |
| 3 | SandboxDropdown (header) | "Select or create a sandbox for safe experimentation" |
| 4 | Architect Chat (right panel) | "Type a task and hit Enter — or click ▶ Execute!" |

### Visual
- Semi-transparent overlay (rgba(0,0,0,0.6)) with cutout around target element
- Small tooltip card next to target: message + "Next" button + progress dots (●○○○)
- Pulsing glow border on target element
- "Skip" link to dismiss

### Persistence
- localStorage key: `vetka_onboarding`
- Value: `{ step, completed, dismissed }`
- Once step 4 complete → never show again
- Re-trigger: Help menu → "Restart onboarding" (or keyboard shortcut)

### Integration
```tsx
// In MyceliumCommandCenter.tsx:
const { step, advance, dismiss, completed } = useOnboarding();

return (
  <>
    {/* ... existing layout */}
    {!completed && <OnboardingOverlay step={step} onAdvance={advance} onDismiss={dismiss} />}
  </>
);
```

---

## 151.16 — Contextual Tooltips

### What to Build

Hover tooltips on all header controls. Disappear after user has seen them 3 times.

**Implementation:** Simple `title` attributes or custom tooltip component.

Tooltip text:
- Team dropdown: "Select AI team preset (Dragon Bronze/Silver/Gold)"
- Sandbox dropdown: "Choose working directory for agent file writes"
- Heartbeat: "Set automatic task polling interval"
- Key dropdown: "Select API key and view remaining balance"
- Execute: "Run current workflow or dispatch next task"
- Stats counter (Nt Nr Nd): "pending / running / done tasks"

**Persistence:** localStorage counter per tooltip ID. After 3 hovers → stop showing.

Keep it minimal — don't over-engineer. CSS `title` attribute is fine for v1.

---

## 151.17 — Visual Consistency

### Design Tokens

Create `client/src/styles/tokens.css` (or add to globals.css):

```css
:root {
  /* Nolan Grayscale */
  --bg-primary: #000;
  --bg-secondary: #0a0a0a;
  --bg-tertiary: #111;
  --bg-hover: #1a1a1a;
  --bg-active: #222;

  --border-dim: #222;
  --border-default: #333;
  --border-bright: #555;

  --text-primary: #fff;
  --text-secondary: #ccc;
  --text-muted: #888;
  --text-dim: #555;
  --text-disabled: #333;

  /* Accent */
  --accent: #4ecdc4;
  --accent-dim: rgba(78, 205, 196, 0.3);

  /* Status */
  --status-success: #4ecdc4;
  --status-warning: #f0c040;
  --status-error: #ff4444;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;

  /* Typography */
  --font-mono: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  --font-size-xs: 9px;
  --font-size-sm: 10px;
  --font-size-md: 11px;
  --font-size-lg: 13px;

  /* Radius */
  --radius-sm: 3px;
  --radius-md: 6px;
  --radius-lg: 12px;
}
```

### Button Hierarchy

- **Primary** (Execute, Start): `background: var(--accent); color: #000; border: none;`
- **Secondary** (Save, Set): `background: transparent; color: var(--text-secondary); border: 1px solid var(--border-default);`
- **Ghost** (toggle, panel): `background: transparent; color: var(--text-muted); border: none;`

### Audit
Go through all `*.tsx` in `client/src/components/mcc/` and `client/src/components/panels/`:
- Replace hardcoded colors with CSS vars where practical
- Ensure consistent button styles
- Remove any non-monospace fonts

This is a polish pass — don't refactor everything, just the most visible inconsistencies.

---

## 151.18 — Playground ↔ Workflow Logic

### Decision: 1 Playground = N Workflows (workspace model)

**What to Build:**

1. **SandboxDropdown** already created in 151.5 — enhance it:
   - Show workflows inside each playground
   - "New Workflow" button per playground
   - Default playground auto-created on first run if none exists

2. **useMCCStore** — add mapping:
```typescript
interface MCCState {
  // ... existing
  activePlayground: string | null;  // playground ID
  playgroundWorkflows: Record<string, string[]>;  // pg_id → [workflow_ids]
}
```

3. **Auto-create on first Execute:**
   - If no playground exists → create one automatically (transparent)
   - Name: `vetka-workspace-{timestamp}`
   - Show brief toast: "Created sandbox: vetka-workspace-..."

This keeps it simple for grandma (auto-creates) while allowing power users to manage multiple.

---

*Codex Brief Wave 5 | Phase 151 | Opus Commander*
