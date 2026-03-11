# Opus — Integration, UI Testing, Git Management

> **Agent:** Opus (Claude Code — Commander)
> **Territory:** MyceliumCommandCenter orchestration, visual testing, ALL commits
> **Phase:** 175 integration → app delivery
> **Priority:** THE MOST IMPORTANT — I see what users see

---

## MY MISSION

I am the final gatekeeper. Nothing ships without my visual verification.
I test on all 4 MCC surfaces, verify agent outputs, handle git, build the dmg.

---

## ROADMAP

### Phase 1: Immediate — Visual Test MCC Standalone (NOW)

After distributing agent briefs, immediately:

1. Start `mycelium-client` (port 3002) + `vetka-backend` (port 5001) + `mycelium` WS (8082)
2. Navigate to MCC at localhost:3002
3. Screenshot and verify:
   - MCC loads without errors
   - DAG view renders
   - MiniWindows appear (Chat, Tasks, Stats, Balance, Context)
   - Navigation levels work (first_run → roadmap → tasks)
   - No console errors (except expected Tauri invoke missing)
4. Document findings in `docs/175_MCC_APP/VISUAL_TEST_REPORT.md`

### Phase 2: After Codex A — Endpoint Integration Test

When Codex A completes 3 endpoints:
1. Run Codex A's test suite: `python -m pytest tests/test_175_backend_api.py -v`
2. Test from UI:
   - TaskEditPopup → PATCH task → verify updated
   - RedoFeedbackInput → POST feedback → verify status change
   - MiniChat → POST chat/quick → verify response appears
3. If issues found → create specific bug fix tasks for Codex A

### Phase 3: After Codex B — Analytics UI Integration

When Codex B completes StatsDashboard:
1. Verify TypeScript compilation: `cd client && npx tsc --noEmit`
2. Rebuild MCC: `VITE_MODE=mcc npm run build:mcc`
3. Visual test in browser:
   - StatsDashboard renders in DevPanel Stats tab
   - Charts populate with data from analytics API
   - TaskDrillDown modal opens correctly
   - FilterBar filters task list
4. Verify MiniBalance works with useMCCStore

### Phase 4: After Dragon — Bundle Optimization Verify

When Dragon completes APNG optimization:
1. Rebuild MCC with optimized assets
2. Verify bundle size < 20MB
3. Test LazyAvatar loads correctly (static → animated transition)
4. Verify no visual regression in agent avatars

### Phase 5: Final Assembly — MYCELIUM.app Build

After all 3 agents complete:
1. Merge all branches into working branch
2. Run FULL test suite: `python -m pytest tests/ -v`
3. Build production bundle: `VITE_MODE=mcc npm run build:mcc`
4. Attempt Tauri build: `cargo tauri build --config src-tauri-mcc/tauri.conf.json`
5. If Tauri build succeeds → test .app on macOS
6. If Tauri build fails → debug Rust compilation, fix, retry
7. Create final dmg

### Phase 6: Git Cleanup + Commit

Organize all changes into logical commits:
```
feat(175): Wave 1 — MCC build splitting (mycelium.html, vite multi-page)
feat(175): Wave 2 — src-tauri-mcc Tauri project
feat(175): Codex A — Backend API endpoints + generic TaskBoard
feat(152): Codex B — Analytics dashboard UI + store fixes
perf(175): Dragon — APNG optimization + lazy-loading
feat(175): Final assembly — MYCELIUM.app integration
```

---

## SURFACES I TEST (all 4)

1. **Browser MCC** — localhost:3002 (mycelium-client)
2. **Embedded MCC** — localhost:3001/mycelium (within VETKA)
3. **DevPanel MCC** — MCC tab in DevPanel
4. **Tauri MCC** — MYCELIUM.app native window (final)

---

## MY FILES (only I edit these)

| File | Purpose |
|------|---------|
| `client/src/components/mcc/MyceliumCommandCenter.tsx` | Root MCC orchestration |
| `client/src/components/mcc/DAGView.tsx` | DAG workspace |
| `client/src/MyceliumStandalone.tsx` | Standalone wrapper |
| `client/src/mycelium-entry.tsx` | Entry point |
| `client/vite.config.ts` | Build config |
| `client/src-tauri-mcc/*` | All Tauri MCC files |
| `scripts/build_mycelium.sh` | Build script |
| `docs/175_MCC_APP/*` | All coordination docs |
| ALL git operations | Commit, merge, push |

---

## SUCCESS CRITERIA (FINAL)

1. ✅ MCC loads in browser at localhost:3002 with ALL MiniWindows
2. ✅ All 5 MiniWindows functional (Chat, Tasks, Stats, Balance, Context)
3. ✅ Analytics dashboard renders with real data
4. ✅ TaskEditPopup, RedoFeedbackInput, MiniChat work end-to-end
5. ✅ Bundle < 20MB (with optimized APNG)
6. ✅ MYCELIUM.app builds and launches on macOS
7. ✅ All tests pass (existing + new)
8. ✅ Clean git history with logical commits
