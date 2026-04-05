from __future__ import annotations

from pathlib import Path


def test_role_preview_registry_contains_expected_roles_and_system_assets() -> None:
    code = Path('client/src/components/mcc/mycoRolePreview.ts').read_text(encoding='utf-8')
    assert 'team_A/architect_primary.png' in code
    assert 'team_A/coder_coder1.png' in code
    assert 'team_A/coder_coder2.png' in code
    assert 'team_A/researcher_primary.png' in code
    assert 'team_A/scout_scout1.png' in code
    assert 'team_A/scout_scout2.png' in code
    assert 'team_A/scout_scout3.png' in code
    assert 'team_A/verifier_primary.png' in code
    assert 'architect_primary.apng' in code
    assert 'coder_coder1.apng' in code
    assert 'coder_coder2.apng' in code
    assert 'researcher_primary.apng' in code
    assert 'scout_scout1.apng' in code
    assert 'scout_scout2.apng' in code
    assert 'scout_scout3.apng' in code
    assert 'verifier_primary.apng' in code
    assert 'resolveMiniChatCompactAvatar' in code
    assert 'resolveMiniStatsCompactRoleAsset' in code
    assert 'resolveRoleMotionAsset' in code
    assert 'resolveSystemMycoAsset' in code


def test_mini_chat_compact_uses_role_preview_but_expanded_stays_system_myco() -> None:
    code = Path('client/src/components/mcc/MiniChat.tsx').read_text(encoding='utf-8')
    assert 'MARKER_168.MYCO.RUNTIME.MINI_CHAT_COMPACT_ROLE_PREVIEW.V1' in code
    assert 'MARKER_168.MYCO.RUNTIME.MINI_CHAT_COMPACT_HELPER_STAYS_MYCO.V1' in code
    assert "if (helperMode !== 'off')" in code
    assert 'MARKER_168.MYCO.RUNTIME.MINI_CHAT_COMPACT_ROLE_STICKY.V1' in code
    assert "if (helperMode === 'off' && (compactTriggerRoleAvatar || compactRoleAvatar))" in code
    assert 'alt="Architect avatar"' in code
    assert 'resolveSystemMycoAsset(mycoAvatarState)' in code


def test_mini_stats_compact_shows_role_preview_next_to_workflow_action() -> None:
    code = Path('client/src/components/mcc/MiniStats.tsx').read_text(encoding='utf-8')
    assert 'MARKER_168.MYCO.RUNTIME.MINI_STATS_COMPACT_ROLE_PREVIEW.V1' in code
    assert 'resolveMiniStatsCompactRoleAsset(context)' in code
    assert 'alt="Workflow role preview"' in code
    assert 'WORKFLOW' in code
