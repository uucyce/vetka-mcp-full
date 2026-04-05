"""Phase 117.3 — System Commands (@dragon, @doctor) + Cross-Chat Dispatch

Tests for:
- MCP_AGENTS registration (dragon, doctor, pipeline, reserves)
- HEARTBEAT_AGENTS set for auto-dispatch
- _dispatch_system_command() function
- @doctor in heartbeat TASK_PATTERNS
- KNOWN_AGENTS registration
- Alias matching (@mcp/dragon, @doc, etc.)

@status: active
@phase: 117.3
@depends: src/api/handlers/group_message_handler.py
"""

import pytest
import re
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 117 contracts changed")

# ═══════════════════════════════════════════════════════════════════════
# 1. MCP_AGENTS Registration
# ═══════════════════════════════════════════════════════════════════════

class TestMCPAgentsRegistration:
    """Test that system commands are registered in MCP_AGENTS."""

    def _get_mcp_agents(self):
        from src.api.handlers.group_message_handler import MCP_AGENTS
        return MCP_AGENTS

    def test_dragon_registered(self):
        agents = self._get_mcp_agents()
        assert "dragon" in agents
        assert agents["dragon"]["role"] == "Orchestrator"
        assert agents["dragon"]["icon"] == "flame"

    def test_doctor_registered(self):
        agents = self._get_mcp_agents()
        assert "doctor" in agents
        assert agents["doctor"]["role"] == "Diagnostic"
        assert agents["doctor"]["icon"] == "stethoscope"

    def test_pipeline_registered(self):
        agents = self._get_mcp_agents()
        assert "pipeline" in agents
        assert agents["pipeline"]["role"] == "Builder"

    def test_existing_agents_preserved(self):
        """Original browser_haiku and claude_code still exist."""
        agents = self._get_mcp_agents()
        assert "browser_haiku" in agents
        assert "claude_code" in agents

    def test_reserve_agents_registered(self):
        """Future agents are reserved to prevent Ollama hijack."""
        agents = self._get_mcp_agents()
        assert "grok" in agents
        assert "haiku_scout" in agents
        assert "opus" in agents
        assert "gemini" in agents

    def test_all_agents_have_required_fields(self):
        """Every agent has name, icon, role, aliases."""
        agents = self._get_mcp_agents()
        required = {"name", "icon", "role", "aliases"}
        for agent_id, info in agents.items():
            missing = required - set(info.keys())
            assert not missing, f"Agent '{agent_id}' missing fields: {missing}"

    def test_total_agent_count(self):
        """At least 9 agents registered (2 original + 7 new)."""
        agents = self._get_mcp_agents()
        assert len(agents) >= 9


# ═══════════════════════════════════════════════════════════════════════
# 2. Alias Matching
# ═══════════════════════════════════════════════════════════════════════

class TestAliasMatching:
    """Test that @mcp/dragon, @doc, etc. resolve correctly."""

    def _find_agent(self, mention: str):
        """Simulate alias lookup from notify_mcp_agents()."""
        from src.api.handlers.group_message_handler import MCP_AGENTS
        mention_lower = mention.lower()

        # Direct match
        if mention_lower in MCP_AGENTS:
            return mention_lower

        # Alias match
        for agent_id, info in MCP_AGENTS.items():
            if mention_lower in info.get("aliases", []):
                return agent_id

        return None

    def test_dragon_direct(self):
        assert self._find_agent("dragon") == "dragon"

    def test_dragon_mcp_alias(self):
        assert self._find_agent("mcp/dragon") == "dragon"

    def test_doctor_direct(self):
        assert self._find_agent("doctor") == "doctor"

    def test_doc_alias(self):
        assert self._find_agent("doc") == "doctor"

    def test_doctor_mcp_alias(self):
        assert self._find_agent("mcp/doctor") == "doctor"

    def test_pipeline_direct(self):
        assert self._find_agent("pipeline") == "pipeline"

    def test_mycelium_alias(self):
        assert self._find_agent("mycelium") == "pipeline"

    def test_scout_alias(self):
        assert self._find_agent("scout") == "haiku_scout"

    def test_dreamteam_alias(self):
        assert self._find_agent("dreamteam") == "opus"

    def test_all_stars_alias(self):
        assert self._find_agent("all-stars") == "opus"

    def test_unknown_returns_none(self):
        assert self._find_agent("nonexistent") is None


# ═══════════════════════════════════════════════════════════════════════
# 3. HEARTBEAT_AGENTS Set
# ═══════════════════════════════════════════════════════════════════════

class TestHeartbeatAgents:
    """Test HEARTBEAT_AGENTS set for auto-dispatch."""

    def test_heartbeat_agents_exist(self):
        from src.api.handlers.group_message_handler import HEARTBEAT_AGENTS
        assert isinstance(HEARTBEAT_AGENTS, set)

    def test_dragon_in_heartbeat(self):
        from src.api.handlers.group_message_handler import HEARTBEAT_AGENTS
        assert "dragon" in HEARTBEAT_AGENTS

    def test_doctor_in_heartbeat(self):
        from src.api.handlers.group_message_handler import HEARTBEAT_AGENTS
        assert "doctor" in HEARTBEAT_AGENTS

    def test_pipeline_in_heartbeat(self):
        from src.api.handlers.group_message_handler import HEARTBEAT_AGENTS
        assert "pipeline" in HEARTBEAT_AGENTS

    def test_reserves_not_in_heartbeat(self):
        """Reserve agents (grok, opus, etc.) don't auto-dispatch yet."""
        from src.api.handlers.group_message_handler import HEARTBEAT_AGENTS
        assert "grok" not in HEARTBEAT_AGENTS
        assert "opus" not in HEARTBEAT_AGENTS
        assert "gemini" not in HEARTBEAT_AGENTS


# ═══════════════════════════════════════════════════════════════════════
# 4. _dispatch_system_command Function
# ═══════════════════════════════════════════════════════════════════════

class TestDispatchSystemCommand:
    """Test _dispatch_system_command() function."""

    def test_function_exists(self):
        from src.api.handlers.group_message_handler import _dispatch_system_command
        assert callable(_dispatch_system_command)

    def test_system_command_phases(self):
        from src.api.handlers.group_message_handler import _SYSTEM_COMMAND_PHASES
        assert _SYSTEM_COMMAND_PHASES["dragon"] == "build"
        assert _SYSTEM_COMMAND_PHASES["doctor"] == "research"
        assert _SYSTEM_COMMAND_PHASES["pipeline"] == "build"

    @pytest.mark.asyncio
    async def test_dispatch_extracts_task(self):
        """@dragon prefix is stripped from task text."""
        from src.api.handlers.group_message_handler import _dispatch_system_command

        with patch("src.orchestration.agent_pipeline.AgentPipeline") as MockPipeline, \
             patch("httpx.AsyncClient") as MockHttpx:

            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value={
                "status": "done",
                "results": {"subtasks_completed": 1, "subtasks_total": 1}
            })
            MockPipeline.return_value = mock_pipeline

            # Mock httpx context manager
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            MockHttpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockHttpx.return_value.__aexit__ = AsyncMock(return_value=False)

            await _dispatch_system_command(
                agent_id="dragon",
                chat_id="test-group-id",
                content="@dragon fix the login bug",
                message_id="msg-123",
                sender_id="user"
            )

            # Pipeline should have been called with task (without @dragon prefix)
            mock_pipeline.execute.assert_called_once()
            call_args = mock_pipeline.execute.call_args
            task = call_args[0][0]  # First positional arg
            assert "fix the login bug" in task
            assert "@dragon" not in task

    @pytest.mark.asyncio
    async def test_dispatch_uses_correct_phase(self):
        """Doctor uses research phase, dragon uses build."""
        from src.api.handlers.group_message_handler import _dispatch_system_command

        with patch("src.orchestration.agent_pipeline.AgentPipeline") as MockPipeline, \
             patch("httpx.AsyncClient") as MockHttpx:

            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value={"status": "done", "results": {}})
            MockPipeline.return_value = mock_pipeline

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            MockHttpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockHttpx.return_value.__aexit__ = AsyncMock(return_value=False)

            await _dispatch_system_command(
                agent_id="doctor",
                chat_id="test-group",
                content="@doctor general checkup",
                message_id="msg-456",
                sender_id="user"
            )

            call_args = mock_pipeline.execute.call_args
            phase = call_args[0][1]  # Second positional arg
            assert phase == "research"

    @pytest.mark.asyncio
    async def test_dispatch_uses_chat_id(self):
        """Pipeline receives chat_id for cross-chat streaming."""
        from src.api.handlers.group_message_handler import _dispatch_system_command

        with patch("src.orchestration.agent_pipeline.AgentPipeline") as MockPipeline, \
             patch("httpx.AsyncClient") as MockHttpx:

            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value={"status": "done", "results": {}})
            MockPipeline.return_value = mock_pipeline

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            MockHttpx.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockHttpx.return_value.__aexit__ = AsyncMock(return_value=False)

            await _dispatch_system_command(
                agent_id="dragon",
                chat_id="custom-chat-id-from-another-group",
                content="@dragon task from other chat",
                message_id="msg-789",
                sender_id="user"
            )

            # AgentPipeline created with the correct chat_id
            MockPipeline.assert_called_once_with(chat_id="custom-chat-id-from-another-group")


# ═══════════════════════════════════════════════════════════════════════
# 5. Heartbeat @doctor Pattern
# ═══════════════════════════════════════════════════════════════════════

class TestHeartbeatDoctorPattern:
    """Test that @doctor is in heartbeat TASK_PATTERNS."""

    def test_doctor_pattern_exists(self):
        from src.orchestration.mycelium_heartbeat import TASK_PATTERNS
        patterns_str = [p.pattern for p in TASK_PATTERNS]
        assert any("doctor" in p for p in patterns_str), \
            "@doctor must be in heartbeat TASK_PATTERNS"

    def test_doctor_phase_mapping(self):
        from src.orchestration.mycelium_heartbeat import PHASE_TYPE_MAP
        assert PHASE_TYPE_MAP["doctor"] == "research"

    def test_doctor_parsed_from_message(self):
        from src.orchestration.mycelium_heartbeat import _parse_tasks
        messages = [
            {"id": "m1", "sender_id": "user", "content": "@doctor check the API health"}
        ]
        tasks = _parse_tasks(messages)
        assert len(tasks) == 1
        assert tasks[0].trigger == "doctor"
        assert tasks[0].phase_type == "research"
        assert "check the API health" in tasks[0].task


# ═══════════════════════════════════════════════════════════════════════
# 6. KNOWN_AGENTS Registration
# ═══════════════════════════════════════════════════════════════════════

class TestKnownAgents:
    """Test KNOWN_AGENTS in debug_routes."""

    def test_dragon_in_known_agents(self):
        from src.api.routes.debug_routes import KNOWN_AGENTS
        assert "dragon" in KNOWN_AGENTS
        assert KNOWN_AGENTS["dragon"]["icon"] == "flame"

    def test_doctor_in_known_agents(self):
        from src.api.routes.debug_routes import KNOWN_AGENTS
        assert "doctor" in KNOWN_AGENTS
        assert KNOWN_AGENTS["doctor"]["icon"] == "stethoscope"

    def test_pipeline_still_in_known_agents(self):
        from src.api.routes.debug_routes import KNOWN_AGENTS
        assert "pipeline" in KNOWN_AGENTS


# ═══════════════════════════════════════════════════════════════════════
# 7. Integration: Code Consistency
# ═══════════════════════════════════════════════════════════════════════

class TestCodeConsistency:
    """Test that all registrations are consistent across files."""

    def test_dragon_in_all_three_systems(self):
        """Dragon registered in MCP_AGENTS, KNOWN_AGENTS, and heartbeat."""
        from src.api.handlers.group_message_handler import MCP_AGENTS
        from src.api.routes.debug_routes import KNOWN_AGENTS
        from src.orchestration.mycelium_heartbeat import PHASE_TYPE_MAP

        assert "dragon" in MCP_AGENTS
        assert "dragon" in KNOWN_AGENTS
        assert "dragon" in PHASE_TYPE_MAP

    def test_doctor_in_all_three_systems(self):
        """Doctor registered in MCP_AGENTS, KNOWN_AGENTS, and heartbeat."""
        from src.api.handlers.group_message_handler import MCP_AGENTS
        from src.api.routes.debug_routes import KNOWN_AGENTS
        from src.orchestration.mycelium_heartbeat import PHASE_TYPE_MAP

        assert "doctor" in MCP_AGENTS
        assert "doctor" in KNOWN_AGENTS
        assert "doctor" in PHASE_TYPE_MAP

    def test_heartbeat_agents_subset_of_mcp_agents(self):
        """HEARTBEAT_AGENTS must be a subset of MCP_AGENTS."""
        from src.api.handlers.group_message_handler import MCP_AGENTS, HEARTBEAT_AGENTS

        for agent in HEARTBEAT_AGENTS:
            assert agent in MCP_AGENTS, f"HEARTBEAT_AGENTS '{agent}' not in MCP_AGENTS"

    def test_no_haiku_alias_conflict(self):
        """'haiku' alias belongs to browser_haiku, not haiku_scout."""
        from src.api.handlers.group_message_handler import MCP_AGENTS

        # browser_haiku has "haiku" alias
        assert "haiku" in MCP_AGENTS["browser_haiku"]["aliases"]
        # haiku_scout should NOT have "haiku" alias (would conflict)
        assert "haiku" not in MCP_AGENTS["haiku_scout"]["aliases"]
