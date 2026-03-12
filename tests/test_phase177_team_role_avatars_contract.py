from pathlib import Path


def test_mini_stats_agent_performance_uses_prepared_role_assets() -> None:
    code = Path("client/src/components/mcc/MiniStats.tsx").read_text(encoding="utf-8")
    assert "MARKER_177.LOCALGUYS.AGENT_AVATAR_STATS.V1" in code
    assert "resolveAgentStatsAvatar" in code
    assert 'alt={`${agentType} avatar`}' in code
    assert "resolveRoleMotionAsset" in code
    assert "resolveRolePreviewAsset" in code
    assert "width: 26" in code
    assert "height: 26" in code
    assert "width: 21" in code
    assert "height: 21" in code
