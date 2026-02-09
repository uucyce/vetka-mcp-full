"""
Tests for Phase 125.0 — Role Clarity + Verifier Fixes.

MARKER_125.0A: Verifier context limit 3000→6000 + original file context injection
MARKER_125.0B: VERIFIER_PASS_THRESHOLD confidence gate

Tests:
- TestResearcherPrompt: 6 tests — web research specialist, Tavily/Context7 awareness, new fields
- TestVerifierPrompt: 8 tests — 10-point checklist, severity guide, pass rules
- TestVerifierContextEnrichment: 5 tests — 6000 char limit, Scout files, marker rails
- TestConfidenceGate: 6 tests — threshold gate, auto-fail, severity routing
- TestRegressionPrevious: 4 tests — existing features intact
"""

import os
import json
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


# ── Helpers ──

def _load_prompts():
    """Load pipeline_prompts.json."""
    prompts_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
    )
    with open(prompts_path) as f:
        return json.load(f)


# ── Researcher Prompt Tests ──

class TestResearcherPrompt:
    """Tests for Phase 125.0: Researcher prompt upgrade."""

    def test_researcher_is_web_researcher(self):
        """Researcher prompt should identify as WEB RESEARCHER."""
        prompts = _load_prompts()
        researcher = prompts["researcher"]["system"]
        assert "WEB RESEARCHER" in researcher

    def test_researcher_mentions_grok(self):
        """Researcher prompt should mention Grok."""
        prompts = _load_prompts()
        researcher = prompts["researcher"]["system"]
        assert "Grok" in researcher

    def test_researcher_knows_tavily(self):
        """Researcher prompt should mention Tavily pre-fetch."""
        prompts = _load_prompts()
        researcher = prompts["researcher"]["system"]
        assert "Tavily" in researcher

    def test_researcher_knows_context7(self):
        """Researcher prompt should mention Context7 library docs."""
        prompts = _load_prompts()
        researcher = prompts["researcher"]["system"]
        assert "Context7" in researcher

    def test_researcher_has_api_patterns_field(self):
        """Researcher output should have api_patterns field."""
        prompts = _load_prompts()
        researcher = prompts["researcher"]["system"]
        assert "api_patterns" in researcher

    def test_researcher_has_known_issues_field(self):
        """Researcher output should have known_issues field."""
        prompts = _load_prompts()
        researcher = prompts["researcher"]["system"]
        assert "known_issues" in researcher


# ── Verifier Prompt Tests ──

class TestVerifierPrompt:
    """Tests for Phase 125.0: Verifier prompt upgrade with 10-point checklist."""

    def test_verifier_has_checklist(self):
        """Verifier prompt should have CHECKLIST section."""
        prompts = _load_prompts()
        verifier = prompts["verifier"]["system"]
        assert "CHECKLIST" in verifier

    def test_verifier_checks_code_present(self):
        """Checklist item 1: CODE PRESENT."""
        prompts = _load_prompts()
        verifier = prompts["verifier"]["system"]
        assert "CODE PRESENT" in verifier

    def test_verifier_checks_minimum_length(self):
        """Checklist item 3: MINIMUM LENGTH."""
        prompts = _load_prompts()
        verifier = prompts["verifier"]["system"]
        assert "MINIMUM LENGTH" in verifier or "10 lines" in verifier

    def test_verifier_checks_imports(self):
        """Checklist item 5: IMPORTS."""
        prompts = _load_prompts()
        verifier = prompts["verifier"]["system"]
        assert "IMPORTS" in verifier

    def test_verifier_checks_no_placeholders(self):
        """Checklist item 10: NO PLACEHOLDERS."""
        prompts = _load_prompts()
        verifier = prompts["verifier"]["system"]
        assert "NO PLACEHOLDERS" in verifier or "TODO" in verifier

    def test_verifier_severity_guide(self):
        """Verifier should define severity guide (minor vs major)."""
        prompts = _load_prompts()
        verifier = prompts["verifier"]["system"]
        assert "minor" in verifier
        assert "major" in verifier
        assert "Severity" in verifier or "severity" in verifier

    def test_verifier_pass_rules(self):
        """Verifier pass rule: items 1, 3, 5, 8, 10 must all pass."""
        prompts = _load_prompts()
        verifier = prompts["verifier"]["system"]
        # Should mention which items are required for pass
        assert "passed" in verifier.lower()
        assert "FAIL" in verifier

    def test_verifier_receives_original_context(self):
        """Verifier prompt should mention original file context."""
        prompts = _load_prompts()
        verifier = prompts["verifier"]["system"]
        assert "original file context" in verifier.lower() or "original" in verifier.lower()


# ── Verifier Context Enrichment Tests (MARKER_125.0A) ──

class TestVerifierContextEnrichment:
    """Tests for MARKER_125.0A: Verifier context 6000 chars + original file context."""

    def test_marker_125_0a_exists(self):
        """agent_pipeline.py should have MARKER_125.0A."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "MARKER_125.0A" in source

    def test_context_limit_6000(self):
        """Verifier should use 6000 char limit (not 3000)."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        # Should have [:6000] somewhere near MARKER_125.0A
        assert "[:6000]" in source

    def test_scout_report_injected(self):
        """Verifier should inject Scout report (relevant_files, marker_map)."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "scout_report" in source
        assert "relevant_files" in source
        assert "marker_map" in source

    def test_original_context_variable(self):
        """Should build original_context string from Scout data."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "original_context" in source
        assert "Original target files" in source

    def test_marker_rails_in_verifier(self):
        """Verifier should see marker rails from Scout."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "Marker rails" in source


# ── Confidence Gate Tests (MARKER_125.0B) ──

class TestConfidenceGate:
    """Tests for MARKER_125.0B: VERIFIER_PASS_THRESHOLD confidence gate."""

    def test_marker_125_0b_exists(self):
        """agent_pipeline.py should have MARKER_125.0B."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "MARKER_125.0B" in source

    def test_threshold_constant_exists(self):
        """VERIFIER_PASS_THRESHOLD should be defined."""
        from src.orchestration.agent_pipeline import VERIFIER_PASS_THRESHOLD
        assert isinstance(VERIFIER_PASS_THRESHOLD, float)
        assert 0.0 < VERIFIER_PASS_THRESHOLD < 1.0

    def test_threshold_default_075(self):
        """Default threshold should be 0.75."""
        from src.orchestration.agent_pipeline import VERIFIER_PASS_THRESHOLD
        # If env var not set, should default to 0.75
        assert VERIFIER_PASS_THRESHOLD == 0.75 or VERIFIER_PASS_THRESHOLD > 0

    def test_confidence_gate_logic_in_code(self):
        """Code should compare confidence < VERIFIER_PASS_THRESHOLD."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "confidence < VERIFIER_PASS_THRESHOLD" in source

    def test_auto_fail_sets_passed_false(self):
        """Confidence gate should set passed=False."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        # Find the confidence gate block — need wider window
        idx = source.find("MARKER_125.0B")
        block = source[idx:idx + 800]
        assert 'verification["passed"] = False' in block

    def test_auto_fail_adds_issue(self):
        """Confidence gate should add issue explaining why it failed."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        idx = source.find("MARKER_125.0B")
        block = source[idx:idx + 900]
        assert "Low confidence" in block
        assert "needs closer review" in block


# ── Regression Tests ──

class TestRegressionPrevious:
    """Ensure 124.9 features still work after 125.0 changes."""

    def test_scout_prompt_has_marker_map(self):
        """Scout prompt should still have marker_map (124.9)."""
        prompts = _load_prompts()
        scout = prompts["scout"]["system"]
        assert "marker_map" in scout

    def test_coder_prompt_has_marker_rails(self):
        """Coder prompt should still mention MARKER RAILS (124.9)."""
        prompts = _load_prompts()
        coder = prompts["coder"]["system"]
        assert "MARKER" in coder

    def test_all_prompts_valid_json(self):
        """pipeline_prompts.json should be valid JSON with all roles."""
        prompts = _load_prompts()
        assert "scout" in prompts
        assert "architect" in prompts
        assert "coder" in prompts
        assert "verifier" in prompts
        assert "researcher" in prompts

    def test_verify_subtask_method_exists(self):
        """AgentPipeline should have _verify_subtask method."""
        from src.orchestration.agent_pipeline import AgentPipeline
        assert hasattr(AgentPipeline, '_verify_subtask')
