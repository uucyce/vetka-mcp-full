# Phase 104: Architecture Merge Test Coverage

**File:** `tests/test_phase104_arch_merge.py`
**Header:** `MARKER_104_TESTS`
**Total Tests:** 89
**Status:** Ready for implementation validation

---

## Overview

Comprehensive test suite for 7 new methods from MERGE_IMPLEMENTATION_GUIDE.md. Tests validate:

- ✅ Hybrid flow: PM → Architect → [PIPELINE LOOP] → Dev||QA
- ✅ ElisyaState preservation through pipeline loop
- ✅ Feature flag toggling (VETKA_PIPELINE_ENABLED)
- ✅ Researcher auto-trigger on `needs_research=True`
- ✅ STM (Short-Term Memory) context passing between subtasks
- ✅ Artifact extraction for approval gate
- ✅ Error handling & graceful degradation

---

## Test Organization

### 1. Feature Flag Tests (4 tests)
**Class:** `TestFeatureFlagToggling`
**Marker:** `@pytest.mark.feature_flag`

Tests for VETKA_PIPELINE_ENABLED environment variable:

```python
test_feature_flag_default_disabled()          # Default: disabled
test_feature_flag_enabled()                   # Enable via env
test_feature_flag_case_insensitive()          # "TRUE"/"true"/"True"
test_feature_flag_false_values()              # "false"/"0"/"no"
```

**Run single class:**
```bash
pytest tests/test_phase104_arch_merge.py::TestFeatureFlagToggling -v
```

---

### 2. Execute Pipeline Loop Tests (7 tests)
**Class:** `TestExecutePipelineLoop`
**Marker:** `@pytest.mark.pipeline_loop`
**Method:** `_execute_pipeline_loop()`

Tests for main pipeline loop execution:

```python
test_pipeline_loop_initialization()                   # Task creation
test_pipeline_loop_stm_injection()                    # STM context injection
test_pipeline_loop_preserves_elisya_state()           # State preservation
test_pipeline_loop_artifact_extraction_in_build_phase() # Code extraction
test_pipeline_loop_no_artifacts_in_research_phase()   # Skip extraction for research
test_pipeline_loop_stm_limit_enforcement()            # STM size limits
test_pipeline_loop_merged_output_generation()         # Output compilation
```

**Key validations:**
- Pipeline task creation with proper status tracking
- STM markers preserved in context
- ElisyaState workflow_id and semantic_path unchanged
- Code blocks extracted only in build phase
- STM respects 5-item limit
- Merged output includes all subtask results

---

### 3. Architect Planning Tests (6 tests)
**Class:** `TestPipelineArchitectPlan`
**Marker:** `@pytest.mark.pipeline_loop`, `@pytest.mark.architecture_merge`
**Method:** `_pipeline_architect_plan()`

Tests for task breakdown into subtasks:

```python
test_architect_plan_valid_structure()              # Required fields
test_architect_plan_subtask_fields()               # Each subtask structure
test_architect_plan_complexity_levels()            # low|medium|high
test_architect_plan_execution_order_options()      # sequential|parallel
test_architect_plan_fallback_on_error()            # Graceful degradation
test_architect_plan_research_flag_marking()        # needs_research flag
```

**Key validations:**
- Plan has subtasks, execution_order, estimated_complexity
- Each subtask has description, needs_research, marker
- Complexity in {low, medium, high}
- Execution order in {sequential, parallel}
- Fallback creates single research subtask on error
- Research-needed subtasks properly identified

---

### 4. Research Loop Tests (7 tests)
**Class:** `TestPipelineResearch`
**Marker:** `@pytest.mark.pipeline_loop`, `@pytest.mark.architecture_merge`
**Method:** `_pipeline_research()`

Tests for deep research on unclear subtasks:

```python
test_research_valid_response_structure()           # Required fields
test_research_confidence_range()                   # [0.0, 1.0]
test_research_recursive_trigger_threshold()        # confidence < 0.7
test_research_further_questions_limit()            # Max 2 recursive calls
test_research_actionable_steps_structure()         # Step format
test_research_fallback_on_parse_error()            # JSON parse fallback
test_research_context_enrichment()                 # Enriched context
```

**Key validations:**
- Response has insights, actionable_steps, enriched_context, confidence
- Confidence in [0, 1] range
- Recursion triggers when confidence < 0.7
- Max 2 recursive questions limit
- Actionable steps have required fields
- JSON parse errors handled gracefully
- Enriched context preserved

---

### 5. Build Subtask Prompt Tests (9 tests)
**Class:** `TestBuildSubtaskPrompt`
**Marker:** `@pytest.mark.pipeline_loop`, `@pytest.mark.architecture_merge`
**Method:** `_build_subtask_prompt()`

Tests for prompt construction with injected context:

```python
test_prompt_includes_description()                # Subtask description
test_prompt_includes_marker()                     # Marker in prompt
test_prompt_includes_research_context()           # Research context section
test_prompt_includes_previous_results()           # STM section
test_prompt_build_phase_guidance()                # Build instructions
test_prompt_fix_phase_guidance()                  # Fix instructions
test_prompt_research_phase_guidance()             # Research instructions
test_prompt_complete_with_all_context()           # All sections present
```

**Key validations:**
- Description included in prompt
- Marker included when available
- Research context section added when present
- Previous results (STM) section added
- Phase-specific guidance included
- Complete prompt > 100 chars with all sections

---

### 6. Code Block Extraction Tests (8 tests)
**Class:** `TestExtractCodeBlocks`
**Marker:** `@pytest.mark.architecture_merge`
**Method:** `_extract_code_blocks()`

Tests for artifact extraction from LLM responses:

```python
test_extract_single_code_block()                  # Single block
test_extract_multiple_code_blocks()               # Multiple blocks
test_extract_code_block_without_language()        # No language spec
test_extract_filepath_from_description()          # Path extraction
test_extract_multiple_filepaths()                 # Multiple paths
test_no_code_blocks_returns_empty()               # Empty response
test_artifact_size_tracking()                     # Size calculation
test_language_identification_common_languages()   # Language detection
```

**Key validations:**
- Single and multiple code blocks extracted
- Language detection (python, javascript, etc.)
- Filepath extraction from descriptions
- Multiple filepaths found
- Empty response returns empty list
- Artifact sizes calculated
- Common languages recognized (python, js, ts, json, yaml, sql)

---

### 7. Task Storage Tests (5 tests)
**Class:** `TestSavePipelineTask`
**Marker:** `@pytest.mark.architecture_merge`
**Method:** `_save_pipeline_task()`

Tests for task persistence:

```python
test_pipeline_task_serialization()                # Task → dict
test_subtask_serialization()                      # Subtask → dict
test_pipeline_task_json_compatibility()           # Task → JSON
test_tasks_file_path_defined()                    # TASKS_FILE path
test_pipeline_task_results_structure()            # Results dict
```

**Key validations:**
- PipelineTask converts to dict with asdict()
- Subtask converts to dict
- JSON serialization works
- TASKS_FILE path includes "pipeline_tasks.json"
- Results structure valid

---

### 8. JSON Extraction Tests (8 tests)
**Class:** `TestExtractJsonRobust`
**Marker:** `@pytest.mark.architecture_merge`
**Method:** `_extract_json_robust()`

Tests for robust JSON extraction from LLM responses:

```python
test_extract_raw_json()                          # Direct JSON
test_extract_json_from_markdown_block()           # ```json ... ```
test_extract_json_from_generic_code_block()       # ``` ... ```
test_extract_json_embedded_in_prose()             # Embedded JSON
test_extract_json_from_first_brace()              # From first {
test_extract_json_with_nested_objects()           # Nested structures
test_empty_text_handling()                        # Empty input
test_json_extraction_strategy_priority()          # Strategy fallback
```

**Key validations:**
- Raw JSON parsed directly
- JSON extracted from markdown blocks
- JSON extracted from generic code blocks
- JSON embedded in prose extracted
- JSON extracted from first brace position
- Nested JSON objects handled
- Empty text returns {}
- Multiple strategies tried with fallback

---

### 9. Hybrid Flow Integration Tests (5 tests)
**Class:** `TestHybridFlowIntegration`
**Markers:** `@pytest.mark.integration`, `@pytest.mark.pipeline_loop`

Tests for end-to-end PM → Architect → Pipeline → Dev||QA flow:

```python
test_hybrid_flow_phase_sequence()                 # Phase order
test_elisya_state_preserved_through_pipeline()    # State integrity
test_pipeline_artifacts_available_for_dev_qa()    # Artifacts in result
test_dev_qa_can_use_pipeline_context()            # Context usage
test_hybrid_flow_graceful_degradation()           # Fallback on error
```

**Key validations:**
- Phase sequence: PM → Architect → Dev
- ElisyaState workflow_id/path unchanged
- Artifacts available in result
- Dev/QA can access pipeline context
- System degrades gracefully on pipeline failure

---

### 10. Researcher Auto-Trigger Tests (5 tests)
**Class:** `TestResearcherAutoTrigger`
**Marker:** `@pytest.mark.pipeline_loop`, `@pytest.mark.architecture_merge`

Tests for automatic researcher activation:

```python
test_auto_trigger_on_needs_research_flag()       # Flag detection
test_auto_trigger_uses_question_when_available() # Question usage
test_auto_trigger_falls_back_to_description()    # Fallback logic
test_recursive_research_on_low_confidence()       # Recursion trigger
test_high_confidence_skips_recursion()            # High confidence skip
```

**Key validations:**
- Research triggered when needs_research=True
- Question used when available
- Falls back to description
- Confidence < 0.7 triggers recursion
- Confidence >= 0.7 skips recursion

---

### 11. STM Context Passing Tests (6 tests)
**Class:** `TestSTMContextPassing`
**Marker:** `@pytest.mark.pipeline_loop`, `@pytest.mark.architecture_merge`

Tests for Short-Term Memory between subtasks:

```python
test_stm_buffer_initialization()                  # Empty STM
test_stm_add_result()                             # Add to STM
test_stm_limit_enforcement()                      # Size limit (5)
test_stm_summary_generation()                     # Summary format
test_stm_context_injection_into_subtask()         # Injection logic
test_stm_overflow_removes_oldest()                # FIFO removal
```

**Key validations:**
- STM starts empty
- Items added correctly
- Size limit enforced (max 5)
- Summary generation includes markers
- Context injected into subtasks
- Oldest items removed on overflow

---

### 12. Error Handling Tests (6 tests)
**Class:** `TestErrorHandlingAndEdgeCases`
**Marker:** `@pytest.mark.architecture_merge`

Tests for error handling and edge cases:

```python
test_empty_architect_output()                     # Empty input
test_no_subtasks_in_plan()                        # Empty plan
test_subtask_with_null_context()                  # Null context
test_malformed_json_response()                    # Bad JSON
test_pipeline_graceful_degradation()              # Error recovery
test_code_extraction_with_empty_blocks()          # Empty blocks
```

**Key validations:**
- Empty output handled
- Empty plans handled gracefully
- Null context initialized to {}
- Malformed JSON detected
- Pipeline continues on error
- Empty code blocks skipped

---

### 13. Parametrized Tests (12 tests)
**Class:** `TestParametrizedWorkflows`
**Marker:** `@pytest.mark.architecture_merge`

Parametrized tests for multiple scenarios:

```python
test_phase_specific_guidance[build/fix/research]  # 3 tests
test_research_recursion_threshold[0.5-0.95]       # 5 tests
test_language_detection[python/js/ts/json/yaml/sql] # 6 tests
```

**Run parametrized tests:**
```bash
pytest tests/test_phase104_arch_merge.py::TestParametrizedWorkflows -v
```

---

## Test Execution

### Run all Phase 104 tests:
```bash
pytest tests/test_phase104_arch_merge.py -v
```

### Run by marker:
```bash
# All architecture merge tests
pytest tests/test_phase104_arch_merge.py -m architecture_merge -v

# Pipeline loop tests only
pytest tests/test_phase104_arch_merge.py -m pipeline_loop -v

# Feature flag tests
pytest tests/test_phase104_arch_merge.py -m feature_flag -v

# Integration tests
pytest tests/test_phase104_arch_merge.py -m integration -v
```

### Run specific test class:
```bash
pytest tests/test_phase104_arch_merge.py::TestExecutePipelineLoop -v
```

### Run with coverage:
```bash
pytest tests/test_phase104_arch_merge.py --cov=src.orchestration --cov-report=html
```

### Run async tests only:
```bash
pytest tests/test_phase104_arch_merge.py -m asyncio -v
```

---

## Test Fixtures

All tests use shared fixtures defined at module level:

### `mock_elisya_state`
Mock ElisyaState with:
- workflow_id: "test_workflow_104"
- speaker tracking
- conversation_history
- add_message() method

### `sample_subtasks`
3 pre-configured Subtask objects:
1. Feature A (no research)
2. Feature B (needs research)
3. Tests C (no research)

### `sample_architect_plan`
Valid architect plan with 3 subtasks and metadata

### `sample_research_response`
Valid research response with insights and confidence

### `sample_code_response_with_artifacts`
LLM response with 3 code blocks (python, python, javascript)

---

## Implementation Validation Checklist

Before implementing the 7 methods, ensure:

- [ ] All 89 tests collect without errors
- [ ] pytest.ini registers custom markers
- [ ] Fixtures import correctly
- [ ] No syntax errors in test file

After implementing methods:

- [ ] All tests pass: `pytest tests/test_phase104_arch_merge.py -v`
- [ ] Feature flag tests pass
- [ ] Pipeline loop tests pass
- [ ] Async tests pass with pytest-asyncio
- [ ] Mock objects can be replaced with real implementations

---

## Method-to-Test Mapping

| Method | Test Class | Tests | Markers |
|--------|-----------|-------|---------|
| `_execute_pipeline_loop()` | TestExecutePipelineLoop | 7 | pipeline_loop |
| `_pipeline_architect_plan()` | TestPipelineArchitectPlan | 6 | pipeline_loop, architecture_merge |
| `_pipeline_research()` | TestPipelineResearch | 7 | pipeline_loop, architecture_merge |
| `_build_subtask_prompt()` | TestBuildSubtaskPrompt | 9 | pipeline_loop, architecture_merge |
| `_extract_code_blocks()` | TestExtractCodeBlocks | 8 | architecture_merge |
| `_save_pipeline_task()` | TestSavePipelineTask | 5 | architecture_merge |
| `_extract_json_robust()` | TestExtractJsonRobust | 8 | architecture_merge |
| Feature Flag | TestFeatureFlagToggling | 4 | feature_flag |
| Integration | TestHybridFlowIntegration | 5 | integration, pipeline_loop |
| Researcher | TestResearcherAutoTrigger | 5 | pipeline_loop, architecture_merge |
| STM | TestSTMContextPassing | 6 | pipeline_loop, architecture_merge |
| Edge Cases | TestErrorHandlingAndEdgeCases | 6 | architecture_merge |
| Parametrized | TestParametrizedWorkflows | 12 | architecture_merge |

**Total: 89 tests across 13 test classes**

---

## Next Steps

1. **Review** this test suite against MERGE_IMPLEMENTATION_GUIDE.md
2. **Implement** the 7 methods in orchestrator_with_elisya.py
3. **Run tests** to validate implementation: `pytest tests/test_phase104_arch_merge.py -v`
4. **Debug** any failures using test output and markers
5. **Iterate** until all tests pass
6. **Commit** with marker: MARKER_104_TESTS_PASSING

---

## References

- MERGE_IMPLEMENTATION_GUIDE.md - Method specifications
- ARCHITECTURE_MERGE_PLAN.md - Design overview
- pytest documentation: https://docs.pytest.org/
- pytest-asyncio: https://github.com/pytest-dev/pytest-asyncio

---

**Generated:** Phase 104 Architecture Merge
**Status:** Ready for implementation
**Header:** MARKER_104_TESTS
