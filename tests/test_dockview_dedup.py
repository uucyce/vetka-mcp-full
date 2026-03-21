"""
MARKER_W6.DEDUP: Tests for dockview layout deduplication guard.

Prevents corrupted saved layouts with duplicate panel IDs
from being restored, which causes duplicate transport bars.
"""
import pytest
import json


# ── Simulated dockview layout validation ─────────────────────

def validate_layout(layout_json: dict) -> tuple[bool, str]:
    """Validate a serialized dockview layout. Returns (ok, reason)."""
    panels = layout_json.get('panels', {}).get('data', [])
    if not isinstance(panels, list):
        return True, 'ok'  # no panels data to validate
    ids = [p.get('id') for p in panels if p.get('id')]
    unique = set(ids)
    if len(ids) != len(unique):
        dupes = [x for x in ids if ids.count(x) > 1]
        return False, f'duplicate panels: {set(dupes)}'
    return True, 'ok'


def deduplicate_panels(layout_json: dict) -> dict:
    """Remove duplicate panels, keeping the first occurrence."""
    panels = layout_json.get('panels', {}).get('data', [])
    if not isinstance(panels, list):
        return layout_json
    seen = set()
    deduped = []
    for p in panels:
        pid = p.get('id')
        if pid and pid in seen:
            continue
        seen.add(pid)
        deduped.append(p)
    result = dict(layout_json)
    result['panels'] = dict(result.get('panels', {}))
    result['panels']['data'] = deduped
    return result


# ── Test fixtures ────────────────────────────────────────────

@pytest.fixture
def clean_layout():
    return {
        'panels': {
            'data': [
                {'id': 'project', 'component': 'project'},
                {'id': 'source', 'component': 'source'},
                {'id': 'program', 'component': 'program'},
                {'id': 'timeline', 'component': 'timeline'},
            ]
        }
    }


@pytest.fixture
def corrupt_layout():
    return {
        'panels': {
            'data': [
                {'id': 'project', 'component': 'project'},
                {'id': 'source', 'component': 'source'},
                {'id': 'program', 'component': 'program'},
                {'id': 'source', 'component': 'source'},  # DUPLICATE
                {'id': 'timeline', 'component': 'timeline'},
            ]
        }
    }


@pytest.fixture
def empty_layout():
    return {'panels': {'data': []}}


# ── Tests ────────────────────────────────────────────────────


class TestValidateLayout:
    def test_clean_layout_passes(self, clean_layout):
        ok, reason = validate_layout(clean_layout)
        assert ok is True

    def test_corrupt_layout_fails(self, corrupt_layout):
        ok, reason = validate_layout(corrupt_layout)
        assert ok is False
        assert 'source' in reason

    def test_empty_layout_passes(self, empty_layout):
        ok, _ = validate_layout(empty_layout)
        assert ok is True

    def test_no_panels_key_passes(self):
        ok, _ = validate_layout({})
        assert ok is True

    def test_triple_duplicate(self):
        layout = {
            'panels': {
                'data': [
                    {'id': 'source', 'component': 'source'},
                    {'id': 'source', 'component': 'source'},
                    {'id': 'source', 'component': 'source'},
                ]
            }
        }
        ok, reason = validate_layout(layout)
        assert ok is False


class TestDeduplicatePanels:
    def test_dedup_removes_duplicates(self, corrupt_layout):
        result = deduplicate_panels(corrupt_layout)
        ids = [p['id'] for p in result['panels']['data']]
        assert ids == ['project', 'source', 'program', 'timeline']

    def test_dedup_clean_is_noop(self, clean_layout):
        result = deduplicate_panels(clean_layout)
        ids = [p['id'] for p in result['panels']['data']]
        assert len(ids) == 4

    def test_dedup_preserves_order(self, corrupt_layout):
        """First occurrence wins."""
        result = deduplicate_panels(corrupt_layout)
        ids = [p['id'] for p in result['panels']['data']]
        assert ids.index('source') < ids.index('program')


class TestLayoutRoundTrip:
    def test_json_serialization(self, clean_layout):
        """Layout survives JSON round-trip."""
        serialized = json.dumps(clean_layout)
        restored = json.loads(serialized)
        ok, _ = validate_layout(restored)
        assert ok is True

    def test_corrupt_detected_after_roundtrip(self, corrupt_layout):
        serialized = json.dumps(corrupt_layout)
        restored = json.loads(serialized)
        ok, _ = validate_layout(restored)
        assert ok is False
