/**
 * MARKER_126.6: BalancesPanel — unified usage and balance monitoring.
 * MARKER_126.8: Scroll support (unified pattern from DevPanel/ChatPanel)
 * MARKER_126.9A: Key row click → select key for next pipeline dispatch
 * Style: Nolan monochrome. Palette: #111, #222, #333, #e0e0e0, #888, #666.
 * Color accents ONLY for status (muted red/green).
 *
 * @status active
 * @phase 126.3
 * @depends none (pure CSS)
 */

import { useState, useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';

interface UsageRecord {
  provider: string;
  key_masked: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  balance_usd: number | null;
  balance_limit: number | null;
  is_free_tier: boolean;
  exhausted: boolean;
  last_used: number;
  call_count: number;
}

interface Totals {
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_usd: number;
  total_calls: number;
  by_provider: Record<string, {
    tokens_in: number;
    tokens_out: number;
    cost_usd: number;
    calls: number;
    keys: number;
  }>;
  records_count: number;
}

const API_BASE = 'http://localhost:5001/api/debug';

// MARKER_126.6A: Nolan monochrome palette
const COLORS = {
  bg: '#111',
  bgLight: '#1a1a1a',
  border: '#222',
  borderLight: '#333',
  text: '#e0e0e0',
  textMuted: '#888',
  textDim: '#666',
  textDimmer: '#444',
  // Status accents (muted)
  success: '#2a3a2a',
  successText: '#6a8a6a',
  error: '#3a2a2a',
  errorText: '#8a6a6a',
};

export function BalancesPanel() {
  const [records, setRecords] = useState<UsageRecord[]>([]);
  const [totals, setTotals] = useState<Totals | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // MARKER_126.9A: Selected API key for next pipeline dispatch
  const selectedKey = useStore((s) => s.selectedKey);
  const setSelectedKey = useStore((s) => s.setSelectedKey);

  const handleKeyClick = useCallback((provider: string, key_masked: string) => {
    // Toggle selection: click same key to deselect
    if (selectedKey?.provider === provider && selectedKey?.key_masked === key_masked) {
      setSelectedKey(null);
    } else {
      setSelectedKey({ provider, key_masked });
    }
  }, [selectedKey, setSelectedKey]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/usage/balances`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success) {
        setRecords(data.records || []);
        setTotals(data.totals || null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleReset = async () => {
    if (!confirm('Reset all usage counters?')) return;
    try {
      await fetch(`${API_BASE}/usage/reset`, { method: 'POST' });
      fetchData();
    } catch (err) {
      console.error('Reset failed:', err);
    }
  };

  // MARKER_126.6B: Format helpers
  const formatTokens = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
    return n.toString();
  };

  const formatTime = (ts: number) => {
    if (!ts) return '-';
    return new Date(ts * 1000).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    // MARKER_126.8A: Flex column layout for proper scrolling
    <div style={{
      padding: 0,
      fontSize: 11,
      color: COLORS.text,
      fontFamily: 'monospace',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }}>
      {/* Header — fixed at top */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
        paddingBottom: 10,
        borderBottom: `1px solid ${COLORS.border}`
      }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: COLORS.text, letterSpacing: 1.5, textTransform: 'uppercase' }}>
            usage / balances
          </div>
          {totals && (
            <div style={{ color: COLORS.textDim, marginTop: 4, fontSize: 9 }}>
              {formatTokens(totals.total_tokens_in)} in, {formatTokens(totals.total_tokens_out)} out, {totals.total_calls} calls
              <span style={{ color: COLORS.textMuted, marginLeft: 8 }}>
                ${totals.total_cost_usd.toFixed(4)}
              </span>
            </div>
          )}
          {/* MARKER_126.9A: Selected key indicator */}
          {selectedKey && (
            <div style={{
              color: COLORS.text,
              marginTop: 4,
              fontSize: 9,
              padding: '3px 6px',
              background: 'rgba(255,255,255,0.05)',
              borderRadius: 2,
              display: 'inline-block'
            }}>
              next: {selectedKey.provider}/{selectedKey.key_masked.slice(0, 8)}...
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={handleReset}
            style={{
              padding: '4px 8px',
              background: 'transparent',
              border: `1px solid ${COLORS.border}`,
              borderRadius: 2,
              color: COLORS.textDim,
              fontSize: 9,
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            reset
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            style={{
              padding: '4px 8px',
              background: loading ? 'transparent' : `rgba(255,255,255,0.03)`,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 2,
              color: loading ? COLORS.textDimmer : COLORS.textMuted,
              fontSize: 9,
              fontFamily: 'monospace',
              cursor: loading ? 'wait' : 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {loading ? '...' : 'refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          color: COLORS.errorText,
          marginBottom: 10,
          padding: '6px 8px',
          background: COLORS.error,
          borderRadius: 2,
          fontSize: 10
        }}>
          {error}
        </div>
      )}

      {/* MARKER_126.8B: Scrollable table area (pattern from DevPanel Task List) */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        overflowX: 'auto',
        minHeight: 0,  // Critical for flex scroll
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${COLORS.border}` }}>
              <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500, color: COLORS.textDim, fontSize: 9, letterSpacing: 0.5 }}>PROVIDER</th>
              <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500, color: COLORS.textDim, fontSize: 9, letterSpacing: 0.5 }}>KEY</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500, color: COLORS.textDim, fontSize: 9, letterSpacing: 0.5 }}>IN</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500, color: COLORS.textDim, fontSize: 9, letterSpacing: 0.5 }}>OUT</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500, color: COLORS.textDim, fontSize: 9, letterSpacing: 0.5 }}>COST</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500, color: COLORS.textDim, fontSize: 9, letterSpacing: 0.5 }}>BAL</th>
              <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500, color: COLORS.textDim, fontSize: 9, letterSpacing: 0.5 }}>LAST</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => {
              // MARKER_126.9A: Check if this row is selected
              const isSelected = selectedKey?.provider === r.provider && selectedKey?.key_masked === r.key_masked;
              return (
              <tr
                key={i}
                onClick={() => handleKeyClick(r.provider, r.key_masked)}
                style={{
                  borderBottom: `1px solid ${COLORS.bgLight}`,
                  opacity: r.exhausted ? 0.4 : 1,
                  cursor: 'pointer',
                  // MARKER_126.9A: Visual highlight for selected key
                  borderLeft: isSelected ? `2px solid ${COLORS.text}` : '2px solid transparent',
                  background: isSelected ? 'rgba(255,255,255,0.03)' : 'transparent',
                  transition: 'all 0.15s',
                }}
              >
                <td style={{ padding: '7px 0 7px 6px', color: isSelected ? COLORS.text : COLORS.textMuted }}>
                  {isSelected ? '▸ ' : ''}{r.provider}
                </td>
                <td style={{ padding: '7px 0', color: isSelected ? COLORS.textMuted : COLORS.textDim }}>{r.key_masked}</td>
                <td style={{ padding: '7px 0', textAlign: 'right', color: COLORS.textMuted }}>
                  {formatTokens(r.tokens_in)}
                </td>
                <td style={{ padding: '7px 0', textAlign: 'right', color: COLORS.text }}>
                  {formatTokens(r.tokens_out)}
                </td>
                <td style={{ padding: '7px 0', textAlign: 'right', color: COLORS.textMuted }}>
                  ${r.cost_usd.toFixed(4)}
                </td>
                <td style={{ padding: '7px 0', textAlign: 'right' }}>
                  {r.is_free_tier ? (
                    <span style={{ color: COLORS.textDim }}>free</span>
                  ) : r.exhausted ? (
                    <span style={{ color: COLORS.errorText }}>$0</span>
                  ) : r.balance_usd !== null ? (
                    <span style={{ color: r.balance_usd > 5 ? COLORS.successText : COLORS.textMuted }}>
                      ${r.balance_usd.toFixed(2)}
                    </span>
                  ) : (
                    <span style={{ color: COLORS.textDimmer }}>-</span>
                  )}
                </td>
                <td style={{ padding: '7px 0', textAlign: 'right', color: COLORS.textDimmer }}>
                  {formatTime(r.last_used)}
                </td>
              </tr>
            );
            })}
          </tbody>
        </table>
      </div>

      {records.length === 0 && !loading && (
        <div style={{ textAlign: 'center', color: COLORS.textDim, padding: 32, fontSize: 10 }}>
          no usage data yet
        </div>
      )}

      {/* Provider Summary — simplified footer stats */}
      {totals && Object.keys(totals.by_provider).length > 1 && (
        <div style={{
          marginTop: 12,
          paddingTop: 10,
          borderTop: `1px solid ${COLORS.border}`,
          display: 'flex',
          gap: 16,
          flexWrap: 'wrap',
          fontSize: 10,
          color: COLORS.textDim,
        }}>
          {Object.entries(totals.by_provider).map(([provider, data]) => (
            <span key={provider} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{ color: COLORS.textMuted }}>{provider}:</span>
              <span style={{ color: COLORS.text }}>${data.cost_usd.toFixed(3)}</span>
              <span style={{ color: COLORS.textDimmer }}>({data.calls})</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
