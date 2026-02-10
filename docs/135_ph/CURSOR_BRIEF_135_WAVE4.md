# Phase 135.4: 3-Tab MCC + VETKA Style Unification

## Context

Wave 1-3 created DAG view but:
1. Lost useful tabs (API Keys, Task Board)
2. Colors too varied — need strict Nolan monochrome
3. Users want 3 tabs max: **DAG | Tasks | Keys**

## Objective

Refactor MyceliumCommandCenter to have 3 tabs with unified VETKA styling.

## Tab Structure

```
┌─────────────────────────────────────────────────────────────┐
│ [DAG] [Tasks] [Keys]                    ● LIVE    [Filters] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Tab Content Area (flex: 1)                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Tab 1: DAG (default)
- Current DAGView + DetailPanel
- FilterBar inline in header
- 80/20 split when DetailPanel visible

### Tab 2: Tasks
- Reuse TaskBoard from DevPanel
- Simple list of tasks with status, dispatch button
- Click task → show in DAG tab (switch + select node)

### Tab 3: Keys
- Reuse BalancesPanel from DevPanel
- API key balances, usage stats
- Click key → select for next pipeline

## Strict Nolan Palette

From BalancesPanel.tsx — MUST use these colors ONLY:

```typescript
const NOLAN = {
  // Backgrounds
  bg: '#111',           // Main background
  bgLight: '#1a1a1a',   // Cards, hover
  bgDim: '#0d0d0d',     // Darker areas

  // Borders
  border: '#222',       // Default border
  borderLight: '#333',  // Accent border

  // Text
  text: '#e0e0e0',      // Primary text
  textMuted: '#888',    // Secondary text
  textDim: '#666',      // Tertiary text
  textDimmer: '#444',   // Disabled text

  // Status (MUTED — no bright colors!)
  successBg: '#2a3a2a',
  successText: '#6a8a6a',
  errorBg: '#3a2a2a',
  errorText: '#8a6a6a',
  runningBg: '#2a2a3a',
  runningText: '#6a6a8a',
};
```

**FORBIDDEN COLORS:**
- Bright green (#00ff00, #4caf50)
- Bright red (#ff0000, #f44336)
- Brown/tan (#8b7355)
- Any saturated color

## Files to Modify

### 1. `client/src/utils/dagLayout.ts`
Update NOLAN_PALETTE to match BalancesPanel exactly:
```typescript
export const NOLAN_PALETTE = {
  bg: '#111',
  bgLight: '#1a1a1a',
  bgDim: '#0d0d0d',
  border: '#222',
  borderLight: '#333',
  text: '#e0e0e0',
  textMuted: '#888',
  textDim: '#666',
  textDimmer: '#444',
  statusDone: '#6a8a6a',
  statusRunning: '#6a6a8a',
  statusFailed: '#8a6a6a',
  statusPending: '#444',
};
```

### 2. `client/src/components/mcc/nodes/*.tsx`
Update all 4 nodes to use NOLAN_PALETTE:
- Remove any hardcoded colors
- Use statusDone/statusRunning/statusFailed for borders

### 3. `client/src/components/mcc/MyceliumCommandCenter.tsx`
Add tab system:
```typescript
type MCCTab = 'dag' | 'tasks' | 'keys';

const [activeTab, setActiveTab] = useState<MCCTab>('dag');

// Tab bar with NOLAN styling
<div style={{ display: 'flex', gap: 0, borderBottom: `1px solid ${NOLAN.border}` }}>
  {(['dag', 'tasks', 'keys'] as MCCTab[]).map(tab => (
    <button
      key={tab}
      onClick={() => setActiveTab(tab)}
      style={{
        background: 'transparent',
        border: 'none',
        borderBottom: activeTab === tab ? `1px solid ${NOLAN.text}` : 'none',
        color: activeTab === tab ? NOLAN.text : NOLAN.textDim,
        padding: '8px 16px',
        fontSize: 11,
        fontWeight: activeTab === tab ? 600 : 400,
        cursor: 'pointer',
        textTransform: 'uppercase',
        letterSpacing: 1,
      }}
    >
      {tab}
    </button>
  ))}
</div>

// Tab content
{activeTab === 'dag' && <DAGTabContent />}
{activeTab === 'tasks' && <TasksTabContent />}
{activeTab === 'keys' && <KeysTabContent />}
```

### 4. Create `client/src/components/mcc/TasksTab.tsx`
Extract TaskBoard rendering from DevPanel:
- List tasks with status indicators
- Dispatch button
- Click row to navigate to DAG

### 5. Create `client/src/components/mcc/KeysTab.tsx`
Wrapper around BalancesPanel:
- Import BalancesPanel
- Add MCC-specific styling wrapper

## Implementation Order

1. Update NOLAN_PALETTE in dagLayout.ts
2. Update all 4 node components
3. Add tab bar to MyceliumCommandCenter
4. Create TasksTab wrapper
5. Create KeysTab wrapper
6. Test all 3 tabs visually

## Acceptance Criteria

- [ ] 3 tabs: DAG (default), Tasks, Keys
- [ ] Unified Nolan monochrome palette
- [ ] No bright colors anywhere
- [ ] Tasks tab shows task list with dispatch
- [ ] Keys tab shows API key balances
- [ ] DAG tab preserves current functionality
- [ ] Live indicator visible on all tabs

## Reference Files

- `client/src/components/panels/BalancesPanel.tsx` — COLORS constant
- `client/src/components/panels/DevPanel.tsx` — TaskBoard implementation
- `client/src/components/mcc/MyceliumCommandCenter.tsx` — current implementation

---

*Phase 135.4 Brief | Opus Commander | 2026-02-10*
