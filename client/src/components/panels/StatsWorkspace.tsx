import { useMemo } from 'react';
import { StatsDashboard } from './StatsDashboard';
import { useDevPanelStore } from '../../store/useDevPanelStore';
import { useMCCStore } from '../../store/useMCCStore';
import { useMCCDiagnostics } from '../../hooks/useMCCDiagnostics';

function tsLabel(ts: number | null): string {
  if (!ts) return '-';
  return new Date(ts).toLocaleTimeString();
}

function decisionColor(decision: string): string {
  const d = decision.toLowerCase();
  if (d === 'pass') return '#67e6bf';
  if (d === 'warn') return '#f7d070';
  return '#ef8d8d';
}

function runtimeColor(ok: boolean): string {
  return ok ? '#67e6bf' : '#ef8d8d';
}

function DiagnosticsPanel() {
  const {
    loading,
    error,
    lastUpdatedAt,
    lastReason,
    runtimeHealth,
    buildDesign,
    eventLog,
    refresh,
  } = useMCCDiagnostics();

  const verifier = buildDesign?.verifier || {};
  const spectral = verifier.spectral || {};
  const decision = String(verifier.decision || 'warn');
  const focusRestorePolicy = useMCCStore(s => s.focusRestorePolicy);
  const focusRestoreSource = useMCCStore(s => s.focusRestoreSource);

  const graphNodeCount = Array.isArray(buildDesign?.design_graph?.nodes)
    ? buildDesign?.design_graph?.nodes?.length || 0
    : 0;
  const graphEdgeCount = Array.isArray(buildDesign?.design_graph?.edges)
    ? buildDesign?.design_graph?.edges?.length || 0
    : 0;

  const summary = useMemo(() => ([
    { k: 'Graph Health', v: decision.toUpperCase(), c: decisionColor(decision) },
    { k: 'Runtime', v: runtimeHealth?.ok ? 'OK' : 'DOWN', c: runtimeColor(Boolean(runtimeHealth?.ok)) },
    { k: 'Restore Policy', v: focusRestorePolicy === 'scope_first' ? 'SCOPE_FIRST' : 'SELECTION_FIRST', c: '#8ecbff' },
    { k: 'Restore Source', v: (focusRestoreSource || '-').toUpperCase(), c: '#9ec8a4' },
    { k: 'Updated', v: tsLabel(lastUpdatedAt), c: '#bbb' },
    { k: 'Trigger', v: lastReason || '-', c: '#9aa2ad' },
  ]), [decision, runtimeHealth?.ok, focusRestorePolicy, focusRestoreSource, lastUpdatedAt, lastReason]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontFamily: 'monospace' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 10, color: '#8a8a8a', textTransform: 'uppercase', letterSpacing: 1.2 }}>
          Diagnostics
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={() => refresh(false)}
            style={{
              border: '1px solid #2e2e2e',
              borderRadius: 3,
              padding: '3px 8px',
              background: '#1a1a1a',
              color: '#aaa',
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            refresh
          </button>
          <button
            onClick={() => refresh(true)}
            style={{
              border: '1px solid #2e2e2e',
              borderRadius: 3,
              padding: '3px 8px',
              background: '#1a1a1a',
              color: '#8ecbff',
              fontSize: 10,
              cursor: 'pointer',
            }}
            title="Force runtime health probe (bypass short cache)"
          >
            force health
          </button>
        </div>
      </div>

      {error && (
        <div style={{ border: '1px solid #4a1d1d', background: '#1f1111', color: '#ef4444', borderRadius: 4, padding: '8px 10px', fontSize: 10 }}>
          Diagnostics error: {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
        {summary.map(item => (
          <div key={item.k} style={{ border: '1px solid #2a2a2a', background: '#141414', borderRadius: 4, padding: '8px 10px' }}>
            <div style={{ color: '#777', fontSize: 9, textTransform: 'uppercase', letterSpacing: 0.8 }}>{item.k}</div>
            <div style={{ color: item.c, fontSize: 13, marginTop: 6 }}>{loading ? '-' : item.v}</div>
          </div>
        ))}
      </div>

      <div style={{ border: '1px solid #2a2a2a', background: '#111', borderRadius: 4, padding: 10 }}>
        <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>Layout Objective / Verifier</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 8, fontSize: 10 }}>
          <span style={{ color: '#aaa' }}>nodes: <span style={{ color: '#ddd' }}>{graphNodeCount}</span></span>
          <span style={{ color: '#aaa' }}>edges: <span style={{ color: '#ddd' }}>{graphEdgeCount}</span></span>
          <span style={{ color: '#aaa' }}>acyclic: <span style={{ color: verifier.acyclic ? '#67e6bf' : '#ef8d8d' }}>{String(Boolean(verifier.acyclic))}</span></span>
          <span style={{ color: '#aaa' }}>monotonic: <span style={{ color: verifier.monotonic_knowledge_y ? '#67e6bf' : '#ef8d8d' }}>{String(Boolean(verifier.monotonic_knowledge_y))}</span></span>
          <span style={{ color: '#aaa' }}>λ2: <span style={{ color: '#ddd' }}>{Number(spectral.lambda2 || 0).toFixed(3)}</span></span>
          <span style={{ color: '#aaa' }}>gap: <span style={{ color: '#ddd' }}>{Number(spectral.eigengap || 0).toFixed(3)}</span></span>
          <span style={{ color: '#aaa' }}>components: <span style={{ color: '#ddd' }}>{Number(spectral.component_count || 0)}</span></span>
          <span style={{ color: '#aaa' }}>orphan rate: <span style={{ color: '#ddd' }}>{(Number(verifier.orphan_rate || 0) * 100).toFixed(1)}%</span></span>
        </div>
      </div>

      <div style={{ border: '1px solid #2a2a2a', background: '#111', borderRadius: 4, padding: 10 }}>
        <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>Runtime Health</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8, fontSize: 10 }}>
          <span style={{ color: '#aaa' }}>enabled: <span style={{ color: '#ddd' }}>{String(Boolean(runtimeHealth?.enabled))}</span></span>
          <span style={{ color: '#aaa' }}>backend: <span style={{ color: '#ddd' }}>{runtimeHealth?.backend || '-'}</span></span>
          <span style={{ color: '#aaa' }}>module: <span style={{ color: '#ddd' }}>{runtimeHealth?.runtime_module || '-'}</span></span>
          <span style={{ color: '#aaa' }}>detail: <span style={{ color: '#ddd' }}>{runtimeHealth?.detail || '-'}</span></span>
        </div>
      </div>

      <div style={{ border: '1px solid #2a2a2a', background: '#111', borderRadius: 4, padding: 10 }}>
        <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>Trigger Log (event-driven)</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 180, overflowY: 'auto' }}>
          {eventLog.length === 0 && (
            <div style={{ color: '#666', fontSize: 10 }}>No trigger events yet</div>
          )}
          {eventLog.map((e, idx) => (
            <div key={`${e.ts}-${idx}`} style={{ fontSize: 10, color: '#9097a2', display: 'flex', gap: 8 }}>
              <span style={{ color: '#666', minWidth: 72 }}>{new Date(e.ts).toLocaleTimeString()}</span>
              <span style={{ color: '#8aa0b8', minWidth: 120 }}>{e.source}</span>
              <span style={{ color: e.action === 'fetch' ? '#67e6bf' : e.action === 'queue' ? '#f7d070' : '#8a8f98', minWidth: 52 }}>{e.action}</span>
              <span style={{ color: '#7d838e' }}>{e.note}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function StatsWorkspace() {
  const statsMode = useDevPanelStore(s => s.statsMode);
  const setStatsMode = useDevPanelStore(s => s.setStatsMode);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%', overflowY: 'auto' }}>
      <div style={{
        display: 'flex',
        gap: 6,
        alignItems: 'center',
        border: '1px solid #2a2a2a',
        borderRadius: 4,
        padding: 6,
        background: '#111',
        width: 'fit-content',
      }}>
        <button
          onClick={() => setStatsMode('ops')}
          style={{
            border: '1px solid #2e2e2e',
            borderRadius: 3,
            padding: '3px 8px',
            background: statsMode === 'ops' ? '#1f2a22' : '#1a1a1a',
            color: statsMode === 'ops' ? '#22c55e' : '#999',
            fontSize: 10,
            cursor: 'pointer',
            fontFamily: 'monospace',
          }}
        >
          Ops
        </button>
        <button
          onClick={() => setStatsMode('diagnostics')}
          style={{
            border: '1px solid #2e2e2e',
            borderRadius: 3,
            padding: '3px 8px',
            background: statsMode === 'diagnostics' ? '#1f2830' : '#1a1a1a',
            color: statsMode === 'diagnostics' ? '#8ecbff' : '#999',
            fontSize: 10,
            cursor: 'pointer',
            fontFamily: 'monospace',
          }}
        >
          Diagnostics
        </button>
      </div>

      {statsMode === 'ops' ? <StatsDashboard mode="expanded" /> : <DiagnosticsPanel />}
    </div>
  );
}
