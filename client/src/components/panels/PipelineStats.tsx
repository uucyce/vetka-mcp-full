/**
 * MARKER_126.0D: Pipeline Statistics — monochrome bars, no chart library.
 * MARKER_126.12: Live refresh + running task progress + improved summary.
 * MARKER_136.W1C: Enhanced stats — confidence, subtasks, model breakdown.
 * MARKER_138.MCC_STATS_NORMALIZE: normalized scales + horizontal token areas + hover tooltips.
 * Nolan style: dark, serious, minimal color. Itten color only for accents.
 *
 * @phase 136
 * @depends TaskData
 */

import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { TaskData, PipelineStatsData } from './TaskCard';
import { useDevPanelStore } from '../../store/useDevPanelStore';

interface PipelineStatsProps {
  tasks: TaskData[];
  mode?: 'compact' | 'expanded';
  onRefresh?: () => void;  // MARKER_126.12A: Callback to trigger parent refresh
}

interface PresetStats {
  preset: string;
  total: number;
  success: number;
  llmCalls: number;
  tokensOut: number;
  tokensIn: number;
  avgDuration: number;
  avgConfidence: number;
}

// MARKER_126.12B: Calculate elapsed time for running tasks
function formatElapsed(startedAt?: string): string {
  if (!startedAt) return '-';
  const start = new Date(startedAt).getTime();
  const now = Date.now();
  const seconds = Math.floor((now - start) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}m ${secs}s`;
}

export function PipelineStats({ tasks, mode = 'expanded', onRefresh }: PipelineStatsProps) {
  const setActiveTab = useDevPanelStore(s => s.setActiveTab);
  // MARKER_126.12A: Live refresh via CustomEvent
  const [, setTick] = useState(0);

  // MARKER_145.CLEANUP: Event-driven + cheap 60s re-render tick.
  // Was: 5s/30s setInterval polling data PLUS event listener = triple-fetch.
  // Now: event fires data refresh, 60s tick only for elapsed time display.
  useEffect(() => {
    const handleBoardUpdate = () => {
      setTick(t => t + 1);
      onRefresh?.();
    };

    window.addEventListener('task-board-updated', handleBoardUpdate);

    // 60s tick for elapsed time display only — no data fetch
    const interval = setInterval(() => {
      setTick(t => t + 1);
    }, 60000);

    return () => {
      window.removeEventListener('task-board-updated', handleBoardUpdate);
      clearInterval(interval);
    };
  }, [tasks, onRefresh]);

  // MARKER_126.12B: Running tasks
  const runningTasks = tasks.filter(t => t.status === 'running');
  // Aggregate stats by preset
  const byPreset: Record<string, PresetStats> = {};

  for (const task of tasks) {
    const stats: PipelineStatsData | undefined = task.stats;
    if (!stats) continue;

    const preset = stats.preset || task.preset || 'unknown';
    if (!byPreset[preset]) {
      byPreset[preset] = {
        preset,
        total: 0,
        success: 0,
        llmCalls: 0,
        tokensOut: 0,
        tokensIn: 0,
        avgDuration: 0,
        avgConfidence: 0,
      };
    }
    const p = byPreset[preset];
    p.total += 1;
    if (stats.success) p.success += 1;
    p.llmCalls += stats.llm_calls || 0;
    p.tokensOut += stats.tokens_out || 0;
    p.tokensIn += stats.tokens_in || 0;
    p.avgDuration += stats.duration_s || 0;
    p.avgConfidence += stats.verifier_avg_confidence || 0;
  }

  // Finalize averages
  const presets = Object.values(byPreset);
  for (const p of presets) {
    if (p.total > 0) {
      p.avgDuration = Math.round(p.avgDuration / p.total);
      p.avgConfidence = Math.round((p.avgConfidence / p.total) * 100);
    }
  }

  const maxLlmCalls = Math.max(...presets.map(p => p.llmCalls), 1);
  const maxTokens = Math.max(...presets.map(p => p.tokensOut), 1);
  const maxSuccess = Math.max(...presets.map(p => (p.total > 0 ? Math.round((p.success / p.total) * 100) : 0)), 1);
  const normalizedYMax = Math.max(10, Math.ceil(maxSuccess / 10) * 10);

  // MARKER_126.12C: Calculate totals
  const totalRuns = presets.reduce((s, p) => s + p.total, 0);
  const totalSuccess = presets.reduce((s, p) => s + p.success, 0);
  const totalLlmCalls = presets.reduce((s, p) => s + p.llmCalls, 0);
  const totalTokensIn = presets.reduce((s, p) => s + p.tokensIn, 0);
  const totalTokensOut = presets.reduce((s, p) => s + p.tokensOut, 0);
  const avgDuration = totalRuns > 0
    ? Math.round(presets.reduce((s, p) => s + p.avgDuration * p.total, 0) / totalRuns)
    : 0;
  const successRate = totalRuns > 0 ? Math.round((totalSuccess / totalRuns) * 100) : 0;

  // MARKER_136.W1C: Additional stats
  const avgConfidence = presets.reduce((s, p) => s + p.avgConfidence * p.total, 0) / (totalRuns || 1);
  let totalSubtasks = 0;
  let completedSubtasks = 0;
  for (const task of tasks) {
    if (task.stats?.subtasks_total) {
      totalSubtasks += task.stats.subtasks_total;
      completedSubtasks += task.stats.subtasks_completed || 0;
    }
  }

  const tokenSeries = [
    { key: 'in', value: totalTokensIn, color: '#8c8c8c' },
    { key: 'out', value: totalTokensOut, color: '#d9d9d9' },
  ];
  const tokenMax = Math.max(...tokenSeries.map(s => s.value), 1);
  const weakLink = presets.length > 0
    ? [...presets].sort((a, b) => a.avgConfidence - b.avgConfidence)[0]?.preset || '-'
    : '-';

  if (mode === 'compact') {
    return (
      <div
        style={{
          border: '1px solid #222',
          borderRadius: 4,
          padding: 8,
          background: 'rgba(255,255,255,0.01)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 8, color: '#666', textTransform: 'uppercase', letterSpacing: 1 }}>
            stats
          </span>
          <button
            onClick={() => setActiveTab('stats')}
            style={{
              marginLeft: 'auto',
              border: '1px solid #333',
              borderRadius: 2,
              background: 'transparent',
              color: '#999',
              fontFamily: 'monospace',
              fontSize: 9,
              padding: '1px 6px',
              cursor: 'pointer',
            }}
            title="Expand to Stats tab"
          >
            ↗
          </button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 6 }}>
          <StatBox label="Total Runs" value={totalRuns} />
          <StatBox label="Success" value={`${successRate}%`} />
          <StatBox label="Confidence" value={avgConfidence > 0 ? `${Math.round(avgConfidence)}%` : '-'} />
          <StatBox label="Weak Link" value={weakLink.replace('dragon_', '').replace('titan_', '')} />
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 9, color: '#666', textTransform: 'uppercase', letterSpacing: 1 }}>
          stats
        </span>
        <button
          onClick={() => setActiveTab('mcc')}
          style={{
            border: '1px solid #333',
            borderRadius: 2,
            background: 'transparent',
            color: '#999',
            fontFamily: 'monospace',
            fontSize: 9,
            padding: '1px 6px',
            cursor: 'pointer',
          }}
          title="Collapse back to MCC"
        >
          ↙
        </button>
      </div>
      {/* MARKER_126.12B: Running Tasks Section */}
      {runningTasks.length > 0 && (
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid #333',
          borderRadius: 4,
          padding: 10,
        }}>
          <div style={{ color: '#888', fontSize: 9, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
            running ({runningTasks.length})
          </div>
          {runningTasks.map(t => (
            <div key={t.id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 0',
            }}>
              {/* Pulsing indicator */}
              <span style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#e0e0e0',
                boxShadow: '0 0 6px rgba(224,224,224,0.4)',
                animation: 'taskPulse 1.5s ease-in-out infinite',
              }} />
              <span style={{ flex: 1, color: '#ccc', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {t.title}
              </span>
              <span style={{ color: '#888', fontSize: 10, fontFamily: 'monospace' }}>
                {formatElapsed((t as TaskData & { started_at?: string }).started_at)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Summary row */}
      {presets.length === 0 && runningTasks.length === 0 ? (
        <div style={{ color: '#555', textAlign: 'center', padding: 40, fontSize: 12, lineHeight: 1.6 }}>
          No pipeline runs yet.<br />
          Dispatch a task to see statistics.
        </div>
      ) : presets.length > 0 && (
        <>
          {/* MARKER_136.W1C: Enhanced stats grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 8,
          }}>
            <StatBox label="Total Runs" value={totalRuns} />
            <StatBox label="Success" value={`${successRate}%`} />
            <StatBox label="Confidence" value={avgConfidence > 0 ? `${Math.round(avgConfidence)}%` : '-'} />
            <StatBox label="Avg Duration" value={avgDuration > 0 ? `${avgDuration}s` : '-'} />
          </div>

          {/* MARKER_136.W1C: Second row — subtasks + LLM */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 8,
          }}>
            <StatBox label="Subtasks" value={totalSubtasks > 0 ? `${completedSubtasks}/${totalSubtasks}` : '-'} />
            <StatBox label="LLM Calls" value={totalLlmCalls} />
            <StatBox
              label="Tokens"
              value={totalTokensIn + totalTokensOut > 1000
                ? `${((totalTokensIn + totalTokensOut) / 1000).toFixed(1)}k`
                : totalTokensIn + totalTokensOut}
            />
          </div>

          {/* MARKER_138.MCC_STATS_NORMALIZE: Horizontal token area chart */}
          <div style={{
            padding: '8px 10px',
            background: '#111',
            borderRadius: 3,
            fontSize: 10,
            fontFamily: 'monospace',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ color: '#666' }}>token breakdown</span>
              <span style={{ color: '#888' }}>
                <span style={{ color: '#777' }}>ratio:</span> {totalTokensIn > 0 ? (totalTokensOut / totalTokensIn).toFixed(1) : '-'}x
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {tokenSeries.map((series) => {
                const widthPct = Math.max(2, (series.value / tokenMax) * 100);
                const formatted = series.value > 1000 ? `${(series.value / 1000).toFixed(1)}k` : String(series.value);
                return (
                  <div key={series.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ color: '#777', width: 28, textTransform: 'uppercase' }}>{series.key}</span>
                    <div
                      style={{
                        flex: 1,
                        height: 10,
                        background: '#1a1a1a',
                        borderRadius: 5,
                        overflow: 'hidden',
                        position: 'relative',
                      }}
                      title={`${series.key.toUpperCase()}: ${series.value} tokens`}
                    >
                      <div
                        style={{
                          width: `${widthPct}%`,
                          height: '100%',
                          background: `linear-gradient(90deg, ${series.color}66 0%, ${series.color} 100%)`,
                          borderRadius: 5,
                          transition: 'width 0.3s ease',
                        }}
                      />
                    </div>
                    <span style={{ color: '#999', width: 40, textAlign: 'right' }}>{formatted}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* MARKER_134.C34H: Recharts visualization */}
      {presets.length > 0 && (
        <div style={{
          height: 120,
          marginBottom: 8,
          background: '#0d0d0d',
          borderRadius: 4,
          padding: '8px 0',
        }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={presets.map(p => ({
                name: p.preset.replace('dragon_', '').replace('titan_', ''),
                success: p.total > 0 ? Math.round((p.success / p.total) * 100) : 0,
                calls: p.llmCalls,
              }))}
              margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
            >
              <XAxis
                dataKey="name"
                tick={{ fill: '#666', fontSize: 9 }}
                axisLine={{ stroke: '#333' }}
                tickLine={false}
              />
              <YAxis
                domain={[0, normalizedYMax]}
                tick={{ fill: '#555', fontSize: 8 }}
                axisLine={false}
                tickLine={false}
                width={25}
              />
              <Tooltip
                contentStyle={{
                  background: '#1a1a1a',
                  border: '1px solid #333',
                  borderRadius: 3,
                  fontSize: 10,
                }}
                labelStyle={{ color: '#888' }}
              />
              <Bar dataKey="success" name="Success %" radius={[2, 2, 0, 0]}>
                {presets.map((_, i) => (
                  <Cell key={i} fill={i % 2 === 0 ? '#e0e0e0' : '#888'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Per-preset bars */}
      {presets.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>
            By Preset
          </div>
          {presets.map(p => {
          const successPct = p.total > 0 ? Math.round((p.success / p.total) * 100) : 0;
          const llmWidth = Math.max(2, (p.llmCalls / maxLlmCalls) * 100);
          const tokenWidth = Math.max(2, (p.tokensOut / maxTokens) * 100);
          return (
          <div key={p.preset} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#ccc', fontFamily: 'monospace' }}>{p.preset}</span>
              <span style={{ color: '#888' }}>
                {p.success}/{p.total} ok
                {` · ${successPct}%`}
                {p.avgConfidence > 0 && ` · ${p.avgConfidence}%`}
                {p.avgDuration > 0 && ` · ${p.avgDuration}s`}
              </span>
            </div>
            {/* LLM calls bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: '#666', fontSize: 9, width: 50 }}>LLM</span>
              <div
                style={{ flex: 1, height: 6, background: '#1a1a1a', borderRadius: 3 }}
                title={`LLM calls: ${p.llmCalls}`}
              >
                <div style={{
                  width: `${llmWidth}%`,
                  height: '100%',
                  background: '#e0e0e0',
                  borderRadius: 3,
                  transition: 'width 0.3s',
                }} />
              </div>
              <span style={{ color: '#888', fontSize: 9, width: 30, textAlign: 'right' }}>{p.llmCalls}</span>
            </div>
            {/* Tokens bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: '#666', fontSize: 9, width: 50 }}>Tokens</span>
              <div
                style={{ flex: 1, height: 6, background: '#1a1a1a', borderRadius: 3 }}
                title={`Tokens out: ${p.tokensOut}`}
              >
                <div style={{
                  width: `${tokenWidth}%`,
                  height: '100%',
                  background: '#999',
                  borderRadius: 3,
                  transition: 'width 0.3s',
                }} />
              </div>
              <span style={{ color: '#888', fontSize: 9, width: 30, textAlign: 'right' }}>
                {p.tokensOut > 1000 ? `${(p.tokensOut / 1000).toFixed(1)}k` : p.tokensOut}
              </span>
            </div>
          </div>
        );
        })}
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{
      background: '#111',
      border: '1px solid #222',
      borderRadius: 4,
      padding: '8px 10px',
      textAlign: 'center',
    }}>
      <div style={{ color: '#e0e0e0', fontSize: 18, fontWeight: 600, fontFamily: 'monospace' }}>
        {value}
      </div>
      <div style={{ color: '#666', fontSize: 9, textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 2 }}>
        {label}
      </div>
    </div>
  );
}
