import { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  BarChart,
  Bar,
} from 'recharts';

interface StatsDashboardProps {
  mode?: 'compact' | 'expanded';
}

type Period = 'day' | 'week';

const API_BASE = 'http://localhost:5001/api/analytics';

interface SummaryData {
  total_runs?: number;
  success_rate?: number;
  adjusted_success_avg?: number;
  total_tokens?: number;
  total_cost_estimate?: number;
  avg_duration_s?: number;
  total_retries?: number;
  total_llm_calls?: number;
  weak_links?: Array<{ role?: string; severity?: number; reasons?: string[] }>;
  time_series?: Array<Record<string, unknown>>;
  agent_efficiency?: Array<Record<string, unknown>>;
}

interface AgentsResponse {
  agents?: Array<Record<string, unknown>>;
  weak_links?: Array<{ role?: string; severity?: number; reasons?: string[] }>;
}

interface TrendsResponse {
  data?: {
    trend?: string;
    change_pct?: number;
    period?: string;
    metric?: string;
    data_points?: Array<Record<string, unknown>>;
  };
}

interface TeamsResponse {
  teams?: Array<Record<string, unknown>>;
}

interface CostResponse {
  data?: Record<string, unknown>;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

function toNumber(v: unknown, fallback = 0): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') {
    const parsed = Number(v);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function fmtPct(v: unknown): string {
  const n = toNumber(v, 0);
  return `${n.toFixed(1)}%`;
}

function fmtUsd(v: unknown): string {
  const n = toNumber(v, 0);
  return `$${n.toFixed(3)}`;
}

function fmtDurationSec(v: unknown): string {
  const s = toNumber(v, 0);
  if (s < 60) return `${s.toFixed(1)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

export function StatsDashboard({ mode = 'expanded' }: StatsDashboardProps) {
  const [period, setPeriod] = useState<Period>('day');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [agents, setAgents] = useState<AgentsResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [teams, setTeams] = useState<TeamsResponse | null>(null);
  const [cost, setCost] = useState<CostResponse | null>(null);

  useEffect(() => {
    let alive = true;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [summaryRes, agentsRes, trendsRes, teamsRes, costRes] = await Promise.all([
          fetchJson<{ success: boolean; data?: SummaryData }>(`${API_BASE}/summary`),
          fetchJson<{ success: boolean; agents?: Array<Record<string, unknown>>; weak_links?: Array<{ role?: string; severity?: number; reasons?: string[] }> }>(`${API_BASE}/agents`),
          fetchJson<{ success: boolean; data?: TrendsResponse['data'] }>(`${API_BASE}/trends?period=${period}&metric=success_rate`),
          fetchJson<{ success: boolean; teams?: Array<Record<string, unknown>> }>(`${API_BASE}/teams`),
          fetchJson<{ success: boolean; data?: Record<string, unknown> }>(`${API_BASE}/cost`),
        ]);

        if (!alive) return;

        setSummary(summaryRes.data || null);
        setAgents({ agents: agentsRes.agents || [], weak_links: agentsRes.weak_links || [] });
        setTrends({ data: trendsRes.data || {} });
        setTeams({ teams: teamsRes.teams || [] });
        setCost({ data: costRes.data || {} });
      } catch (e) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : 'Analytics fetch failed');
      } finally {
        if (alive) setLoading(false);
      }
    };

    load();
    return () => {
      alive = false;
    };
  }, [period]);

  const chartData = useMemo(() => {
    const source = summary?.time_series || trends?.data?.data_points || [];
    return source.map((row: Record<string, unknown>, idx: number) => {
      const bucket = String(row.bucket || row.date || row.ts || idx);
      const successRate = toNumber(row.success_rate, 0);
      const tokens = toNumber(row.tokens_total, toNumber(row.tokens, toNumber(row.tokens_in, 0) + toNumber(row.tokens_out, 0)));
      const costEstimate = toNumber(row.cost_estimate, toNumber(row.cost, 0));
      return {
        bucket,
        successRate,
        tokens,
        costEstimate,
      };
    });
  }, [summary?.time_series, trends?.data?.data_points]);

  const agentRows = useMemo(() => {
    const rows = (agents?.agents || summary?.agent_efficiency || []) as Array<Record<string, unknown>>;
    const weakSet = new Set((agents?.weak_links || summary?.weak_links || []).map(w => String(w.role || '').toLowerCase()));
    return rows.map((a) => {
      const role = String(a.role || 'unknown');
      return {
        role,
        calls: toNumber(a.calls, 0),
        tokens: toNumber(a.tokens_total, toNumber(a.tokens, 0)),
        duration: toNumber(a.avg_duration, toNumber(a.duration_s, 0)),
        successRate: toNumber(a.success_rate, 0),
        retries: toNumber(a.retries, 0),
        weak: weakSet.has(role.toLowerCase()),
      };
    });
  }, [agents?.agents, agents?.weak_links, summary?.agent_efficiency, summary?.weak_links]);

  const teamRows = useMemo(() => {
    return ((teams?.teams || []) as Array<Record<string, unknown>>).map((t) => ({
      preset: String(t.preset || '-'),
      successRate: toNumber(t.success_rate, 0),
      avgDuration: toNumber(t.avg_duration_s, 0),
      totalCost: toNumber(t.total_cost, 0),
    }));
  }, [teams?.teams]);

  const summaryCards = [
    { label: 'Total Runs', value: String(summary?.total_runs ?? '-') },
    { label: 'Success %', value: fmtPct(summary?.success_rate ?? 0) },
    { label: 'Avg Duration', value: fmtDurationSec(summary?.avg_duration_s ?? 0) },
    { label: 'Cost', value: fmtUsd(summary?.total_cost_estimate ?? 0) },
  ];

  if (mode === 'compact') {
    return (
      <div style={{ border: '1px solid #262626', background: '#111', borderRadius: 4, padding: 8 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 6 }}>
          {summaryCards.map((card) => (
            <div key={card.label} style={{ border: '1px solid #2b2b2b', borderRadius: 4, padding: '6px 8px', background: '#1a1a1a' }}>
              <div style={{ color: '#777', fontSize: 9, textTransform: 'uppercase', letterSpacing: 0.8 }}>{card.label}</div>
              <div style={{ color: '#e0e0e0', fontSize: 12, marginTop: 4 }}>{loading ? '-' : card.value}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, color: '#ddd', fontFamily: 'monospace' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 10, color: '#8a8a8a', textTransform: 'uppercase', letterSpacing: 1.2 }}>
          Stats Dashboard
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            onClick={() => setPeriod('day')}
            style={{
              border: '1px solid #2e2e2e',
              borderRadius: 3,
              padding: '3px 8px',
              background: period === 'day' ? '#1f2a22' : '#1a1a1a',
              color: period === 'day' ? '#22c55e' : '#999',
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            day
          </button>
          <button
            onClick={() => setPeriod('week')}
            style={{
              border: '1px solid #2e2e2e',
              borderRadius: 3,
              padding: '3px 8px',
              background: period === 'week' ? '#1f2a22' : '#1a1a1a',
              color: period === 'week' ? '#22c55e' : '#999',
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            week
          </button>
        </div>
      </div>

      {error && (
        <div style={{ border: '1px solid #4a1d1d', background: '#1f1111', color: '#ef4444', borderRadius: 4, padding: '8px 10px', fontSize: 10 }}>
          Analytics error: {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 8 }}>
        {summaryCards.map((card) => (
          <div key={card.label} style={{ border: '1px solid #2a2a2a', background: '#1a1a1a', borderRadius: 4, padding: '8px 10px' }}>
            <div style={{ color: '#777', fontSize: 9, textTransform: 'uppercase', letterSpacing: 0.8 }}>{card.label}</div>
            <div style={{ color: '#f0f0f0', fontSize: 14, marginTop: 6 }}>{loading ? '-' : card.value}</div>
          </div>
        ))}
      </div>

      <div style={{ border: '1px solid #2a2a2a', background: '#111', borderRadius: 4, padding: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ color: '#9a9a9a', fontSize: 10 }}>Trend ({period})</span>
          <span style={{ color: trends?.data?.trend === 'down' ? '#ef4444' : '#22c55e', fontSize: 10 }}>
            {trends?.data?.trend || '-'} {typeof trends?.data?.change_pct === 'number' ? `${trends.data.change_pct.toFixed(1)}%` : ''}
          </span>
        </div>
        <div style={{ width: '100%', height: 240 }}>
          <ResponsiveContainer>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#222" strokeDasharray="3 3" />
              <XAxis dataKey="bucket" stroke="#666" tick={{ fill: '#888', fontSize: 10 }} />
              <YAxis yAxisId="left" stroke="#666" tick={{ fill: '#888', fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" stroke="#666" tick={{ fill: '#888', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 4, color: '#ddd' }}
                labelStyle={{ color: '#aaa' }}
              />
              <Legend wrapperStyle={{ color: '#aaa', fontSize: 10 }} />
              <Line yAxisId="left" type="monotone" dataKey="successRate" name="success %" stroke="#22c55e" dot={false} strokeWidth={2} />
              <Line yAxisId="right" type="monotone" dataKey="tokens" name="tokens" stroke="#9ca3af" dot={false} strokeWidth={1.8} />
              <Line yAxisId="right" type="monotone" dataKey="costEstimate" name="cost" stroke="#ef4444" dot={false} strokeWidth={1.5} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(165px, 1fr))', gap: 8 }}>
        {agentRows.length === 0 && (
          <div style={{ border: '1px solid #2a2a2a', background: '#111', borderRadius: 4, padding: 12, color: '#888', fontSize: 10 }}>
            {loading ? 'Loading agents...' : 'No agent data'}
          </div>
        )}
        {agentRows.map((row) => (
          <div
            key={row.role}
            style={{
              border: `1px solid ${row.weak ? '#4a1d1d' : '#2a2a2a'}`,
              background: row.weak ? '#1a1212' : '#111',
              borderRadius: 4,
              padding: 10,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: '#e0e0e0', fontSize: 10, textTransform: 'uppercase' }}>{row.role}</span>
              {row.weak && <span style={{ color: '#ef4444', fontSize: 9 }}>WEAK</span>}
            </div>
            <div style={{ color: '#9a9a9a', fontSize: 9, lineHeight: 1.6 }}>
              <div>calls: <span style={{ color: '#ddd' }}>{row.calls}</span></div>
              <div>tokens: <span style={{ color: '#ddd' }}>{row.tokens}</span></div>
              <div>duration: <span style={{ color: '#ddd' }}>{row.duration.toFixed(1)}s</span></div>
              <div>success: <span style={{ color: row.successRate >= 60 ? '#22c55e' : '#ef4444' }}>{row.successRate.toFixed(1)}%</span></div>
              <div>retries: <span style={{ color: '#ddd' }}>{row.retries}</span></div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 8 }}>
        <div style={{ border: '1px solid #2a2a2a', borderRadius: 4, background: '#111', padding: 10 }}>
          <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>Team Comparison</div>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={teamRows}>
                <CartesianGrid stroke="#222" strokeDasharray="3 3" />
                <XAxis dataKey="preset" stroke="#666" tick={{ fill: '#888', fontSize: 10 }} />
                <YAxis stroke="#666" tick={{ fill: '#888', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 4 }} />
                <Legend wrapperStyle={{ color: '#aaa', fontSize: 10 }} />
                <Bar dataKey="successRate" name="success %" fill="#22c55e" radius={[3, 3, 0, 0]} />
                <Bar dataKey="avgDuration" name="avg duration" fill="#9ca3af" radius={[3, 3, 0, 0]} />
                <Bar dataKey="totalCost" name="cost" fill="#ef4444" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{ border: '1px solid #2a2a2a', borderRadius: 4, background: '#111', padding: 10 }}>
          <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>Cost Snapshot</div>
          <div style={{ color: '#a0a0a0', fontSize: 9, lineHeight: 1.7 }}>
            <div>total cost: <span style={{ color: '#ddd' }}>{fmtUsd(summary?.total_cost_estimate ?? 0)}</span></div>
            <div>total tokens: <span style={{ color: '#ddd' }}>{toNumber(summary?.total_tokens, 0)}</span></div>
            <div>LLM calls: <span style={{ color: '#ddd' }}>{toNumber(summary?.total_llm_calls, 0)}</span></div>
            <div>retries: <span style={{ color: '#ddd' }}>{toNumber(summary?.total_retries, 0)}</span></div>
            <div>cost payload: <span style={{ color: '#ddd' }}>{cost?.data ? 'ok' : '-'}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
