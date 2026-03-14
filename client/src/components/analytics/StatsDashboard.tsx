import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { API_BASE } from '../../config/api.config';
import { resolveRolePreviewAsset, type MycoRolePreviewRole } from '../mcc/mycoRolePreview';

interface StatsDashboardProps {
  mode?: 'compact' | 'expanded';
}

type RangePreset = '7d' | '30d' | '90d';

interface SummaryData {
  total_runs?: number;
  success_rate?: number;
  total_tokens?: number;
  total_cost_estimate?: number;
  avg_duration_s?: number;
  total_retries?: number;
  total_llm_calls?: number;
}

interface AgentData {
  role?: string;
  calls?: number;
  tokens_total?: number;
  avg_duration?: number;
  duration_s?: number;
  success_rate?: number;
  retries?: number;
  efficiency_score?: number;
}

interface TrendPoint {
  bucket?: string;
  success_rate?: number;
  cost_estimate?: number;
  tokens_in?: number;
  tokens_out?: number;
}

interface TeamData {
  preset?: string;
  runs?: number;
  success_rate?: number;
  avg_duration?: number;
  avg_tokens?: number;
  cost_per_run?: number;
  retries_per_run?: number;
}

interface CostPresetData {
  preset?: string;
  cost?: number;
  runs?: number;
}

interface CostData {
  total_cost_estimate?: number;
  cost_by_preset?: CostPresetData[];
}

const ANALYTICS_BASE = `${API_BASE}/analytics`;
const BG = '#0d0d0d';
const CARD = '#141414';
const BORDER = '#222';
const TEXT = '#f5f5f5';
const MUTED = '#909090';
const SUBTLE = '#6c6c6c';
const PURPLE = '#8b5cf6';
const GREEN = '#22c55e';
const RED = '#ef4444';
const BLUE = '#38bdf8';
const PIE_COLORS = ['#8b5cf6', '#22c55e', '#38bdf8', '#f59e0b', '#ef4444'];

const numberFmt = new Intl.NumberFormat('en-US');
const usdFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function formatCompactNumber(value: unknown): string {
  const number = toNumber(value, 0);
  if (number >= 1000000) return `${(number / 1000000).toFixed(1)}M`;
  if (number >= 1000) return `${(number / 1000).toFixed(1)}k`;
  return numberFmt.format(Math.round(number));
}

function formatPercent(value: unknown): string {
  return `${toNumber(value, 0).toFixed(1)}%`;
}

function formatDuration(value: unknown): string {
  const seconds = toNumber(value, 0);
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.round(seconds % 60);
    return `${minutes}m ${remainder}s`;
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

function formatUsd(value: unknown): string {
  return usdFmt.format(toNumber(value, 0));
}

function formatBucketLabel(bucket: string): string {
  const parsed = new Date(bucket);
  if (Number.isNaN(parsed.getTime())) return bucket;
  return `${parsed.getMonth() + 1}/${parsed.getDate()}`;
}

function getTrendParams(range: RangePreset): { period: 'day' | 'week'; limitDays: number } {
  if (range === '90d') return { period: 'week', limitDays: 90 };
  if (range === '30d') return { period: 'day', limitDays: 30 };
  return { period: 'day', limitDays: 7 };
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${ANALYTICS_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function Card({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        border: `1px solid ${BORDER}`,
        background: CARD,
        borderRadius: 16,
        padding: 16,
        boxShadow: '0 18px 40px rgba(0,0,0,0.18)',
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function CardTitle({
  title,
  meta,
}: {
  title: string;
  meta?: string;
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline', marginBottom: 14 }}>
      <span style={{ color: TEXT, fontSize: 12, letterSpacing: 0.8, textTransform: 'uppercase' }}>{title}</span>
      {meta ? <span style={{ color: MUTED, fontSize: 10 }}>{meta}</span> : null}
    </div>
  );
}

export function StatsDashboard({ mode = 'expanded' }: StatsDashboardProps) {
  const [range, setRange] = useState<RangePreset>('7d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [weakLinks, setWeakLinks] = useState<string[]>([]);
  const [trendPoints, setTrendPoints] = useState<TrendPoint[]>([]);
  const [trendMeta, setTrendMeta] = useState<{ trend?: string; changePct?: number; period?: string }>({});
  const [teams, setTeams] = useState<TeamData[]>([]);
  const [cost, setCost] = useState<CostData | null>(null);

  useEffect(() => {
    let active = true;
    const { period, limitDays } = getTrendParams(range);

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [summaryJson, agentsJson, trendsJson, teamsJson, costJson] = await Promise.all([
          fetchJson<{ success: boolean; data?: SummaryData }>('/summary'),
          fetchJson<{ success: boolean; agents?: AgentData[]; weak_links?: Array<{ role?: string }> }>('/agents'),
          fetchJson<{
            success: boolean;
            data?: { trend?: string; change_pct?: number; period?: string; data_points?: TrendPoint[] };
          }>(`/trends?period=${period}&limit_days=${limitDays}&metric=success_rate`),
          fetchJson<{ success: boolean; teams?: TeamData[] }>('/teams'),
          fetchJson<{ success: boolean; data?: CostData }>('/cost'),
        ]);

        if (!active) return;

        setSummary(summaryJson.data || null);
        setAgents(Array.isArray(agentsJson.agents) ? agentsJson.agents : []);
        setWeakLinks(
          Array.isArray(agentsJson.weak_links)
            ? agentsJson.weak_links
                .map((item) => String(item.role || '').toLowerCase())
                .filter(Boolean)
            : [],
        );
        setTrendPoints(Array.isArray(trendsJson.data?.data_points) ? trendsJson.data?.data_points : []);
        setTrendMeta({
          trend: trendsJson.data?.trend,
          changePct: trendsJson.data?.change_pct,
          period: trendsJson.data?.period,
        });
        setTeams(Array.isArray(teamsJson.teams) ? teamsJson.teams : []);
        setCost(costJson.data || null);
      } catch (loadError) {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : 'Analytics load failed');
      } finally {
        if (active) setLoading(false);
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [range]);

  const lineData = useMemo(() => (
    trendPoints.map((point, index) => {
      const tokens = toNumber(point.tokens_in, 0) + toNumber(point.tokens_out, 0);
      const bucket = String(point.bucket || index);
      return {
        bucket,
        label: formatBucketLabel(bucket),
        successRate: toNumber(point.success_rate, 0),
        tokens,
        costEstimate: toNumber(point.cost_estimate, 0),
      };
    })
  ), [trendPoints]);

  const agentRows = useMemo(() => (
    [...agents]
      .map((agent) => ({
        role: String(agent.role || 'unknown'),
        calls: toNumber(agent.calls, 0),
        tokens: toNumber(agent.tokens_total, 0),
        avgDuration: toNumber(agent.avg_duration ?? agent.duration_s, 0),
        successRate: toNumber(agent.success_rate, 0),
        retries: toNumber(agent.retries, 0),
        efficiencyScore: toNumber(agent.efficiency_score, 0),
        weak: weakLinks.includes(String(agent.role || '').toLowerCase()),
      }))
      .sort((left, right) => right.efficiencyScore - left.efficiencyScore)
  ), [agents, weakLinks]);

  const pieData = useMemo(() => (
    Array.isArray(cost?.cost_by_preset)
      ? cost.cost_by_preset
          .filter((item) => toNumber(item.cost, 0) > 0)
          .map((item) => ({
            name: String(item.preset || 'unknown'),
            value: toNumber(item.cost, 0),
            runs: toNumber(item.runs, 0),
          }))
      : []
  ), [cost?.cost_by_preset]);

  const teamRows = useMemo(() => (
    [...teams]
      .map((team) => ({
        preset: String(team.preset || 'unknown'),
        runs: toNumber(team.runs, 0),
        successRate: toNumber(team.success_rate, 0),
        avgDuration: toNumber(team.avg_duration, 0),
        avgTokens: toNumber(team.avg_tokens, 0),
        costPerRun: toNumber(team.cost_per_run, 0),
        retriesPerRun: toNumber(team.retries_per_run, 0),
      }))
      .sort((left, right) => right.runs - left.runs)
  ), [teams]);

  const kpis = [
    { label: 'Runs', value: summary ? numberFmt.format(toNumber(summary.total_runs, 0)) : '-', meta: 'completed tasks' },
    { label: 'Success', value: summary ? formatPercent(summary.success_rate) : '-', meta: 'pipeline success' },
    { label: 'Avg Time', value: summary ? formatDuration(summary.avg_duration_s) : '-', meta: 'mean runtime' },
    { label: 'Est Cost', value: summary ? formatUsd(summary.total_cost_estimate) : '-', meta: `${formatCompactNumber(summary?.total_llm_calls)} calls` },
  ];

  if (mode === 'compact') {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
        {kpis.map((kpi) => (
          <Card key={kpi.label} style={{ padding: 12, borderRadius: 12 }}>
            <div style={{ color: SUBTLE, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>{kpi.label}</div>
            <div style={{ color: TEXT, fontSize: 20, marginTop: 8, fontFamily: "'JetBrains Mono', 'SFMono-Regular', monospace" }}>
              {loading ? '-' : kpi.value}
            </div>
            <div style={{ color: MUTED, fontSize: 10, marginTop: 6 }}>{kpi.meta}</div>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, color: TEXT, fontFamily: 'Inter, sans-serif', background: BG }}>
      <Card style={{ background: 'linear-gradient(180deg, #151515 0%, #121212 100%)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <div style={{ color: TEXT, fontSize: 18, fontWeight: 600 }}>Pipeline Analytics</div>
            <div style={{ color: MUTED, fontSize: 11, marginTop: 6 }}>
              Nolan dark dashboard for runs, agent efficiency, team cost share, and trend movement.
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['7d', '30d', '90d'] as RangePreset[]).map((preset) => (
              <button
                key={preset}
                onClick={() => setRange(preset)}
                style={{
                  border: `1px solid ${range === preset ? PURPLE : BORDER}`,
                  borderRadius: 999,
                  padding: '7px 12px',
                  background: range === preset ? 'rgba(139,92,246,0.14)' : '#101010',
                  color: range === preset ? '#d9cbff' : MUTED,
                  fontSize: 11,
                  cursor: 'pointer',
                  fontFamily: "'JetBrains Mono', 'SFMono-Regular', monospace",
                }}
              >
                {preset}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {error ? (
        <Card style={{ borderColor: '#4b1f28', background: '#1c1114' }}>
          <div style={{ color: RED, fontSize: 12 }}>Analytics error: {error}</div>
        </Card>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12 }}>
        {kpis.map((kpi, index) => (
          <Card key={kpi.label} style={{ position: 'relative', overflow: 'hidden' }}>
            <div
              style={{
                position: 'absolute',
                inset: '0 auto auto 0',
                height: 3,
                width: '100%',
                background: index === 0 ? PURPLE : index === 1 ? GREEN : index === 2 ? BLUE : RED,
              }}
            />
            <div style={{ color: SUBTLE, fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
            <div style={{ color: TEXT, fontSize: 28, marginTop: 12, fontFamily: "'JetBrains Mono', 'SFMono-Regular', monospace" }}>
              {loading ? '-' : kpi.value}
            </div>
            <div style={{ color: MUTED, fontSize: 10, marginTop: 8 }}>{kpi.meta}</div>
          </Card>
        ))}
      </div>

      <Card>
        <CardTitle
          title="Run Trend"
          meta={trendMeta.trend ? `${trendMeta.trend}${typeof trendMeta.changePct === 'number' ? ` · ${trendMeta.changePct.toFixed(1)}%` : ''}` : 'success_rate'}
        />
        <div style={{ width: '100%', height: 280 }}>
          <ResponsiveContainer>
            <LineChart data={lineData}>
              <CartesianGrid stroke="#1e1e1e" strokeDasharray="3 3" />
              <XAxis dataKey="label" stroke={SUBTLE} tick={{ fill: MUTED, fontSize: 11 }} />
              <YAxis yAxisId="success" stroke={SUBTLE} tick={{ fill: MUTED, fontSize: 11 }} />
              <YAxis yAxisId="tokens" orientation="right" stroke={SUBTLE} tick={{ fill: MUTED, fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#101010', border: `1px solid ${BORDER}`, borderRadius: 12 }}
                labelStyle={{ color: TEXT }}
              />
              <Line yAxisId="success" type="monotone" dataKey="successRate" name="success %" stroke={PURPLE} strokeWidth={2.5} dot={false} />
              <Line yAxisId="tokens" type="monotone" dataKey="tokens" name="tokens" stroke={BLUE} strokeWidth={1.8} dot={false} />
              <Line yAxisId="tokens" type="monotone" dataKey="costEstimate" name="cost" stroke={GREEN} strokeWidth={1.8} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.55fr) minmax(320px, 0.95fr)', gap: 12 }}>
        <Card>
          <CardTitle
            title="Agent Efficiency"
            meta={summary ? `${formatCompactNumber(summary.total_retries)} retries · ${formatCompactNumber(summary.total_tokens)} tokens` : undefined}
          />
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={agentRows}>
                <CartesianGrid stroke="#1e1e1e" strokeDasharray="3 3" />
                <XAxis dataKey="role" stroke={SUBTLE} tick={{ fill: MUTED, fontSize: 11 }} />
                <YAxis stroke={SUBTLE} tick={{ fill: MUTED, fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#101010', border: `1px solid ${BORDER}`, borderRadius: 12 }}
                />
                <Bar dataKey="successRate" name="success %" radius={[8, 8, 0, 0]}>
                  {agentRows.map((row) => (
                    <Cell key={row.role} fill={row.weak ? RED : PURPLE} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10, marginTop: 10 }}>
            {agentRows.map((row) => {
              const avatarSrc = resolveRolePreviewAsset(
                row.role.toLowerCase() as MycoRolePreviewRole,
                row.role,
              );
              return (
              <div key={`${row.role}_meta`} style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                  {/* MARKER_175.AVATAR: Role avatar in analytics */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {avatarSrc && (
                      <img
                        src={avatarSrc}
                        alt={row.role}
                        style={{ width: 20, height: 20, borderRadius: 3, objectFit: 'cover', opacity: 0.85 }}
                      />
                    )}
                    <span style={{ color: TEXT, fontSize: 11, textTransform: 'uppercase' }}>{row.role}</span>
                  </div>
                  <span style={{ color: row.weak ? RED : GREEN, fontSize: 10 }}>{row.weak ? 'weak link' : 'stable'}</span>
                </div>
                <div style={{ color: MUTED, fontSize: 10, lineHeight: 1.7, marginTop: 6 }}>
                  <div>calls: {row.calls}</div>
                  <div>tokens: {formatCompactNumber(row.tokens)}</div>
                  <div>avg: {formatDuration(row.avgDuration)}</div>
                  <div>retries: {row.retries}</div>
                </div>
              </div>
              );
            })}
          </div>
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card>
            <CardTitle
              title="Cost Share"
              meta={cost ? `${formatUsd(cost.total_cost_estimate)} total` : undefined}
            />
            <div style={{ width: '100%', height: 240 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={56}
                    outerRadius={86}
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
          </Card>

          <Card>
            <CardTitle title="Team Comparison" meta={`${teamRows.length} presets`} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {teamRows.length === 0 ? (
                <div style={{ color: MUTED, fontSize: 11 }}>{loading ? 'Loading teams...' : 'No completed team runs yet.'}</div>
              ) : null}
              {teamRows.map((team) => (
                <div key={team.preset} style={{ border: `1px solid ${BORDER}`, borderRadius: 12, padding: 12, background: '#101010' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                    <span style={{ color: TEXT, fontSize: 11, textTransform: 'uppercase' }}>{team.preset.replace(/^dragon_/, '').replace(/^titan_/, '')}</span>
                    <span style={{ color: PURPLE, fontSize: 10, fontFamily: "'JetBrains Mono', 'SFMono-Regular', monospace" }}>{team.runs} runs</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 6, marginTop: 10, color: MUTED, fontSize: 10 }}>
                    <span>success: <span style={{ color: GREEN }}>{formatPercent(team.successRate)}</span></span>
                    <span>avg: <span style={{ color: TEXT }}>{formatDuration(team.avgDuration)}</span></span>
                    <span>tokens: <span style={{ color: TEXT }}>{formatCompactNumber(team.avgTokens)}</span></span>
                    <span>cost/run: <span style={{ color: TEXT }}>{formatUsd(team.costPerRun)}</span></span>
                    <span>retries/run: <span style={{ color: TEXT }}>{team.retriesPerRun.toFixed(1)}</span></span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
