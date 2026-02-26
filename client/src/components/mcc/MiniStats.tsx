/**
 * MARKER_154.14A: MiniStats — compact statistics overlay in DAG canvas.
 *
 * Compact: 4 key numbers (runs, success%, avg duration, total cost).
 * Expanded: full stats dashboard.
 * Position: top-right.
 * Data: GET /api/analytics/summary
 *
 * @phase 154
 * @wave 4
 * @status active
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { MiniWindow } from './MiniWindow';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { useDevPanelStore } from '../../store/useDevPanelStore';
import { useMCCDiagnostics } from '../../hooks/useMCCDiagnostics';

const API_BASE = 'http://localhost:5001/api';

interface SummaryData {
  total_pipelines: number;
  success_rate: number;
  avg_duration_s: number;
  total_cost_usd: number;
  total_llm_calls: number;
  total_tokens: number;
  // Optional per-team breakdown
  by_preset?: Record<string, {
    count: number;
    success_rate: number;
    avg_duration_s: number;
  }>;
}

// MARKER_154.14A_FIX: Normalize API response to match SummaryData interface
function normalizeSummary(raw: any): SummaryData {
  // API may wrap in { success, data } or return flat
  const d = raw?.data || raw;
  return {
    total_pipelines: d.total_pipelines ?? d.total_runs ?? 0,
    success_rate: d.success_rate ?? 0,
    avg_duration_s: d.avg_duration_s ?? 0,
    total_cost_usd: d.total_cost_usd ?? d.total_cost_estimate ?? 0,
    total_llm_calls: d.total_llm_calls ?? 0,
    total_tokens: d.total_tokens ?? 0,
    by_preset: d.by_preset ?? d.tasks_by_preset ? Object.fromEntries(
      Object.entries(d.tasks_by_preset || {}).map(([k, v]: [string, any]) => [
        k,
        typeof v === 'number'
          ? { count: v, success_rate: 0, avg_duration_s: 0 }
          : { count: v?.count ?? 0, success_rate: v?.success_rate ?? 0, avg_duration_s: v?.avg_duration_s ?? 0 },
      ])
    ) : undefined,
  };
}

// MARKER_155.STATS.UI: Agent metrics data
interface AgentSummary {
  agent_type: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  avg_duration: number;
  avg_quality: number;
  total_tokens: number;
  total_cost: number;
  recent_remarks: string[];
}

interface AgentsData {
  period: string;
  agents: Record<string, AgentSummary>;
}

function useSummaryData() {
  const [data, setData] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const lastFetchRef = useRef(0);

  const fetch_ = useCallback(async () => {
    const now = Date.now();
    if (now - lastFetchRef.current < 1000) return;
    lastFetchRef.current = now;
    try {
      const res = await fetch(`${API_BASE}/analytics/summary`);
      if (!res.ok) return;
      const json = await res.json();
      // MARKER_154.14A_FIX: Normalize response (API wraps in {success, data})
      setData(normalizeSummary(json));
    } catch {
      // API may not be available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch_();
    const onVisibility = () => {
      if (!document.hidden) fetch_();
    };
    window.addEventListener('pipeline-stats', fetch_ as EventListener);
    window.addEventListener('task-board-updated', fetch_ as EventListener);
    window.addEventListener('focus', fetch_);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('pipeline-stats', fetch_ as EventListener);
      window.removeEventListener('task-board-updated', fetch_ as EventListener);
      window.removeEventListener('focus', fetch_);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [fetch_]);

  return { data, loading, refresh: fetch_ };
}

// MARKER_155.STATS.UI: Hook for agent metrics
function useAgentsData() {
  const [data, setData] = useState<AgentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const lastFetchRef = useRef(0);

  const fetch_ = useCallback(async () => {
    const now = Date.now();
    if (now - lastFetchRef.current < 1500) return;
    lastFetchRef.current = now;
    try {
      const res = await fetch(`${API_BASE}/analytics/agents/summary?period=7d`);
      if (!res.ok) return;
      const json = await res.json();
      if (json.success) {
        setData(json);
      }
    } catch {
      // API may not be available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch_();
    const onVisibility = () => {
      if (!document.hidden) fetch_();
    };
    window.addEventListener('pipeline-stats', fetch_ as EventListener);
    window.addEventListener('task-board-updated', fetch_ as EventListener);
    window.addEventListener('focus', fetch_);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('pipeline-stats', fetch_ as EventListener);
      window.removeEventListener('task-board-updated', fetch_ as EventListener);
      window.removeEventListener('focus', fetch_);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [fetch_]);

  return { data, loading, refresh: fetch_ };
}

// Single stat box
function StatBox({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div style={{ textAlign: 'center', flex: 1 }}>
      <div style={{
        color: NOLAN_PALETTE.text,
        fontSize: 14,
        fontWeight: 700,
        lineHeight: 1,
      }}>
        {value}
        {unit && <span style={{ fontSize: 8, color: '#555', marginLeft: 1 }}>{unit}</span>}
      </div>
      <div style={{
        color: '#555',
        fontSize: 7,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        marginTop: 2,
      }}>
        {label}
      </div>
    </div>
  );
}

// Compact: 4 stat boxes
function StatsCompact() {
  const { data, loading } = useSummaryData();
  const setStatsMode = useDevPanelStore(s => s.setStatsMode);
  const diagnostics = useMCCDiagnostics();

  if (loading || !data) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <span style={{ color: '#444', fontSize: 9 }}>
          {loading ? 'Loading...' : 'No stats yet'}
        </span>
      </div>
    );
  }

  const formatDuration = (s: number) => {
    if (s < 60) return `${Math.round(s)}s`;
    return `${Math.round(s / 60)}m`;
  };

  const rate = data.success_rate ?? 0;
  const successColor = rate >= 70 ? '#8a8' : rate >= 50 ? '#aa8' : '#a66';
  const cost = data.total_cost_usd ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'center', gap: 8 }}>
      <div style={{ display: 'flex', gap: 4 }}>
        <StatBox label="Runs" value={data.total_pipelines ?? 0} />
        <StatBox
          label="Success"
          value={
            <span style={{ color: successColor }}>{Math.round(rate)}%</span> as any
          }
        />
      </div>
      <div style={{ display: 'flex', gap: 4 }}>
        <StatBox label="Avg Time" value={formatDuration(data.avg_duration_s ?? 0)} />
        <StatBox label="Cost" value={`$${cost.toFixed(2)}`} />
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginTop: 2,
        paddingTop: 6,
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
      }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <span style={{
            fontSize: 8,
            color: diagnostics.buildDesign?.verifier?.decision === 'pass' ? '#67e6bf' : diagnostics.buildDesign?.verifier?.decision === 'warn' ? '#f7d070' : '#ef8d8d',
          }}>
            graph:{String(diagnostics.buildDesign?.verifier?.decision || '-')}
          </span>
          <span style={{
            fontSize: 8,
            color: diagnostics.runtimeHealth?.ok ? '#67e6bf' : '#ef8d8d',
          }}>
            rt:{diagnostics.runtimeHealth?.ok ? 'ok' : 'down'}
          </span>
        </div>
        <button
          onClick={() => {
            setStatsMode('diagnostics');
          }}
          style={{
            border: '1px solid #2e2e2e',
            borderRadius: 3,
            background: '#151515',
            color: '#9aa2ad',
            fontSize: 8,
            padding: '1px 6px',
            cursor: 'pointer',
            fontFamily: 'monospace',
          }}
          title="Open diagnostics"
        >
          diag ↗
        </button>
      </div>
    </div>
  );
}

// Agent icon mapping
const AGENT_ICONS: Record<string, string> = {
  scout: '🕵️',
  researcher: '🔬',
  architect: '👨‍💻',
  coder: '💻',
  verifier: '✅',
};

// Agent Performance Section
function AgentPerformanceSection() {
  const { data, loading } = useAgentsData();

  if (loading) {
    return (
      <div style={{ color: '#444', fontSize: 11, padding: '12px 0' }}>
        Loading agent metrics...
      </div>
    );
  }

  if (!data || !data.agents) {
    return (
      <div style={{ color: '#444', fontSize: 11, padding: '12px 0' }}>
        No agent data available
      </div>
    );
  }

  const agents = Object.entries(data.agents);
  
  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ 
        color: NOLAN_PALETTE.textMuted, 
        fontSize: 9, 
        marginBottom: 12, 
        textTransform: 'uppercase',
        borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
        paddingBottom: 8,
      }}>
        Agent Performance ({data.period})
      </div>
      
      {agents.map(([agentType, stats]) => {
        const successRate = stats.total_runs > 0 
          ? Math.round((stats.successful_runs / stats.total_runs) * 100) 
          : 0;
        
        return (
          <div
            key={agentType}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 0',
              borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
            }}
          >
            <span style={{ fontSize: 12, width: 20 }}>
              {AGENT_ICONS[agentType] || '🤖'}
            </span>
            <span style={{ 
              color: NOLAN_PALETTE.text, 
              fontSize: 10, 
              width: 80,
              textTransform: 'capitalize',
            }}>
              {agentType}
            </span>
            <span style={{ color: '#666', fontSize: 9, width: 50 }}>
              {stats.total_runs} runs
            </span>
            <span style={{
              color: successRate >= 70 ? '#8a8' : successRate >= 50 ? '#aa8' : '#a66',
              fontSize: 9,
              width: 40,
            }}>
              {successRate}%
            </span>
            <span style={{ color: '#666', fontSize: 9, width: 60 }}>
              ~{Math.round(stats.avg_duration)}s
            </span>
            <span style={{ color: '#666', fontSize: 9 }}>
              ${stats.total_cost.toFixed(2)}
            </span>
          </div>
        );
      })}
      
      {/* Recent Remarks */}
      {agents.some(([_, s]) => s.recent_remarks.length > 0) && (
        <div style={{ marginTop: 12 }}>
          <div style={{ 
            color: NOLAN_PALETTE.textMuted, 
            fontSize: 8, 
            marginBottom: 8,
          }}>
            Recent Architect Remarks
          </div>
          {agents.flatMap(([agentType, stats]) => 
            stats.recent_remarks.map((remark, idx) => (
              <div
                key={`${agentType}-${idx}`}
                style={{
                  padding: '4px 8px',
                  marginBottom: 4,
                  background: NOLAN_PALETTE.bg,
                  borderRadius: 4,
                  fontSize: 8,
                  color: '#888',
                }}
              >
                <span style={{ color: NOLAN_PALETTE.textAccent }}>{AGENT_ICONS[agentType]}</span>
                {' '}{remark}
              </div>
            ))
          ).slice(0, 3)}
        </div>
      )}
    </div>
  );
}

// Expanded: detailed stats
function StatsExpanded() {
  const { data, loading, refresh } = useSummaryData();

  if (loading || !data) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <span style={{ color: '#444', fontSize: 11 }}>
          {loading ? 'Loading stats...' : 'No analytics data available'}
        </span>
      </div>
    );
  }

  const presets = data.by_preset ? Object.entries(data.by_preset) : [];

  return (
    <div style={{ padding: '12px 16px', fontFamily: 'monospace' }}>
      {/* Summary row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <StatBox label="Total Runs" value={data.total_pipelines ?? 0} />
        <StatBox label="Success Rate" value={`${Math.round(data.success_rate ?? 0)}%`} />
        <StatBox label="Avg Duration" value={`${Math.round(data.avg_duration_s ?? 0)}s`} />
        <StatBox label="Total Cost" value={`$${(data.total_cost_usd ?? 0).toFixed(2)}`} />
      </div>

      {/* Token stats */}
      <div style={{
        display: 'flex',
        gap: 16,
        marginBottom: 20,
        padding: '8px 12px',
        background: NOLAN_PALETTE.bg,
        borderRadius: 6,
      }}>
        <StatBox label="LLM Calls" value={data.total_llm_calls} />
        <StatBox label="Tokens" value={
          data.total_tokens > 1000000 ? `${(data.total_tokens / 1000000).toFixed(1)}M` :
          data.total_tokens > 1000 ? `${(data.total_tokens / 1000).toFixed(0)}K` :
          data.total_tokens
        } />
      </div>

      {/* Per-team breakdown */}
      {presets.length > 0 && (
        <>
          <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, marginBottom: 8, textTransform: 'uppercase' }}>
            Team Breakdown
          </div>
          {presets.map(([preset, stats]) => (
            <div
              key={preset}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '6px 0',
                borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
              }}
            >
              <span style={{ color: NOLAN_PALETTE.textAccent, fontSize: 10, width: 100 }}>
                {preset}
              </span>
              <span style={{ color: NOLAN_PALETTE.text, fontSize: 10 }}>
                {stats.count} runs
              </span>
              <span style={{
                color: stats.success_rate >= 70 ? '#8a8' : '#a66',
                fontSize: 10,
              }}>
                {Math.round(stats.success_rate)}%
              </span>
              <span style={{ color: '#555', fontSize: 10 }}>
                ~{Math.round(stats.avg_duration_s)}s
              </span>
            </div>
          ))}
        </>
      )}

      {/* MARKER_155.STATS.UI: Agent Performance Section */}
      <AgentPerformanceSection />

      {/* Refresh button */}
      <button
        onClick={refresh}
        style={{
          marginTop: 16,
          padding: '4px 12px',
          background: NOLAN_PALETTE.bg,
          border: `1px solid ${NOLAN_PALETTE.border}`,
          borderRadius: 4,
          color: NOLAN_PALETTE.textMuted,
          fontSize: 9,
          cursor: 'pointer',
          fontFamily: 'monospace',
        }}
      >
        ↻ Refresh
      </button>
    </div>
  );
}

export function MiniStats() {
  return (
    <MiniWindow
      windowId="stats" // MARKER_155.DRAGGABLE.012: Unique ID for position persistence
      title="Stats"
      icon="📊"
      position="top-right"
      compactWidth={200}
      compactHeight={120}
      compactContent={<StatsCompact />}
      expandedContent={<StatsExpanded />}
    />
  );
}
