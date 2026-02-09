/**
 * MARKER_126.0D: League Tester — run pipeline tests with different presets.
 * Nolan style: dark grid, monochrome buttons, minimal accents.
 *
 * @phase 126.0
 */

import { useState } from 'react';

const LEAGUES = [
  { name: 'Dragon Bronze', preset: 'dragon_bronze', tier: 'economy' },
  { name: 'Dragon Silver', preset: 'dragon_silver', tier: 'standard' },
  { name: 'Dragon Gold', preset: 'dragon_gold', tier: 'premium' },
  { name: 'Titan Lite', preset: 'titan_lite', tier: 'economy' },
  { name: 'Titan Core', preset: 'titan_core', tier: 'standard' },
  { name: 'Titan Prime', preset: 'titan_prime', tier: 'premium' },
] as const;

const API_BASE = 'http://localhost:5001/api/debug';

interface LeagueTesterProps {
  onTestComplete: () => void;
}

interface TestResult {
  preset: string;
  success: boolean;
  stats?: any;
  error?: string;
}

export function LeagueTester({ onTestComplete }: LeagueTesterProps) {
  const [running, setRunning] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<TestResult | null>(null);

  const runTest = async (preset: string) => {
    setRunning(preset);
    setLastResult(null);
    try {
      const res = await fetch(`${API_BASE}/task-board/test-league`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset }),
      });
      const data = await res.json();
      setLastResult({
        preset,
        success: data.success,
        stats: data.stats,
        error: data.error,
      });
      onTestComplete();
    } catch (e: any) {
      setLastResult({ preset, success: false, error: e.message });
    } finally {
      setRunning(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>
        Select a league to benchmark
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
        {LEAGUES.map(league => {
          const isRunning = running === league.preset;
          const isDone = lastResult?.preset === league.preset;
          return (
            <button
              key={league.preset}
              onClick={() => runTest(league.preset)}
              disabled={running !== null}
              style={{
                padding: '10px 8px',
                background: isRunning ? '#1a1a1a' : isDone
                  ? (lastResult?.success ? '#0a1a0a' : '#1a0a0a')
                  : '#111',
                border: `1px solid ${isRunning ? '#444' : isDone
                  ? (lastResult?.success ? '#2a3a2a' : '#3a2a2a')
                  : '#222'}`,
                borderRadius: 4,
                color: isRunning ? '#666' : '#ccc',
                cursor: running ? 'not-allowed' : 'pointer',
                fontSize: 11,
                fontFamily: 'monospace',
                transition: 'all 0.15s',
                textAlign: 'center',
                lineHeight: 1.4,
              }}
            >
              <div style={{ fontWeight: 600 }}>{league.name.split(' ')[0]}</div>
              <div style={{ fontSize: 10, color: '#888' }}>
                {isRunning ? 'running...' : league.name.split(' ')[1]}
              </div>
            </button>
          );
        })}
      </div>

      {/* Last result */}
      {lastResult && (
        <div style={{
          background: '#0d0d0d',
          border: '1px solid #222',
          borderRadius: 4,
          padding: 10,
          fontSize: 11,
          fontFamily: 'monospace',
        }}>
          <div style={{ color: lastResult.success ? '#ccc' : '#888', marginBottom: 4 }}>
            {lastResult.preset}: {lastResult.success ? 'PASS' : 'FAIL'}
          </div>
          {lastResult.stats && (
            <div style={{ color: '#666', lineHeight: 1.6 }}>
              subtasks: {lastResult.stats.subtasks_completed}/{lastResult.stats.subtasks_total}
              {lastResult.stats.llm_calls > 0 && ` \u00B7 ${lastResult.stats.llm_calls} LLM calls`}
              {lastResult.stats.duration_s > 0 && ` \u00B7 ${lastResult.stats.duration_s}s`}
            </div>
          )}
          {lastResult.error && (
            <div style={{ color: '#666', marginTop: 4 }}>
              {lastResult.error.slice(0, 120)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
