# Git Sync Plan for 92 Changes

## 📊 Breakdown
- ❌ DELETED: 29 (legacy root MDs + broken tests)
- 📝 MODIFIED: 53 (client, src, data, docs)
- ❓ UNTRACKED: 10+ (new docs, modules)
- **Total**: 92 changes

---

## 🗑️ DELETED (29) — Clean Root Docs
All moved to `docs/` or obsolete:
- ANALYSIS_*.md (5)
- PHASE_*_*.md (9) → docs/[phase]_ph/
- README.md → docs/README.md
- INSTALL.md → docs/INSTALL.md
- START_HERE.md → docs/START_HERE.md
- Others (9)

**Action**: Git will handle delete tracking

---

## 📝 MODIFIED (53)

### Client (10 files)
- ArtifactWindow.tsx, FileCard.tsx, MessageBubble.tsx
- ScannerPanel.tsx, VoiceButton.tsx
- useDrag3D.ts, useRealtimeVoice.ts
- chat.ts, api.ts, chatApi.ts

**Type**: Phase 65-74 improvements (UI/UX)

### Backend (8 files)
- handler_utils.py, search_handlers.py, user_message_handler.py
- qdrant_client.py, cam_engine.py
- orchestration modules (Phase 75)
- context_fusion.py, elysia_tools.py

**Type**: Phase 75 integration

### Data (6 files) ⚠️
- changelog.jsonl, chat_history.json
- config.json, learned_key_patterns.json
- models_cache.json, watcher_state.json

**Action**: Add to .gitignore (runtime data)

### Docs (3 files)
- README.md (updated), SKILL.md, tools.md
- docs/README.md (new structure)

---

## ❓ UNTRACKED (~35) — New Files

### Documentation (Phase docs)
- docs/29_ph/, docs/55_ph/, ... docs/75_ph/
- AUDIT.md, MARKERS.md, PHASE_75_*_AUDIT.md

### Source Code (Production)
- src/search/ (new search module)
- src/mcp/vetka_mcp_bridge.py
- src/mcp/vetka_mcp_server.py

### Tests (Production)
- tests/test_mcp_*.py
- tests/test_phase75_*.py

### Frontend (New)
- client/src/config/ (config files)
- client/src/components/search/ (search UI)

---

## 🎯 Recommended Commit Strategy

### Commit 1: Cleanup & Reorganization
```
git add -A
git rm <deleted-29-files>
git commit -m "Cleanup: Move legacy docs to docs/, remove obsolete files"
```

### Commit 2: Backend Integration (Phase 75)
```
git add src/orchestration/ src/api/ src/mcp/
git commit -m "Phase 75: Integrate spatial context into backend
- Add context_fusion bridge
- Integrate CAM Tool Memory
- Add Elysia code tools
- All Phase 75.5 integration complete"
```

### Commit 3: Frontend Updates
```
git add client/
git commit -m "Phase 65-74: Update React components
- Improve artifact window rendering
- Update file card UI
- Enhance voice and drag interactions
- Add search component"
```

### Commit 4: Documentation & Tests
```
git add docs/ tests/
git commit -m "Phase 75: Add phase documentation and integration tests
- Add AUDIT reports for Phase 75, 75.5
- Add integration tests for spatial context
- Add MCP bridge tests"
```

### Commit 5: Configuration
```
git add .gitignore
git commit -m "Config: Update .gitignore to exclude runtime data"
```

---

## ⚠️ Important Notes

1. **Data files** (*.jsonl, *.json in /data):
   - These are runtime-generated, add to .gitignore
   - Don't commit unless critical

2. **Untracked files**:
   - Most are new features (Phase 75, MCP)
   - Some are documentation
   - All should be included

3. **Breaking changes**: None
   - All modifications are backward compatible
   - New fields are Optional

---

## ✅ Verification Checklist
- [ ] Phase 75 tests pass (32 + 20 = 52)
- [ ] No syntax errors in modified files
- [ ] .gitignore updated for data/
- [ ] All commits with clear messages
- [ ] GitHub reflects 92 changes → clean commits

---

**Status**: Ready for implementation
**Recommendation**: Execute 5 commits for clarity
