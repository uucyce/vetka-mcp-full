import { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ScatterChart,
  Scatter,
  CartesianGrid,
  XAxis,
  YAxis,
} from 'recharts';

interface TaskDrillDownProps {
  isOpen: boolean;
  taskId: string | null;
  onClose: () => void;
}

const API_BASE = 'http://localhost:5001/api/analytics';
const PIE_COLORS = ['#22c55e', '#9ca3af', '#ef4444', '#3b82f6', '#f59e0b', '#a855f7'];

interface TimelineEvent {
  role?: string;
  event?: string;
  offset_s?: number;
  start_offset?: number;
  duration_s?: number;
}

interface TaskAnalyticsData {
  task_id?: string;
  title?: string;
  status?: string;
  preset?: string;
  phase_type?: string;
  duration_s?: number;
  llm_calls?: number;
  token_distribution?: Array<{ role?: string; tokens?: number; pct?: number }>;
  timeline_events?: TimelineEvent[];
  agent_stats?: Record<string, { calls?: number; tokens_in?: number; tokens_out?: number; duration_s?: number }>;
  adjusted_stats?: {
    adjusted_success?: number;
    user_feedback?: string;
    has_user_feedback?: boolean;
  };
}

function toNumber(v: unknown, fallback = 0): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return fallback;
}

export function TaskDrillDown({ isOpen, taskId, onClose }: TaskDrillDownProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TaskAnalyticsData | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const onEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen || !taskId) return;

    let alive = true;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/task/${encodeURIComponent(taskId)}`);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const json = await res.json();
        if (!alive) return;
        if (json?.success && json?.data) {
          setData(json.data as TaskAnalyticsData);
        } else {
          setData(null);
          setError(json?.error || 'Task analytics unavailable');
        }
      } catch (e) {
        if (!alive) return;
        setData(null);
        setError(e instanceof Error ? e.message : 'Failed to load task analytics');
      } finally {
        if (alive) setLoading(false);
      }
    };

    load();
    return () => {
      alive = false;
    };
  }, [isOpen, taskId]);

  const timelineEvents = data?.timeline_events || [];
  const firstEvent = timelineEvents[0];
  const timelineMode: 'real' | 'legacy' | 'none' =
    firstEvent && typeof firstEvent.offset_s === 'number'
      ? 'real'
      : firstEvent && typeof firstEvent.start_offset === 'number'
        ? 'legacy'
        : 'none';

  const roleOrder = useMemo(() => {
    const set = new Set<string>();
    timelineEvents.forEach((e) => set.add(String(e.role || 'unknown')));
    return Array.from(set);
  }, [timelineEvents]);

  const realTimelinePoints = useMemo(() => {
    const roleIndex = new Map<string, number>();
    roleOrder.forEach((role, idx) => roleIndex.set(role, idx));

    return timelineEvents
      .filter((e) => typeof e.offset_s === 'number')
      .map((e, idx) => ({
        id: idx,
        x: toNumber(e.offset_s, 0),
        y: roleIndex.get(String(e.role || 'unknown')) ?? 0,
        role: String(e.role || 'unknown'),
        event: String(e.event || ''),
      }));
  }, [timelineEvents, roleOrder]);

  const legacyBars = useMemo(() => {
    return timelineEvents
      .filter((e) => typeof e.start_offset === 'number')
      .map((e) => ({
        role: String(e.role || 'unknown'),
        start: toNumber(e.start_offset, 0),
        duration: Math.max(0.2, toNumber(e.duration_s, 0.2)),
      }));
  }, [timelineEvents]);

  const legacyMaxEnd = useMemo(() => {
    if (legacyBars.length === 0) return 1;
    return Math.max(...legacyBars.map((b) => b.start + b.duration), 1);
  }, [legacyBars]);

  const pieData = (data?.token_distribution || []).map((d) => ({
    name: String(d.role || '-'),
    value: toNumber(d.tokens, 0),
    pct: toNumber(d.pct, 0),
  }));

  const agentRows = Object.entries(data?.agent_stats || {}).map(([role, stats]) => ({
    role,
    calls: toNumber(stats.calls, 0),
    tokens: toNumber(stats.tokens_in, 0) + toNumber(stats.tokens_out, 0),
    duration: toNumber(stats.duration_s, 0),
  }));

  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 12000,
        background: 'rgba(0,0,0,0.62)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(1100px, 96vw)',
          maxHeight: '92vh',
          overflowY: 'auto',
          border: '1px solid #2a2a2a',
          borderRadius: 6,
          background: '#111',
          color: '#ddd',
          fontFamily: 'monospace',
          padding: 14,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div>
            <div style={{ color: '#f0f0f0', fontSize: 14 }}>{data?.title || taskId || '-'}</div>
            <div style={{ color: '#8a8a8a', fontSize: 10, marginTop: 4 }}>
              status: {data?.status || '-'} | preset: {data?.preset || '-'} | duration: {toNumber(data?.duration_s, 0).toFixed(1)}s | calls: {toNumber(data?.llm_calls, 0)}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ border: '1px solid #333', background: '#1a1a1a', color: '#aaa', borderRadius: 3, padding: '4px 8px', cursor: 'pointer' }}
          >
            Close
          </button>
        </div>

        {loading && <div style={{ color: '#888', fontSize: 11, padding: '8px 2px' }}>Loading task analytics...</div>}
        {error && <div style={{ color: '#ef4444', fontSize: 11, padding: '8px 2px' }}>{error}</div>}

        {!loading && !error && (
          <>
            <div style={{ border: '1px solid #262626', borderRadius: 4, background: '#1a1a1a', padding: 10, marginBottom: 10 }}>
              <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>
                Timeline ({timelineMode === 'real' ? 'real offset_s events' : timelineMode === 'legacy' ? 'legacy start_offset bars' : 'n/a'})
              </div>

              {timelineMode === 'real' && realTimelinePoints.length > 0 && (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer>
                    <ScatterChart>
                      <CartesianGrid stroke="#222" strokeDasharray="3 3" />
                      <XAxis type="number" dataKey="x" name="offset" unit="s" stroke="#666" tick={{ fill: '#888', fontSize: 10 }} />
                      <YAxis
                        type="number"
                        dataKey="y"
                        domain={[0, Math.max(0, roleOrder.length - 1)]}
                        allowDecimals={false}
                        tickFormatter={(v) => roleOrder[v] || ''}
                        stroke="#666"
                        tick={{ fill: '#888', fontSize: 10 }}
                      />
                      <Tooltip
                        cursor={{ strokeDasharray: '3 3' }}
                        contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 4 }}
                        formatter={(value: any, name: any, entry: any) => {
                          if (name === 'offset') return [`${value}s`, 'offset'];
                          return [value, name];
                        }}
                        labelFormatter={(_, payload: any) => {
                          const p = payload?.[0]?.payload;
                          return p ? `${p.role} ${p.event}` : '';
                        }}
                      />
                      <Scatter name="offset" data={realTimelinePoints} fill="#22c55e" />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              )}

              {timelineMode === 'legacy' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {legacyBars.map((bar, idx) => {
                    const leftPct = (bar.start / legacyMaxEnd) * 100;
                    const widthPct = (bar.duration / legacyMaxEnd) * 100;
                    return (
                      <div key={`${bar.role}_${idx}`} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 60px', gap: 8, alignItems: 'center' }}>
                        <span style={{ color: '#aaa', fontSize: 10 }}>{bar.role}</span>
                        <div style={{ position: 'relative', height: 10, background: '#0f0f0f', border: '1px solid #242424', borderRadius: 8, overflow: 'hidden' }}>
                          <div
                            style={{
                              position: 'absolute',
                              left: `${leftPct}%`,
                              width: `${Math.max(widthPct, 1.2)}%`,
                              top: 0,
                              bottom: 0,
                              background: '#9ca3af',
                            }}
                          />
                        </div>
                        <span style={{ color: '#777', fontSize: 10 }}>{bar.duration.toFixed(1)}s</span>
                      </div>
                    );
                  })}
                </div>
              )}

              {timelineMode === 'none' && (
                <div style={{ color: '#777', fontSize: 10 }}>No timeline events.</div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
              <div style={{ border: '1px solid #262626', borderRadius: 4, background: '#1a1a1a', padding: 10 }}>
                <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>Token Distribution</div>
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={80}
                        label={(item: any) => `${item.name} ${(toNumber(item.percent, 0) * 100).toFixed(1)}%`}
                      >
                        {pieData.map((_, idx) => (
                          <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 4 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div style={{ border: '1px solid #262626', borderRadius: 4, background: '#1a1a1a', padding: 10 }}>
                <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>Adjusted Score</div>
                <div style={{ color: '#ccc', fontSize: 11, lineHeight: 1.8 }}>
                  <div>adjusted: <span style={{ color: '#22c55e' }}>{(toNumber(data?.adjusted_stats?.adjusted_success, 0) * 100).toFixed(1)}%</span></div>
                  <div>feedback: <span style={{ color: data?.adjusted_stats?.has_user_feedback ? '#22c55e' : '#888' }}>{data?.adjusted_stats?.user_feedback || '-'}</span></div>
                  <div>phase: <span style={{ color: '#ddd' }}>{data?.phase_type || '-'}</span></div>
                </div>
              </div>
            </div>

            <div style={{ border: '1px solid #262626', borderRadius: 4, background: '#1a1a1a', padding: 10 }}>
              <div style={{ color: '#9a9a9a', fontSize: 10, marginBottom: 8 }}>Agent Stats</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
                  <thead>
                    <tr style={{ color: '#888', textAlign: 'left' }}>
                      <th style={{ padding: '6px 4px', borderBottom: '1px solid #2a2a2a' }}>role</th>
                      <th style={{ padding: '6px 4px', borderBottom: '1px solid #2a2a2a' }}>calls</th>
                      <th style={{ padding: '6px 4px', borderBottom: '1px solid #2a2a2a' }}>tokens</th>
                      <th style={{ padding: '6px 4px', borderBottom: '1px solid #2a2a2a' }}>duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agentRows.length === 0 && (
                      <tr><td colSpan={4} style={{ color: '#666', padding: '8px 4px' }}>No agent stats.</td></tr>
                    )}
                    {agentRows.map((row) => (
                      <tr key={row.role}>
                        <td style={{ padding: '6px 4px', borderBottom: '1px solid #232323', color: '#ddd' }}>{row.role}</td>
                        <td style={{ padding: '6px 4px', borderBottom: '1px solid #232323', color: '#aaa' }}>{row.calls}</td>
                        <td style={{ padding: '6px 4px', borderBottom: '1px solid #232323', color: '#aaa' }}>{row.tokens}</td>
                        <td style={{ padding: '6px 4px', borderBottom: '1px solid #232323', color: '#aaa' }}>{row.duration.toFixed(1)}s</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
