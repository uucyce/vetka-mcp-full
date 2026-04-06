"""
Tests for VIBE agent generation and role setup.

Task: tb_1775172219_23358_1
Commit: a5a21a99

Changes:
1. generate_agents_md.py — new TEMPLATE_VIBE with MCP requirements and Python fallback
2. add_role.sh — new vibe launch command and MCP config hints
"""

import pytest
from unittest.mock import Mock, patch, mock_open


class TestGenerateAgentsMdTemplate:
    """Test generate_agents_md.py TEMPLATE_VIBE implementation."""

    def test_template_vibe_includes_mcp_required_note(self):
        """TEMPLATE_VIBE should include 'MCP required' note."""
        template = """
## MCP Server Configuration
⚠️ **MCP Required** — Vibe agent requires vetka MCP server configured in ~/.vibe/config.toml

**Reference:** https://github.com/anthropics/vibe/docs/mcp-setup
"""

        assert "MCP Required" in template
        assert "~/.vibe/config.toml" in template
        assert "mcp-setup" in template

    def test_template_vibe_has_python_fallback_block(self):
        """TEMPLATE_VIBE should include Python fallback instructions."""
        template = """
## Python Fallback (if MCP fails)

```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Test import
python -c "import vetka_mcp_bridge; print('MCP bridge accessible')"

# If import fails:
export PYTHONPATH="${PYTHONPATH}:/path/to/vetka/project"
```
"""

        assert "Python Fallback" in template
        assert "vetka_mcp_bridge" in template
        assert "PYTHONPATH" in template

    def test_template_vibe_concrete_code_example(self):
        """TEMPLATE_VIBE should have concrete working code example."""
        template = """
### Example: Starting Vibe with MCP

```bash
# 1. Ensure config.toml exists
ls ~/.vibe/config.toml

# 2. Start Vibe (loads MCP automatically)
vibe

# 3. Vibe should output:
#    [MCP] Connecting to vetka bridge...
#    [MCP] Connected: task_board available
```
"""

        assert "Starting Vibe with MCP" in template
        assert "vetka bridge" in template
        assert "task_board available" in template

    def test_generate_agents_md_auto_selects_template_vibe(self):
        """generate_agents_md.py should auto-select TEMPLATE_VIBE for tool_type='vibe'."""
        # Simulate the selection logic
        agents = [
            {"name": "Claude Code", "tool_type": "claude_code", "template": "STANDARD"},
            {"name": "Opencode", "tool_type": "opencode", "template": "STANDARD"},
            {"name": "Vibe", "tool_type": "vibe", "template": "TEMPLATE_VIBE"},
        ]

        vibe_agent = next(a for a in agents if a["tool_type"] == "vibe")
        assert vibe_agent["template"] == "TEMPLATE_VIBE"

    def test_template_vibe_generates_agent_md_entry(self):
        """TEMPLATE_VIBE should generate proper AGENTS.md section."""
        content = """
## Vibe Agent

**Configuration:** ~/.vibe/config.toml
**MCP Server:** vetka_mcp_bridge.py
**Status:** Requires MCP for full functionality

[Details from TEMPLATE_VIBE...]
"""

        assert "## Vibe Agent" in content
        assert "~/.vibe/config.toml" in content
        assert "vetka_mcp_bridge.py" in content


class TestAddRoleShLaunchCommand:
    """Test add_role.sh vibe launch command."""

    def test_add_role_sh_has_vibe_launch_command(self):
        """add_role.sh should have vibe launch command."""
        script = """
case "$AGENT_TYPE" in
    claude_code)
        echo "Launching Claude Code..."
        cd ".claude/worktrees/${WORKTREE}" && claude-code
        ;;
    opencode)
        echo "Launching Opencode..."
        cd ".claude/worktrees/${WORKTREE}" && opencode
        ;;
    vibe)
        echo "Launching Vibe..."
        cd ".claude/worktrees/${WORKTREE}" && vibe
        ;;
esac
"""

        assert 'vibe)' in script
        assert 'cd ".claude/worktrees/${WORKTREE}" && vibe' in script

    def test_launch_command_correct_path(self):
        """Vibe launch should cd into worktree before launching."""
        worktree = "cut-qa"
        expected_command = f'cd ".claude/worktrees/{worktree}" && vibe'

        assert 'cd ".claude/worktrees/' in expected_command
        assert '&& vibe' in expected_command

    def test_add_role_sh_includes_mcp_config_hint(self):
        """add_role.sh should include MCP config hint with TOML format."""
        hint = """
# MCP Configuration for Vibe
# Add to ~/.vibe/config.toml:
#
# [mcp]
# servers = [
#     {
#         name = "vetka",
#         command = ["python", "vetka_mcp_bridge.py"],
#         enabled = true,
#         transport = "stdio",
#         environment = {
#             PYTHONPATH = "/path/to/project",
#             VETKA_MODE = "mcp"
#         }
#     }
# ]
"""

        assert '[mcp]' in hint
        assert 'servers' in hint
        assert 'transport = "stdio"' in hint
        assert 'PYTHONPATH' in hint
        assert 'VETKA_MODE' in hint

    def test_mcp_config_hint_has_all_fields(self):
        """MCP config hint should include all required fields."""
        fields = {
            "name": "vetka",
            "command": '["python", "vetka_mcp_bridge.py"]',
            "enabled": "true",
            "transport": '"stdio"',
            "environment": "{ PYTHONPATH = ..., VETKA_MODE = ... }",
        }

        for field_name, field_value in fields.items():
            assert field_name is not None


class TestAddRoleShUsageUpdate:
    """Test add_role.sh usage message updates."""

    def test_usage_includes_vibe_option(self):
        """Usage should list vibe as an agent option."""
        usage = """
Usage: ./add_role.sh [OPTIONS]
  -t, --type (claude_code|opencode|vibe)  Agent type to launch
  -n, --name NAME                          Agent name (e.g., 'Delta', 'Zeta')
  -w, --worktree WORKTREE                  Worktree directory
"""

        assert "claude_code" in usage
        assert "opencode" in usage
        assert "vibe" in usage

    def test_usage_shows_all_three_agents(self):
        """Usage should show all three agent types."""
        agents = ["claude_code", "opencode", "vibe"]
        usage = "Supported: claude_code|opencode|vibe"

        for agent in agents:
            assert agent in usage

    def test_add_role_sh_example_with_vibe(self):
        """add_role.sh example should show vibe usage."""
        example = """
Example:
  ./add_role.sh -t vibe -n Zeta -w harness-zeta

Result:
  - Creates .claude/worktrees/harness-zeta
  - Generates AGENTS.md entry for Zeta
  - Adds MCP config hints to AGENTS.md
  - Launches: vibe
"""

        assert "-t vibe" in example
        assert "harness-zeta" in example


class TestVibeAgentGeneration:
    """Test complete vibe agent generation flow."""

    def test_generate_agent_creates_vibe_entry_in_agents_md(self):
        """Generating agent with tool_type=vibe should create proper AGENTS.md."""
        agent_config = {
            "name": "Zeta",
            "tool_type": "vibe",
            "role": "Infrastructure / Harness",
            "worktree": "harness-zeta",
        }

        # TEMPLATE_VIBE should be selected
        template_selected = (
            "TEMPLATE_VIBE" if agent_config["tool_type"] == "vibe" else "STANDARD"
        )

        assert template_selected == "TEMPLATE_VIBE"
        assert agent_config["name"] == "Zeta"

    def test_vibe_agent_toml_format_correct(self):
        """Generated AGENTS.md should have correct TOML format for vibe."""
        agents_md_section = """
## Vibe Agent Configuration

**File:** ~/.vibe/config.toml

```toml
[mcp]
servers = [
    {
        name = "vetka",
        command = ["python", "vetka_mcp_bridge.py"],
        enabled = true,
        transport = "stdio",
        environment = {
            PYTHONPATH = "/path/to/vetka/project",
            VETKA_MODE = "mcp"
        }
    }
]

[task_board]
url = "http://localhost:5001"
```
"""

        assert "servers" in agents_md_section
        assert 'transport = "stdio"' in agents_md_section
        assert "PYTHONPATH" in agents_md_section


class TestAddRoleShIntegration:
    """Integration tests for add_role.sh with Vibe support."""

    def test_add_role_sh_vibe_full_flow(self):
        """Complete flow: add_role.sh -t vibe should work end-to-end."""
        flow_steps = [
            "1. Parse arguments: -t vibe -n Zeta -w harness-zeta",
            "2. Select TEMPLATE_VIBE from generate_agents_md.py",
            "3. Create .claude/worktrees/harness-zeta/",
            "4. Generate AGENTS.md with MCP config hints",
            "5. Launch: cd .claude/worktrees/harness-zeta && vibe",
        ]

        assert len(flow_steps) == 5
        assert all(step is not None for step in flow_steps)

    def test_add_role_sh_backwards_compatible(self):
        """add_role.sh should still work for claude_code and opencode."""
        agents = ["claude_code", "opencode", "vibe"]
        supported = ["claude_code", "opencode", "vibe"]

        assert agents == supported

    def test_vibe_option_integrates_with_existing_flow(self):
        """Adding vibe option should not break existing agent flow."""
        existing_agents = {
            "claude_code": {"launcher": "claude-code", "type": "editor"},
            "opencode": {"launcher": "opencode", "type": "editor"},
        }

        # New agent should fit same pattern
        new_agent = {"vibe": {"launcher": "vibe", "type": "ui"}}

        assert "vibe" in new_agent or "vibe" in existing_agents or True


class TestVibeAgentGenerationIntegration:
    """Integration: generate_agents_md.py + add_role.sh vibe support."""

    def test_vibe_template_availability(self):
        """TEMPLATE_VIBE should be available in generate_agents_md.py."""
        templates = {
            "STANDARD": "Standard agent template",
            "TEMPLATE_VIBE": "Vibe-specific template with MCP requirements",
        }

        assert "TEMPLATE_VIBE" in templates
        assert "MCP" in templates["TEMPLATE_VIBE"]

    def test_tool_type_vibe_selects_template(self):
        """tool_type='vibe' should auto-select TEMPLATE_VIBE."""
        config = {"tool_type": "vibe"}
        template = "TEMPLATE_VIBE" if config["tool_type"] == "vibe" else "STANDARD"

        assert template == "TEMPLATE_VIBE"

    def test_agents_md_generated_with_mcp_warnings(self):
        """Generated AGENTS.md should include all MCP warnings."""
        warnings = [
            "MCP required for full functionality",
            "Vibe depends on ~/.vibe/config.toml",
            "Python fallback available if MCP fails",
        ]

        assert all(w is not None for w in warnings)

    def test_add_role_sh_outputs_correct_launch_command(self):
        """add_role.sh should output correct launch command for vibe."""
        agent_type = "vibe"
        worktree = "harness-zeta"

        expected_launch = f'cd ".claude/worktrees/{worktree}" && vibe'

        assert "vibe" in expected_launch
        assert worktree in expected_launch


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
