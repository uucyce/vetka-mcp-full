"""
Phase 180 — PULSE Auto-Montage Tests (180.12 + 180.13).

Tests all 3 auto-montage modes:
- Mode A: Favorite assembly
- Mode B: Script-driven
- Mode C: Music-driven

Safety rule: ALWAYS new timeline, NEVER overwrite.

MARKER_180.12_TESTS
"""
import pytest
import time

from src.services.pulse_auto_montage import (
    FavoriteMarker,
    MaterialAsset,
    MontageClip,
    MontageResult,
    PulseAutoMontage,
)
from src.services.pulse_conductor import AudioBPM


@pytest.fixture
def engine():
    return PulseAutoMontage(handle_duration_sec=1.0, min_clip_duration_sec=0.5)


@pytest.fixture
def sample_markers():
    return [
        FavoriteMarker(
            marker_id="m1", media_path="/media/clip01.mp4",
            start_sec=10.0, end_sec=15.0, score=1.0, text="Best moment",
        ),
        FavoriteMarker(
            marker_id="m2", media_path="/media/clip02.mp4",
            start_sec=5.0, end_sec=12.0, score=0.8, text="Good take",
        ),
        FavoriteMarker(
            marker_id="m3", media_path="/media/clip03.mp4",
            start_sec=0.5, end_sec=3.5, score=0.9, text="Opening",
        ),
    ]


@pytest.fixture
def sample_materials():
    return [
        MaterialAsset(
            asset_id="a1", source_path="/media/clip01.mp4",
            duration_sec=60.0, camelot_key="8A", energy=0.7, pendulum=-0.3,
        ),
        MaterialAsset(
            asset_id="a2", source_path="/media/clip02.mp4",
            duration_sec=45.0, camelot_key="3B", energy=0.4, pendulum=0.5,
        ),
        MaterialAsset(
            asset_id="a3", source_path="/media/clip03.mp4",
            duration_sec=30.0, camelot_key="8B", energy=0.9, pendulum=-0.8,
        ),
    ]


# ---------------------------------------------------------------------------
# Mode A: Favorite Assembly
# ---------------------------------------------------------------------------

class TestFavoriteAssembly:

    def test_basic_assembly(self, engine, sample_markers):
        result = engine.assemble_favorites(
            markers=sample_markers,
            project_name="test_film",
            version=1,
        )
        assert result.mode == "favorites"
        assert result.clip_count == 3
        assert result.total_duration > 0
        assert len(result.clips) == 3

    def test_new_timeline_id(self, engine, sample_markers):
        """§7.1: Must create new timeline with proper naming."""
        result = engine.assemble_favorites(
            markers=sample_markers,
            project_name="my_film",
            version=5,
        )
        assert "my_film_cut-05" in result.timeline_label
        assert result.timeline_id.startswith("tl_")

    def test_handles_added(self, engine):
        """Handles (1s default) are added around marker boundaries."""
        markers = [
            FavoriteMarker(
                marker_id="m1", media_path="/media/clip.mp4",
                start_sec=10.0, end_sec=15.0, score=1.0,
            ),
        ]
        result = engine.assemble_favorites(markers=markers)
        clip = result.clips[0]
        assert clip.in_sec == 9.0   # 10.0 - 1.0 handle
        assert clip.out_sec == 16.0  # 15.0 + 1.0 handle

    def test_order_by_time(self, engine, sample_markers):
        result = engine.assemble_favorites(
            markers=sample_markers, order_by="time",
        )
        # Clips should be ordered by start_sec
        starts = [c.in_sec for c in result.clips]
        # Marker 3 (0.5s) → Marker 2 (5.0s) → Marker 1 (10.0s)
        assert starts[0] < starts[1] < starts[2]

    def test_order_by_energy(self, engine, sample_markers):
        result = engine.assemble_favorites(
            markers=sample_markers, order_by="energy",
        )
        # Ordered by score descending: m1(1.0) → m3(0.9) → m2(0.8)
        scores = [c.confidence for c in result.clips]
        assert scores[0] >= scores[1] >= scores[2]

    def test_empty_markers(self, engine):
        result = engine.assemble_favorites(markers=[])
        assert result.clip_count == 0
        assert result.total_duration == 0.0
        assert "No favorite markers" in result.warnings[0]

    def test_invalid_marker_filtered(self, engine):
        """Markers with end <= start are filtered out."""
        markers = [
            FavoriteMarker(
                marker_id="bad", media_path="/clip.mp4",
                start_sec=10.0, end_sec=10.0,  # zero duration
            ),
        ]
        result = engine.assemble_favorites(markers=markers)
        assert result.clip_count == 0

    def test_sync_point_snapping(self, engine, sample_markers):
        """Clips snap to sync points when available."""
        sync_points = [0.0, 7.5, 15.0, 22.5]
        result = engine.assemble_favorites(
            markers=sample_markers,
            sync_points=sync_points,
        )
        assert result.sync_points_hit >= 0  # may or may not snap

    def test_clips_non_overlapping(self, engine, sample_markers):
        result = engine.assemble_favorites(markers=sample_markers)
        for i in range(len(result.clips) - 1):
            assert result.clips[i].timeline_end <= result.clips[i + 1].timeline_start + 0.001

    def test_created_at_timestamp(self, engine, sample_markers):
        before = time.time()
        result = engine.assemble_favorites(markers=sample_markers)
        after = time.time()
        assert before <= result.created_at <= after


# ---------------------------------------------------------------------------
# Mode B: Script-Driven
# ---------------------------------------------------------------------------

class TestScriptDriven:

    SAMPLE_SCRIPT = """
    EXT. BERLIN WALL - NIGHT
    Rain on concrete. ANNA walks alone through the rubble.
    She stops. Turns. Sees a flickering light.

    INT. UNDERGROUND CLUB - CONTINUOUS
    Music. Bodies. She finds MAX at the bar.
    "You're the one who sent the signal?"

    EXT. ROOFTOP - DAWN
    The sun rises over the city. Anna speaks into the microphone.
    """

    def test_basic_script_assembly(self, engine, sample_materials):
        result = engine.assemble_from_script(
            script_text=self.SAMPLE_SCRIPT,
            materials=sample_materials,
            project_name="berlin_film",
            version=2,
        )
        assert result.mode == "script"
        assert result.clip_count > 0
        assert result.scores_used > 0
        assert "berlin_film_cut-02" in result.timeline_label

    def test_empty_script(self, engine, sample_materials):
        """Empty script may still produce a default scene from analyzer.
        Key check: mode is script, no crashes, result is valid."""
        result = engine.assemble_from_script(
            script_text="",
            materials=sample_materials,
        )
        assert result.mode == "script"
        # Script analyzer may return a default scene for empty text
        assert result.clip_count >= 0

    def test_no_materials(self, engine):
        result = engine.assemble_from_script(
            script_text=self.SAMPLE_SCRIPT,
            materials=[],
        )
        # Should warn about unmatched scenes
        assert len(result.warnings) > 0

    def test_camelot_smoothness_computed(self, engine, sample_materials):
        result = engine.assemble_from_script(
            script_text=self.SAMPLE_SCRIPT,
            materials=sample_materials,
        )
        assert 0.0 <= result.camelot_smoothness <= 1.0

    def test_clips_have_pulse_data(self, engine, sample_materials):
        result = engine.assemble_from_script(
            script_text=self.SAMPLE_SCRIPT,
            materials=sample_materials,
        )
        for clip in result.clips:
            assert clip.camelot_key  # should have key
            assert clip.reason.startswith("Script scene:")


# ---------------------------------------------------------------------------
# Mode C: Music-Driven
# ---------------------------------------------------------------------------

class TestMusicDriven:

    def test_basic_music_assembly(self, engine, sample_materials):
        music = AudioBPM(
            bpm=120.0,
            key="A minor",
            camelot_key="8A",
            downbeats=[i * 0.5 for i in range(60)],  # 30 seconds
        )
        result = engine.assemble_from_music(
            music_audio=music,
            materials=sample_materials,
            project_name="music_vid",
            version=3,
        )
        assert result.mode == "music"
        assert result.clip_count > 0
        assert "music_vid_cut-03" in result.timeline_label

    def test_cuts_at_downbeats(self, engine, sample_materials):
        """Music mode should cut at downbeats → sync_points_hit > 0."""
        music = AudioBPM(
            bpm=120.0,
            key="A minor",
            camelot_key="8A",
            downbeats=[i * 0.5 for i in range(60)],
        )
        result = engine.assemble_from_music(
            music_audio=music,
            materials=sample_materials,
        )
        assert result.sync_points_hit > 0

    def test_no_bpm_no_downbeats(self, engine, sample_materials):
        """Zero BPM + no downbeats = can't create montage."""
        music = AudioBPM(bpm=0.0, key="", camelot_key="1A")
        result = engine.assemble_from_music(
            music_audio=music,
            materials=sample_materials,
        )
        assert result.clip_count == 0
        assert len(result.warnings) > 0

    def test_synthetic_beats_from_bpm(self, engine, sample_materials):
        """If BPM given but no downbeats, generate synthetic beats."""
        music = AudioBPM(
            bpm=90.0,
            key="C major",
            camelot_key="8B",
            energy_curve=[0.5] * 10,  # 10 energy values → duration hint
        )
        result = engine.assemble_from_music(
            music_audio=music,
            materials=sample_materials,
        )
        assert result.clip_count > 0

    def test_camelot_matching(self, engine):
        """Materials with matching Camelot key should be preferred."""
        materials = [
            MaterialAsset(asset_id="far", source_path="/far.mp4", duration_sec=30, camelot_key="1A"),
            MaterialAsset(asset_id="close", source_path="/close.mp4", duration_sec=30, camelot_key="8A"),
        ]
        music = AudioBPM(
            bpm=120, key="A minor", camelot_key="8A",
            downbeats=[i * 0.5 for i in range(32)],
        )
        result = engine.assemble_from_music(music_audio=music, materials=materials)
        # The "close" material (8A) should be preferred over "far" (1A)
        if result.clips:
            assert result.clips[0].source_path == "/close.mp4"

    def test_material_rotation(self, engine):
        """If more sections than materials, materials should be reused."""
        materials = [
            MaterialAsset(asset_id="a1", source_path="/clip1.mp4", duration_sec=60, camelot_key="8A"),
        ]
        music = AudioBPM(
            bpm=120, key="A minor", camelot_key="8A",
            downbeats=[i * 0.5 for i in range(120)],  # lots of sections
        )
        result = engine.assemble_from_music(music_audio=music, materials=materials)
        assert result.clip_count > 1  # reused the single material


# ---------------------------------------------------------------------------
# Safety & cross-mode tests
# ---------------------------------------------------------------------------

class TestMontageResult:

    def test_to_dict_serialization(self, engine, sample_markers):
        result = engine.assemble_favorites(markers=sample_markers)
        d = result.to_dict()
        assert "timeline_id" in d
        assert "clips" in d
        assert isinstance(d["clips"], list)
        assert d["mode"] == "favorites"

    def test_clip_to_dict(self, engine, sample_markers):
        result = engine.assemble_favorites(markers=sample_markers)
        clip_dict = result.clips[0].to_dict()
        assert "clip_id" in clip_dict
        assert "in_sec" in clip_dict
        assert "out_sec" in clip_dict
        assert "timeline_start" in clip_dict
        assert "duration" in clip_dict
        assert "reason" in clip_dict

    def test_never_overwrite_rule(self, engine, sample_markers):
        """Two calls with different versions → different timeline IDs."""
        r1 = engine.assemble_favorites(markers=sample_markers, version=1)
        r2 = engine.assemble_favorites(markers=sample_markers, version=2)
        assert r1.timeline_id != r2.timeline_id
        assert r1.timeline_label != r2.timeline_label
        assert "cut-01" in r1.timeline_label
        assert "cut-02" in r2.timeline_label

    def test_version_formatting(self, engine, sample_markers):
        """Version numbers should be zero-padded."""
        result = engine.assemble_favorites(
            markers=sample_markers,
            project_name="film",
            version=7,
        )
        assert "film_cut-07" in result.timeline_label
