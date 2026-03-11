import { useEffect, useMemo, useState } from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { API_BASE } from '../../config/api.config';

interface TaskDrillDownProps {
  isOpen: boolean;
  taskId: string | null;
  onClose: () => void;
}

interface TimelineEvent {
  role?: string;
  event?: string;
  offset_s?: number;
  start_offset?: number;
  duration_s?: number;
}

interface AgentStat {
  calls?: number;
  tokens_in?: number;
  tokens_out?: number;
  duration_s?: number;
  success_count?: number;
  fail_count?: number;
}

interface TaskAnalyticsData {
  task_id?: string;
  title?: string;
  status?: string;
  preset?: string;
  phase_type?: string;
  duration_s?: number;
  llm_calls?: number;
  cost_estimate?: number;
  verifier_confidence?: number;
  token_distribution?: Array<{ role?: string; tokens?: number; pct?: number }>;
  timeline_events?: TimelineEvent[];
  agent_stats?: Record<string, AgentStat>;
  adjusted_stats?: {
    adjusted_success?: number;
    user_feedback?: string;
    has_user_feedback?: boolean;
  };
}

const ANALYTICS_BASE = `${API_BASE}/analytics`;
const BG = '#0d0d0d';
const CARD = '#141414';
const BORDER = '#222';
const TEXT = '#f5f5f5';
const MUTED = '#909090';
const PURPLE = '#8b5cf6';
const GREEN = '#22c55e';
const RED = '#ef4444';
const PIE_COLORS = ['#8b5cf6', '#22c55e', '#38bdf8', '#f59e0b', '#ef4444'];

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function formatDuration(value: unknown): string {
  const seconds = toNumber(value, 0);
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes}m ${remainder}s`;
}

function formatPercent(value: unknown): string {
  return `${toNumber(value, 0).toFixed(1)}%`;
}

function formatCompactNumber(value: unknown): string {
  const number = toNumber(value, 0);
  if (number >= 1000000) return `${(number / 1000000).toFixed(1)}M`;
  if (number >= 1000) return `${(number / 1000).toFixed(1)}k`;
  return String(Math.round(number));
}

function formatUsd(value: unknown): string {
  return `$${toNumber(value, 0).toFixed(3)}`;
}

function buildTimelineBars(
  events: TimelineEvent[],
  agentStats: Record<string, AgentStat>,
): Array<{ role: string; start: number; duration: number; startLabel: string; endLabel: string }> {
  if (events.length === 0) return [];

  const hasLegacy = events.some((event) => typeof event.start_offset === 'number');
  if (hasLegacy) {
    return events
      .filter((event) => typeof event.start_offset === 'number')
      .map((event) => {
        const start = toNumber(event.start_offset, 0);
        const duration = Math.max(0.3, toNumber(event.duration_s, 0.3));
        return {
          role: String(event.role || 'unknown'),
          start,
          duration,
          startLabel: `${start.toFixed(1)}s`,
          endLabel: `${(start + duration).toFixed(1)}s`,
        };
      })
      .sort((left, right) => left.start - right.start);
  }

  const grouped = new Map<string, number[]>();
  events.forEach((event) => {
    if (typeof event.offset_s !== 'number') return;
    const role = String(event.role || 'unknown');
    const bucket = grouped.get(role) || [];
    bucket.push(event.offset_s);
    grouped.set(role, bucket);
  });

  return Array.from(grouped.entries())
    .map(([role, offsets]) => {
      const start = Math.min(...offsets);
      const inferredDuration = Math.max(...offsets) - start;
      const fallbackDuration = toNumber(agentStats[role]?.duration_s, 0.6);
      const duration = Math.max(0.4, inferredDuration || fallbackDuration || 0.4);
      return {
        role,
        start,
        duration,
        startLabel: `${start.toFixed(1)}s`,
        endLabel: `${(start + duration).toFixed(1)}s`,
      };
    })
    .sort((left, right) => left.start - right.start);
}

function MetaCard({
  label,
  value,
  tone = TEXT,
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div style={{ border: `1px solid ${BORDER}`, borderRadius: 12, background: '#101010', padding: 12 }}>
      <div style={{ color: MUTED, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>{label}</div>
      <div style={{ color: tone, fontSize: 18, marginTop: 8, fontFamily: "'JetBrains Mono', 'SFMono-Regular', monospace" }}>{value}</div>
    </div>
  );
}

export function TaskDrillDown({ isOpen, taskId, onClose }: TaskDrillDownProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TaskAnalyticsData | null>(null);

  useEffect(() => {
    if (!isOpen) return undefined;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen || !taskId) return undefined;

    let active = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${ANALYTICS_BASE}/task/${encodeURIComponent(taskId)}`);
        if (!response.ok) {
          throw new Error(`${response.status} ${response.statusText}`);
        }
        const json = await response.json();
        if (!active) return;
        if (json?.success && json?.data) {
          setData(json.data as TaskAnalyticsData);
          return;
        }
        setData(null);
        setError(json?.error || 'Task analytics unavailable');
      } catch (loadError) {
        if (!active) return;
        setData(null);
        setError(loadError instanceof Error ? loadError.message : 'Task analytics load failed');
      } finally {
        if (active) setLoading(false);
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [isOpen, taskId]);

  const agentStats = data?.agent_stats || {};

  const timelineBars = useMemo(
    () => buildTimelineBars(data?.timeline_events || [], agentStats),
    [data?.timeline_events, agentStats],
  );

  const timelineTotal = useMemo(() => (
    timelineBars.length > 0
      ? Math.max(...timelineBars.map((bar) => bar.start + bar.duration))
      : Math.max(toNumber(data?.duration_s, 0), 1)
  ), [data?.duration_s, timelineBars]);

  const pieData = useMemo(() => (
    Array.isArray(data?.token_distribution)
      ? data.token_distribution.map((item) => ({
          name: String(item.role || 'unknown'),
          value: toNumber(item.tokens, 0),
        }))
      : []
  ), [data?.token_distribution]);

  const agentRows = useMemo(() => (
    Object.entries(agentStats).map(([role, stats]) => {
      const tokens = toNumber(stats.tokens_in, 0) + toNumber(stats.tokens_out, 0);
      const successCount = toNumber(stats.success_count, 0);
      const failCount = toNumber(stats.fail_count, 0);
      const status = failCount > 0 && successCount === 0 ? 'failed' : 'done';
      return {
        role,
        calls: toNumber(stats.calls, 0),
        tokens,
        duration: toNumber(stats.duration_s, 0),
        status,
      };
    })
  ), [agentStats]);

  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 12000,
        background: 'rgba(0,0,0,0.72)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
      }}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        style={{
          width: 'min(1120px, 96vw)',
          maxHeight: '92vh',
          overflowY: 'auto',
          border: `1px solid ${BORDER}`,
          borderRadius: 20,
          background: BG,
          color: TEXT,
          padding: 20,
          boxShadow: '0 28px 80px rgba(0,0,0,0.42)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <div style={{ color: TEXT, fontSize: 22, fontWeight: 600 }}>{data?.title || taskId || 'Task analytics'}</div>
            <div style={{ color: MUTED, fontSize: 11, marginTop: 8 }}>
              {data?.task_id || taskId || '-'} · {data?.phase_type || 'phase ?'} · {data?.preset || 'preset ?'}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              border: `1px solid ${BORDER}`,
              background: '#121212',
              color: TEXT,
              borderRadius: 999,
              padding: '8px 12px',
              fontSize: 11,
              cursor: 'pointer',
              fontFamily: "'JetBrains Mono', 'SFMono-Regular', monospace",
            }}
          >
            close
          </button>
        </div>

        {loading ? <div style={{ color: MUTED, fontSize: 12, padding: '6px 0 14px' }}>Loading task analytics...</div> : null}
        {error ? <div style={{ color: RED, fontSize: 12, padding: '6px 0 14px' }}>{error}</div> : null}

        {!loading && !error && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 14 }}>
              <MetaCard label="Status" value={String(data?.status || '-')} tone={data?.status === 'done' ? GREEN : data?.status === 'failed' ? RED : PURPLE} />
              <MetaCard label="Runtime" value={formatDuration(data?.duration_s)} />
              <MetaCard label="Cost" value={formatUsd(data?.cost_estimate)} />
              <MetaCard
                label="Adjusted"
                value={formatPercent(toNumber(data?.adjusted_stats?.adjusted_success, 0) * 100)}
                tone={GREEN}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.45fr) minmax(320px, 0.9fr)', gap: 14 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ border: `1px solid ${BORDER}`, borderRadius: 16, background: CARD, padding: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline', marginBottom: 14 }}>
                    <span style={{ color: TEXT, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.8 }}>Gantt Timeline</span>
                    <span style={{ color: MUTED, fontSize: 10 }}>{timelineTotal.toFixed(1)}s total</span>
                  </div>

                  {timelineBars.length === 0 ? (
                    <div style={{ color: MUTED, fontSize: 11 }}>No timeline events for this task.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {timelineBars.map((bar) => {
                        const left = (bar.start / timelineTotal) * 100;
                        const width = Math.max((bar.duration / timelineTotal) * 100, 2.5);
                        return (
                          <div key={`${bar.role}_${bar.start}`} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 96px', gap: 10, alignItems: 'center' }}>
                            <span style={{ color: TEXT, fontSize: 11, textTransform: 'uppercase' }}>{bar.role}</span>
                            <div style={{ position: 'relative', height: 14, borderRadius: 999, border: `1px solid ${BORDER}`, background: '#101010', overflow: 'hidden' }}>
                              <div
                                style={{
                                  position: 'absolute',
                                  top: 1,
                                  bottom: 1,
                                  left: `${left}%`,
                                  width: `${width}%`,
                                  minWidth: 10,
                                  borderRadius: 999,
                                  background: 'linear-gradient(90deg, #8b5cf6 0%, #6d28d9 100%)',
                                  boxShadow: '0 0 18px rgba(139,92,246,0.28)',
                                }}
                              />
                            </div>
                            <span style={{ color: MUTED, fontSize: 10, fontFamily: "'JetBrains Mono', 'SFMono-Regular', monospace" }}>
                              {bar.startLabel} - {bar.endLabel}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div style={{ border: `1px solid ${BORDER}`, borderRadius: 16, background: CARD, padding: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline', marginBottom: 14 }}>
                    <span style={{ color: TEXT, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.8 }}>Agent Stats</span>
                    <span style={{ color: MUTED, fontSize: 10 }}>
                      confidence {data?.verifier_confidence != null ? formatPercent(toNumber(data.verifier_confidence, 0) * 100) : '-'}
                    </span>
                  </div>

                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                      <thead>
                        <tr style={{ color: MUTED, textAlign: 'left' }}>
                          <th style={{ padding: '0 0 10px', borderBottom: `1px solid ${BORDER}` }}>agent</th>
                          <th style={{ padding: '0 0 10px', borderBottom: `1px solid ${BORDER}` }}>tokens</th>
                          <th style={{ padding: '0 0 10px', borderBottom: `1px solid ${BORDER}` }}>time</th>
                          <th style={{ padding: '0 0 10px', borderBottom: `1px solid ${BORDER}` }}>calls</th>
                          <th style={{ padding: '0 0 10px', borderBottom: `1px solid ${BORDER}` }}>status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {agentRows.length === 0 ? (
                          <tr>
                            <td colSpan={5} style={{ padding: '12px 0 0', color: MUTED }}>No per-agent stats.</td>
                          </tr>
                        ) : null}
                        {agentRows.map((row) => (
                          <tr key={row.role}>
                            <td style={{ padding: '12px 0', borderBottom: `1px solid ${BORDER}`, color: TEXT, textTransform: 'uppercase' }}>{row.role}</td>
                            <td style={{ padding: '12px 0', borderBottom: `1px solid ${BORDER}`, color: TEXT, fontFamily: "'JetBrains Mono', 'SFMono-Regular', monospace" }}>{formatCompactNumber(row.tokens)}</td>
                            <td style={{ padding: '12px 0', borderBottom: `1px solid ${BORDER}`, color: TEXT }}>{formatDuration(row.duration)}</td>
                            <td style={{ padding: '12px 0', borderBottom: `1px solid ${BORDER}`, color: TEXT }}>{row.calls}</td>
                            <td style={{ padding: '12px 0', borderBottom: `1px solid ${BORDER}`, color: row.status === 'done' ? GREEN : RED }}>{row.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ border: `1px solid ${BORDER}`, borderRadius: 16, background: CARD, padding: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline', marginBottom: 14 }}>
                    <span style={{ color: TEXT, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.8 }}>Token Split</span>
                    <span style={{ color: MUTED, fontSize: 10 }}>{formatCompactNumber(pieData.reduce((sum, item) => sum + item.value, 0))} total</span>
                  </div>
                  <div style={{ width: '100%', height: 260 }}>
                    <ResponsiveContainer>
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={56}
                          outerRadius={88}
                          paddingAngle={2}
                          label={({ name, percent }) => `${name} ${(toNumber(percent, 0) * 100).toFixed(0)}%`}
                        >
                          {pieData.map((item, index) => (
                            <Cell key={item.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{ background: '#101010', border: `1px solid ${BORDER}`, borderRadius: 12 }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div style={{ border: `1px solid ${BORDER}`, borderRadius: 16, background: CARD, padding: 16 }}>
                  <div style={{ color: TEXT, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 14 }}>Task Notes</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, color: MUTED, fontSize: 11 }}>
                    <div>feedback: <span style={{ color: data?.adjusted_stats?.has_user_feedback ? GREEN : TEXT }}>{data?.adjusted_stats?.user_feedback || '-'}</span></div>
                    <div>llm calls: <span style={{ color: TEXT }}>{toNumber(data?.llm_calls, 0)}</span></div>
                    <div>preset: <span style={{ color: TEXT }}>{data?.preset || '-'}</span></div>
                    <div>phase: <span style={{ color: TEXT }}>{data?.phase_type || '-'}</span></div>
                    <div>cost: <span style={{ color: TEXT }}>{formatUsd(data?.cost_estimate)}</span></div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
