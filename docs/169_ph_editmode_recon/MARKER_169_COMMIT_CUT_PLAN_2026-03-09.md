# MARKER_169_COMMIT_CUT_PLAN_2026-03-09

Date: 2026-03-09
Branch: `codex/mcc-wave-d-runtime-closeout`
Goal: split current dirty tree into safe, reviewable commit batches

## Snapshot Baseline

- Total non-clean entries: 336
- Tracked modified: 58
- Untracked: 278
- Main pressure areas: `docs` (167), `tests` (103), `client` (25), `src` (25)

Marker: `MARKER_169_CUT_BASELINE`

## Cut Strategy (strict order)

### Cut 0 — Safety checkpoint (mandatory)

1. Save current status snapshot:

```bash
git status --short > /tmp/vetka_status_before_cut_169.txt
```

2. Never run destructive cleanup (`git clean`, reset) while parallel agents are active.

Marker: `MARKER_169_CUT_0`

---

### Cut 1 — Runtime/Core code only (no tests/docs)

Scope:
- `client/src` + `client/src-tauri` + `src/*` + `run.sh`
- exclude docs/tests/contracts

Staging pattern:

```bash
git add run.sh
# selectively add runtime files only
git add client/index.html client/src-tauri client/src/App.tsx client/src/components client/src/hooks client/src/main.tsx client/src/store client/src/utils

git add src/api src/elisya src/memory src/orchestration src/search src/services src/voice
```

Then verify:

```bash
git diff --cached --name-only | rg '^(client/|src/|run.sh)'
```

Commit message template:
- `feat(runtime): <focused runtime slice>`

Marker: `MARKER_169_CUT_1_RUNTIME`

---

### Cut 2 — Tests/contracts matching Cut 1

Scope:
- `tests/*` only
- include only tests validating Cut 1 behavior

Staging pattern:

```bash
git add tests/
```

Sanity check:

```bash
git diff --cached --name-only | rg '^tests/'
```

Commit message template:
- `test(runtime): add contract coverage for <slice>`

Marker: `MARKER_169_CUT_2_TESTS`

---

### Cut 3 — Docs for Cut 1/2 only

Scope:
- docs that directly explain the runtime/test slice
- avoid bulk phase dumps in this cut

Staging pattern (surgical):

```bash
# example pattern — stage only directly related docs, not whole docs/
git add docs/169_ph_editmode_recon/
# plus explicitly chosen docs files
```

Commit message template:
- `docs(runtime): update recon/impl notes for <slice>`

Marker: `MARKER_169_CUT_3_DOCS`

---

### Cut 4 — Workflow templates + converters

Scope:
- `data/templates/workflows/*`
- related converter/runtime files if not already covered

Staging pattern:

```bash
git add data/templates/workflows/
# optional if needed:
# git add src/services/workflow_canonical_converters.py
```

Commit message template:
- `feat(workflows): register/update external workflow templates`

Marker: `MARKER_169_CUT_4_WORKFLOWS`

---

### Cut 5 — Cut/EditMode backend slice

Scope:
- `src/api/routes/cut_routes.py`
- `src/services/cut_*`
- `src/services/media_mcp_job_store.py`
- related `config/cut/`

Staging pattern:

```bash
git add src/api/routes/cut_routes.py src/services/cut_mcp_job_store.py src/services/cut_project_store.py src/services/media_mcp_job_store.py config/cut/
```

Commit message template:
- `feat(cut-mode): add cut project/job store and API routes`

Marker: `MARKER_169_CUT_5_CUTMODE`

---

### Cut 6 — Cut/EditMode tests + contracts docs

Scope:
- `tests/phase159/*`, `tests/phase170/*` and related contract tests
- `docs/contracts/*` and `docs/170_ph_VIDEO_edit_mode/*`

Staging pattern:

```bash
git add tests/phase159 tests/phase170 docs/contracts docs/170_ph_VIDEO_edit_mode
```

Commit message template:
- `test(cut-mode): add schema and media-window contract coverage`
- `docs(contracts): publish cut/media schema pack`

Marker: `MARKER_169_CUT_6_CONTRACTS`

---

### Cut 7 — Large phase doc bundles (optional separate PR)

Scope:
- `docs/155_ph`, `docs/157_ph`, `docs/158_ph`, `docs/162_*`, `docs/163_*`, `docs/164_*`

Recommendation:
- move as docs-only PR/branch to avoid drowning code review

Marker: `MARKER_169_CUT_7_DIGEST`

## Guardrails per cut

Before commit:

```bash
git diff --cached --name-only
```

After commit:

```bash
git status --short
```

If staged set contains mixed code/tests/docs unexpectedly:

```bash
git restore --staged <path>
```

Marker: `MARKER_169_CUT_GUARDRAILS`

## Practical Next Step

Start with **Cut 1** and **Cut 2** only, then stop for verification.
This keeps immediate risk low and prevents accidental doc avalanche into runtime commits.

Marker: `MARKER_169_NEXT_STEP`
