# RECON REPORT — Phase 149
## 6 Haiku Scouts completed | 2026-02-14

---

## SUMMARY: All clear for Dragon execution

| Scout | Finding | Status |
|-------|---------|--------|
| H1 | MCC header mapped — injection point after WatcherMicroStatus (L448-450) | ✅ |
| H2 | Heartbeat toggle at MCCTaskList.tsx L347-403, self-contained | ✅ |
| H3 | TaskCard run button at L617-665, uses `onDispatch` callback | ✅ |
| H4 | useSocket.ts: 55 events, pattern clear, add ~15 lines for playground | ✅ |
| H5 | Heartbeat extraction: ~70 lines, clean boundary, low risk | ✅ |
| H6 | ALL 10 backend endpoints confirmed, zero missing | ✅ |

---

## KEY INJECTION POINTS FOR DRAGON

### D-149.1 HeartbeatChip
- **Create:** `client/src/components/mcc/HeartbeatChip.tsx`
- **Extract from:** `MCCTaskList.tsx` lines 347-403 (collapsed + expanded)
- **Move state:** `hbExpanded` (L59), `nextTickIn` (L60), countdown effect (L76-89)
- **Move util:** `fmtInterval()` (L32-36)
- **Store access:** `useMCCStore()` → `heartbeat`, `updateHeartbeat`
- **API:** POST `/api/debug/heartbeat/settings` with `{ enabled, interval }`
- **Style reference:** fontSize 9, Nolan palette (#111, #e0e0e0, #4ecdc4 accent)

### D-149.2 PlaygroundBadge
- **Create:** `client/src/components/mcc/PlaygroundBadge.tsx`
- **API:** GET `/api/debug/playground` → `{ playgrounds: [...], active_count: N }`
- **Pattern:** Same as HeartbeatChip — compact chip + dropdown on click
- **Events:** Add `playground_updated` to useSocket.ts (after L1380)
- **Style:** Same Nolan palette, 24px chip height

### D-149.3 TaskCard Sandbox Toggle
- **Modify:** `client/src/components/panels/TaskCard.tsx`
- **Injection:** After preset selector (L642), before run button (L643)
- **Add:** `<select>` with Direct/Sandbox options
- **Sandbox flow:**
  1. POST `/api/debug/playground/create { task }` → get playground_id
  2. Call `onDispatch(task.id, preset)` with playground_id (need to extend callback)
- **Parent change:** DevPanel must pass playground_id to dispatch API

### D-149.4 Wire Header
- **Modify:** `MyceliumCommandCenter.tsx` L448-450 (right section)
- **Insert:** `<HeartbeatChip />` and `<PlaygroundBadge />` between WatcherMicroStatus and stats
- **Modify:** `MCCTaskList.tsx` — remove heartbeat section (L347-403) + state (L59-60) + effect (L76-89)
- **Risk:** Low — header uses flex with gap:8, new chips fit naturally

---

## ARCHITECTURE NOTES

1. **State management:** Zustand via `useMCCStore` — NOT MobX, NOT Redux
2. **Socket pattern:** socket.on → CustomEvent dispatch → component listeners
3. **Style system:** NOLAN_PALETTE constants (import from dagLayout.ts)
4. **Component pattern:** functional React with hooks, inline styles
5. **API base:** configurable, defaults to `http://localhost:5001`
6. **Font size:** 9px in header, 8px for secondary text
7. **Color scheme:** #111 bg, #222 borders, #e0e0e0 text, #4ecdc4 accent, #666 dim

---

## RISKS

| Risk | Mitigation |
|------|-----------|
| Dragon may use wrong imports (MobX) | Coder prompt specifies "Zustand only" + Scout reads store |
| Layout break when adding chips | Flex with gap:8 handles it naturally |
| Socket event not wired | Can be added later — HeartbeatChip works with REST polling |
| TaskCard callback change | onDispatch signature extends with optional playground_id |

---

## DECISION: PROCEED WITH DRAGON EXECUTION

All injection points confirmed. Backend 100% ready. Pattern is clear.
Execute D-149.1 → D-149.2 → D-149.3 → D-149.4 sequentially in Playground sandbox.

---

*Recon Report by Opus Commander | 6 Haiku Scouts | Phase 149*
