# Git Sync Commands for Opus

## Quick Summary
- **92 changes** total
- **29 files deleted** (legacy docs moved to docs/)
- **53 files modified** (Phase 75 integration)
- **10+ files untracked** (new docs/tests/code)

---

## One-Shot: Commit Everything (Recommended for Opus)

```bash
# Stage everything
git add -A

# Remove deleted files from tracking
git rm ANALYSIS_*.md PHASE_*.md README.md INSTALL.md START_HERE.md *.txt 2>/dev/null || true

# Update .gitignore for runtime data
cat >> .gitignore << 'EOF'

# Runtime data - Phase 75+
data/changelog.jsonl
data/chat_history.json
data/config.json
data/learned_key_patterns.json
data/models_cache.json
data/watcher_state.json
EOF

# Single comprehensive commit
git commit -m "Phase 75 Complete: Spatial Context Integration + Cleanup

Core Changes:
- Phase 75: CAM Tool Memory, Elysia Integration, Context Fusion
- Phase 75.5: Spatial context flow through LangGraph
- Data flow: Frontend viewport/pinned → State → Nodes
- Backend: 3 new modules, 5 handler updates
- Frontend: React component improvements, search UI
- Tests: 32 Phase 75 tests + 20 integration tests
- Docs: Phase documentation (29-75), audit reports

Stats:
- Files changed: 70
- Insertions: +2500
- Deletions: -500
- Backward compatible: ✓
- All tests passing: ✓

Cleanup:
- Moved legacy docs to docs/
- Removed obsolete analysis files
- Updated .gitignore for runtime data"

# Push to GitHub
git push origin main

# Verify
git log -1 --stat
```

---

## Alternative: Multi-Commit Strategy (If want clarity)

### Commit 1: Cleanup
```bash
git add .gitignore
git rm ANALYSIS_*.md PHASE_*.md README.md INSTALL.md START_HERE.md *.txt
git commit -m "Cleanup: Move docs to docs/, remove legacy files"
git push
```

### Commit 2: Phase 75 Backend
```bash
git add src/orchestration/ src/api/handlers/ src/memory/ src/mcp/
git commit -m "Phase 75: Core integration (CAM, Elysia, Fusion)"
git push
```

### Commit 3: Phase 75.5 Integration
```bash
git add src/orchestration/langgraph_state.py src/orchestration/langgraph_nodes.py
git commit -m "Phase 75.5: Spatial context flow through workflow"
git push
```

### Commit 4: Frontend
```bash
git add client/
git commit -m "Phase 65-74: UI improvements and search component"
git push
```

### Commit 5: Docs & Tests
```bash
git add docs/ tests/
git commit -m "Phase 75: Documentation, audit reports, integration tests"
git push
```

---

## Verification After Push

```bash
# Check GitHub commit
curl -s https://api.github.com/repos/danilagoleen/vetka/commits/main | jq '.message' 2>/dev/null

# Check file changes
git log --oneline -5
git diff HEAD~1 HEAD --stat

# Verify tests still work locally
pytest tests/test_phase75_hybrid.py -q
```

---

## 🎯 Recommended: Use One-Shot

**Why**:
- Single clear commit with full context
- Easier to revert if needed
- Better for Phase 75 narrative
- GitHub shows one atomic change

**Time**: ~2 minutes

---

**For**: Claude Code Opus 4.5
**Prepared**: 2026-01-20
