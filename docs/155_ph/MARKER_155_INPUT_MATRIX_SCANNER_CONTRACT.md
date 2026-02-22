# MARKER_155.INPUT_MATRIX.SCANNERS.V1

Status: draft-for-implementation  
Scope: MCC architecture DAG (one-canvas), backend L0/L1/L2 builder

## 1) Direct Answer To Current State

Current implementation is **not yet** full input-matrix 3x3.

Implemented now:
- L0 code modules + explicit imports (`python/ts/js`)  
- L1 SCC condensation (Tarjan) -> acyclic DAG
- L2 trimmed architecture view for MCC

Missing for full target:
- semantic channel (embedding similarity)
- temporal channel (A earlier than B)
- reference/citation channel for docs/media
- cross-type channel (code<->doc<->media)
- typed scanner family contract

## 2) Scanner Family (Modular)

Base interface:

```python
class Scanner:
    scanner_type: str
    def scan(scope_root: str) -> tuple[list[Node], list[SignalEdge]]:
        ...
```

Specializations:
- `CodeScanner` -> imports, inheritance, calls
- `DocumentScanner` -> headings, references, links, citations
- `BookScanner` -> chapters, glossary refs, source citations
- `ScriptScanner` -> scenes, characters, cue dependencies
- `VideoScanner` -> timeline segments, chapter refs, transcript refs
- `AudioScanner` -> segments, topics, mentions, transcript refs

All scanners return unified `SignalEdge`.

## 3) Unified Signal Contract

```json
{
  "source": "node_a",
  "target": "node_b",
  "channel": "structural|semantic|temporal|reference|contextual",
  "evidence": ["import x", "citation", "timestamp overlap"],
  "confidence": 0.0,
  "weight": 0.0,
  "source_type": "code|doc|book|video|audio|script",
  "target_type": "code|doc|book|video|audio|script",
  "time_delta_days": 0.0
}
```

## 4) Input Matrix (3x3 Types)

Matrix key = `(source_type, target_type)`.

Example policies:
- code->code: structural dominates (explicit imports first)
- doc->doc: semantic/reference dominates
- media->doc: reference/temporal dominates
- doc->code: citation/reference + temporal support

Each pair maps to channel weights:

```python
PAIR_WEIGHTS[(src_type, tgt_type)] = {
  "structural": w1,
  "semantic": w2,
  "temporal": w3,
  "reference": w4,
  "contextual": w5,
}
```

## 5) Dependency Score (Per Pair)

For each candidate edge:

```text
score = sigmoid(
  w_struct*structural +
  w_sem*semantic +
  w_temp*temporal +
  w_ref*reference +
  w_ctx*contextual
)
```

Rules:
- Explicit structural evidence can hard-raise minimum score.
- If edge introduces cycle on L1 view graph, keep in SCC evidence, not as direct acyclic edge.
- Keep `evidence[]` and `confidence` on every accepted edge.

## 6) DAG Build Pipeline (Required)

1. L0 collect nodes from all scanners  
2. Build typed signal graph (multi-channel)  
3. Aggregate score per edge (input-matrix policy)  
4. Build directed graph from accepted edges  
5. Run SCC condensation -> L1 DAG  
6. Compute longest-path layers (rank)  
7. Build L2 view graph with root anchoring and budget trimming  
8. Render in MCC (single canvas)

## 7) Sugiyama Contract For MCC

Required for architecture view:
- One root anchor at bottom (`project_root`)
- rank direction: bottom->top (`BT`)
- y-axis semantics: earlier/foundational lower, derived higher
- avoid disconnected rails by ensuring incoming constraint for non-root nodes

## 8) JEPA Role

JEPA is optional for core DAG correctness, useful for:
- predictive dashed overlays (`/api/mcc/graph/predict`)
- latent cross-type dependency suggestions
- uncertainty-aware candidate edges

JEPA must not replace deterministic base graph rules (imports/refs/time).

## 9) Implementation Markers

- `MARKER_155.INPUT_MATRIX.SCANNERS.V1`
- `MARKER_155.INPUT_MATRIX.PAIR_WEIGHTS.V1`
- `MARKER_155.INPUT_MATRIX.SIGNAL_EDGE.V1`
- `MARKER_155.INPUT_MATRIX.SCC_BRIDGE.V1`
- `MARKER_155.INPUT_MATRIX.SUGIYAMA_CONTRACT.V1`

