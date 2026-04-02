# RECON: Git Mirror Failures — Phase 203
## PUBLIC_MIRROR_TOKEN expired + submodule issue

**Date:** 2026-04-02
**Phase:** 203
**Author:** Eta (Harness Engineer 2)
**Task:** tb_1775145769_85698_1
**Status:** COMPLETED — root cause identified, fix task created

---

## 1. Mirror Architecture

```
danilagoleen/vetka (private) ──push──► .github/workflows/public-mirror-publish.yml
                                              │
                                              ├─ scripts/release/publish_public_mirrors.sh
                                              │    └─ pushes filtered subtrees to each public repo
                                              │
                                              └─ job: parallax-extras
                                                   └─ syncs scripts/docs/tests → vetka-parallax
```

**Auth mechanism:** `secrets.PUBLIC_MIRROR_TOKEN` — Personal Access Token (classic/fine-grained)

---

## 2. Root Cause

### BUG-1 (CRITICAL): PUBLIC_MIRROR_TOKEN expired

**Evidence from GitHub Actions logs:**
```
GITHUB_TOKEN Permissions:
  Contents: read      ← only read!

remote: Permission to danilagoleen/vetka-mcp-core.git denied to github-actions[bot].
fatal: unable to access '...': The requested URL returned error: 403
[mirror] push failed for vetka-mcp-core@main
[mirror] push failed for vetka-bridge-core@main
[mirror] push failed for vetka-search-retrieval@main
[mirror] push failed for vetka-memory-stack@main
[mirror] push failed for vetka-ingest-engine@main
[mirror] push failed for vetka-elisya-runtime@main
[mirror] push failed for vetka-orchestration-core@main
[mirror] push failed for vetka-chat-ui@main
[mirror] push failed for mycelium@main
[mirror] push failed for vetka-parallax@main
[mirror] push failed for vetka-taskboard@main
```

**Root cause:** `PUBLIC_MIRROR_TOKEN` secret was created **2026-03-04**. PATs with 30-day expiry expired ~2026-04-03. When PAT is empty/expired, workflow falls back to `GITHUB_TOKEN` which only has `contents: read` on the source repo — cannot push to ANY other repo.

**All 11 mirrors fail simultaneously** — confirms single-token root cause, not per-repo issue.

### BUG-2 (WARNING): Broken submodule reference

**Evidence:**
```
fatal: No url found for submodule path 'photo_parallax_playground/vendor/lama' in .gitmodules
```

**Root cause:** Submodule `photo_parallax_playground/vendor/lama` was removed/moved but `.gitmodules` or git index still references it. Non-blocking for mirrors (exit 128 = warning), but causes noise.

---

## 3. Mirrors Inventory (11 public repos)

| Mirror Repo | Domain | Last Sync |
|-------------|--------|-----------|
| vetka-taskboard | architect | 2026-03-31 |
| vetka-cut | cut/media | 2026-03-31 |
| vetka-chat-ui | ux | 2026-03-31 |
| vetka-orchestration-core | engine | 2026-03-31 |
| vetka-elisya-runtime | engine | 2026-03-31 |
| vetka-ingest-engine | engine | 2026-03-31 |
| vetka-memory-stack | engine | 2026-03-31 |
| vetka-search-retrieval | engine | 2026-03-31 |
| vetka-bridge-core | engine | 2026-03-31 |
| mycelium | ux | 2026-03-31 |
| vetka-parallax | parallax | 2026-03-31 |

**All frozen since 2026-03-31** — ~2 days of commits not mirrored.

---

## 4. Fix Plan

### Fix 1 (BUG-1): Regenerate PAT + update secret

1. Go to: github.com → Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens
2. Create new token:
   - **Resource owner:** danilagoleen
   - **Repository access:** All repositories (or select all 11 mirror repos)
   - **Permissions → Contents:** Read and write
   - **Expiry:** 1 year (or no expiry)
3. Update secret:
   ```bash
   gh secret set PUBLIC_MIRROR_TOKEN -R danilagoleen/vetka
   # paste new token interactively
   ```
4. Re-run failed workflow:
   ```bash
   gh workflow run "Publish Public Mirrors" -R danilagoleen/vetka
   ```

### Fix 2 (BUG-2): Clean stale submodule reference

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
# Check if submodule entry exists in .gitmodules
cat .gitmodules | grep lama
# If stale: remove from index
git rm --cached photo_parallax_playground/vendor/lama 2>/dev/null || true
git rm -f .gitmodules  # only if file is stale
# Or edit .gitmodules to remove lama entry
```

### Fix 3 (FUTURE): Add Sherpa to mirror pipeline

When ready — add to `scripts/release/publish_public_mirrors.sh`:
```bash
mirror_repo "vetka-sherpa" "src/sherpa/" "Sherpa — [description]"
```
And create repo: `gh repo create danilagoleen/vetka-sherpa --public --description "..."`

---

## 5. Prevention

- **PAT expiry alert:** Add calendar reminder or GitHub notification for token renewal
- **Workflow improvement:** Add `if: env.PUBLIC_MIRROR_TOKEN != ''` check with fail-fast error message instead of silent 403
- **Rotation cadence:** Renew PAT every 11 months (set 1-year expiry)

---

*Recon completed by Eta, 2026-04-02*
