/**
 * MARKER_196.3: CutEditorLayoutV2 — Dockview-powered NLE layout.
 *
 * Architecture doc: RECON_PANEL_DOCKING_2026-03-19.md
 * Replaces PanelGrid + PanelShell manual layout with dockview drag-to-dock.
 *
 * What changed:
 *   - PanelGrid → DockviewLayout (10 panels, 5-zone drop targets, tab reorder)
 *   - PanelShell title bars → dockview native headers
 *   - Manual tab state (leftTab, analysisTab) → dockview tab groups
 *   - Layout persistence → useDockviewStore (workspace presets)
 *   - Panel focus → dockview onDidActivePanelChange
 *
 * What stays:
 *   - All panel content components unchanged
 *   - useCutHotkeys (MARKER_196.1) — hotkey handlers
 *   - ProjectSettings + ExportDialog modal overlays
 *   - useCutEditorStore — untouched
 */
import { useMemo, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useCutHotkeys, type CutHotkeyHandlers } from '../../hooks/useCutHotkeys';
import { useCutAutosave } from '../../hooks/useCutAutosave';
import DockviewLayout from './DockviewLayout';
import ProjectSettings from './ProjectSettings';
import ExportDialog from './ExportDialog';
import SaveIndicator from './SaveIndicator';

// ─── Styles ───

const ROOT: CSSProperties = {
  width: '100%',
  height: '100vh',
  background: '#0D0D0D',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
};

// ─── Component ───

interface CutEditorLayoutV2Props {
  /** Script text for ScriptPanel and BPMTrack */
  scriptText?: string;
}

export default function CutEditorLayoutV2({ scriptText = '' }: CutEditorLayoutV2Props) {
  // ─── MARKER_W4.3: Autosave + manual save ───
  const { saveProject } = useCutAutosave();

  // ─── MARKER_196.1: Hotkey handlers ───
  const hotkeyHandlers = useMemo<CutHotkeyHandlers>(() => ({
    // Playback
    playPause: () => useCutEditorStore.getState().togglePlay(),
    stop: () => { useCutEditorStore.getState().pause(); useCutEditorStore.getState().setShuttleSpeed(0); },
    shuttleBack: () => {
      const s = useCutEditorStore.getState();
      const cur = s.shuttleSpeed;
      const next = cur > 0 ? 0 : Math.max(cur - 1, -4);
      s.setShuttleSpeed(next);
    },
    shuttleForward: () => {
      const s = useCutEditorStore.getState();
      const cur = s.shuttleSpeed;
      const next = cur < 0 ? 0 : Math.min(cur + 1, 4);
      s.setShuttleSpeed(next);
    },
    frameStepBack: () => {
      const s = useCutEditorStore.getState();
      s.pause();
      s.seek(Math.max(0, s.currentTime - 1 / s.projectFramerate));
    },
    frameStepForward: () => {
      const s = useCutEditorStore.getState();
      s.pause();
      s.seek(Math.min(s.duration, s.currentTime + 1 / s.projectFramerate));
    },
    fiveFrameStepBack: () => {
      const s = useCutEditorStore.getState();
      s.pause();
      s.seek(Math.max(0, s.currentTime - 5 / s.projectFramerate));
    },
    fiveFrameStepForward: () => {
      const s = useCutEditorStore.getState();
      s.pause();
      s.seek(Math.min(s.duration, s.currentTime + 5 / s.projectFramerate));
    },
    goToStart: () => useCutEditorStore.getState().seek(0),
    goToEnd: () => { const s = useCutEditorStore.getState(); s.seek(s.duration); },

    // Marking — context-aware: source panel → source marks, else → sequence marks
    markIn: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkIn(s.currentTime);
      else s.setSequenceMarkIn(s.currentTime);
    },
    markOut: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkOut(s.currentTime);
      else s.setSequenceMarkOut(s.currentTime);
    },
    clearIn: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkIn(null);
      else s.setSequenceMarkIn(null);
    },
    clearOut: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkOut(null);
      else s.setSequenceMarkOut(null);
    },
    clearInOut: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') { s.setSourceMarkIn(null); s.setSourceMarkOut(null); }
      else { s.setSequenceMarkIn(null); s.setSequenceMarkOut(null); }
    },
    goToIn: () => {
      const s = useCutEditorStore.getState();
      const mark = s.focusedPanel === 'source' ? s.sourceMarkIn : s.sequenceMarkIn;
      if (mark !== null) s.seek(mark);
    },
    goToOut: () => {
      const s = useCutEditorStore.getState();
      const mark = s.focusedPanel === 'source' ? s.sourceMarkOut : s.sequenceMarkOut;
      if (mark !== null) s.seek(mark);
    },

    // Editing
    selectAll: () => useCutEditorStore.getState().selectAllClips(),
    deleteClip: () => {
      const s = useCutEditorStore.getState();
      if (s.selectedClipId) {
        const newLanes = s.lanes.map((lane) => ({
          ...lane,
          clips: lane.clips.filter((c) => c.clip_id !== s.selectedClipId),
        }));
        s.setLanes(newLanes);
        s.setSelectedClip(null);
      }
    },
    splitClip: () => {
      const s = useCutEditorStore.getState();
      const t = s.currentTime;
      const newLanes = s.lanes.map((lane) => ({
        ...lane,
        clips: lane.clips.flatMap((c) => {
          if (t > c.start_sec && t < c.start_sec + c.duration_sec) {
            const leftDur = t - c.start_sec;
            const rightDur = c.duration_sec - leftDur;
            return [
              { ...c, duration_sec: leftDur },
              { ...c, clip_id: c.clip_id + '_split', start_sec: t, duration_sec: rightDur },
            ];
          }
          return [c];
        }),
      }));
      s.setLanes(newLanes);
    },

    // Tools
    razorTool: () => useCutEditorStore.getState().setActiveTool('razor'),
    selectTool: () => useCutEditorStore.getState().setActiveTool('selection'),

    // View
    zoomIn: () => { const s = useCutEditorStore.getState(); s.setZoom(Math.min(s.zoom * 1.25, 500)); },
    zoomOut: () => { const s = useCutEditorStore.getState(); s.setZoom(Math.max(s.zoom / 1.25, 10)); },
    zoomToFit: () => {
      const s = useCutEditorStore.getState();
      if (s.duration > 0) {
        s.setZoom(Math.max(10, Math.min(500, (window.innerWidth - 560) / s.duration)));
        s.setScrollLeft(0);
      }
    },

    // Project
    saveProject: () => saveProject(),
    toggleViewMode: () => {
      const s = useCutEditorStore.getState();
      s.setViewMode(s.viewMode === 'nle' ? 'debug' : 'nle');
    },
    escapeContext: () => {
      const s = useCutEditorStore.getState();
      s.clearSelection();
      s.setActiveTool('selection');
      s.setShuttleSpeed(0);
    },
  }), [saveProject]);

  useCutHotkeys({ handlers: hotkeyHandlers });

  return (
    <div style={ROOT}>
      <DockviewLayout scriptText={scriptText} />
      <ProjectSettings />
      <ExportDialog />
      <SaveIndicator />
    </div>
  );
}
