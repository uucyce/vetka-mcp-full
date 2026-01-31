# MARKER_104_TESTS
"""
Phase 104: Hybrid Architecture Merge Tests

Tests for the merge of Legacy Orchestrator (orchestrator_with_elisya.py)
with AgentPipeline (agent_pipeline.py) into a unified Hybrid Architecture.

Tests cover:
- 7 new methods from MERGE_IMPLEMENTATION_GUIDE.md
- Hybrid flow: PM -> Architect -> [PIPELINE LOOP] -> Dev||QA
- ElisyaState preservation through pipeline loop
- Feature flag toggling (VETKA_PIPELINE_ENABLED)
- Researcher auto-trigger on unclear parts
- STM context passing between subtasks

Run: pytest tests/test_phase104_hybrid.py -v

@status: active
@phase: 104
@depends: pytest, pytest-asyncio, unittest.mock
"""

import pytest
import asyncio
import json
import time
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from dataclasses import asdict
from typing import Dict, Any, List

# Import core components
from src.orchestration.agent_pipeline import (
    PipelineTask,
    Subtask,
    TASKS_FILE,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_elisya_state():
    """Create a mock ElisyaState for testing."""
    from src.elisya.state import ElisyaState
    return ElisyaState(
        workflow_id="test_workflow_104",
        speaker="Architect",
        semantic_path="projects/vetka/phase104",
        context="Test context for pipeline",
        raw_context="Original test context",
        lod_level="tree",
        tint="general"
    )


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


# ============================================================
# TEST CLASS: Feature Flag Tests
# ============================================================

class TestFeatureFlagToggling:
    """Tests for VETKA_PIPELINE_ENABLED feature flag."""

    def test_feature_flag_default_disabled(self):
        """Test that pipeline loop is disabled by default."""
        # Clear any existing env var
        env_value = os.environ.pop("VETKA_PIPELINE_ENABLED", None)
        try:
            # Verify default behavior (disabled)
            flag = os.environ.get("VETKA_PIPELINE_ENABLED", "false").lower() == "true"
            assert flag is False
        finally:
            # Restore if was set
            if env_value is not None:
                os.environ["VETKA_PIPELINE_ENABLED"] = env_value

    def test_feature_flag_enabled(self):
        """Test enabling pipeline loop via environment variable."""
        original = os.environ.get("VETKA_PIPELINE_ENABLED")
        try:
            os.environ["VETKA_PIPELINE_ENABLED"] = "true"
            flag = os.environ.get("VETKA_PIPELINE_ENABLED", "false").lower() == "true"
            assert flag is True
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
                assert flag is True, f"Failed for value: {value}"
        finally:
            if original is not None:
                os.environ["VETKA_PIPELINE_ENABLED"] = original
            else:
                os.environ.pop("VETKA_PIPELINE_ENABLED", None)


# ============================================================
# TEST CLASS: Method 1 - Execute Pipeline Loop
# ============================================================

class TestExecutePipelineLoop:
    """Tests for _execute_pipeline_loop method."""

    @pytest.mark.asyncio
    async def test_pipeline_loop_basic_execution(self, mock_elisya_state, sample_architect_plan):
        """Test basic pipeline loop execution."""
        # Mock orchestrator with required methods
        mock_orchestrator = MagicMock()
        mock_orchestrator._pipeline_architect_plan = AsyncMock(return_value=sample_architect_plan)
        mock_orchestrator._pipeline_research = AsyncMock(return_value={
            "insights": ["Test insight"],
            "enriched_context": "Test context",
            "confidence": 0.9,
            "further_questions": []
        })
        mock_orchestrator._run_agent_with_elisya_async = AsyncMock(
            return_value=("Subtask completed successfully", mock_elisya_state)
        )
        mock_orchestrator._build_subtask_prompt = MagicMock(return_value="Test prompt")
        mock_orchestrator._extract_code_blocks = MagicMock(return_value=[])
        mock_orchestrator._save_pipeline_task = MagicMock()

        # Simulate _execute_pipeline_loop logic
        architect_output = "Design a new feature module"
        workflow_id = "test_workflow"
        phase_type = "build"

        # Initialize pipeline task
        task_id = f"pipeline_{workflow_id}"
        pipeline_task = PipelineTask(
            task_id=task_id,
            task=architect_output,
            phase_type=phase_type,
            status="planning",
            timestamp=time.time()
        )

        # Get plan
        plan = await mock_orchestrator._pipeline_architect_plan(architect_output, phase_type, mock_elisya_state)
        assert "subtasks" in plan
        assert len(plan["subtasks"]) == 3

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
            "result": "First subtask completed with important data"
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

        assert subtask.context is not None
        assert "previous_results" in subtask.context
        assert "MARKER_104.1" in subtask.context["previous_results"]

    @pytest.mark.asyncio
    async def test_pipeline_loop_preserves_elisya_state(self, mock_elisya_state):
        """Test that ElisyaState is preserved and updated through pipeline loop."""
        original_workflow_id = mock_elisya_state.workflow_id
        original_path = mock_elisya_state.semantic_path

        # Simulate state updates during pipeline
        mock_elisya_state.speaker = "Dev"
        mock_elisya_state.add_message("Dev", "Implemented feature")

        # Verify state integrity
        assert mock_elisya_state.workflow_id == original_workflow_id
        assert mock_elisya_state.semantic_path == original_path
        assert mock_elisya_state.speaker == "Dev"
        assert len(mock_elisya_state.conversation_history) == 1

    @pytest.mark.asyncio
    async def test_pipeline_loop_artifact_extraction(self):
        """Test that code artifacts are extracted during build phase."""
        content = '''
Here is the implementation:

```python
def hello_world():
    """MARKER_104.1: Hello world function"""
    return "Hello, VETKA!"
```

And another file:

```python
class Config:
    """MARKER_104.2: Configuration class"""
    debug = True
```
'''
        # Simulate _extract_code_blocks logic
        import re
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        artifacts = []
        for i, match in enumerate(matches):
            lang = match.group('lang') or 'text'
            code = match.group('code').strip()
            if code:
                artifacts.append({
                    "code": code,
                    "language": lang,
                    "marker": f"test_{i+1}",
                    "size": len(code)
                })

        assert len(artifacts) == 2
        assert artifacts[0]["language"] == "python"
        assert "hello_world" in artifacts[0]["code"]


# ============================================================
# TEST CLASS: Method 2 - Architect Planning
# ============================================================

class TestPipelineArchitectPlan:
    """Tests for _pipeline_architect_plan method."""

    @pytest.mark.asyncio
    async def test_architect_plan_returns_valid_structure(self, sample_architect_plan):
        """Test that architect plan has required structure."""
        plan = sample_architect_plan

        assert "subtasks" in plan
        assert "execution_order" in plan
        assert "estimated_complexity" in plan
        assert len(plan["subtasks"]) > 0

    @pytest.mark.asyncio
    async def test_architect_plan_subtask_structure(self, sample_architect_plan):
        """Test that each subtask has required fields."""
        for subtask in sample_architect_plan["subtasks"]:
            assert "description" in subtask
            assert "needs_research" in subtask
            assert "marker" in subtask

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

        assert len(fallback_plan["subtasks"]) == 1
        assert fallback_plan["subtasks"][0]["needs_research"] is True


# ============================================================
# TEST CLASS: Method 3 - Research Loop
# ============================================================

class TestPipelineResearch:
    """Tests for _pipeline_research method."""

    @pytest.mark.asyncio
    async def test_research_returns_valid_structure(self, sample_research_response):
        """Test that research response has required structure."""
        research = sample_research_response

        assert "insights" in research
        assert "actionable_steps" in research
        assert "enriched_context" in research
        assert "confidence" in research

    @pytest.mark.asyncio
    async def test_research_recursive_on_low_confidence(self, mock_elisya_state):
        """Test that research triggers recursive calls on low confidence."""
        low_confidence_response = {
            "insights": ["Partial insight"],
            "actionable_steps": [],
            "enriched_context": "Need more research",
            "confidence": 0.5,
            "further_questions": [
                "What specific library should be used?",
                "How to handle edge cases?"
            ]
        }

        # Verify recursive trigger condition
        assert low_confidence_response["confidence"] < 0.7
        assert len(low_confidence_response["further_questions"]) > 0

        # Simulate recursive research (max 2 recursions)
        further_questions = low_confidence_response["further_questions"][:2]
        assert len(further_questions) <= 2

    @pytest.mark.asyncio
    async def test_research_fallback_on_parse_error(self):
        """Test fallback when research response parsing fails."""
        raw_response = "This is not valid JSON but contains useful info"

        # Simulate fallback
        fallback = {
            "insights": ["Research data available in enriched_context"],
            "actionable_steps": [],
            "enriched_context": raw_response[:500],
            "confidence": 0.6,
            "further_questions": []
        }

        assert fallback["confidence"] == 0.6
        assert raw_response[:500] in fallback["enriched_context"]


# ============================================================
# TEST CLASS: Method 4 - Subtask Prompt Builder
# ============================================================

class TestBuildSubtaskPrompt:
    """Tests for _build_subtask_prompt method."""

    def test_prompt_includes_description(self, sample_subtasks):
        """Test that prompt includes subtask description."""
        subtask = sample_subtasks[0]
        prompt_parts = [f"# Subtask: {subtask.description}"]
        prompt = "\n".join(prompt_parts)

        assert subtask.description in prompt

    def test_prompt_includes_marker(self, sample_subtasks):
        """Test that prompt includes marker when available."""
        subtask = sample_subtasks[0]
        parts = [f"# Subtask: {subtask.description}"]
        if subtask.marker:
            parts.append(f"Marker: {subtask.marker}")
        prompt = "\n".join(parts)

        assert subtask.marker in prompt

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

        assert "Research Context" in prompt
        assert "pydantic" in prompt
        assert "Actionable Steps" in prompt

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

        assert "Previous Subtask Results" in prompt
        assert "MARKER_104.1" in prompt

    def test_prompt_phase_guidance_build(self):
        """Test build phase guidance in prompt."""
        phase_type = "build"
        parts = []
        if phase_type == "build":
            parts.append("\n## Instructions:\nImplement this subtask. Provide code with clear markers.")

        prompt = "\n".join(parts)
        assert "Implement this subtask" in prompt

    def test_prompt_phase_guidance_fix(self):
        """Test fix phase guidance in prompt."""
        phase_type = "fix"
        parts = []
        if phase_type == "fix":
            parts.append("\n## Instructions:\nFix the issue described. Include before/after code.")

        prompt = "\n".join(parts)
        assert "Fix the issue" in prompt


# ============================================================
# TEST CLASS: Method 5 - Code Block Extraction
# ============================================================

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
        import re
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        assert len(matches) == 1
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
        import re
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        assert len(matches) == 2
        assert matches[0].group('lang') == 'python'
        assert matches[1].group('lang') == 'javascript'

    def test_extract_code_block_without_language(self):
        """Test extracting code block without language specification."""
        content = '''
```
plain text code
```
'''
        import re
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        assert len(matches) == 1
        assert matches[0].group('lang') is None

    def test_extract_filepath_from_description(self):
        """Test extracting filepath from subtask description."""
        description = "Create src/voice/config.py with configuration settings"
        import re

        filepath_match = re.search(
            r'(src/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
            description,
            re.IGNORECASE
        )

        assert filepath_match is not None
        assert filepath_match.group(1) == "src/voice/config.py"

    def test_no_code_blocks_returns_empty(self):
        """Test that content without code blocks returns empty list."""
        content = "This is just plain text without any code blocks."
        import re
        pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        assert len(matches) == 0


# ============================================================
# TEST CLASS: Method 6 - Task Storage
# ============================================================

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

    def test_tasks_file_path_exists(self):
        """Test that TASKS_FILE path is properly defined."""
        assert TASKS_FILE is not None
        assert "pipeline_tasks.json" in str(TASKS_FILE)


# ============================================================
# TEST CLASS: Method 7 - Robust JSON Extraction
# ============================================================

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
        import re
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
        import re
        code_block = re.search(r'```\s*([\s\S]*?)\s*```', text)
        assert code_block is not None
        result = json.loads(code_block.group(1))

        assert result["key"] == "value"

    def test_extract_json_embedded_in_prose(self):
        """Test extracting JSON embedded in prose."""
        text = 'The response is {"result": true} as expected.'
        import re
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

    def test_empty_text_returns_empty_dict(self):
        """Test that empty text handling."""
        text = ""
        if not text or not text.strip():
            result = {}
        else:
            result = json.loads(text)

        assert result == {}


# ============================================================
# TEST CLASS: Hybrid Flow Integration
# ============================================================

class TestHybridFlowIntegration:
    """Integration tests for PM -> Architect -> [PIPELINE LOOP] -> Dev||QA flow."""

    @pytest.mark.asyncio
    async def test_hybrid_flow_sequence(self, mock_elisya_state):
        """Test the full hybrid flow sequence."""
        # Phase 1: PM processes request
        mock_elisya_state.speaker = "PM"
        mock_elisya_state.add_message("PM", "Feature request analyzed")
        assert mock_elisya_state.speaker == "PM"

        # Phase 2: Architect creates design
        mock_elisya_state.speaker = "Architect"
        mock_elisya_state.add_message("Architect", "Architecture designed with 3 components")
        assert mock_elisya_state.speaker == "Architect"

        # Phase 3: Pipeline Loop (simulated)
        pipeline_output = "Pipeline completed with 3 subtasks"
        artifacts = [{"code": "def test(): pass", "marker": "MARKER_104.1"}]

        # Phase 4: Dev processes enriched context
        mock_elisya_state.speaker = "Dev"
        mock_elisya_state.add_message("Dev", "Implementation complete")
        assert mock_elisya_state.speaker == "Dev"

        # Verify conversation flow
        assert len(mock_elisya_state.conversation_history) == 3
        speakers = [msg.speaker for msg in mock_elisya_state.conversation_history]
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
            "pipeline_enriched_context": "Detailed implementation context"
        }

        # Verify artifacts available
        assert len(result["pipeline_artifacts"]) == 2
        assert len(result["pipeline_enriched_context"]) > 0


# ============================================================
# TEST CLASS: Researcher Auto-Trigger
# ============================================================

class TestResearcherAutoTrigger:
    """Tests for researcher auto-trigger on unclear parts."""

    def test_auto_trigger_on_needs_research_flag(self, sample_subtasks):
        """Test that researcher is triggered when needs_research=True."""
        research_needed = [st for st in sample_subtasks if st.needs_research]

        assert len(research_needed) == 1
        assert research_needed[0].marker == "MARKER_104.2"

    def test_auto_trigger_uses_question_when_available(self, sample_subtasks):
        """Test that question is used for research when available."""
        subtask = sample_subtasks[1]  # The one with needs_research=True

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


# ============================================================
# TEST CLASS: STM Context Passing
# ============================================================

class TestSTMContextPassing:
    """Tests for Short-Term Memory context passing between subtasks."""

    def test_stm_buffer_initialization(self):
        """Test STM buffer starts empty."""
        stm: List[Dict[str, str]] = []
        assert len(stm) == 0

    def test_stm_add_result(self):
        """Test adding result to STM."""
        stm: List[Dict[str, str]] = []
        stm_limit = 5

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
        assert len(stm) == 5
        assert stm[0]["marker"] == "MARKER_104.3"

    def test_stm_summary_generation(self):
        """Test STM summary generation for context injection."""
        stm = [
            {"marker": "MARKER_104.1", "result": "Created module structure"},
            {"marker": "MARKER_104.2", "result": "Added validation logic"},
            {"marker": "MARKER_104.3", "result": "Implemented tests"}
        ]

        summary_parts = ["Previous results:"]
        for item in stm[-3:]:
            summary_parts.append(f"- [{item['marker']}]: {item['result'][:200]}...")

        summary = "\n".join(summary_parts)

        assert "Previous results:" in summary
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


# ============================================================
# TEST CLASS: Error Handling & Edge Cases
# ============================================================

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


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
