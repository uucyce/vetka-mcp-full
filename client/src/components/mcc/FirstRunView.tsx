/**
 * MARKER_154.16A: FirstRunView — clean project setup surface.
 *
 * P161.8 update:
 * - In-interface modal overlay (no route-level onboarding page)
 * - delayed appearance over empty draft tab canvas
 * - source -> workspace flow with skip support
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { isTauri, openFolderDialog } from '../../config/tauri';

const API_BASE = 'http://localhost:5001/api';

type Step = 'hidden' | 'choose' | 'source_input' | 'workspace' | 'creating' | 'error';
type SourceMode = 'local' | 'git' | 'empty';

function inferWorkspacePath(sourceMode: SourceMode, sourcePath: string): string {
  const clean = String(sourcePath || '').trim().replace(/\\/g, '/');
  if (!clean) return '/tmp/mycelium_project_playground';
  if (sourceMode === 'git') {
    const repo = clean.replace(/\.git$/i, '').split('/').filter(Boolean).pop() || 'repo';
    return `/tmp/${repo}_playground`;
  }
  const parts = clean.replace(/\/+$/, '').split('/').filter(Boolean);
  if (!parts.length) return '/tmp/mycelium_project_playground';
  const name = parts[parts.length - 1] || 'project';
  const parent = parts.length > 1 ? `/${parts.slice(0, -1).join('/')}` : '/tmp';
  return `${parent}/${name}_playground`;
}

export function FirstRunView() {
  // MARKER_161.8.MULTIPROJECT.UI.GRANDMA_FLOW_SOURCE_STEP.V2
  // MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_DELAYED_OVERLAY.V1
  const [step, setStep] = useState<Step>('hidden');
  const [sourceMode, setSourceMode] = useState<SourceMode>('local');
  const [sourcePath, setSourcePath] = useState('');
  const [workspacePath, setWorkspacePath] = useState('');
  const [error, setError] = useState('');

  const inputRef = useRef<HTMLInputElement>(null);
  const drillDown = useMCCStore((s) => s.drillDown);
  const initMCC = useMCCStore((s) => s.initMCC);

  useEffect(() => {
    const t = window.setTimeout(() => setStep('choose'), 900);
    return () => window.clearTimeout(t);
  }, []);

  const suggestedWorkspace = useMemo(
    () => inferWorkspacePath(sourceMode, sourcePath),
    [sourceMode, sourcePath],
  );

  useEffect(() => {
    if (step !== 'workspace') return;
    if (!workspacePath.trim() && suggestedWorkspace) {
      setWorkspacePath(suggestedWorkspace);
    }
  }, [step, workspacePath, suggestedWorkspace]);

  const pickLocalSource = useCallback(async () => {
    if (!isTauri()) {
      setSourceMode('local');
      setStep('source_input');
      return;
    }
    const picked = await openFolderDialog('Select project source folder');
    if (picked && String(picked).trim()) {
      setSourceMode('local');
      setSourcePath(String(picked));
      setError('');
      setStep('workspace');
      return;
    }
    setSourceMode('local');
    setStep('source_input');
  }, []);

  const pickWorkspace = useCallback(async () => {
    if (!isTauri()) return;
    const picked = await openFolderDialog('Select workspace folder');
    if (picked && String(picked).trim()) {
      setWorkspacePath(String(picked));
      setError('');
    }
  }, []);

  const submit = useCallback(async () => {
    const sandbox = String(workspacePath || '').trim();
    if (!sandbox) {
      setError('Choose where to create workspace');
      return;
    }
    if (sourceMode !== 'empty' && !String(sourcePath || '').trim()) {
      setError('Choose source path first');
      return;
    }

    setStep('creating');
    setError('');

    try {
      const payload = {
        source_type: sourceMode === 'empty' ? 'empty' : sourceMode,
        source_path: sourceMode === 'empty' ? '' : String(sourcePath || '').trim(),
        sandbox_path: sandbox,
        quota_gb: 10,
      };

      const res = await fetch(`${API_BASE}/mcc/project/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data?.success) {
        setError(String(data?.errors?.[0] || data?.detail || `HTTP ${res.status}`));
        setStep('error');
        return;
      }

      await initMCC();
      drillDown('roadmap');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
      setStep('error');
    }
  }, [workspacePath, sourceMode, sourcePath, initMCC, drillDown]);

  if (step === 'hidden') return null;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: 'rgba(0,0,0,0.32)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 35,
        pointerEvents: 'auto',
        fontFamily: 'monospace',
      }}
    >
      <div
        style={{
          width: 680,
          background: NOLAN_PALETTE.bgLight,
          border: `1px solid ${NOLAN_PALETTE.border}`,
          borderRadius: 10,
          padding: 18,
        }}
      >
        <div style={{ color: NOLAN_PALETTE.text, fontSize: 18, fontWeight: 700, marginBottom: 4 }}>
          Continue with an existing project or create a new project
        </div>
        <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 11, marginBottom: 14 }}>
          Choose source, then choose workspace location.
        </div>

        {step === 'choose' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <button
              onClick={() => { void pickLocalSource(); }}
              style={{ border: `1px solid ${NOLAN_PALETTE.border}`, borderRadius: 8, background: NOLAN_PALETTE.bgDim, color: NOLAN_PALETTE.text, padding: '16px 10px', cursor: 'pointer' }}
            >
              <div style={{ fontSize: 20, fontWeight: 700 }}>From Disk</div>
              <div style={{ fontSize: 11, color: NOLAN_PALETTE.textMuted, marginTop: 6 }}>Copy existing folder</div>
            </button>
            <button
              onClick={() => { setSourceMode('git'); setStep('source_input'); }}
              style={{ border: `1px solid ${NOLAN_PALETTE.border}`, borderRadius: 8, background: NOLAN_PALETTE.bgDim, color: NOLAN_PALETTE.text, padding: '16px 10px', cursor: 'pointer' }}
            >
              <div style={{ fontSize: 20, fontWeight: 700 }}>From Git</div>
              <div style={{ fontSize: 11, color: NOLAN_PALETTE.textMuted, marginTop: 6 }}>Clone repository URL</div>
            </button>
          </div>
        )}

        {step === 'source_input' && (
          <div>
            <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 10, marginBottom: 6 }}>
              {sourceMode === 'git' ? 'Git repository URL' : 'Source folder path'}
            </div>
            <input
              ref={inputRef}
              autoFocus
              value={sourcePath}
              onChange={(e) => setSourcePath(e.target.value)}
              placeholder={sourceMode === 'git' ? 'https://github.com/org/repo.git' : '/Users/you/projects/my-app'}
              style={{ width: '100%', boxSizing: 'border-box', borderRadius: 6, border: `1px solid ${NOLAN_PALETTE.border}`, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.text, padding: '9px 10px', fontFamily: 'monospace', fontSize: 12 }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button onClick={() => setStep('choose')} style={{ flex: 1, borderRadius: 6, border: `1px solid ${NOLAN_PALETTE.border}`, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.textMuted, padding: '9px 10px', cursor: 'pointer' }}>Back</button>
              <button onClick={() => setStep('workspace')} disabled={!sourcePath.trim()} style={{ flex: 2, borderRadius: 6, border: `1px solid ${sourcePath.trim() ? NOLAN_PALETTE.borderLight : NOLAN_PALETTE.border}`, background: sourcePath.trim() ? NOLAN_PALETTE.bgDim : NOLAN_PALETTE.bg, color: sourcePath.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim, padding: '9px 10px', cursor: sourcePath.trim() ? 'pointer' : 'not-allowed' }}>Next: Workspace</button>
            </div>
          </div>
        )}

        {(step === 'workspace' || step === 'creating' || step === 'error') && (
          <div>
            <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 10, marginBottom: 6 }}>Workspace path (where this tab project will live)</div>
            <input
              value={workspacePath}
              onChange={(e) => setWorkspacePath(e.target.value)}
              placeholder={suggestedWorkspace || '/tmp/mycelium_project_playground'}
              style={{ width: '100%', boxSizing: 'border-box', borderRadius: 6, border: `1px solid ${NOLAN_PALETTE.border}`, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.text, padding: '9px 10px', fontFamily: 'monospace', fontSize: 12 }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button onClick={() => { void pickWorkspace(); }} style={{ flex: 1, borderRadius: 6, border: `1px solid ${NOLAN_PALETTE.border}`, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.textMuted, padding: '9px 10px', cursor: 'pointer' }}>Choose Folder</button>
              <button onClick={() => setStep(sourceMode === 'empty' ? 'choose' : 'source_input')} style={{ flex: 1, borderRadius: 6, border: `1px solid ${NOLAN_PALETTE.border}`, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.textMuted, padding: '9px 10px', cursor: 'pointer' }}>Back</button>
              <button onClick={() => { void submit(); }} disabled={!workspacePath.trim() || step === 'creating'} style={{ flex: 2, borderRadius: 6, border: `1px solid ${workspacePath.trim() ? NOLAN_PALETTE.borderLight : NOLAN_PALETTE.border}`, background: workspacePath.trim() ? NOLAN_PALETTE.bgDim : NOLAN_PALETTE.bg, color: workspacePath.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim, padding: '9px 10px', cursor: workspacePath.trim() ? 'pointer' : 'not-allowed' }}>{step === 'creating' ? 'Creating...' : 'Create Tab Project'}</button>
            </div>
            {error && (
              <div style={{ marginTop: 10, border: `1px solid ${NOLAN_PALETTE.border}`, borderRadius: 6, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.text, padding: '8px 10px', fontSize: 10 }}>
                {error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
