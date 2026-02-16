# CODEX BRIEF — Wave 2: Unified Control Bar
## Phase 151 | Tasks 151.5, 151.6, 151.7
**Depends on: Wave 1 complete (HeartbeatDropdown from 151.1)**

---

## OVERVIEW

Merge scattered header controls into one unified bar.
Three questions always answered: КТО (team) / ГДЕ (sandbox) / КОГДА (heartbeat).

**After Wave 2:** Header shows `[Team▾] [Sandbox▾(+)] [⏱Heartbeat▾] [Key▾($)] ●LIVE [3t 1r 2d] [▶Execute]`

**Rules:**
- Nolan palette (grayscale + teal #4ecdc4)
- Monospace font
- All inline styles
- Each dropdown is a self-contained component
- Do NOT touch python backend — frontend only

---

## 151.5 — Unified Header Bar

### Problem
Current header (MyceliumCommandCenter.tsx, lines 410-516) has scattered controls:
- Left: MCC title, PresetDropdown, ●LIVE
- Right: WatcherMicroStatus, HeartbeatChip, PlaygroundBadge, stats text, stream toggle, panel toggles

User can't see the 3 core settings (team/sandbox/schedule) at a glance.

### Target Layout
```
┌───────────────────────────────────────────────────────────────────────────┐
│ MCC  [◇ Dragon Silver ▾]  [📂 ~/vetka ▾ (+)]  [⏱ Off ▾]  [🔑 Polza ▾ ($0.12)]  ●LIVE  [3t 1r 2d]  [▶ Execute] │
└───────────────────────────────────────────────────────────────────────────┘
```

### What to Build

**File: `client/src/components/mcc/MyceliumCommandCenter.tsx`**

Rewrite the header section (lines ~410-516). New structure:

```tsx
<div style={{ /* header bar */ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderBottom: '1px solid #222' }}>
  {/* Left: brand */}
  <span style={{ fontFamily: 'monospace', fontSize: 11, fontWeight: 700, color: '#fff' }}>MCC</span>

  {/* Core controls */}
  <PresetDropdown />                     {/* Existing component — team selector */}
  <SandboxDropdown />                    {/* New — wraps PlaygroundBadge logic */}
  <HeartbeatChip />                      {/* Updated in Wave 1 (151.1) — now a dropdown */}
  <KeyDropdown />                        {/* New — mini balance/key selector */}

  {/* Spacer */}
  <div style={{ flex: 1 }} />

  {/* Status */}
  <ConnectionStatus />                   {/* ●LIVE / ○OFF indicator */}
  <span style={{ fontFamily: 'monospace', fontSize: 9, color: '#666' }}>
    {summary?.by_status?.pending || 0}t {summary?.by_status?.running || 0}r {summary?.by_status?.done || 0}d
  </span>

  {/* Execute */}
  <button onClick={handleExecute} style={{ /* teal accent button */ }}>
    ▶ Execute
  </button>

  {/* Panel toggles (keep) */}
  <button onClick={toggleLeftPanel}>◀</button>
  <button onClick={toggleRightPanel}>▶</button>
</div>
```

### New Components to Create

**`SandboxDropdown`** — wraps PlaygroundBadge logic into dropdown:
- Shows current playground name or "No sandbox"
- Click → dropdown listing active playgrounds
- "(+) Create new" at bottom → calls `POST /api/debug/playground/create`
- Each playground: name, age, task, Destroy button
- Source data: fetch from `/api/debug/playground/list`

**`KeyDropdown`** — mini API key selector:
- Shows `🔑 {provider} ($X.XX)` in chip
- Click → dropdown with available API keys from BalancesPanel data
- Click key → select it (store in `useStore.selectedKey`)
- Show remaining balance next to each key
- Source data: fetch from `/api/debug/usage/balances`

### What to Remove
- **WatcherMicroStatus** — remove entirely (low-value noise)
- **stream toggle button** — remove (StreamPanel auto-shows during pipeline)
- **PlaygroundBadge as separate chip** — replaced by SandboxDropdown

---

## 151.6 — Toolbar Merge

### Problem
WorkflowToolbar (518 lines) has 15 buttons hidden behind editMode. Save and Execute are invisible to user.

### What to Change

**File: `client/src/components/mcc/WorkflowToolbar.tsx`**

Move to header: **Save** and **Execute** (already moved Execute in 151.5).
Keep in canvas toolbar (only when editMode=true):
- Edit toggle (✎)
- Workflow name
- New, Load, Undo, Redo
- Validate, Generate, Import, Export

Save button: move to header, next to Execute. Or: auto-save on Execute (Execute already calls save first).

Simplify: if Execute auto-saves, we don't need a separate Save button in header. Just keep it in toolbar for manual saves.

### Minimal Change
Remove `[▶ Execute]` from WorkflowToolbar (it's now in header via 151.5).
Keep everything else in toolbar as-is — it works, just needs editMode=true (done in 151.3).

---

## 151.7 — Cleanup Duplicates

### What to Remove/Simplify

1. **WatcherMicroStatus** — delete import and usage from MCC header
2. **stream toggle** — remove button. StreamPanel: auto-show when any task is `running`, auto-hide when idle
3. **Consolidate stats text** — `{N}t {N}r {N}d` format stays, just make sure it uses MCC store data consistently

### Files
- `MyceliumCommandCenter.tsx` — remove WatcherMicroStatus, stream toggle from header
- If WatcherMicroStatus is a separate file, leave it but don't import

---

*Codex Brief Wave 2 | Phase 151 | Opus Commander*
