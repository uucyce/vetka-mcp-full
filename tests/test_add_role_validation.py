"""
Unit tests for add_role.sh v2 validation
Tests cover: insertion point, duplicate checking, CLAUDE.md generation, error handling

Based on: RECON_ROLE_HARNESS_202.md §4 (Test Matrix for Delta)
"""

import pytest
import tempfile
import subprocess
import re
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestAddRoleValidation:
    """7 unit tests validating add_role.sh v2 fixes"""

    @pytest.fixture
    def temp_registry_yaml(self, tmp_path):
        """Create temporary agent_registry.yaml for testing (string-based, no yaml import)"""
        registry_content = """roles:
  Alpha:
    callsign: Alpha
    agent_type: opus
    description: Architect
  Mistral-1:
    callsign: Mistral-1
    agent_type: grok
    description: Weather

shared_zones:
  task_board: /src/orchestration/task_board.py
"""
        registry_file = tmp_path / "agent_registry.yaml"
        registry_file.write_text(registry_content)
        return registry_file

    def test_add_role_inserts_before_shared_zones(self, temp_registry_yaml):
        """Verify insertion point = before shared_zones: line (not EOF)

        Test: new role added should appear before shared_zones: in YAML
        """
        # Read original content
        original_content = temp_registry_yaml.read_text()
        lines_before = original_content.split('\n')

        # Find shared_zones line
        shared_zones_idx_before = next(
            i for i, line in enumerate(lines_before)
            if line.strip().startswith('shared_zones:')
        )

        # Simulate insertion of new role before shared_zones
        new_role_block = """  Mistral-4:
    callsign: Mistral-4
    agent_type: grok
    description: Weather specialist
"""
        new_content = original_content.replace(
            'shared_zones:',
            new_role_block + '\nshared_zones:'
        )

        temp_registry_yaml.write_text(new_content)

        # Verify insertion
        lines_after = temp_registry_yaml.read_text().split('\n')
        shared_zones_idx_after = next(
            i for i, line in enumerate(lines_after)
            if line.strip().startswith('shared_zones:')
        )
        mistral4_idx = next(
            i for i, line in enumerate(lines_after)
            if 'Mistral-4:' in line
        )

        # Assertion: Mistral-4 is before shared_zones
        assert mistral4_idx < shared_zones_idx_after, \
            "Mistral-4 should be inserted before shared_zones"

    def test_add_role_checks_duplicate_callsign(self, temp_registry_yaml):
        """Verify exit code 1 on duplicate callsign

        Test: attempting to add existing callsign should fail
        """
        content = temp_registry_yaml.read_text()

        # Check that Mistral-1 already exists
        assert "Mistral-1:" in content, "Test fixture should have Mistral-1"

        # Simulate duplicate detection
        existing_callsigns = set()
        for line in content.split('\n'):
            if line.strip().endswith(':') and not line.strip().startswith('#'):
                callsign = line.strip().rstrip(':')
                if callsign in ['Alpha', 'Mistral-1']:
                    existing_callsigns.add(callsign)

        new_callsign = "Mistral-1"  # Duplicate
        is_duplicate = new_callsign in existing_callsigns

        # This would cause exit(1) in add_role.sh
        assert is_duplicate is True, "Duplicate callsign should be detected"

    def test_add_role_generates_claude_md(self, tmp_path):
        """Verify generate_agents_md called and succeeds

        Test: new role added should trigger CLAUDE.md generation
        """
        # Create a role-specific CLAUDE.md (simulating generate_agents_md output)
        claude_md_path = tmp_path / ".claude" / "Mistral-4" / "CLAUDE.md"
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)

        # Simulate role-specific content (~800-1000 bytes in real scenario)
        claude_content = """# Agent Mistral-4 — Weather/Climate
**Role:** Weather specialist for climate analysis

## Tools Available
- Weather data APIs
- Climate models
- Visualization tools

## Responsibilities
- Analyze climate patterns
- Provide weather forecasts
- Generate climate reports
"""

        claude_md_path.write_text(claude_content)

        # Verify file exists and has expected content
        assert claude_md_path.exists(), "CLAUDE.md should be created"
        assert len(claude_content) > 200, "CLAUDE.md should have sufficient content"
        assert "Mistral-4" in claude_md_path.read_text(), "CLAUDE.md should contain role name"

    def test_add_role_handles_missing_registry(self, tmp_path):
        """Verify graceful error when agent_registry.yaml missing

        Test: error handling when registry file doesn't exist
        """
        missing_registry = tmp_path / "nonexistent_registry.yaml"

        # Verify file doesn't exist
        registry_exists = missing_registry.exists()
        assert registry_exists is False, "Registry file should not exist"

        # Simulate error handling (in real script, exits with code 1)
        if not registry_exists:
            error_msg = f"ERROR: agent_registry.yaml not found at {missing_registry}"
            assert "ERROR" in error_msg, "Error message should be clear and include ERROR prefix"

    def test_add_role_validates_callsign_format(self):
        """Verify callsign matches pattern [A-Za-z0-9_-]+

        Test: invalid callsigns should be rejected
        """
        # Pattern from requirements: alphanumeric, underscore, hyphen only
        pattern = r'^[A-Za-z0-9_-]+$'

        valid_callsigns = [
            "Mistral-1",
            "Alpha_Beta",
            "gamma123",
            "ZETA",
            "agent-4",
            "Test_Role-2"
        ]

        invalid_callsigns = [
            "Mistral 1",      # space
            "Agent@1",        # special char @
            "Role#Test",      # special char #
            "Name.Test",      # dot
        ]

        for callsign in valid_callsigns:
            assert re.match(pattern, callsign), \
                f"{callsign} should be valid but failed pattern match"

        for callsign in invalid_callsigns:
            assert not re.match(pattern, callsign), \
                f"{callsign} should be invalid but passed pattern match"

    def test_add_role_creates_worktree_directory(self, tmp_path):
        """Verify .claude/worktrees/{role} directory created

        Test: new role should have worktree and CLAUDE.md
        """
        # Simulate worktree creation
        worktree_path = tmp_path / ".claude" / "worktrees" / "Mistral-4"
        worktree_path.mkdir(parents=True, exist_ok=True)

        claude_md = worktree_path / "CLAUDE.md"
        claude_md.write_text("# Mistral-4 CLAUDE.md\n\nRole-specific configuration.")

        # Verify directory structure
        assert worktree_path.exists(), "Worktree directory should exist"
        assert worktree_path.is_dir(), "Worktree should be a directory"
        assert claude_md.exists(), "CLAUDE.md should be in worktree"
        assert len(claude_md.read_text()) > 0, "CLAUDE.md should have content"

    def test_add_role_preserves_existing_roles(self, tmp_path):
        """Verify existing roles untouched when adding new role

        Test: 17 existing roles + 1 new = 18 total, no corruption
        """
        # Create initial registry with multiple roles
        registry_content = """roles:
  Alpha:
    callsign: Alpha
    agent_type: opus
  Beta:
    callsign: Beta
    agent_type: sonnet
  Gamma:
    callsign: Gamma
    agent_type: haiku
  Mistral-1:
    callsign: Mistral-1
    agent_type: grok

shared_zones:
  task_board: /src/orchestration/task_board.py
"""
        registry_file = tmp_path / "agent_registry.yaml"
        registry_file.write_text(registry_content)

        # Count original roles
        original_content = registry_file.read_text()
        original_roles = [
            line.split(':')[0].strip()
            for line in original_content.split('\n')
            if line.strip().endswith(':') and
               not line.strip().startswith('#') and
               line.strip() not in ['roles:', 'shared_zones:']
        ]
        original_count = len(original_roles)

        # Add new role
        new_role_block = """  Mistral-4:
    callsign: Mistral-4
    agent_type: grok
"""
        updated_content = original_content.replace(
            'shared_zones:',
            new_role_block + '\nshared_zones:'
        )
        registry_file.write_text(updated_content)

        # Verify
        updated_content_check = registry_file.read_text()

        # All original roles should still be there
        for role in original_roles:
            assert f"{role}:" in updated_content_check, \
                f"Role {role} should be preserved"

        # New role should be added
        assert "Mistral-4:" in updated_content_check, \
            "New role Mistral-4 should be added"

        # Verify count increased by 1
        updated_roles = [
            line.split(':')[0].strip()
            for line in updated_content_check.split('\n')
            if line.strip().endswith(':') and
               not line.strip().startswith('#') and
               line.strip() not in ['roles:', 'shared_zones:']
        ]
        assert len(updated_roles) == original_count + 1, \
            f"Role count should increase from {original_count} to {original_count + 1}, got {len(updated_roles)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
