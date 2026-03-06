/**
 * MARKER_153.3A: OnboardingModal — first-open project setup wizard.
 *
 * Extended in P161.7.E for multi-project tab creation:
 * - Step 1: Source
 * - Step 2: Sandbox path
 * - Esc closes modal (no explicit Cancel button)
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { isTauri, openFolderDialog } from '../../config/tauri';

const API_BASE = 'http://localhost:5001/api/mcc';

type Step = 'source' | 'sandbox' | 'scanning' | 'ready' | 'error';

interface Props {
  onComplete: () => void;
}

function inferSandboxPath(sourceType: 'local' | 'git', sourcePath: string): string {
  const trimmed = String(sourcePath || '').trim();
  if (!trimmed) return '';

  if (sourceType === 'local') {
    const normalized = trimmed.replace(/\\/g, '/').replace(/\/+$/, '');
    const parts = normalized.split('/').filter(Boolean);
    const name = parts.length > 0 ? parts[parts.length - 1] : 'project';
    const parent = parts.length > 1 ? `/${parts.slice(0, -1).join('/')}` : '/tmp';
    return `${parent}/${name}_playground`;
  }

  const repo = trimmed
    .replace(/\.git$/i, '')
    .split('/')
    .filter(Boolean)
    .pop() || 'repo';
  return `/tmp/${repo}_playground`;
}

export function OnboardingModal({ onComplete }: Props) {
  // MARKER_161.7.MULTIPROJECT.UI.NEW_TAB_WIZARD.V1
  // MARKER_161.7.MULTIPROJECT.UI.ESC_CLOSE_MODAL.V1
  // MARKER_161.7.MULTIPROJECT.UI.LOCAL_SOURCE_PICKER.V1
  // MARKER_161.7.MULTIPROJECT.UI.SANDBOX_PICKER.V1
  // MARKER_161.8.MULTIPROJECT.UI.GRANDMA_FLOW_SOURCE_STEP.V1
  const [step, setStep] = useState<Step>('source');
  const [sourceType, setSourceType] = useState<'local' | 'git'>('local');
  const [sourcePath, setSourcePath] = useState('');
  const [sandboxPath, setSandboxPath] = useState('');
  const [quotaGb, setQuotaGb] = useState(10);
  const [error, setError] = useState('');
  const [projectId, setProjectId] = useState('');

  const initMCC = useMCCStore((s) => s.initMCC);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onComplete();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onComplete]);

  const suggestedSandbox = useMemo(
    () => inferSandboxPath(sourceType, sourcePath),
    [sourceType, sourcePath],
  );

  useEffect(() => {
    if (step !== 'sandbox') return;
    if (!sandboxPath.trim() && suggestedSandbox) {
      setSandboxPath(suggestedSandbox);
    }
  }, [step, sandboxPath, suggestedSandbox]);

  const handleSourceNext = useCallback(() => {
    if (!sourcePath.trim()) {
      setError('Please enter a source path');
      return;
    }
    setError('');
    setStep('sandbox');
  }, [sourcePath]);

  const handleBrowseLocalSource = useCallback(async () => {
    if (!isTauri()) {
      setError('Native folder picker is available only in desktop app (Tauri).');
      return;
    }
    const picked = await openFolderDialog('Select project source folder');
    if (!picked) return;
    setSourcePath(String(picked));
    setError('');
  }, []);

  const handleBrowseSandboxPath = useCallback(async () => {
    if (!isTauri()) {
      setError('Native folder picker is available only in desktop app (Tauri).');
      return;
    }
    const picked = await openFolderDialog('Select sandbox folder');
    if (!picked) return;
    setSandboxPath(String(picked));
    setError('');
  }, []);

  const handleSelectSourceType = useCallback(
    async (nextType: 'local' | 'git') => {
      setSourceType(nextType);
      if (nextType === 'local') {
        await handleBrowseLocalSource();
      }
    },
    [handleBrowseLocalSource],
  );

  const handleSubmit = useCallback(async () => {
    if (!sourcePath.trim()) {
      setError('Please enter a source path');
      setStep('source');
      return;
    }
    if (!sandboxPath.trim()) {
      setError('Please enter a sandbox path');
      setStep('sandbox');
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
          sandbox_path: sandboxPath.trim(),
          quota_gb: quotaGb,
        }),
      });

      const data = await res.json();

      if (data.success) {
        setProjectId(data.project_id);
        setStep('ready');
        await initMCC();
      } else {
        setError(data.errors?.join(', ') || 'Project setup failed');
        setStep('error');
      }
    } catch (err) {
      setError(`Connection error: ${err instanceof Error ? err.message : 'unknown'}`);
      setStep('error');
    }
  }, [sourcePath, sandboxPath, sourceType, quotaGb, initMCC]);

  const handleRetry = useCallback(() => {
    setStep('source');
    setError('');
  }, []);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1300,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.75)',
        fontFamily: 'monospace',
      }}
    >
      <div
        style={{
          width: 520,
          background: NOLAN_PALETTE.bgLight,
          border: `1px solid ${NOLAN_PALETTE.border}`,
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '16px 20px',
            borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: 2,
              border: `1px solid ${NOLAN_PALETTE.borderLight}`,
              display: 'inline-block',
            }}
          />
          <div style={{ flex: 1 }}>
            <div style={{ color: NOLAN_PALETTE.text, fontSize: 13, fontWeight: 600 }}>
              MYCELIUM
            </div>
            <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 9, marginTop: 2 }}>
              {step === 'source' && 'Step 1: Import project source'}
              {step === 'sandbox' && 'Step 2: Choose sandbox path'}
              {step === 'scanning' && 'Step 3: Creating project tab'}
              {step === 'ready' && 'Step 4: Ready'}
              {step === 'error' && 'Setup failed'}
            </div>
          </div>
          <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 9 }}>Esc</div>
        </div>

        <div style={{ padding: '20px' }}>
          {step === 'source' && (
            <>
              <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                {(['local', 'git'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => {
                      void handleSelectSourceType(t);
                    }}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      background: sourceType === t ? NOLAN_PALETTE.bgDim : NOLAN_PALETTE.bg,
                      border: `1px solid ${sourceType === t ? NOLAN_PALETTE.borderLight : NOLAN_PALETTE.border}`,
                      borderRadius: 4,
                      color: sourceType === t ? NOLAN_PALETTE.text : NOLAN_PALETTE.textMuted,
                      fontSize: 11,
                      cursor: 'pointer',
                      fontFamily: 'monospace',
                    }}
                  >
                    {t === 'local' ? 'From This Mac' : 'From Git URL'}
                  </button>
                ))}
              </div>

              <div style={{ marginBottom: 14 }}>
                <label
                  style={{
                    display: 'block',
                    fontSize: 9,
                    color: NOLAN_PALETTE.textDim,
                    marginBottom: 4,
                    textTransform: 'uppercase',
                  }}
                >
                  {sourceType === 'local' ? 'Project Folder' : 'Git Repository URL'}
                </label>
                <input
                  type="text"
                  value={sourcePath}
                  onChange={(e) => setSourcePath(e.target.value)}
                  placeholder={sourceType === 'local' ? '/Users/you/my-project' : 'https://github.com/user/repo.git'}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSourceNext();
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: NOLAN_PALETTE.bg,
                    border: `1px solid ${NOLAN_PALETTE.border}`,
                    borderRadius: 4,
                    color: NOLAN_PALETTE.text,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={onComplete}
                  style={{
                    flex: 1,
                    padding: '10px 16px',
                    background: NOLAN_PALETTE.bg,
                    border: `1px solid ${NOLAN_PALETTE.border}`,
                    borderRadius: 4,
                    color: NOLAN_PALETTE.textMuted,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    cursor: 'pointer',
                  }}
                >
                  Skip for now
                </button>
                <button
                  onClick={handleSourceNext}
                  disabled={!sourcePath.trim()}
                  style={{
                    flex: 2,
                    padding: '10px 16px',
                    background: sourcePath.trim() ? NOLAN_PALETTE.bgDim : NOLAN_PALETTE.bg,
                    border: `1px solid ${sourcePath.trim() ? NOLAN_PALETTE.borderLight : NOLAN_PALETTE.border}`,
                    borderRadius: 4,
                    color: sourcePath.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    cursor: sourcePath.trim() ? 'pointer' : 'not-allowed',
                  }}
                >
                  Next: Choose Workspace
                </button>
              </div>
            </>
          )}

          {step === 'sandbox' && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label
                  style={{
                    display: 'block',
                    fontSize: 9,
                    color: NOLAN_PALETTE.textDim,
                    marginBottom: 4,
                    textTransform: 'uppercase',
                  }}
                >
                  Sandbox Path
                </label>
                <input
                  type="text"
                  value={sandboxPath}
                  onChange={(e) => setSandboxPath(e.target.value)}
                  placeholder={suggestedSandbox || '/tmp/project_playground'}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSubmit();
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: NOLAN_PALETTE.bg,
                    border: `1px solid ${NOLAN_PALETTE.border}`,
                    borderRadius: 4,
                    color: NOLAN_PALETTE.text,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
                <button
                  onClick={handleBrowseSandboxPath}
                  style={{
                    marginTop: 8,
                    width: '100%',
                    padding: '8px 10px',
                    background: NOLAN_PALETTE.bg,
                    border: `1px solid ${NOLAN_PALETTE.border}`,
                    borderRadius: 4,
                    color: NOLAN_PALETTE.textMuted,
                    fontSize: 11,
                    fontFamily: 'monospace',
                    cursor: 'pointer',
                  }}
                >
                  Browse Sandbox in Finder
                </button>
              </div>

              <div style={{ marginBottom: 14 }}>
                <label
                  style={{
                    display: 'block',
                    fontSize: 9,
                    color: NOLAN_PALETTE.textDim,
                    marginBottom: 4,
                    textTransform: 'uppercase',
                  }}
                >
                  Sandbox Quota: {quotaGb} GB
                </label>
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={quotaGb}
                  onChange={(e) => setQuotaGb(Number(e.target.value))}
                  style={{ width: '100%', accentColor: NOLAN_PALETTE.text }}
                />
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={() => setStep('source')}
                  style={{
                    flex: 1,
                    padding: '10px 16px',
                    background: NOLAN_PALETTE.bg,
                    border: `1px solid ${NOLAN_PALETTE.border}`,
                    borderRadius: 4,
                    color: NOLAN_PALETTE.textMuted,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    cursor: 'pointer',
                  }}
                >
                  Back
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!sandboxPath.trim()}
                  style={{
                    flex: 2,
                    padding: '10px 16px',
                    background: sandboxPath.trim() ? NOLAN_PALETTE.bgDim : NOLAN_PALETTE.bg,
                    border: `1px solid ${sandboxPath.trim() ? NOLAN_PALETTE.borderLight : NOLAN_PALETTE.border}`,
                    borderRadius: 4,
                    color: sandboxPath.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    cursor: sandboxPath.trim() ? 'pointer' : 'not-allowed',
                  }}
                >
                  Create Project Tab
                </button>
              </div>
            </>
          )}

          {step === 'scanning' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ color: NOLAN_PALETTE.text, fontSize: 12, marginBottom: 8 }}>Creating project tab...</div>
              <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 10 }}>Preparing sandbox and project context</div>
              <div
                style={{
                  marginTop: 16,
                  height: 3,
                  background: NOLAN_PALETTE.borderDim,
                  borderRadius: 2,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: '60%',
                    height: '100%',
                    background: NOLAN_PALETTE.text,
                    borderRadius: 2,
                    animation: 'onboarding-scan 1.5s ease-in-out infinite',
                  }}
                />
              </div>
            </div>
          )}

          {step === 'ready' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ color: NOLAN_PALETTE.text, fontSize: 14, marginBottom: 8 }}>Project Ready</div>
              <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 10, marginBottom: 16 }}>{projectId}</div>
              <button
                onClick={onComplete}
                style={{
                  padding: '10px 24px',
                  background: NOLAN_PALETTE.bgDim,
                  border: `1px solid ${NOLAN_PALETTE.borderLight}`,
                  borderRadius: 4,
                  color: NOLAN_PALETTE.text,
                  fontSize: 12,
                  fontFamily: 'monospace',
                  cursor: 'pointer',
                }}
              >
                Open Command Center
              </button>
            </div>
          )}

          {step === 'error' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ color: NOLAN_PALETTE.text, fontSize: 12, marginBottom: 8 }}>Setup Failed</div>
              <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 10, marginBottom: 16, maxWidth: 420, marginInline: 'auto' }}>{error}</div>
              <button
                onClick={handleRetry}
                style={{
                  padding: '8px 20px',
                  background: NOLAN_PALETTE.bg,
                  border: `1px solid ${NOLAN_PALETTE.border}`,
                  borderRadius: 4,
                  color: NOLAN_PALETTE.text,
                  fontSize: 11,
                  fontFamily: 'monospace',
                  cursor: 'pointer',
                }}
              >
                Retry
              </button>
            </div>
          )}

          {error && step !== 'error' && (
            <div
              style={{
                marginTop: 10,
                padding: '8px 10px',
                background: NOLAN_PALETTE.bg,
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 4,
                color: NOLAN_PALETTE.text,
                fontSize: 10,
              }}
            >
              {error}
            </div>
          )}
        </div>

        <div
          style={{
            padding: '10px 20px',
            borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
            display: 'flex',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          {(['source', 'sandbox', 'scanning', 'ready'] as const).map((s) => (
            <span
              key={s}
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: step === s || (step === 'error' && s === 'source') ? NOLAN_PALETTE.text : NOLAN_PALETTE.border,
                display: 'inline-block',
              }}
            />
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
