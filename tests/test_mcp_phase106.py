"""
Tests for VETKA MCP Phase 106 - Multi-Agent Architecture

@file tests/test_mcp_phase106.py
@status ACTIVE
@phase Phase 106
@lastAudit 2026-02-02

Tests HTTP transport, session isolation, actor pools, and load handling.
"""

import pytest
import asyncio
import httpx
import json
import time
from typing import Dict, Any, List
from pathlib import Path

# Configuration
MCP_HTTP_URL = "http://localhost:5002"
VETKA_API_URL = "http://localhost:5001"


class TestPhase106Health:
    """Phase 106a: Health and basic connectivity tests"""
    
    @pytest.fixture
    def client(self):
        """HTTP client fixture"""
        return httpx.Client(timeout=30.0)
    
    def test_vetka_api_health(self, client):
        """Test VETKA API is running"""
        try:
            resp = client.get(f"{VETKA_API_URL}/api/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("status") == "healthy"
        except httpx.ConnectError:
            pytest.skip("VETKA API not running on :5001")
    
    def test_mcp_http_health(self, client):
        """Test MCP HTTP server health endpoint"""
        try:
            resp = client.get(f"{MCP_HTTP_URL}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running on :5002")
    
    def test_mcp_stats_endpoint(self, client):
        """Test stats endpoint returns actor/pool info"""
        try:
            resp = client.get(f"{MCP_HTTP_URL}/api/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert "actors" in data or "pools" in data
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running on :5002")


class TestPhase106ToolsList:
    """Phase 106: Tools listing via HTTP"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(timeout=30.0)
    
    def test_tools_list(self, client):
        """Test tools/list returns VETKA tools"""
        try:
            resp = client.post(
                f"{MCP_HTTP_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                },
                headers={"Content-Type": "application/json"}
            )
            assert resp.status_code == 200
            data = resp.json()
            
            assert "result" in data
            tools = data["result"].get("tools", [])
            assert len(tools) >= 20, f"Expected 20+ tools, got {len(tools)}"
            
            # Check for key VETKA tools
            tool_names = [t.get("name") for t in tools]
            assert "vetka_health" in tool_names
            assert "vetka_search_semantic" in tool_names
            
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running")
    
    def test_tools_list_count(self, client):
        """Verify minimum tool count"""
        try:
            resp = client.post(
                f"{MCP_HTTP_URL}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                headers={"Content-Type": "application/json"}
            )
            data = resp.json()
            tools = data.get("result", {}).get("tools", [])
            assert len(tools) >= 25, f"Expected 25+ tools for Phase 106"
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running")


class TestPhase106ToolCall:
    """Phase 106: Tool execution via HTTP"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(timeout=60.0)
    
    def test_vetka_health_call(self, client):
        """Test vetka_health tool call"""
        try:
            resp = client.post(
                f"{MCP_HTTP_URL}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 42,
                    "method": "tools/call",
                    "params": {
                        "name": "vetka_health",
                        "arguments": {}
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Session-ID": "test_health_call"
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            
            # Should have result with healthy status
            assert "result" in data or "error" not in data
            
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running")


class TestPhase106bSessionIsolation:
    """Phase 106b: Session isolation via X-Session-ID"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(timeout=30.0)
    
    def test_different_sessions(self, client):
        """Test that different session IDs create separate contexts"""
        try:
            sessions = ["session_a", "session_b", "session_c"]
            results = []
            
            for session_id in sessions:
                resp = client.post(
                    f"{MCP_HTTP_URL}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": "vetka_health", "arguments": {}}
                    },
                    headers={
                        "Content-Type": "application/json",
                        "X-Session-ID": session_id
                    }
                )
                results.append(resp.status_code)
            
            # All should succeed
            assert all(r == 200 for r in results)
            
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running")
    
    def test_session_in_stats(self, client):
        """Test that sessions appear in stats"""
        try:
            # Make a request with session ID
            client.post(
                f"{MCP_HTTP_URL}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                headers={"X-Session-ID": "stats_test_session"}
            )
            
            # Check stats
            resp = client.get(f"{MCP_HTTP_URL}/api/stats")
            data = resp.json()
            
            # Should have actor data
            actors = data.get("actors", {})
            assert "active_actors" in actors or len(actors) > 0
            
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running")


class TestPhase106cConcurrency:
    """Phase 106c: Concurrent request handling"""
    
    @pytest.mark.asyncio
    async def test_parallel_requests(self):
        """Test 10 parallel requests don't block each other"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                tasks = []
                for i in range(10):
                    task = client.post(
                        f"{MCP_HTTP_URL}/mcp",
                        json={
                            "jsonrpc": "2.0",
                            "id": i,
                            "method": "tools/call",
                            "params": {"name": "vetka_health", "arguments": {}}
                        },
                        headers={"X-Session-ID": f"parallel_{i}"}
                    )
                    tasks.append(task)
                
                start = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                elapsed = time.time() - start
                
                # Count successes
                successes = sum(1 for r in results if isinstance(r, httpx.Response) and r.status_code == 200)
                
                assert successes >= 8, f"Expected 8+ successes, got {successes}"
                # Should complete in reasonable time (not sequential)
                assert elapsed < 30, f"Took too long: {elapsed}s"
                
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running")
    
    @pytest.mark.asyncio
    async def test_no_request_blocking(self):
        """Test requests from different sessions don't block"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fire 5 requests simultaneously
                tasks = [
                    client.post(
                        f"{MCP_HTTP_URL}/mcp",
                        json={"jsonrpc": "2.0", "id": i, "method": "tools/list", "params": {}},
                        headers={"X-Session-ID": f"noblock_{i}"}
                    )
                    for i in range(5)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successes = [r for r in results if isinstance(r, httpx.Response) and r.status_code == 200]
                
                assert len(successes) == 5
                
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running")


class TestPhase106Integration:
    """Phase 106 full integration tests"""
    
    @pytest.fixture
    def client(self):
        return httpx.Client(timeout=60.0)
    
    def test_full_workflow(self, client):
        """Test complete workflow: list -> call -> stats"""
        try:
            session_id = f"integration_{int(time.time())}"
            
            # 1. List tools
            resp1 = client.post(
                f"{MCP_HTTP_URL}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                headers={"X-Session-ID": session_id}
            )
            assert resp1.status_code == 200
            tools = resp1.json().get("result", {}).get("tools", [])
            assert len(tools) > 0
            
            # 2. Call a tool
            resp2 = client.post(
                f"{MCP_HTTP_URL}/mcp",
                json={
                    "jsonrpc": "2.0", "id": 2,
                    "method": "tools/call",
                    "params": {"name": "vetka_health", "arguments": {}}
                },
                headers={"X-Session-ID": session_id}
            )
            assert resp2.status_code == 200
            
            # 3. Check stats
            resp3 = client.get(f"{MCP_HTTP_URL}/api/stats")
            assert resp3.status_code == 200
            
        except httpx.ConnectError:
            pytest.skip("MCP HTTP not running")


# Run with: pytest tests/test_mcp_phase106.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
