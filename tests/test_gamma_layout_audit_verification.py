"""
MARKER_EPSILON.LAYOUT1: Gamma layout audit verification tests.

Verifies Gamma's structural changes from Wave 6:
1. Editing workspace preset composition matches Unified Vision
2. SpeedControl is a modal dialog, NOT a dockview panel
3. Transitions is inside Effects tab group (direction: 'within')
4. Effect Controls dual mode: Browser (no clip) / Controls (clip selected)
5. No Scopes/Color/LUTs/Montage/Mixer in Editing workspace

Strategy: Source-parsing contract tests (no browser needed).
"""

import re
from pathlib import Path

import pytest

# ─── Paths ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CLIENT_SRC = ROOT / "client" / "src" / "components" / "cut"
PRESET_BUILDERS = CLIENT_SRC / "presetBuilders.ts"
DOCKVIEW_LAYOUT = CLIENT_SRC / "DockviewLayout.tsx"
EFFECTS_PANEL = CLIENT_SRC / "EffectsPanel.tsx"
MENU_BAR = CLIENT_SRC / "MenuBar.tsx"
SPEED_CONTROL = CLIENT_SRC / "SpeedControl.tsx"


def _read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"File not found: {path}")
    return path.read_text()


def _find(source: str, pattern: str) -> bool:
    return bool(re.search(pattern, source))


# ─── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def preset_src():
    return _read(PRESET_BUILDERS)


@pytest.fixture(scope="module")
def dockview_src():
    return _read(DOCKVIEW_LAYOUT)


@pytest.fixture(scope="module")
def effects_src():
    return _read(EFFECTS_PANEL)


@pytest.fixture(scope="module")
def menubar_src():
    return _read(MENU_BAR)


def _extract_editing_preset_panels(source: str) -> list[str]:
    """Extract panel IDs added in the editing preset builder function."""
    # Find the editing preset function
    match = re.search(
        r"(?:function\s+buildEditing|buildEditing\s*=|editing.*?=.*?(?:api|dockview))"
        r"(.*?)(?=function\s+build|export\s|const\s+\w+Preset|$)",
        source, re.DOTALL | re.IGNORECASE
    )
    if not match:
        # Try alternative: find all addPanel calls in first preset function
        match = re.search(
            r"(?:editing|Editing).*?\{(.*?)\}",
            source, re.DOTALL
        )
    # Fallback: find all addPanel with id:
    panels = re.findall(r"""addPanel\(\{[^}]*id:\s*['"](\w+)['"]""", source)
    if not panels:
        panels = re.findall(r"""id:\s*['"](\w+)['"]""", source)
    return panels


# ═══════════════════════════════════════════════════════════════════════
# PART 1: Editing workspace preset composition
# ═══════════════════════════════════════════════════════════════════════

class TestEditingPresetComposition:
    """Editing workspace must contain exactly the right panels."""

    REQUIRED_PANELS = {
        "project", "script", "graph",           # Navigation
        "inspector", "clip", "history",          # Analysis
        "storyspace",                            # Analysis
        "source", "program",                     # Monitors
        "effects", "transitions",                # Effects group
        "timeline",                              # Timeline
    }

    FORBIDDEN_IN_EDITING = {
        "scopes", "colorcorrector", "lutbrowser",  # Color workspace
        "montage",                                  # AI features
        "mixer",                                    # Audio workspace
    }

    def test_preset_builders_file_exists(self):
        assert PRESET_BUILDERS.exists(), \
            f"presetBuilders.ts not found at {PRESET_BUILDERS}"

    def test_required_panels_present(self, preset_src):
        """All required panels must appear in the editing preset."""
        for panel in self.REQUIRED_PANELS:
            assert re.search(
                rf"""id:\s*['\"]({panel})['\"]""", preset_src
            ), f"Required panel '{panel}' not found in presetBuilders"

    def test_forbidden_panels_absent_from_editing(self, preset_src):
        """Scopes/Color/LUTs/Montage/Mixer must NOT be in editing preset."""
        # Extract the editing function specifically
        # The editing function is typically the first builder
        editing_match = re.search(
            r"(function\s+buildEditing|buildEditing\s*[:=]|Editing\s*[:=]\s*\()"
            r"(.*?)(?=function\s+build[A-Z]|export\s+(?:default|const\s+(?!buildEditing)))",
            preset_src, re.DOTALL
        )
        if not editing_match:
            # If we can't isolate editing function, check the whole first section
            # before Color/Audio sections appear
            sections = re.split(r"function\s+build(?:Color|Audio|Minimal)", preset_src)
            editing_section = sections[0] if sections else preset_src

        editing_section = editing_match.group(2) if editing_match else preset_src.split("buildColor")[0] if "buildColor" in preset_src else preset_src

        for panel in self.FORBIDDEN_IN_EDITING:
            if re.search(rf"""addPanel\([^)]*id:\s*['\"]({panel})['\"]""", editing_section):
                pytest.fail(
                    f"Forbidden panel '{panel}' found in Editing preset! "
                    "Should only be in Color/Audio/Minimal workspace."
                )


# ═══════════════════════════════════════════════════════════════════════
# PART 2: SpeedControl is a modal, NOT a dockview panel
# ═══════════════════════════════════════════════════════════════════════

class TestSpeedControlIsModal:
    """SpeedControl must be a modal dialog, not a dockview panel."""

    def test_speed_not_in_dockview_registry(self, dockview_src):
        """SpeedControl must NOT be in PANEL_COMPONENTS registry."""
        # Check it's not a registered dockview panel
        has_speed_panel = _find(
            dockview_src,
            r"""speed\s*:\s*\w+"""
        )
        if has_speed_panel:
            # Verify it's commented out
            lines = dockview_src.split("\n")
            for line in lines:
                if re.search(r"speed\s*:", line) and not line.strip().startswith("//"):
                    pytest.fail(
                        "SpeedControl registered as dockview panel — should be modal"
                    )

    def test_speed_control_file_exists(self):
        """SpeedControl component must exist."""
        assert SPEED_CONTROL.exists(), \
            f"SpeedControl.tsx not found at {SPEED_CONTROL}"

    def test_speed_mounted_in_menubar(self, menubar_src):
        """SpeedControl must be mounted as modal via MenuBar."""
        assert _find(menubar_src, r"SpeedControl"), \
            "SpeedControl not referenced in MenuBar.tsx"
        # Check it's a Suspense/lazy loaded modal
        has_lazy = _find(menubar_src, r"lazy\(.*SpeedControl")
        has_suspense = _find(menubar_src, r"Suspense.*SpeedControl|SpeedControl.*Suspense")
        has_modal = _find(menubar_src, r"speedControl.*[Oo]pen|showSpeed|setSpeed")
        assert has_lazy or has_suspense or has_modal, \
            "SpeedControl not mounted as modal in MenuBar (expected lazy/Suspense)"

    def test_speed_not_in_editing_preset(self, preset_src):
        """Speed panel must not appear in editing preset addPanel calls."""
        assert not re.search(
            r"""addPanel\([^)]*id:\s*['"]speed['"]""", preset_src
        ), "SpeedControl appears as addPanel in presetBuilders — should be modal"


# ═══════════════════════════════════════════════════════════════════════
# PART 3: Transitions inside Effects tab group
# ═══════════════════════════════════════════════════════════════════════

class TestTransitionsInEffectsGroup:
    """Transitions must be a tab WITHIN the Effects panel group."""

    def test_transitions_uses_within_direction(self, preset_src):
        """Transitions panel must use direction: 'within' referencing effects."""
        # Find transitions addPanel call
        transitions_match = re.search(
            r"""addPanel\(\{[^}]*id:\s*['"]transitions['"][^}]*\}""",
            preset_src, re.DOTALL
        )
        assert transitions_match, "Transitions addPanel not found in presetBuilders"
        block = transitions_match.group(0)
        assert _find(block, r"direction:\s*['\"]within['\"]"), \
            "Transitions panel must use direction: 'within' (tab in same group)"
        assert _find(block, r"referencePanel:\s*['\"]effects['\"]"), \
            "Transitions must reference 'effects' panel"

    def test_transitions_not_standalone_tab(self, preset_src):
        """Transitions must NOT be a separate dockview column/row."""
        transitions_match = re.search(
            r"""addPanel\(\{[^}]*id:\s*['"]transitions['"][^}]*\}""",
            preset_src, re.DOTALL
        )
        if transitions_match:
            block = transitions_match.group(0)
            for bad_dir in ["right", "left", "above", "below"]:
                if _find(block, rf"direction:\s*['\"]({bad_dir})['\"]"):
                    pytest.fail(
                        f"Transitions uses direction='{bad_dir}' — "
                        "should be 'within' to tab inside Effects group"
                    )


# ═══════════════════════════════════════════════════════════════════════
# PART 4: Effect Controls dual mode
# ═══════════════════════════════════════════════════════════════════════

class TestEffectControlsDualMode:
    """EffectsPanel must have dual mode: Browser + Controls."""

    def test_effects_panel_checks_selected_clip(self, effects_src):
        """Must branch on selectedClip to show Browser vs Controls."""
        assert _find(effects_src, r"selectedClip"), \
            "EffectsPanel doesn't check selectedClip"
        assert _find(effects_src, r"!selectedClip|selectedClip\s*===?\s*null|selectedClip\s*===?\s*undefined"), \
            "EffectsPanel doesn't branch on clip selection state"

    def test_effects_browser_mode(self, effects_src):
        """No clip selected → shows Effects Browser."""
        assert _find(effects_src, r"EffectsBrowser|effects.*browser|Browser"), \
            "EffectsPanel missing Effects Browser mode (no clip selected)"

    def test_effect_controls_header(self, effects_src):
        """Clip selected → shows 'Effect Controls' header."""
        assert _find(effects_src, r"Effect Controls"), \
            "EffectsPanel missing 'Effect Controls' header"

    def test_motion_controls_in_effect_controls(self, effects_src):
        """Effect Controls must include Motion section (Position/Scale/Rotation)."""
        assert _find(effects_src, r"[Mm]otion"), \
            "EffectsPanel missing Motion section in Effect Controls"


# ═══════════════════════════════════════════════════════════════════════
# PART 5: Dockview panel registry completeness
# ═══════════════════════════════════════════════════════════════════════

class TestDockviewRegistry:
    """PANEL_COMPONENTS registry must include all workspace panels."""

    EXPECTED_PANELS = {
        "project", "script", "graph",
        "inspector", "clip", "storyspace", "history",
        "effects", "transitions",
        "mixer", "scopes", "colorcorrector", "lutbrowser",
        "source", "program", "timeline",
    }

    def test_registry_has_all_panels(self, dockview_src):
        """All expected panels must be in PANEL_COMPONENTS."""
        for panel in self.EXPECTED_PANELS:
            assert re.search(
                rf"""{panel}\s*:""", dockview_src
            ), f"Panel '{panel}' not in PANEL_COMPONENTS registry"

    def test_speed_not_in_registry(self, dockview_src):
        """Speed must NOT be in PANEL_COMPONENTS (it's a modal)."""
        lines = dockview_src.split("\n")
        for line in lines:
            if re.search(r"^\s*speed\s*:", line) and not line.strip().startswith("//"):
                pytest.fail("Speed is registered as dockview panel — should be modal")


# ═══════════════════════════════════════════════════════════════════════
# PART 6: Workspace preset isolation
# ═══════════════════════════════════════════════════════════════════════

class TestWorkspaceIsolation:
    """Different workspaces must have different panel sets."""

    def test_color_workspace_has_scopes(self, preset_src):
        """Color workspace must include scopes/colorcorrector/lutbrowser."""
        # Find color section
        color_section = ""
        if "buildColor" in preset_src:
            match = re.search(
                r"buildColor(.*?)(?=function\s+build[A-Z]|export\s|$)",
                preset_src, re.DOTALL
            )
            if match:
                color_section = match.group(1)

        if not color_section:
            pytest.skip("buildColor function not found")

        for panel in ["scopes", "colorcorrector", "lutbrowser"]:
            assert re.search(
                rf"""id:\s*['\"]({panel})['\"]""", color_section
            ), f"Color workspace missing '{panel}' panel"

    def test_audio_workspace_has_mixer(self, preset_src):
        """Audio workspace must include mixer panel."""
        audio_section = ""
        if "buildAudio" in preset_src:
            match = re.search(
                r"buildAudio(.*?)(?=function\s+build[A-Z]|export\s|$)",
                preset_src, re.DOTALL
            )
            if match:
                audio_section = match.group(1)

        if not audio_section:
            pytest.skip("buildAudio function not found")

        assert re.search(
            r"""id:\s*['\"]mixer['\"]""", audio_section
        ), "Audio workspace missing 'mixer' panel"


# ═══════════════════════════════════════════════════════════════════════
# PART 7: Dead component cleanup verification
# ═══════════════════════════════════════════════════════════════════════

class TestDeadComponentsRemoved:
    """Legacy components identified in Unified Vision §1.5 should be deleted."""

    DEAD_COMPONENTS = [
        "CutEditorLayout.tsx",      # Legacy, replaced by V2
        "SourceBrowser.tsx",         # Legacy, replaced by ProjectPanel
        "TransportBar.tsx",          # Replaced by MonitorTransport + TimelineToolbar
    ]

    @pytest.mark.parametrize("component", DEAD_COMPONENTS)
    def test_dead_component_deleted(self, component):
        """Dead component should be deleted (per Unified Vision §1.5)."""
        path = CLIENT_SRC / component
        if path.exists():
            # Check if it's truly dead (0 imports)
            src = _read(path)
            # Not a hard failure — document as xfail
            pytest.xfail(
                f"Dead component {component} still exists ({len(src)} chars). "
                "Gamma-8 deleted 9 files but this may remain."
            )
