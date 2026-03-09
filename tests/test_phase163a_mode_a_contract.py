from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_mode_a_files_and_markers_exist():
    rules = _read("client/src/components/myco/mycoModeARules.ts")
    hook = _read("client/src/components/myco/useMycoModeA.ts")
    lane = _read("client/src/components/myco/MycoGuideLane.tsx")
    assert "MARKER_163A.MODE_A.SEARCH.DISABLED_CONTEXT_REDIRECT.V1" in rules
    assert "MARKER_163A.MODE_A.EXTERNAL_ARTIFACT.INGEST_HINT.V1" in rules
    assert 'data-testid="myco-mode-a-guide"' in lane
    assert "useMycoModeA" in hook
    assert "vetka-myco-key-inventory-refresh" in hook


def test_app_mounts_mode_a_lane_without_mcc_dependency():
    app = _read("client/src/App.tsx")
    assert "useMycoModeA" in app
    assert 'mycoSurfaceScope="main"' in app
    assert "mycoHint={mycoModeA.hint}" in app
    assert "mycoStateKey={mycoModeA.stateKey}" in app
    assert "Click=Select" not in app


def test_mode_a_chat_and_search_event_bridges_exist():
    search = _read("client/src/components/search/UnifiedSearchBar.tsx")
    chat = _read("client/src/components/chat/ChatPanel.tsx")
    assert "vetka-myco-search-state" in search
    assert "vetka-myco-search-context-attempt" in search
    assert "mode: searchMode" in search
    assert "MARKER_163A.MODE_A.SEARCH.DISABLED_CONTEXT_REDIRECT.V1" in search
    assert 'data-testid="myco-search-lane"' in search
    assert "mycoHint?: MycoModeAHint | null;" in search
    assert "vetka-myco-chat-input-state" in chat
    assert "MARKER_163A.MODE_A.SILENCE.ON_TYPING.V1" in chat


def test_mode_a_silence_rules_are_locked_in_rules_layer():
    rules = _read("client/src/components/myco/mycoModeARules.ts")
    assert "if (!snapshot.chatInputEmpty) return null;" in rules
    assert "if (!snapshot.searchQueryEmpty && !snapshot.isChatOpen && (snapshot.surface === 'tree' || snapshot.surface === 'search')) return null;" in rules


def test_mode_a_supports_scanner_and_group_surfaces():
    rules = _read("client/src/components/myco/mycoModeARules.ts")
    hook = _read("client/src/components/myco/useMycoModeA.ts")
    chat = _read("client/src/components/chat/ChatPanel.tsx")
    assert "return 'scanner';" in rules
    assert "return 'group_chat';" in rules
    assert "return 'group_setup';" in rules
    assert "input.isChatOpen && input.hasActiveGroup" in rules
    assert "vetka-myco-chat-surface-state" in hook
    assert "vetka-myco-chat-surface-state" in chat
    assert "preferredSearchContext={activeTab === 'scanner' ? scannerLaneContext : undefined}" in chat
    assert "contextPrefix={activeTab === 'scanner' ? `${scannerLaneContext}/` : 'vetka/'}" in chat
    assert "activeTab !== 'scanner' && (" in chat
    assert "scanner uses unified lane as canonical entry" in chat


def test_mode_a_supports_tree_modes_search_modes_and_media_artifacts():
    app = _read("client/src/App.tsx")
    tree_hook = _read("client/src/hooks/useTreeData.ts")
    api_types = _read("client/src/utils/api.ts")
    rules = _read("client/src/components/myco/mycoModeARules.ts")
    types = _read("client/src/components/myco/mycoModeATypes.ts")
    assert "artifactKind" in app
    assert "artifactLooksLikeCode" in app
    assert "vetka-switch-tree-mode" in app
    assert "requestedMode === 'media_edit'" in tree_hook
    assert "'media_edit'" in api_types
    assert "searchMode" in types
    assert "SAVE TO VETKA" in rules
    assert "favorites" in rules
    assert "сначала открыть чат" in rules.lower()
    assert "External video artifact" in rules
    assert "External audio artifact" in rules
    assert "Directed Mode показывает рабочий поток" in rules
    assert "First run · keys missing" in rules
    assert "web/ needs Tavily key" in rules
    assert "VETKA subscription" in rules


def test_mode_a_supports_key_onboarding_and_search_provider_remediation():
    model_dir = _read("client/src/components/ModelDirectory.tsx")
    hook = _read("client/src/components/myco/useMycoModeA.ts")
    search = _read("client/src/components/search/UnifiedSearchBar.tsx")
    types = _read("client/src/components/myco/mycoModeATypes.ts")
    assert "emitMycoKeyInventory" in model_dir
    assert "vetka-myco-key-inventory-refresh" in model_dir
    assert "providerHealth" in search
    assert "error: activeError" in search
    assert "classifySearchError" in hook
    assert "hasSearchProviderKey" in types
    assert "hasLlmProviderKey" in types
