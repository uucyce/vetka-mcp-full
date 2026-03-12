# Contributing to REFLEX

Thank you for your interest in contributing to REFLEX!

## Development Setup

```bash
git clone https://github.com/danilagoleen/reflex-tool-engine.git
cd reflex-tool-engine
pip install -e ".[dev]"
pytest -v
```

## Guidelines

1. **Zero external dependencies** for core modules. Optional deps go in `[project.optional-dependencies]`.
2. **Performance**: Scoring must stay under 5ms. No LLM calls in the scoring path.
3. **Thread safety**: All file writes use `threading.Lock`. All state is append-only.
4. **Tests**: Add tests for new features. Target: every public method has at least one test.
5. **Markers**: Use `MARKER_XXX.Y` convention for code comments referencing phases.

## Architecture

- `scorer.py` — Pure scoring engine. 8 signals, configurable weights. No side effects.
- `registry.py` — Tool catalog loader. JSON-backed, immutable after load.
- `feedback.py` — Append-only JSONL log. Thread-safe writes. Aggregation with decay.
- `integration.py` — Hooks for pipeline injection. pre_fc → LLM → post_fc → verifier.
- `filter.py` — Active tool schema filtering per model tier.
- `preferences.py` — User pin/ban overrides.
- `decay.py` — Score decay with phase-specific half-lives.
- `streaming.py` — WebSocket event emission.
- `experiment.py` — A/B testing framework.

## Pull Requests

- Keep PRs focused — one feature/fix per PR
- Include tests
- Update README if adding new public API
- Maintain backward compatibility

## Code of Conduct

Be respectful. We're building tools to make AI agents better — let's be good humans while doing it.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
