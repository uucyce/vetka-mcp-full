# Codex B — Frontend Analytics + Store Fixes

> **Agent:** Codex B (fresh session)
> **Territory:** Frontend TypeScript only (client/src/components/analytics/, MiniBalance, stores)
> **Branch:** `codex-b/152-analytics-ui`
> **Phase:** 152.5-152.8 + 175 store fix
> **Estimated:** 6-8 hours total

---

## YOUR MISSION

Build the analytics dashboard frontend and fix MiniBalance store dependency.
You own the analytics UI components and specific store additions. No backend work.

---

## CONTEXT DOCUMENTS (READ FIRST)

1. **Analytics spec:** `docs/152_ph/PHASE_152_ROADMAP.md` — Full Phase 152 roadmap
2. **Dashboard brief:** `docs/152_ph/CODEX_BRIEF_WAVE2_STATS_DASHBOARD.md` — Original Codex brief
3. **Grok design research:** `docs/152_ph/GROK_RESEARCH_152_STATS_DASHBOARD.md` — UI patterns, Recharts, Nolan dark style
4. **Coordination:** `docs/175_MCC_APP/AGENTS_COORDINATION_175.md` — Territory map
5. **MCC recon:** `docs/175_MCC_APP/RECON_175_UNIFIED.md` — MiniBalance store dependency (section 2)

---

## ROADMAP (execute top-to-bottom)

### Step 0: MiniBalance Store Extraction (P0 — quick fix)

**Problem:** MiniBalance.tsx imports from main `useStore` (the VETKA app store).
For standalone MYCELIUM.app, these need to live in `useMCCStore`.

**File:** `client/src/store/useMCCStore.ts`

Add to the store:
```typescript
// MARKER_175.0D: API key management for standalone MCC
selectedKey: string;
setSelectedKey: (key: string) => void;
favoriteKeys: string[];
toggleFavoriteKey: (key: string) => void;
```

Initialize `selectedKey` from localStorage key `mcc_selected_key` or empty string.
Persist `favoriteKeys` to localStorage key `mcc_favorite_keys`.

**File:** `client/src/components/mcc/MiniBalance.tsx`

Change store import:
```typescript
// Before:
import { useStore } from '../../store/useStore';
const { selectedKey, setSelectedKey, favoriteKeys, toggleFavoriteKey } = useStore();

// After:
import { useMCCStore } from '../../store/useMCCStore';
const { selectedKey, setSelectedKey, favoriteKeys, toggleFavoriteKey } = useMCCStore();
```

### Step 1: StatsDashboard Component (Phase 152.5)

**File:** `client/src/components/analytics/StatsDashboard.tsx` (NEW)

Create new directory: `client/src/components/analytics/`

Dashboard displays pipeline performance using Recharts:

**Data sources (REST API — already working):**
- `GET /api/analytics/summary` → KPI cards (total runs, success%, avg time, cost)
- `GET /api/analytics/agents` → Per-agent efficiency bars
- `GET /api/analytics/trends` → Time-series line chart (runs over time)
- `GET /api/analytics/teams` → Team comparison (Bronze vs Silver vs Gold)
- `GET /api/analytics/cost` → Cost breakdown pie chart

**Layout (Nolan dark style from Grok research):**
```
┌─────────────────────────────────────────────────────────┐
│ 📊 Pipeline Analytics                     [7d▾] [↗]    │
├─────────┬──────────┬──────────┬────────────────────────┤
│ Runs    │ Success  │ Avg Time │ Est Cost               │
│  47     │  89.4%   │  42s     │ $2.34                  │
├─────────┴──────────┴──────────┴────────────────────────┤
│ [Line Chart: Runs over time — 7d/30d/90d]              │
├────────────────────────────────────┬───────────────────┤
│ [Bar Chart: Agent Efficiency]      │ [Pie: Team Share] │
│ architect ████████░░ 92%           │  Silver 60%       │
│ coder     ██████░░░░ 78%           │  Gold   25%       │
│ verifier  █████████░ 94%           │  Bronze 15%       │
└────────────────────────────────────┴───────────────────┘
```

**Style:** Background `#0d0d0d`, cards with `border: 1px solid #222`, accent `#8b5cf6` (purple).
Use `recharts` (already in package.json): LineChart, BarChart, PieChart, ResponsiveContainer.

### Step 2: TaskDrillDown Modal (Phase 152.6)

**File:** `client/src/components/analytics/TaskDrillDown.tsx` (NEW)

Modal that shows detailed task execution timeline:

**Data source:** `GET /api/analytics/task/{task_id}`

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│ Task: "Fix auth bug" (task_abc123)          [✕]      │
├──────────────────────────────────────────────────────┤
│ Status: ✅ complete  │ Team: Silver  │ Time: 38s     │
├──────────────────────────────────────────────────────┤
│ Timeline (Gantt):                                    │
│ architect ████░░░░░░░░░░░ 0-8s                      │
│ researcher ░░░████░░░░░░░ 8-16s                     │
│ coder     ░░░░░░░█████░░ 16-30s                     │
│ verifier  ░░░░░░░░░░░██░ 30-38s                     │
├──────────────────────────────────────────────────────┤
│ Agent Stats:                                         │
│ ┌─────────┬────────┬───────┬────────┐               │
│ │ Agent   │ Tokens │ Time  │ Status │               │
│ ├─────────┼────────┼───────┼────────┤               │
│ │ architect│ 1,240 │ 8.2s  │ ✅     │               │
│ │ coder   │ 3,891 │ 14.1s │ ✅     │               │
│ └─────────┴────────┴───────┴────────┘               │
└──────────────────────────────────────────────────────┘
```

Uses Recharts BarChart for Gantt-like timeline.
Opens from: StatsDashboard task click, MiniStats task click, or TaskCard click.

### Step 3: TaskFilterBar Component (Phase 152.8)

**File:** `client/src/components/mcc/FilterBar.tsx` (NEW or extend existing)

Inline filter bar for task list:
- Status filter: pending | running | complete | failed | all
- Phase filter: research | fix | build | all
- Preset filter: dragon_bronze | dragon_silver | dragon_gold | all
- Text search: fuzzy match on title/description

Filter state stored in useMCCStore:
```typescript
// MARKER_152.8: Task filter state
taskFilters: {
  status: string;
  phase: string;
  preset: string;
  search: string;
};
setTaskFilter: (key: string, value: string) => void;
```

### Step 4: TaskEditor Inline (Phase 152.7)

**File:** `client/src/components/mcc/MCCTaskList.tsx` (MODIFY — your territory)

Add inline editing to task list items:
- Double-click title → editable input
- Double-click description → editable textarea
- Save on Enter or blur
- Cancel on Escape
- Calls `PATCH /api/mcc/tasks/{task_id}` (Codex A builds this endpoint)

### Step 5: Wire StatsDashboard into DevPanel

**File:** `client/src/components/panels/DevPanel.tsx` (MODIFY — minimal addition)

The Stats tab already exists in DevPanel. Wire StatsDashboard:
```typescript
// In Stats tab content:
import { StatsDashboard } from '../analytics/StatsDashboard';
// Replace existing placeholder with:
<StatsDashboard />
```

Also wire TaskDrillDown as a modal overlay accessible from stats clicks.

---

## TESTS

**Testing approach:** Since these are frontend components, use a combination of:
1. TypeScript compilation (`npx tsc --noEmit`)
2. Vite build verification (`VITE_MODE=mcc npm run build:mcc`)
3. Manual preview verification (Opus handles via preview tool)

**Verification commands:**
```bash
# TypeScript check
cd client && npx tsc --noEmit 2>&1 | grep -E "error|Error"

# MCC build (must succeed)
cd client && VITE_MODE=mcc npx vite build 2>&1 | tail -5

# Regular VETKA build (must not break)
cd client && npx vite build 2>&1 | tail -5
```

---

## SELF-CORRECTION ALGORITHM

```
1. Read docs/152_ph/GROK_RESEARCH_152_STATS_DASHBOARD.md (design patterns)
2. Read docs/152_ph/CODEX_BRIEF_WAVE2_STATS_DASHBOARD.md (specs)
3. Read existing analytics_routes.py to understand API response shapes
4. Create client/src/components/analytics/ directory
5. Implement StatsDashboard.tsx (fetch + Recharts)
6. Run: cd client && npx tsc --noEmit → fix type errors
7. Run: cd client && VITE_MODE=mcc npx vite build → fix build errors
8. Implement TaskDrillDown.tsx
9. Repeat tsc + build check
10. Implement FilterBar + TaskEditor
11. Fix MiniBalance store import
12. Final: VITE_MODE=mcc npx vite build → must succeed
13. Final: npx vite build → must also succeed (VETKA not broken)
14. Write completion status to docs/175_MCC_APP/STATUS_CODEX_B.md
```

---

## FILES YOU OWN (only edit these)

| File | Action |
|------|--------|
| `client/src/components/analytics/StatsDashboard.tsx` | NEW |
| `client/src/components/analytics/TaskDrillDown.tsx` | NEW |
| `client/src/components/analytics/index.ts` | NEW (barrel export) |
| `client/src/components/mcc/FilterBar.tsx` | NEW or extend |
| `client/src/components/mcc/MiniBalance.tsx` | FIX store import |
| `client/src/components/mcc/MCCTaskList.tsx` | ADD inline editing |
| `client/src/store/useMCCStore.ts` | ADD key management + filter state sections |
| `client/src/components/panels/DevPanel.tsx` | WIRE StatsDashboard import |
| `docs/175_MCC_APP/STATUS_CODEX_B.md` | Write completion status |

## FILES YOU MUST NOT TOUCH

- ANY file under `src/` (backend is Codex A + Opus territory)
- `client/src/components/mcc/MyceliumCommandCenter.tsx` (Opus territory)
- `client/src/components/mcc/DAGView.tsx` (Opus territory)
- `client/src/components/mcc/MiniChat.tsx` (Opus territory — already modified by Codex 2)
- `client/src/components/mcc/MiniStats.tsx` (Opus territory — already modified by Codex 2)
- `client/src/mycelium-entry.tsx` (Opus territory)
- `client/vite.config.ts` (Opus territory)
- ANY file under `src-tauri-mcc/` (Opus territory)
- `tests/` (Codex A writes backend tests; Opus handles frontend verification)

---

## DESIGN TOKENS (Nolan Dark Style)

```css
/* From docs/152_ph/GROK_RESEARCH — Nolan dark palette */
--bg-primary: #0d0d0d;
--bg-card: #141414;
--bg-card-hover: #1a1a1a;
--border: #222;
--border-hover: #333;
--text-primary: #e6e6e6;
--text-secondary: #999;
--text-muted: #666;
--accent-purple: #8b5cf6;
--accent-green: #22c55e;
--accent-red: #ef4444;
--accent-yellow: #eab308;
--accent-blue: #3b82f6;
--font-mono: 'JetBrains Mono', 'SF Mono', monospace;
```

Import from `client/src/styles/tokens.css` where available.

---

## SUCCESS CRITERIA

1. `VITE_MODE=mcc npx vite build` → SUCCESS (MCC bundle includes analytics)
2. `npx vite build` → SUCCESS (VETKA not broken)
3. `npx tsc --noEmit` → zero errors
4. StatsDashboard renders 4 KPI cards + 3 charts
5. TaskDrillDown shows Gantt timeline + agent stats table
6. MiniBalance works with useMCCStore (no useStore dependency)
7. FilterBar filters task list by status/phase/preset
8. STATUS_CODEX_B.md written with results
