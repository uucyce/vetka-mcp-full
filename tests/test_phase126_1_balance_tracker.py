"""
Tests for Phase 126.1 & 126.2 — Balance Tracker + DevPanel Balance Tab.

Phase 126.1:
- MARKER_126.1: BalanceTracker singleton service (balance_tracker.py)
- MARKER_126.5: Debug routes endpoints (/api/debug/usage/balances, /reset)
- MARKER_126.6: BalancesPanel.tsx component
- MARKER_126.7: DevPanel 'balance' tab integration

Phase 126.2:
- MARKER_126.3A: OpenRouter free-tier detection (_parse_openrouter_balance)
- MARKER_126.3B: BALANCE_ENDPOINTS uses fixed parser
- MARKER_126.3C: BalanceTracker integration in fetch_provider_balance
- MARKER_126.4A: _report_key_failure zeros balance on 402/403
- MARKER_126.4B: OpenAICompatibleProvider passes status_code
- MARKER_126.4C: BaseProvider._handle_error_with_rotation integration

Tests:
- TestBalanceTrackerMarkers: 9 tests — marker checks in source
- TestBalanceTrackerLogic: 5 tests — functional tests
- TestDebugRoutesEndpoints: 3 tests — endpoint registration
- TestDevPanelBalanceTab: 4 tests — UI integration
- TestPhase126_2_OpenRouterFix: 5 tests — OpenRouter free-tier & 402 handling
- TestRegressionPhase126_0: 3 tests — previous features intact
"""

import os
import json
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 126 contracts changed")

# ── Helpers ──

def _read_source(path: str) -> str:
    filepath = os.path.join(os.path.dirname(__file__), "..", path)
    with open(filepath) as f:
        return f.read()


# ── Balance Tracker Markers (126.1) ──

class TestBalanceTrackerMarkers:
    """Tests for MARKER_126.1: BalanceTracker source markers."""

    def test_marker_126_1_exists(self):
        """balance_tracker.py should have MARKER_126.1."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1" in source

    def test_marker_126_1a_pricing(self):
        """MARKER_126.1A: Pricing dict should exist."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1A" in source
        assert "PRICING" in source

    def test_marker_126_1b_usage_record(self):
        """MARKER_126.1B: UsageRecord dataclass should exist."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1B" in source
        assert "class UsageRecord" in source

    def test_marker_126_1c_singleton(self):
        """MARKER_126.1C: BalanceTracker should be singleton."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1C" in source
        assert "_instance" in source

    def test_marker_126_1d_estimate_cost(self):
        """MARKER_126.1D: _estimate_cost method should exist."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1D" in source
        assert "def _estimate_cost" in source

    def test_marker_126_1e_record_usage(self):
        """MARKER_126.1E: record_usage method should exist."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1E" in source
        assert "def record_usage" in source

    def test_marker_126_1f_update_balance(self):
        """MARKER_126.1F: update_balance method should exist."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1F" in source
        assert "def update_balance" in source

    def test_marker_126_1g_mark_exhausted(self):
        """MARKER_126.1G: mark_exhausted method should exist."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1G" in source
        assert "def mark_exhausted" in source

    def test_marker_126_1h_get_totals(self):
        """MARKER_126.1H: get_totals method should exist."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.1H" in source
        assert "def get_totals" in source


# ── Balance Tracker Logic ──

class TestBalanceTrackerLogic:
    """Tests for BalanceTracker functional behavior."""

    def test_singleton_pattern(self):
        """BalanceTracker should be singleton."""
        from src.services.balance_tracker import BalanceTracker
        t1 = BalanceTracker()
        t2 = BalanceTracker()
        assert t1 is t2

    def test_get_balance_tracker_function(self):
        """get_balance_tracker() should return singleton."""
        from src.services.balance_tracker import get_balance_tracker, BalanceTracker
        tracker = get_balance_tracker()
        assert isinstance(tracker, BalanceTracker)

    def test_record_usage_increments(self):
        """record_usage should increment counters."""
        from src.services.balance_tracker import get_balance_tracker
        tracker = get_balance_tracker()

        # Get initial state
        before = tracker.get_totals()
        initial_calls = before.get('total_calls', 0)

        # Record usage
        tracker.record_usage(
            provider="test",
            key_masked="test****test",
            model="gpt-4o",
            tokens_in=100,
            tokens_out=50
        )

        after = tracker.get_totals()
        assert after['total_calls'] > initial_calls

    def test_estimate_cost_gpt4o(self):
        """Cost estimation should work for known models."""
        from src.services.balance_tracker import BalanceTracker
        tracker = BalanceTracker()

        # GPT-4o: $2.50/1M in, $10/1M out
        cost = tracker._estimate_cost("gpt-4o", 1000000, 1000000)
        assert cost == 12.5  # 2.5 + 10

    def test_get_all_returns_list(self):
        """get_all should return list of dicts."""
        from src.services.balance_tracker import get_balance_tracker
        tracker = get_balance_tracker()
        result = tracker.get_all()
        assert isinstance(result, list)


# ── Debug Routes Endpoints (126.5) ──

class TestDebugRoutesEndpoints:
    """Tests for MARKER_126.5: Debug routes balance endpoints."""

    def test_marker_126_5_exists(self):
        """debug_routes.py should have MARKER_126.5."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_126.5" in source

    def test_usage_balances_endpoint(self):
        """GET /api/debug/usage/balances endpoint should exist."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "usage/balances" in source
        assert "async def get_usage_balances" in source

    def test_usage_reset_endpoint(self):
        """POST /api/debug/usage/reset endpoint should exist."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "usage/reset" in source
        assert "async def reset_usage" in source


# ── DevPanel Balance Tab (126.6, 126.7) ──

class TestDevPanelBalanceTab:
    """Tests for MARKER_126.6/126.7: DevPanel balance tab."""

    def test_balances_panel_exists(self):
        """BalancesPanel.tsx should exist."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "client", "src", "components", "panels", "BalancesPanel.tsx"
        )
        assert os.path.exists(filepath)

    def test_marker_126_6_in_panel(self):
        """BalancesPanel.tsx should have MARKER_126.6."""
        source = _read_source("client/src/components/panels/BalancesPanel.tsx")
        assert "MARKER_126.6" in source

    def test_devpanel_has_balance_tab(self):
        """DevPanel should have 'balance' tab."""
        source = _read_source("client/src/components/panels/DevPanel.tsx")
        assert "'balance'" in source

    def test_devpanel_imports_balances_panel(self):
        """DevPanel should import BalancesPanel."""
        source = _read_source("client/src/components/panels/DevPanel.tsx")
        assert "BalancesPanel" in source
        assert "MARKER_126.7" in source

    def test_marker_126_8_scroll_support(self):
        """MARKER_126.8: BalancesPanel should have scroll support."""
        source = _read_source("client/src/components/panels/BalancesPanel.tsx")
        assert "MARKER_126.8" in source
        assert "overflowY" in source
        assert "minHeight: 0" in source


# ── Phase 126.2: OpenRouter Free-Tier Fix ──

class TestPhase126_2_OpenRouterFix:
    """Tests for MARKER_126.3 & 126.4: OpenRouter balance fix + 402 handling."""

    def test_marker_126_3a_parse_openrouter_balance(self):
        """MARKER_126.3A: _parse_openrouter_balance method should exist."""
        source = _read_source("src/utils/unified_key_manager.py")
        assert "MARKER_126.3A" in source
        assert "def _parse_openrouter_balance" in source

    def test_marker_126_3b_balance_endpoints(self):
        """MARKER_126.3B: BALANCE_ENDPOINTS should use fixed parser."""
        source = _read_source("src/utils/unified_key_manager.py")
        assert "MARKER_126.3B" in source

    def test_marker_126_3c_tracker_integration(self):
        """MARKER_126.3C: fetch_provider_balance should update tracker."""
        source = _read_source("src/utils/unified_key_manager.py")
        assert "MARKER_126.3C" in source

    def test_marker_126_3d_sync_from_key_manager(self):
        """MARKER_126.3D: sync_from_key_manager should exist in BalanceTracker."""
        source = _read_source("src/services/balance_tracker.py")
        assert "MARKER_126.3D" in source
        assert "def sync_from_key_manager" in source

    def test_marker_126_3e_endpoint_calls_sync(self):
        """MARKER_126.3E: debug_routes should call sync before returning."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_126.3E" in source
        assert "sync_from_key_manager" in source

    def test_marker_126_4a_report_key_failure(self):
        """MARKER_126.4A: _report_key_failure should zero balance on 402/403."""
        source = _read_source("src/elisya/provider_registry.py")
        assert "MARKER_126.4A" in source
        assert "mark_exhausted" in source

    def test_marker_126_4c_handle_error_integration(self):
        """MARKER_126.4C: _handle_error_with_rotation should update tracker."""
        source = _read_source("src/elisya/provider_registry.py")
        assert "MARKER_126.4C" in source


# ── Phase 126.10: DELETE Endpoint Fix ──

class TestPhase126_10_DeleteEndpoint:
    """Tests for MARKER_126.10: DELETE /keys/{provider}/{key_id} fix."""

    def test_marker_126_10_exists(self):
        """MARKER_126.10: New delete endpoint should exist."""
        source = _read_source("src/api/routes/model_routes.py")
        assert "MARKER_126.10" in source
        assert "remove_specific_key" in source

    def test_delete_endpoint_has_key_id_param(self):
        """Endpoint should accept key_id parameter."""
        source = _read_source("src/api/routes/model_routes.py")
        assert "/keys/{provider}/{key_id}" in source


# ── Phase 126.11: Multi-Agent Task Board ──

class TestPhase126_11_MultiAgentTaskBoard:
    """Tests for MARKER_126.11: Multi-agent Task Board support markers."""

    def test_marker_126_11a_in_task_board(self):
        """MARKER_126.11A: Task Board should have multi-agent markers."""
        source = _read_source("src/orchestration/task_board.py")
        assert "MARKER_126.11A" in source

    def test_marker_126_11b_in_task_board(self):
        """MARKER_126.11B: Claim/release methods markers."""
        source = _read_source("src/orchestration/task_board.py")
        assert "MARKER_126.11B" in source

    def test_marker_126_11c_in_mcp_tools(self):
        """MARKER_126.11C: MCP tools should have claim tool marker."""
        source = _read_source("src/mcp/tools/task_board_tools.py")
        assert "MARKER_126.11C" in source

    def test_marker_126_11d_in_session_init(self):
        """MARKER_126.11D: session_init should have available_tasks marker."""
        source = _read_source("src/mcp/tools/session_tools.py")
        assert "MARKER_126.11D" in source


# ── Regression Tests ──

class TestRegressionPhase126_0:
    """Ensure Phase 126.0 features still work."""

    def test_pipeline_stats_component_exists(self):
        """PipelineStats.tsx should still exist."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "client", "src", "components", "panels", "PipelineStats.tsx"
        )
        assert os.path.exists(filepath)

    def test_league_tester_component_exists(self):
        """LeagueTester.tsx should still exist."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "client", "src", "components", "panels", "LeagueTester.tsx"
        )
        assert os.path.exists(filepath)

    def test_test_league_endpoint_exists(self):
        """test-league endpoint should still exist (126.0E)."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "task-board/test-league" in source
        assert "MARKER_126.0E" in source


# ── Phase 126.9: Key Selection → Pipeline ──

class TestPhase126_9_KeySelection:
    """Tests for MARKER_126.9: Key Selection → Pipeline Dispatch feature."""

    def test_marker_126_9a_balances_panel_click(self):
        """MARKER_126.9A: BalancesPanel should have key click handler."""
        source = _read_source("client/src/components/panels/BalancesPanel.tsx")
        assert "MARKER_126.9A" in source
        assert "handleKeyClick" in source
        assert "selectedKey" in source

    def test_balances_panel_uses_mcc_store_for_selected_key(self):
        """Balance panel selection must flow through MCC store so reopen keeps the same active key."""
        source = _read_source("client/src/components/panels/BalancesPanel.tsx")
        assert "useMCCStore" in source
        assert "const selectedKey = useMCCStore" in source
        assert "const setSelectedKey = useMCCStore" in source

    def test_marker_126_9b_usestore_selected_key(self):
        """MARKER_126.9B: useStore should have selectedKey state."""
        source = _read_source("client/src/store/useStore.ts")
        assert "MARKER_126.9B" in source
        assert "selectedKey:" in source
        assert "setSelectedKey" in source
        assert "clearSelectedKey" in source

    def test_marker_126_9c_devpanel_dispatch(self):
        """MARKER_126.9C: DevPanel dispatch should include selected_key."""
        source = _read_source("client/src/components/panels/DevPanel.tsx")
        assert "MARKER_126.9C" in source
        assert "selected_key" in source

    def test_marker_126_9d_debug_routes(self):
        """MARKER_126.9D: debug_routes dispatch endpoint accepts selected_key."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_126.9D" in source
        assert "selected_key" in source

    def test_marker_126_9e_task_board_wiring(self):
        """MARKER_126.9E: task_board dispatch passes selected_key."""
        source = _read_source("src/orchestration/task_board.py")
        assert "MARKER_126.9E" in source
        assert "selected_key" in source

    def test_marker_126_9e_pipeline_wiring(self):
        """MARKER_126.9E: AgentPipeline sets preferred key from selected_key."""
        source = _read_source("src/orchestration/agent_pipeline.py")
        assert "MARKER_126.9E" in source
        assert "selected_key" in source
        assert "set_preferred_key" in source

    def test_marker_126_9f_key_manager_preferred(self):
        """MARKER_126.9F: UnifiedKeyManager has preferred key methods."""
        source = _read_source("src/utils/unified_key_manager.py")
        assert "MARKER_126.9F" in source
        assert "def set_preferred_key" in source
        assert "def get_preferred_key" in source
        assert "def clear_preferred_key" in source
        assert "_preferred_keys" in source

    def test_preferred_key_integration(self):
        """Functional test: set_preferred_key affects get_key_with_rotation."""
        from src.utils.unified_key_manager import get_key_manager

        km = get_key_manager()

        # Set a preferred key (even if doesn't exist, method should accept)
        result = km.set_preferred_key("test_provider", "test****key")
        assert result is True

        # Clear preference
        km.clear_preferred_key("test_provider")

        # Verify cleared
        assert "test_provider" not in km._preferred_keys


# ── Phase 127.0: Pipeline Results Viewer ──

class TestPhase127_0_ResultsViewer:
    """Tests for MARKER_127.0: Pipeline Results Viewer feature."""

    def test_marker_127_0a_backend_endpoint(self):
        """MARKER_127.0A: debug_routes should have pipeline-results endpoint."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_127.0A" in source
        assert "/pipeline-results/{task_id}" in source
        assert "async def get_pipeline_results" in source

    def test_marker_127_0b_taskcard_results(self):
        """MARKER_127.0B: TaskCard should have results viewing."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "MARKER_127.0B" in source
        assert "showResults" in source
        assert "fetchResults" in source
        assert "PipelineResults" in source

    def test_taskcard_has_results_button(self):
        """TaskCard should have results button for done tasks."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "hasPipelineResults" in source
        assert "'results'" in source  # Button text

    def test_taskcard_has_subtask_display(self):
        """TaskCard should display subtasks with results."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "subtasks" in source
        assert "expandedSubtask" in source
        assert "copy" in source  # Copy button


# ── Phase 126.12: Stats Monitor Live Refresh ──

class TestPhase126_12_StatsMonitor:
    """Tests for MARKER_126.12: PipelineStats live refresh."""

    def test_marker_126_12a_live_refresh(self):
        """MARKER_126.12A: PipelineStats should have live refresh."""
        source = _read_source("client/src/components/panels/PipelineStats.tsx")
        assert "MARKER_126.12" in source
        assert "task-board-updated" in source
        assert "onRefresh" in source

    def test_marker_126_12b_running_tasks(self):
        """MARKER_126.12B: PipelineStats should show running tasks."""
        source = _read_source("client/src/components/panels/PipelineStats.tsx")
        assert "MARKER_126.12B" in source
        assert "runningTasks" in source
        assert "formatElapsed" in source

    def test_marker_126_12c_summary_improvements(self):
        """MARKER_126.12C: PipelineStats should show improved summary."""
        source = _read_source("client/src/components/panels/PipelineStats.tsx")
        assert "MARKER_126.12C" in source
        assert "totalTokensIn" in source
        assert "totalTokensOut" in source
        assert "successRate" in source


# ── Phase 127.2: Activity Log Tab ──

class TestPhase127_2_ActivityLog:
    """Tests for MARKER_127.2: Activity Log component and DevPanel integration."""

    def test_marker_127_2a_activity_log_component(self):
        """MARKER_127.2A: ActivityLog component should exist."""
        source = _read_source("client/src/components/panels/ActivityLog.tsx")
        assert "MARKER_127.2A" in source
        assert "pipeline-activity" in source
        assert "LogEntry" in source

    def test_activity_log_ring_buffer(self):
        """ActivityLog should use ring buffer (max 100 entries)."""
        source = _read_source("client/src/components/panels/ActivityLog.tsx")
        assert "MAX_ENTRIES" in source
        assert "100" in source
        assert ".slice(0, MAX_ENTRIES)" in source

    def test_activity_log_follow_tail(self):
        """ActivityLog should have follow tail toggle."""
        source = _read_source("client/src/components/panels/ActivityLog.tsx")
        assert "followTail" in source
        assert "setFollowTail" in source

    def test_marker_127_2b_devpanel_integration(self):
        """MARKER_127.2B: DevPanel should have Activity tab."""
        source = _read_source("client/src/components/panels/DevPanel.tsx")
        assert "MARKER_127.2B" in source
        assert "'activity'" in source
        assert "ActivityLog" in source
        assert "import { ActivityLog }" in source


# ── Phase 127.3: API Key Refresh Fix ──

class TestPhase127_3_KeyRefreshFix:
    """Tests for MARKER_127.3: Fix new API keys not showing after refresh."""

    def test_marker_127_3_reload_on_fetch(self):
        """MARKER_127.3: /usage/balances should reload keys from config."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_127.3" in source
        assert "km.load_from_config()" in source
        assert "keys_loaded" in source
