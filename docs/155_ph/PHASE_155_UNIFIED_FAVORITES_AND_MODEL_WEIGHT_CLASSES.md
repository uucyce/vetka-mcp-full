# Phase 155: Unified Favorites Service + Model Weight Classes

<!-- TODO_PHASE_155: Unified favorites + model weight classes -->
<!-- DEPENDS_ON: Phase 152.FIX3 (star favorites), Phase 151.12 (adjusted_stats), Phase 145 (adaptive timeout) -->
<!-- BLOCKS: Jarvis agent preferences, team benchmarking, eval agent model selection -->
<!-- SEARCH_TAGS: favorites, weight_class, model_tiers, leagues, eval, jarvis, team_bench -->

**Status:** PLANNED (conserved architecture)
**Target:** After Phase 153 stabilizes (~Phase 155)
**Author:** Opus (architect) + Grok (research)
**Date:** 2026-02-17

---

## Problem Statement

### 1. Fragmented Favorites
Currently 4 separate star/favorite systems with no shared schema:

| System | Storage | Scope | ENGRAM | CAM |
|--------|---------|-------|--------|-----|
| API keys + models | `data/favorites.json` | config_routes.py | fire-forget | - |
| File/node paths | `data/node_favorites.json` | tree_routes.py | highlights | partial |
| Chats | `chat_history.json` | chat_history_routes.py | full | full |
| Artifacts | artifact DB | artifact_routes.py | - | partial |

**Impact:** Jarvis agent can't answer "what does the user prefer?" holistically.
Architect can't factor in "user starred Polza + Grok" when selecting team.
Eval/Verifier can't learn from user's favorite patterns.

### 2. No Model Weight Classes
Models are grouped into leagues (Dragon/Titan) and tiers (bronze/silver/gold)
but lack a formal **weight class** system based on:
- **Context capacity** (how much fits in the window)
- **Speed** (tokens per second output)
- **Cost efficiency** (quality per dollar)

These three axes determine which models are suitable for which roles.
Currently hardcoded in `model_presets.json` — no dynamic classification.

---

## Architecture: Unified Favorites Service

### Core Principle
**One service, typed favorites, multiple consumers.**

```
                    +---------------------------+
                    |   FavoritesService        |
                    |   (src/services/)          |
                    |                           |
                    |  add(type, id, meta)      |
                    |  remove(type, id)         |
                    |  list(type?) -> []        |
                    |  is_favorite(type, id)    |
                    +---------------------------+
                           |           |
                    +------+           +------+
                    |                         |
              JSON (primary)           ENGRAM (secondary)
              data/favorites.json      user_preferences
                    |                         |
              REST API                  LLM context
              GET/PUT /api/fav          vetka_get_user_preferences
```

### Schema: `data/favorites_v2.json`

```json
{
  "version": 2,
  "items": [
    {
      "type": "api_key",
      "id": "polza:pza_****9PUM",
      "meta": { "provider": "polza" },
      "starred_at": "2026-02-17T...",
      "starred_by": "danila"
    },
    {
      "type": "model",
      "id": "x-ai/grok-4.1-fast",
      "meta": { "source": "polza", "weight_class": "heavyweight" },
      "starred_at": "2026-02-17T..."
    },
    {
      "type": "chat",
      "id": "uuid-of-chat",
      "meta": { "title": "Input matrix" },
      "starred_at": "2026-02-17T..."
    },
    {
      "type": "file",
      "id": "/src/orchestration/agent_pipeline.py",
      "meta": { "reason": "core pipeline" },
      "starred_at": "2026-02-17T..."
    },
    {
      "type": "artifact",
      "id": "art_123",
      "meta": {},
      "starred_at": "2026-02-17T..."
    },
    {
      "type": "team_preset",
      "id": "dragon_silver",
      "meta": { "league": "dragon", "tier": "silver" },
      "starred_at": "2026-02-17T..."
    }
  ],
  "updated_at": "2026-02-17T..."
}
```

### Types

```python
FAVORITE_TYPES = [
    "api_key",       # API keys (Polza, OpenRouter, xAI...)
    "model",         # Individual models (grok-4.1-fast, claude-opus...)
    "chat",          # Chat conversations
    "file",          # Files/folders in project tree
    "artifact",      # Pipeline-generated artifacts
    "team_preset",   # Team configurations (dragon_silver, titan_core)
    "workflow",      # DAG workflow templates
]
```

### REST API

```
GET  /api/favorites?type=model          → list favorites, optional type filter
POST /api/favorites                     → add favorite {type, id, meta}
DELETE /api/favorites/{type}/{id}       → remove favorite
GET  /api/favorites/check/{type}/{id}   → is_favorite? (fast O(1))
```

### Migration from v1

```python
# Phase 155 migration: merge 4 systems into one
def migrate_favorites_v1_to_v2():
    items = []

    # 1. From data/favorites.json (keys + models)
    old = json.load("data/favorites.json")
    for k in old["keys"]:
        items.append({"type": "api_key", "id": k, ...})
    for m in old["models"]:
        items.append({"type": "model", "id": m, ...})

    # 2. From data/node_favorites.json (files)
    nodes = json.load("data/node_favorites.json")
    for path, is_fav in nodes["favorites"].items():
        if is_fav:
            items.append({"type": "file", "id": path, ...})

    # 3. From chat_history.json (chats with is_favorite=true)
    for chat in chats:
        if chat.get("is_favorite"):
            items.append({"type": "chat", "id": chat["id"], ...})

    # Write unified file
    json.dump({"version": 2, "items": items}, "data/favorites_v2.json")
```

### Consumers

| Consumer | How it uses favorites |
|----------|----------------------|
| **ModelDirectory** | Star keys/models, auto-filter (current behavior) |
| **ChatSidebar** | Star chats, sort to top |
| **TreePanel** | Star files/folders |
| **Architect** | "User prefers Polza models" in planning prompt |
| **Jarvis** | "User's favorite tools: Grok, Polza, dragon_silver" |
| **Eval/Verifier** | Feedback weight: starred models get higher trust baseline |
| **Team Creator** | Pre-fill with starred models when creating new team |

---

## Architecture: Model Weight Classes

### Concept

Every model belongs to one or more **weight classes** based on measurable specs:

```
                    CONTEXT CAPACITY
                    (how much fits)
                         |
            Feather  Welter  Middle  Heavy  Super
            <32K    32-64K  64-128K 128-256K >256K
                         |
                    SPEED CLASS
                    (output TPS)
                         |
            Turtle  Steady  Quick   Flash   Turbo
            <20     20-40   40-80   80-150  >150
                         |
                    COST CLASS
                    ($ per 1M output tokens)
                         |
            Free    Cheap   Mid     Premium  Elite
            $0      <$1     $1-5    $5-20    >$20
```

### Weight Class Matrix

From existing data in `llm_model_registry.py` (`_SAFE_DEFAULTS`):

| Model | Context | Speed | Cost | Weight Classes |
|-------|---------|-------|------|----------------|
| grok-4.1-fast | 131K (Heavy) | 90 TPS (Flash) | ~$0.60/M (Cheap) | Heavy-Flash-Cheap |
| claude-opus-4.6 | 200K (Super) | 40 TPS (Steady) | ~$75/M (Elite) | Super-Steady-Elite |
| qwen3-coder-flash | 131K (Heavy) | 85 TPS (Flash) | ~$0.40/M (Cheap) | Heavy-Flash-Cheap |
| qwen3-235b | 131K (Heavy) | 30 TPS (Steady) | ~$4/M (Mid) | Heavy-Steady-Mid |
| kimi-k2.5 | 131K (Heavy) | 50 TPS (Quick) | ~$1.60/M (Mid) | Heavy-Quick-Mid |
| gemini-2.0-flash | 1M (Super) | 100 TPS (Flash) | ~$0.30/M (Cheap) | Super-Flash-Cheap |
| gpt-5.2 | 200K (Super) | 35 TPS (Steady) | ~$30/M (Elite) | Super-Steady-Elite |
| haiku-3.5 | 200K (Super) | 100+ TPS (Turbo) | ~$1/M (Cheap) | Super-Turbo-Cheap |

### Role Suitability by Weight Class

```python
ROLE_WEIGHT_REQUIREMENTS = {
    "scout": {
        # Fast scan, small context ok, cheap
        "speed": ["Flash", "Turbo"],
        "cost": ["Free", "Cheap"],
        "context": "any",
    },
    "architect": {
        # Needs intelligence (big model), large context for planning
        "speed": "any",
        "cost": ["Mid", "Premium", "Elite"],
        "context": ["Heavy", "Super"],
    },
    "researcher": {
        # Fast, web-aware, medium context
        "speed": ["Quick", "Flash", "Turbo"],
        "cost": "any",
        "context": ["Middle", "Heavy", "Super"],
    },
    "coder": {
        # Large context (reads files), moderate speed, code-specialized
        "speed": ["Steady", "Quick", "Flash"],
        "cost": "any",
        "context": ["Heavy", "Super"],
    },
    "verifier": {
        # Fast validation, small context ok, cheap
        "speed": ["Quick", "Flash", "Turbo"],
        "cost": ["Free", "Cheap", "Mid"],
        "context": "any",
    },
}
```

### Dynamic Team Assembly

Instead of hardcoded presets, Architect can **compose teams** from weight classes:

```python
# Current: static preset
preset = "dragon_silver"  # always Kimi + Grok + Qwen + GLM

# Phase 155: dynamic weight-class team
team = assemble_team(
    budget="cheap",           # Dragon league constraint
    task_complexity="medium",
    user_favorites=["polza"],  # From favorites service
    role_requirements=ROLE_WEIGHT_REQUIREMENTS,
    available_models=model_registry.get_healthy_models(),
)
# Result: picks best model per role from healthy + favorited + weight-matched pool
```

### Storage: `data/model_weight_classes.json`

Auto-generated from `llm_model_registry.py` profiles:

```json
{
  "generated_at": "2026-02-17T...",
  "source": "llm_model_registry + artificial_analysis",
  "classes": {
    "x-ai/grok-4.1-fast": {
      "context_class": "heavy",
      "speed_class": "flash",
      "cost_class": "cheap",
      "composite": "heavy-flash-cheap",
      "suitable_roles": ["scout", "researcher", "verifier", "coder"],
      "leagues": ["dragon_silver", "dragon_gold", "titan_lite"]
    }
  },
  "role_coverage": {
    "scout": ["qwen3-30b", "grok-4.1-fast", "haiku-3.5", ...],
    "architect": ["kimi-k2.5", "claude-opus", "gpt-5.2", ...],
    "coder": ["qwen3-coder", "qwen3-coder-flash", "gpt-5.2", ...],
    ...
  }
}
```

### Integration with Existing Systems

```
llm_model_registry.py (ModelProfile: context_length, output_tps, cost)
        |
        v
model_weight_classifier.py (NEW — computes weight classes from profiles)
        |
        +---> data/model_weight_classes.json (cache, auto-regenerated)
        |
        +---> agent_pipeline.py (_resolve_tier → now weight-class aware)
        |
        +---> pipeline_analytics.py (team_comparison by weight class)
        |
        +---> Architect prompt: "Available models by weight class: ..."
        |
        +---> Eval agent: "Model X is Heavy-Flash-Cheap, expected quality: ..."
```

---

## Eval Agent & Feedback Loop

### How favorites + weight classes improve evaluation

```
User stars model ──> FavoritesService.add("model", id)
                          |
                          v
Architect reads favorites ──> "User trusts grok-4.1-fast (starred)"
                          |
                          v
Coder uses starred model ──> pipeline executes
                          |
                          v
Verifier evaluates ──> confidence score + issues
                          |
                          v
User feedback ──> "applied" / "rejected" / "rework"
                          |
                          v
Eval agent correlates ──> "grok-4.1-fast as coder: 87% applied rate"
                          |       "qwen3-coder as coder: 92% applied rate"
                          |
                          v
Weight class analytics ──> "Heavy-Flash-Cheap models: avg 85% for coder role"
                          |   "Heavy-Quick-Mid models: avg 90% for coder role"
                          |
                          v
Architect learns ──> Next time prefers Quick-Mid for coder if budget allows
                          |
                          v
Jarvis reports ──> "Your team performs best with Kimi as architect, Qwen as coder"
```

### Eval Agent Model Selection

```python
# MARKER_155.EVAL: Weight-class-aware model selection for eval/verifier
def select_verifier_model(task_complexity, budget_tier):
    """Pick verifier from weight class pool, not hardcoded preset."""
    candidates = weight_classifier.get_models_for_role("verifier")

    # Filter by budget
    if budget_tier == "dragon":
        candidates = [m for m in candidates if m.cost_class in ["free", "cheap"]]

    # Prefer user's starred models
    favorites = favorites_service.list(type="model")
    fav_ids = {f["id"] for f in favorites}
    starred = [m for m in candidates if m.model_id in fav_ids]

    # Prefer models with high historical success rate
    for m in candidates:
        m.eval_score = analytics.get_model_success_rate(m.model_id, role="verifier")

    # Sort: starred first, then by eval_score
    pool = sorted(starred, key=lambda m: -m.eval_score) + \
           sorted([m for m in candidates if m not in starred], key=lambda m: -m.eval_score)

    return pool[0] if pool else fallback_verifier
```

---

## Implementation Plan

### Wave 0: Research (Grok)
- Benchmark existing model speed/cost data accuracy
- Survey: Artificial Analysis API vs OpenRouter vs LiteLLM for model metadata
- Design weight class thresholds (context/speed/cost boundaries)

### Wave 1: Backend — FavoritesService (Opus, ~30 lines core)
- `src/services/favorites_service.py` — unified CRUD
- Migration script: merge 4 systems into `favorites_v2.json`
- REST API: GET/POST/DELETE /api/favorites
- ENGRAM sync on every write (fire-forget, all types)
- CAM events for all favorite types (not just chats)
- **Backward compat:** old endpoints still work, delegate to new service

### Wave 2: Backend — ModelWeightClassifier (Opus, ~80 lines)
- `src/elisya/model_weight_classifier.py` — compute classes from ModelProfile
- Auto-generate `data/model_weight_classes.json` on startup
- Role suitability matrix
- Integration with `_resolve_tier()` in agent_pipeline.py

### Wave 3: Frontend — Unified Star UI (Codex)
- All star toggles call same endpoint: `POST /api/favorites`
- ModelDirectory, ChatSidebar, TreePanel — unified toggle hook
- Team creator: pre-fill from starred models

### Wave 4: Intelligence — Architect + Eval (Opus + Dragon)
- Architect prompt: inject starred models + weight classes
- Eval agent: correlate weight class with success rate
- Jarvis: "your team performance by weight class" report
- MARKER_155.EVAL: Weight-class-aware verifier selection

---

## MARKERs

```
MARKER_155.FAV_SERVICE     — Unified FavoritesService core
MARKER_155.FAV_MIGRATE     — Migration from v1 (4 systems) to v2 (1 system)
MARKER_155.WEIGHT_CLASS    — ModelWeightClassifier implementation
MARKER_155.WEIGHT_CACHE    — Auto-generated weight class cache
MARKER_155.ROLE_MATRIX     — Role suitability by weight class
MARKER_155.DYNAMIC_TEAM    — Weight-class-aware team assembly
MARKER_155.EVAL            — Eval agent model selection by weight class
MARKER_155.JARVIS          — Jarvis favorite/weight-class reporting
```

---

## Dependencies

```
Phase 152.FIX3 (star favorites)        → foundation, migrate from
Phase 151.12 (adjusted_stats)          → user feedback scores
Phase 145 (adaptive timeout)           → ModelProfile with speed/context
Phase 126.0 (pipeline stats)           → per-model success tracking
Phase 122 (feedback loops)             → verifier confidence → eval
llm_model_registry.py                  → ModelProfile dataclass
model_presets.json                     → league/tier definitions
pipeline_analytics.py                  → cost + weak link detection
```

## Estimated Effort

| Wave | Agent | Effort | Files |
|------|-------|--------|-------|
| 0 | Grok | 1 day | research doc |
| 1 | Opus | 1 day | favorites_service.py, config_routes.py, migration |
| 2 | Opus | 1 day | model_weight_classifier.py, model_presets.json |
| 3 | Codex | 1-2 days | ModelDirectory, ChatSidebar, TreePanel |
| 4 | Opus+Dragon | 2 days | agent_pipeline.py, pipeline_prompts.json, eval |

**Total: ~6-7 days**
