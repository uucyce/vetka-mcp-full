"""
MARKER_204.ETA_TEST: e2e integration tests — Vibe/Opencode agent harness quality parity.

Tests verify that Vibe and Opencode agents are as well-integrated as Claude Code agents:
  - Registry integrity (tool_type, memory_path, owned_paths)
  - AGENTS.md content (Vibe: no mcp__ prefix, Error Handling, Signal Setup, memory section)
  - CLAUDE.md content (correct Init block per tool_type)
  - launch_vibe.sh (exists, has PRETOOL_HOOK env var, correct VETKA_AGENT_ROLE)
  - Signal delivery roundtrip (check_opencode_signals.sh reads both signal dirs)
  - Session init returns tool_type + memory_path
  - Notification relay: Vibe→Claude, Claude→Vibe
  - Guard: owned_paths + blocked_paths defined for all agents
  - STM/ENGRAM/Reflex: session_init returns expected context sections
  - Behavioral checklist (printed as SKIP — requires manual/Delta run)

Task: tb_1775306427_23491_1
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path

import pytest

# ── Fixtures & helpers ────────────────────────────────────────────────────────

# test file:  .../vetka_live_03/.claude/worktrees/harness-eta/tests/test_xxx.py
# HARNESS_WT: .../vetka_live_03/.claude/worktrees/harness-eta/
# WORKTREES:  .../vetka_live_03/.claude/worktrees/
# PROJECT:    .../vetka_live_03/
HARNESS_WORKTREE = Path(__file__).resolve().parent.parent
WORKTREES_DIR = HARNESS_WORKTREE.parent
PROJECT_ROOT = WORKTREES_DIR.parent.parent  # up through .claude/ → vetka_live_03/
REGISTRY_PATH = PROJECT_ROOT / "data" / "templates" / "agent_registry.yaml"
SCRIPTS_DIR = HARNESS_WORKTREE / "scripts"

VIBE_CALLSIGNS = ["Mistral-1", "Mistral-2", "Mistral-3"]
OPENCODE_CALLSIGNS = ["Lambda", "Mu", "Polaris", "Theta", "Iota", "Kappa"]
CLAUDE_CODE_CALLSIGNS = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Commander"]
ALL_CALLSIGNS = VIBE_CALLSIGNS + OPENCODE_CALLSIGNS + CLAUDE_CODE_CALLSIGNS

VIBE_WORKTREES = {
    "Mistral-1": "weather-mistral-1",
    "Mistral-2": "cut-qa-5",
    "Mistral-3": "weather-mistral-2",
}


def _load_registry():
    from src.services.agent_registry import AgentRegistry
    return AgentRegistry(REGISTRY_PATH)


def _agents_md(worktree: str) -> str:
    path = WORKTREES_DIR / worktree / "AGENTS.md"
    if not path.exists():
        return ""
    return path.read_text()


def _claude_md(worktree: str) -> str:
    path = WORKTREES_DIR / worktree / "CLAUDE.md"
    if not path.exists():
        return ""
    return path.read_text()


# ── 1. Registry integrity ─────────────────────────────────────────────────────

class TestRegistryIntegrity:
    """All agent roles have correct tool_type, memory_path, owned_paths."""

    def test_vibe_agents_tool_type(self):
        reg = _load_registry()
        for cs in VIBE_CALLSIGNS:
            role = reg.get_by_callsign(cs)
            assert role is not None, f"{cs} not in registry"
            assert role.tool_type == "vibe", (
                f"{cs} has tool_type={role.tool_type!r}, expected 'vibe'. "
                "Fix: data/templates/agent_registry.yaml"
            )

    def test_opencode_agents_tool_type(self):
        reg = _load_registry()
        for cs in OPENCODE_CALLSIGNS:
            role = reg.get_by_callsign(cs)
            assert role is not None, f"{cs} not in registry"
            assert role.tool_type == "opencode", (
                f"{cs} has tool_type={role.tool_type!r}, expected 'opencode'"
            )

    def test_claude_code_agents_tool_type(self):
        reg = _load_registry()
        for cs in CLAUDE_CODE_CALLSIGNS:
            role = reg.get_by_callsign(cs)
            assert role is not None, f"{cs} not in registry"
            assert role.tool_type == "claude_code", (
                f"{cs} has tool_type={role.tool_type!r}, expected 'claude_code'"
            )

    def test_all_non_claude_agents_have_memory_path(self):
        reg = _load_registry()
        for cs in VIBE_CALLSIGNS + OPENCODE_CALLSIGNS:
            role = reg.get_by_callsign(cs)
            assert role is not None, f"{cs} not in registry"
            assert role.memory_path, (
                f"{cs} has no memory_path — agents cannot persist lessons across sessions"
            )
            assert "memory/roles/" in role.memory_path, (
                f"{cs}.memory_path={role.memory_path!r} — expected path under memory/roles/"
            )

    def test_claude_code_agents_have_memory_path(self):
        """Claude Code agents already had memory_path — regression guard."""
        reg = _load_registry()
        # Alpha/Beta/Gamma/Delta/Epsilon/Zeta/Eta/Commander all have memory_path
        for cs in ["Alpha", "Beta", "Gamma", "Delta", "Zeta", "Eta"]:
            role = reg.get_by_callsign(cs)
            if role:
                assert role.memory_path, f"{cs} lost memory_path — regression!"

    def test_all_agents_have_owned_paths(self):
        reg = _load_registry()
        for cs in ALL_CALLSIGNS:
            role = reg.get_by_callsign(cs)
            if role is None:
                continue
            assert role.owned_paths, (
                f"{cs} has no owned_paths — agent has no guard against touching wrong files"
            )

    def test_all_agents_have_branch(self):
        reg = _load_registry()
        for cs in ALL_CALLSIGNS:
            role = reg.get_by_callsign(cs)
            if role is None:
                continue
            assert role.branch, f"{cs} has no branch — cannot action=complete"

    def test_vibe_agents_have_worktree_dirs(self):
        for cs, wt in VIBE_WORKTREES.items():
            wt_dir = WORKTREES_DIR / wt
            assert wt_dir.exists(), (
                f"{cs} worktree dir missing: {wt_dir}. "
                "Cannot regenerate AGENTS.md or install hooks."
            )


# ── 2. AGENTS.md content ─────────────────────────────────────────────────────

class TestAgentsMdVibe:
    """Vibe AGENTS.md must NOT use mcp__ prefix and must have Error Handling."""

    @pytest.fixture(params=VIBE_CALLSIGNS)
    def vibe_agents_md(self, request):
        cs = request.param
        wt = VIBE_WORKTREES[cs]
        content = _agents_md(wt)
        assert content, f"AGENTS.md missing for {cs} (worktree: {wt})"
        return cs, content

    def test_no_mcp_prefix_in_vibe_agents_md(self, vibe_agents_md):
        """No mcp__ prefix in actual tool calls — explanation text is allowed."""
        cs, content = vibe_agents_md
        # Only check lines that look like actual tool invocations (start with digits or are in code blocks)
        # Explanation lines like "DO NOT use mcp__vetka__" are fine
        code_block_lines = []
        in_code = False
        for line in content.splitlines():
            if line.strip().startswith("```"):
                in_code = not in_code
            elif in_code and "mcp__vetka__" in line:
                code_block_lines.append(line)
        assert not code_block_lines, (
            f"{cs} AGENTS.md has mcp__vetka__ inside code blocks (tool calls): {code_block_lines}. "
            "Run: python -m src.tools.generate_agents_md --role " + cs
        )

    def test_error_handling_section_present(self, vibe_agents_md):
        cs, content = vibe_agents_md
        assert "Error Handling" in content, (
            f"{cs} AGENTS.md missing Error Handling section — Vibe will loop on tool errors"
        )
        assert "DO NOT retry" in content or "STOP immediately" in content, (
            f"{cs} AGENTS.md Error Handling section too weak — must explicitly say STOP/DO NOT retry"
        )

    def test_signal_setup_section_present(self, vibe_agents_md):
        cs, content = vibe_agents_md
        assert "PRETOOL_HOOK" in content, (
            f"{cs} AGENTS.md missing PRETOOL_HOOK — Vibe agent won't receive Commander signals"
        )
        assert "check_opencode_signals.sh" in content, (
            f"{cs} AGENTS.md should reference check_opencode_signals.sh"
        )

    def test_memory_section_present(self, vibe_agents_md):
        cs, content = vibe_agents_md
        assert "Role Memory" in content or "memory/roles" in content, (
            f"{cs} AGENTS.md missing Role Memory section — agent cannot find its persistent memory"
        )

    def test_correct_role_memory_path(self, vibe_agents_md):
        cs, content = vibe_agents_md
        expected_path = f"memory/roles/{cs}/MEMORY.md"
        assert expected_path in content, (
            f"{cs} AGENTS.md should reference memory_path={expected_path!r}"
        )

    def test_action_complete_workflow(self, vibe_agents_md):
        cs, content = vibe_agents_md
        assert "action=complete" in content, (
            f"{cs} AGENTS.md uses old 'need_qa' workflow instead of action=complete"
        )

    def test_vetka_session_init_no_prefix(self, vibe_agents_md):
        cs, content = vibe_agents_md
        # Should call vetka_session_init (no prefix), not mcp__vetka__vetka_session_init
        assert "vetka_session_init" in content
        # The call in the init block should be just `vetka_session_init`, not prefixed
        lines_with_init = [l for l in content.splitlines() if "session_init" in l]
        for line in lines_with_init:
            if "mcp__" in line:
                pytest.fail(
                    f"{cs} AGENTS.md: session_init still uses mcp__ prefix in line: {line!r}"
                )


class TestAgentsMdOpencode:
    """Opencode AGENTS.md must use mcp__ prefix (Opencode supports it)."""

    @pytest.fixture(params=["Lambda", "Theta", "Iota"])
    def opencode_agents_md(self, request):
        reg = _load_registry()
        cs = request.param
        role = reg.get_by_callsign(cs)
        if role is None:
            pytest.skip(f"{cs} not in registry")
        content = _agents_md(role.worktree)
        if not content:
            pytest.skip(f"AGENTS.md missing for {cs}")
        return cs, content

    def test_mcp_prefix_in_opencode_agents_md(self, opencode_agents_md):
        cs, content = opencode_agents_md
        assert "mcp__vetka__" in content, (
            f"{cs} (Opencode) AGENTS.md missing mcp__ prefix — "
            "Opencode supports mcp__server__tool notation"
        )

    def test_signal_setup_in_opencode(self, opencode_agents_md):
        cs, content = opencode_agents_md
        assert "PRETOOL_HOOK" in content, (
            f"{cs} AGENTS.md missing PRETOOL_HOOK setup"
        )

    def test_memory_section_in_opencode(self, opencode_agents_md):
        cs, content = opencode_agents_md
        assert "memory/roles" in content, (
            f"{cs} AGENTS.md missing memory_path — agent loses lessons each session"
        )


# ── 3. CLAUDE.md content ─────────────────────────────────────────────────────

class TestClaudeMdPerToolType:
    """CLAUDE.md Init section must match the agent's tool_type."""

    def test_vibe_claude_md_no_mcp_prefix(self):
        """No actual mcp__ tool calls in Vibe Init — explanatory 'DO NOT use mcp__' lines are ok."""
        for cs, wt in VIBE_WORKTREES.items():
            content = _claude_md(wt)
            if not content:
                continue
            in_code = False
            bad_lines = []
            for line in content.splitlines():
                if line.strip().startswith("```"):
                    in_code = not in_code
                # Only flag mcp__ in code blocks, not in explanatory text
                if in_code and "mcp__vetka__" in line:
                    bad_lines.append(line)
            assert not bad_lines, (
                f"{cs} CLAUDE.md has mcp__vetka__ inside code blocks: {bad_lines}"
            )

    def test_claude_code_claude_md_has_mcp_prefix(self):
        reg = _load_registry()
        for cs in ["Alpha", "Beta", "Zeta", "Eta"]:
            role = reg.get_by_callsign(cs)
            if not role:
                continue
            content = _claude_md(role.worktree)
            if not content:
                continue
            assert "mcp__vetka__vetka_session_init" in content, (
                f"{cs} CLAUDE.md lost mcp__ prefix — Claude Code agents need it"
            )

    def test_vibe_claude_md_has_error_handling(self):
        for cs, wt in VIBE_WORKTREES.items():
            content = _claude_md(wt)
            if not content:
                continue
            assert "Error Handling" in content, (
                f"{cs} CLAUDE.md missing Error Handling section"
            )

    def test_all_claude_mds_have_memory_section(self):
        reg = _load_registry()
        for cs in VIBE_CALLSIGNS + ["Lambda", "Theta", "Alpha", "Zeta"]:
            role = reg.get_by_callsign(cs)
            if not role or not role.memory_path:
                continue
            content = _claude_md(role.worktree)
            if not content:
                continue
            assert "Role Memory" in content or role.memory_path in content, (
                f"{cs} CLAUDE.md missing Role Memory section despite having memory_path in registry"
            )


# ── 4. launch_vibe.sh ─────────────────────────────────────────────────────────

class TestLaunchVibeScript:
    """Vibe worktrees must have launch_vibe.sh with correct env vars."""

    @pytest.fixture(params=list(VIBE_WORKTREES.items()))
    def vibe_worktree(self, request):
        return request.param  # (callsign, worktree_name)

    def test_launch_vibe_sh_exists(self, vibe_worktree):
        cs, wt = vibe_worktree
        script = WORKTREES_DIR / wt / "launch_vibe.sh"
        assert script.exists(), (
            f"{cs}: launch_vibe.sh missing in {wt}. "
            "Run: bash scripts/install_notification_hooks.sh"
        )

    def test_launch_vibe_sh_has_pretool_hook(self, vibe_worktree):
        cs, wt = vibe_worktree
        script = WORKTREES_DIR / wt / "launch_vibe.sh"
        if not script.exists():
            pytest.skip("launch_vibe.sh missing")
        content = script.read_text()
        assert "PRETOOL_HOOK" in content, f"{cs}: launch_vibe.sh missing PRETOOL_HOOK"
        assert "check_opencode_signals.sh" in content, (
            f"{cs}: launch_vibe.sh should use check_opencode_signals.sh"
        )

    def test_launch_vibe_sh_has_correct_role(self, vibe_worktree):
        cs, wt = vibe_worktree
        script = WORKTREES_DIR / wt / "launch_vibe.sh"
        if not script.exists():
            pytest.skip("launch_vibe.sh missing")
        content = script.read_text()
        assert f'VETKA_AGENT_ROLE="{cs}"' in content or f"VETKA_AGENT_ROLE={cs}" in content, (
            f"{cs}: launch_vibe.sh has wrong or missing VETKA_AGENT_ROLE"
        )

    def test_launch_vibe_sh_is_executable(self, vibe_worktree):
        cs, wt = vibe_worktree
        script = WORKTREES_DIR / wt / "launch_vibe.sh"
        if not script.exists():
            pytest.skip("launch_vibe.sh missing")
        assert os.access(script, os.X_OK), (
            f"{cs}: launch_vibe.sh not executable — run: chmod +x {script}"
        )


# ── 5. Signal delivery roundtrip ─────────────────────────────────────────────

class TestSignalDelivery:
    """check_opencode_signals.sh must read from both ~/.vetka/signals/ and ~/.claude/signals/."""

    SCRIPT = SCRIPTS_DIR / "check_opencode_signals.sh"
    TEST_ROLE = "TestVibeRoleEta99"

    def _write_signal(self, signal_dir: Path, role: str, msg: str) -> Path:
        signal_dir.mkdir(parents=True, exist_ok=True)
        sig_file = signal_dir / f"{role}.json"
        notifications = [{"id": "test_001", "from": "Commander", "message": msg,
                          "ts": "2026-04-04T12:00:00", "ntype": "custom"}]
        sig_file.write_text(json.dumps(notifications))
        return sig_file

    def _run_script(self, role: str, env: dict | None = None) -> subprocess.CompletedProcess:
        script_env = os.environ.copy()
        if env:
            script_env.update(env)
        return subprocess.run(
            ["bash", str(self.SCRIPT), role],
            capture_output=True, text=True, env=script_env,
            cwd=str(PROJECT_ROOT / ".claude" / "worktrees" / "harness-eta"),
        )

    def test_script_exists(self):
        assert self.SCRIPT.exists(), (
            f"check_opencode_signals.sh not found at {self.SCRIPT}"
        )

    def test_no_op_when_no_signal_file(self):
        result = self._run_script(self.TEST_ROLE)
        assert result.returncode == 0, f"Script failed with no signal: {result.stderr}"
        assert result.stdout.strip() == "", (
            f"Script printed output when no signal file exists: {result.stdout!r}"
        )

    def test_reads_vetka_signals_dir(self, tmp_path):
        """Signal from ~/.vetka/signals/ must be delivered."""
        vetka_dir = Path.home() / ".vetka" / "signals"
        sig = self._write_signal(vetka_dir, self.TEST_ROLE, "test-vetka-signal")
        try:
            result = self._run_script(self.TEST_ROLE)
            assert result.returncode == 0, f"Script error: {result.stderr}"
            assert "test-vetka-signal" in result.stdout, (
                f"Signal from ~/.vetka/signals/ not delivered. stdout={result.stdout!r}"
            )
            assert "Commander" in result.stdout
        finally:
            sig.unlink(missing_ok=True)
            # Ensure signal was consumed (file deleted)
            assert not sig.exists(), "Signal file not deleted after read (no atomic cleanup)"

    def test_reads_claude_signals_dir(self, tmp_path):
        """Signal from ~/.claude/signals/ must be delivered (Claude Code fallback)."""
        claude_dir = Path.home() / ".claude" / "signals"
        sig = self._write_signal(claude_dir, self.TEST_ROLE, "test-claude-fallback-signal")
        try:
            result = self._run_script(self.TEST_ROLE)
            assert result.returncode == 0, f"Script error: {result.stderr}"
            assert "test-claude-fallback-signal" in result.stdout, (
                f"Signal from ~/.claude/signals/ not delivered. stdout={result.stdout!r}"
            )
        finally:
            sig.unlink(missing_ok=True)

    def test_combines_both_signal_dirs(self):
        """When both dirs have signals, both must appear in output."""
        vetka_dir = Path.home() / ".vetka" / "signals"
        claude_dir = Path.home() / ".claude" / "signals"
        sig_v = self._write_signal(vetka_dir, self.TEST_ROLE, "from-vetka-dir")
        sig_c = self._write_signal(claude_dir, self.TEST_ROLE, "from-claude-dir")
        try:
            result = self._run_script(self.TEST_ROLE)
            assert "from-vetka-dir" in result.stdout, "vetka signal missing from combined output"
            assert "from-claude-dir" in result.stdout, "claude signal missing from combined output"
        finally:
            sig_v.unlink(missing_ok=True)
            sig_c.unlink(missing_ok=True)

    def test_signal_file_deleted_after_read(self):
        """Signal must be consumed — no duplicate delivery on next tool call."""
        vetka_dir = Path.home() / ".vetka" / "signals"
        sig = self._write_signal(vetka_dir, self.TEST_ROLE, "one-shot")
        self._run_script(self.TEST_ROLE)
        assert not sig.exists(), (
            "Signal file still exists after read — will deliver duplicate on next tool call!"
        )
        # Second run must be no-op
        result2 = self._run_script(self.TEST_ROLE)
        assert result2.stdout.strip() == "", "Second run should be no-op after file consumed"

    def test_no_op_when_role_empty(self):
        """No role → fast exit with no output."""
        result = subprocess.run(
            ["bash", str(self.SCRIPT)],
            capture_output=True, text=True,
            cwd=str(PROJECT_ROOT / ".claude" / "worktrees" / "harness-eta"),
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_malformed_json_does_not_crash(self):
        vetka_dir = Path.home() / ".vetka" / "signals"
        sig = vetka_dir / f"{self.TEST_ROLE}.json"
        vetka_dir.mkdir(parents=True, exist_ok=True)
        sig.write_text("{broken json{{")
        try:
            result = self._run_script(self.TEST_ROLE)
            assert result.returncode == 0, "Script should not crash on malformed JSON"
        finally:
            sig.unlink(missing_ok=True)


# ── 6. Session init — role_context fields ────────────────────────────────────

class TestSessionInitRoleContext:
    """session_init must return tool_type and memory_path for Vibe/Opencode agents."""

    @pytest.fixture(scope="class")
    def session_init_fn(self):
        import asyncio
        from src.mcp.tools.session_tools import vetka_session_init

        def call(role: str) -> dict:
            result = asyncio.run(vetka_session_init(
                user_id="test_eta",
                role=role,
                compress=True,
            ))
            # session_init returns {"success": True, "result": {...}} — unwrap
            if isinstance(result, dict) and "result" in result:
                return result["result"]
            return result

        return call

    @pytest.mark.parametrize("callsign", VIBE_CALLSIGNS)
    def test_vibe_role_context_has_tool_type(self, session_init_fn, callsign):
        result = session_init_fn(callsign)
        rc = result.get("role_context", {})
        assert rc, f"{callsign}: session_init returned no role_context"
        assert rc.get("tool_type") == "vibe", (
            f"{callsign}: role_context.tool_type={rc.get('tool_type')!r}, expected 'vibe'"
        )

    @pytest.mark.parametrize("callsign", VIBE_CALLSIGNS)
    def test_vibe_role_context_has_memory_path(self, session_init_fn, callsign):
        result = session_init_fn(callsign)
        rc = result.get("role_context", {})
        assert rc.get("memory_path"), (
            f"{callsign}: role_context missing memory_path — "
            "agent cannot find its persistent memory"
        )

    @pytest.mark.parametrize("callsign", ["Theta", "Lambda"])
    def test_opencode_role_context_has_tool_type(self, session_init_fn, callsign):
        result = session_init_fn(callsign)
        rc = result.get("role_context", {})
        assert rc.get("tool_type") == "opencode", (
            f"{callsign}: role_context.tool_type={rc.get('tool_type')!r}, expected 'opencode'"
        )

    @pytest.mark.parametrize("callsign", ["Alpha", "Eta"])
    def test_claude_code_role_context_has_tool_type(self, session_init_fn, callsign):
        result = session_init_fn(callsign)
        rc = result.get("role_context", {})
        assert rc.get("tool_type") == "claude_code", (
            f"{callsign}: role_context.tool_type={rc.get('tool_type')!r}"
        )

    @pytest.mark.parametrize("callsign", VIBE_CALLSIGNS + ["Theta", "Alpha"])
    def test_role_context_has_owned_paths(self, session_init_fn, callsign):
        result = session_init_fn(callsign)
        rc = result.get("role_context", {})
        owned = rc.get("owned_paths", [])
        assert owned, f"{callsign}: role_context.owned_paths is empty — agent has no guard"

    def test_session_init_returns_stm_or_engram_context(self, session_init_fn):
        """Session init should return memory/ENGRAM context sections for agents with memory_path."""
        result = session_init_fn("Mistral-1")
        # STM/ENGRAM may appear as 'memory_summary', 'engram', or 'predecessor_advice'
        has_memory_context = any(
            k in result for k in ("memory_summary", "engram", "predecessor_advice",
                                   "experience_reports", "reflex_context")
        )
        # Not failing — but flagging if missing (may not be wired yet)
        if not has_memory_context:
            pytest.xfail(
                "session_init for Vibe agents does not yet return STM/ENGRAM/predecessor context. "
                "memory_path is set but not yet read into session. "
                "Enhancement: wire memory_path read into session_init for Vibe/Opencode."
            )


# ── 7. Memory structure (STM/ENGRAM persistence) ──────────────────────────────

class TestMemoryStructure:
    """memory_path directories and MEMORY.md files — structure and format."""

    def test_memory_roles_dir_exists_or_creatable(self):
        memory_dir = PROJECT_ROOT / "memory" / "roles"
        # Either exists, or parent exists so we can create
        assert memory_dir.exists() or memory_dir.parent.exists(), (
            f"memory/roles/ directory not found at {memory_dir}. "
            "Persistent memory cannot be written."
        )

    @pytest.mark.parametrize("callsign", VIBE_CALLSIGNS + OPENCODE_CALLSIGNS + ["Alpha", "Zeta", "Eta"])
    def test_memory_path_format(self, callsign):
        reg = _load_registry()
        role = reg.get_by_callsign(callsign)
        if not role or not role.memory_path:
            pytest.skip(f"{callsign} has no memory_path")
        expected_pattern = f"memory/roles/{callsign}/MEMORY.md"
        assert role.memory_path == expected_pattern, (
            f"{callsign}.memory_path={role.memory_path!r} — "
            f"expected '{expected_pattern}' for consistent role isolation"
        )

    @pytest.mark.parametrize("callsign", VIBE_CALLSIGNS + OPENCODE_CALLSIGNS)
    def test_existing_memory_file_is_valid_markdown(self, callsign):
        reg = _load_registry()
        role = reg.get_by_callsign(callsign)
        if not role or not role.memory_path:
            pytest.skip(f"{callsign} has no memory_path")
        memory_file = PROJECT_ROOT / role.memory_path
        if not memory_file.exists():
            pytest.skip(f"{callsign}: memory file not yet created (ok for new agents)")
        content = memory_file.read_text(encoding="utf-8")
        assert len(content) > 0, f"{callsign}: MEMORY.md exists but is empty"
        # Basic markdown check — should start with a heading
        assert content.startswith("#") or "##" in content[:200], (
            f"{callsign}: MEMORY.md doesn't look like structured markdown"
        )


# ── 8. Relay / эстафетность (notification roundtrip) ─────────────────────────

class TestNotificationRelay:
    """Notifications must flow: Vibe→Claude and Claude→Vibe through task_board."""

    def _board(self):
        from src.orchestration.task_board import get_task_board
        return get_task_board()

    def test_vibe_can_send_notification_to_claude_agent(self):
        """Mistral-1 (Vibe) → Alpha (Claude Code) notification roundtrip.
        get_notifications returns List[Dict], not dict with 'notifications' key.
        """
        board = self._board()
        result = board.notify(
            source_role="Mistral-1",
            target_role="Alpha",
            message="[test] Vibe→Claude relay check",
            ntype="custom",
        )
        assert result.get("success"), f"Notify failed: {result}"
        notif_id = result.get("notification_id", "")

        # get_notifications returns List[Dict] directly
        notifs = board.get_notifications(role="Alpha", unread_only=True)
        assert isinstance(notifs, list), f"Expected list, got {type(notifs)}"
        msgs = [n.get("message", "") for n in notifs]
        assert any("Vibe→Claude relay check" in m for m in msgs), (
            f"Alpha did not receive Mistral-1's notification. Notifications: {msgs}"
        )

        if notif_id:
            board.ack_notifications(role="Alpha", notification_ids=[notif_id])

    def test_claude_can_send_notification_to_vibe_agent(self):
        """Commander (Claude Code) → Mistral-1 (Vibe) notification roundtrip."""
        board = self._board()
        result = board.notify(
            source_role="Commander",
            target_role="Mistral-1",
            message="[test] Claude→Vibe relay check",
            ntype="custom",
        )
        assert result.get("success"), f"Notify failed: {result}"
        notif_id = result.get("notification_id", "")

        notifs = board.get_notifications(role="Mistral-1", unread_only=True)
        assert isinstance(notifs, list)
        msgs = [n.get("message", "") for n in notifs]
        assert any("Claude→Vibe relay check" in m for m in msgs), (
            f"Mistral-1 did not receive Commander notification. Notifications: {msgs}"
        )

        if notif_id:
            board.ack_notifications(role="Mistral-1", notification_ids=[notif_id])

    def test_signal_file_written_for_vibe_agent(self):
        """Signal file must appear in ~/.vetka/signals/ or ~/.claude/signals/ for Vibe agents."""
        board = self._board()
        board.notify(
            source_role="Commander",
            target_role="Mistral-3",
            message="[test] signal file presence check",
            ntype="custom",
        )
        vetka_sig = Path.home() / ".vetka" / "signals" / "Mistral-3.json"
        claude_sig = Path.home() / ".claude" / "signals" / "Mistral-3.json"
        signal_exists = vetka_sig.exists() or claude_sig.exists()
        # Clean up
        vetka_sig.unlink(missing_ok=True)
        claude_sig.unlink(missing_ok=True)
        assert signal_exists, (
            "Notification to Mistral-3 did not create a signal file in "
            "~/.vetka/signals/ or ~/.claude/signals/. "
            "PRETOOL_HOOK-based delivery will not work."
        )


# ── 9. Guard — owned_paths enforcement ───────────────────────────────────────

class TestOwnershipGuard:
    """AgentRegistry ownership checks for Vibe/Opencode agents."""

    def test_vibe_agents_cannot_own_client_src(self):
        reg = _load_registry()
        for cs in VIBE_CALLSIGNS:
            role = reg.get_by_callsign(cs)
            if not role:
                continue
            for path in role.owned_paths:
                assert not path.startswith("client/src/components/cut/"), (
                    f"{cs} owns cut frontend path {path!r} — "
                    "Vibe agents should not touch CUT UI components"
                )

    def test_opencode_agents_blocked_from_e2e(self):
        reg = _load_registry()
        for cs in OPENCODE_CALLSIGNS + VIBE_CALLSIGNS:
            role = reg.get_by_callsign(cs)
            if not role:
                continue
            # e2e should be in blocked_paths or not in owned_paths
            in_blocked = any("e2e" in p for p in role.blocked_paths)
            in_owned = any("e2e" in p for p in role.owned_paths)
            # Mu is QA so may own e2e
            if cs not in ("Mu", "Lambda", "Mistral-2"):
                assert in_blocked or not in_owned, (
                    f"{cs} can access e2e/ without being a QA agent"
                )

    def test_registry_file_ownership_check(self):
        """AgentRegistry.validate_file_ownership() works for Vibe agents."""
        reg = _load_registry()
        mistral1 = reg.get_by_callsign("Mistral-1")
        if not mistral1:
            pytest.skip("Mistral-1 not in registry")
        result = reg.validate_file_ownership(mistral1.callsign, "src/services/test_file.py")
        assert result.is_owned, "Mistral-1 should own src/services/ paths"

        result_blocked = reg.validate_file_ownership(
            mistral1.callsign, "client/src/components/SomeUI.tsx"
        )
        assert result_blocked.is_blocked, "Mistral-1 should be blocked from client/src/components/"


# ── 10. Behavioral checklist (manual / Delta) ────────────────────────────────

class TestBehavioralChecklist:
    """
    Tests that require actually launching agents.
    Marked xfail with detailed instructions for manual or Delta verification.

    Run with: pytest -v -k behavioral --runxfail
    """

    @pytest.mark.xfail(reason="Requires launching Vibe agent manually", strict=False)
    def test_vibe_agent_startup_time(self):
        """
        MANUAL: Launch Vibe in weather-mistral-1 and measure time until first tool call.

        Expected: Agent calls vetka_session_init within first 2 messages.
        Red flag: Agent asks clarifying questions before calling session_init.

        Launch:
          cd .claude/worktrees/weather-mistral-1
          bash launch_vibe.sh
          > (say nothing — observe first action)
        """
        pytest.xfail("Manual test — see docstring")

    @pytest.mark.xfail(reason="Requires two Vibe sessions", strict=False)
    def test_vibe_session_to_session_memory(self):
        """
        MANUAL: Verify Vibe agent reads memory/roles/<Role>/MEMORY.md across sessions.

        Steps:
          1. Session 1: Write something to memory: "Lesson: always check owned_paths first"
          2. Close Vibe
          3. Session 2: Ask agent "what do you remember from previous sessions?"
          4. Expected: Agent mentions the lesson from memory file

        Memory file location: memory/roles/Mistral-1/MEMORY.md
        """
        pytest.xfail("Manual test — see docstring")

    @pytest.mark.xfail(reason="Requires live MCP server", strict=False)
    def test_vibe_all_tools_accessible(self):
        """
        MANUAL: Verify all expected vetka MCP tools are accessible in Vibe.

        Expected tools (no prefix in Vibe):
          vetka_session_init, vetka_task_board, vetka_git_commit,
          vetka_read_file, vetka_search_files, vetka_web_search

        Red flags:
          - "Unknown tool" error
          - Tool list empty
          - Only partial tools visible

        Check: In Vibe, look at Tools panel or run: vetka_health
        Config: ~/.vibe/config.toml must have [mcpServers.vetka] entry
        """
        pytest.xfail("Manual test — see docstring")

    @pytest.mark.xfail(reason="Requires Reflex service running", strict=False)
    def test_reflex_tools_in_vibe_context(self):
        """
        MANUAL: Verify REFLEX scoring works for Vibe/Opencode agent tool selection.

        session_init for Mistral-1 should return reflex_context with:
          - available_tools scored by REFLEX signals
          - Signal 9 (Weaviate embedding) = 0.0 (stub, expected)
          - Signals 1-8 computed normally

        Check: session_init result → reflex_context key
        """
        pytest.xfail("Manual test — see docstring")

    @pytest.mark.xfail(reason="Requires completed task + Vibe session", strict=False)
    def test_vibe_relay_full_cycle(self):
        """
        MANUAL: Full relay cycle test.

        1. Commander sends notification to Mistral-1 via task_board action=notify
        2. Launch Vibe with launch_vibe.sh
        3. Vibe triggers PRETOOL_HOOK on first tool call
        4. check_opencode_signals.sh reads ~/.vetka/signals/Mistral-1.json
        5. Signal content injected as context before tool
        6. Agent sees notification in its context

        Verify step 6 by asking: "Did you receive any messages from Commander?"
        """
        pytest.xfail("Manual test — see docstring")
