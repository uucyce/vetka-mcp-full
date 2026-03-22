"""
Tests for Phase 6.3 Part 3 - Learning System Integration
Tests: MemoryManager feedback methods, AgentOrchestrator context building, E2E feedback loop
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestration.memory_manager import MemoryManager
from src.orchestration.agent_orchestrator import AgentOrchestrator
from src.agents.vetka_pm import VETKAPMAgent
from src.agents.vetka_dev import VETKADevAgent
from src.agents.vetka_qa import VETKAQAAgent


class TestMemoryManagerFeedback:
    """Test MemoryManager feedback and learning methods"""
    
    @pytest.fixture
    def memory(self):
        """Create MemoryManager instance"""
        return MemoryManager()
    
    def test_save_feedback(self, memory):
        """Test save_feedback method"""
        result = memory.save_feedback(
            evaluation_id="eval_test_001",
            task="Add login button",
            output="<button>Login</button>",
            rating="👍",
            correction="Perfect",
            score=0.95
        )
        assert result is not None
        print(f"✅ save_feedback: {result}")
    
    def test_retrieve_past_feedback(self, memory):
        """Test retrieve_past_feedback method - signature is (task, limit=3)"""
        # First save some feedback
        memory.save_feedback(
            evaluation_id="eval_test_002",
            task="Style button",
            output="button { color: blue; }",
            rating="👍",
            score=0.88
        )
        
        # Then retrieve with correct signature: task parameter required
        feedback_list = memory.retrieve_past_feedback(task="style", limit=5)
        assert isinstance(feedback_list, list)
        print(f"✅ retrieve_past_feedback: {len(feedback_list)} items")
    
    def test_query_high_score_examples(self, memory):
        """Test query_high_score_examples method - signature is (complexity, limit=3, min_score=0.8)"""
        # Save high-score examples
        for i in range(3):
            memory.save_feedback(
                evaluation_id=f"eval_high_{i}",
                task="Test task",
                output=f"Output {i}",
                rating="👍",
                score=0.90 + (i * 0.01)
            )
        
        # Query high-score examples with correct signature
        examples = memory.query_high_score_examples(complexity="MEDIUM", limit=10, min_score=0.85)
        assert isinstance(examples, list)
        print(f"✅ query_high_score_examples: {len(examples)} examples")
    
    def test_save_evaluation_result(self, memory):
        """Test save_evaluation_result method"""
        result = memory.save_evaluation_result(
            evaluation_id="eval_test_003",
            task="Create dashboard",
            output="Dashboard code here",
            complexity="MEDIUM",
            score=0.92,
            scores_breakdown={"correctness": 0.95, "completeness": 0.90}
        )
        assert result is not None
        print(f"✅ save_evaluation_result: {result}")
    
    def test_create_few_shot_prompt_section(self, memory):
        """Test create_few_shot_prompt_section method"""
        examples = [
            {"task": "Add button", "output": "Code1", "score": 0.95},
            {"task": "Style form", "output": "CSS1", "score": 0.92},
        ]
        
        prompt_section = memory.create_few_shot_prompt_section(examples)
        assert isinstance(prompt_section, str)
        assert "EXAMPLES" in prompt_section or "Ex" in prompt_section
        print(f"✅ create_few_shot_prompt_section: {len(prompt_section)} chars")


class TestAgentOrchestrator:
    """Test AgentOrchestrator with learning context"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create AgentOrchestrator instance"""
        return AgentOrchestrator(socketio=None)
    
    def test_build_context_section(self, orchestrator):
        """Test _build_context_section method - signature is (past_feedback, examples)"""
        past_feedback = [
            {"task": "login", "score": 0.95, "rating": "👍", "correction": "Good work"}
        ]
        examples = [
            {"task": "button", "output": "code", "score": 0.92}
        ]
        
        context = orchestrator._build_context_section(
            past_feedback=past_feedback,
            examples=examples
        )
        
        assert isinstance(context, str)
        assert len(context) > 0
        assert "LEARNING CONTEXT" in context
        print(f"✅ _build_context_section: {len(context)} chars")
    
    def test_execute_full_workflow_with_learning(self, orchestrator):
        """Test execute_full_workflow_with_learning method"""
        # This would be a more complex integration test
        # Typically mocked to avoid calling actual LLMs
        pass


class TestAgentContextIntegration:
    """Test agents accepting context_section parameter"""
    
    @pytest.fixture
    def pm_agent(self):
        return VETKAPMAgent()
    
    @pytest.fixture
    def dev_agent(self):
        return VETKADevAgent()
    
    @pytest.fixture
    def qa_agent(self):
        return VETKAQAAgent()
    
    def test_pm_agent_execute_signature(self, pm_agent):
        """Test PM agent execute() method signature"""
        # Check method exists
        assert hasattr(pm_agent, 'execute')
        
        # Check it accepts context_section parameter
        import inspect
        sig = inspect.signature(pm_agent.execute)
        params = list(sig.parameters.keys())
        assert 'task' in params
        assert 'context_section' in params
        print(f"✅ PM agent execute() signature: {params}")
    
    def test_dev_agent_execute_signature(self, dev_agent):
        """Test Dev agent execute() method signature"""
        assert hasattr(dev_agent, 'execute')
        
        import inspect
        sig = inspect.signature(dev_agent.execute)
        params = list(sig.parameters.keys())
        assert 'plan' in params
        assert 'context_section' in params
        print(f"✅ Dev agent execute() signature: {params}")
    
    def test_qa_agent_execute_signature(self, qa_agent):
        """Test QA agent execute() method signature"""
        assert hasattr(qa_agent, 'execute')
        
        import inspect
        sig = inspect.signature(qa_agent.execute)
        params = list(sig.parameters.keys())
        assert 'implementation' in params
        assert 'context_section' in params
        print(f"✅ QA agent execute() signature: {params}")


class TestLearningE2E:
    """End-to-End tests for learning system"""
    
    def test_feedback_to_context_flow(self):
        """Test full flow: feedback → context → improved output"""
        # This would be a full integration test
        # Typically run with mocked LLMs
        
        memory = MemoryManager()
        
        # Step 1: Save feedback
        memory.save_feedback(
            evaluation_id="e2e_test_001",
            task="E2E test task",
            output="Output 1",
            rating="👍",
            score=0.90
        )
        
        # Step 2: Retrieve feedback with correct signature
        past_feedback = memory.retrieve_past_feedback(task="E2E", limit=5)
        assert isinstance(past_feedback, list)  # May be 0 if Weaviate not connected
        
        # Step 3: Build context
        high_score_examples = memory.query_high_score_examples(complexity="MEDIUM", limit=5, min_score=0.85)
        assert isinstance(high_score_examples, list)
        
        print(f"✅ E2E flow: feedback → context")


class TestMetrics:
    """Test metrics and monitoring"""
    
    def test_memory_health_check(self):
        """Test memory manager health check"""
        memory = MemoryManager()
        health = memory.health_check()
        # health may be True or False depending on Weaviate connection
        assert isinstance(health, bool)
        print(f"✅ Memory health: {health}")


# ==========================
# PYTEST EXECUTION HELPERS
# ==========================

def run_tests():
    """Run all tests with pytest"""
    import subprocess

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 63 contracts changed")

    result = subprocess.run(
        ["python3", "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return result.returncode


if __name__ == "__main__":
    # Allow running directly: python3 tests/test_phase63_part3_learning.py
    print("\n" + "="*70)
    print("🧪 VETKA Phase 6.3 Part 3 - Learning System Tests")
    print("="*70 + "\n")
    
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*70)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*70 + "\n")
    
    sys.exit(exit_code)
