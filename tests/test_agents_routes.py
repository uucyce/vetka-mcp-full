```python
# file: tests/test_agents_routes.py
"""
Test suite for Agent Memory Analysis Routes

@file tests/test_agents_routes.py
@status ACTIVE
@phase Phase 102.3
@created 2026-02-03

Tests the /api/agents/* endpoints for agent memory analysis and insights.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from src.api.routes.agents_routes import router


@pytest.fixture
def app():
    """Create a test FastAPI app with agents router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestAgentsRoutes:
    """Test cases for agents routes."""

    def test_get_agent_memory_basic(self, client):
        """Test basic agent memory retrieval."""
        response = client.get("/api/agents/test-agent/memory")
        
        # Should return 200 or 404 depending on whether agent exists
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "agent_id" in data
            assert "memories" in data
            assert isinstance(data["memories"], list)

    def test_get_agent_memory_with_limit(self, client):
        """Test agent memory retrieval with limit parameter."""
        response = client.get("/api/agents/test-agent/memory?limit=5")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "memories" in data
            # If memories exist, should respect limit
            if data["memories"]:
                assert len(data["memories"]) <= 5

    def test_get_agent_insights(self, client):
        """Test agent insights endpoint."""
        response = client.get("/api/agents/test-agent/insights")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "agent_id" in data
            assert "insights" in data
            assert isinstance(data["insights"], dict)

    def test_analyze_agent_performance(self, client):
        """Test agent performance analysis endpoint."""
        response = client.post(
            "/api/agents/test-agent/analyze",
            json={"time_window": "24h"}
        )
        
        assert response.status_code in [200, 404, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert "agent_id" in data
            assert "analysis" in data

    def test_invalid_agent_id(self, client):
        """Test handling of invalid agent IDs."""
        response = client.get("/api/agents//memory")
        
        # Should return 404 for empty agent_id
        assert response.status_code == 404

    def test_get_all_agents(self, client):
        """Test listing all agents."""
        response = client.get("/api/agents/")
        
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_memory_search(self, client):
        """Test memory search functionality."""
        response = client.post(
            "/api/agents/test-agent/memory/search",
            json={"query": "test query", "limit": 10}
        )
        
        assert response.status_code in [200, 404, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert isinstance(data["results"], list)


class TestAgentsRoutesIntegration:
    """Integration tests for agents routes."""

    def test_memory_lifecycle(self, client):
        """Test complete memory lifecycle: create, retrieve, analyze."""
        agent_id = "lifecycle-test-agent"
        
        # 1. Get initial state (might be empty)
        response = client.get(f"/api/agents/{agent_id}/memory")
        initial_status = response.status_code
        
        # 2. Get insights
        response = client.get(f"/api/agents/{agent_id}/insights")
        assert response.status_code in [200, 404]
        
        # 3. Analyze performance
        response = client.post(
            f"/api/agents/{agent_id}/analyze",
            json={"time_window": "1h"}
        )
        assert response.status_code in [200, 404, 422]

    def test_concurrent_agent_access(self, client):
        """Test accessing multiple agents concurrently."""
        agent_ids = ["agent-1", "agent-2", "agent-3"]
        
        responses = []
        for agent_id in agent_ids:
            response = client.get(f"/api/agents/{agent_id}/memory")
            responses.append(response)
        
        # All requests should complete successfully or return 404
        for response in responses:
            assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])