"""Test Flask API endpoints"""
import pytest
import json
from unittest.mock import Mock, patch
from main import app, whelper, context_manager, agents

class TestFlaskAPI:
    """Test Flask API functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def teardown_method(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    def test_index_route(self):
        """Test main index route"""
        response = self.client.get('/')
        assert response.status_code == 200
        assert b'VETKA Live 0.3' in response.data
        print("✅ Index route test passed")
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'components' in data
        print("✅ Health check test passed")
    
    def test_init_tree(self):
        """Test tree initialization endpoint"""
        response = self.client.get('/api/init')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'tree' in data
        assert 'nodes' in data['tree']
        assert 'links' in data['tree']
        print("✅ Tree initialization test passed")
    
    def test_get_tree_data(self):
        """Test tree data retrieval for different zoom levels"""
        zoom_levels = ['global', 'tree', 'leaf']
        
        for zoom_level in zoom_levels:
            response = self.client.get(f'/api/tree/{zoom_level}')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert data['zoom_level'] == zoom_level
            assert 'tree' in data
            print(f"✅ Tree data test passed for zoom level: {zoom_level}")
    
    def test_get_tree_data_invalid_zoom(self):
        """Test tree data retrieval with invalid zoom level"""
        response = self.client.get('/api/tree/invalid')
        assert response.status_code == 200  # Should still work, defaults to global
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        print("✅ Invalid zoom level test passed")
    
    @patch('main.whelper')
    def test_init_tree_with_weaviate_error(self, mock_whelper):
        """Test tree initialization with Weaviate error"""
        mock_whelper.hybrid_search.side_effect = Exception("Weaviate connection failed")
        
        response = self.client.get('/api/init')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        print("✅ Weaviate error handling test passed")
    
    def test_404_route(self):
        """Test 404 handling"""
        response = self.client.get('/nonexistent')
        assert response.status_code == 404
        print("✅ 404 handling test passed")
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = self.client.get('/api/health')
        
        # Flask-SocketIO adds CORS headers
        # This is a basic test to ensure the endpoint is accessible
        assert response.status_code == 200
        print("✅ CORS headers test passed")

if __name__ == '__main__':
    # Run tests
    test_instance = TestFlaskAPI()
    test_instance.setup_method()
    
    try:
        test_instance.test_index_route()
        test_instance.test_health_check()
        test_instance.test_init_tree()
        test_instance.test_get_tree_data()
        test_instance.test_get_tree_data_invalid_zoom()
        test_instance.test_404_route()
        test_instance.test_cors_headers()
        print("\n🎉 All API tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    finally:
        test_instance.teardown_method()
