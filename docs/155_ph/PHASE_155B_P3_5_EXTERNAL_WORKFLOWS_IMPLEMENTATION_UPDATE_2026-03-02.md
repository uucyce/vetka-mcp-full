# PHASE 155B-P3.5 — External Workflow Research & Implementation Update (2026-03-02)

Status: `REPORT` (protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`)

## 1. Why this research
Goal: ground MCC workflow-template library (`ralph_loop`, `g3_critic_coder`, future presets) in primary sources, not ad-hoc JSONs, and define a realistic adoption order by complexity/budget.

## 2. Source corpus (primary)
1. Dorsey et al., *Adversarial Cooperation in Code Synthesis* (Block, 2025)
   - https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf
2. G3 repository
   - https://github.com/dhanji/g3
3. Ralph repository
   - https://github.com/snarktank/ralph
4. Get Shit Done repository
   - https://github.com/gsd-build/get-shit-done
5. OpenHands repository
   - https://github.com/All-Hands-AI/OpenHands

Local evidence inspected from cloned repos under `/tmp/mcc_research_155b` and paper text extraction from the PDF.

## 3. Extracted patterns by source

### 3.1 Ralph (single-agent loop) — strongest near-term fit
What is reusable for MCC:
1. Fresh context per iteration (hard reset) with externalized memory (`prd.json`, `progress.txt`, git history).
2. Single-story-at-a-time execution with explicit `passes` state.
3. Hard bounded loop (`max_iterations`) + deterministic completion signal.
4. Quality gate each turn (tests/typecheck) before story closure.

Why useful for MCC:
- maps directly to low-token, high-reliability “microfix/small feature” runs;
- minimal orchestration overhead;
- stable deterministic state machine.

### 3.2 G3 paper + repo (critic/coder adversarial cooperation) — high upside, medium risk
What is reusable for MCC:
1. Role separation: generator/coder vs adversarial evaluator/critic.
2. Iterative critique-revise loop with explicit acceptance criteria.
3. Budget/termination boundaries (avoid infinite self-critique).
4. Architecture patterns from repo: coach/player mode, context thinning/compaction, role-specific model configs.

Why useful for MCC:
- improves correctness on complex coding tasks;
- gives a principled 2-agent “quality amplifier” over plain single-agent execution.

Risk:
- if acceptance/budget contracts are weak, loops degrade into expensive churn.

### 3.3 GSD (spec-driven orchestration) — best planning backbone
What is reusable for MCC:
1. Discovery -> research -> planning -> execution -> verify lifecycle.
2. Wave-based parallel execution with dependency grouping.
3. Explicit checkpoint/handoff protocol for human-gated or auth-gated steps.
4. Persistent planning state artifacts and phase-level verification contracts.

Why useful for MCC:
- strongest template for “large project delivery orchestration”, not just code generation.

Risk:
- too heavy for small tasks; must stay as optional “deep mode”.

### 3.4 OpenHands (runtime/system architecture) — strategic platform layer
What is reusable for MCC:
1. EventStream-centric control plane (action/observation bus).
2. Runtime abstraction and sandbox lifecycle.
3. Session/conversation orchestration and multi-agent delegation model.
4. Production concerns (security analyzer, integrations, session management).

Why useful for MCC:
- blueprint for scaling MCC from workflow library to robust multi-session runtime.

Risk:
- highest implementation cost; not a quick “template import”.

### 3.5 Convergence note (MCC templates x OpenHands)
There is real overlap:
1. explicit action/observation control loops,
2. role/delegation model for multi-agent flows,
3. session/runtime boundaries and stop conditions.

Interpretation for MCC:
- keep current template library (Ralph/G3) as execution patterns,
- strengthen it by gradual convergence with OpenHands-style runtime contracts,
- track this as **merge-strengthening**, not direct replacement.

## 4. Ranking for MCC (complexity vs budget vs ROI)

1. **Ralph pattern**
   - Complexity: Low
   - Budget: Low
   - ROI speed: Very high (immediate)
   - Recommended use: default for narrow tasks and short loops.

2. **G3 critic/coder**
   - Complexity: Medium
   - Budget: Medium
   - ROI speed: High (quality gains on non-trivial tasks)
   - Recommended use: medium-complex coding tasks needing stronger verification.

3. **GSD orchestration**
   - Complexity: Medium-High
   - Budget: Medium-High
   - ROI speed: Medium (pays off on larger initiatives)
   - Recommended use: phased delivery / roadmap-driven execution.

4. **OpenHands architectural layer**
   - Complexity: High
   - Budget: High
   - ROI speed: Long-term strategic
   - Recommended use: when MCC runtime/session scale becomes bottleneck.

## 5. Decision in context of MCC roadmap
Your strategy (“take best parts from each, rank by cost/complexity, avoid reinventing”) is correct.

Recommended adoption order:
1. Normalize import/conversion layer first (MD/TXT/XLSX/JSON).
2. Lock template library primitives (Ralph + G3) with strict execution contracts.
3. Add GSD-style phase orchestration as optional deep workflow family.
4. Move toward OpenHands-grade runtime/event architecture only after MCC confirms repeated multi-session load.

## 6. Implementation update done in this turn

### 6.1 Evidence-based template hardening
Updated `g3_critic_coder` template from generic chain to bounded adversarial loop:
- file: `data/templates/workflows/g3_critic_coder.json`
- changes:
  1. Added explicit `spec -> critic -> coder -> acceptance_gate` flow.
  2. Added `budget_guard` with bounded review rounds (`max_iterations`).
  3. Added feedback edge for controlled iterate-if-needed loop.
  4. Added `pattern_source` and execution contract metadata.

### 6.2 Verification
Command:
- `pytest -q tests/test_phase155b_p3_5_template_library.py tests/test_phase153_wave4.py -k "TestWorkflowTemplateLibrary or TestArchitectPrefetch"`

Result:
- `18 passed, 18 deselected`.

## 7. Explicit note on previous concern (“hardcoded from nowhere?”)
Fair point. Initial baseline templates were generic scaffolds to activate template-first path quickly. This update re-grounds them in primary source patterns and introduces bounded execution contracts to prevent token burn and loop drift.

## 8. Readiness gate for “workflow base library” milestone
Add dedicated milestone when MCC is architecturally ready (criteria):
1. converters are stable for MD/TXT/XLSX/JSON,
2. template selection supports deterministic routing,
3. verify/report artifacts exist per run,
4. loop budgets and stop conditions are enforceable at runtime.

When all 4 are true, implement “Core Workflow Library v1” as a first-class MCC subsystem.
