/**
 * @deprecated MARKER_CUT_0.3: Replaced by MonitorTransport.tsx + TimelineToolbar.tsx.
 * MonitorTransport renders under each monitor (Source/Program).
 * TimelineToolbar renders above timeline tracks (snap, zoom only).
 * This file kept for reference — will be removed after full migration.
 *
 * MARKER_170.NLE.TRANSPORT: Transport controls bar for CUT NLE.
 * Play/Pause, timecode display, playback rate, zoom slider.
 * Keyboard shortcuts: Space=play/pause, J/K/L=shuttle, Left/Right=step.
 */
import { useState, useEffect, useCallback, useRef, useMemo, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useCutHotkeys, type CutHotkeyHandlers } from '../../hooks/useCutHotkeys';
import {
  IconSkipStart, IconPlay, IconPause, IconSkipEnd,
  IconExport, IconSpinner, IconCheck,
  IconLayoutNLE, IconWrench, IconScissors,
} from './icons/CutIcons';

const BAR_STYLE: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '4px 12px',
  background: '#0a0a0a',
  borderBottom: '1px solid #222',
  height: 36,
  fontFamily: 'system-ui',
  fontSize: 12,
  color: '#ccc',
  userSelect: 'none',
  flexShrink: 0,
};

const BTN_STYLE: CSSProperties = {
  background: 'none',
  border: '1px solid #333',
  color: '#ccc',
  borderRadius: 3,
  padding: '3px 8px',
  cursor: 'pointer',
  fontSize: 13,
  fontFamily: 'system-ui',
  lineHeight: 1,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  minWidth: 28,
  height: 26,
};

const BTN_ACTIVE: CSSProperties = {
  ...BTN_STYLE,
  background: '#fff',
  color: '#000',
  border: '1px solid #fff',
};

const TC_STYLE: CSSProperties = {
  fontFamily: '"JetBrains Mono", "SF Mono", monospace',
  fontSize: 14,
  color: '#fff',
  letterSpacing: 1,
  minWidth: 100,
  textAlign: 'center',
};

const RATE_STYLE: CSSProperties = {
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: 11,
  color: '#888',
  cursor: 'pointer',
  padding: '2px 6px',
  borderRadius: 3,
  border: '1px solid #222',
};

const ZOOM_STYLE: CSSProperties = {
  width: 80,
  height: 3,
  appearance: 'none' as const,
  background: '#333',
  borderRadius: 2,
  outline: 'none',
  cursor: 'pointer',
};

const SEPARATOR: CSSProperties = {
  width: 1,
  height: 20,
  background: '#333',
  margin: '0 4px',
};

const LABEL_STYLE: CSSProperties = {
  fontSize: 10,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: 1,
};

const UNDO_BADGE_STYLE: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minWidth: 16,
  height: 16,
  padding: '0 4px',
  borderRadius: 999,
  background: '#111',
  color: '#9ca3af',
  border: '1px solid #2a2a2a',
  fontSize: 9,
  lineHeight: 1,
};

const TOAST_STYLE: CSSProperties = {
  position: 'absolute',
  top: 42,
  left: 12,
  zIndex: 20,
  padding: '8px 10px',
  borderRadius: 6,
  background: 'rgba(10,10,10,0.94)',
  border: '1px solid #262626',
  color: '#d1d5db',
  fontSize: 11,
  boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
  pointerEvents: 'none',
  maxWidth: 280,
};

type UndoStackLabel = {
  index?: number;
  label?: string;
  timestamp?: string;
};

type UndoStackInfo = {
  undo_depth: number;
  redo_depth: number;
  can_undo: boolean;
  can_redo: boolean;
  labels: UndoStackLabel[];
};

type ToastState = {
  tone: 'info' | 'success' | 'error';
  text: string;
} | null;

function formatTimecode(seconds: number, fps = 25): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const f = Math.floor((seconds % 1) * fps);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}

const RATES = [0.25, 0.5, 1, 1.5, 2, 4];

export default function TransportBar() {
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  const playbackRate = useCutEditorStore((s) => s.playbackRate);
  const duration = useCutEditorStore((s) => s.duration);
  const markIn = useCutEditorStore((s) => s.markIn);
  const markOut = useCutEditorStore((s) => s.markOut);
  const zoom = useCutEditorStore((s) => s.zoom);
  const viewMode = useCutEditorStore((s) => s.viewMode);
  const sceneGraphSurfaceMode = useCutEditorStore((s) => s.sceneGraphSurfaceMode);
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const projectId = useCutEditorStore((s) => s.projectId);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const refreshProjectState = useCutEditorStore((s) => s.refreshProjectState);
  const lanes = useCutEditorStore((s) => s.lanes);
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const activeMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const togglePlay = useCutEditorStore((s) => s.togglePlay);
  const seek = useCutEditorStore((s) => s.seek);
  const setMarkIn = useCutEditorStore((s) => s.setMarkIn);
  const setMarkOut = useCutEditorStore((s) => s.setMarkOut);
  const setPlaybackRate = useCutEditorStore((s) => s.setPlaybackRate);
  const setZoom = useCutEditorStore((s) => s.setZoom);
  const setViewMode = useCutEditorStore((s) => s.setViewMode);
  const pause = useCutEditorStore((s) => s.pause);
  const [exportStatus, setExportStatus] = useState<'idle' | 'exporting' | 'done' | 'error'>('idle');
  const [exportFormat, setExportFormat] = useState<'premiere' | 'fcpxml'>('premiere');
  const [sceneDetectStatus, setSceneDetectStatus] = useState<'idle' | 'detecting' | 'done' | 'error'>('idle');
  const [undoStack, setUndoStack] = useState<UndoStackInfo>({
    undo_depth: 0,
    redo_depth: 0,
    can_undo: false,
    can_redo: false,
    labels: [],
  });
  const [undoToast, setUndoToast] = useState<ToastState>(null);
  const undoToastTimeoutRef = useRef<number | null>(null);

  const showUndoToast = useCallback((tone: 'info' | 'success' | 'error', text: string) => {
    if (undoToastTimeoutRef.current != null) {
      window.clearTimeout(undoToastTimeoutRef.current);
    }
    setUndoToast({ tone, text });
    undoToastTimeoutRef.current = window.setTimeout(() => {
      setUndoToast(null);
      undoToastTimeoutRef.current = null;
    }, 2200);
  }, []);

  const refreshUndoStack = useCallback(async () => {
    if (!sandboxRoot || !projectId) {
      setUndoStack({
        undo_depth: 0,
        redo_depth: 0,
        can_undo: false,
        can_redo: false,
        labels: [],
      });
      return;
    }
    try {
      const response = await fetch(
        `${API_BASE}/cut/undo-stack?sandbox_root=${encodeURIComponent(sandboxRoot)}&project_id=${encodeURIComponent(projectId)}&timeline_id=${encodeURIComponent(timelineId || 'main')}`
      );
      if (!response.ok) {
        throw new Error(`undo stack failed: HTTP ${response.status}`);
      }
      const payload = (await response.json()) as { success?: boolean } & Partial<UndoStackInfo>;
      if (!payload.success) {
        throw new Error('undo stack request failed');
      }
      setUndoStack({
        undo_depth: Number(payload.undo_depth || 0),
        redo_depth: Number(payload.redo_depth || 0),
        can_undo: Boolean(payload.can_undo),
        can_redo: Boolean(payload.can_redo),
        labels: Array.isArray(payload.labels) ? payload.labels : [],
      });
    } catch (error) {
      console.warn('[CUT] undo stack refresh failed:', error);
    }
  }, [projectId, sandboxRoot, timelineId]);

  useEffect(() => {
    void refreshUndoStack();
  }, [refreshUndoStack]);

  useEffect(() => {
    if (!sandboxRoot || !projectId) return;
    void refreshUndoStack();
  }, [lanes, projectId, refreshUndoStack, sandboxRoot]);

  useEffect(() => {
    return () => {
      if (undoToastTimeoutRef.current != null) {
        window.clearTimeout(undoToastTimeoutRef.current);
      }
    };
  }, []);

  // MARKER_170.NLE.EXPORT_UI: Export timeline to Premiere XML or FCPXML
  const handleExport = useCallback(async () => {
    if (!sandboxRoot) return;
    setExportStatus('exporting');
    const endpoint = exportFormat === 'premiere' ? 'premiere-xml' : 'fcpxml';
    try {
      const res = await fetch(`${API_BASE}/cut/export/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId || '',
          fps: 25,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setExportStatus('done');
        console.info(`[CUT] Exported ${endpoint} → ${data.export_path}`);
        setTimeout(() => setExportStatus('idle'), 3000);
      } else {
        console.warn('[CUT] Export failed:', data.error, data.message);
        setExportStatus('error');
        setTimeout(() => setExportStatus('idle'), 3000);
      }
    } catch (err) {
      console.error('[CUT] Export error:', err);
      setExportStatus('error');
      setTimeout(() => setExportStatus('idle'), 3000);
    }
  }, [sandboxRoot, projectId, exportFormat]);

  const cycleExportFormat = useCallback(() => {
    setExportFormat((f) => (f === 'premiere' ? 'fcpxml' : 'premiere'));
  }, []);

  // MARKER_185.1: Scene Detection — calls POST /cut/scene-detect-and-apply
  const handleSceneDetect = useCallback(async () => {
    if (!sandboxRoot || !projectId) return;
    if (sceneDetectStatus === 'detecting') return; // prevent double-click
    setSceneDetectStatus('detecting');
    showUndoToast('info', 'Detecting scenes…');
    try {
      const res = await fetch(`${API_BASE}/cut/scene-detect-and-apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: timelineId || 'main',
          threshold: 0.3,
          interval_sec: 1.0,
          lane_id: 'scenes',
          update_scene_graph: true,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setSceneDetectStatus('done');
        showUndoToast('success', `${data.boundary_count ?? 0} scene boundaries detected`);
        await refreshProjectState?.();
        setTimeout(() => setSceneDetectStatus('idle'), 3000);
      } else {
        setSceneDetectStatus('error');
        showUndoToast('error', `Scene detect failed: ${data.error || data.message || 'unknown'}`);
        setTimeout(() => setSceneDetectStatus('idle'), 3000);
      }
    } catch (err) {
      console.error('[CUT] Scene detect error:', err);
      setSceneDetectStatus('error');
      showUndoToast('error', `Scene detect error: ${err instanceof Error ? err.message : 'network'}`);
      setTimeout(() => setSceneDetectStatus('idle'), 3000);
    }
  }, [sandboxRoot, projectId, timelineId, sceneDetectStatus, showUndoToast, refreshProjectState]);

  // Cycle playback rate
  const cycleRate = useCallback(() => {
    const idx = RATES.indexOf(playbackRate);
    const next = idx >= 0 ? RATES[(idx + 1) % RATES.length] : 1;
    setPlaybackRate(next);
  }, [playbackRate, setPlaybackRate]);

  const resolveMarkerMediaPath = useCallback(() => {
    if (selectedClipId) {
      for (const lane of lanes) {
        const clip = lane.clips.find((item) => item.clip_id === selectedClipId);
        if (clip?.source_path) {
          return clip.source_path;
        }
      }
    }
    for (const lane of lanes) {
      const match = lane.clips.find(
        (clip) => currentTime >= clip.start_sec && currentTime <= clip.start_sec + clip.duration_sec
      );
      if (match?.source_path) {
        return match.source_path;
      }
    }
    return activeMediaPath || null;
  }, [activeMediaPath, currentTime, lanes, selectedClipId]);

  const createMarker = useCallback(
    async (kind: 'favorite' | 'comment', text: string) => {
      if (!sandboxRoot || !projectId) return;
      const mediaPath = resolveMarkerMediaPath();
      if (!mediaPath) return;
      const endSec = Math.min(duration || currentTime + 1, currentTime + 1);
      const response = await fetch(`${API_BASE}/cut/time-markers/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: timelineId || 'main',
          author: 'cut_transport',
          op: 'create',
          media_path: mediaPath,
          kind,
          start_sec: currentTime,
          end_sec: Math.max(currentTime, endSec),
          anchor_sec: currentTime,
          score: kind === 'favorite' ? 1.0 : 0.7,
          text,
          source_engine: 'cut_transport',
        }),
      });
      if (!response.ok) {
        throw new Error(`marker create failed: HTTP ${response.status}`);
      }
      const payload = (await response.json()) as { success?: boolean; error?: { message?: string } };
      if (!payload.success) {
        throw new Error(payload.error?.message || 'marker create failed');
      }
      await refreshProjectState?.();
    },
    [currentTime, duration, projectId, refreshProjectState, resolveMarkerMediaPath, sandboxRoot, timelineId]
  );

  const removeSelectedClip = useCallback(async () => {
    if (!sandboxRoot || !projectId || !selectedClipId) return;
    const response = await fetch(`${API_BASE}/cut/timeline/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sandbox_root: sandboxRoot,
        project_id: projectId,
        timeline_id: timelineId || 'main',
        author: 'cut_transport',
        ops: [{ op: 'remove_clip', clip_id: selectedClipId }],
      }),
    });
    if (!response.ok) {
      throw new Error(`remove clip failed: HTTP ${response.status}`);
    }
    const payload = (await response.json()) as { success?: boolean; error?: { message?: string } };
    if (!payload.success) {
      throw new Error(payload.error?.message || 'remove clip failed');
    }
    await refreshProjectState?.();
  }, [projectId, refreshProjectState, sandboxRoot, selectedClipId, timelineId]);

  // MARKER_W3.1: Split clip at playhead position
  const splitAtPlayhead = useCallback(async () => {
    if (!sandboxRoot || !projectId) return;
    const response = await fetch(`${API_BASE}/cut/timeline/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sandbox_root: sandboxRoot,
        project_id: projectId,
        timeline_id: timelineId || 'main',
        author: 'cut_transport',
        ops: [{ op: 'split_clip', time: currentTime }],
      }),
    });
    if (response.ok) {
      const payload = (await response.json()) as { success?: boolean };
      if (payload.success) await refreshProjectState?.();
    }
  }, [currentTime, projectId, refreshProjectState, sandboxRoot, timelineId]);

  // MARKER_W3.1: Ripple delete — remove selected clip and close the gap
  const rippleDeleteClip = useCallback(async () => {
    if (!sandboxRoot || !projectId || !selectedClipId) return;
    const response = await fetch(`${API_BASE}/cut/timeline/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sandbox_root: sandboxRoot,
        project_id: projectId,
        timeline_id: timelineId || 'main',
        author: 'cut_transport',
        ops: [{ op: 'ripple_delete', clip_id: selectedClipId }],
      }),
    });
    if (response.ok) {
      const payload = (await response.json()) as { success?: boolean };
      if (payload.success) await refreshProjectState?.();
    }
  }, [projectId, refreshProjectState, sandboxRoot, selectedClipId, timelineId]);

  const runUndoAction = useCallback(
    async (mode: 'undo' | 'redo') => {
      if (!sandboxRoot || !projectId) return;
      const response = await fetch(`${API_BASE}/cut/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: timelineId || 'main',
        }),
      });
      if (!response.ok) {
        throw new Error(`${mode} failed: HTTP ${response.status}`);
      }
      const payload = (await response.json()) as {
        success?: boolean;
        error?: string;
        undo_depth?: number;
        redo_depth?: number;
        undone_label?: string;
        redone_label?: string;
      };
      if (!payload.success) {
        const knownError = payload.error === 'nothing_to_undo' || payload.error === 'nothing_to_redo';
        showUndoToast(knownError ? 'info' : 'error', knownError ? (payload.error || '').split('_').join(' ') : payload.error || `${mode} failed`);
        return;
      }
      await refreshProjectState?.();
      await refreshUndoStack();
      if (mode === 'undo') {
        showUndoToast('success', `Undo: ${payload.undone_label || 'timeline edit'}`);
      } else {
        showUndoToast('success', `Redo: ${payload.redone_label || 'timeline edit'}`);
      }
    },
    [projectId, refreshProjectState, refreshUndoStack, sandboxRoot, showUndoToast, timelineId]
  );

  // MARKER_185.7: Centralized hotkey registry (Premiere / FCP7 / Custom presets)
  const hotkeyHandlers: CutHotkeyHandlers = useMemo(() => ({
    playPause:        () => togglePlay(),
    // MARKER_W3.4: JKL Progressive Shuttle
    // K = pause + reset shuttle. J = reverse (progressive). L = forward (progressive).
    stop:             () => { pause(); useCutEditorStore.getState().setShuttleSpeed(0); },
    shuttleBack:      () => {
      const s = useCutEditorStore.getState().shuttleSpeed;
      const next = s > 0 ? -1 : s === 0 ? -1 : Math.max(-8, s * 2);
      useCutEditorStore.getState().setShuttleSpeed(next);
      useCutEditorStore.getState().setPlaybackRate(Math.abs(next));
      if (next < 0) {
        // Reverse: simulate by stepping backward via rAF
        pause();
      } else {
        play();
      }
    },
    shuttleForward:   () => {
      const s = useCutEditorStore.getState().shuttleSpeed;
      const next = s < 0 ? 1 : s === 0 ? 1 : Math.min(8, s * 2);
      useCutEditorStore.getState().setShuttleSpeed(next);
      useCutEditorStore.getState().setPlaybackRate(Math.abs(next));
      play();
    },
    frameStepBack:    () => { pause(); seek(Math.max(0, currentTime - 1 / 25)); },
    frameStepForward: () => { pause(); seek(Math.min(duration, currentTime + 1 / 25)); },
    // MARKER_W3.5: 5-frame step (Shift+Arrow)
    fiveFrameStepBack:    () => { pause(); seek(Math.max(0, currentTime - 5 / 25)); },
    fiveFrameStepForward: () => { pause(); seek(Math.min(duration, currentTime + 5 / 25)); },
    goToStart:        () => seek(0),
    goToEnd:          () => seek(duration),
    cyclePlaybackRate: () => cycleRate(),
    markIn:           () => setMarkIn(currentTime),
    markOut:          () => setMarkOut(currentTime),
    // MARKER_W3.5: Clear and Go to marks
    clearIn:          () => setMarkIn(null),
    clearOut:         () => setMarkOut(null),
    clearInOut:       () => { setMarkIn(null); setMarkOut(null); },
    goToIn:           () => { const m = useCutEditorStore.getState().sourceMarkIn; if (m != null) seek(m); },
    goToOut:          () => { const m = useCutEditorStore.getState().sourceMarkOut; if (m != null) seek(m); },
    undo:             () => runUndoAction('undo'),
    redo:             () => runUndoAction('redo'),
    deleteClip:       () => removeSelectedClip(),
    splitClip:        () => splitAtPlayhead(),
    rippleDelete:     () => rippleDeleteClip(),
    // MARKER_W3.3: Navigate edit points + Zoom to fit
    prevEditPoint:    () => {
      const lanes = useCutEditorStore.getState().lanes;
      const editPoints = new Set<number>();
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          editPoints.add(clip.timeline_in);
          editPoints.add(clip.timeline_in + (clip.duration ?? 0));
        }
      }
      const sorted = [...editPoints].sort((a, b) => a - b);
      const prev = sorted.filter((t) => t < currentTime - 0.01).pop();
      if (prev != null) seek(prev);
    },
    nextEditPoint:    () => {
      const lanes = useCutEditorStore.getState().lanes;
      const editPoints = new Set<number>();
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          editPoints.add(clip.timeline_in);
          editPoints.add(clip.timeline_in + (clip.duration ?? 0));
        }
      }
      const sorted = [...editPoints].sort((a, b) => a - b);
      const next = sorted.find((t) => t > currentTime + 0.01);
      if (next != null) seek(next);
    },
    zoomToFit:        () => {
      const { lanes, duration: dur } = useCutEditorStore.getState();
      if (dur <= 0) return;
      // Estimate visible width (~80% of window minus lane headers)
      const visibleWidth = Math.max(400, window.innerWidth - 200);
      const fitZoom = visibleWidth / dur;
      setZoom(Math.max(10, Math.min(300, fitZoom)));
      useCutEditorStore.getState().setScrollLeft(0);
    },
    addMarker:        () => createMarker('favorite', ''),
    addComment:       async () => {
      const text = window.prompt('Comment marker text', 'CUT note') || '';
      await createMarker('comment', text);
    },
    zoomIn:           () => setZoom(zoom * 1.3),
    zoomOut:          () => setZoom(zoom / 1.3),
    importMedia:      () => window.dispatchEvent(new CustomEvent('cut:trigger-import')),
    sceneDetect:      () => handleSceneDetect(),
    // MARKER_W3.6: Tool State Machine hotkeys
    selectTool:       () => useCutEditorStore.getState().setActiveTool('selection'),
    razorTool:        () => useCutEditorStore.getState().setActiveTool('razor'),
    // MARKER_W3.7: Selection hotkeys
    selectAll:        () => useCutEditorStore.getState().selectAllClips(),
    escapeContext:    () => useCutEditorStore.getState().clearSelection(),
    toggleViewMode:   () => setViewMode(viewMode === 'nle' ? 'debug' : 'nle'),
  }), [
    togglePlay, pause, seek, currentTime, duration, cycleRate,
    setMarkIn, setMarkOut, runUndoAction, removeSelectedClip,
    splitAtPlayhead, rippleDeleteClip,
    createMarker, setZoom, zoom, handleSceneDetect, setViewMode, viewMode,
  ]);

  const { labelFor } = useCutHotkeys({ handlers: hotkeyHandlers });

  return (
    <div data-testid="cut-transport-bar" style={{ ...BAR_STYLE, position: 'relative' }}>
      {undoToast && (
        <div
          data-testid="cut-undo-toast"
          style={{
            ...TOAST_STYLE,
            borderColor:
              undoToast.tone === 'success' ? '#14532d' : undoToast.tone === 'error' ? '#7f1d1d' : '#262626',
            color:
              undoToast.tone === 'success' ? '#86efac' : undoToast.tone === 'error' ? '#fca5a5' : '#d1d5db',
          }}
        >
          {undoToast.text}
        </div>
      )}
      {/* Skip to start */}
      <button style={BTN_STYLE} onClick={() => seek(0)} title={`Go to start (${labelFor('goToStart')})`}>
        <IconSkipStart size={14} />
      </button>

      {/* Play/Pause */}
      <button
        style={isPlaying ? BTN_ACTIVE : BTN_STYLE}
        onClick={togglePlay}
        title={`Play/Pause (${labelFor('playPause')})`}
      >
        {isPlaying ? <IconPause size={14} /> : <IconPlay size={14} />}
      </button>

      {/* Skip to end */}
      <button style={BTN_STYLE} onClick={() => seek(duration)} title={`Go to end (${labelFor('goToEnd')})`}>
        <IconSkipEnd size={14} />
      </button>

      <div style={SEPARATOR} />

      {/* Timecode */}
      <div style={TC_STYLE}>{formatTimecode(currentTime)}</div>

      <div style={SEPARATOR} />

      {/* Duration */}
      <span style={{ ...LABEL_STYLE, marginRight: 2 }}>DUR</span>
      <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, color: '#666' }}>
        {formatTimecode(duration)}
      </span>

      <div style={SEPARATOR} />

      <span style={{ ...LABEL_STYLE, marginRight: 2 }}>IN</span>
      <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, color: markIn == null ? '#444' : '#22c55e' }}>
        {markIn == null ? '--:--:--:--' : formatTimecode(markIn)}
      </span>

      <span style={{ ...LABEL_STYLE, marginLeft: 8, marginRight: 2 }}>OUT</span>
      <span style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, color: markOut == null ? '#444' : '#ef4444' }}>
        {markOut == null ? '--:--:--:--' : formatTimecode(markOut)}
      </span>

      <div style={SEPARATOR} />

      {/* Playback rate */}
      <span
        style={RATE_STYLE}
        onClick={cycleRate}
        title="Cycle playback speed"
      >
        {playbackRate}x
      </span>

      <div style={SEPARATOR} />

      <button
        data-testid="cut-undo-button"
        style={undoStack.can_undo ? BTN_STYLE : { ...BTN_STYLE, opacity: 0.35, cursor: 'default' }}
        onClick={() => void runUndoAction('undo')}
        disabled={!undoStack.can_undo}
        title={
          undoStack.can_undo
            ? `Undo ${undoStack.labels[0]?.label || 'edit'} (${labelFor('undo')})`
            : 'Nothing to undo'
        }
      >
        ↶
        <span style={UNDO_BADGE_STYLE}>{undoStack.undo_depth}</span>
      </button>

      <button
        data-testid="cut-redo-button"
        style={undoStack.can_redo ? BTN_STYLE : { ...BTN_STYLE, opacity: 0.35, cursor: 'default' }}
        onClick={() => void runUndoAction('redo')}
        disabled={!undoStack.can_redo}
        title={undoStack.can_redo ? `Redo last undone edit (${labelFor('redo')})` : 'Nothing to redo'}
      >
        ↷
        <span style={UNDO_BADGE_STYLE}>{undoStack.redo_depth}</span>
      </button>

      <div style={SEPARATOR} />

      {/* MARKER_185.1: Scene Detection button */}
      <button
        data-testid="cut-scene-detect-button"
        style={{
          ...BTN_STYLE,
          opacity: sandboxRoot && projectId ? 1 : 0.3,
          color: sceneDetectStatus === 'done' ? '#22c55e' : sceneDetectStatus === 'error' ? '#ef4444' : '#ccc',
        }}
        onClick={() => void handleSceneDetect()}
        disabled={!sandboxRoot || !projectId || sceneDetectStatus === 'detecting'}
        title={`Detect Scenes (${labelFor('sceneDetect')})`}
      >
        {sceneDetectStatus === 'detecting' ? <IconSpinner size={14} /> : <IconScissors size={14} />}
        <span style={{ marginLeft: 4, fontSize: 10 }}>Scenes</span>
      </button>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Zoom */}
      <span style={LABEL_STYLE}>ZOOM</span>
      <input
        type="range"
        min={10}
        max={300}
        value={zoom}
        onChange={(e) => setZoom(Number(e.target.value))}
        style={ZOOM_STYLE}
        title={`${zoom.toFixed(0)}px/sec`}
      />

      <div style={SEPARATOR} />

      {/* Export format selector */}
      <span
        style={{ ...RATE_STYLE, fontSize: 9, cursor: 'pointer' }}
        onClick={cycleExportFormat}
        title="Click to switch export format"
      >
        {exportFormat === 'premiere' ? 'PPro' : 'FCP/DR'}
      </span>

      {/* Export button */}
      <button
        style={{
          ...BTN_STYLE,
          opacity: sandboxRoot ? 1 : 0.3,
          color: exportStatus === 'done' ? '#22c55e' : exportStatus === 'error' ? '#ef4444' : '#ccc',
        }}
        onClick={handleExport}
        disabled={!sandboxRoot || exportStatus === 'exporting'}
        title={`Export to ${exportFormat === 'premiere' ? 'Premiere Pro XML' : 'FCPXML (FCP/DaVinci)'}`}
      >
        {exportStatus === 'exporting' ? <IconSpinner size={14} /> : exportStatus === 'done' ? <IconCheck size={14} /> : <IconExport size={14} />}
      </button>

      <div style={SEPARATOR} />

      {sceneGraphSurfaceMode === 'nle_ready' && (
        <>
          <div style={SEPARATOR} />
          <span style={{ ...BTN_ACTIVE, cursor: 'default' }} title="Scene Graph peer-pane state is ready for NLE promotion">
            Graph Ready
          </span>
        </>
      )}

      {/* View mode toggle */}
      <button
        style={viewMode === 'nle' ? BTN_ACTIVE : BTN_STYLE}
        onClick={() => setViewMode(viewMode === 'nle' ? 'debug' : 'nle')}
        title="Toggle NLE / Debug view"
      >
        {viewMode === 'nle' ? <IconLayoutNLE size={14} /> : <IconWrench size={14} />}
      </button>
    </div>
  );
}
