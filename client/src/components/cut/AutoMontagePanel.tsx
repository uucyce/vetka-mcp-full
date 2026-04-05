/**
 * MARKER_C14: Auto-Montage Panel — 3 PULSE modes with progress + result.
 *
 * Modes:
 *   - Favorites: assemble from favorite markers (order by time/energy/script)
 *   - Script: match script scenes to available materials
 *   - Music: match materials to music track via Camelot/mood
 *
 * Backend: POST /api/cut/pulse/auto-montage (already working)
 * Result: new timeline created → opens as dockview panel tab
 *
 * @phase 198
 */
import { useState, useCallback } from 'react';
import { API_BASE } from '../../config/api.config';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useTimelineInstanceStore } from '../../store/useTimelineInstanceStore';
import { useDockviewStore } from '../../store/useDockviewStore';

type MontageMode = 'favorites' | 'script' | 'music';

const MODES: { mode: MontageMode; label: string; desc: string }[] = [
  { mode: 'favorites', label: 'Favorites', desc: 'Assemble from marked favorites' },
  { mode: 'script', label: 'Script', desc: 'Match script scenes to materials' },
  { mode: 'music', label: 'Music', desc: 'Match materials to music BPM/key' },
];

const btnStyle = (active: boolean, disabled: boolean): React.CSSProperties => ({
  flex: 1,
  background: active ? '#1a2a1a' : '#1a1a1a',
  border: `1px solid ${active ? '#4a9' : '#333'}`,
  borderRadius: 3,
  color: disabled ? '#444' : active ? '#7ecf7e' : '#ccc',
  fontSize: 10,
  fontFamily: 'system-ui, sans-serif',
  padding: '6px 4px',
  cursor: disabled ? 'not-allowed' : 'pointer',
  textAlign: 'center',
  transition: 'all 0.15s',
});

export default function AutoMontagePanel() {
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const projectId = useCutEditorStore((s) => s.projectId);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const refreshProjectState = useCutEditorStore((s) => s.refreshProjectState);
  const setMontageRunning = useCutEditorStore((s) => s.setMontageRunning);
  const setMontageMode = useCutEditorStore((s) => s.setMontageMode);
  const setMontageProgress = useCutEditorStore((s) => s.setMontageProgress);
  const setMontageError = useCutEditorStore((s) => s.setMontageError);

  const createTimeline = useTimelineInstanceStore((s) => s.createTimeline);
  const addTimelinePanel = useDockviewStore((s) => s.addTimelinePanel);

  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const runMontage = useCallback(async (mode: MontageMode) => {
    if (running || !sandboxRoot) return;

    setRunning(true);
    setError(null);
    setProgress('Starting PULSE analysis...');
    setLastResult(null);
    setMontageRunning(true);
    setMontageMode(mode);
    setMontageProgress('Starting...');

    try {
      const res = await fetch(`${API_BASE}/cut/pulse/auto-montage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          project_name: projectId || 'project',
          sandbox_root: sandboxRoot,
          timeline_id: timelineId || 'main',
          version: Date.now(),
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setProgress(null);
      setMontageProgress(null);
      setMontageRunning(false);

      // Create new timeline instance + dockview panel
      const newLabel = data.timeline_label || `${mode} cut`;
      const newId = createTimeline({
        label: newLabel,
        mode,
      });
      addTimelinePanel(newId, newLabel);
      setLastResult(`Created: ${newLabel}`);

      // Refresh project state to load new timeline data
      if (refreshProjectState) {
        await refreshProjectState();
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      setProgress(null);
      setMontageError(msg);
      setMontageRunning(false);
      setMontageProgress(null);
    } finally {
      setRunning(false);
    }
  }, [running, sandboxRoot, projectId, timelineId, refreshProjectState,
      setMontageRunning, setMontageMode, setMontageProgress, setMontageError,
      createTimeline, addTimelinePanel]);

  const noProject = !sandboxRoot;

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      padding: 8,
      gap: 8,
      background: '#0d0d0d',
      fontFamily: 'system-ui, sans-serif',
    }}>
      {/* Header */}
      <div style={{ fontSize: 10, color: '#888', fontFamily: 'monospace', textTransform: 'uppercase', letterSpacing: 0.5 }}>
        PULSE Auto-Montage
      </div>

      {/* 3 Mode buttons */}
      <div style={{ display: 'flex', gap: 4 }}>
        {MODES.map(({ mode, label, desc }) => (
          <button
            key={mode}
            style={btnStyle(false, running || noProject)}
            disabled={running || noProject}
            onClick={() => runMontage(mode)}
            title={desc}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Progress */}
      {running && progress && (
        <div style={{
          fontSize: 9,
          color: '#4a9eff',
          fontFamily: 'monospace',
          padding: '4px 0',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}>
          <span style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: '#4a9eff',
            animation: 'pulse 1s infinite',
          }} />
          {progress}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          fontSize: 9,
          color: '#e88',
          fontFamily: 'monospace',
          padding: '4px 6px',
          background: '#1a1111',
          borderRadius: 3,
          border: '1px solid #333',
        }}>
          {error}
        </div>
      )}

      {/* Result */}
      {lastResult && !running && (
        <div style={{
          fontSize: 9,
          color: '#7ecf7e',
          fontFamily: 'monospace',
          padding: '4px 6px',
          background: '#111a11',
          borderRadius: 3,
          border: '1px solid #2a3a2a',
        }}>
          {lastResult}
        </div>
      )}

      {/* No project hint */}
      {noProject && (
        <div style={{ fontSize: 9, color: '#444', fontFamily: 'monospace', padding: '8px 0' }}>
          Bootstrap a project to use Auto-Montage
        </div>
      )}

      {/* Info */}
      <div style={{ marginTop: 'auto', fontSize: 8, color: '#333', fontFamily: 'monospace', lineHeight: 1.4 }}>
        Favorites: marker-based assembly{'\n'}
        Script: scene-to-material matching{'\n'}
        Music: BPM + Camelot key alignment
      </div>
    </div>
  );
}
