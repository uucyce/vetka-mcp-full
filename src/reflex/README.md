# REFLEX — Reactive Tool Recommendation Engine

**Intelligent tool scoring & recommendation for LLM agent pipelines.**

REFLEX observes which tools agents use, learns from outcomes, and recommends the best tools for each context — making AI pipelines faster and more accurate.

## What it does

```
Agent gets task → REFLEX scores 45+ tools → Top-5 recommended → Agent picks → Outcome recorded → REFLEX learns
```

### 8-Signal Scoring Engine

| Signal | Source | Weight | Description |
|--------|--------|--------|-------------|
| Semantic Match | Vector similarity | 0.30 | Task embedding vs tool intent tags |
| Feedback Score | Historical outcomes | 0.20 | Success rate from past usage |
| Phase Match | Pipeline phase | 0.15 | Fix → debug tools, Build → write tools |
| ENGRAM Preference | User memory | 0.10 | User's preferred tools (long-term) |
| CAM Surprise | Context memory | 0.08 | Novel context → broader tool palette |
| STM Relevance | Short-term memory | 0.07 | Recent working memory items |
| HOPE LOD | Viewport zoom | 0.05 | Zoom level → tool granularity |
| MGC Heat | Cache stats | 0.05 | Cache tier → file context relevance |

### Feedback Loop

```
REFLEX recommends → Agent uses tools → Verifier checks result → Outcome recorded → Scores updated
```

- `match_rate` = intersection(recommended, used) / len(recommended)
- Success/failure feeds back into scoring
- Exponential decay on old entries (configurable half-life)

## Architecture

```
src/reflex/
├── __init__.py          # Public API
├── scorer.py            # 8-signal scoring engine (<5ms, no LLM calls)
├── registry.py          # Tool catalog (JSON-backed, auto-discovery)
├── feedback.py          # JSONL feedback log + aggregation
├── integration.py       # Pipeline injection hooks (pre_fc, post_fc, verifier)
├── filter.py            # Active tool schema filtering (per model tier)
├── preferences.py       # User pin/ban tool overrides
├── decay.py             # Score decay + phase-specific half-lives
├── streaming.py         # WebSocket event streaming
├── experiment.py        # A/B testing framework
├── data/
│   └── tool_catalog.json  # 45+ tool definitions
└── LICENSE              # MIT
```

## Quick Start

```python
from reflex import ReflexScorer, ReflexRegistry, ReflexFeedback

# Load tool catalog
registry = ReflexRegistry()
tools = registry.get_tools_for_role("coder")

# Score tools for a task
scorer = ReflexScorer(registry)
recommendations = scorer.recommend(
    context={"task": "fix the login bug", "phase": "fix"},
    available_tools=tools,
    top_n=5
)

for rec in recommendations:
    print(f"  {rec.tool_id}: {rec.score:.2f} — {rec.reason}")

# Record feedback after use
feedback = ReflexFeedback()
feedback.record(
    tool_id="vetka_edit_file",
    success=True,
    useful=True,
    phase_type="fix"
)

# Get feedback summary
summary = feedback.get_feedback_summary()
print(f"Success rate: {summary['success_rate']:.0%}")
```

## Pipeline Integration

REFLEX hooks into LLM function-calling loops:

```python
from reflex.integration import reflex_pre_fc, reflex_post_fc

# Before LLM call: get recommendations
recommendations = reflex_pre_fc(subtask, available_tools)

# After LLM call: record what was actually used
reflex_post_fc(subtask, tool_calls_made, recommendations)
```

### Universal Hooks

REFLEX injects at the LLM call choke point — every model call through the ecosystem gets:
- Pre-hook: tool recommendations logged
- Post-hook: actual tool usage recorded
- Match rate tracked across all surfaces

## Active Filtering (Optional)

Reduce tokens sent to LLM by filtering tool schemas based on scores:

```python
from reflex.filter import filter_tool_schemas

# Gold models: all tools | Silver: top 15 | Bronze: top 8
filtered = filter_tool_schemas(all_tools, context, model_tier="silver")
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `REFLEX_ENABLED` | `true` | Master switch |
| `REFLEX_SEMANTIC_WEIGHT` | `0.30` | Semantic match weight |
| `REFLEX_FEEDBACK_WEIGHT` | `0.20` | Feedback score weight |
| `REFLEX_PHASE_WEIGHT` | `0.15` | Phase match weight |
| `REFLEX_CONFIDENCE_THRESHOLD` | `0.3` | Minimum score to recommend |

## Performance

- Scoring: **<5ms** per recommendation (no LLM calls)
- Registry load: **<10ms**
- Feedback write: async, non-blocking
- Zero external dependencies beyond Python stdlib

## License

MIT — see [LICENSE](LICENSE)

## Part of VETKA

REFLEX is a standalone module extracted from the [VETKA AI](https://github.com/danilagoleen/vetka) spatial intelligence platform. It powers tool recommendation across Dragon pipelines, MCC workflows, and multi-agent systems.
