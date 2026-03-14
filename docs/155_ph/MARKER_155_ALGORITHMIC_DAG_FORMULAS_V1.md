# MARKER_155.ALGORITHMIC_DAG_FORMULAS.V1

Date: 2026-02-22  
Status: normative spec (no-hardcode policy)  
Scope: MCC/Knowledge architecture graph for any repository

## 1) Non-Negotiable Rule

Graph construction must be algorithmic and data-driven.

Forbidden as primary logic:
- hardcoded folder names (`tests`, `docs`, `src`, etc.)
- manual layer assignment by path
- fixed root ids

Allowed:
- path names as weak priors/features only (small weights, never hard filters)

## 2) Canonical Pipeline (No Hardcode)

1. Build L0 typed relation graph from scanners (`structural`, `reference`, `semantic`, `temporal`).
2. Aggregate relation strength via input-matrix weights.
3. Create weighted directed graph.
4. Condense SCC -> L1 DAG.
5. Compute root candidates from graph statistics (not names).
6. Build backbone DAG (main causal tree/forest) from weighted DAG.
7. Compute ranks/layers from partial order.
8. Render backbone as default; cross-links as optional overlay.

## 3) Edge Scoring (Input-Matrix)

For candidate edge `A -> B`:

```text
base(A,B) =
  w_struct(A_type,B_type) * S_struct +
  w_ref(A_type,B_type)    * S_ref +
  w_sem(A_type,B_type)    * S_sem +
  w_temp(A_type,B_type)   * S_temp +
  w_ctx(A_type,B_type)    * S_ctx

DEP(A,B) = sigmoid(k * (base(A,B) - theta))
```

Recommended defaults:
- `k = 12`
- `theta = 0.35`

Temporal signal:

```text
S_temp = 0, if t(B) <= t(A)
S_temp = 0.2 + 0.8 * exp(-Δt / 30),  where Δt = (t(B)-t(A)) in days
```

Semantic gating:

```text
S_sem' = max(0, (S_sem - 0.5) / 0.5)
```

Use `S_sem'` in `base`.

## 4) SCC Condensation (Truth-Preserving Acyclic Projection)

- Find SCCs using Tarjan/Kosaraju.
- Collapse each SCC into supernode.
- Preserve evidence of internal cycle and edge provenance.
- Resulting L1 graph is DAG by definition.

## 5) Computed Root (No Manual Root)

On L1 DAG, compute:

```text
source_centrality(v) = out_degree(v) / (in_degree(v) + 1)
time_earliness(v)    = 1 - normalized_timestamp(v)
authority(v)         = normalized_reference_citations(v)
cycle_penalty(v)     = normalized_scc_density(v)

root_score(v) =
  α * source_centrality(v) +
  β * time_earliness(v) +
  γ * authority(v) -
  δ * cycle_penalty(v)
```

Recommended defaults:
- `α=0.40`, `β=0.30`, `γ=0.20`, `δ=0.10`

Root set:
- top-k by `root_score` under acyclic constraints.
- if multiple disconnected components: one root per component.

## 6) Backbone DAG (Default View)

Goal: readable causal skeleton, not full spaghetti.

Given L1 DAG with weighted edges:
- Build maximum-weight arborescence/forest (per component) rooted at computed roots.
- Keep only backbone edges in default architecture view.
- Non-backbone edges become overlay (`cross-links` toggle).

This is algorithmic and repository-agnostic.

## 7) Knowledge Level (Y Axis)

Knowledge level is computed, not assigned:

```text
rank(v) = longest_path_distance(root, v)          # primary partial-order rank
complexity(v) = normalized(info_density(v))
derivation(v) = normalized(backbone_depth(v))

KL(v) = λ1 * rank(v) + λ2 * complexity(v) + λ3 * derivation(v)
```

Recommended defaults:
- `λ1=0.60`, `λ2=0.20`, `λ3=0.20`

Render policy:
- Y is monotone in `rank(v)` (acyclic order guarantee).
- KL refines spacing, not order.

## 8) Cross-Type Support (3x3 Matrix)

Types: `code`, `doc`, `media` (extensible).

Each pair `(src_type, tgt_type)` has its own channel weights:
- `w_struct`, `w_ref`, `w_sem`, `w_temp`, `w_ctx`.

No pair-specific hardcoded paths.

## 9) JEPA Role

JEPA is not base truth builder.

JEPA is predictive layer:
- proposes future edges/nodes in embedding space
- provides uncertainty/confidence
- merged as overlay (`mode_layer > 0`)
- accepted into base graph only after deterministic validation rules

## 10) Determinism & Verification

Must hold for identical snapshot:
- same roots
- same backbone edges
- same rank order
- same node positions up to stable tie-breakers

Required checks:
- acyclicity (post-SCC and backbone)
- edge density budget
- root stability across reruns
- KL monotonic order consistency

## 11) Current Gap Note (As of 2026-02-22)

Current implementation already has:
- L0 channels, SCC condensation, L2 projection.

Still incomplete vs this spec:
- full computed-root contract not yet exposed in API
- explicit backbone extraction as default view not fully enforced
- KL formula terms not all surfaced in UI payload

