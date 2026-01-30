"""Test Weaviate connection and CRUD operations"""
import pytest
import time
from src.memory.weaviate_helper import WeaviateHelper
from config.config import VECTOR_SIZE

class TestWeaviateHelper:
    """Test Weaviate helper functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.whelper = WeaviateHelper()
    
    def test_connection(self):
        """Test Weaviate connection"""
        # Connection is tested in __init__, just verify helper exists
        assert self.whelper is not None
        print("✅ Weaviate connection test passed")
    
    def test_embed_text(self):
        """Test text embedding generation"""
        text = "Test embedding text"
        embedding = self.whelper.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == VECTOR_SIZE
        assert all(isinstance(x, (int, float)) for x in embedding)
        print("✅ Text embedding test passed")
    
    def test_upsert_node(self):
        """Test node upsertion"""
        node_id = f"test_node_{int(time.time())}"
        vector = [0.1] * VECTOR_SIZE
        payload = {
            'content': 'Test content',
            'path': '/test/path',
            'node_type': 'test',
            'timestamp': time.time()
        }
        
        result_id = self.whelper.upsert_node(node_id, vector, payload)
        assert result_id == node_id
        print("✅ Node upsert test passed")
    
    def test_hybrid_search(self):
        """Test hybrid search functionality"""
        # First create a test node
        node_id = f"search_test_{int(time.time())}"
        vector = self.whelper.embed_text("Search test content")
        payload = {
            'content': 'Search test content',
            'path': '/search/test',
            'node_type': 'test',
            'timestamp': time.time()
        }
        
        self.whelper.upsert_node(node_id, vector, payload)
        
        # Wait a moment for indexing
        time.sleep(1)
        
        # Search for the node
        results = self.whelper.hybrid_search("Search test", limit=5)
        assert isinstance(results, list)
        print("✅ Hybrid search test passed")
    
    def test_get_tree_structure(self):
        """Test tree structure retrieval"""
        tree_data = self.whelper.get_tree_structure('global')
        
        assert isinstance(tree_data, dict)
        assert 'nodes' in tree_data
        assert 'links' in tree_data
        assert isinstance(tree_data['nodes'], list)
        assert isinstance(tree_data['links'], list)
        print("✅ Tree structure test passed")
    
    def test_add_log(self):
        """Test changelog functionality"""
        log_data = {
            'action': 'test_action',
            'initiator': 'test_user',
            'path': '/test/path',
            'status': 'success'
        }
        
        # Should not raise an exception
        self.whelper.add_log(log_data)
        print("✅ Add log test passed")

if __name__ == '__main__':
    # Run tests
    test_instance = TestWeaviateHelper()
    test_instance.setup_method()
    
    try:
        test_instance.test_connection()
        test_instance.test_embed_text()
        test_instance.test_upsert_node()
        test_instance.test_hybrid_search()
        test_instance.test_get_tree_structure()
        test_instance.test_add_log()
        print("\n🎉 All Weaviate tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
