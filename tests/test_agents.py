"""Test VETKA agents functionality"""
import pytest
import time
from src.agents import (
    VetkaPM, VetkaArchitect, VetkaDev, 
    VetkaQA, VetkaOps, VetkaVisual
)
from src.memory.weaviate_helper import WeaviateHelper

class TestVETKAAgents:
    """Test VETKA agents functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.whelper = WeaviateHelper()
        self.mock_socketio = None  # Mock socketio for testing
    
    def test_pm_agent(self):
        """Test Product Manager agent"""
        pm = VetkaPM(self.whelper, self.mock_socketio)
        
        assert pm.name == 'VETKA-PM'
        assert pm.context_limit > 0
        
        # Test basic task handling
        result = pm.handle_task("Create a new feature", {})
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ PM Agent test passed")
    
    def test_architect_agent(self):
        """Test System Architect agent"""
        architect = VetkaArchitect(self.whelper, self.mock_socketio)
        
        assert architect.name == 'VETKA-Architect'
        assert architect.context_limit > 0
        
        # Test basic task handling
        result = architect.handle_task("Design system architecture", {})
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ Architect Agent test passed")
    
    def test_dev_agent(self):
        """Test Developer agent"""
        dev = VetkaDev(self.whelper, self.mock_socketio)
        
        assert dev.name == 'VETKA-Dev'
        assert dev.context_limit > 0
        
        # Test basic task handling
        result = dev.handle_task("Implement new feature", {})
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ Dev Agent test passed")
    
    def test_qa_agent(self):
        """Test QA Engineer agent"""
        qa = VetkaQA(self.whelper, self.mock_socketio)
        
        assert qa.name == 'VETKA-QA'
        assert qa.context_limit > 0
        
        # Test basic task handling
        result = qa.handle_task("Test new feature", {})
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ QA Agent test passed")
    
    def test_ops_agent(self):
        """Test DevOps agent"""
        ops = VetkaOps(self.whelper, self.mock_socketio)
        
        assert ops.name == 'VETKA-Ops'
        assert ops.context_limit > 0
        
        # Test basic task handling
        result = ops.handle_task("Deploy new feature", {})
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ Ops Agent test passed")
    
    def test_visual_agent(self):
        """Test Visualization agent"""
        visual = VetkaVisual(self.whelper, self.mock_socketio)
        
        assert visual.name == 'VETKA-Visual'
        assert visual.context_limit > 0
        
        # Test basic task handling
        result = visual.handle_task("Create 3D visualization", {})
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ Visual Agent test passed")
    
    def test_agent_model_rotation(self):
        """Test agent model rotation"""
        pm = VetkaPM(self.whelper, self.mock_socketio)
        
        # Test model rotation
        initial_model = pm.current_model()
        pm.rotate_model()
        rotated_model = pm.current_model()
        
        # Models should be different after rotation (if multiple models available)
        if len(pm.model_pool) > 1:
            assert initial_model != rotated_model
        else:
            assert initial_model == rotated_model
        print("✅ Agent model rotation test passed")
    
    def test_agent_embedding(self):
        """Test agent text embedding"""
        pm = VetkaPM(self.whelper, self.mock_socketio)
        
        text = "Test embedding for agent"
        embedding = pm.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, (int, float)) for x in embedding)
        print("✅ Agent embedding test passed")

if __name__ == '__main__':
    # Run tests
    test_instance = TestVETKAAgents()
    test_instance.setup_method()
    
    try:
        test_instance.test_pm_agent()
        test_instance.test_architect_agent()
        test_instance.test_dev_agent()
        test_instance.test_qa_agent()
        test_instance.test_ops_agent()
        test_instance.test_visual_agent()
        test_instance.test_agent_model_rotation()
        test_instance.test_agent_embedding()
        print("\n🎉 All Agent tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
