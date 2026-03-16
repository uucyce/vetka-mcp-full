# Phase 177 — localguys Recon Report (2026-03-17)

**Status:** In Progress  
**Scope:** MCC + local models (localguys) + TaskBoard integration

---

## Current TaskBoard Status

### Pending Tasks (localguys-related)
| Task ID | Title | Source |
|---------|-------|--------|
| `tb_1773275513_6` | LiteRT feasibility on Apple Silicon | phase177_pack |
| `tb_1773275513_7` | LiteRT vs current local stack benchmark | phase177_pack |
| `tb_1773376273_1` | Enforce MCC localguys runtime guard at run-update boundary | mcp |

### Completed Tasks (recent)
- `tb_1773275513_1-5` — Phase 177 pack items (done)
- `tb_1773276211_1` — Verify MCC agent context ingestion (done)

---

## Master Roadmap Analysis

### Stage 1 — Model grounding ✅ PARTIAL
- Model Policy Matrix exists: `docs/177_MCC_local/MODEL_POLICY_MATRIX.md`
- Maps qwen3:8b, deepseek-r1:8b, etc. to roles
- **Missing:** Actual implementation in `LLMModelRegistry` + `ModelRegistry` merge

### Stage 2 — Workflow contract ❌ NOT STARTED
- No `workflow_contract` registry implemented
- No contract resolution in MCC API

### Stage 3 — localguys workflow family ❌ NOT STARTED
- G3 template exists: `data/templates/workflows/g3_critic_coder.json`
- No `g3_localguys` workflow family bound to TaskBoard

### Stage 4 — Playground execution ✅ EXISTS
- `playground_manager.py` — worktree isolation
- Runtime guard task pending: `tb_1773376273_1`

### Stage 5 — Artifact and proof layer ⚠️ PARTIAL
- Artifact tools exist (approve/reject)
- No structured `facts.json`, `plan.json`, `patch.diff` per run

### Stage 6 — MCC runtime control ❌ NOT STARTED
- No worker roster UI in MCC
- No active run status display

### Stage 7 — Autonomy hardening ❌ NOT STARTED
- No stop conditions enforcement
- No structured failure reasons

### Stage 8 — Real-task proving ground ❌ NOT STARTED
- No benchmark pack executed
- No real TaskBoard tasks assigned to localguys

---

## Implementation Backlog Gap

From `LOCALGUYS_IMPLEMENTATION_BACKLOG.md`:

| Backlog Item | Description | TaskBoard Status |
|--------------|-------------|------------------|
| BG-001 | Workflow contract registry | ❌ Not created |
| BG-002 | Local model policy resolver | ❌ Not created |
| BG-003 | g3_localguys workflow family | ❌ Not created |
| BG-004 | Artifact contract implementation | ❌ Not created |
| BG-005 | MCC runtime surface (worker roster) | ❌ Not created |
| BG-006 | Playground isolation enforcement | ⚠️ Partial (guard pending) |
| BG-007 | Real-task benchmark execution | ❌ Not created |

---

## LiteRT Tasks (already in TaskBoard)

| Task ID | Status | Notes |
|---------|--------|-------|
| `tb_1773275513_6` | pending | Research feasibility |
| `tb_1773275513_7` | pending | Benchmark pack |

---

## Next Steps

1. **Complete runtime guard** — `tb_1773376273_1`
2. **Create tasks for BG-001, BG-002** — core infrastructure
3. **Create tasks for BG-003** — first local workflow
4. **Create tasks for BG-005, BG-006** — MCC UI + isolation

---

## References
- Master Roadmap: `docs/177_MCC_local/MASTER_ROADMAP.md`
- Model Policy: `docs/177_MCC_local/MODEL_POLICY_MATRIX.md`
- Implementation Backlog: `docs/177_MCC_local/LOCALGUYS_IMPLEMENTATION_BACKLOG.md`
- Handoff: `docs/177_MCC_local/HANDOFF_MCC_PHASE177_2026-03-15.md`
