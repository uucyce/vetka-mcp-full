/**
 * MARKER_156.MINI_BALANCE.001: MiniBalance — compact balance overlay in DAG canvas.
 *
 * Compact: selected key + provider summary.
 * Expanded: full BalancesPanel.
 * Position: top-right (stacked below stats via MiniWindow default placement rule).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MiniWindow } from './MiniWindow';
import { BalancesPanel } from '../panels/BalancesPanel';
import { useStore } from '../../store/useStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

const API_DEBUG = 'http://localhost:5001/api/debug';

interface BalanceRecord {
  provider: string;
  key_masked: string;
  model?: string;
  tokens_in?: number;
  tokens_out?: number;
  cost_usd?: number;
  balance_usd: number | null;
  exhausted: boolean;
  is_free_tier?: boolean;
  call_count?: number;
}

interface BalancesResponse {
  success?: boolean;
  records?: BalanceRecord[];
  totals?: {
    total_cost_usd?: number;
  };
}

function formatUsd(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--';
  return `$${value.toFixed(2)}`;
}

function formatNum(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '--';
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(Math.round(value));
}

function BalanceCompact() {
  const selectedKey = useStore((s) => s.selectedKey);
  const setSelectedKey = useStore((s) => s.setSelectedKey);
  const [records, setRecords] = useState<BalanceRecord[]>([]);
  const [totalCost, setTotalCost] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const lastFetchRef = useRef(0);

  const fetchBalances = useCallback(async () => {
    const now = Date.now();
    if (now - lastFetchRef.current < 1000) return;
    lastFetchRef.current = now;
    try {
      const res = await fetch(`${API_DEBUG}/usage/balances`);
      if (!res.ok) return;
      const data: BalancesResponse = await res.json();
      if (data.success && Array.isArray(data.records)) {
        setRecords(data.records);
        setTotalCost(Number(data.totals?.total_cost_usd || 0));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBalances();
    const onVisibility = () => {
      if (!document.hidden) fetchBalances();
    };
    window.addEventListener('task-board-updated', fetchBalances as EventListener);
    window.addEventListener('pipeline-stats', fetchBalances as EventListener);
    window.addEventListener('focus', fetchBalances);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('task-board-updated', fetchBalances as EventListener);
      window.removeEventListener('pipeline-stats', fetchBalances as EventListener);
      window.removeEventListener('focus', fetchBalances);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [fetchBalances]);

  const grouped = useMemo(() => {
    const map = new Map<string, BalanceRecord>();
    for (const r of records) {
      const key = `${r.provider}:${r.key_masked}`;
      if (!map.has(key)) map.set(key, r);
    }
    return Array.from(map.values()).sort((a, b) => {
      if (a.exhausted !== b.exhausted) return a.exhausted ? 1 : -1;
      return a.provider.localeCompare(b.provider);
    });
  }, [records]);

  const selected = useMemo(() => {
    if (!selectedKey) return null;
    const exact = grouped.find((r) => r.provider === selectedKey.provider && r.key_masked === selectedKey.key_masked);
    if (exact) return exact;
    return grouped.find((r) => r.provider === selectedKey.provider) || null;
  }, [grouped, selectedKey]);

  const compactRows = useMemo(() => {
    if (!selected) return grouped.slice(0, 2);
    const rest = grouped.filter((r) => !(r.provider === selected.provider && r.key_masked === selected.key_masked));
    return [selected, ...rest].slice(0, 2);
  }, [grouped, selected]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#7f8893', fontSize: 8 }}>
        <span>keys: {grouped.length}</span>
        <span>cost: ${totalCost.toFixed(2)}</span>
      </div>

      <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 8 }}>
        active: {selected ? selected.provider : (selectedKey ? selectedKey.provider : 'auto')}
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        {loading && <span style={{ color: '#555', fontSize: 8 }}>loading...</span>}
        {!loading && grouped.length === 0 && <span style={{ color: '#555', fontSize: 8 }}>no usage records</span>}
        {selected ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, fontSize: 8, color: '#aeb6bf' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>key</span>
              <span style={{ maxWidth: 110, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selected.key_masked}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>balance</span>
              <span>{selected.is_free_tier ? 'free' : formatUsd(selected.balance_usd)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>cost</span>
              <span>{formatUsd(selected.cost_usd ?? null)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>tokens</span>
              <span>{formatNum((selected.tokens_in || 0) + (selected.tokens_out || 0))}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>calls</span>
              <span>{formatNum(selected.call_count ?? null)}</span>
            </div>
          </div>
        ) : (
          compactRows.map((r) => (
            <button
              key={`${r.provider}-${r.key_masked}`}
              onClick={() => setSelectedKey({ provider: r.provider, key_masked: r.key_masked })}
              style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 8,
                color: '#9ea6b0',
                background: 'transparent',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
                fontFamily: 'monospace',
              }}
              title={`${r.provider} ${r.key_masked}`}
            >
              <span style={{ maxWidth: 92, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.provider}</span>
              <span>{formatUsd(r.balance_usd)}</span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

export function MiniBalance() {
  return (
    <MiniWindow
      windowId="balance"
      title="Balance"
      icon="💳"
      position="top-right"
      compactWidth={200}
      compactHeight={120}
      compactContent={<BalanceCompact />}
      expandedContent={<BalancesPanel />}
    />
  );
}
