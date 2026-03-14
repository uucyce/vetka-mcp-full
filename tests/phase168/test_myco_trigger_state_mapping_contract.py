from __future__ import annotations

import json
from pathlib import Path

ROOT = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03')
MAPPING = ROOT / 'artifacts' / 'myco_motion' / 'team_A' / 'trigger_state_mapping.json'


def test_mapping_manifest_exists_and_preserves_top_myco_channels():
    data = json.loads(MAPPING.read_text(encoding='utf-8'))

    assert data['marker'] == 'MARKER_168.MYCO.TRIGGER_STATE.MAPPING.V1'
    assert data['surface_policy']['top_avatar']['channel'] == 'system_myco'
    assert data['surface_policy']['top_avatar']['role_assets_allowed'] is False
    assert data['surface_policy']['top_hint']['channel'] == 'system_myco'
    assert data['surface_policy']['top_hint']['role_assets_allowed'] is False


def test_role_preview_surfaces_and_variants_are_declared():
    data = json.loads(MAPPING.read_text(encoding='utf-8'))

    assert data['surface_policy']['mini_chat_compact']['channel'] == 'role_preview'
    assert data['surface_policy']['mini_stats_expanded']['channel'] == 'role_preview'

    assert data['variant_assignment']['coder']['order'] == ['coder1', 'coder2']
    assert data['variant_assignment']['scout']['order'] == ['scout1', 'scout2', 'scout3']

    role_assets = data['role_assets']
    assert 'architect' in role_assets and 'primary' in role_assets['architect']
    assert 'coder' in role_assets and set(role_assets['coder']) == {'coder1', 'coder2'}
    assert 'researcher' in role_assets and 'primary' in role_assets['researcher']
    assert 'verifier' in role_assets and 'primary' in role_assets['verifier']
    assert 'scout' in role_assets and set(role_assets['scout']) == {'scout1', 'scout2', 'scout3'}

    for variants in role_assets.values():
        for asset_path in variants.values():
            assert (ROOT / asset_path).exists(), asset_path


def test_trigger_mapping_uses_expected_surface_routing():
    data = json.loads(MAPPING.read_text(encoding='utf-8'))
    triggers = {item['trigger']: item for item in data['triggers']}

    assert triggers['speaking']['target_surfaces'] == ['top_avatar', 'top_hint']
    assert triggers['workflow_selected']['target_surfaces'] == ['mini_stats_compact', 'mini_stats_expanded']
    assert triggers['model_selected']['target_surfaces'] == ['mini_chat_compact', 'mini_chat_expanded']
    assert triggers['parallel_role_active']['target_surfaces'] == ['mini_chat_expanded', 'mini_stats_expanded']
