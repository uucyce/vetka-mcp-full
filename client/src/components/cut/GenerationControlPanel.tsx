/**
 * MARKER_GEN-PANEL: Generation Control Panel — root panel with 3 tabs.
 *
 * FCP7 Deck Control (Ch.50-51) → AI Generation Control.
 * Tabs: GENERATE | QUEUE | SETTINGS
 *
 * State machine lives in useGenerationControlStore.
 * Hotkeys wired via useGenerationHotkeys (scoped to focusedPanel='generation').
 *
 * Provider selector: monogram pill row at top.
 * Generate tab: prompt + params + preview thumb + cost badge + transport bar.
 * Queue tab: GenerationQueueList.
 * Settings tab: GenerationProviderSettings.
 *
 * Monochrome: #0a0a0a panel, #fff progress, #888 status.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */
import { useState, useCallback, type CSSProperties } from 'react';
import { useGenerationControlStore } from '../../store/useGenerationControlStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useGenerationHotkeys } from '../../hooks/useGenerationHotkeys';
import { GENERATION_PROVIDERS } from '../../config/generation.config';
import GenerationPromptInput from './GenerationPromptInput';
import GenerationPreviewThumb from './GenerationPreviewThumb';
import GenerationCostBadge from './GenerationCostBadge';
import GenerationTransportBar from './GenerationTransportBar';
import GenerationQueueList from './GenerationQueueList';
import GenerationProviderSettings from './GenerationProviderSettings';
import { API_BASE } from '../../config/api.config';

// ─── Styles ───

const PANEL: CSSProperties = {
  display: 'flex', flexDirection: 'column', height: '100%',
  background: '#0a0a0a', fontFamily: 'system-ui', fontSize: 11, color: '#ccc',
  overflow: 'hidden',
};

const HEADER: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 0,
  padding: '0 0 0 0', borderBottom: '1px solid #1a1a1a',
  flexShrink: 0,
};

const TAB: CSSProperties = {
  padding: '7px 12px', fontSize: 9,
  textTransform: 'uppercase', letterSpacing: 0.5,
  color: '#555', cursor: 'pointer', userSelect: 'none',
  borderBottom: '2px solid transparent',
};

const TAB_ACTIVE: CSSProperties = {
  ...TAB, color: '#ccc', borderBottom: '2px solid #888',
};

const PROVIDER_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 4,
  padding: '6px 10px', borderBottom: '1px solid #111',
  flexWrap: 'wrap', flexShrink: 0,
};

const PROVIDER_PILL: CSSProperties = {
  width: 22, height: 22, borderRadius: 3,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: '#111', color: '#666', fontSize: 9, fontWeight: 700,
  cursor: 'pointer', userSelect: 'none', border: '1px solid #222',
  flexShrink: 0,
};

const PROVIDER_PILL_ACTIVE: CSSProperties = {
  ...PROVIDER_PILL, background: '#1a1a1a', color: '#ccc', border: '1px solid #444',
};

const CONTENT: CSSProperties = {
  flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column',
};

type Tab = 'generate' | 'queue' | 'settings';

// ─── Component ───

export default function GenerationControlPanel() {
  const [activeTab, setActiveTab] = useState<Tab>('generate');

  const machineState = useGenerationControlStore((s) => s.machineState);
  const activeProviderId = useGenerationControlStore((s) => s.activeProviderId);
  const connectProvider = useGenerationControlStore((s) => s.connectProvider);
  const connectionSuccess = useGenerationControlStore((s) => s.connectionSuccess);
  const connectionFailed = useGenerationControlStore((s) => s.connectionFailed);

  const setFocusedPanel = useCutEditorStore((s) => s.setFocusedPanel);

  // Mount hotkeys
  useGenerationHotkeys();

  const selectProvider = useCallback(async (providerId: string) => {
    if (providerId === activeProviderId) return;
    connectProvider(providerId);
    try {
      const res = await fetch(`${API_BASE}/cut/generate/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: providerId }),
      });
      const data = await res.json() as { success: boolean };
      if (data.success) connectionSuccess();
      else connectionFailed();
    } catch {
      connectionFailed();
    }
  }, [activeProviderId, connectProvider, connectionSuccess, connectionFailed]);

  return (
    <div
      style={PANEL}
      data-testid="generation-control-panel"
      onFocus={() => setFocusedPanel('generation')}
      tabIndex={-1}
    >
      {/* Tab bar */}
      <div style={HEADER}>
        {(['generate', 'queue', 'settings'] as Tab[]).map((tab) => (
          <div
            key={tab}
            style={activeTab === tab ? TAB_ACTIVE : TAB}
            onClick={() => setActiveTab(tab)}
            data-testid={`gen-tab-${tab}`}
          >
            {tab}
          </div>
        ))}
        {/* Machine state indicator pushed right */}
        <div style={{ flex: 1 }} />
        <div style={{
          fontSize: 8, color: '#333', fontFamily: 'monospace',
          textTransform: 'uppercase', letterSpacing: 1, padding: '0 10px',
        }}
          data-testid="gen-machine-state"
        >
          {machineState}
        </div>
      </div>

      {/* Provider selector (generate + settings tabs) */}
      {(activeTab === 'generate' || activeTab === 'settings') && (
        <div style={PROVIDER_ROW} data-testid="provider-selector">
          <span style={{ fontSize: 8, color: '#444', marginRight: 2 }}>Provider:</span>
          {GENERATION_PROVIDERS.map((p) => (
            <div
              key={p.id}
              style={p.id === activeProviderId ? PROVIDER_PILL_ACTIVE : PROVIDER_PILL}
              onClick={() => selectProvider(p.id)}
              title={p.name}
              data-testid={`provider-pill-${p.id}`}
            >
              {p.monogram}
            </div>
          ))}
        </div>
      )}

      {/* Tab content */}
      <div style={CONTENT}>
        {activeTab === 'generate' && (
          <>
            <GenerationPreviewThumb />
            <GenerationPromptInput />
            <div style={{ flex: 1 }} />
            <GenerationCostBadge />
            <GenerationTransportBar />
          </>
        )}
        {activeTab === 'queue' && <GenerationQueueList />}
        {activeTab === 'settings' && <GenerationProviderSettings />}
      </div>
    </div>
  );
}
