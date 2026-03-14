"""
Phase 180 — DAG Project API tests (180.17).

Tests the asset classification logic and DAG structure.

MARKER_180.17_TESTS
"""
import pytest


# Import the classification function directly
from src.api.routes.cut_routes import _classify_asset_cluster


class TestAssetClassification:
    """Test _classify_asset_cluster logic."""

    def test_character_by_node_type(self):
        node = {"node_type": "character", "metadata": {}}
        assert _classify_asset_cluster(node) == "character"

    def test_character_by_tag(self):
        node = {"node_type": "unknown", "metadata": {"tags": ["character"]}}
        assert _classify_asset_cluster(node) == "character"

    def test_location_by_node_type(self):
        node = {"node_type": "location", "metadata": {}}
        assert _classify_asset_cluster(node) == "location"

    def test_scene_is_location(self):
        node = {"node_type": "scene", "metadata": {}}
        assert _classify_asset_cluster(node) == "location"

    def test_take_by_node_type(self):
        node = {"node_type": "take", "metadata": {}}
        assert _classify_asset_cluster(node) == "take"

    def test_clip_is_take(self):
        node = {"node_type": "clip", "metadata": {}}
        assert _classify_asset_cluster(node) == "take"

    def test_music_by_extension_mp3(self):
        node = {"node_type": "asset", "metadata": {"source_path": "/audio/track.mp3", "tags": []}}
        assert _classify_asset_cluster(node) == "music"

    def test_music_by_extension_wav(self):
        node = {"node_type": "asset", "metadata": {"source_path": "/audio/ambient.wav", "tags": []}}
        assert _classify_asset_cluster(node) == "music"

    def test_sfx_by_extension_and_tag(self):
        node = {"node_type": "asset", "metadata": {"source_path": "/sfx/bang.wav", "tags": ["sfx"]}}
        assert _classify_asset_cluster(node) == "sfx"

    def test_graphics_by_extension_png(self):
        node = {"node_type": "asset", "metadata": {"source_path": "/gfx/title.png", "tags": []}}
        assert _classify_asset_cluster(node) == "graphics"

    def test_graphics_by_extension_psd(self):
        node = {"node_type": "asset", "metadata": {"source_path": "/design/comp.psd", "tags": []}}
        assert _classify_asset_cluster(node) == "graphics"

    def test_unknown_fallback(self):
        node = {"node_type": "unknown", "metadata": {"tags": []}}
        assert _classify_asset_cluster(node) == "other"

    def test_no_metadata(self):
        node = {"node_type": "thing", "metadata": {}}
        assert _classify_asset_cluster(node) == "other"

    def test_music_tag_overrides_video(self):
        """Audio tag should classify as music even without audio extension."""
        node = {"node_type": "asset", "metadata": {"source_path": "/misc/file.dat", "tags": ["music"]}}
        assert _classify_asset_cluster(node) == "music"

    def test_location_tag(self):
        node = {"node_type": "asset", "metadata": {"tags": ["location", "outdoor"]}}
        assert _classify_asset_cluster(node) == "location"


class TestDAGClusterTypes:
    """Validate cluster types match Architecture doc §2.2."""

    EXPECTED_CLUSTERS = {"character", "location", "take", "dub", "music", "sfx", "graphics", "other"}

    def test_all_cluster_types_defined(self):
        from src.api.routes.cut_routes import _DAG_CLUSTER_TYPES
        assert _DAG_CLUSTER_TYPES == self.EXPECTED_CLUSTERS

    def test_cluster_count(self):
        assert len(self.EXPECTED_CLUSTERS) == 8

    def test_no_duplicate_clusters(self):
        assert len(self.EXPECTED_CLUSTERS) == len(set(self.EXPECTED_CLUSTERS))
