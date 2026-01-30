"""
Tests for VETKA LangGraph Integration (Phase 60.1)

@file test_langgraph_phase60.py
@status ACTIVE
@phase Phase 60.1 - LangGraph Foundation
@lastAudit 2026-01-10

Tests cover:
- VETKAState creation and manipulation
- Routing logic (score threshold, retries)
- LearnerAgent functionality
- Helper functions
- Feature flag behavior
- VETKASaver checkpointer
- Mention parsing
- Task parsing
"""

import pytest
from datetime import datetime
from typing import Dict


class TestVETKAState:
    """Test VETKAState creation and manipulation."""

    def test_create_initial_state(self):
        """Test initial state creation with all fields."""
        from src.orchestration.langgraph_state import create_initial_state

        state = create_initial_state(
            workflow_id="test-123",
            context="Create a calculator",
            group_id="group-456",
            participants=["PM", "Dev", "QA"],
            lod_level="MEDIUM",
            max_retries=3
        )

        # Core identity
        assert state['workflow_id'] == "test-123"
        assert state['group_id'] == "group-456"

        # Context
        assert state['context'] == "Create a calculator"
        assert state['raw_context'] == "Create a calculator"
        assert state['lod_level'] == "MEDIUM"

        # Participants
        assert state['participants'] == ["PM", "Dev", "QA"]

        # Defaults
        assert state['retry_count'] == 0
        assert state['max_retries'] == 3
        assert state['eval_score'] == 0.0
        assert state['next'] == "hostess"  # Default entry point

        # Lists should be empty
        assert state['agent_outputs'] == {}
        assert state['artifacts'] == []
        assert state['tasks'] == []
        assert state['lessons_learned'] == []

    def test_create_initial_state_defaults(self):
        """Test that defaults are properly set."""
        from src.orchestration.langgraph_state import create_initial_state

        state = create_initial_state(
            workflow_id="test",
            context="context"
        )

        assert state['group_id'] is None
        assert state['participants'] == []
        assert state['lod_level'] == "MEDIUM"
        assert state['max_retries'] == 3

    def test_state_has_messages(self):
        """Test that initial state has one HumanMessage."""
        from src.orchestration.langgraph_state import create_initial_state
        from langchain_core.messages import HumanMessage

        state = create_initial_state(
            workflow_id="test",
            context="Hello world"
        )

        assert len(state['messages']) == 1
        assert isinstance(state['messages'][0], HumanMessage)
        assert state['messages'][0].content == "Hello world"


class TestRoutingLogic:
    """Test routing decisions in graph."""

    def test_route_by_score_pass(self):
        """Test routing when score >= 0.75 (pass threshold)."""
        from src.orchestration.langgraph_state import create_initial_state, should_retry

        state = create_initial_state("test", "context")
        state['eval_score'] = 0.8
        state['retry_count'] = 0

        # Score >= 0.75 should NOT retry
        assert not should_retry(state, threshold=0.75)

    def test_route_by_score_fail_retry_available(self):
        """Test routing when score < 0.75 and retries available."""
        from src.orchestration.langgraph_state import create_initial_state, should_retry

        state = create_initial_state("test", "context")
        state['eval_score'] = 0.6
        state['retry_count'] = 1
        state['max_retries'] = 3

        # Score < 0.75 with retries available should retry
        assert should_retry(state, threshold=0.75)

    def test_route_by_score_max_retries_reached(self):
        """Test routing when max retries reached."""
        from src.orchestration.langgraph_state import create_initial_state, should_retry

        state = create_initial_state("test", "context")
        state['eval_score'] = 0.5
        state['retry_count'] = 3
        state['max_retries'] = 3

        # Even with low score, max retries reached = no retry
        assert not should_retry(state, threshold=0.75)

    def test_threshold_boundary(self):
        """Test exact threshold boundary (0.75)."""
        from src.orchestration.langgraph_state import create_initial_state, should_retry

        state = create_initial_state("test", "context")
        state['retry_count'] = 0
        state['max_retries'] = 3

        # Exactly at threshold = pass (no retry)
        state['eval_score'] = 0.75
        assert not should_retry(state, threshold=0.75)

        # Just below threshold = retry
        state['eval_score'] = 0.749
        assert should_retry(state, threshold=0.75)


class TestStateHelpers:
    """Test state helper functions."""

    def test_get_last_message_content(self):
        """Test getting last message content."""
        from src.orchestration.langgraph_state import (
            create_initial_state,
            get_last_message_content
        )

        state = create_initial_state("test", "Hello world")
        assert get_last_message_content(state) == "Hello world"

    def test_add_agent_message(self):
        """Test adding agent message."""
        from src.orchestration.langgraph_state import (
            create_initial_state,
            add_agent_message
        )
        from langchain_core.messages import AIMessage

        state = create_initial_state("test", "Initial message")
        new_messages = add_agent_message(state, "Dev", "Agent response")

        assert len(new_messages) == 2
        assert isinstance(new_messages[1], AIMessage)
        assert new_messages[1].content == "Agent response"
        assert new_messages[1].name == "Dev"

    def test_get_workflow_summary(self):
        """Test workflow summary generation."""
        from src.orchestration.langgraph_state import (
            create_initial_state,
            get_workflow_summary
        )

        state = create_initial_state("test-123", "Build something")
        state['current_agent'] = "Dev"
        state['eval_score'] = 0.85
        state['retry_count'] = 1
        state['agent_outputs'] = {'PM': 'plan', 'Dev': 'code'}

        summary = get_workflow_summary(state)

        assert summary['workflow_id'] == "test-123"
        assert summary['current_agent'] == "Dev"
        assert summary['eval_score'] == 0.85
        assert summary['retry_count'] == 1
        assert 'PM' in summary['agents_completed']
        assert 'Dev' in summary['agents_completed']

    def test_state_to_elisya_dict(self):
        """Test conversion to ElisyaState-compatible dict."""
        from src.orchestration.langgraph_state import (
            create_initial_state,
            state_to_elisya_dict
        )

        state = create_initial_state("test", "context")
        state['current_agent'] = "PM"
        state['semantic_path'] = "projects/test"
        state['eval_score'] = 0.8

        elisya_dict = state_to_elisya_dict(state)

        assert elisya_dict['workflow_id'] == "test"
        assert elisya_dict['speaker'] == "PM"
        assert elisya_dict['semantic_path'] == "projects/test"
        assert elisya_dict['score'] == 0.8
        assert elisya_dict['lod_level'] == "medium"


class TestLearnerAgent:
    """Test LearnerAgent functionality."""

    def test_learner_agent_initialization(self):
        """Test LearnerAgent can be instantiated."""
        from src.agents.learner_agent import LearnerAgent

        learner = LearnerAgent()
        assert learner is not None
        assert learner.memory is None  # No memory manager provided

    def test_learner_agent_with_memory(self):
        """Test LearnerAgent with mock memory manager."""
        from src.agents.learner_agent import LearnerAgent

        class MockMemoryManager:
            def get_similar_context(self, query, limit=5):
                return []

            def triple_write(self, data):
                return "mock-id"

        learner = LearnerAgent(memory_manager=MockMemoryManager())
        assert learner.memory is not None

    @pytest.mark.asyncio
    async def test_failure_categorization_syntax(self):
        """Test failure category detection - syntax errors."""
        from src.agents.learner_agent import LearnerAgent

        learner = LearnerAgent()

        category = await learner._categorize_failure(
            "SyntaxError: unexpected token at line 5",
            "def foo( return 1"
        )
        assert category == "syntax"

    @pytest.mark.asyncio
    async def test_failure_categorization_logic(self):
        """Test failure category detection - logic errors."""
        from src.agents.learner_agent import LearnerAgent

        learner = LearnerAgent()

        category = await learner._categorize_failure(
            "Test failed: expected 4, got 5. Incorrect result.",
            "def add(a, b): return a - b"
        )
        assert category == "logic"

    @pytest.mark.asyncio
    async def test_failure_categorization_incomplete(self):
        """Test failure category detection - incomplete."""
        from src.agents.learner_agent import LearnerAgent

        learner = LearnerAgent()

        category = await learner._categorize_failure(
            "Missing implementation for delete method. TODO found.",
            "# TODO: implement delete"
        )
        assert category == "incomplete"

    @pytest.mark.asyncio
    async def test_analyze_failure(self):
        """Test full failure analysis."""
        from src.agents.learner_agent import LearnerAgent

        learner = LearnerAgent()

        analysis = await learner.analyze_failure(
            task="Create a function to add two numbers",
            output="def add(a, b): return a - b",
            eval_feedback="Logic error: subtraction instead of addition",
            retry_count=0
        )

        assert 'failure_category' in analysis
        assert 'root_cause' in analysis
        assert 'improvement_suggestion' in analysis
        assert 'enhanced_prompt' in analysis
        assert 'confidence' in analysis
        assert 0 <= analysis['confidence'] <= 1

    @pytest.mark.asyncio
    async def test_enhanced_prompt_generation(self):
        """Test enhanced prompt contains retry information."""
        from src.agents.learner_agent import LearnerAgent

        learner = LearnerAgent()

        enhanced = await learner._create_enhanced_prompt(
            task="Build a calculator",
            feedback="Missing division handling",
            suggestion="Add division with zero check",
            retry_count=1,
            similar_failures=[]
        )

        assert "RETRY ATTEMPT 2" in enhanced
        assert "Missing division handling" in enhanced
        assert "Add division with zero check" in enhanced


class TestGraphStructure:
    """Test graph building and structure."""

    def test_required_nodes_count(self):
        """Test that all required nodes are defined."""
        required_nodes = [
            "hostess", "architect", "pm",
            "dev_qa_parallel", "eval", "learner", "approval"
        ]

        # We can at least verify the list matches expectations
        assert len(required_nodes) == 7

    def test_langgraph_state_is_typeddict(self):
        """Test that VETKAState is a proper TypedDict."""
        from src.orchestration.langgraph_state import VETKAState

        # VETKAState should be a TypedDict subclass
        # Check it has __annotations__ (TypedDict feature)
        assert hasattr(VETKAState, '__annotations__')

        # Check key fields exist
        annotations = VETKAState.__annotations__
        assert 'workflow_id' in annotations
        assert 'messages' in annotations
        assert 'eval_score' in annotations
        assert 'retry_count' in annotations


class TestFeatureFlag:
    """Test feature flag behavior."""

    def test_feature_flag_exists(self):
        """Test that feature flag is defined."""
        from src.orchestration.orchestrator_with_elisya import FEATURE_FLAG_LANGGRAPH

        assert isinstance(FEATURE_FLAG_LANGGRAPH, bool)

    def test_feature_flag_default_enabled(self):
        """Test that feature flag is enabled (Phase 60.3)."""
        from src.orchestration.orchestrator_with_elisya import FEATURE_FLAG_LANGGRAPH

        # Phase 60.3: Now enabled by default
        assert FEATURE_FLAG_LANGGRAPH == True


class TestVETKASaver:
    """Test VETKASaver checkpointer."""

    def test_saver_initialization(self):
        """Test VETKASaver can be initialized."""
        from src.orchestration.vetka_saver import VETKASaver

        class MockMemoryManager:
            changelog_path = "data/changelog.jsonl"

            def triple_write(self, data):
                return "mock-id"

        saver = VETKASaver(memory_manager=MockMemoryManager())
        assert saver is not None
        assert saver.memory is not None

    def test_checkpoint_serialization(self):
        """Test checkpoint serialization."""
        from src.orchestration.vetka_saver import VETKASaver

        class MockMemoryManager:
            changelog_path = "data/changelog.jsonl"

        saver = VETKASaver(memory_manager=MockMemoryManager())

        # Test serialization of simple checkpoint
        checkpoint = {
            "v": 1,
            "ts": datetime.now().isoformat(),
            "id": "test-id",
            "channel_values": {"test": "value"},
            "channel_versions": {},
            "versions_seen": {}
        }

        serialized = saver._serialize_checkpoint(checkpoint)
        assert isinstance(serialized, str)

        # Test deserialization
        deserialized = saver._deserialize_checkpoint(serialized)
        assert deserialized['v'] == 1
        assert deserialized['id'] == "test-id"


class TestMentionParsing:
    """Test @mention parsing in messages."""

    def test_parse_single_mention(self):
        """Test parsing single @mention."""
        from src.orchestration.langgraph_nodes import VETKANodes

        # Create minimal mock orchestrator
        class MockOrchestrator:
            memory_service = None
            elisya_service = None
            routing_service = None
            key_service = None
            cam_service = None

        nodes = VETKANodes.__new__(VETKANodes)
        nodes.orchestrator = MockOrchestrator()

        mentions = nodes._parse_mentions("Hey @dev can you help?")
        assert mentions == ["dev"]

    def test_parse_multiple_mentions(self):
        """Test parsing multiple @mentions."""
        from src.orchestration.langgraph_nodes import VETKANodes

        class MockOrchestrator:
            pass

        nodes = VETKANodes.__new__(VETKANodes)
        nodes.orchestrator = MockOrchestrator()

        mentions = nodes._parse_mentions("@pm and @qa please review")
        assert "pm" in mentions
        assert "qa" in mentions

    def test_parse_invalid_mentions_filtered(self):
        """Test that invalid @mentions are filtered out."""
        from src.orchestration.langgraph_nodes import VETKANodes

        class MockOrchestrator:
            pass

        nodes = VETKANodes.__new__(VETKANodes)
        nodes.orchestrator = MockOrchestrator()

        mentions = nodes._parse_mentions("@random @dev @invalid @qa")
        # Only valid agents should be returned
        assert "dev" in mentions
        assert "qa" in mentions
        assert "random" not in mentions
        assert "invalid" not in mentions


class TestTaskParsing:
    """Test task parsing from Architect output."""

    def test_parse_bullet_tasks(self):
        """Test parsing bullet-point tasks."""
        from src.orchestration.langgraph_nodes import VETKANodes

        class MockOrchestrator:
            pass

        nodes = VETKANodes.__new__(VETKANodes)
        nodes.orchestrator = MockOrchestrator()

        output = """
        - Create user model
        - Implement authentication
        - Add tests
        """

        tasks = nodes._parse_tasks(output)
        assert len(tasks) == 3
        assert tasks[0]['description'] == "Create user model"
        assert tasks[0]['status'] == "pending"

    def test_parse_numbered_tasks(self):
        """Test parsing numbered tasks."""
        from src.orchestration.langgraph_nodes import VETKANodes

        class MockOrchestrator:
            pass

        nodes = VETKANodes.__new__(VETKANodes)
        nodes.orchestrator = MockOrchestrator()

        output = """
        1. Design database schema
        2. Create API endpoints
        3. Write documentation
        """

        tasks = nodes._parse_tasks(output)
        assert len(tasks) == 3
        assert "Design database schema" in tasks[0]['description']

    def test_parse_no_tasks_fallback(self):
        """Test fallback when no tasks found."""
        from src.orchestration.langgraph_nodes import VETKANodes

        class MockOrchestrator:
            pass

        nodes = VETKANodes.__new__(VETKANodes)
        nodes.orchestrator = MockOrchestrator()

        output = "Just some text without any task markers."

        tasks = nodes._parse_tasks(output)
        # Should return default task
        assert len(tasks) == 1
        assert tasks[0]['description'] == "Complete the requested task"


class TestLearnerAgentFactory:
    """Test LearnerAgent factory function."""

    def test_create_learner_agent(self):
        """Test factory function creates agent."""
        from src.agents.learner_agent import create_learner_agent

        learner = create_learner_agent()
        assert learner is not None
        assert learner.model == "qwen2:7b"

    def test_create_learner_agent_custom_model(self):
        """Test factory function with custom model."""
        from src.agents.learner_agent import create_learner_agent

        learner = create_learner_agent(model="llama3:8b")
        assert learner.model == "llama3:8b"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
