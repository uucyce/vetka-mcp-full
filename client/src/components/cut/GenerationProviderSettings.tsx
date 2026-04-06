/**
 * MARKER_GEN-SETTINGS: Generation Provider Settings — API keys, connection test, budgets.
 *
 * Collapsible section per provider (10 total).
 * - API key input (masked)
 * - Test connection button with inline result
 * - Local path for CLI providers (FLUX/SDXL/ESRGAN/Topaz)
 * - Budget: daily/monthly limits, current spend, alert threshold
 *
 * Monochrome — ZERO color. Provider icons as single-letter monograms in #888.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432042_1
 */
import { useState, useCallback, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';

// ─── Provider metadata ───

interface ProviderDef {
  id: string;
  name: string;
  monogram: string;
  type: 'api' | 'local';
  category: 'video' | 'music' | 'voice' | 'upscale';
}

const PROVIDERS: ProviderDef[] = [
  { id: 'runway',      name: 'Runway Gen-3',   monogram: 'R', type: 'api',   category: 'video' },
  { id: 'sora',        name: 'OpenAI Sora',    monogram: 'S', type: 'api',   category: 'video' },
  { id: 'kling',       name: 'Kling',          monogram: 'K', type: 'api',   category: 'video' },
  { id: 'flux',        name: 'FLUX.1',         monogram: 'F', type: 'local', category: 'video' },
  { id: 'sdxl',        name: 'SDXL',           monogram: 'X', type: 'local', category: 'video' },
  { id: 'suno',        name: 'Suno',           monogram: 'U', type: 'api',   category: 'music' },
  { id: 'udio',        name: 'Udio',           monogram: 'D', type: 'api',   category: 'music' },
  { id: 'elevenlabs',  name: 'ElevenLabs',     monogram: 'E', type: 'api',   category: 'voice' },
  { id: 'realesrgan',  name: 'Real-ESRGAN',    monogram: 'G', type: 'local', category: 'upscale' },
  { id: 'topaz',       name: 'Topaz Video AI', monogram: 'T', type: 'local', category: 'upscale' },
];

// ─── Provider config state ───

interface ProviderConfig {
  apiKey: string;
  localPath: string;
  connected: boolean | null; // null = untested
  testing: boolean;
}

type ProviderConfigs = Record<string, ProviderConfig>;

interface BudgetConfig {
  dailyLimit: string;
  monthlyLimit: string;
  alertThreshold: string;
  currentSpend: number;
}

const defaultConfig = (): ProviderConfig => ({
  apiKey: '', localPath: '', connected: null, testing: false,
});

// ─── Styles ───

const PANEL: CSSProperties = {
  display: 'flex', flexDirection: 'column', height: '100%',
  background: '#0d0d0d', fontFamily: 'system-ui', fontSize: 11, color: '#ccc',
  overflow: 'auto',
};

const SECTION_HEADER: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6,
  padding: '8px 10px', cursor: 'pointer', userSelect: 'none',
  borderBottom: '1px solid #1a1a1a',
};

const MONOGRAM: CSSProperties = {
  width: 18, height: 18, borderRadius: 3,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: '#1a1a1a', color: '#888', fontSize: 9, fontWeight: 700,
  flexShrink: 0,
};

const SECTION_BODY: CSSProperties = {
  padding: '6px 10px 10px 34px',
  borderBottom: '1px solid #111',
};

const FIELD: CSSProperties = {
  marginBottom: 6,
};

const LABEL: CSSProperties = {
  fontSize: 9, color: '#555', textTransform: 'uppercase',
  letterSpacing: 0.5, marginBottom: 2,
};

const INPUT: CSSProperties = {
  width: '100%', padding: '4px 6px', background: '#111',
  border: '1px solid #333', borderRadius: 3, color: '#ccc',
  fontSize: 10, fontFamily: 'system-ui', outline: 'none',
  boxSizing: 'border-box',
};

const BTN: CSSProperties = {
  padding: '3px 8px', border: '1px solid #333', borderRadius: 3,
  background: '#111', color: '#aaa', fontSize: 9, cursor: 'pointer',
};

const STATUS_DOT: CSSProperties = {
  display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
  marginRight: 4,
};

const BUDGET_SECTION: CSSProperties = {
  padding: '10px', borderTop: '1px solid #222',
};

const BUDGET_ROW: CSSProperties = {
  display: 'flex', gap: 8, marginBottom: 6, alignItems: 'center',
};

// ─── Component ───

export default function GenerationProviderSettings() {
  const [configs, setConfigs] = useState<ProviderConfigs>(() => {
    const init: ProviderConfigs = {};
    for (const p of PROVIDERS) init[p.id] = defaultConfig();
    return init;
  });
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [budget, setBudget] = useState<BudgetConfig>({
    dailyLimit: '10', monthlyLimit: '100', alertThreshold: '80', currentSpend: 0,
  });

  const toggleExpand = useCallback((id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const updateConfig = useCallback((id: string, patch: Partial<ProviderConfig>) => {
    setConfigs((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));
  }, []);

  const testConnection = useCallback(async (provider: ProviderDef) => {
    updateConfig(provider.id, { testing: true, connected: null });
    try {
      const cfg = configs[provider.id];
      const res = await fetch(`${API_BASE}/cut/generate/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: provider.id,
          api_key: cfg.apiKey,
          local_path: cfg.localPath,
        }),
      });
      const data = await res.json();
      updateConfig(provider.id, { testing: false, connected: !!data.success });
    } catch {
      updateConfig(provider.id, { testing: false, connected: false });
    }
  }, [configs, updateConfig]);

  return (
    <div style={PANEL} data-testid="generation-provider-settings">
      {/* Header */}
      <div style={{ padding: '8px 10px', borderBottom: '1px solid #1a1a1a', fontWeight: 600, fontSize: 12 }}>
        Provider Settings
      </div>

      {/* Provider list */}
      {PROVIDERS.map((provider) => {
        const cfg = configs[provider.id];
        const isExpanded = expanded[provider.id] || false;

        return (
          <div key={provider.id} data-testid={`provider-${provider.id}`}>
            <div
              style={SECTION_HEADER}
              onClick={() => toggleExpand(provider.id)}
            >
              <span style={{ fontSize: 9, color: '#555', width: 8 }}>
                {isExpanded ? '-' : '+'}
              </span>
              <span style={MONOGRAM}>{provider.monogram}</span>
              <span style={{ flex: 1, fontWeight: 500 }}>{provider.name}</span>
              <span style={{ fontSize: 8, color: '#444' }}>{provider.category}</span>
              {cfg.connected !== null && (
                <span
                  style={{
                    ...STATUS_DOT,
                    background: cfg.connected ? '#888' : '#444',
                    boxShadow: cfg.connected ? '0 0 4px rgba(136,136,136,0.5)' : 'none',
                  }}
                  title={cfg.connected ? 'Connected' : 'Disconnected'}
                />
              )}
            </div>

            {isExpanded && (
              <div style={SECTION_BODY}>
                {/* API Key (for API providers) */}
                {provider.type === 'api' && (
                  <div style={FIELD}>
                    <div style={LABEL}>API Key</div>
                    <input
                      style={INPUT}
                      type="password"
                      value={cfg.apiKey}
                      onChange={(e) => updateConfig(provider.id, { apiKey: e.target.value })}
                      placeholder="sk-..."
                      data-testid={`api-key-${provider.id}`}
                    />
                  </div>
                )}

                {/* Local path (for CLI providers) */}
                {provider.type === 'local' && (
                  <div style={FIELD}>
                    <div style={LABEL}>Local Path</div>
                    <input
                      style={INPUT}
                      value={cfg.localPath}
                      onChange={(e) => updateConfig(provider.id, { localPath: e.target.value })}
                      placeholder="/usr/local/bin/..."
                      data-testid={`local-path-${provider.id}`}
                    />
                  </div>
                )}

                {/* Test connection */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button
                    style={BTN}
                    onClick={() => testConnection(provider)}
                    disabled={cfg.testing}
                    data-testid={`test-${provider.id}`}
                  >
                    {cfg.testing ? 'Testing...' : 'Test Connection'}
                  </button>
                  {cfg.connected === true && (
                    <span style={{ fontSize: 9, color: '#888' }}>Connected</span>
                  )}
                  {cfg.connected === false && (
                    <span style={{ fontSize: 9, color: '#666' }}>Failed</span>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Budget section */}
      <div style={BUDGET_SECTION}>
        <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>Budget</div>

        <div style={BUDGET_ROW}>
          <div style={{ flex: 1 }}>
            <div style={LABEL}>Daily Limit ($)</div>
            <input
              style={INPUT}
              type="number"
              value={budget.dailyLimit}
              onChange={(e) => setBudget((b) => ({ ...b, dailyLimit: e.target.value }))}
              data-testid="budget-daily"
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={LABEL}>Monthly Limit ($)</div>
            <input
              style={INPUT}
              type="number"
              value={budget.monthlyLimit}
              onChange={(e) => setBudget((b) => ({ ...b, monthlyLimit: e.target.value }))}
              data-testid="budget-monthly"
            />
          </div>
        </div>

        <div style={BUDGET_ROW}>
          <div style={{ flex: 1 }}>
            <div style={LABEL}>Alert at (%)</div>
            <input
              style={INPUT}
              type="number"
              value={budget.alertThreshold}
              onChange={(e) => setBudget((b) => ({ ...b, alertThreshold: e.target.value }))}
              data-testid="budget-alert"
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={LABEL}>Current Spend</div>
            <div style={{ fontSize: 14, fontFamily: 'monospace', color: '#888', padding: '4px 0' }}>
              ${budget.currentSpend.toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
