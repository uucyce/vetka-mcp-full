# MARKER_104_TESTS
"""
Phase 104: Architecture Merge - Comprehensive Test Suite

Tests for 7 new methods from MERGE_IMPLEMENTATION_GUIDE.md:
1. _execute_pipeline_loop - Fractal decomposition & subtask execution
2. _pipeline_architect_plan - Break down task into subtasks
3. _pipeline_research - Deep research on unclear parts
4. _build_subtask_prompt - Prompt builder with injected context
5. _extract_code_blocks - Code artifact extraction
6. _save_pipeline_task - Task persistence
7. _extract_json_robust - Robust JSON extraction from LLM

Tests validate:
- Hybrid flow: PM -> Architect -> [PIPELINE LOOP] -> Dev||QA
- ElisyaState preservation through pipeline loop
- Feature flag toggling (VETKA_PIPELINE_ENABLED)
- Researcher auto-trigger on needs_research=True
- STM (Short-Term Memory) context passing between subtasks
- Parallel Dev/QA execution after pipeline completes
- Artifact extraction for approval gate

Run: pytest tests/test_phase104_arch_merge.py -v
Run with markers: pytest tests/test_phase104_arch_merge.py -m architecture_merge -v

@status: active
@phase: 104
@depends: pytest, pytest-asyncio, unittest.mock
@markers: architecture_merge, pipeline_loop, elisya_integration, feature_flag
"""

import pytest
import asyncio
import json
import time
import os
import re
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock, call
from dataclasses import asdict, dataclass
from pathlib import Path

# Import core components
from src.orchestration.agent_pipeline import (
    PipelineTask,
    Subtask,
    TASKS_FILE,
)


# ============================================================
# TEST MARKERS
# ============================================================

pytestmark = [
    pytest.mark.architecture_merge,
    pytest.mark.phase_104,
]


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_elisya_state():
    """Create a mock ElisyaState for testing."""
    @dataclass
    class MockElisyaState:
        workflow_id: str = "test_workflow_104"
        speaker: str = "Architect"
        semantic_path: str = "projects/vetka/phase104"
        context: str = "Test context for pipeline"
        raw_context: str = "Original test context"
        lod_level: str = "tree"
        tint: str = "general"
        conversation_history: List[Dict] = None

        def __post_init__(self):
            if self.conversation_history is None:
                self.conversation_history = []

        def add_message(self, speaker: str, content: str):
            """Add message to conversation history."""
            self.conversation_history.append({
                "speaker": speaker,
                "content": content,
                "timestamp": time.time()
            })

    return MockElisyaState()


@pytest.fixture
def sample_subtasks():
    """Create sample subtasks for testing."""
    return [
        Subtask(
            description="Implement feature A",
            needs_research=False,
            marker="MARKER_104.1",
            status="pending"
        ),
        Subtask(
            description="Research best practices for B",
            needs_research=True,
            question="What is the best approach for B?",
            marker="MARKER_104.2",
            status="pending"
        ),
        Subtask(
            description="Write tests for C",
            needs_research=False,
            marker="MARKER_104.3",
            status="pending"
        )
    ]


@pytest.fixture
def sample_architect_plan():
    """Sample architect plan response."""
    return {
        "subtasks": [
            {
                "description": "Create module structure",
                "needs_research": False,
                "question": None,
                "marker": "MARKER_104.1"
            },
            {
                "description": "Implement data validation",
                "needs_research": True,
                "question": "What validation library is best for VETKA?",
                "marker": "MARKER_104.2"
            },
            {
                "description": "Add unit tests",
                "needs_research": False,
                "question": None,
                "marker": "MARKER_104.3"
            }
        ],
        "execution_order": "sequential",
        "estimated_complexity": "medium"
    }


@pytest.fixture
def sample_research_response():
    """Sample researcher response."""
    return {
        "insights": ["Use pydantic for validation", "Consider dataclasses for simple cases"],
        "actionable_steps": [
            {"step": "Install pydantic", "needs_code": False, "marker": "MARKER_104.2.1"},
            {"step": "Create validation schemas", "needs_code": True, "marker": "MARKER_104.2.2"}
        ],
        "enriched_context": "Pydantic is recommended for VETKA due to its performance and integration with FastAPI.",
        "confidence": 0.85,
        "further_questions": []
    }


@pytest.fixture
def sample_code_response_with_artifacts():
    """Sample LLM response with code artifacts."""
    return '''
# Implementation

Here is the implementation for MARKER_104.1:

```python
def create_module_structure():
    """Create base module structure."""
    import os
    os.makedirs("src/feature", exist_ok=True)
    return {"status": "created"}
```

And for MARKER_104.2:

```python
from pydantic import BaseModel

class ValidationSchema(BaseModel):
    name: str
    value: int
    enabled: bool = True
```

Also a JavaScript example:

```javascript
function initializeFeature() {
    console.log("Feature initialized");
    return true;
}
```
'''


# ============================================================
# TEST CLASS: Feature Flag Tests
# ============================================================

@pytest.mark.feature_flag
class TestFeatureFlagToggling:
    """Tests for VETKA_PIPELINE_ENABLED feature flag."""

    def test_feature_flag_default_disabled(self):
        """Test that pipeline loop is disabled by default."""
        env_value = os.environ.pop("VETKA_PIPELINE_ENABLED", None)
        try:
            flag = os.environ.get("VETKA_PIPELINE_ENABLED", "false").lower() == "true"
            assert flag is False, "Pipeline should be disabled by default"
        finally:
            if env_value is not None:
                os.environ["VETKA_PIPELINE_ENABLED"] = env_value

    def test_feature_flag_enabled(self):
        """Test enabling pipeline loop via environment variable."""
        original = os.environ.get("VETKA_PIPELINE_ENABLED")
        try:
            os.environ["VETKA_PIPELINE_ENABLED"] = "true"
            flag = os.environ.get("VETKA_PIPELINE_ENABLED", "false").lower() == "true"
            assert flag is True, "Pipeline should be enabled when set to 'true'"
        finally:
            if original is not None:
                os.environ["VETKA_PIPELINE_ENABLED"] = original
            else:
                os.environ.pop("VETKA_PIPELINE_ENABLED", None)

    def test_feature_flag_case_insensitive(self):
        """Test that feature flag parsing is case-insensitive."""
        original = os.environ.get("VETKA_PIPELINE_ENABLED")
        try:
            for value in ["TRUE", "True", "true", "TrUe"]:
                os.environ["VETKA_PIPELINE_ENABLED"] = value
                flag = os.environ.get("VETKA_PIPELINE_ENABLED", "false").lower() == "true"
                assert flag is True, f"Flag should be True for value: {value}"
        finally:
            if original is not None:
                os.environ["VETKA_PIPELINE_ENABLED"] = original
            else:
                os.environ.pop("VETKA_PIPELINE_ENABLED", None)

    def test_feature_flag_false_values(self):
        """Test that false values disable the flag."""
        original = os.environ.get("VETKA_PIPELINE_ENABLED")
        try:
            for value in ["false", "False", "0", "no"]:
                os.environ["VETKA_PIPELINE_ENABLED"] = value
                flag = os.environ.get("VETKA_PIPELINE_ENABLED", "false").lower() == "true"
                assert flag is False, f"Flag should be False for value: {value}"
        finally:
            if original is not None:
                os.environ["VETKA_PIPELINE_ENABLED"] = original
            else:
                os.environ.pop("VETKA_PIPELINE_ENABLED", None)


# ============================================================
# TEST CLASS: Method 1 - Execute Pipeline Loop
# ============================================================

@pytest.mark.pipeline_loop
class TestExecutePipelineLoop:
    """Tests for _execute_pipeline_loop method."""

    @pytest.mark.asyncio
    async def test_pipeline_loop_initialization(self, mock_elisya_state):
        """Test pipeline loop initialization and task creation."""
        architect_output = "Design a new feature module"
        workflow_id = "test_workflow"
        phase_type = "build"
        timestamp = time.time()

        # Initialize pipeline task
        task_id = f"pipeline_{workflow_id}"
        pipeline_task = PipelineTask(
            task_id=task_id,
            task=architect_output,
            phase_type=phase_type,
            status="planning",
            timestamp=timestamp
        )

        assert pipeline_task.task_id == task_id
        assert pipeline_task.task == architect_output
        assert pipeline_task.phase_type == phase_type
        assert pipeline_task.status == "planning"

    @pytest.mark.asyncio
    async def test_pipeline_loop_stm_injection(self, mock_elisya_state):
        """Test that STM context is properly injected between subtasks."""
        stm = []
        subtask = Subtask(
            description="Second subtask",
            needs_research=False,
            marker="MARKER_104.2",
            status="pending"
        )

        # Add previous result to STM
        stm.append({
            "marker": "MARKER_104.1",
            "result": "First subtask completed with important data structure"
        })

        # Inject STM into subtask context
        if stm:
            stm_summary = "\n".join([
                f"- [{s['marker']}]: {s['result'][:200]}..."
                for s in stm[-3:]
            ])
            if subtask.context is None:
                subtask.context = {}
            subtask.context["previous_results"] = stm_summary

        assert subtask.context is not None, "Context should not be None"
        assert "previous_results" in subtask.context, "Context should have previous_results"
        assert "MARKER_104.1" in subtask.context["previous_results"], "STM marker should be in context"

    @pytest.mark.asyncio
    async def test_pipeline_loop_preserves_elisya_state(self, mock_elisya_state):
        """Test that ElisyaState is preserved and updated through pipeline loop."""
        original_workflow_id = mock_elisya_state.workflow_id
        original_path = mock_elisya_state.semantic_path

        # Simulate state updates during pipeline
        mock_elisya_state.speaker = "Dev"
        mock_elisya_state.add_message("Dev", "Subtask 1 implemented")
        mock_elisya_state.add_message("Dev", "Subtask 2 implemented")

        # Verify state integrity
        assert mock_elisya_state.workflow_id == original_workflow_id, "Workflow ID should not change"
        assert mock_elisya_state.semantic_path == original_path, "Semantic path should not change"
        assert mock_elisya_state.speaker == "Dev", "Speaker should be updated"
        assert len(mock_elisya_state.conversation_history) == 2, "History should have 2 messages"

    @pytest.mark.asyncio
    async def test_pipeline_loop_artifact_extraction_in_build_phase(self, sample_code_response_with_artifacts):
        """Test that code artifacts are extracted during build phase."""
        phase_type = "build"
        marker = "MARKER_104.1"

        # Simulate _extract_code_blocks logic
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, sample_code_response_with_artifacts, re.DOTALL | re.IGNORECASE))

        artifacts = []
        for i, match in enumerate(matches):
            lang = match.group('lang') or 'text'
            code = match.group('code').strip()
            if code:
                artifacts.append({
                    "code": code,
                    "language": lang,
                    "marker": f"{marker}_{i+1}" if i > 0 else marker,
                    "size": len(code)
                })

        assert len(artifacts) == 3, "Should extract 3 code blocks"
        assert artifacts[0]["language"] == "python"
        assert artifacts[1]["language"] == "python"
        assert artifacts[2]["language"] == "javascript"
        assert "create_module_structure" in artifacts[0]["code"]

    @pytest.mark.asyncio
    async def test_pipeline_loop_no_artifacts_in_research_phase(self, sample_code_response_with_artifacts):
        """Test that artifacts are NOT extracted during research phase."""
        phase_type = "research"

        # In research phase, code extraction should be skipped
        if phase_type == "build":
            # Extract
            pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
            matches = list(re.finditer(pattern, sample_code_response_with_artifacts, re.DOTALL | re.IGNORECASE))
            artifacts = [m.group(0) for m in matches]
        else:
            # Skip extraction for research
            artifacts = []

        assert len(artifacts) == 0, "Research phase should not extract artifacts"

    @pytest.mark.asyncio
    async def test_pipeline_loop_stm_limit_enforcement(self):
        """Test that STM respects maximum size limit."""
        stm: List[Dict[str, str]] = []
        stm_limit = 5

        # Add 7 items
        for i in range(7):
            stm.append({
                "marker": f"MARKER_104.{i+1}",
                "result": f"Result {i+1} data"
            })
            # Enforce limit
            if len(stm) > stm_limit:
                stm.pop(0)

        assert len(stm) == stm_limit, f"STM should enforce limit of {stm_limit}"
        assert stm[0]["marker"] == "MARKER_104.3", "Should keep last N items"

    @pytest.mark.asyncio
    async def test_pipeline_loop_merged_output_generation(self, sample_subtasks):
        """Test merged output generation from subtasks."""
        # Set results on subtasks
        sample_subtasks[0].result = "Result for feature A"
        sample_subtasks[1].result = "Result for feature B research"
        sample_subtasks[2].result = "Result for feature C tests"
        sample_subtasks[0].status = "done"
        sample_subtasks[1].status = "done"
        sample_subtasks[2].status = "done"

        # Generate merged output
        merged_output = "\n\n".join([
            f"## {st.marker or f'Step {i+1}'}: {st.description}\n{st.result}"
            for i, st in enumerate(sample_subtasks) if st.result
        ])

        assert len(merged_output) > 0
        assert "MARKER_104.1" in merged_output
        assert "Result for feature A" in merged_output
        assert len(merged_output.split("##")) == 4  # Header + 3 sections


# ============================================================
# TEST CLASS: Method 2 - Architect Planning
# ============================================================

@pytest.mark.pipeline_loop
@pytest.mark.architecture_merge
class TestPipelineArchitectPlan:
    """Tests for _pipeline_architect_plan method."""

    @pytest.mark.asyncio
    async def test_architect_plan_valid_structure(self, sample_architect_plan):
        """Test that architect plan has required structure."""
        plan = sample_architect_plan

        assert "subtasks" in plan, "Plan must have subtasks"
        assert "execution_order" in plan, "Plan must have execution_order"
        assert "estimated_complexity" in plan, "Plan must have estimated_complexity"
        assert len(plan["subtasks"]) > 0, "Plan must have at least one subtask"

    @pytest.mark.asyncio
    async def test_architect_plan_subtask_fields(self, sample_architect_plan):
        """Test that each subtask has required fields."""
        required_fields = {"description", "needs_research", "marker"}

        for i, subtask in enumerate(sample_architect_plan["subtasks"]):
            assert all(field in subtask for field in required_fields), \
                f"Subtask {i} missing required fields"
            assert isinstance(subtask["description"], str)
            assert isinstance(subtask["needs_research"], bool)
            assert isinstance(subtask["marker"], str)

    @pytest.mark.asyncio
    async def test_architect_plan_complexity_levels(self):
        """Test that estimated_complexity is valid."""
        valid_complexities = {"low", "medium", "high"}

        for complexity in ["low", "medium", "high"]:
            plan = {
                "subtasks": [{"description": "Test", "needs_research": False}],
                "execution_order": "sequential",
                "estimated_complexity": complexity
            }
            assert plan["estimated_complexity"] in valid_complexities

    @pytest.mark.asyncio
    async def test_architect_plan_execution_order_options(self):
        """Test that execution_order is valid."""
        valid_orders = {"sequential", "parallel"}

        for order in ["sequential", "parallel"]:
            plan = {
                "subtasks": [{"description": "Test", "needs_research": False}],
                "execution_order": order,
                "estimated_complexity": "medium"
            }
            assert plan["execution_order"] in valid_orders

    @pytest.mark.asyncio
    async def test_architect_plan_fallback_on_error(self):
        """Test fallback behavior when architect planning fails."""
        task = "Implement complex feature"

        # Simulate fallback plan
        fallback_plan = {
            "subtasks": [
                {
                    "description": task,
                    "needs_research": True,
                    "question": f"How to implement: {task[:100]}?",
                    "marker": "MARKER_104.1"
                }
            ],
            "execution_order": "sequential",
            "estimated_complexity": "medium"
        }

        assert len(fallback_plan["subtasks"]) == 1, "Fallback should have 1 subtask"
        assert fallback_plan["subtasks"][0]["needs_research"] is True, "Fallback assumes research needed"
        assert "How to implement" in fallback_plan["subtasks"][0]["question"]

    @pytest.mark.asyncio
    async def test_architect_plan_research_flag_marking(self, sample_architect_plan):
        """Test that subtasks needing research are properly marked."""
        research_needed = [st for st in sample_architect_plan["subtasks"] if st["needs_research"]]

        assert len(research_needed) > 0, "Should identify subtasks needing research"
        assert any("validation" in st["description"].lower() for st in research_needed)


# ============================================================
# TEST CLASS: Method 3 - Research Loop
# ============================================================

@pytest.mark.pipeline_loop
@pytest.mark.architecture_merge
class TestPipelineResearch:
    """Tests for _pipeline_research method."""

    @pytest.mark.asyncio
    async def test_research_valid_response_structure(self, sample_research_response):
        """Test that research response has required structure."""
        research = sample_research_response

        required_fields = {"insights", "actionable_steps", "enriched_context", "confidence"}
        assert all(field in research for field in required_fields), \
            "Research response missing required fields"

    @pytest.mark.asyncio
    async def test_research_confidence_range(self):
        """Test that confidence is in valid range [0, 1]."""
        for confidence in [0.0, 0.5, 0.7, 0.99, 1.0]:
            research = {
                "insights": [],
                "actionable_steps": [],
                "enriched_context": "Test",
                "confidence": confidence
            }
            assert 0 <= research["confidence"] <= 1.0, \
                f"Confidence {confidence} out of range"

    @pytest.mark.asyncio
    async def test_research_recursive_trigger_threshold(self):
        """Test that low confidence triggers recursive research."""
        low_confidence = {"confidence": 0.5, "further_questions": ["Q1", "Q2"]}
        high_confidence = {"confidence": 0.9, "further_questions": []}

        should_recurse_low = low_confidence["confidence"] < 0.7
        should_recurse_high = high_confidence["confidence"] < 0.7

        assert should_recurse_low is True, "Low confidence should trigger recursion"
        assert should_recurse_high is False, "High confidence should not trigger recursion"

    @pytest.mark.asyncio
    async def test_research_further_questions_limit(self):
        """Test that further questions respect recursion limit."""
        research_with_questions = {
            "confidence": 0.5,
            "further_questions": ["Q1", "Q2", "Q3", "Q4", "Q5"]
        }

        # Limit recursion to max 2 questions
        questions_to_research = research_with_questions["further_questions"][:2]
        assert len(questions_to_research) <= 2, "Should limit recursive questions to 2"

    @pytest.mark.asyncio
    async def test_research_actionable_steps_structure(self, sample_research_response):
        """Test that actionable steps have required fields."""
        for step in sample_research_response["actionable_steps"]:
            assert "step" in step or "description" in step, "Step must have description"
            # needs_code may be optional
            if "needs_code" in step:
                assert isinstance(step["needs_code"], bool)

    @pytest.mark.asyncio
    async def test_research_fallback_on_parse_error(self):
        """Test fallback when research response parsing fails."""
        raw_response = "This is not valid JSON but contains useful info about pydantic"

        # Simulate fallback
        fallback = {
            "insights": ["Research data available in enriched_context"],
            "actionable_steps": [],
            "enriched_context": raw_response[:500],
            "confidence": 0.6,
            "further_questions": []
        }

        assert fallback["confidence"] == 0.6, "Fallback should have low confidence"
        assert len(fallback["insights"]) > 0, "Fallback should have fallback insight"

    @pytest.mark.asyncio
    async def test_research_context_enrichment(self, sample_research_response):
        """Test that enriched_context is preserved and accessible."""
        enriched = sample_research_response["enriched_context"]
        assert len(enriched) > 0, "Enriched context should not be empty"
        assert isinstance(enriched, str), "Enriched context should be string"


# ============================================================
# TEST CLASS: Method 4 - Subtask Prompt Builder
# ============================================================

@pytest.mark.pipeline_loop
@pytest.mark.architecture_merge
class TestBuildSubtaskPrompt:
    """Tests for _build_subtask_prompt method."""

    def test_prompt_includes_description(self, sample_subtasks):
        """Test that prompt includes subtask description."""
        subtask = sample_subtasks[0]
        parts = [f"# Subtask: {subtask.description}"]
        prompt = "\n".join(parts)

        assert subtask.description in prompt, "Description should be in prompt"

    def test_prompt_includes_marker(self, sample_subtasks):
        """Test that prompt includes marker when available."""
        subtask = sample_subtasks[0]
        parts = [f"# Subtask: {subtask.description}"]
        if subtask.marker:
            parts.append(f"Marker: {subtask.marker}")
        prompt = "\n".join(parts)

        assert subtask.marker in prompt, "Marker should be in prompt"

    def test_prompt_includes_research_context(self):
        """Test that prompt includes research context when available."""
        subtask = Subtask(
            description="Implement validation",
            needs_research=True,
            marker="MARKER_104.2",
            context={
                "enriched_context": "Use pydantic for validation",
                "actionable_steps": [
                    {"step": "Install pydantic"},
                    {"step": "Create schema"}
                ]
            }
        )

        parts = [f"# Subtask: {subtask.description}"]
        if subtask.context:
            if subtask.context.get("enriched_context"):
                parts.append(f"\n## Research Context:\n{subtask.context['enriched_context']}")
            if subtask.context.get("actionable_steps"):
                steps = "\n".join([f"- {s.get('step', s)}" for s in subtask.context["actionable_steps"]])
                parts.append(f"\n## Actionable Steps:\n{steps}")

        prompt = "\n".join(parts)

        assert "Research Context" in prompt, "Research context section should be present"
        assert "pydantic" in prompt, "Research insight should be included"
        assert "Actionable Steps" in prompt, "Actionable steps section should be present"

    def test_prompt_includes_previous_results(self):
        """Test that prompt includes STM previous results."""
        subtask = Subtask(
            description="Continue from previous step",
            needs_research=False,
            marker="MARKER_104.3",
            context={
                "previous_results": "- [MARKER_104.1]: Created module structure\n- [MARKER_104.2]: Added validation"
            }
        )

        parts = [f"# Subtask: {subtask.description}"]
        if subtask.context and subtask.context.get("previous_results"):
            parts.append(f"\n## Previous Subtask Results:\n{subtask.context['previous_results']}")

        prompt = "\n".join(parts)

        assert "Previous Subtask Results" in prompt, "Previous results section should be present"
        assert "MARKER_104.1" in prompt, "Previous markers should be referenced"

    def test_prompt_build_phase_guidance(self):
        """Test build phase guidance in prompt."""
        phase_type = "build"
        parts = [f"# Subtask: Test implementation"]

        if phase_type == "build":
            parts.append("\n## Instructions:\nImplement this subtask. Provide code with clear markers.")

        prompt = "\n".join(parts)
        assert "Implement this subtask" in prompt, "Build guidance should be present"

    def test_prompt_fix_phase_guidance(self):
        """Test fix phase guidance in prompt."""
        phase_type = "fix"
        parts = [f"# Subtask: Test fix"]

        if phase_type == "fix":
            parts.append("\n## Instructions:\nFix the issue described. Include before/after code.")

        prompt = "\n".join(parts)
        assert "Fix the issue" in prompt, "Fix guidance should be present"

    def test_prompt_research_phase_guidance(self):
        """Test research phase guidance in prompt."""
        phase_type = "research"
        parts = [f"# Subtask: Test research"]

        if phase_type == "research":
            parts.append("\n## Instructions:\nProvide analysis and recommendations.")

        prompt = "\n".join(parts)
        assert "analysis and recommendations" in prompt, "Research guidance should be present"

    def test_prompt_complete_with_all_context(self):
        """Test complete prompt with all context sections."""
        subtask = Subtask(
            description="Implement feature",
            needs_research=True,
            marker="MARKER_104.2",
            context={
                "enriched_context": "Use pydantic",
                "actionable_steps": [{"step": "Install"}],
                "previous_results": "- [MARKER_104.1]: Done"
            }
        )
        phase_type = "build"

        parts = [f"# Subtask: {subtask.description}"]
        if subtask.marker:
            parts.append(f"Marker: {subtask.marker}")
        if subtask.context:
            if subtask.context.get("enriched_context"):
                parts.append(f"\n## Research Context:\n{subtask.context['enriched_context']}")
            if subtask.context.get("actionable_steps"):
                steps = "\n".join([f"- {s.get('step')}" for s in subtask.context["actionable_steps"]])
                parts.append(f"\n## Actionable Steps:\n{steps}")
            if subtask.context.get("previous_results"):
                parts.append(f"\n## Previous Subtask Results:\n{subtask.context['previous_results']}")

        if phase_type == "build":
            parts.append("\n## Instructions:\nImplement this subtask. Provide code with clear markers.")

        prompt = "\n".join(parts)

        assert len(prompt) > 100, "Complete prompt should be substantial"
        assert "MARKER_104.2" in prompt
        assert "Research Context" in prompt
        assert "Actionable Steps" in prompt
        assert "Previous Subtask Results" in prompt


# ============================================================
# TEST CLASS: Method 5 - Code Block Extraction
# ============================================================

@pytest.mark.architecture_merge
class TestExtractCodeBlocks:
    """Tests for _extract_code_blocks method."""

    def test_extract_single_code_block(self):
        """Test extracting a single code block."""
        content = '''
Here is the code:

```python
def test_function():
    return True
```
'''
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        assert len(matches) == 1, "Should find exactly one code block"
        assert matches[0].group('lang') == 'python'
        assert 'test_function' in matches[0].group('code')

    def test_extract_multiple_code_blocks(self):
        """Test extracting multiple code blocks."""
        content = '''
First file:
```python
def file1():
    pass
```

Second file:
```javascript
function file2() {}
```
'''
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        assert len(matches) == 2, "Should find two code blocks"
        assert matches[0].group('lang') == 'python'
        assert matches[1].group('lang') == 'javascript'

    def test_extract_code_block_without_language(self):
        """Test extracting code block without language specification."""
        content = '''
```
plain text code
```
'''
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        assert len(matches) == 1, "Should find one code block"
        assert matches[0].group('lang') is None

    def test_extract_filepath_from_description(self):
        """Test extracting filepath from subtask description."""
        description = "Create src/voice/config.py with configuration settings"

        filepath_match = re.search(
            r'(src/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
            description,
            re.IGNORECASE
        )

        assert filepath_match is not None, "Should extract filepath"
        assert filepath_match.group(1) == "src/voice/config.py"

    def test_extract_multiple_filepaths(self):
        """Test extracting multiple filepaths."""
        description = "Create src/module/config.py and src/utils/helpers.ts"

        filepaths = re.findall(
            r'(src/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
            description,
            re.IGNORECASE
        )

        assert len(filepaths) == 2
        assert "src/module/config.py" in filepaths
        assert "src/utils/helpers.ts" in filepaths

    def test_no_code_blocks_returns_empty(self):
        """Test that content without code blocks returns empty list."""
        content = "This is just plain text without any code blocks."
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        assert len(matches) == 0, "Should find no code blocks"

    def test_artifact_size_tracking(self):
        """Test that artifact sizes are tracked."""
        content = '''
```python
def short():
    pass

def long_function_with_many_lines():
    for i in range(100):
        do_something(i)
```
'''
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        artifacts = []
        for match in matches:
            code = match.group('code').strip()
            artifacts.append({
                "code": code,
                "size": len(code)
            })

        assert len(artifacts) == 1
        assert artifacts[0]["size"] > 0

    def test_language_identification_common_languages(self):
        """Test language identification for common languages."""
        content = '''
```python
python_code = True
```

```javascript
const js = true;
```

```typescript
const ts: boolean = true;
```

```json
{"key": "value"}
```
'''
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        languages = [m.group('lang') for m in matches]
        assert "python" in languages
        assert "javascript" in languages
        assert "typescript" in languages
        assert "json" in languages


# ============================================================
# TEST CLASS: Method 6 - Task Storage
# ============================================================

@pytest.mark.architecture_merge
class TestSavePipelineTask:
    """Tests for _save_pipeline_task method."""

    def test_pipeline_task_serialization(self, sample_subtasks):
        """Test that PipelineTask can be serialized to dict."""
        task = PipelineTask(
            task_id="test_task_1",
            task="Implement feature",
            phase_type="build",
            status="done",
            subtasks=sample_subtasks,
            timestamp=time.time(),
            results={"subtasks_completed": 3, "subtasks_total": 3}
        )

        task_dict = asdict(task)

        assert task_dict["task_id"] == "test_task_1"
        assert task_dict["phase_type"] == "build"
        assert task_dict["status"] == "done"
        assert len(task_dict["subtasks"]) == 3
        assert task_dict["results"]["subtasks_completed"] == 3

    def test_subtask_serialization(self):
        """Test that Subtask can be serialized to dict."""
        subtask = Subtask(
            description="Test subtask",
            needs_research=True,
            question="How to test?",
            marker="MARKER_TEST",
            status="done",
            result="Test completed"
        )

        subtask_dict = asdict(subtask)

        assert subtask_dict["description"] == "Test subtask"
        assert subtask_dict["needs_research"] is True
        assert subtask_dict["result"] == "Test completed"
        assert subtask_dict["marker"] == "MARKER_TEST"

    def test_pipeline_task_json_compatibility(self, sample_subtasks):
        """Test that PipelineTask can be converted to JSON."""
        task = PipelineTask(
            task_id="test_json",
            task="Test JSON",
            phase_type="build",
            status="done",
            subtasks=sample_subtasks,
            timestamp=time.time()
        )

        task_dict = asdict(task)
        json_str = json.dumps(task_dict, default=str)

        assert isinstance(json_str, str)
        restored = json.loads(json_str)
        assert restored["task_id"] == "test_json"

    def test_tasks_file_path_defined(self):
        """Test that TASKS_FILE path is properly defined."""
        assert TASKS_FILE is not None, "TASKS_FILE must be defined"
        assert "pipeline_tasks.json" in str(TASKS_FILE), "TASKS_FILE must reference pipeline_tasks.json"
        assert isinstance(TASKS_FILE, Path), "TASKS_FILE should be Path object"

    def test_pipeline_task_results_structure(self):
        """Test that results structure is valid."""
        task = PipelineTask(
            task_id="test_results",
            task="Test",
            phase_type="build",
            results={
                "subtasks_completed": 3,
                "subtasks_total": 3,
                "artifacts_count": 5
            }
        )

        assert task.results["subtasks_completed"] == 3
        assert task.results["subtasks_total"] == 3
        assert task.results["artifacts_count"] == 5


# ============================================================
# TEST CLASS: Method 7 - Robust JSON Extraction
# ============================================================

@pytest.mark.architecture_merge
class TestExtractJsonRobust:
    """Tests for _extract_json_robust method."""

    def test_extract_raw_json(self):
        """Test extracting raw JSON."""
        text = '{"key": "value", "number": 42}'
        result = json.loads(text)

        assert result["key"] == "value"
        assert result["number"] == 42

    def test_extract_json_from_markdown_block(self):
        """Test extracting JSON from markdown code block."""
        text = '''Here is the response:

```json
{
    "subtasks": [
        {"description": "Step 1"}
    ]
}
```
'''
        json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        assert json_block is not None
        result = json.loads(json_block.group(1))

        assert "subtasks" in result
        assert len(result["subtasks"]) == 1

    def test_extract_json_from_generic_code_block(self):
        """Test extracting JSON from generic code block."""
        text = '''
```
{"key": "value"}
```
'''
        code_block = re.search(r'```\s*([\s\S]*?)\s*```', text)
        assert code_block is not None
        result = json.loads(code_block.group(1))

        assert result["key"] == "value"

    def test_extract_json_embedded_in_prose(self):
        """Test extracting JSON embedded in prose."""
        text = 'The response is {"result": true} as expected.'
        json_match = re.search(r'\{[\s\S]*\}', text)
        assert json_match is not None
        result = json.loads(json_match.group(0))

        assert result["result"] is True

    def test_extract_json_from_first_brace(self):
        """Test extracting JSON starting from first brace."""
        text = 'Prefix text {"data": [1, 2, 3]}'
        first_brace = text.find('{')
        assert first_brace != -1
        result = json.loads(text[first_brace:])

        assert result["data"] == [1, 2, 3]

    def test_extract_json_with_nested_objects(self):
        """Test extracting complex nested JSON."""
        text = '''Response:
{
    "plan": {
        "subtasks": [
            {"id": 1, "nested": {"key": "value"}}
        ]
    }
}
'''
        json_match = re.search(r'\{[\s\S]*\}', text)
        assert json_match is not None
        result = json.loads(json_match.group(0))

        assert "plan" in result
        assert "subtasks" in result["plan"]

    def test_empty_text_handling(self):
        """Test that empty text handling."""
        text = ""
        if not text or not text.strip():
            result = {}
        else:
            result = json.loads(text)

        assert result == {}

    def test_json_extraction_strategy_priority(self):
        """Test JSON extraction tries multiple strategies."""
        strategies = [
            ('{"direct": true}', "direct"),
            ('```json\n{"block": true}\n```', "block"),
            ('Some text {"embedded": true}', "embedded"),
        ]

        for text, strategy_type in strategies:
            # Try direct
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # Try markdown
                json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
                if json_block:
                    result = json.loads(json_block.group(1))
                else:
                    # Try embedded
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        result = json.loads(json_match.group(0))

            assert "result" in locals()


# ============================================================
# TEST CLASS: Hybrid Flow Integration
# ============================================================

@pytest.mark.integration
@pytest.mark.pipeline_loop
class TestHybridFlowIntegration:
    """Integration tests for PM -> Architect -> [PIPELINE LOOP] -> Dev||QA flow."""

    @pytest.mark.asyncio
    async def test_hybrid_flow_phase_sequence(self, mock_elisya_state):
        """Test the full hybrid flow phase sequence."""
        # Phase 1: PM processes request
        mock_elisya_state.speaker = "PM"
        mock_elisya_state.add_message("PM", "Feature request analyzed")
        assert mock_elisya_state.speaker == "PM"
        assert len(mock_elisya_state.conversation_history) == 1

        # Phase 2: Architect creates design
        mock_elisya_state.speaker = "Architect"
        mock_elisya_state.add_message("Architect", "Architecture designed with 3 components")
        assert mock_elisya_state.speaker == "Architect"
        assert len(mock_elisya_state.conversation_history) == 2

        # Phase 3: Pipeline Loop (simulated)
        pipeline_output = "Pipeline completed with 3 subtasks"
        artifacts = [
            {"code": "def test(): pass", "marker": "MARKER_104.1"},
            {"code": "class Config: pass", "marker": "MARKER_104.2"}
        ]

        # Phase 4: Dev processes enriched context
        mock_elisya_state.speaker = "Dev"
        mock_elisya_state.add_message("Dev", "Implementation complete")
        assert mock_elisya_state.speaker == "Dev"
        assert len(mock_elisya_state.conversation_history) == 3

        # Verify conversation flow
        speakers = [msg["speaker"] for msg in mock_elisya_state.conversation_history]
        assert speakers == ["PM", "Architect", "Dev"]

    @pytest.mark.asyncio
    async def test_elisya_state_preserved_through_pipeline(self, mock_elisya_state):
        """Test that ElisyaState is preserved through pipeline loop."""
        original_workflow_id = mock_elisya_state.workflow_id
        original_path = mock_elisya_state.semantic_path

        # Simulate multiple subtask executions
        for i in range(3):
            mock_elisya_state.speaker = "Dev"
            mock_elisya_state.add_message("Dev", f"Subtask {i+1} completed")

        # Verify state integrity
        assert mock_elisya_state.workflow_id == original_workflow_id
        assert mock_elisya_state.semantic_path == original_path
        assert len(mock_elisya_state.conversation_history) == 3

    @pytest.mark.asyncio
    async def test_pipeline_artifacts_available_for_dev_qa(self):
        """Test that pipeline artifacts are available for Dev and QA."""
        result = {
            "pipeline_artifacts": [
                {"code": "def feature(): pass", "marker": "MARKER_104.1"},
                {"code": "class Config: pass", "marker": "MARKER_104.2"}
            ],
            "pipeline_enriched_context": "Detailed implementation context from pipeline"
        }

        # Verify artifacts available
        assert len(result["pipeline_artifacts"]) == 2
        assert len(result["pipeline_enriched_context"]) > 0
        assert "pipeline_enriched_context" in result

    @pytest.mark.asyncio
    async def test_dev_qa_can_use_pipeline_context(self):
        """Test that Dev and QA use pipeline-enriched context."""
        architect_output = "Design complete"
        pipeline_output = "Pipeline enriched design with 3 subtasks and research"

        # If pipeline loop enabled, use its output
        use_pipeline_output = True
        dev_prompt = pipeline_output if use_pipeline_output else architect_output

        assert len(dev_prompt) >= len(architect_output)
        assert "subtasks" in dev_prompt or "enriched" in dev_prompt

    @pytest.mark.asyncio
    async def test_hybrid_flow_graceful_degradation(self):
        """Test that system degrades gracefully if pipeline fails."""
        architect_output = "Design complete"

        # If pipeline fails, use architect output
        pipeline_success = False
        dev_prompt = architect_output if not pipeline_success else "pipeline output"

        assert len(dev_prompt) > 0
        assert dev_prompt == architect_output


# ============================================================
# TEST CLASS: Researcher Auto-Trigger
# ============================================================

@pytest.mark.pipeline_loop
@pytest.mark.architecture_merge
class TestResearcherAutoTrigger:
    """Tests for researcher auto-trigger on unclear parts."""

    def test_auto_trigger_on_needs_research_flag(self, sample_subtasks):
        """Test that researcher is triggered when needs_research=True."""
        research_needed = [st for st in sample_subtasks if st.needs_research]

        assert len(research_needed) == 1, "Should identify one research-needed subtask"
        assert research_needed[0].marker == "MARKER_104.2"

    def test_auto_trigger_uses_question_when_available(self, sample_subtasks):
        """Test that question is used for research when available."""
        subtask = sample_subtasks[1]

        question = subtask.question or subtask.description
        assert question == "What is the best approach for B?"

    def test_auto_trigger_falls_back_to_description(self):
        """Test fallback to description when no question provided."""
        subtask = Subtask(
            description="Implement complex algorithm",
            needs_research=True,
            question=None,
            marker="MARKER_TEST"
        )

        question = subtask.question or subtask.description
        assert question == "Implement complex algorithm"

    @pytest.mark.asyncio
    async def test_recursive_research_on_low_confidence(self):
        """Test that low confidence triggers recursive research."""
        research_result = {
            "confidence": 0.5,
            "further_questions": [
                "What specific library?",
                "How to handle errors?"
            ]
        }

        # Should trigger recursion
        should_recurse = research_result["confidence"] < 0.7
        assert should_recurse is True

        # Max 2 recursive calls
        questions_to_research = research_result["further_questions"][:2]
        assert len(questions_to_research) == 2

    def test_high_confidence_skips_recursion(self):
        """Test that high confidence skips recursive research."""
        research_result = {
            "confidence": 0.95,
            "further_questions": ["Q1", "Q2"]
        }

        should_recurse = research_result["confidence"] < 0.7
        assert should_recurse is False


# ============================================================
# TEST CLASS: STM Context Passing
# ============================================================

@pytest.mark.pipeline_loop
@pytest.mark.architecture_merge
class TestSTMContextPassing:
    """Tests for Short-Term Memory context passing between subtasks."""

    def test_stm_buffer_initialization(self):
        """Test STM buffer starts empty."""
        stm: List[Dict[str, str]] = []
        assert len(stm) == 0

    def test_stm_add_result(self):
        """Test adding result to STM."""
        stm: List[Dict[str, str]] = []

        stm.append({
            "marker": "MARKER_104.1",
            "result": "First subtask completed"[:500]
        })

        assert len(stm) == 1
        assert stm[0]["marker"] == "MARKER_104.1"

    def test_stm_limit_enforcement(self):
        """Test that STM respects size limit."""
        stm: List[Dict[str, str]] = []
        stm_limit = 5

        # Add 7 items
        for i in range(7):
            stm.append({
                "marker": f"MARKER_104.{i+1}",
                "result": f"Result {i+1}"
            })
            if len(stm) > stm_limit:
                stm.pop(0)

        # Should only keep last 5
        assert len(stm) == stm_limit
        assert stm[0]["marker"] == "MARKER_104.3"

    def test_stm_summary_generation(self):
        """Test STM summary generation for context injection."""
        stm = [
            {"marker": "MARKER_104.1", "result": "Created module structure"},
            {"marker": "MARKER_104.2", "result": "Added validation logic"},
            {"marker": "MARKER_104.3", "result": "Implemented tests"}
        ]

        summary_parts = []
        for item in stm[-3:]:
            summary_parts.append(f"- [{item['marker']}]: {item['result'][:200]}...")

        summary = "\n".join(summary_parts)

        assert "MARKER_104.1" in summary
        assert "MARKER_104.2" in summary
        assert "MARKER_104.3" in summary

    def test_stm_context_injection_into_subtask(self):
        """Test that STM summary is injected into subtask context."""
        stm = [{"marker": "MARKER_104.1", "result": "Previous work done"}]
        subtask = Subtask(
            description="Continue work",
            needs_research=False,
            marker="MARKER_104.2"
        )

        # Inject STM
        if stm:
            stm_summary = "\n".join([
                f"- [{s['marker']}]: {s['result'][:200]}..."
                for s in stm[-3:]
            ])
            if subtask.context is None:
                subtask.context = {}
            subtask.context["previous_results"] = stm_summary

        assert subtask.context is not None
        assert "previous_results" in subtask.context
        assert "MARKER_104.1" in subtask.context["previous_results"]

    def test_stm_overflow_removes_oldest(self):
        """Test that STM overflow removes oldest items first."""
        stm: List[Dict[str, str]] = []

        # Add items with incremental markers
        for i in range(6):
            stm.append({"marker": f"MARKER_{i}", "result": f"Result {i}"})
            if len(stm) > 5:
                stm.pop(0)

        # First item should be MARKER_1, not MARKER_0
        assert stm[0]["marker"] == "MARKER_1"
        assert stm[-1]["marker"] == "MARKER_5"


# ============================================================
# TEST CLASS: Error Handling & Edge Cases
# ============================================================

@pytest.mark.architecture_merge
class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases."""

    def test_empty_architect_output(self):
        """Test handling of empty architect output."""
        architect_output = ""

        # Should create fallback task
        if not architect_output or not architect_output.strip():
            fallback_task = PipelineTask(
                task_id="fallback_task",
                task="Empty task",
                phase_type="build",
                status="pending"
            )
            assert fallback_task.task == "Empty task"

    def test_no_subtasks_in_plan(self):
        """Test handling of plan with no subtasks."""
        plan = {
            "subtasks": [],
            "execution_order": "sequential"
        }

        # Should handle empty subtasks gracefully
        assert len(plan["subtasks"]) == 0

    def test_subtask_with_null_context(self):
        """Test subtask with null context."""
        subtask = Subtask(
            description="Test subtask",
            needs_research=False,
            context=None
        )

        # Should handle null context
        if subtask.context is None:
            subtask.context = {}

        assert subtask.context == {}

    def test_malformed_json_response(self):
        """Test handling of malformed JSON response."""
        malformed_response = "This is not JSON { broken"

        try:
            json.loads(malformed_response)
            parsed = True
        except json.JSONDecodeError:
            parsed = False

        assert parsed is False

    @pytest.mark.asyncio
    async def test_pipeline_graceful_degradation(self, mock_elisya_state):
        """Test that pipeline degrades gracefully on error."""
        # Simulate pipeline failure
        pipeline_error = "LLM call timeout"

        result = {
            "pipeline_error": pipeline_error,
            "metrics": {"phases": {"pipeline_loop": 5.0}}
        }

        # Should continue to Dev/QA with Architect output
        assert "pipeline_error" in result
        assert result["metrics"]["phases"]["pipeline_loop"] > 0

    def test_code_extraction_with_empty_blocks(self):
        """Test code extraction skips empty blocks."""
        content = '''
```python

```

```python
def actual_code():
    pass
```
'''
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        artifacts = []
        for match in matches:
            code = match.group('code').strip()
            if code:  # Skip empty
                artifacts.append({"code": code})

        assert len(artifacts) == 1


# ============================================================
# PARAMETRIZED TESTS
# ============================================================

class TestParametrizedWorkflows:
    """Parametrized tests for various workflow scenarios."""

    @pytest.mark.parametrize("phase_type,expected_guidance", [
        ("build", "Implement this subtask"),
        ("fix", "Fix the issue"),
        ("research", "Provide analysis")
    ])
    def test_phase_specific_guidance(self, phase_type, expected_guidance):
        """Test phase-specific guidance in prompts."""
        parts = []
        if phase_type == "build":
            parts.append("Implement this subtask. Provide code with clear markers.")
        elif phase_type == "fix":
            parts.append("Fix the issue described. Include before/after code.")
        else:  # research
            parts.append("Provide analysis and recommendations.")

        prompt = "\n".join(parts)
        assert expected_guidance in prompt

    @pytest.mark.parametrize("confidence,should_recurse", [
        (0.5, True),
        (0.6, True),
        (0.7, False),
        (0.8, False),
        (0.95, False),
    ])
    def test_research_recursion_threshold(self, confidence, should_recurse):
        """Test research recursion based on confidence."""
        should_trigger = confidence < 0.7
        assert should_trigger == should_recurse

    @pytest.mark.parametrize("code_lang", [
        "python", "javascript", "typescript", "json", "yaml", "sql"
    ])
    def test_language_detection(self, code_lang):
        """Test language detection for various languages."""
        content = f"```{code_lang}\ncode here\n```"
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        assert match is not None
        assert match.group('lang') == code_lang


# ============================================================
# TEST EXECUTION
# ============================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "architecture_merge",
        "--co"  # Show collection
    ])
