/**
 * MARKER_153.3A: OnboardingModal — first-open project setup wizard.
 *
 * Shows when /api/mcc/init returns has_project=false.
 * 3 steps:
 *   1. Source: Choose local path or git URL
 *   2. Scanning: POST /api/mcc/project/init → progress
 *   3. Ready: "Project ready!" → close modal
 *
 * After completing, useMCCStore.hasProject becomes true,
 * and the MCC shows the Roadmap DAG view.
 *
 * @phase 153
 * @wave 3
 */

import { useCallback, useState } from 'react';
import { useMCCStore } from '../../store/useMCCStore';

const API_BASE = 'http://localhost:5001/api/mcc';

type Step = 'source' | 'scanning' | 'ready' | 'error';

interface Props {
  onComplete: () => void;
}

export function OnboardingModal({ onComplete }: Props) {
  const [step, setStep] = useState<Step>('source');
  const [sourceType, setSourceType] = useState<'local' | 'git'>('local');
  const [sourcePath, setSourcePath] = useState('');
  const [quotaGb, setQuotaGb] = useState(10);
  const [error, setError] = useState('');
  const [projectId, setProjectId] = useState('');

  const initMCC = useMCCStore(s => s.initMCC);

  const handleSubmit = useCallback(async () => {
    if (!sourcePath.trim()) {
      setError('Please enter a source path');
      return;
    }

    setStep('scanning');
    setError('');

    try {
      const res = await fetch(`${API_BASE}/project/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: sourceType,
          source_path: sourcePath.trim(),
          quota_gb: quotaGb,
        }),
      });

      const data = await res.json();

      if (data.success) {
        setProjectId(data.project_id);
        setStep('ready');
        // Refresh MCC store with new project data
        await initMCC();
      } else {
        setError(data.errors?.join(', ') || 'Project setup failed');
        setStep('error');
      }
    } catch (err) {
      setError(`Connection error: ${err instanceof Error ? err.message : 'unknown'}`);
      setStep('error');
    }
  }, [sourcePath, sourceType, quotaGb, initMCC]);

  const handleRetry = useCallback(() => {
    setStep('source');
    setError('');
  }, []);

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 1300,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(0,0,0,0.75)',
      fontFamily: 'monospace',
    }}>
      <div style={{
        width: 440,
        background: '#0a0a0a',
        border: '1px solid #333',
        borderRadius: 8,
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #222',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <span style={{ fontSize: 16 }}>{'🌿'}</span>
          <div>
            <div style={{ color: '#e0e0e0', fontSize: 13, fontWeight: 600 }}>
              Mycelium Command Center
            </div>
            <div style={{ color: '#666', fontSize: 9, marginTop: 2 }}>
              {step === 'source' && 'Step 1: Choose your project source'}
              {step === 'scanning' && 'Step 2: Setting up sandbox...'}
              {step === 'ready' && 'Step 3: Ready!'}
              {step === 'error' && 'Setup failed'}
            </div>
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: '20px' }}>

          {/* Step 1: Source selection */}
          {step === 'source' && (
            <>
              {/* Source type toggle */}
              <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                {(['local', 'git'] as const).map(t => (
                  <button
                    key={t}
                    onClick={() => setSourceType(t)}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      background: sourceType === t ? 'rgba(78,205,196,0.12)' : '#111',
                      border: `1px solid ${sourceType === t ? '#4ecdc4' : '#333'}`,
                      borderRadius: 4,
                      color: sourceType === t ? '#c6ffff' : '#888',
                      fontSize: 11,
                      cursor: 'pointer',
                      fontFamily: 'monospace',
                    }}
                  >
                    {t === 'local' ? '📂 Local Path' : '🔗 Git URL'}
                  </button>
                ))}
              </div>

              {/* Source path input */}
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontSize: 9, color: '#666', marginBottom: 4, textTransform: 'uppercase' }}>
                  {sourceType === 'local' ? 'Project Path' : 'Git Repository URL'}
                </label>
                <input
                  type="text"
                  value={sourcePath}
                  onChange={e => setSourcePath(e.target.value)}
                  placeholder={sourceType === 'local'
                    ? '/Users/you/my-project'
                    : 'https://github.com/user/repo.git'
                  }
                  autoFocus
                  onKeyDown={e => { if (e.key === 'Enter') handleSubmit(); }}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: '#111',
                    border: '1px solid #333',
                    borderRadius: 4,
                    color: '#e0e0e0',
                    fontSize: 12,
                    fontFamily: 'monospace',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              {/* Quota slider */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 9, color: '#666', marginBottom: 4, textTransform: 'uppercase' }}>
                  Sandbox Quota: {quotaGb} GB
                </label>
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={quotaGb}
                  onChange={e => setQuotaGb(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#4ecdc4' }}
                />
              </div>

              {error && (
                <div style={{ padding: '8px 10px', background: '#1a0a0a', border: '1px solid #422', borderRadius: 4, color: '#e74c3c', fontSize: 10, marginBottom: 12 }}>
                  {error}
                </div>
              )}

              {/* Submit button */}
              <button
                onClick={handleSubmit}
                disabled={!sourcePath.trim()}
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  background: sourcePath.trim() ? 'rgba(78,205,196,0.15)' : '#111',
                  border: `1px solid ${sourcePath.trim() ? '#4ecdc4' : '#333'}`,
                  borderRadius: 4,
                  color: sourcePath.trim() ? '#c6ffff' : '#555',
                  fontSize: 12,
                  fontFamily: 'monospace',
                  cursor: sourcePath.trim() ? 'pointer' : 'not-allowed',
                }}
              >
                {'→'} Initialize Project
              </button>
            </>
          )}

          {/* Step 2: Scanning */}
          {step === 'scanning' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: 24, marginBottom: 12 }}>{'⏳'}</div>
              <div style={{ color: '#aaa', fontSize: 12, marginBottom: 8 }}>
                Setting up sandbox...
              </div>
              <div style={{ color: '#666', fontSize: 10 }}>
                {sourceType === 'local' ? 'Copying project files' : 'Cloning repository'}
              </div>
              {/* Progress bar animation */}
              <div style={{
                marginTop: 16,
                height: 3,
                background: '#222',
                borderRadius: 2,
                overflow: 'hidden',
              }}>
                <div style={{
                  width: '60%',
                  height: '100%',
                  background: '#4ecdc4',
                  borderRadius: 2,
                  animation: 'onboarding-scan 1.5s ease-in-out infinite',
                }} />
              </div>
            </div>
          )}

          {/* Step 3: Ready */}
          {step === 'ready' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: 24, marginBottom: 12 }}>{'✓'}</div>
              <div style={{ color: '#c6ffff', fontSize: 14, marginBottom: 8 }}>
                Project Ready!
              </div>
              <div style={{ color: '#666', fontSize: 10, marginBottom: 16 }}>
                {projectId}
              </div>
              <button
                onClick={onComplete}
                style={{
                  padding: '10px 24px',
                  background: 'rgba(78,205,196,0.15)',
                  border: '1px solid #4ecdc4',
                  borderRadius: 4,
                  color: '#c6ffff',
                  fontSize: 12,
                  fontFamily: 'monospace',
                  cursor: 'pointer',
                }}
              >
                Open Command Center {'→'}
              </button>
            </div>
          )}

          {/* Error state */}
          {step === 'error' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: 24, marginBottom: 12 }}>{'✕'}</div>
              <div style={{ color: '#e74c3c', fontSize: 12, marginBottom: 8 }}>
                Setup Failed
              </div>
              <div style={{ color: '#777', fontSize: 10, marginBottom: 16, maxWidth: 360, margin: '0 auto 16px' }}>
                {error}
              </div>
              <button
                onClick={handleRetry}
                style={{
                  padding: '8px 20px',
                  background: '#1a1a1a',
                  border: '1px solid #333',
                  borderRadius: 4,
                  color: '#ddd',
                  fontSize: 11,
                  fontFamily: 'monospace',
                  cursor: 'pointer',
                }}
              >
                {'←'} Try Again
              </button>
            </div>
          )}
        </div>

        {/* Footer - step dots */}
        <div style={{
          padding: '10px 20px',
          borderTop: '1px solid #1a1a1a',
          display: 'flex',
          justifyContent: 'center',
          gap: 6,
        }}>
          {(['source', 'scanning', 'ready'] as const).map((s, i) => (
            <span key={s} style={{
              width: 6, height: 6, borderRadius: '50%',
              background: step === s || (step === 'error' && s === 'source')
                ? '#4ecdc4' : '#333',
              display: 'inline-block',
            }} />
          ))}
        </div>
      </div>

      <style>{`
        @keyframes onboarding-scan {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(67%); }
          100% { transform: translateX(-100%); }
        }
      `}</style>
    </div>
  );
}
