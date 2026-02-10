/**
 * MARKER_126.0D: League Tester — run pipeline tests with different presets.
 * MARKER_126.2C: Style upgrade — glassmorphism buttons, monospace.
 * Nolan: dark grid, no emoji, serious.
 *
 * @phase 126.2
 */

import { useState } from 'react';

// MARKER_134.C34G: Quick model test models
const QUICK_MODELS = [
  { id: 'grok-3-fast', label: 'Grok Fast' },
  { id: 'qwen3-coder-flash', label: 'Qwen Flash' },
  { id: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { id: 'claude-3-5-haiku-20241022', label: 'Haiku' },
  { id: 'gemini-2.0-flash', label: 'Gemini Flash' },
] as const;

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

  // MARKER_134.C34G: Quick model test state
  const [quickPrompt, setQuickPrompt] = useState('');
  const [quickModel, setQuickModel] = useState<string>(QUICK_MODELS[0].id);
  const [quickLoading, setQuickLoading] = useState(false);
  const [quickResponse, setQuickResponse] = useState<string | null>(null);

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
      <div style={{ color: '#444', fontSize: 9, textTransform: 'uppercase', letterSpacing: 2, fontFamily: 'monospace' }}>
        league benchmark
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
                background: isRunning
                  ? 'rgba(255,255,255,0.03)'
                  : isDone
                    ? (lastResult?.success ? 'rgba(120,160,120,0.06)' : 'rgba(160,120,120,0.06)')
                    : 'rgba(255,255,255,0.02)',
                border: `1px solid ${isRunning ? 'rgba(255,255,255,0.12)' : isDone
                  ? (lastResult?.success ? 'rgba(120,160,120,0.15)' : 'rgba(160,120,120,0.15)')
                  : 'rgba(255,255,255,0.06)'}`,
                borderRadius: 3,
                color: isRunning ? '#555' : '#bbb',
                cursor: running ? 'not-allowed' : 'pointer',
                fontSize: 10,
                fontFamily: 'monospace',
                transition: 'all 0.2s',
                textAlign: 'center',
                lineHeight: 1.4,
                backdropFilter: 'blur(2px)',
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
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: 3,
          padding: 10,
          fontSize: 10,
          fontFamily: 'monospace',
        }}>
          <div style={{ color: lastResult.success ? '#aaa' : '#777', marginBottom: 4, letterSpacing: 0.5 }}>
            {lastResult.preset} {lastResult.success ? '— pass' : '— fail'}
          </div>
          {lastResult.stats && (
            <div style={{ color: '#666', lineHeight: 1.6 }}>
              subtasks: {lastResult.stats.subtasks_completed}/{lastResult.stats.subtasks_total}
              {lastResult.stats.llm_calls > 0 && ` · ${lastResult.stats.llm_calls} LLM calls`}
              {lastResult.stats.duration_s > 0 && ` · ${lastResult.stats.duration_s}s`}
            </div>
          )}
          {lastResult.error && (
            <div style={{ color: '#666', marginTop: 4 }}>
              {lastResult.error.slice(0, 120)}
            </div>
          )}
        </div>
      )}

      {/* MARKER_134.C34G: Quick Model Test */}
      <div style={{
        marginTop: 16,
        paddingTop: 16,
        borderTop: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{ color: '#444', fontSize: 9, textTransform: 'uppercase', letterSpacing: 2, fontFamily: 'monospace', marginBottom: 10 }}>
          quick model test
        </div>

        <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
          <select
            value={quickModel}
            onChange={(e) => setQuickModel(e.target.value)}
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 3,
              color: '#999',
              fontSize: 10,
              fontFamily: 'monospace',
              padding: '6px 8px',
              outline: 'none',
            }}
          >
            {QUICK_MODELS.map(m => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
          <button
            onClick={async () => {
              if (!quickPrompt.trim()) return;
              setQuickLoading(true);
              setQuickResponse(null);
              try {
                const res = await fetch('http://localhost:5001/api/chat', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    text: quickPrompt,
                    model: quickModel,
                    node_path: 'playground_test',
                    node_id: 'test',
                  }),
                });
                const data = await res.json();
                setQuickResponse(data.reply || data.error || 'No response');
              } catch (e: any) {
                setQuickResponse(`Error: ${e.message}`);
              } finally {
                setQuickLoading(false);
              }
            }}
            disabled={quickLoading || !quickPrompt.trim()}
            style={{
              padding: '6px 12px',
              background: quickLoading ? 'transparent' : 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 3,
              color: quickLoading ? '#555' : '#aaa',
              fontSize: 10,
              fontFamily: 'monospace',
              cursor: quickLoading ? 'wait' : 'pointer',
            }}
          >
            {quickLoading ? '...' : 'send'}
          </button>
        </div>

        <textarea
          value={quickPrompt}
          onChange={(e) => setQuickPrompt(e.target.value)}
          placeholder="Enter test prompt..."
          style={{
            width: '100%',
            height: 60,
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 3,
            color: '#ccc',
            fontSize: 11,
            fontFamily: 'monospace',
            padding: 8,
            resize: 'none',
            outline: 'none',
          }}
        />

        {quickResponse && (
          <div style={{
            marginTop: 8,
            padding: 10,
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 3,
            fontSize: 11,
            fontFamily: 'monospace',
            color: '#aaa',
            maxHeight: 150,
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.5,
          }}>
            {quickResponse}
          </div>
        )}
      </div>
    </div>
  );
}
