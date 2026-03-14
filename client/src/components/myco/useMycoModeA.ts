import { useEffect, useMemo, useState } from 'react';
import { buildMycoModeAHint, buildMycoModeAStateKey, createMycoModeAFocusSnapshot } from './mycoModeARules';
import type { MycoModeAInputs } from './mycoModeATypes';

type SearchContext = 'vetka' | 'web' | 'file' | 'cloud' | 'social';

interface SearchStateDetail {
  scope?: string;
  context?: SearchContext;
  mode?: 'hybrid' | 'semantic' | 'keyword' | 'filename';
  queryEmpty?: boolean;
  providerHealth?: Record<string, { available?: boolean; error?: string | null }>;
  error?: string | null;
}

interface SearchAttemptDetail {
  scope?: string;
  context?: SearchContext;
  available?: boolean;
}

interface ChatInputStateDetail {
  empty?: boolean;
  isOpen?: boolean;
}

interface ChatSurfaceStateDetail {
  activeTab?: 'chat' | 'scanner' | 'group';
  hasActiveGroup?: boolean;
}

interface KeyInventoryRefreshDetail {
  totalKeys?: number;
  providers?: string[];
}

interface ScannerStateDetail {
  source?: 'local' | 'cloud' | 'browser' | 'social';
  category?: 'none' | 'browser_placeholder' | 'auth_modal_open' | 'missing_oauth_client' | 'provider_connected' | 'provider_expired' | 'provider_token_missing' | 'tree_preview_unavailable' | 'provider_pending';
  providerLabel?: string;
  message?: string;
  authMethod?: 'oauth' | 'api_key' | 'link' | '';
  requiresVerification?: boolean;
}

const LLM_KEY_PROVIDERS = new Set([
  'openrouter',
  'openai',
  'anthropic',
  'gemini',
  'google',
  'xai',
  'polza',
  'poe',
  'mistral',
  'nanogpt',
  'perplexity',
  'groq',
  'deepseek',
]);

function classifySearchError(errorMessage: string, webProviderAvailable: boolean | null): MycoModeAInputs['searchErrorCategory'] {
  const text = (errorMessage || '').toLowerCase().trim();
  if (!text) {
    return webProviderAvailable === false ? 'missing_key' : 'none';
  }
  if (
    text.includes('no tavily api key')
    || text.includes('configure tavily')
    || text.includes('provider unavailable')
    || text.includes('missing key')
  ) {
    return 'missing_key';
  }
  if (
    text.includes('401')
    || text.includes('403')
    || text.includes('invalid')
    || text.includes('expired')
    || text.includes('auth')
    || text.includes('unauthorized')
  ) {
    return 'auth';
  }
  if (
    text.includes('402')
    || text.includes('billing')
    || text.includes('quota')
    || text.includes('balance')
    || text.includes('credit')
    || text.includes('payment')
    || text.includes('insufficient')
  ) {
    return 'billing';
  }
  if (text.includes('429') || text.includes('rate limit')) {
    return 'rate_limit';
  }
  if (text.includes('timeout') || text.includes('timed out')) {
    return 'timeout';
  }
  if (
    text.includes('service returned')
    || text.includes('network')
    || text.includes('failed')
    || text.includes('fetch')
    || text.includes('unavailable')
  ) {
    return 'provider_down';
  }
  return 'unknown';
}

export function useMycoModeA(
  inputs: Omit<
    MycoModeAInputs,
    | 'searchContext'
    | 'searchMode'
    | 'searchQueryEmpty'
    | 'chatInputEmpty'
    | 'disabledSearchAttempt'
    | 'keyInventoryLoaded'
    | 'totalConfiguredKeys'
    | 'configuredProviders'
    | 'hasAnyKeys'
    | 'hasLlmProviderKey'
    | 'hasSearchProviderKey'
    | 'webProviderAvailable'
    | 'searchErrorCategory'
    | 'searchErrorMessage'
    | 'scannerSource'
    | 'scannerStateCategory'
    | 'scannerProviderLabel'
    | 'scannerStateMessage'
    | 'scannerAuthMethod'
    | 'scannerRequiresVerification'
  >,
) {
  const [searchContext, setSearchContext] = useState<SearchContext>('vetka');
  const [searchMode, setSearchMode] = useState<'hybrid' | 'semantic' | 'keyword' | 'filename'>('hybrid');
  const [searchQueryEmpty, setSearchQueryEmpty] = useState(true);
  const [chatInputEmpty, setChatInputEmpty] = useState(true);
  const [chatMode, setChatMode] = useState<'chat' | 'scanner' | 'group'>('chat');
  const [hasActiveGroup, setHasActiveGroup] = useState(false);
  const [disabledSearchAttempt, setDisabledSearchAttempt] = useState<'cloud' | 'social' | null>(null);
  const [keyInventoryLoaded, setKeyInventoryLoaded] = useState(false);
  const [totalConfiguredKeys, setTotalConfiguredKeys] = useState(0);
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const [webProviderAvailable, setWebProviderAvailable] = useState<boolean | null>(null);
  const [searchErrorMessage, setSearchErrorMessage] = useState('');
  const [scannerSource, setScannerSource] = useState<'local' | 'cloud' | 'browser' | 'social'>('local');
  const [scannerStateCategory, setScannerStateCategory] = useState<MycoModeAInputs['scannerStateCategory']>('none');
  const [scannerProviderLabel, setScannerProviderLabel] = useState('');
  const [scannerStateMessage, setScannerStateMessage] = useState('');
  const [scannerAuthMethod, setScannerAuthMethod] = useState<MycoModeAInputs['scannerAuthMethod']>('');
  const [scannerRequiresVerification, setScannerRequiresVerification] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const applyInventory = (providers: string[], totalKeys: number) => {
      if (cancelled) return;
      setConfiguredProviders(providers);
      setTotalConfiguredKeys(totalKeys);
      setKeyInventoryLoaded(true);
    };

    const loadKeyInventory = async () => {
      try {
        const res = await fetch('/api/keys');
        const data = await res.json();
        const providerRows = Array.isArray(data?.providers) ? data.providers : [];
        const providers = providerRows
          .map((row: { provider?: string }) => String(row?.provider || '').toLowerCase().trim())
          .filter(Boolean);
        const totalKeys = providerRows.reduce((sum: number, row: { count?: number; keys?: unknown[] }) => {
          if (typeof row?.count === 'number') return sum + row.count;
          if (Array.isArray(row?.keys)) return sum + row.keys.length;
          return sum;
        }, 0);
        applyInventory(providers, totalKeys);
      } catch {
        if (!cancelled) {
          setKeyInventoryLoaded(true);
          setConfiguredProviders([]);
          setTotalConfiguredKeys(0);
        }
      }
    };

    loadKeyInventory();

    const onKeyInventoryRefresh = (event: Event) => {
      const detail = ((event as CustomEvent).detail || {}) as KeyInventoryRefreshDetail;
      const providers = Array.isArray(detail.providers)
        ? detail.providers.map((provider) => String(provider || '').toLowerCase().trim()).filter(Boolean)
        : [];
      const totalKeys = typeof detail.totalKeys === 'number' ? detail.totalKeys : providers.length;
      applyInventory(providers, totalKeys);
    };

    window.addEventListener('vetka-myco-key-inventory-refresh', onKeyInventoryRefresh as EventListener);
    return () => {
      cancelled = true;
      window.removeEventListener('vetka-myco-key-inventory-refresh', onKeyInventoryRefresh as EventListener);
    };
  }, []);

  useEffect(() => {
    const onSearchState = (event: Event) => {
      const detail = ((event as CustomEvent).detail || {}) as SearchStateDetail;
      if (detail.scope !== 'main') return;
      setSearchContext((detail.context as SearchContext) || 'vetka');
      setSearchMode(detail.mode || 'hybrid');
      setSearchQueryEmpty(detail.queryEmpty !== false);
      const tavilyAvailable = detail.providerHealth?.tavily?.available;
      setWebProviderAvailable(typeof tavilyAvailable === 'boolean' ? tavilyAvailable : null);
      setSearchErrorMessage(detail.error || '');
      if (detail.context === 'vetka') {
        setDisabledSearchAttempt(null);
      }
    };

    const onSearchAttempt = (event: Event) => {
      const detail = ((event as CustomEvent).detail || {}) as SearchAttemptDetail;
      if (detail.scope !== 'main') return;
      if (detail.available === false && (detail.context === 'cloud' || detail.context === 'social')) {
        setDisabledSearchAttempt(detail.context);
      }
    };

    window.addEventListener('vetka-myco-search-state', onSearchState as EventListener);
    window.addEventListener('vetka-myco-search-context-attempt', onSearchAttempt as EventListener);
    return () => {
      window.removeEventListener('vetka-myco-search-state', onSearchState as EventListener);
      window.removeEventListener('vetka-myco-search-context-attempt', onSearchAttempt as EventListener);
    };
  }, []);

  useEffect(() => {
    const onChatInputState = (event: Event) => {
      const detail = ((event as CustomEvent).detail || {}) as ChatInputStateDetail;
      setChatInputEmpty(detail.isOpen === false ? true : detail.empty !== false);
    };

    window.addEventListener('vetka-myco-chat-input-state', onChatInputState as EventListener);
    return () => {
      window.removeEventListener('vetka-myco-chat-input-state', onChatInputState as EventListener);
    };
  }, []);

  useEffect(() => {
    const onChatSurfaceState = (event: Event) => {
      const detail = ((event as CustomEvent).detail || {}) as ChatSurfaceStateDetail;
      setChatMode(detail.activeTab || 'chat');
      setHasActiveGroup(Boolean(detail.hasActiveGroup));
    };

    window.addEventListener('vetka-myco-chat-surface-state', onChatSurfaceState as EventListener);
    return () => {
      window.removeEventListener('vetka-myco-chat-surface-state', onChatSurfaceState as EventListener);
    };
  }, []);

  useEffect(() => {
    const onScannerState = (event: Event) => {
      const detail = ((event as CustomEvent).detail || {}) as ScannerStateDetail;
      if (detail.source) setScannerSource(detail.source);
      setScannerStateCategory(detail.category || 'none');
      setScannerProviderLabel(detail.providerLabel || '');
      setScannerStateMessage(detail.message || '');
      setScannerAuthMethod(detail.authMethod || '');
      setScannerRequiresVerification(Boolean(detail.requiresVerification));
    };

    window.addEventListener('vetka-myco-scanner-state', onScannerState as EventListener);
    return () => {
      window.removeEventListener('vetka-myco-scanner-state', onScannerState as EventListener);
    };
  }, []);

  useEffect(() => {
    if (!inputs.isChatOpen) {
      setChatInputEmpty(true);
      setChatMode('chat');
      setHasActiveGroup(false);
      setScannerStateCategory('none');
      setScannerProviderLabel('');
      setScannerStateMessage('');
      setScannerAuthMethod('');
      setScannerRequiresVerification(false);
    }
  }, [inputs.isChatOpen]);

  useEffect(() => {
    if (disabledSearchAttempt === null) return;
    const timer = window.setTimeout(() => setDisabledSearchAttempt(null), 2200);
    return () => window.clearTimeout(timer);
  }, [disabledSearchAttempt]);

  const snapshot = useMemo(
    () =>
      createMycoModeAFocusSnapshot({
        ...inputs,
        chatMode,
        hasActiveGroup,
        searchContext,
        searchMode,
        searchQueryEmpty: inputs.isChatOpen ? true : searchQueryEmpty,
        chatInputEmpty,
        disabledSearchAttempt,
        keyInventoryLoaded,
        totalConfiguredKeys,
        configuredProviders,
        hasAnyKeys: totalConfiguredKeys > 0,
        hasLlmProviderKey: configuredProviders.some((provider) => LLM_KEY_PROVIDERS.has(provider)),
        hasSearchProviderKey: configuredProviders.includes('tavily'),
        webProviderAvailable,
        searchErrorCategory: classifySearchError(searchErrorMessage, webProviderAvailable),
        searchErrorMessage,
        scannerSource,
        scannerStateCategory,
        scannerProviderLabel,
        scannerStateMessage,
        scannerAuthMethod,
        scannerRequiresVerification,
      }),
    [
      chatInputEmpty,
      chatMode,
      configuredProviders,
      disabledSearchAttempt,
      hasActiveGroup,
      inputs,
      keyInventoryLoaded,
      searchContext,
      searchErrorMessage,
      searchMode,
      searchQueryEmpty,
      totalConfiguredKeys,
      webProviderAvailable,
      scannerProviderLabel,
      scannerAuthMethod,
      scannerRequiresVerification,
      scannerSource,
      scannerStateCategory,
      scannerStateMessage,
    ],
  );

  const stateKey = useMemo(() => buildMycoModeAStateKey(snapshot), [snapshot]);
  const hint = useMemo(() => buildMycoModeAHint(snapshot), [snapshot]);

  return {
    hint,
    snapshot,
    stateKey,
  };
}
