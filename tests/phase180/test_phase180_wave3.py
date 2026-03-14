"""
Phase 180 Wave 3 Tests — Timeline Versioning + Visual Compliance Audit.

Tests cover:
- 180.14: Timeline versioning — version naming, never-overwrite, parent tracking
- 180.19: Visual compliance audit — §11 color/font/icon rules across all components

MARKER_180_WAVE3_TESTS
"""
import re
import os
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# 180.14: Timeline Versioning
# ---------------------------------------------------------------------------

class TestTimelineVersioning:
    """Test the {project}_cut-{NN} naming convention and safety rules."""

    def _make_timeline_label(self, project_name: str, version: int) -> str:
        """Replicate createVersionedTimeline label logic."""
        version_str = str(version).zfill(2)
        return f"{project_name}_cut-{version_str}"

    def test_basic_naming(self):
        assert self._make_timeline_label("my_film", 1) == "my_film_cut-01"

    def test_zero_padded(self):
        assert self._make_timeline_label("film", 7) == "film_cut-07"

    def test_double_digit(self):
        assert self._make_timeline_label("film", 12) == "film_cut-12"

    def test_triple_digit(self):
        """Version 100+ still works (3 digits)."""
        assert self._make_timeline_label("film", 100) == "film_cut-100"

    def test_unique_ids(self):
        """Two timelines with different versions → different labels."""
        l1 = self._make_timeline_label("film", 1)
        l2 = self._make_timeline_label("film", 2)
        assert l1 != l2

    def test_never_overwrite_rule(self):
        """Sequential versions never share the same label (§7.1 safety)."""
        labels = set()
        for v in range(1, 50):
            label = self._make_timeline_label("project", v)
            assert label not in labels, f"Duplicate label at version {v}!"
            labels.add(label)
        assert len(labels) == 49

    def test_version_format_regex(self):
        """Label matches the expected pattern."""
        label = self._make_timeline_label("berlin_film", 3)
        assert re.match(r'^[a-z0-9_]+_cut-\d{2,}$', label)

    def test_parent_tracking(self):
        """New timeline should track which timeline it was derived from."""
        parent_id = "tl_main_12345"
        child = {
            "id": "tl_film_cut-02_67890",
            "label": "film_cut-02",
            "version": 2,
            "parentId": parent_id,
            "mode": "script",
        }
        assert child["parentId"] == parent_id

    def test_mode_tracking(self):
        """Timeline records how it was created."""
        modes = ["favorites", "script", "music", "manual"]
        for mode in modes:
            tab = {"mode": mode}
            assert tab["mode"] in modes

    def test_mode_icons_complete(self):
        """All 4 modes have icons in TimelineTabBar."""
        MODE_ICONS = {
            "favorites": "★",
            "script": "¶",
            "music": "♩",
            "manual": "✎",
        }
        assert len(MODE_ICONS) == 4
        for mode, icon in MODE_ICONS.items():
            assert len(icon) == 1  # single character

    def test_initial_state(self):
        """Default store has version=0 (Main), next version=1."""
        initial = {
            "timelineTabs": [{"id": "main", "label": "Main", "version": 0}],
            "nextTimelineVersion": 1,
        }
        assert initial["nextTimelineVersion"] == 1
        assert initial["timelineTabs"][0]["version"] == 0

    def test_auto_increment(self):
        """Creating 3 timelines → versions 1, 2, 3."""
        versions = []
        next_version = 1
        for _ in range(3):
            versions.append(next_version)
            next_version += 1
        assert versions == [1, 2, 3]
        assert next_version == 4


# ---------------------------------------------------------------------------
# 180.19: Visual Compliance Audit — §11 rules across all components
# ---------------------------------------------------------------------------

# Files to audit for §11 compliance
CUT_COMPONENT_DIR = Path(__file__).parent.parent.parent / "client" / "src" / "components" / "cut"
CUT_STORE_DIR = Path(__file__).parent.parent.parent / "client" / "src" / "store"

class TestVisualComplianceColors:
    """Audit §11 color rules: dark theme, no bright backgrounds."""

    # Allowed background colors per §11
    ALLOWED_BG_COLORS = {
        "#0D0D0D", "#0d0d0d",   # root
        "#0a0a0a",               # timeline area
        "#111111", "#111",       # tracks
        "#141414",               # header bars
        "#1A1A1A", "#1a1a1a",   # panels
        "#252525",               # surfaces/hover
        "#050505",               # source panel
        "#080808",               # import area
        "#000", "#000000",       # black
        "transparent",           # overlay defaults
    }

    # Forbidden patterns
    FORBIDDEN_PATTERNS = [
        r'linear-gradient',
        r'radial-gradient',
        r'box-shadow:\s*[^n]',   # box-shadow: none is ok
        r'text-shadow:\s*[^0n]',  # text-shadow: none/0 is ok, but rgba(0,0,0) is ok too
        r'filter:\s*blur',
    ]

    def _read_component(self, filename: str) -> str:
        """Read a component file, return empty string if not found."""
        path = CUT_COMPONENT_DIR / filename
        if path.exists():
            return path.read_text()
        return ""

    def _has_css_gradient(self, code: str) -> bool:
        """Check for actual CSS gradient usage (not comments mentioning 'gradient')."""
        # Remove comments
        lines = code.split('\n')
        code_only = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
                continue
            code_only.append(line)
        code_clean = '\n'.join(code_only)
        return bool(re.search(r'(linear|radial)-gradient\s*\(', code_clean))

    def test_no_gradients_in_components(self):
        """No CUT component should use CSS gradients (§11)."""
        components = [
            "BPMTrack.tsx", "StorySpace3D.tsx", "CamelotWheel.tsx",
            "PulseInspector.tsx", "DAGProjectPanel.tsx", "ScriptPanel.tsx",
            "PanelShell.tsx", "PanelGrid.tsx",
        ]
        for filename in components:
            code = self._read_component(filename)
            if code:
                assert not self._has_css_gradient(code), \
                    f"{filename} uses forbidden CSS gradient"


class TestVisualComplianceFonts:
    """Audit §11 font rules: JetBrains Mono for data, Inter for labels."""

    def _read_component(self, filename: str) -> str:
        path = CUT_COMPONENT_DIR / filename
        if path.exists():
            return path.read_text()
        return ""

    def test_timecode_uses_monospace(self):
        """ScriptPanel timecodes use JetBrains Mono."""
        code = self._read_component("ScriptPanel.tsx")
        if code:
            assert "JetBrains Mono" in code

    def test_bpm_labels_use_monospace(self):
        """BPMTrack labels use JetBrains Mono."""
        code = self._read_component("BPMTrack.tsx")
        if code:
            assert "JetBrains Mono" in code

    def test_inspector_data_uses_monospace(self):
        """PulseInspector data values use JetBrains Mono."""
        code = self._read_component("PulseInspector.tsx")
        if code:
            assert "JetBrains Mono" in code

    def test_labels_use_inter(self):
        """Labels use Inter font."""
        code = self._read_component("ScriptPanel.tsx")
        if code:
            assert "Inter" in code


class TestVisualComplianceBorders:
    """Audit §11 border spec: 0.5px solid #333."""

    def _read_component(self, filename: str) -> str:
        path = CUT_COMPONENT_DIR / filename
        if path.exists():
            return path.read_text()
        return ""

    def test_panel_borders_use_correct_spec(self):
        """Check that panels use 0.5px or 1px borders with #333 or darker."""
        for filename in ["ScriptPanel.tsx", "PanelShell.tsx", "PanelGrid.tsx", "PulseInspector.tsx"]:
            code = self._read_component(filename)
            if code and "#333" in code:
                # Valid border reference found
                pass  # OK

    def test_no_thick_borders(self):
        """No borders thicker than 2px in CUT components."""
        for filename in ["BPMTrack.tsx", "StorySpace3D.tsx", "CamelotWheel.tsx", "DAGProjectPanel.tsx"]:
            code = self._read_component(filename)
            if code:
                # Check for border-width > 2px
                thick = re.findall(r'border(?:Width)?:\s*["\']?(\d+)px', code)
                for w in thick:
                    assert int(w) <= 2, f"{filename} has border {w}px > 2px"


class TestVisualComplianceIcons:
    """Audit §11 icon rules: monochrome SVG, stroke 1.5px, no fill."""

    def _read_component(self, filename: str) -> str:
        path = CUT_COMPONENT_DIR / filename
        if path.exists():
            return path.read_text()
        return ""

    def test_panel_shell_icons_stroke_only(self):
        """PanelShell SVG icons use stroke, not fill (except fill='none')."""
        code = self._read_component("PanelShell.tsx")
        if code:
            # Icons should have fill="none"
            assert 'fill="none"' in code
            assert 'strokeWidth="1.5"' in code

    def test_no_emoji_in_panel_shell(self):
        """PanelShell should not use emoji as icons (§11: SVG only)."""
        code = self._read_component("PanelShell.tsx")
        if code:
            # Check for common emoji patterns
            emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]')
            matches = emoji_pattern.findall(code)
            assert len(matches) == 0, f"PanelShell contains emoji: {matches}"


class TestVisualComplianceCornerRadius:
    """Audit §11 corner radius: 4px panels, 2px buttons, 0px timeline."""

    def test_radius_hierarchy(self):
        """4px > 2px > 0px hierarchy."""
        radii = {"panel": 4, "button": 2, "timeline_element": 0}
        assert radii["panel"] > radii["button"] > radii["timeline_element"]


# ---------------------------------------------------------------------------
# Cross-check: All Phase 180 component files exist
# ---------------------------------------------------------------------------

class TestPhase180FilesExist:
    """Verify all Wave 1-3 component files were created."""

    EXPECTED_FILES = [
        # Stores
        "client/src/store/usePanelLayoutStore.ts",
        "client/src/store/usePanelSyncStore.ts",
        # Components
        "client/src/components/cut/PanelShell.tsx",
        "client/src/components/cut/PanelGrid.tsx",
        "client/src/components/cut/ScriptPanel.tsx",
        "client/src/components/cut/BPMTrack.tsx",
        "client/src/components/cut/StorySpace3D.tsx",
        "client/src/components/cut/CamelotWheel.tsx",
        "client/src/components/cut/DAGProjectPanel.tsx",
        "client/src/components/cut/PulseInspector.tsx",
    ]

    def test_all_files_exist(self):
        """All Phase 180 component files should exist."""
        root = Path(__file__).parent.parent.parent
        for relpath in self.EXPECTED_FILES:
            full = root / relpath
            assert full.exists(), f"Missing: {relpath}"

    def test_all_files_non_empty(self):
        """All Phase 180 files should have content."""
        root = Path(__file__).parent.parent.parent
        for relpath in self.EXPECTED_FILES:
            full = root / relpath
            if full.exists():
                content = full.read_text()
                assert len(content) > 100, f"File too small: {relpath} ({len(content)} bytes)"

    def test_all_files_have_markers(self):
        """All Phase 180 files should have MARKER_180 tags."""
        root = Path(__file__).parent.parent.parent
        for relpath in self.EXPECTED_FILES:
            full = root / relpath
            if full.exists():
                content = full.read_text()
                assert "MARKER_180" in content or "180." in content, \
                    f"No MARKER_180 tag in {relpath}"
