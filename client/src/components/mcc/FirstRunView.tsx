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
// MARKER_176.15: Centralized MCC API config import.
import { MCC_API } from '../../config/api.config';


type Step = 'hidden' | 'choose' | 'source_input' | 'workspace' | 'creating' | 'error';
type SourceMode = 'local' | 'git' | 'empty';

function inferWorkspacePath(sourceMode: SourceMode, sourcePath: string): string {
  const clean = String(sourcePath || '').trim().replace(/\\/g, '/');
  if (!clean) return '';
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

function inferProjectNameFromWorkspace(workspacePath: string): string {
  const clean = String(workspacePath || '').trim().replace(/\\/g, '/').replace(/\/+$/, '');
  if (!clean) return '';
  const base = clean.split('/').filter(Boolean).pop() || '';
  return String(base || '').trim();
}

function normalizeAbsPath(input: string): string {
  const raw = String(input || '').trim();
  if (!raw) return '';
  return raw.replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
}

function pathsOverlapOrNested(pathA: string, pathB: string): boolean {
  const a = normalizeAbsPath(pathA);
  const b = normalizeAbsPath(pathB);
  if (!a || !b) return false;
  return a === b || a.startsWith(`${b}/`) || b.startsWith(`${a}/`);
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
  const projectTabs = useMCCStore((s) => s.projectTabs);

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
    if (sourceMode === 'empty') return;
    if (!workspacePath.trim() && suggestedWorkspace) {
      setWorkspacePath(suggestedWorkspace);
    }
  }, [step, workspacePath, suggestedWorkspace, sourceMode]);

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
    if (sourceMode === 'local' && pathsOverlapOrNested(sourcePath, sandbox)) {
      setError('Workspace must be isolated from source path (no nested/equal folders)');
      return;
    }
    // MARKER_161.9.MULTIPROJECT.ISOLATION.UI_REGISTRY_PRECHECK.V1
    for (const tab of projectTabs) {
      const tabName = String((tab as any)?.display_name || (tab as any)?.project_id || 'project');
      const tabSandbox = String((tab as any)?.sandbox_path || '');
      const tabSource = String((tab as any)?.source_path || '');
      if (pathsOverlapOrNested(sandbox, tabSandbox) || pathsOverlapOrNested(sandbox, tabSource)) {
        setError(`Workspace overlaps existing project: ${tabName}`);
        return;
      }
    }

    setStep('creating');
    setError('');

    try {
      const projectName = inferProjectNameFromWorkspace(sandbox) || 'name_project';
      const payload = {
        source_type: sourceMode === 'empty' ? 'empty' : sourceMode,
        source_path: sourceMode === 'empty' ? '' : String(sourcePath || '').trim(),
        sandbox_path: sandbox,
        // MARKER_161.9.MULTIPROJECT.NAMING.API_CONTRACT.V1
        project_name: projectName,
        quota_gb: 10,
      };

      const res = await fetch(`${MCC_API}/project/init`, {
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
      // MARKER_176.18: Surface backend/network failures instead of silent create dead-ends.
      const message = err instanceof Error ? err.message : 'Create failed';
      setError(message && /fetch|network|failed to fetch/i.test(message)
        ? 'Network error - check if backend is running'
        : message);
      setStep('error');
    }
  }, [workspacePath, sourceMode, sourcePath, projectTabs, initMCC, drillDown]);

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
        <div style={{ color: NOLAN_PALETTE.text, fontSize: 18, fontWeight: 700, marginBottom: 14 }}>
          Project location and name
        </div>

        {step === 'choose' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
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
            <button
              onClick={() => {
                setSourceMode('empty');
                setSourcePath('');
                setError('');
                setStep('workspace');
              }}
              style={{ border: `1px solid ${NOLAN_PALETTE.border}`, borderRadius: 8, background: NOLAN_PALETTE.bgDim, color: NOLAN_PALETTE.text, padding: '16px 10px', cursor: 'pointer' }}
            >
              <div style={{ fontSize: 20, fontWeight: 700 }}>New Project</div>
              <div style={{ fontSize: 11, color: NOLAN_PALETTE.textMuted, marginTop: 6 }}>Start from empty workspace</div>
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
              placeholder={suggestedWorkspace || '/tmp/playgrounds/name_project'}
              style={{ width: '100%', boxSizing: 'border-box', borderRadius: 6, border: `1px solid ${NOLAN_PALETTE.border}`, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.text, padding: '9px 10px', fontFamily: 'monospace', fontSize: 12 }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button onClick={() => { void pickWorkspace(); }} style={{ flex: 1, borderRadius: 6, border: `1px solid ${NOLAN_PALETTE.border}`, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.textMuted, padding: '9px 10px', cursor: 'pointer' }}>Choose Folder</button>
              <button onClick={() => setStep(sourceMode === 'empty' ? 'choose' : 'source_input')} style={{ flex: 1, borderRadius: 6, border: `1px solid ${NOLAN_PALETTE.border}`, background: NOLAN_PALETTE.bg, color: NOLAN_PALETTE.textMuted, padding: '9px 10px', cursor: 'pointer' }}>Back</button>
              <button onClick={() => { void submit(); }} disabled={!workspacePath.trim() || step === 'creating'} style={{ flex: 2, borderRadius: 6, border: `1px solid ${workspacePath.trim() ? NOLAN_PALETTE.borderLight : NOLAN_PALETTE.border}`, background: workspacePath.trim() ? NOLAN_PALETTE.bgDim : NOLAN_PALETTE.bg, color: workspacePath.trim() ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim, padding: '9px 10px', cursor: workspacePath.trim() ? 'pointer' : 'not-allowed' }}>{step === 'creating' ? 'Creating...' : 'Create Tab Project'}</button>
            </div>
            {error && (
              <div style={{ marginTop: 10, border: `1px solid ${NOLAN_PALETTE.border}`, borderRadius: 6, background: NOLAN_PALETTE.bg, color: '#ff6b6b', padding: '8px 10px', fontSize: 10 }}>
                <div>{error}</div>
                <button
                  type="button"
                  onClick={() => {
                    // MARKER_176.18: Retry clears error and returns to editable workspace state.
                    setError('');
                    setStep('workspace');
                  }}
                  style={{
                    marginTop: 8,
                    borderRadius: 4,
                    border: `1px solid ${NOLAN_PALETTE.border}`,
                    background: NOLAN_PALETTE.bgDim,
                    color: NOLAN_PALETTE.text,
                    padding: '4px 8px',
                    cursor: 'pointer',
                    fontFamily: 'monospace',
                    fontSize: 9,
                  }}
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
