export type MycoModeASurface =
  | 'tree'
  | 'chat'
  | 'chat_history'
  | 'model_directory'
  | 'artifact'
  | 'search'
  | 'scanner'
  | 'group_chat'
  | 'group_setup'
  | 'devpanel'
  | 'context_menu';

export interface MycoModeASelectedNode {
  id: string;
  name: string;
  path: string;
  type: string;
}

export interface MycoModeAFocusSnapshot {
  surface: MycoModeASurface;
  selectedNode: MycoModeASelectedNode | null;
  isChatOpen: boolean;
  leftPanel: 'none' | 'history' | 'models';
  isArtifactOpen: boolean;
  artifactPath: string;
  artifactInVetka: boolean;
  isDevPanelOpen: boolean;
  isContextMenuOpen: boolean;
  treeViewMode: 'directed' | 'knowledge' | 'media_edit';
  artifactKind: 'none' | 'file' | 'web' | 'audio' | 'video';
  artifactLooksLikeCode: boolean;
  chatMode: 'chat' | 'scanner' | 'group';
  hasActiveGroup: boolean;
  searchContext: 'vetka' | 'web' | 'file' | 'cloud' | 'social';
  searchMode: 'hybrid' | 'semantic' | 'keyword' | 'filename';
  searchQueryEmpty: boolean;
  chatInputEmpty: boolean;
  disabledSearchAttempt: 'cloud' | 'social' | null;
  keyInventoryLoaded: boolean;
  totalConfiguredKeys: number;
  configuredProviders: string[];
  hasAnyKeys: boolean;
  hasLlmProviderKey: boolean;
  hasSearchProviderKey: boolean;
  webProviderAvailable: boolean | null;
  searchErrorCategory: 'none' | 'missing_key' | 'auth' | 'billing' | 'rate_limit' | 'timeout' | 'provider_down' | 'unknown';
  searchErrorMessage: string;
  scannerSource: 'local' | 'cloud' | 'browser' | 'social';
  scannerStateCategory: 'none' | 'browser_placeholder' | 'auth_modal_open' | 'missing_oauth_client' | 'provider_connected' | 'provider_expired' | 'provider_token_missing' | 'tree_preview_unavailable' | 'provider_pending';
  scannerProviderLabel: string;
  scannerStateMessage: string;
  scannerAuthMethod: 'oauth' | 'api_key' | 'link' | '';
  scannerRequiresVerification: boolean;
}

export interface MycoModeAHint {
  title: string;
  body: string;
  nextActions: string[];
  shortcuts: string[];
  tone: 'info' | 'action' | 'warning';
}

export interface MycoModeAInputs {
  selectedNode: MycoModeASelectedNode | null;
  isChatOpen: boolean;
  leftPanel: 'none' | 'history' | 'models';
  isArtifactOpen: boolean;
  artifactPath: string;
  artifactInVetka: boolean;
  isDevPanelOpen: boolean;
  isContextMenuOpen: boolean;
  treeViewMode: 'directed' | 'knowledge' | 'media_edit';
  artifactKind: 'none' | 'file' | 'web' | 'audio' | 'video';
  artifactLooksLikeCode: boolean;
  chatMode: 'chat' | 'scanner' | 'group';
  hasActiveGroup: boolean;
  searchContext: 'vetka' | 'web' | 'file' | 'cloud' | 'social';
  searchMode: 'hybrid' | 'semantic' | 'keyword' | 'filename';
  searchQueryEmpty: boolean;
  chatInputEmpty: boolean;
  disabledSearchAttempt: 'cloud' | 'social' | null;
  keyInventoryLoaded: boolean;
  totalConfiguredKeys: number;
  configuredProviders: string[];
  hasAnyKeys: boolean;
  hasLlmProviderKey: boolean;
  hasSearchProviderKey: boolean;
  webProviderAvailable: boolean | null;
  searchErrorCategory: 'none' | 'missing_key' | 'auth' | 'billing' | 'rate_limit' | 'timeout' | 'provider_down' | 'unknown';
  searchErrorMessage: string;
  scannerSource: 'local' | 'cloud' | 'browser' | 'social';
  scannerStateCategory: 'none' | 'browser_placeholder' | 'auth_modal_open' | 'missing_oauth_client' | 'provider_connected' | 'provider_expired' | 'provider_token_missing' | 'tree_preview_unavailable' | 'provider_pending';
  scannerProviderLabel: string;
  scannerStateMessage: string;
  scannerAuthMethod: 'oauth' | 'api_key' | 'link' | '';
  scannerRequiresVerification: boolean;
}
