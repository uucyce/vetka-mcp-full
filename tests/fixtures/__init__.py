"""
Shared test fixtures for VETKA CUT QA agents.

Eliminates duplication across 15+ contract test files.
Import from tests.fixtures instead of redefining in each test module.

Usage:
    from tests.fixtures.cut_paths import ROOT, CLIENT_SRC, CUT_COMPONENTS
    from tests.fixtures.cut_helpers import read_source, find_pattern, strip_comments
    from tests.fixtures.cut_timeline_factory import make_clip, make_lane, make_timeline_state
    from tests.fixtures.cut_monochrome import is_grey, is_allowed_red, parse_rgb, normalise_hex
"""
