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
import { useMemo, useEffect, useRef, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';
import { useCutHotkeys, type CutHotkeyHandlers } from '../../hooks/useCutHotkeys';
import { useCutAutosave } from '../../hooks/useCutAutosave';
import { useThreePointEdit } from '../../hooks/useThreePointEdit';
import DockviewLayout from './DockviewLayout';
import MenuBar from './MenuBar';
import ProjectSettings from './ProjectSettings';
import ExportDialog from './ExportDialog';
import SpeedControl from './SpeedControl';
import SaveIndicator from './SaveIndicator';
import DebugShellPanel from './DebugShellPanel';


// ─── Styles ───

const ROOT: CSSProperties = {
  width: '100%',
  height: '100vh',
  background: '#0D0D0D',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
};

// ─── MARKER_W3.3: Collect all edit points (clip boundaries) from unlocked tracks ───

function collectEditPoints(
  lanes: { lane_id: string; clips: { start_sec: number; duration_sec: number }[] }[],
  lockedLanes: Set<string>,
): number[] {
  const pts = new Set<number>();
  for (const lane of lanes) {
    if (lockedLanes.has(lane.lane_id)) continue;
    for (const clip of lane.clips) {
      pts.add(clip.start_sec);
      pts.add(clip.start_sec + clip.duration_sec);
    }
  }
  return [...pts].sort((a, b) => a - b);
}

// ─── Component ───

// MARKER_B11: Speed/Duration modal overlay
function SpeedControlModal() {
  const show = useCutEditorStore((s) => s.showSpeedControl);
  if (!show) return null;
  const close = () => useCutEditorStore.getState().setShowSpeedControl(false);
  return (
    <div data-testid="speed-control-overlay" role="dialog" style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.5)' }}
         onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div data-testid="speed-control">
        <SpeedControl onClose={close} />
      </div>
    </div>
  );
}

interface CutEditorLayoutV2Props {
  /** Script text for ScriptPanel and BPMTrack */
  scriptText?: string;
}

export default function CutEditorLayoutV2({ scriptText = '' }: CutEditorLayoutV2Props) {
  // ─── MARKER_W4.3: Autosave + manual save ───
  const { saveProject } = useCutAutosave();

  // ─── MARKER_W5.3PT: Three-Point Editing (FCP7 Ch.36) ───
  const { insertEdit: threePointInsert, overwriteEdit: threePointOverwrite } = useThreePointEdit();

  // ─── MARKER_A2.6: Smooth zoom animation (150ms ease-out) ───
  const smoothZoomTo = useCallback((s: ReturnType<typeof useCutEditorStore.getState>, targetZoom: number, targetScroll: number) => {
    const startZoom = s.zoom;
    const startScroll = s.scrollLeft;
    const duration = 150; // ms
    const startTime = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - startTime) / duration);
      const ease = 1 - Math.pow(1 - t, 3); // ease-out cubic
      useCutEditorStore.getState().setZoom(startZoom + (targetZoom - startZoom) * ease);
      useCutEditorStore.getState().setScrollLeft(startScroll + (targetScroll - startScroll) * ease);
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, []);

  // MARKER_JKL-KJ-KL: Track K key held state for K+J/K+L frame stepping
  const kHeldRef = useRef(false);
  useEffect(() => {
    const onDown = (e: KeyboardEvent) => { if (e.key === 'k' && !e.metaKey && !e.ctrlKey) kHeldRef.current = true; };
    const onUp = (e: KeyboardEvent) => { if (e.key === 'k') kHeldRef.current = false; };
    window.addEventListener('keydown', onDown);
    window.addEventListener('keyup', onUp);
    return () => { window.removeEventListener('keydown', onDown); window.removeEventListener('keyup', onUp); };
  }, []);

  // ─── MARKER_196.1: Hotkey handlers ───
  const hotkeyHandlers = useMemo<CutHotkeyHandlers>(() => ({
    // Playback
    playPause: () => useCutEditorStore.getState().togglePlay(),
    stop: () => { useCutEditorStore.getState().pause(); useCutEditorStore.getState().setShuttleSpeed(0); },
    // MARKER_W6.JKL: Progressive shuttle (FCP7 Ch.8 / App A)
    // J: reverse ramp 1x→2x→4x→8x. If playing forward, first press stops.
    // L: forward ramp 1x→2x→4x→8x. If playing reverse, first press stops.
    // K: stop (pause + reset shuttle)
    // K+J: frame step backward. K+L: frame step forward.
    shuttleBack: () => {
      // MARKER_JKL-KJ-KL: K+J = single frame backward
      if (kHeldRef.current) {
        const s = useCutEditorStore.getState();
        s.pause();
        s.setShuttleSpeed(0);
        s.seek(Math.max(0, s.currentTime - 1 / s.projectFramerate));
        return;
      }
      const s = useCutEditorStore.getState();
      const cur = s.shuttleSpeed;
      if (cur > 0) {
        s.setShuttleSpeed(0);
        s.pause();
      } else {
        const REVERSE_STEPS = [0, -1, -2, -4, -8];
        const idx = REVERSE_STEPS.indexOf(cur);
        const next = idx >= 0 && idx < REVERSE_STEPS.length - 1 ? REVERSE_STEPS[idx + 1] : -8;
        s.setShuttleSpeed(next);
        s.play();
      }
    },
    shuttleForward: () => {
      // MARKER_JKL-KJ-KL: K+L = single frame forward
      if (kHeldRef.current) {
        const s = useCutEditorStore.getState();
        s.pause();
        s.setShuttleSpeed(0);
        s.seek(Math.min(s.duration, s.currentTime + 1 / s.projectFramerate));
        return;
      }
      const s = useCutEditorStore.getState();
      const cur = s.shuttleSpeed;
      if (cur < 0) {
        s.setShuttleSpeed(0);
        s.pause();
      } else {
        const FORWARD_STEPS = [0, 1, 2, 4, 8];
        const idx = FORWARD_STEPS.indexOf(cur);
        const next = idx >= 0 && idx < FORWARD_STEPS.length - 1 ? FORWARD_STEPS[idx + 1] : 8;
        s.setShuttleSpeed(next);
        s.play();
      }
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
    // MARKER_W6.WIRE: Cycle playback rate (1x → 2x → 0.5x → 1x)
    cyclePlaybackRate: () => {
      const s = useCutEditorStore.getState();
      const RATES = [0.5, 1, 2, 4];
      const idx = RATES.indexOf(s.playbackRate);
      const next = RATES[(idx + 1) % RATES.length];
      s.setPlaybackRate(next);
    },

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

    // MARKER_W6.WIRE: Undo/Redo via backend API
    undo: async () => {
      const s = useCutEditorStore.getState();
      if (!s.sandboxRoot || !s.projectId) return;
      await fetch(`${API_BASE}/cut/undo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sandbox_root: s.sandboxRoot, project_id: s.projectId, timeline_id: s.timelineId || 'main' }),
      });
      await s.refreshProjectState?.();
    },
    redo: async () => {
      const s = useCutEditorStore.getState();
      if (!s.sandboxRoot || !s.projectId) return;
      await fetch(`${API_BASE}/cut/redo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sandbox_root: s.sandboxRoot, project_id: s.projectId, timeline_id: s.timelineId || 'main' }),
      });
      await s.refreshProjectState?.();
    },

    // Editing
    selectAll: () => useCutEditorStore.getState().selectAllClips(),

    // MARKER_CLIPBOARD: Clipboard operations
    copy: () => useCutEditorStore.getState().copyClips(),
    cut: () => useCutEditorStore.getState().cutClips(),
    paste: () => useCutEditorStore.getState().pasteClips('overwrite'),
    pasteInsert: () => useCutEditorStore.getState().pasteClips('insert'),

    // MARKER_UNDO-FIX: All editing ops route through applyTimelineOps for undo support
    deleteClip: async () => {
      const s = useCutEditorStore.getState();
      if (!s.selectedClipId) return;
      await s.applyTimelineOps([{ op: 'remove_clip', clip_id: s.selectedClipId }]);
      s.setSelectedClip(null);
    },
    splitClip: async () => {
      const s = useCutEditorStore.getState();
      const t = s.currentTime;
      // Find clip under playhead to get its clip_id
      for (const lane of s.lanes) {
        for (const c of lane.clips) {
          if (t > c.start_sec && t < c.start_sec + c.duration_sec) {
            await s.applyTimelineOps([{ op: 'split_at', clip_id: c.clip_id, split_sec: t }]);
            return;
          }
        }
      }
    },

    // MARKER_W6.WIRE: Ripple Delete — remove clip and close gap
    rippleDelete: async () => {
      const s = useCutEditorStore.getState();
      if (!s.selectedClipId) return;
      await s.applyTimelineOps([{ op: 'ripple_delete', clip_id: s.selectedClipId }]);
      s.setSelectedClip(null);
    },

    // MARKER_W6.WIRE: Nudge clip ±1 frame
    nudgeLeft: async () => {
      const s = useCutEditorStore.getState();
      if (!s.selectedClipId) return;
      const frameSec = 1 / s.projectFramerate;
      // Find clip to get its current position and lane
      for (const lane of s.lanes) {
        const clip = lane.clips.find((c) => c.clip_id === s.selectedClipId);
        if (clip) {
          await s.applyTimelineOps([{
            op: 'move_clip', clip_id: clip.clip_id,
            lane_id: lane.lane_id, start_sec: Math.max(0, clip.start_sec - frameSec),
          }]);
          return;
        }
      }
    },
    nudgeRight: async () => {
      const s = useCutEditorStore.getState();
      if (!s.selectedClipId) return;
      const frameSec = 1 / s.projectFramerate;
      for (const lane of s.lanes) {
        const clip = lane.clips.find((c) => c.clip_id === s.selectedClipId);
        if (clip) {
          await s.applyTimelineOps([{
            op: 'move_clip', clip_id: clip.clip_id,
            lane_id: lane.lane_id, start_sec: clip.start_sec + frameSec,
          }]);
          return;
        }
      }
    },

    // MARKER_W5.3PT: Three-Point Editing (FCP7 Ch.36)
    // Comma (,) = Insert (ripple). Period (.) = Overwrite (replace).
    // Tries backend via useThreePointEdit; falls back to local-first insert.
    insertEdit: async () => {
      const ok = await threePointInsert();
      if (!ok) {
        // MARKER_TDD-3PT1: Local-first fallback when backend unavailable
        const s = useCutEditorStore.getState();
        const srcIn = s.sourceMarkIn ?? 0;
        const srcOut = s.sourceMarkOut ?? srcIn + 2;
        const dur = srcOut - srcIn;
        if (dur <= 0) return;
        const { videoLaneId } = s.getInsertTargets();
        if (!videoLaneId) return;
        // Find source media — use sourceMediaPath or clip under playhead
        let srcPath = s.sourceMediaPath;
        if (!srcPath) {
          for (const lane of s.lanes) {
            const c = lane.clips.find((cl) => s.currentTime >= cl.start_sec && s.currentTime < cl.start_sec + cl.duration_sec);
            if (c) { srcPath = c.source_path; break; }
          }
        }
        if (!srcPath) return;
        const seqIn = s.sequenceMarkIn ?? s.currentTime;
        const newClipId = `clip_3pt_${Date.now()}`;
        const newLanes = s.lanes.map((lane) => {
          if (lane.lane_id !== videoLaneId) return lane;
          // Ripple: push subsequent clips right
          const shifted = lane.clips.map((c) =>
            c.start_sec >= seqIn ? { ...c, start_sec: c.start_sec + dur } : c
          );
          shifted.push({ clip_id: newClipId, source_path: srcPath!, start_sec: seqIn, duration_sec: dur, source_in: srcIn } as any);
          shifted.sort((a, b) => a.start_sec - b.start_sec);
          return { ...lane, clips: shifted };
        });
        s.setLanes(newLanes);
        s.seek(seqIn + dur);
      }
    },
    overwriteEdit: async () => {
      const ok = await threePointOverwrite();
      if (!ok) {
        // MARKER_TDD-3PT2: Local-first fallback for overwrite
        const s = useCutEditorStore.getState();
        const srcIn = s.sourceMarkIn ?? 0;
        const srcOut = s.sourceMarkOut ?? srcIn + 2;
        const dur = srcOut - srcIn;
        if (dur <= 0) return;
        const { videoLaneId } = s.getInsertTargets();
        if (!videoLaneId) return;
        let srcPath = s.sourceMediaPath;
        if (!srcPath) {
          for (const lane of s.lanes) {
            const c = lane.clips.find((cl) => s.currentTime >= cl.start_sec && s.currentTime < cl.start_sec + cl.duration_sec);
            if (c) { srcPath = c.source_path; break; }
          }
        }
        if (!srcPath) return;
        const seqIn = s.sequenceMarkIn ?? s.currentTime;
        const newClipId = `clip_3pt_${Date.now()}`;
        const newLanes = s.lanes.map((lane) => {
          if (lane.lane_id !== videoLaneId) return lane;
          const clips = [...lane.clips, { clip_id: newClipId, source_path: srcPath!, start_sec: seqIn, duration_sec: dur, source_in: srcIn } as any];
          clips.sort((a, b) => a.start_sec - b.start_sec);
          return { ...lane, clips };
        });
        s.setLanes(newLanes);
        s.seek(seqIn + dur);
      }
    },
    // MARKER_FCP7.F11: Replace Edit — replace clip at playhead with source content
    // FCP7 Ch.36: F11 replaces clip at playhead position, keeping same duration
    // MARKER_UNDO-FIX: Routes through applyTimelineOps for undo support
    replaceEdit: async () => {
      const s = useCutEditorStore.getState();
      const sourcePath = s.sourceMediaPath;
      if (!sourcePath) return;
      // Find clip under playhead
      for (const lane of s.lanes) {
        for (const clip of lane.clips) {
          if (s.currentTime >= clip.start_sec && s.currentTime < clip.start_sec + clip.duration_sec) {
            await s.applyTimelineOps([{
              op: 'replace_media', clip_id: clip.clip_id,
              source_path: sourcePath, source_in: s.sourceMarkIn ?? 0,
            }]);
            return;
          }
        }
      }
    },

    // MARKER_MARK-MENU: Mark Clip (X) — set In/Out to selected clip boundaries
    markClip: () => {
      const s = useCutEditorStore.getState();
      if (!s.selectedClipId) return;
      for (const lane of s.lanes) {
        const clip = lane.clips.find((c) => c.clip_id === s.selectedClipId);
        if (clip) {
          s.setMarkIn(clip.start_sec);
          s.setMarkOut(clip.start_sec + clip.duration_sec);
          return;
        }
      }
    },

    // MARKER_MARK-MENU: Play In to Out
    playInToOut: () => {
      const s = useCutEditorStore.getState();
      const inPt = s.focusedPanel === 'source' ? s.sourceMarkIn : s.sequenceMarkIn;
      const outPt = s.focusedPanel === 'source' ? s.sourceMarkOut : s.sequenceMarkOut;
      if (inPt == null || outPt == null || outPt <= inPt) return;
      s.seek(inPt);
      s.play();
      // Auto-stop at out point via interval
      const stopCheck = setInterval(() => {
        const cur = useCutEditorStore.getState().currentTime;
        if (cur >= outPt) {
          useCutEditorStore.getState().pause();
          clearInterval(stopCheck);
        }
      }, 50);
      // Safety: clear after 5 minutes max
      setTimeout(() => clearInterval(stopCheck), 300000);
    },

    // MARKER_W6.WIRE: Add Marker (M) — create favorite marker at playhead
    addMarker: async () => {
      const s = useCutEditorStore.getState();
      if (!s.sandboxRoot || !s.projectId) return;
      // Find clip at playhead for media_path
      let mediaPath = s.sourceMediaPath || '';
      for (const lane of s.lanes) {
        for (const clip of lane.clips) {
          if (s.currentTime >= clip.start_sec && s.currentTime < clip.start_sec + clip.duration_sec) {
            mediaPath = clip.source_path;
            break;
          }
        }
        if (mediaPath) break;
      }
      if (!mediaPath) return;
      await fetch(`${API_BASE}/cut/time-markers/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: s.sandboxRoot, project_id: s.projectId, timeline_id: s.timelineId || 'main',
          media_path: mediaPath, kind: 'favorite', start_sec: s.currentTime, end_sec: s.currentTime + 0.04,
          score: 1.0, text: '',
        }),
      });
      await s.refreshProjectState?.();
    },
    // MARKER_W6.WIRE: Add Comment Marker (Shift+M)
    addComment: async () => {
      const s = useCutEditorStore.getState();
      if (!s.sandboxRoot || !s.projectId) return;
      let mediaPath = s.sourceMediaPath || '';
      for (const lane of s.lanes) {
        for (const clip of lane.clips) {
          if (s.currentTime >= clip.start_sec && s.currentTime < clip.start_sec + clip.duration_sec) {
            mediaPath = clip.source_path;
            break;
          }
        }
        if (mediaPath) break;
      }
      if (!mediaPath) return;
      await fetch(`${API_BASE}/cut/time-markers/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: s.sandboxRoot, project_id: s.projectId, timeline_id: s.timelineId || 'main',
          media_path: mediaPath, kind: 'comment', start_sec: s.currentTime, end_sec: s.currentTime + 0.04,
          score: 1.0, text: 'Comment',
        }),
      });
      await s.refreshProjectState?.();
    },

    // MARKER_MARK-MENU: Next/Previous marker navigation
    nextMarker: () => {
      const s = useCutEditorStore.getState();
      const sorted = [...s.markers].sort((a, b) => a.start_sec - b.start_sec);
      const next = sorted.find((m) => m.start_sec > s.currentTime + 0.001);
      if (next) s.seek(next.start_sec);
    },
    prevMarker: () => {
      const s = useCutEditorStore.getState();
      const sorted = [...s.markers].sort((a, b) => b.start_sec - a.start_sec);
      const prev = sorted.find((m) => m.start_sec < s.currentTime - 0.001);
      if (prev) s.seek(prev.start_sec);
    },

    // MARKER_KF67: Keyframe navigation + add (FCP7 Ch.67)
    nextKeyframe: () => {
      const s = useCutEditorStore.getState();
      const times = s.getKeyframeTimes();
      const next = times.find((t) => t > s.currentTime + 0.001);
      if (next !== undefined) s.seek(next);
    },
    prevKeyframe: () => {
      const s = useCutEditorStore.getState();
      const times = s.getKeyframeTimes().reverse();
      const prev = times.find((t) => t < s.currentTime - 0.001);
      if (prev !== undefined) s.seek(prev);
    },
    addKeyframe: () => {
      const s = useCutEditorStore.getState();
      if (!s.selectedClipId) return;
      // Find selected clip to calculate relative time
      for (const lane of s.lanes) {
        const clip = lane.clips.find((c) => c.clip_id === s.selectedClipId);
        if (clip) {
          const relTime = s.currentTime - clip.start_sec;
          if (relTime >= 0 && relTime <= clip.duration_sec) {
            // Add opacity keyframe at current value (default 1.0)
            const currentOpacity = clip.effects?.opacity ?? 1.0;
            s.addKeyframe(clip.clip_id, 'opacity', relTime, currentOpacity);
          }
          return;
        }
      }
    },

    // Navigation — edit points
    prevEditPoint: () => {
      const s = useCutEditorStore.getState();
      const points = collectEditPoints(s.lanes, s.lockedLanes);
      const prev = points.filter((t) => t < s.currentTime - 0.001);
      if (prev.length > 0) s.seek(prev[prev.length - 1]);
    },
    nextEditPoint: () => {
      const s = useCutEditorStore.getState();
      const points = collectEditPoints(s.lanes, s.lockedLanes);
      const next = points.find((t) => t > s.currentTime + 0.001);
      if (next !== undefined) s.seek(next);
    },

    // Track height
    cycleTrackHeight: () => useCutEditorStore.getState().cycleTrackHeights(),

    // Tools
    razorTool: () => useCutEditorStore.getState().setActiveTool('razor'),
    selectTool: () => useCutEditorStore.getState().setActiveTool('selection'),
    // MARKER_W5.TRIM: Trim tool hotkeys — FCP7 cycling (R→ripple→roll, S→slip→slide)
    slipTool: () => {
      const s = useCutEditorStore.getState();
      s.setActiveTool(s.activeTool === 'slip' ? 'slide' : 'slip');
    },
    slideTool: () => useCutEditorStore.getState().setActiveTool('slide'),
    rippleTool: () => {
      const s = useCutEditorStore.getState();
      s.setActiveTool(s.activeTool === 'ripple' ? 'roll' : 'ripple');
    },
    rollTool: () => useCutEditorStore.getState().setActiveTool('roll'),

    // View
    zoomIn: () => { const s = useCutEditorStore.getState(); s.setZoom(Math.min(s.zoom * 1.25, 500)); },
    zoomOut: () => { const s = useCutEditorStore.getState(); s.setZoom(Math.max(s.zoom / 1.25, 10)); },
    // MARKER_A2.5: Zoom to fit / zoom to selection with smooth animation
    zoomToFit: () => {
      const s = useCutEditorStore.getState();
      // If clips are selected, zoom to selection bounds (A2.5)
      const ids = s.selectedClipIds;
      if (ids.size > 0) {
        let minT = Infinity, maxT = -Infinity;
        for (const lane of s.lanes) {
          for (const clip of lane.clips) {
            if (ids.has(clip.clip_id)) {
              minT = Math.min(minT, clip.start_sec);
              maxT = Math.max(maxT, clip.start_sec + clip.duration_sec);
            }
          }
        }
        if (minT < maxT) {
          const selDur = maxT - minT;
          const viewWidth = window.innerWidth - 560;
          const targetZoom = Math.max(10, Math.min(500, viewWidth / (selDur * 1.2))); // 20% padding
          const targetScroll = Math.max(0, minT * targetZoom - viewWidth * 0.1);
          smoothZoomTo(s, targetZoom, targetScroll);
          return;
        }
      }
      // Default: zoom to fit entire timeline
      if (s.duration > 0) {
        const targetZoom = Math.max(10, Math.min(500, (window.innerWidth - 560) / s.duration));
        smoothZoomTo(s, targetZoom, 0);
      }
    },

    // Project
    saveProject: () => saveProject(),
    // MARKER_W6.WIRE: Import Media (Cmd+I) — trigger native file picker
    importMedia: () => {
      // Trigger the file input via dispatching a custom event
      // CutStandalone listens for this and handles the bootstrap flow
      window.dispatchEvent(new CustomEvent('cut:import-media'));
    },
    // MARKER_W6.WIRE: Scene Detect (Cmd+D) — trigger scene detection
    sceneDetect: async () => {
      const s = useCutEditorStore.getState();
      if (!s.sandboxRoot || !s.projectId) return;
      await fetch(`${API_BASE}/cut/scene-detect-and-apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: s.sandboxRoot, project_id: s.projectId, timeline_id: s.timelineId || 'main',
        }),
      });
      await s.refreshProjectState?.();
    },
    toggleLinkedSelection: () => useCutEditorStore.getState().toggleLinkedSelection(),
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

    // MARKER_LAYOUT-3: Panel focus shortcuts (⌘1-5)
    focusSource:  () => useCutEditorStore.getState().setFocusedPanel('source'),
    focusProgram: () => useCutEditorStore.getState().setFocusedPanel('program'),
    focusTimeline:() => useCutEditorStore.getState().setFocusedPanel('timeline'),
    focusProject: () => useCutEditorStore.getState().setFocusedPanel('project'),
    focusEffects: () => useCutEditorStore.getState().setFocusedPanel('effects'),

    // MARKER_W5.MF: Match Frame (F) + Q toggle (FCP7 Ch.50)
    matchFrame: () => {
      const s = useCutEditorStore.getState();
      // Find clip under playhead on any unlocked lane
      for (const lane of s.lanes) {
        if (s.lockedLanes.has(lane.lane_id)) continue;
        for (const clip of lane.clips) {
          if (s.currentTime >= clip.start_sec && s.currentTime < clip.start_sec + clip.duration_sec) {
            const sourceOffset = clip.source_in ?? 0;
            const sourceTime = (s.currentTime - clip.start_sec) + sourceOffset;
            s.setSourceMedia(clip.source_path);
            s.setSourceMarkIn(sourceTime);
            // MARKER_DUAL-VIDEO: Seek source monitor to matched frame
            s.seekSource(sourceTime);
            s.setFocusedPanel('source');
            return;
          }
        }
      }
    },
    toggleSourceProgram: () => {
      const s = useCutEditorStore.getState();
      const current = s.focusedPanel;
      if (current === 'source') {
        s.setFocusedPanel('program');
      } else {
        s.setFocusedPanel('source');
      }
    },

    // MARKER_SEQ-MENU: Sequence operations
    liftClip: () => useCutEditorStore.getState().liftClip(),
    extractClip: () => useCutEditorStore.getState().extractClip(),
    closeGap: () => useCutEditorStore.getState().closeGap(),
    extendEdit: () => useCutEditorStore.getState().extendEdit(),
    // MARKER_SPLIT-EDIT: L-cut / J-cut (FCP7 Ch.41)
    splitEditLCut: () => useCutEditorStore.getState().splitEditLCut(),
    splitEditJCut: () => useCutEditorStore.getState().splitEditJCut(),
    addDefaultTransition: () => useCutEditorStore.getState().addDefaultTransition(),
    // MARKER_FCP7.SPEED: Cmd+J opens speed control dialog (FCP7 Ch.69)
    openSpeedControl: () => useCutEditorStore.getState().setShowSpeedControl(true),
  }), [saveProject, threePointInsert, threePointOverwrite]);

  useCutHotkeys({ handlers: hotkeyHandlers });

  // ─── MARKER_W6.JKL: Shuttle playback loop ───
  // When shuttleSpeed ≠ 0, drive currentTime via rAF at the indicated speed.
  // Speed 1 = normal, 2 = 2x, -1 = reverse, etc.
  // The HTML5 video element only supports forward play at 1x.
  // For |speed| > 1 or reverse, we manually seek rather than relying on video.playbackRate.
  const shuttleSpeed = useCutEditorStore((s) => s.shuttleSpeed);
  const shuttleRafRef = useRef<number>(0);
  const shuttlePrevTimeRef = useRef<number>(0);

  useEffect(() => {
    if (shuttleSpeed === 0) {
      if (shuttleRafRef.current) {
        cancelAnimationFrame(shuttleRafRef.current);
        shuttleRafRef.current = 0;
      }
      return;
    }

    // MARKER_JKL1-FIX: rAF loop for ALL non-zero speeds including 1x.
    // Previously speed=1 was skipped (relied on video element), but that fails
    // when no video is loaded (tests, audio-only clips, proxy not ready).
    shuttlePrevTimeRef.current = performance.now();

    const step = (now: number) => {
      const dt = (now - shuttlePrevTimeRef.current) / 1000; // seconds elapsed
      shuttlePrevTimeRef.current = now;

      const s = useCutEditorStore.getState();
      const newTime = s.currentTime + dt * shuttleSpeed;
      s.seek(Math.max(0, Math.min(newTime, s.duration)));

      shuttleRafRef.current = requestAnimationFrame(step);
    };

    shuttleRafRef.current = requestAnimationFrame(step);

    return () => {
      if (shuttleRafRef.current) {
        cancelAnimationFrame(shuttleRafRef.current);
        shuttleRafRef.current = 0;
      }
    };
  }, [shuttleSpeed]);

  // MARKER_P0.PROGRAM: Derive programMediaPath from topmost clip under playhead
  // Without this, Program Monitor stays empty — setProgramMedia() was never called.
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const lanes = useCutEditorStore((s) => s.lanes);
  const setProgramMedia = useCutEditorStore((s) => s.setProgramMedia);

  useEffect(() => {
    // Scan lanes top-to-bottom (V1 first) for the first clip overlapping currentTime
    for (const lane of lanes) {
      for (const clip of lane.clips) {
        if (currentTime >= clip.start_sec && currentTime < clip.start_sec + clip.duration_sec) {
          setProgramMedia(clip.source_path);
          return;
        }
      }
    }
    // No clip under playhead — clear program monitor
    setProgramMedia(null);
  }, [currentTime, lanes, setProgramMedia]);

  const viewMode = useCutEditorStore((s) => s.viewMode);

  return (
    <div style={ROOT} data-testid="cut-editor-layout">
      <MenuBar />
      {viewMode === 'debug' ? <DebugShellPanel /> : <DockviewLayout scriptText={scriptText} />}
      <ProjectSettings />
      <ExportDialog />
      {/* MARKER_B11: Speed/Duration dialog (⌘R) */}
      <SpeedControlModal />
      <SaveIndicator />
    </div>
  );
}
