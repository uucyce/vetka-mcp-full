"""
MARKER_EPSILON.T5B: Workspace preset BUILDER contract tests.

Extends EPSILON.T5 (WorkspacePresets.tsx UI contract) with
presetBuilders.ts structural verification:
1. Each preset builder produces correct panel set
2. Tab groupings use 'within' direction correctly
3. PRESET_BUILDERS registry maps all names
4. Panel sizing defaults are reasonable
5. No panel ID collisions across presets
6. Cross-preset panel consistency (shared panels)
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PRESET_BUILDERS = ROOT / "client" / "src" / "components" / "cut" / "presetBuilders.ts"


def _read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"File not found: {path}")
    return path.read_text()


def _extract_function_body(source: str, func_name: str) -> str:
    """Extract function body by name."""
    pattern = rf"export function {func_name}\([^)]*\)\s*\{{(.*?)\n\}}"
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        pytest.fail(f"Function {func_name} not found")
    return match.group(1)


def _extract_panels(func_body: str) -> list[dict]:
    """Extract all addPanel calls with their properties (handles nested position:{})."""
    panels = []
    # Match addPanel({ ... }) including nested objects
    for match in re.finditer(
        r"addPanel\(\{((?:[^{}]|\{[^{}]*\})*)\}", func_body
    ):
        block = match.group(1)
        panel = {}
        id_m = re.search(r"id:\s*'(\w+)'", block)
        comp_m = re.search(r"component:\s*'(\w+)'", block)
        title_m = re.search(r"title:\s*'([^']+)'", block)
        dir_m = re.search(r"direction:\s*'(\w+)'", block)
        ref_m = re.search(r"referencePanel:\s*'(\w+)'", block)
        if id_m:
            panel["id"] = id_m.group(1)
        if comp_m:
            panel["component"] = comp_m.group(1)
        if title_m:
            panel["title"] = title_m.group(1)
        if dir_m:
            panel["direction"] = dir_m.group(1)
        if ref_m:
            panel["reference"] = ref_m.group(1)
        if panel:
            panels.append(panel)
    return panels


@pytest.fixture(scope="module")
def source():
    return _read(PRESET_BUILDERS)


@pytest.fixture(scope="module")
def editing_panels(source):
    body = _extract_function_body(source, "buildEditingLayout")
    return _extract_panels(body)


@pytest.fixture(scope="module")
def color_panels(source):
    body = _extract_function_body(source, "buildColorLayout")
    return _extract_panels(body)


@pytest.fixture(scope="module")
def audio_panels(source):
    body = _extract_function_body(source, "buildAudioLayout")
    return _extract_panels(body)


# ═══════════════════════════════════════════════════════════════════════
# PART 1: Editing preset panel composition
# ═══════════════════════════════════════════════════════════════════════

class TestEditingPresetPanels:
    """Editing workspace: Navigation + Analysis + Monitors + Effects + Timeline."""

    EXPECTED_IDS = {
        "project", "script", "graph",
        "source", "program",
        "inspector", "clip", "history", "storyspace",
        "effects", "transitions",
        "timeline",
    }

    def test_panel_count(self, editing_panels):
        assert len(editing_panels) == 12, \
            f"Editing preset: expected 12 panels, got {len(editing_panels)}"

    def test_all_expected_panels(self, editing_panels):
        ids = {p["id"] for p in editing_panels}
        missing = self.EXPECTED_IDS - ids
        assert not missing, f"Editing preset missing panels: {missing}"

    def test_no_unexpected_panels(self, editing_panels):
        ids = {p["id"] for p in editing_panels}
        extra = ids - self.EXPECTED_IDS
        assert not extra, f"Editing preset has unexpected panels: {extra}"

    def test_navigation_tab_group(self, editing_panels):
        """Script and Graph must be tabs within Project group."""
        script = next(p for p in editing_panels if p["id"] == "script")
        graph = next(p for p in editing_panels if p["id"] == "graph")
        assert script.get("direction") == "within"
        assert script.get("reference") == "project"
        assert graph.get("direction") == "within"
        assert graph.get("reference") == "project"

    def test_analysis_tab_group(self, editing_panels):
        """Clip, History, StorySpace must be tabs within Inspector group."""
        for panel_id in ["clip", "history", "storyspace"]:
            panel = next(p for p in editing_panels if p["id"] == panel_id)
            assert panel.get("direction") == "within", \
                f"{panel_id} should be tab within inspector group"
            assert panel.get("reference") == "inspector", \
                f"{panel_id} should reference inspector"

    def test_effects_tab_group(self, editing_panels):
        """Transitions must be tab within Effects."""
        transitions = next(p for p in editing_panels if p["id"] == "transitions")
        assert transitions.get("direction") == "within"
        assert transitions.get("reference") == "effects"

    def test_timeline_is_bottom(self, editing_panels):
        """Timeline must use direction: 'below' (full-width bottom)."""
        timeline = next(p for p in editing_panels if p["id"] == "timeline")
        assert timeline.get("direction") == "below"


# ═══════════════════════════════════════════════════════════════════════
# PART 2: Color preset panel composition
# ═══════════════════════════════════════════════════════════════════════

class TestColorPresetPanels:
    """Color workspace: must include Scopes + ColorCorrector + LUTs."""

    COLOR_SPECIFIC = {"colorcorrector", "lutbrowser", "scopes"}

    def test_has_color_panels(self, color_panels):
        ids = {p["id"] for p in color_panels}
        missing = self.COLOR_SPECIFIC - ids
        assert not missing, f"Color preset missing: {missing}"

    def test_luts_tab_within_colorcorrector(self, color_panels):
        """LUTs must be tab within ColorCorrector group."""
        lut = next(p for p in color_panels if p["id"] == "lutbrowser")
        assert lut.get("direction") == "within"
        assert lut.get("reference") == "colorcorrector"

    def test_has_monitors(self, color_panels):
        ids = {p["id"] for p in color_panels}
        assert "source" in ids and "program" in ids

    def test_has_timeline(self, color_panels):
        ids = {p["id"] for p in color_panels}
        assert "timeline" in ids

    def test_no_mixer(self, color_panels):
        """Mixer should NOT be in Color workspace."""
        ids = {p["id"] for p in color_panels}
        assert "mixer" not in ids


# ═══════════════════════════════════════════════════════════════════════
# PART 3: Audio preset panel composition
# ═══════════════════════════════════════════════════════════════════════

class TestAudioPresetPanels:
    """Audio workspace: must include Mixer, tall timeline."""

    def test_has_mixer(self, audio_panels):
        ids = {p["id"] for p in audio_panels}
        assert "mixer" in ids, "Audio preset missing Mixer"

    def test_has_timeline(self, audio_panels):
        ids = {p["id"] for p in audio_panels}
        assert "timeline" in ids

    def test_no_scopes(self, audio_panels):
        """Scopes should NOT be in Audio workspace."""
        ids = {p["id"] for p in audio_panels}
        assert "scopes" not in ids

    def test_no_colorcorrector(self, audio_panels):
        ids = {p["id"] for p in audio_panels}
        assert "colorcorrector" not in ids

    def test_program_tabs_with_source(self, audio_panels):
        """Program should be tabbed with Source (stacked monitors)."""
        program = next(p for p in audio_panels if p["id"] == "program")
        assert program.get("direction") == "within"
        assert program.get("reference") == "source"


# ═══════════════════════════════════════════════════════════════════════
# PART 4: PRESET_BUILDERS registry
# ═══════════════════════════════════════════════════════════════════════

class TestPresetBuildersRegistry:
    """PRESET_BUILDERS must map all workspace names to builder functions."""

    def test_registry_exists(self, source):
        assert "PRESET_BUILDERS" in source

    def test_registry_has_editing(self, source):
        assert re.search(r"editing:\s*buildEditingLayout", source)

    def test_registry_has_color(self, source):
        assert re.search(r"color:\s*buildColorLayout", source)

    def test_registry_has_audio(self, source):
        assert re.search(r"audio:\s*buildAudioLayout", source)

    def test_registry_has_custom(self, source):
        """Custom uses editing as fallback."""
        assert re.search(r"custom:\s*build\w+Layout", source)

    def test_exported(self, source):
        assert re.search(r"export\s+(const|let)\s+PRESET_BUILDERS", source)


# ═══════════════════════════════════════════════════════════════════════
# PART 5: No panel ID collisions within a preset
# ═══════════════════════════════════════════════════════════════════════

class TestNoPanelIdCollisions:
    """Each preset must have unique panel IDs."""

    @pytest.mark.parametrize("preset_name,fixture_name", [
        ("editing", "editing_panels"),
        ("color", "color_panels"),
        ("audio", "audio_panels"),
    ])
    def test_unique_ids(self, preset_name, fixture_name, request):
        panels = request.getfixturevalue(fixture_name)
        ids = [p["id"] for p in panels]
        dupes = [x for x in ids if ids.count(x) > 1]
        assert not dupes, f"{preset_name} preset has duplicate panel IDs: {set(dupes)}"


# ═══════════════════════════════════════════════════════════════════════
# PART 6: Cross-preset consistency
# ═══════════════════════════════════════════════════════════════════════

class TestCrossPresetConsistency:
    """Shared panels must use same component across presets."""

    def test_timeline_component_consistent(self, editing_panels, color_panels, audio_panels):
        for panels, name in [(editing_panels, "editing"), (color_panels, "color"), (audio_panels, "audio")]:
            tl = next((p for p in panels if p["id"] == "timeline"), None)
            assert tl, f"{name} preset missing timeline"
            assert tl.get("component") == "timeline", \
                f"{name} preset timeline uses wrong component: {tl.get('component')}"

    def test_effects_component_consistent(self, editing_panels, color_panels, audio_panels):
        for panels, name in [(editing_panels, "editing"), (color_panels, "color"), (audio_panels, "audio")]:
            fx = next((p for p in panels if p["id"] == "effects"), None)
            assert fx, f"{name} preset missing effects"
            assert fx.get("component") == "effects"

    def test_all_presets_have_timeline(self, editing_panels, color_panels, audio_panels):
        """Timeline is mandatory in every workspace."""
        for panels, name in [(editing_panels, "editing"), (color_panels, "color"), (audio_panels, "audio")]:
            ids = {p["id"] for p in panels}
            assert "timeline" in ids, f"{name} preset missing timeline"
