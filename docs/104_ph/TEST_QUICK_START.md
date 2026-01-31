# Phase 104: Test Quick Start Guide

**MARKER_104_TESTS** - Architecture Merge Test Suite Quick Reference

## Installation

Ensure pytest and pytest-asyncio are installed:

```bash
pip install pytest pytest-asyncio
```

## Quick Commands

### Run All Tests (89 total)
```bash
pytest tests/test_phase104_arch_merge.py -v
```

### Run by Feature

**Feature Flag Tests (4 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestFeatureFlagToggling -v
```

**Pipeline Loop Tests (7 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestExecutePipelineLoop -v
```

**Architect Planning Tests (6 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestPipelineArchitectPlan -v
```

**Research Loop Tests (7 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestPipelineResearch -v
```

**Subtask Prompt Tests (9 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestBuildSubtaskPrompt -v
```

**Code Extraction Tests (8 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestExtractCodeBlocks -v
```

**Task Storage Tests (5 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestSavePipelineTask -v
```

**JSON Extraction Tests (8 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestExtractJsonRobust -v
```

**Hybrid Flow Integration (5 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestHybridFlowIntegration -v
```

**Researcher Auto-Trigger (5 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestResearcherAutoTrigger -v
```

**STM Context Passing (6 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestSTMContextPassing -v
```

**Error Handling (6 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestErrorHandlingAndEdgeCases -v
```

**Parametrized Tests (12 tests)**
```bash
pytest tests/test_phase104_arch_merge.py::TestParametrizedWorkflows -v
```

### Run by Marker

```bash
# All architecture merge tests
pytest tests/test_phase104_arch_merge.py -m architecture_merge -v

# Pipeline loop tests
pytest tests/test_phase104_arch_merge.py -m pipeline_loop -v

# Feature flag tests
pytest tests/test_phase104_arch_merge.py -m feature_flag -v

# Integration tests
pytest tests/test_phase104_arch_merge.py -m integration -v

# Async tests only
pytest tests/test_phase104_arch_merge.py -m asyncio -v
```

### Specific Test

```bash
# Single test
pytest tests/test_phase104_arch_merge.py::TestFeatureFlagToggling::test_feature_flag_enabled -v
```

### With Output

```bash
# Show print statements
pytest tests/test_phase104_arch_merge.py -v -s

# Show full tracebacks
pytest tests/test_phase104_arch_merge.py -v --tb=long

# Stop on first failure
pytest tests/test_phase104_arch_merge.py -v -x

# Show coverage
pytest tests/test_phase104_arch_merge.py -v --cov=src.orchestration --cov-report=html
```

## Test Collection

List all tests without running:
```bash
pytest tests/test_phase104_arch_merge.py --collect-only -q
```

Expected output: **89 tests collected in 0.02s**

## Fixtures Available

All tests have access to:

- `mock_elisya_state` - Mock ElisyaState object
- `sample_subtasks` - 3 test subtasks
- `sample_architect_plan` - Valid plan structure
- `sample_research_response` - Valid research response
- `sample_code_response_with_artifacts` - LLM response with code blocks

## Test Markers

Register custom markers in `pytest.ini`:

```ini
@pytest.mark.architecture_merge  # Phase 104 method tests
@pytest.mark.pipeline_loop       # Pipeline loop tests
@pytest.mark.elisya_integration  # ElisyaState tests
@pytest.mark.feature_flag        # Feature flag tests
@pytest.mark.phase_104           # All Phase 104 tests
@pytest.mark.integration         # Integration tests
@pytest.mark.asyncio             # Async/await tests
```

## Success Criteria

✅ All 89 tests pass
✅ No import errors
✅ No syntax errors
✅ pytest.ini markers registered
✅ Fixtures import correctly

## Troubleshooting

### "Module not found" error
```bash
# Add project to PYTHONPATH
export PYTHONPATH=/Users/danilagulin/Documents/VETKA_Project/vetka_live_03:$PYTHONPATH
pytest tests/test_phase104_arch_merge.py -v
```

### "pytest: command not found"
```bash
# Use python module syntax
python -m pytest tests/test_phase104_arch_merge.py -v
```

### Async test failures
Ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

### Marker warnings
Ensure `pytest.ini` exists with marker definitions (already created)

## Example Output

```
tests/test_phase104_arch_merge.py::TestFeatureFlagToggling::test_feature_flag_default_disabled PASSED
tests/test_phase104_arch_merge.py::TestFeatureFlagToggling::test_feature_flag_enabled PASSED
tests/test_phase104_arch_merge.py::TestFeatureFlagToggling::test_feature_flag_case_insensitive PASSED
tests/test_phase104_arch_merge.py::TestFeatureFlagToggling::test_feature_flag_false_values PASSED
tests/test_phase104_arch_merge.py::TestExecutePipelineLoop::test_pipeline_loop_initialization PASSED
...
========================= 89 passed in 1.23s =========================
```

## Integration with Implementation

When implementing the 7 methods:

1. Create stub methods returning mock values
2. Run tests to verify test coverage: `pytest tests/test_phase104_arch_merge.py --collect-only`
3. Implement one method at a time
4. Run tests after each implementation: `pytest tests/test_phase104_arch_merge.py -v`
5. Fix any failures
6. Move to next method

Example sequence:
```python
# In orchestrator_with_elisya.py

# Step 1: Add stub
async def _execute_pipeline_loop(self, ...):
    return "mock_output", self.elisya_state, []

# Step 2: Run tests
# pytest tests/test_phase104_arch_merge.py::TestExecutePipelineLoop -v

# Step 3: Implement real logic
async def _execute_pipeline_loop(self, architect_output, elisya_state, ...):
    # ... full implementation from MERGE_IMPLEMENTATION_GUIDE.md
    pass

# Step 4: Run tests again
# pytest tests/test_phase104_arch_merge.py::TestExecutePipelineLoop -v
```

## References

- **Test File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase104_arch_merge.py`
- **Coverage Details:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/104_ph/PHASE104_TEST_COVERAGE.md`
- **Implementation Guide:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/104_ph/MERGE_IMPLEMENTATION_GUIDE.md`
- **pytest docs:** https://docs.pytest.org/

---

**Header:** MARKER_104_TESTS
**Status:** Ready for implementation
