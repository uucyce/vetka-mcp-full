/**
 * MARKER_126.0D: Pipeline Statistics — monochrome bars, no chart library.
 * Nolan style: dark, serious, minimal color. Itten color only for accents.
 *
 * @phase 126.0
 * @depends TaskData
 */

import { TaskData, PipelineStatsData } from './TaskCard';

interface PipelineStatsProps {
  tasks: TaskData[];
}

interface PresetStats {
  preset: string;
  total: number;
  success: number;
  llmCalls: number;
  tokensOut: number;
  avgDuration: number;
  avgConfidence: number;
}

export function PipelineStats({ tasks }: PipelineStatsProps) {
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
        avgDuration: 0,
        avgConfidence: 0,
      };
    }
    const p = byPreset[preset];
    p.total += 1;
    if (stats.success) p.success += 1;
    p.llmCalls += stats.llm_calls || 0;
    p.tokensOut += stats.tokens_out || 0;
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

  if (presets.length === 0) {
    return (
      <div style={{ color: '#555', textAlign: 'center', padding: 40, fontSize: 12, lineHeight: 1.6 }}>
        No pipeline runs yet.<br />
        Dispatch a task to see statistics.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Summary row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 8,
      }}>
        <StatBox label="Total Runs" value={presets.reduce((s, p) => s + p.total, 0)} />
        <StatBox label="Success" value={`${presets.reduce((s, p) => s + p.success, 0)}`} />
        <StatBox label="LLM Calls" value={presets.reduce((s, p) => s + p.llmCalls, 0)} />
      </div>

      {/* Per-preset bars */}
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
