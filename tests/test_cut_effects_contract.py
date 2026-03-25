"""
MARKER_EPSILON.T4: Effects setClipEffects/resetClipEffects contract tests.

Verifies the per-clip effects system (MARKER_W10.6):
1. ClipEffects type has correct fields with default ranges
2. DEFAULT_CLIP_EFFECTS provides neutral defaults
3. setClipEffects merges partial effects onto clip
4. resetClipEffects restores defaults
5. Effects are stored on clip.effects (optional field)

Source: client/src/store/useCutEditorStore.ts
"""

import re
from pathlib import Path

import pytest

STORE_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "store" / "useCutEditorStore.ts"


@pytest.fixture(scope="module")
def source():
    if not STORE_FILE.exists():
        pytest.skip(f"Store not found: {STORE_FILE}")
    return STORE_FILE.read_text()


class TestClipEffectsType:
    """Verify ClipEffects type definition."""

    def test_type_exported(self, source):
        """ClipEffects must be an exported type."""
        assert re.search(r"export\s+type\s+ClipEffects", source)

    def test_has_brightness(self, source):
        assert re.search(r"brightness:\s*number", source)

    def test_has_contrast(self, source):
        assert re.search(r"contrast:\s*number", source)

    def test_has_saturation(self, source):
        assert re.search(r"saturation:\s*number", source)

    def test_has_blur(self, source):
        assert re.search(r"blur:\s*number", source)

    def test_has_opacity(self, source):
        assert re.search(r"opacity:\s*number", source)


class TestDefaultClipEffects:
    """Verify DEFAULT_CLIP_EFFECTS neutral values."""

    def test_defaults_exported(self, source):
        """DEFAULT_CLIP_EFFECTS must be exported."""
        assert re.search(r"export\s+const\s+DEFAULT_CLIP_EFFECTS", source)

    def test_brightness_default_zero(self, source):
        """Brightness default = 0 (no change)."""
        # Find the DEFAULT block and check brightness: 0
        match = re.search(
            r"DEFAULT_CLIP_EFFECTS.*?brightness:\s*(\d+)", source, re.DOTALL
        )
        assert match and match.group(1) == "0"

    def test_saturation_default_one(self, source):
        """Saturation default = 1 (no change)."""
        match = re.search(
            r"DEFAULT_CLIP_EFFECTS.*?saturation:\s*(\d+)", source, re.DOTALL
        )
        assert match and match.group(1) == "1"

    def test_opacity_default_one(self, source):
        """Opacity default = 1 (fully visible)."""
        match = re.search(
            r"DEFAULT_CLIP_EFFECTS.*?opacity:\s*(\d+)", source, re.DOTALL
        )
        assert match and match.group(1) == "1"

    def test_blur_default_zero(self, source):
        """Blur default = 0 (no blur)."""
        match = re.search(
            r"DEFAULT_CLIP_EFFECTS.*?blur:\s*(\d+)", source, re.DOTALL
        )
        assert match and match.group(1) == "0"


class TestSetClipEffects:
    """Verify setClipEffects merges partial effects."""

    def test_action_exists(self, source):
        assert re.search(r"setClipEffects:\s*\(clipId", source)

    def test_accepts_partial_effects(self, source):
        """Must accept Partial<ClipEffects> for incremental updates."""
        assert re.search(r"Partial<ClipEffects>", source)

    def test_merges_with_existing(self, source):
        """Must spread existing effects before applying new ones."""
        # Pattern: { ...c.effects, ...effects } or similar merge
        assert re.search(r"\.\.\..*effects.*\.\.\.effects|\{.*c\.effects.*effects\}", source, re.DOTALL)

    def test_defaults_when_no_existing(self, source):
        """Must use DEFAULT_CLIP_EFFECTS when clip has no effects."""
        assert re.search(r"DEFAULT_CLIP_EFFECTS", source)

    def test_targets_correct_clip(self, source):
        """Must match clip by clipId."""
        assert re.search(r"c\.clip_id\s*===\s*clipId", source)


class TestResetClipEffects:
    """Verify resetClipEffects restores defaults."""

    def test_action_exists(self, source):
        assert re.search(r"resetClipEffects:\s*\(clipId", source)

    def test_sets_undefined_or_default(self, source):
        """Reset should set effects to undefined/DEFAULT or dispatch reset_effects op."""
        # Original: inline effects: undefined / DEFAULT_CLIP_EFFECTS
        # Post-A4.11: ops-based via applyTimelineOps with reset_effects op
        assert re.search(
            r"effects:\s*undefined|effects:\s*DEFAULT_CLIP_EFFECTS|op:\s*['\"]reset_effects['\"]",
            source,
        )


class TestClipHasEffectsField:
    """Verify Clip type includes optional effects field."""

    def test_clip_effects_optional(self, source):
        """Clip.effects must be optional (effects?: ClipEffects)."""
        assert re.search(r"effects\?:\s*ClipEffects", source)
