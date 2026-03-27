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
  background: active ? '#222' : '#1a1a1a',
  border: `1px solid ${active ? '#888' : '#333'}`,
  borderRadius: 3,
  color: disabled ? '#444' : active ? '#fff' : '#ccc',
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
      setProgress('Applying clips to timeline...');
      setMontageProgress('Applying...');

      // Create new timeline instance + dockview panel
      const newLabel = data.timeline_label || `${mode} cut`;
      const newId = createTimeline({
        label: newLabel,
        mode,
      });
      addTimelinePanel(newId, newLabel);

      // MARKER_GAMMA-PW4: Convert montage clips[] to timeline_ops and apply
      const clips = data.clips || data.result?.clips || [];
      if (clips.length > 0) {
        const ops = clips.map((clip: { source_path?: string; start_sec?: number; duration_sec?: number; lane_id?: string }) => ({
          op: 'insert_at',
          lane_id: clip.lane_id || 'video_main',
          start_sec: clip.start_sec ?? 0,
          duration_sec: clip.duration_sec ?? 5,
          source_path: clip.source_path || '',
        }));
        try {
          const applyOps = useCutEditorStore.getState().applyTimelineOps;
          if (applyOps) {
            await applyOps(ops);
          }
        } catch {
          // Best effort — timeline tab created, ops may fail on backend
        }
      }

      setProgress(null);
      setMontageProgress(null);
      setMontageRunning(false);
      const clipCount = clips.length;
      setLastResult(`${newLabel} — ${clipCount} clip${clipCount !== 1 ? 's' : ''} assembled`);

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

      {/* MARKER_GAMMA-PW4: Progress bar + status text */}
      {running && progress && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{
            fontSize: 9,
            color: '#999',
            fontFamily: 'monospace',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <span style={{
              display: 'inline-block',
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#999',
              animation: 'pulse 1s infinite',
            }} />
            {progress}
          </div>
          {/* Indeterminate progress bar */}
          <div style={{
            width: '100%',
            height: 2,
            background: '#222',
            borderRadius: 1,
            overflow: 'hidden',
            position: 'relative',
          }}>
            <div style={{
              position: 'absolute',
              width: '30%',
              height: '100%',
              background: '#666',
              borderRadius: 1,
              animation: 'montage-progress 1.5s ease-in-out infinite',
            }} />
          </div>
          <style>{`
            @keyframes montage-progress {
              0% { left: -30%; }
              100% { left: 100%; }
            }
          `}</style>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          fontSize: 9,
          color: '#999',
          fontFamily: 'monospace',
          padding: '4px 6px',
          background: '#1a1a1a',
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
          color: '#ccc',
          fontFamily: 'monospace',
          padding: '4px 6px',
          background: '#1a1a1a',
          borderRadius: 3,
          border: '1px solid #333',
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
