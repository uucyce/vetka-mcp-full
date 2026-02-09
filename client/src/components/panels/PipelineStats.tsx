/**
 * MARKER_126.0D: Pipeline Statistics — monochrome bars, no chart library.
 * MARKER_126.12: Live refresh + running task progress + improved summary.
 * Nolan style: dark, serious, minimal color. Itten color only for accents.
 *
 * @phase 126.12
 * @depends TaskData
 */

import { useEffect, useState, useCallback } from 'react';
import { TaskData, PipelineStatsData } from './TaskCard';

interface PipelineStatsProps {
  tasks: TaskData[];
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

export function PipelineStats({ tasks, onRefresh }: PipelineStatsProps) {
  // MARKER_126.12A: Live refresh via CustomEvent
  const [, setTick] = useState(0);

  useEffect(() => {
    const handleBoardUpdate = () => {
      setTick(t => t + 1);
      onRefresh?.();
    };

    window.addEventListener('task-board-updated', handleBoardUpdate);

    // MARKER_126.12B: Poll more frequently (5s) when running tasks exist
    const hasRunning = tasks.some(t => t.status === 'running');
    const interval = setInterval(() => {
      setTick(t => t + 1);  // Force re-render for elapsed time
      if (hasRunning) onRefresh?.();  // Fetch fresh data when running
    }, hasRunning ? 5000 : 30000);

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
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
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 8,
          }}>
            <StatBox label="Total Runs" value={totalRuns} />
            <StatBox label="Success" value={`${successRate}%`} />
            <StatBox label="Avg Duration" value={avgDuration > 0 ? `${avgDuration}s` : '-'} />
            <StatBox label="LLM Calls" value={totalLlmCalls} />
          </div>

          {/* MARKER_126.12C: Token totals */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            padding: '6px 8px',
            background: '#111',
            borderRadius: 3,
            fontSize: 10,
            fontFamily: 'monospace',
          }}>
            <span style={{ color: '#666' }}>tokens</span>
            <span style={{ color: '#888' }}>
              {totalTokensIn > 1000 ? `${(totalTokensIn / 1000).toFixed(1)}k` : totalTokensIn} in
              {' / '}
              {totalTokensOut > 1000 ? `${(totalTokensOut / 1000).toFixed(1)}k` : totalTokensOut} out
            </span>
          </div>
        </>
      )}

      {/* Per-preset bars */}
      {presets.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>
            By Preset
          </div>
          {presets.map(p => (
          <div key={p.preset} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#ccc', fontFamily: 'monospace' }}>{p.preset}</span>
              <span style={{ color: '#888' }}>
                {p.success}/{p.total} ok
                {p.avgDuration > 0 && ` \u00B7 ${p.avgDuration}s`}
              </span>
            </div>
            {/* LLM calls bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: '#666', fontSize: 9, width: 50 }}>LLM</span>
              <div style={{ flex: 1, height: 6, background: '#1a1a1a', borderRadius: 3 }}>
                <div style={{
                  width: `${(p.llmCalls / maxLlmCalls) * 100}%`,
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
              <div style={{ flex: 1, height: 6, background: '#1a1a1a', borderRadius: 3 }}>
                <div style={{
                  width: `${(p.tokensOut / maxTokens) * 100}%`,
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
        ))}
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
