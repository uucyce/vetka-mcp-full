"""
MARKER_B14 — Unit tests for compile_audio_transitions() and compile_audio_transition().

Tests cover:
  - acrossfade filter syntax
  - duration parameter mapping
  - curve selection (equal_power, linear, qsin, esin, tri, etc.)
  - non-audio transition types (dip_to_black → skipped)
  - empty input
  - mixed transition lists
"""
import pytest
from src.services.cut_render_pipeline import Transition
from src.services.cut_audio_engine import (
    compile_audio_transition,
    compile_audio_transitions,
    _audio_curve,
)


# ---------------------------------------------------------------------------
# _audio_curve helpers
# ---------------------------------------------------------------------------

class TestAudioCurve:
    def test_equal_power_maps_to_qsin(self):
        assert _audio_curve("equal_power") == "qsin"

    def test_linear_maps_to_tri(self):
        assert _audio_curve("linear") == "tri"

    def test_qsin_passthrough(self):
        assert _audio_curve("qsin") == "qsin"

    def test_tri_passthrough(self):
        assert _audio_curve("tri") == "tri"

    def test_esin_passthrough(self):
        assert _audio_curve("esin") == "esin"

    def test_hsin_passthrough(self):
        assert _audio_curve("hsin") == "hsin"

    def test_unknown_defaults_to_qsin(self):
        assert _audio_curve("unknown_curve") == "qsin"

    def test_empty_string_defaults_to_qsin(self):
        assert _audio_curve("") == "qsin"


# ---------------------------------------------------------------------------
# compile_audio_transition (single)
# ---------------------------------------------------------------------------

class TestCompileAudioTransition:
    def test_crossfade_equal_power_default(self):
        t = Transition(type="crossfade", duration_sec=1.0)
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=1.000:c1=qsin:c2=qsin"

    def test_crossfade_duration_1_5(self):
        t = Transition(type="crossfade", duration_sec=1.5, audio_curve="equal_power")
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=1.500:c1=qsin:c2=qsin"

    def test_crossfade_linear_curve(self):
        t = Transition(type="crossfade", duration_sec=2.0, audio_curve="linear")
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=2.000:c1=tri:c2=tri"

    def test_crossfade_esin_curve(self):
        t = Transition(type="crossfade", duration_sec=0.5, audio_curve="esin")
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=0.500:c1=esin:c2=esin"

    def test_dissolve_produces_acrossfade(self):
        # dissolve = same audio treatment as crossfade
        t = Transition(type="dissolve", duration_sec=1.0, audio_curve="equal_power")
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=1.000:c1=qsin:c2=qsin"

    def test_dip_to_black_no_audio_filter(self):
        t = Transition(type="dip_to_black", duration_sec=1.0)
        result = compile_audio_transition(t)
        assert result == ""

    def test_wipe_no_audio_filter(self):
        t = Transition(type="wipe", duration_sec=1.0)
        result = compile_audio_transition(t)
        assert result == ""

    def test_duration_precision_3_decimals(self):
        t = Transition(type="crossfade", duration_sec=0.333333)
        result = compile_audio_transition(t)
        assert "d=0.333" in result

    def test_short_duration(self):
        t = Transition(type="crossfade", duration_sec=0.1)
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=0.100:c1=qsin:c2=qsin"

    def test_long_duration(self):
        t = Transition(type="crossfade", duration_sec=5.0, audio_curve="linear")
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=5.000:c1=tri:c2=tri"

    def test_explicit_qsin_curve(self):
        t = Transition(type="crossfade", duration_sec=1.0, audio_curve="qsin")
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=1.000:c1=qsin:c2=qsin"

    def test_explicit_tri_curve(self):
        t = Transition(type="crossfade", duration_sec=1.0, audio_curve="tri")
        result = compile_audio_transition(t)
        assert result == "acrossfade=d=1.000:c1=tri:c2=tri"

    def test_result_starts_with_acrossfade(self):
        t = Transition(type="crossfade", duration_sec=1.0)
        assert compile_audio_transition(t).startswith("acrossfade=")

    def test_symmetric_curves_c1_eq_c2(self):
        # c1 and c2 must always be equal (mono crossfade, not stereo split)
        t = Transition(type="crossfade", duration_sec=1.0, audio_curve="esin")
        result = compile_audio_transition(t)
        # Parse: "acrossfade=d=1.000:c1=esin:c2=esin"
        # Split by ":" to get ["acrossfade=d=1.000", "c1=esin", "c2=esin"]
        parts = dict(kv.split("=", 1) for kv in result.split(":")[1:])  # skip first "acrossfade=d=..."
        assert parts["c1"] == parts["c2"]


# ---------------------------------------------------------------------------
# compile_audio_transitions (list)
# ---------------------------------------------------------------------------

class TestCompileAudioTransitions:
    def test_empty_list(self):
        assert compile_audio_transitions([]) == []

    def test_single_crossfade(self):
        transitions = [Transition(type="crossfade", duration_sec=1.0)]
        result = compile_audio_transitions(transitions)
        assert result == ["acrossfade=d=1.000:c1=qsin:c2=qsin"]

    def test_two_crossfades(self):
        transitions = [
            Transition(type="crossfade", duration_sec=1.0, audio_curve="equal_power"),
            Transition(type="crossfade", duration_sec=2.0, audio_curve="linear"),
        ]
        result = compile_audio_transitions(transitions)
        assert len(result) == 2
        assert result[0] == "acrossfade=d=1.000:c1=qsin:c2=qsin"
        assert result[1] == "acrossfade=d=2.000:c1=tri:c2=tri"

    def test_non_audio_transitions_skipped(self):
        transitions = [
            Transition(type="dip_to_black", duration_sec=1.0),
            Transition(type="wipe", duration_sec=0.5),
        ]
        result = compile_audio_transitions(transitions)
        assert result == []

    def test_mixed_types_only_audio_returned(self):
        transitions = [
            Transition(type="crossfade", duration_sec=1.0),
            Transition(type="dip_to_black", duration_sec=1.0),
            Transition(type="dissolve", duration_sec=0.5, audio_curve="linear"),
        ]
        result = compile_audio_transitions(transitions)
        assert len(result) == 2
        assert result[0] == "acrossfade=d=1.000:c1=qsin:c2=qsin"
        assert result[1] == "acrossfade=d=0.500:c1=tri:c2=tri"

    def test_returns_list_of_strings(self):
        transitions = [Transition(type="crossfade", duration_sec=1.0)]
        result = compile_audio_transitions(transitions)
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_all_curve_types(self):
        curves = ["equal_power", "linear", "qsin", "tri", "esin"]
        transitions = [
            Transition(type="crossfade", duration_sec=1.0, audio_curve=c)
            for c in curves
        ]
        result = compile_audio_transitions(transitions)
        assert len(result) == len(curves)
        for f in result:
            assert f.startswith("acrossfade=")
