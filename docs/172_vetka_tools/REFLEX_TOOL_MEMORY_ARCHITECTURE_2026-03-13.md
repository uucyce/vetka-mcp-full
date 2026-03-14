# REFLEX Tool Memory Architecture

Date: 2026-03-13
Phase: 172 / 177 bridge

## Scope

This note defines how `reflex_tool_memory.py` relates to:

- REFLEX static catalog
- CAM tools
- Elisya context/model stack
- semantic retrieval backends (`Qdrant` / `Weaviate`)

## Current State

### 1. Static REFLEX catalog

Canonical tool metadata lives in:

- `data/reflex/tool_catalog.json`
- `src/services/reflex_registry.py`
- `scripts/generate_reflex_catalog.py`

This is the authoritative static layer for:

- tool id
- namespace
- permission
- roles
- intent tags
- cost metadata

### 2. Tool memory overlay

Ad hoc remembered entries live in:

- `src/services/reflex_tool_memory.py`
- `data/reflex/remembered_tools.json`

This layer currently stores:

- local scripts
- internal helper tools
- skills
- trigger hints
- aliases
- notes

It is an overlay, not an authority.

### 3. CAM tools

CAM-related internal tools remain separate:

- `calculate_surprise`
- `compress_with_elision`
- `adaptive_memory_sizing`

These tools operate on content/context analysis, not on tool catalog persistence.

### 4. Elisya / context stack

Elisya-related systems remain separate:

- `src/elisya/llm_model_registry.py`
- context packing / ELISION
- JEPA-related context enrichment

These systems control model/context behavior, not remembered tool metadata.

### 5. Semantic retrieval

Semantic retrieval remains separate:

- Qdrant-backed search
- Weaviate-backed search
- context DAG / search tools

`reflex_tool_memory.py` does not currently write into semantic stores.

## Conclusion: conflict status

### No runtime conflict

There is currently no direct runtime conflict between:

- tool memory
- CAM tools
- Elisya model/context stack
- semantic retrieval backends

They read/write different data and serve different roles.

### No execution duplicate

There is no duplicate execution path:

- CAM analyzes context
- Elisya shapes context/model behavior
- Qdrant/Weaviate retrieve semantic material
- tool memory only stores remembered tool descriptors

### Real gap: logic split

The real issue is not conflict but architectural separation:

- `tool_catalog.json` is canonical static metadata
- `remembered_tools.json` is dynamic memory overlay
- REFLEX recommendation path does not yet merge them

So today tool memory is stored, but not yet fully consumed by REFLEX scoring.

## Risks

### R1. Semantic duplication

The same tool can exist in both:

- static catalog
- remembered overlay

without canonical linking.

### R2. Recommendation gap

Remembered tools may never surface unless explicitly listed.

### R3. Drift

Remembered entries can become stale if:

- tool path changes
- tool is removed
- catalog entry is renamed

## Design rule

`reflex_tool_memory` must stay an overlay, not a second registry.

This means:

1. static catalog remains canonical
2. remembered entries augment ranking and recall
3. CAM remains a signal producer
4. Elisya remains context/model infrastructure
5. semantic search remains retrieval infrastructure

## Recommended integration

### Step 1. Canonical linking

Add optional fields to remembered entries:

- `tool_id`
- `catalog_source`
- `origin`

If a remembered tool already exists in catalog, store the canonical `tool_id`.

### Step 2. Overlay merge in REFLEX recommendation

REFLEX scorer should:

1. load static catalog
2. load remembered overlay
3. merge by `tool_id` or `path`
4. boost matching tools when remembered metadata is relevant

### Step 3. Lightweight semantic hook

Do not push remembered tools into Qdrant/Weaviate as primary records yet.

Instead:

- use `intent_tags`
- use `trigger_hint`
- use `aliases`

as lightweight local ranking features.

### Step 4. Staleness control

Add validation checks:

- path exists
- tool still in catalog
- active flag

Inactive or stale remembered entries should not be recommended.

## Anti-goals

Do not:

- duplicate CAM in tool memory
- duplicate Elisya context packing in REFLEX memory
- duplicate Qdrant/Weaviate indexing just for remembered tools
- create a second canonical registry beside `tool_catalog.json`

## Practical reading

Right now:

- no conflict
- no runtime duplication
- yes, there is a logic gap

The next correct step is:

- merge remembered tool overlay into REFLEX recommendation path
- keep CAM / Elisya / semantic retrieval separate and composable

## Integration marker

`MARKER_177.REFLEX.TOOL_MEMORY.INTEGRATION.V2`

This slice is considered integrated when all three are true:

- remembered overlay is visible in REFLEX debug/read surfaces
- recommendation output explains overlay score impact when it changes ranking metadata
- stale and overlay-applied entries are inspectable without treating memory as a second registry
