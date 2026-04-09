# PROJECT: Mirror Health Guard — Anti-Regression Checklist

**Date:** 2026-04-08
**Phase:** 210
**Author:** Terminal_81ce (VETKA Agent)
**Status:** DRAFT — for review

---

## 1. Problem Statement

Multi-agent git mirror system (11 public repos) keeps breaking. Root causes:

| Bug | Symptom | Root Cause | Fixed |
|-----|---------|------------|-------|
| `permissions: read` | 403 denied to github-actions[bot] | Workflow had only read perms | ✅ |
| `src/reflex` not exists | "prefix not found at main" | reflex files in `src/services/`, not `src/reflex/` | ✅ |
| `vetka-agents` scattered | No single prefix | Files across scripts/, src/agents/, src/generators/ | ✅ |
| PAT token ignored | GITHUB_TOKEN used instead | `persist-credentials: false` missing | ✅ (2026-04-05) |
| `src.api.*` | No mirror | API modules not mirrored to any public repo | ⚠️ NEEDS FIX |

**Pattern:** Every fix requires 1-2 hours of detective work. Need prevention.

---

## 2. Mirror Architecture

```
Monorepo (vetka) ──push──► GitHub Actions
                                │
                                ├─ Workflow: public-mirror-publish.yml
                                │    └─ reads: public_mirror_map.tsv
                                │    └─ runs: publish_public_mirrors.sh
                                │
                                └─ Target repos:
                                     ├─ vetka-mcp-core         (src/mcp)
                                     ├─ vetka-memory-stack    (src/memory)
                                     ├─ vetka-agents          (vetka-agents-wrapper)
                                     └─ ... (8 more)
```

---

## 2.1 Current Mirror Map (public_mirror_map.tsv)

| Prefix | Repo | Status | Notes |
|--------|------|--------|-------|
| src/mcp | vetka-mcp-core | ✅ Active | MCP server core |
| src/bridge | vetka-bridge-core | ✅ Active | Unified tools, validation |
| src/search | vetka-search-retrieval | ✅ Active | Hybrid semantic+keyword search |
| src/memory | vetka-memory-stack | ✅ Active | CAM/ELISION memory layers |
| src/scanners | vetka-ingest-engine | ✅ Active | File scanning, extraction |
| src/elisya | vetka-elisya-runtime | ✅ Active | Multi-provider LLM runtime |
| src/orchestration | vetka-orchestration-core | ✅ Active | DAG execution, workflow |
| client/src/components/chat | vetka-chat-ui | ✅ Active | Agent chat UI |
| client/src/components/mcc | mycelium | ✅ Active | MCC multi-window UI |
| vetka-agents-wrapper | vetka-agents | ✅ Active | Role generation, worktrees |
| vetka-mcp-full | vetka-mcp-full | ✅ Active | Complete MCP bundle |

---

## 2.2 Missing Modules (NOT Mirrored)

From VETKA_DEPENDENCY_CHECKLIST, these modules exist in monorepo but have NO public mirror:

| Module | Location | Status | Recommended Action |
|--------|----------|--------|-------------------|
| `src/services/reflex_integration` | src/services/ | ⚠️ Partially | Already in monorepo, keep as-is |
| `src.services.elisya_tools` | src/elisya/ | ⚠️ Partially | Already covered by vetka-elisya-runtime |
| `src.agents.*` | src/agents/ | ⚠️ Partially | Already covered by vetka-agents (via wrapper) |
| `src/api.*` | src/api/ | ❌ MISSING | **NEEDS NEW REPO** — create vetka-api-core |

### Action Items:
1. ✅ `src/services/reflex*` — No separate mirror needed, works as-is
2. ✅ `src/elisya/*` — Covered by `vetka-elisya-runtime` (src/elisya prefix)
3. ✅ `src/agents/*` — Covered by `vetka-agents` (vetka-agents-wrapper prefix)
4. ❌ `src/api/*` — **MISSING**: Need to create `vetka-api-core` repo or add to existing

---

## 3. Agent Checklist (Pre-Commit)

Before committing changes to files that affect mirrors:

### 3.1 Changing `scripts/release/public_mirror_map.tsv`

```bash
# ALWAYS verify prefix exists in monorepo
PREFIX="src/new-module"  # your new entry
git ls-tree main "$PREFIX" || echo "ERROR: prefix not found!"

# Test subtree split
git subtree split --prefix="$PREFIX" main || echo "ERROR: split failed!"
```

**Checklist:**
- [ ] `git ls-tree main <prefix>` returns a tree (not "fatal")
- [ ] `git subtree split --prefix=<prefix> HEAD` succeeds
- [ ] If wrapper needed: document in `vetka-agents-wrapper/NOTES.md`

### 3.2 Changing `.github/workflows/*.yml`

```bash
# Verify permissions are write, not read
grep -A2 "permissions:" .github/workflows/*.yml
```

**Checklist:**
- [ ] `permissions: write` (not `read`)
- [ ] `persist-credentials: false` (if using checkout)
- [ ] Token secret name matches `publish_public_mirrors.sh`

### 3.3 Adding new mirror repo

```bash
# 1. Verify repo exists on GitHub
gh repo view danilagoleen/<new-repo> || echo "Create repo first!"

# 2. Add to map
echo "prefix\trepo\tbranch" >> scripts/release/public_mirror_map.tsv

# 3. Test split + dry push
./scripts/release/publish_public_mirrors.sh  # will fail on push, but split should work
```

**Checklist:**
- [ ] Repo created on GitHub
- [ ] Added to `public_mirror_map.tsv`
- [ ] Dry-run succeeds (split works)

---

## 4. Mirror-Specific Patterns

### Pattern 1: Simple prefix (1:1 mapping)

```
src/mcp          → vetka-mcp-core
src/memory       → vetka-memory-stack
```

✅ Works with `git subtree split --prefix=`

### Pattern 2: Wrapper prefix (scattered files)

```
scripts/ + src/agents/ + src/generators/ → vetka-agents
```

❌ No single prefix exists. **Solution:**
1. Create `vetka-agents-wrapper/` in monorepo root
2. Copy/link files there
3. Add `sync_vetka_agents.sh` to sync before publish
4. Use `vetka-agents-wrapper` as prefix

**Before adding new scattered module:**
- [ ] Create wrapper directory
- [ ] Add sync script
- [ ] Update wrapper README
- [ ] Document in `docs/MIRROR_WRAPPER_PATTERN.md`

### Pattern 3: Non-existent prefix (common mistake)

```
src/reflex       → ❌ Does NOT exist!
src/services/reflex* → ✅ Real location
```

**Prevention:** Always run `git ls-tree main <prefix>` before adding to map.

---

## 5. Error Signatures (Quick Diagnostics)

| Error | Meaning | Fix |
|-------|---------|-----|
| `denied to github-actions[bot]` | GITHUB_TOKEN used, not PAT | Add `persist-credentials: false` |
| `denied to danilagoleen` | PAT reached GitHub, but no write permission | Check PAT scopes |
| `prefix not found at main` | Prefix doesn't exist | Verify with `git ls-tree` |
| `split failed` | Subtree split error | Check for conflicts or invalid prefix |
| `exit 128` | Submodule or gitlink issue | Clean stale gitlinks |

---

## 6. Monitoring (Future)

### GitHub Actions Alert

```yaml
- name: Verify mirrors health
  run: |
    ./scripts/release/verify_mirrors.sh
    # Exit 1 if any mirror is out of sync > 7 days
```

### Mirror Status Dashboard

| Repo | Prefix | Last Push | Commits Behind | Status |
|------|--------|-----------|----------------|--------|
| vetka-mcp-core | src/mcp | 2026-04-08 | 0 | ✅ |
| vetka-memory-stack | src/memory | 2026-04-05 | ~15 | ⚠️ |

---

## 7. Scripts to Create

### `verify_mirrors.sh`

```bash
#!/bin/bash
# Verify all mirrors are in sync
MAP="scripts/release/public_mirror_map.tsv"
for line in $(tail -n +2 "$MAP" | grep -v "^#"); do
  prefix=$(echo "$line" | cut -f1)
  repo=$(echo "$line" | cut -f2)
  
  # Check if prefix exists
  git ls-tree main "$prefix" > /dev/null 2>&1 || {
    echo "❌ $prefix: not found in main"
    continue
  }
  
  # Check last commit date
  last_push=$(gh api repos/danilagoleen/$repo/commits --jq '.[0].commit.author.date' 2>/dev/null)
  echo "✅ $repo: last push $last_push"
done
```

### `pre_commit_hook.sh`

```bash
#!/bin/bash
# Run before committing mirror-related changes
MAP="scripts/release/public_mirror_map.tsv"

# Check modified prefixes exist
git diff --cached "$MAP" | grep "^+" | grep -v "^+++" | while read line; do
  prefix=$(echo "$line" | cut -f1)
  if ! git ls-tree main "$prefix" > /dev/null 2>&1; then
    echo "❌ ERROR: Prefix '$prefix' not found in main"
    exit 1
  fi
done
```

---

## 8. Open Questions

1. **Auto-sync wrapper:** Should `sync_vetka_agents.sh` run automatically on pre-push hook?
2. **Mirror health alert:** Daily cron job that posts to VETKA chat if any mirror > 7 days behind?
3. **Agent training:** Should checklist be part of AGENTS.md?

---

## 9. Related Docs

- `docs/200_taskboard_forever/RECON_GIT_MIRRORS_203.md` — Original root cause analysis
- `scripts/release/publish_public_mirrors.sh` — Mirror publishing script
- `scripts/release/public_mirror_map.tsv` — Prefix → repo mapping

---

*Document created based on mirror debugging session 2026-04-08*
*Author: Terminal_81ce agent*
