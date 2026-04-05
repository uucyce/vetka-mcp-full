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
import { useSelectionStore } from '../../store/useSelectionStore';
import { API_BASE } from '../../config/api.config';
import { useCutHotkeys, type CutHotkeyHandlers } from '../../hooks/useCutHotkeys';
import { useOverlayEscapeClose } from '../../hooks/useOverlayEscapeClose';
import { useCutAutosave } from '../../hooks/useCutAutosave';
import { useThreePointEdit } from '../../hooks/useThreePointEdit';
import { useAudioPlayback, type AudioClipInfo } from '../../hooks/useAudioPlayback';
import DockviewLayout from './DockviewLayout';
import { useDockviewStore } from '../../store/useDockviewStore';
import MenuBar from './MenuBar';
import ProjectSettings from './ProjectSettings';
import ExportDialog from './ExportDialog';
import SpeedControl from './SpeedControl';
import FindDialog from './FindDialog';
import PasteAttributesDialog from './PasteAttributesDialog';
import SaveIndicator from './SaveIndicator';
import DebugShellPanel from './DebugShellPanel';
import TrimEditWindow from './TrimEditWindow';
import { EditMarkerDialog } from './panels/EditMarkerDialog';
import { TimecodeEntryOverlay } from './panels/TimecodeEntryOverlay';
import { PublishDialog } from '../publish/PublishDialog';
import { useGenerationControlStore } from '../../store/useGenerationControlStore';


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
  // MARKER_GAMMA-ESC-HOOK: Escape closes modal + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);
  return (
    <div data-testid="speed-control-overlay" data-overlay="1" role="dialog" style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.5)' }}
         onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div data-testid="speed-control">
        <SpeedControl onClose={close} />
      </div>
    </div>
  );
}

// MARKER_PASTE_ATTR: Paste Attributes dialog overlay (Alt+V)
function PasteAttributesModal() {
  const show = useCutEditorStore((s) => s.showPasteAttributes);
  if (!show) return null;
  const close = () => useCutEditorStore.getState().setShowPasteAttributes(false);
  const { clipboard, lanes, pasteAttributesSelective } = useCutEditorStore.getState();
  const { selectedClipIds } = useSelectionStore.getState();
  const sourceClipName = clipboard[0]?.source_path?.split('/').pop() ?? 'Unknown';
  const targetNames: string[] = [];
  for (const lane of lanes) {
    for (const c of lane.clips) {
      if (selectedClipIds.has(c.clip_id)) {
        targetNames.push((c as any).source_path?.split('/').pop() ?? c.clip_id);
      }
    }
  }
  return (
    <PasteAttributesDialog
      onClose={close}
      onApply={(config) => pasteAttributesSelective(config)}
      sourceClipName={sourceClipName}
      targetClipNames={targetNames}
    />
  );
}

interface CutEditorLayoutV2Props {
  /** Script text for ScriptPanel and BPMTrack */
  scriptText?: string;
}

export default function CutEditorLayoutV2({ scriptText = '' }: CutEditorLayoutV2Props) {
  // ─── MARKER_W4.3: Autosave + manual save ───
  const { saveProject, saveProjectAs } = useCutAutosave();

  // ─── MARKER_INSPECTOR_SYNC: Auto-activate Clip tab when a clip is selected ───
  const selectedClipId = useSelectionStore((s) => s.selectedClipId);
  useEffect(() => {
    if (!selectedClipId) return;
    const api = useDockviewStore.getState().apiRef;
    if (!api) return;
    try {
      const clipPanel = api.getPanel('clip');
      if (clipPanel) clipPanel.api.setActive();
    } catch { /* panel not found */ }
  }, [selectedClipId]);

  // ─── MARKER_W5.3PT: Three-Point Editing (FCP7 Ch.36) — hook kept for external use/testing ───
  useThreePointEdit();

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
    // MARKER_K_CAPTURE: Use capture phase — dockview/timeline stopPropagation blocks bubble
    window.addEventListener('keydown', onDown, { capture: true });
    window.addEventListener('keyup', onUp, { capture: true });
    return () => { window.removeEventListener('keydown', onDown, { capture: true }); window.removeEventListener('keyup', onUp, { capture: true }); };
  }, []);

  // ─── MARKER_MULTICAM_KEYS: Number keys 1-9 switch multicam angles ───
  const multicamMode = useCutEditorStore((s) => s.multicamMode);
  useEffect(() => {
    if (!multicamMode) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const num = parseInt(e.key, 10);
      if (num >= 1 && num <= 9) {
        e.preventDefault();
        e.stopPropagation();
        useCutEditorStore.getState().multicamSwitchAngle(num - 1);
      }
    };
    window.addEventListener('keydown', onKey, { capture: true });
    return () => window.removeEventListener('keydown', onKey, { capture: true });
  }, [multicamMode]);

  // ─── MARKER_3PT_DEDUP: Shared insert/overwrite helpers (dedup of insertEdit/insertEditF9/overwriteEdit/overwriteEditF10) ───
  // Audio-only source detection: file extensions that carry no video track
  const AUDIO_ONLY_EXTS = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.opus', '.wma', '.aiff', '.aif'];
  const isAudioOnlyPath = useCallback((path: string): boolean => {
    const ext = path.slice(path.lastIndexOf('.')).toLowerCase();
    return AUDIO_ONLY_EXTS.includes(ext);
  }, []);

  const performInsert = useCallback(async () => {
    const s = useCutEditorStore.getState();
    const srcIn = s.sourceMarkIn ?? 0;
    const srcOut = s.sourceMarkOut ?? srcIn + 2;
    const dur = srcOut - srcIn;
    if (dur <= 0) return;
    const { videoLaneId, audioLaneId } = s.getInsertTargets();
    // MARKER_3PT_SRC_FIX: Find source media — sourceMediaPath → clip under playhead → any clip in timeline
    let srcPath = s.sourceMediaPath;
    if (!srcPath) {
      for (const lane of s.lanes) {
        const c = lane.clips.find((cl) => s.currentTime >= cl.start_sec && s.currentTime < cl.start_sec + cl.duration_sec);
        if (c) { srcPath = c.source_path; break; }
      }
    }
    if (!srcPath) {
      for (const lane of s.lanes) {
        if (lane.clips.length > 0) { srcPath = lane.clips[0].source_path; break; }
      }
    }
    if (!srcPath) return;
    const audioOnly = isAudioOnlyPath(srcPath);
    if (audioOnly && !audioLaneId) return;
    if (!audioOnly && !videoLaneId) return;
    const seqIn = s.sequenceMarkIn ?? s.currentTime;
    const newClipId = `clip_3pt_${Date.now()}`;
    const newLanes = s.lanes.map((lane) => {
      const isTargetVideo = !audioOnly && lane.lane_id === videoLaneId;
      const isTargetAudio = audioLaneId && lane.lane_id === audioLaneId;
      if (!isTargetVideo && !isTargetAudio) return lane;
      // Ripple: push subsequent clips right
      const shifted = lane.clips.map((c) =>
        c.start_sec >= seqIn ? { ...c, start_sec: c.start_sec + dur } : c
      );
      const clipId = isTargetVideo ? newClipId : `clip_3pt_a_${Date.now()}`;
      shifted.push({ clip_id: clipId, source_path: srcPath!, start_sec: seqIn, duration_sec: dur, source_in: srcIn } as any);
      shifted.sort((a, b) => a.start_sec - b.start_sec);
      return { ...lane, clips: shifted };
    });
    s.setLanes(newLanes);
    s.seek(seqIn + dur);
    // Async backend ops (skipRefresh: local state already updated)
    const ops: Array<Record<string, unknown>> = [];
    if (!audioOnly && videoLaneId) ops.push({ op: 'insert_at', lane_id: videoLaneId, start_sec: seqIn, duration_sec: dur, source_path: srcPath });
    if (audioLaneId) ops.push({ op: 'insert_at', lane_id: audioLaneId, start_sec: seqIn, duration_sec: dur, source_path: srcPath });
    if (ops.length > 0) s.applyTimelineOps(ops, { skipRefresh: true }).catch(() => {});
  }, [isAudioOnlyPath]);

  const performOverwrite = useCallback(async () => {
    const s = useCutEditorStore.getState();
    const srcIn = s.sourceMarkIn ?? 0;
    const srcOut = s.sourceMarkOut ?? srcIn + 2;
    const dur = srcOut - srcIn;
    if (dur <= 0) return;
    const { videoLaneId, audioLaneId } = s.getInsertTargets();
    // MARKER_3PT_SRC_FIX: Same source resolution as performInsert
    let srcPath = s.sourceMediaPath;
    if (!srcPath) {
      for (const lane of s.lanes) {
        const c = lane.clips.find((cl) => s.currentTime >= cl.start_sec && s.currentTime < cl.start_sec + cl.duration_sec);
        if (c) { srcPath = c.source_path; break; }
      }
    }
    if (!srcPath) {
      for (const lane of s.lanes) {
        if (lane.clips.length > 0) { srcPath = lane.clips[0].source_path; break; }
      }
    }
    if (!srcPath) return;
    const audioOnly = isAudioOnlyPath(srcPath);
    if (audioOnly && !audioLaneId) return;
    if (!audioOnly && !videoLaneId) return;
    const seqIn = s.sequenceMarkIn ?? s.currentTime;
    const newClipId = `clip_3pt_${Date.now()}`;
    const newLanes = s.lanes.map((lane) => {
      const isTargetVideo = !audioOnly && lane.lane_id === videoLaneId;
      const isTargetAudio = audioLaneId && lane.lane_id === audioLaneId;
      if (!isTargetVideo && !isTargetAudio) return lane;
      const clipId = isTargetVideo ? newClipId : `clip_3pt_a_${Date.now()}`;
      const clips = [...lane.clips, { clip_id: clipId, source_path: srcPath!, start_sec: seqIn, duration_sec: dur, source_in: srcIn } as any];
      clips.sort((a, b) => a.start_sec - b.start_sec);
      return { ...lane, clips };
    });
    s.setLanes(newLanes);
    s.seek(seqIn + dur);
    // Async backend ops (skipRefresh: local state already updated)
    const ops: Array<Record<string, unknown>> = [];
    if (!audioOnly && videoLaneId) ops.push({ op: 'overwrite_at', lane_id: videoLaneId, start_sec: seqIn, duration_sec: dur, source_path: srcPath });
    if (audioLaneId) ops.push({ op: 'overwrite_at', lane_id: audioLaneId, start_sec: seqIn, duration_sec: dur, source_path: srcPath });
    if (ops.length > 0) s.applyTimelineOps(ops, { skipRefresh: true }).catch(() => {});
  }, [isAudioOnlyPath]);

  // ─── MARKER_196.1: Hotkey handlers ───
  const hotkeyHandlers = useMemo<CutHotkeyHandlers>(() => ({
    // Playback — MARKER_DUAL-VIDEO: source-aware play/pause/stop
    playPause: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.togglePlaySource(); else s.togglePlay();
    },
    stop: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.pauseSource(); else s.pause();
      s.setShuttleSpeed(0);
    },
    // MARKER_W6.JKL: Progressive shuttle (FCP7 Ch.8 / App A)
    // J: reverse ramp 1x→2x→4x→8x. If playing forward, first press stops.
    // L: forward ramp 1x→2x→4x→8x. If playing reverse, first press stops.
    // K: stop (pause + reset shuttle)
    // K+J: frame step backward. K+L: frame step forward.
    shuttleBack: () => {
      const s = useCutEditorStore.getState();
      // MARKER_TD5: Dynamic Trim — J moves edit point backward when trim overlay is active
      if (s.trimEditActive) {
        const frameSec = 1 / s.projectFramerate;
        s.setTrimEditActive(true, s.trimEditClipId, Math.max(0, s.trimEditPoint - frameSec));
        return;
      }
      const isSourceFocused = s.focusedPanel === 'source';
      const doSeek = isSourceFocused ? s.seekSource : s.seek;
      const doPause = isSourceFocused ? s.pauseSource : s.pause;
      const doPlay = isSourceFocused ? s.playSource : s.play;
      const curTime = isSourceFocused ? s.sourceCurrentTime : s.currentTime;
      // MARKER_JKL-KJ-KL: K+J = single frame backward
      if (kHeldRef.current) {
        doPause();
        s.setShuttleSpeed(0);
        doSeek(Math.max(0, curTime - 1 / s.projectFramerate));
        return;
      }
      const cur = s.shuttleSpeed;
      if (cur > 0) {
        s.setShuttleSpeed(0);
        doPause();
      } else {
        const REVERSE_STEPS = [0, -1, -2, -4, -8];
        const idx = REVERSE_STEPS.indexOf(cur);
        const next = idx >= 0 && idx < REVERSE_STEPS.length - 1 ? REVERSE_STEPS[idx + 1] : -8;
        s.setShuttleSpeed(next);
        doPlay();
      }
    },
    shuttleForward: () => {
      const s = useCutEditorStore.getState();
      // MARKER_TD5: Dynamic Trim — L moves edit point forward when trim overlay is active
      if (s.trimEditActive) {
        const frameSec = 1 / s.projectFramerate;
        s.setTrimEditActive(true, s.trimEditClipId, s.trimEditPoint + frameSec);
        return;
      }
      const isSourceFocused = s.focusedPanel === 'source';
      const doSeek = isSourceFocused ? s.seekSource : s.seek;
      const doPause = isSourceFocused ? s.pauseSource : s.pause;
      const doPlay = isSourceFocused ? s.playSource : s.play;
      const curTime = isSourceFocused ? s.sourceCurrentTime : s.currentTime;
      const maxDur = isSourceFocused ? s.sourceDuration : s.duration;
      // MARKER_JKL-KJ-KL: K+L = single frame forward
      if (kHeldRef.current) {
        doPause();
        s.setShuttleSpeed(0);
        doSeek(Math.min(maxDur, curTime + 1 / s.projectFramerate));
        return;
      }
      const cur = s.shuttleSpeed;
      if (cur < 0) {
        s.setShuttleSpeed(0);
        doPause();
      } else {
        const FORWARD_STEPS = [0, 1, 2, 4, 8];
        const idx = FORWARD_STEPS.indexOf(cur);
        const next = idx >= 0 && idx < FORWARD_STEPS.length - 1 ? FORWARD_STEPS[idx + 1] : 8;
        s.setShuttleSpeed(next);
        doPlay();
      }
    },
    // MARKER_DUAL-VIDEO: Frame stepping is source-aware
    // MARKER_PLAY8-FIX: Don't clamp by duration when duration=0 (no media but clips exist)
    frameStepBack: () => {
      const s = useCutEditorStore.getState();
      const src = s.focusedPanel === 'source';
      const frameSec = 1 / s.projectFramerate;
      if (src) { s.pauseSource(); s.seekSource(Math.max(0, s.sourceCurrentTime - frameSec)); }
      else { s.pause(); s.seek(Math.max(0, s.currentTime - frameSec)); }
    },
    frameStepForward: () => {
      const s = useCutEditorStore.getState();
      const src = s.focusedPanel === 'source';
      const frameSec = 1 / s.projectFramerate;
      if (src) { s.pauseSource(); s.seekSource(s.sourceCurrentTime + frameSec); }
      else { s.pause(); s.seek(s.currentTime + frameSec); }
    },
    fiveFrameStepBack: () => {
      const s = useCutEditorStore.getState();
      const src = s.focusedPanel === 'source';
      const step = 5 / s.projectFramerate;
      if (src) { s.pauseSource(); s.seekSource(Math.max(0, s.sourceCurrentTime - step)); }
      else { s.pause(); s.seek(Math.max(0, s.currentTime - step)); }
    },
    fiveFrameStepForward: () => {
      const s = useCutEditorStore.getState();
      const src = s.focusedPanel === 'source';
      const step = 5 / s.projectFramerate;
      if (src) { s.pauseSource(); s.seekSource(s.sourceCurrentTime + step); }
      else { s.pause(); s.seek(s.currentTime + step); }
    },
    goToStart: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.seekSource(0); else s.seek(0);
    },
    goToEnd: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.seekSource(s.sourceDuration); else s.seek(s.duration);
    },
    // MARKER_W6.WIRE: Cycle playback rate (1x → 2x → 0.5x → 1x)
    cyclePlaybackRate: () => {
      const s = useCutEditorStore.getState();
      const RATES = [0.5, 1, 2, 4];
      const idx = RATES.indexOf(s.playbackRate);
      const next = RATES[(idx + 1) % RATES.length];
      s.setPlaybackRate(next);
    },

    // Marking — context-aware: source panel → source marks + sourceCurrentTime,
    // else → sequence marks + timeline currentTime
    // MARKER_DUAL-VIDEO: Source uses sourceCurrentTime, not timeline currentTime
    markIn: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkIn(s.sourceCurrentTime);
      else s.setSequenceMarkIn(s.currentTime);
    },
    markOut: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkOut(s.sourceCurrentTime);
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
      if (s.focusedPanel === 'source') {
        if (s.sourceMarkIn !== null) s.seekSource(s.sourceMarkIn);
      } else {
        if (s.sequenceMarkIn !== null) s.seek(s.sequenceMarkIn);
      }
    },
    goToOut: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') {
        if (s.sourceMarkOut !== null) s.seekSource(s.sourceMarkOut);
      } else {
        if (s.sequenceMarkOut !== null) s.seek(s.sequenceMarkOut);
      }
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
    selectAll: () => useSelectionStore.getState().selectAllClips(),

    // MARKER_CLIPBOARD: Clipboard operations
    copy: () => useCutEditorStore.getState().copyClips(),
    cut: () => useCutEditorStore.getState().cutClips(),
    paste: () => useCutEditorStore.getState().pasteClips('overwrite'),
    pasteInsert: () => useCutEditorStore.getState().pasteClips('insert'),

    // MARKER_UNDO-FIX: All editing ops route through applyTimelineOps for undo support
    // MARKER_TL4: Delete all selected clips (linked selection may include multiple)
    deleteClip: async () => {
      const s = useCutEditorStore.getState();
      const sel = useSelectionStore.getState();
      const ids = sel.selectedClipIds.size > 0 ? [...sel.selectedClipIds] : sel.selectedClipId ? [sel.selectedClipId] : [];
      if (ids.length === 0) return;
      const ops = ids.map((id) => ({ op: 'remove_clip', clip_id: id }));
      await s.applyTimelineOps(ops);
      sel.setSelectedClip(null);
      sel.clearSelection();
    },
    // MARKER_SPLIT_LOCAL_FIRST: Local-first split for instant visual feedback
    splitClip: () => {
      const s = useCutEditorStore.getState();
      const t = s.currentTime;
      for (const lane of s.lanes) {
        for (const c of lane.clips) {
          if (t > c.start_sec + 0.01 && t < c.start_sec + c.duration_sec - 0.01) {
            // Local-first: split into two halves instantly
            const leftDur = t - c.start_sec;
            const rightDur = c.duration_sec - leftDur;
            const newLanes = s.lanes.map((l) => ({
              ...l,
              clips: l.clips.flatMap((cl) => {
                if (cl.clip_id !== c.clip_id) return [cl];
                return [
                  { ...cl, clip_id: `${cl.clip_id}_L`, duration_sec: leftDur },
                  { ...cl, clip_id: `${cl.clip_id}_R`, start_sec: t, duration_sec: rightDur,
                    source_in: (cl.source_in ?? 0) + leftDur },
                ];
              }),
            }));
            s.setLanes(newLanes);
            // Async backend with skipRefresh (local state is truth)
            s.applyTimelineOps([{ op: 'split_at', clip_id: c.clip_id, split_sec: t }], { skipRefresh: true }).catch(() => {});
            return;
          }
        }
      }
    },

    // MARKER_W6.WIRE: Ripple Delete — remove clip and close gap
    // MARKER_TL4: Ripple delete all selected clips (linked selection)
    rippleDelete: async () => {
      const s = useCutEditorStore.getState();
      const sel = useSelectionStore.getState();
      const ids = sel.selectedClipIds.size > 0 ? [...sel.selectedClipIds] : sel.selectedClipId ? [sel.selectedClipId] : [];
      if (ids.length === 0) return;
      const ops = ids.map((id) => ({ op: 'ripple_delete', clip_id: id }));
      await s.applyTimelineOps(ops);
      sel.setSelectedClip(null);
      sel.clearSelection();
    },

    // MARKER_W6.WIRE: Nudge clip ±1 frame — supports multi-select (all selectedClipIds)
    nudgeLeft: async () => {
      const s = useCutEditorStore.getState();
      const { selectedClipIds } = useSelectionStore.getState();
      if (selectedClipIds.size === 0) return;
      const frameSec = 1 / s.projectFramerate;
      const ops: Array<Record<string, unknown>> = [];
      for (const lane of s.lanes) {
        for (const clip of lane.clips) {
          if (selectedClipIds.has(clip.clip_id)) {
            ops.push({ op: 'move_clip', clip_id: clip.clip_id, lane_id: lane.lane_id, start_sec: Math.max(0, clip.start_sec - frameSec) });
          }
        }
      }
      if (ops.length) await s.applyTimelineOps(ops);
    },
    nudgeRight: async () => {
      const s = useCutEditorStore.getState();
      const { selectedClipIds } = useSelectionStore.getState();
      if (selectedClipIds.size === 0) return;
      const frameSec = 1 / s.projectFramerate;
      const ops: Array<Record<string, unknown>> = [];
      for (const lane of s.lanes) {
        for (const clip of lane.clips) {
          if (selectedClipIds.has(clip.clip_id)) {
            ops.push({ op: 'move_clip', clip_id: clip.clip_id, lane_id: lane.lane_id, start_sec: clip.start_sec + frameSec });
          }
        }
      }
      if (ops.length) await s.applyTimelineOps(ops);
    },

    // MARKER_W5.3PT: Three-Point Editing (FCP7 Ch.36)
    // Comma (,) = Insert (ripple). Period (.) = Overwrite (replace).
    // MARKER_3PT_LOCAL_FIRST: Always do local-first insert/overwrite, then async backend with skipRefresh.
    // MARKER_3PT_DEDUP: Logic extracted into performInsert/performOverwrite above (audio lane support added).
    insertEdit: performInsert,
    // MARKER_3PT_LOCAL_FIRST: Always local-first overwrite
    overwriteEdit: performOverwrite,
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

    // MARKER_TL1: Fit to Fill — speed-adjust source to fill sequence range (Shift+F11)
    // FCP7 Ch.11 p.165: source duration ÷ sequence duration = speed ratio
    fitToFill: async () => {
      const s = useCutEditorStore.getState();
      const srcIn = s.sourceMarkIn ?? 0;
      const srcOut = s.sourceMarkOut;
      const seqIn = s.sequenceMarkIn ?? s.currentTime;
      const seqOut = s.sequenceMarkOut;
      if (srcOut == null || seqOut == null) return; // need both source and sequence OUT
      const srcDur = srcOut - srcIn;
      const seqDur = seqOut - seqIn;
      if (srcDur <= 0 || seqDur <= 0) return;
      const speed = srcDur / seqDur; // source 3s into 6s range = 0.5x speed
      let srcPath = s.sourceMediaPath;
      if (!srcPath) {
        for (const lane of s.lanes) {
          const c = lane.clips.find((cl) => s.currentTime >= cl.start_sec && s.currentTime < cl.start_sec + cl.duration_sec);
          if (c) { srcPath = c.source_path; break; }
        }
      }
      if (!srcPath) return;
      const { videoLaneId } = s.getInsertTargets();
      if (!videoLaneId) return;
      const newClipId = `clip_ftf_${Date.now()}`;
      // Local-first: insert clip with speed
      const newLanes = s.lanes.map((lane) => {
        if (lane.lane_id !== videoLaneId) return lane;
        const clips = [...lane.clips, {
          clip_id: newClipId, source_path: srcPath!, start_sec: seqIn,
          duration_sec: seqDur, source_in: srcIn, speed,
        } as any];
        clips.sort((a: any, b: any) => a.start_sec - b.start_sec);
        return { ...lane, clips };
      });
      s.setLanes(newLanes);
      s.seek(seqIn + seqDur);
      // Also try backend — include speed for fit-to-fill
      void s.applyTimelineOps([{
        op: 'overwrite_at', lane_id: videoLaneId, start_sec: seqIn,
        duration_sec: seqDur, source_path: srcPath, clip_id: newClipId, speed,
      }], { skipRefresh: true });
    },

    // MARKER_TL2: Superimpose — add clip on V2 above current clip (F12)
    // FCP7 Ch.11 p.167: places source clip on next higher video track at playhead
    // MARKER_TDD-GREEN: Verified — fixed V2 auto-creation when only V1 exists
    superimpose: () => {
      const s = useCutEditorStore.getState();
      const srcIn = s.sourceMarkIn ?? 0;
      const srcOut = s.sourceMarkOut ?? srcIn + 2;
      const dur = srcOut - srcIn;
      if (dur <= 0) return;
      let srcPath = s.sourceMediaPath;
      if (!srcPath) return;
      const seqIn = s.currentTime;
      const newClipId = `clip_super_${Date.now()}`;
      const videoLanes = s.lanes.filter((l) => l.lane_type.startsWith('video'));
      if (videoLanes.length === 0) return;
      let newLanes = [...s.lanes];
      if (videoLanes.length < 2) {
        // FCP7: auto-create V2 lane when superimposing with only V1
        const v2Lane = {
          lane_id: `video_${Date.now()}`,
          lane_type: 'video',
          clips: [{
            clip_id: newClipId, source_path: srcPath, start_sec: seqIn,
            duration_sec: dur, source_in: srcIn,
          }],
        };
        // Insert V2 after V1
        const v1Idx = newLanes.findIndex((l) => l.lane_id === videoLanes[0].lane_id);
        newLanes.splice(v1Idx + 1, 0, v2Lane as any);
      } else {
        // Place on existing V2
        const targetLaneId = videoLanes[1].lane_id;
        newLanes = newLanes.map((lane) => {
          if (lane.lane_id !== targetLaneId) return lane;
          const clips = [...lane.clips, {
            clip_id: newClipId, source_path: srcPath!, start_sec: seqIn,
            duration_sec: dur, source_in: srcIn,
          } as any];
          clips.sort((a: any, b: any) => a.start_sec - b.start_sec);
          return { ...lane, clips };
        });
      }
      s.setLanes(newLanes);
    },

    // MARKER_MARK-MENU: Mark Clip (X) — set In/Out to selected clip boundaries
    markClip: () => {
      const s = useCutEditorStore.getState();
      const selectedClipId = useSelectionStore.getState().selectedClipId;
      if (!selectedClipId) return;
      for (const lane of s.lanes) {
        const clip = lane.clips.find((c) => c.clip_id === selectedClipId);
        if (clip) {
          s.setSequenceMarkIn(clip.start_sec);
          s.setSequenceMarkOut(clip.start_sec + clip.duration_sec);
          return;
        }
      }
    },

    // MARKER_MARK-MENU: Play In to Out
    // MARKER_DUAL-VIDEO: Source panel uses source playback, program uses timeline
    playInToOut: () => {
      const s = useCutEditorStore.getState();
      const isSourcePanel = s.focusedPanel === 'source';
      const inPt = isSourcePanel ? s.sourceMarkIn : s.sequenceMarkIn;
      const outPt = isSourcePanel ? s.sourceMarkOut : s.sequenceMarkOut;
      if (inPt == null || outPt == null || outPt <= inPt) return;
      if (isSourcePanel) { s.seekSource(inPt); s.playSource(); }
      else { s.seek(inPt); s.play(); }
      const stopCheck = setInterval(() => {
        const st = useCutEditorStore.getState();
        const cur = isSourcePanel ? st.sourceCurrentTime : st.currentTime;
        if (cur >= outPt) {
          if (isSourcePanel) st.pauseSource(); else st.pause();
          clearInterval(stopCheck);
        }
      }, 50);
      setTimeout(() => clearInterval(stopCheck), 300000);
    },

    // MARKER_W6.WIRE: Add Marker (M) — create favorite marker at playhead
    // MARKER_PLAY8-FIX: local-first when backend unavailable
    addMarker: async () => {
      const s = useCutEditorStore.getState();
      let mediaPath = s.sourceMediaPath || '';
      for (const lane of s.lanes) {
        for (const clip of lane.clips) {
          if (s.currentTime >= clip.start_sec && s.currentTime < clip.start_sec + clip.duration_sec) {
            mediaPath = clip.source_path; break;
          }
        }
        if (mediaPath) break;
      }
      if (!mediaPath) mediaPath = 'timeline';
      // MARKER_FCP7_M: Generic marker (FCP7 Ch.52), not 'favorite'
      const newMarker = {
        marker_id: `marker_${Date.now()}`, media_path: mediaPath,
        kind: 'comment' as const, start_sec: s.currentTime, end_sec: s.currentTime + 0.04,
        score: 1.0, text: '',
      };
      if (s.sandboxRoot && s.projectId) {
        await fetch(`${API_BASE}/cut/time-markers/apply`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sandbox_root: s.sandboxRoot, project_id: s.projectId, timeline_id: s.timelineId || 'main',
            ...newMarker,
          }),
        });
        await s.refreshProjectState?.();
      } else {
        // Local-first: add to store markers directly
        s.setMarkers([...s.markers, newMarker]);
      }
    },
    // MARKER_FCP7_SHIFT_M: Extend nearest marker to playhead (FCP7 Ch.52)
    // If no marker before playhead, creates new marker from playhead
    addComment: () => {
      const s = useCutEditorStore.getState();
      // Find nearest marker that starts at or before playhead
      let nearest: typeof s.markers[0] | null = null;
      let nearestDist = Infinity;
      for (const m of s.markers) {
        if (m.start_sec <= s.currentTime) {
          const dist = s.currentTime - m.start_sec;
          if (dist < nearestDist) { nearest = m; nearestDist = dist; }
        }
      }
      if (nearest && nearestDist < 30) {
        // Extend marker's end_sec to playhead
        const updated = s.markers.map((m) =>
          m.marker_id === nearest!.marker_id
            ? { ...m, end_sec: Math.max(m.end_sec ?? m.start_sec, s.currentTime) }
            : m,
        );
        s.setMarkers(updated);
      } else {
        // No nearby marker — add new comment marker
        const newMarker = {
          marker_id: `marker_${Date.now()}`, media_path: 'timeline',
          kind: 'comment' as const, start_sec: s.currentTime, end_sec: s.currentTime + 0.04,
          score: 1.0, text: 'Comment',
        };
        s.setMarkers([...s.markers, newMarker]);
      }
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
      const selectedClipId = useSelectionStore.getState().selectedClipId;
      if (!selectedClipId) return;
      // Find selected clip to calculate relative time
      for (const lane of s.lanes) {
        const clip = lane.clips.find((c) => c.clip_id === selectedClipId);
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

    // MARKER_B3.2: Record Mode toggle
    toggleRecordMode: () => {
      const s = useCutEditorStore.getState();
      s.toggleRecordMode();
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
    // MARKER_W5.TRIM: Trim tool hotkeys — cycling (R→ripple→roll, Y→slip→slide)
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
    // MARKER_FCP7_CH19: Hand + Zoom tools
    handTool: () => useCutEditorStore.getState().setActiveTool('hand'),
    zoomTool: () => useCutEditorStore.getState().setActiveTool('zoom'),

    // View
    zoomIn: () => { const s = useCutEditorStore.getState(); s.setZoom(Math.min(s.zoom * 1.25, 500)); },
    zoomOut: () => { const s = useCutEditorStore.getState(); s.setZoom(Math.max(s.zoom / 1.25, 10)); },
    // MARKER_A2.5: Zoom to fit / zoom to selection with smooth animation
    zoomToFit: () => {
      const s = useCutEditorStore.getState();
      // If clips are selected, zoom to selection bounds (A2.5)
      const ids = useSelectionStore.getState().selectedClipIds;
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
    saveProjectAs: () => saveProjectAs(),
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
    toggleLinkedSelection: () => useSelectionStore.getState().toggleLinkedSelection(),
    // MARKER_SNAP_N: Snap toggle (N key, FCP7 standard)
    toggleSnap: () => useCutEditorStore.getState().toggleSnap(),
    // MARKER_SUBCLIP: Make Subclip (Cmd+U, FCP7 Ch.12)
    // Source In/Out → create subclip entry in project media list
    makeSubclip: () => {
      const s = useCutEditorStore.getState();
      const srcPath = s.sourceMediaPath;
      if (!srcPath) return;
      const inPt = s.sourceMarkIn ?? 0;
      const outPt = s.sourceMarkOut ?? inPt + 2;
      if (outPt <= inPt) return;
      // Create subclip as a virtual media item with in/out range
      const subclipId = `subclip_${Date.now()}`;
      const subclip = {
        clip_id: subclipId,
        source_path: srcPath,
        source_in: inPt,
        duration_sec: outPt - inPt,
        start_sec: 0,
        scene_id: `SC_${subclipId.slice(-4)}`,
      };
      // Notify via pipeline-activity event (ProjectPanel listens for new media)
      window.dispatchEvent(new CustomEvent('pipeline-activity', {
        detail: { status: 'subclip-created', subclip },
      }));
    },
    toggleViewMode: () => {
      const s = useCutEditorStore.getState();
      s.setViewMode(s.viewMode === 'nle' ? 'debug' : 'nle');
    },
    escapeContext: () => {
      const s = useCutEditorStore.getState();
      useSelectionStore.getState().clearSelection();
      s.setActiveTool('selection');
      s.setShuttleSpeed(0);
    },
    // MARKER_A4: PULSE integration hotkeys
    runPulseAnalysis: () => useCutEditorStore.getState().runPulseAnalysis(),
    runAutoMontageFavorites: () => useCutEditorStore.getState().runAutoMontage('favorites'),
    // MARKER_EXPORT: Export timeline (Cmd+E → default Premiere XML)
    exportTimeline: () => useCutEditorStore.getState().exportTimeline('premiere-xml'),

    // MARKER_TRIM5: Ripple trim, swap, delete marker, paste attributes, F9/F10 aliases
    // W — ripple trim: trim clip's Out point to playhead, close gap (FCP7 App A)
    rippleTrimToPlayhead: async () => {
      const s = useCutEditorStore.getState();
      // Find clip whose body contains the playhead on any unlocked lane
      for (const lane of s.lanes) {
        if (s.lockedLanes.has(lane.lane_id)) continue;
        for (const clip of lane.clips) {
          const clipEnd = clip.start_sec + clip.duration_sec;
          if (s.currentTime > clip.start_sec + 0.001 && s.currentTime < clipEnd - 0.001) {
            // Trim this clip's Out to playhead, then ripple subsequent clips left
            const trimAmount = clipEnd - s.currentTime;
            const newDur = s.currentTime - clip.start_sec;
            const newLanes = s.lanes.map((l) => {
              if (l.lane_id !== lane.lane_id) return l;
              return {
                ...l,
                clips: l.clips.map((c) => {
                  if (c.clip_id === clip.clip_id) return { ...c, duration_sec: newDur };
                  if (c.start_sec > clip.start_sec) return { ...c, start_sec: c.start_sec - trimAmount };
                  return c;
                }),
              };
            });
            s.setLanes(newLanes);
            // Async backend
            s.applyTimelineOps([{
              op: 'trim_clip', clip_id: clip.clip_id,
              duration_sec: newDur, ripple: true,
            }], { skipRefresh: true }).catch(() => {});
            return;
          }
        }
      }
    },
    // Cmd+Shift+S — swap two selected adjacent clips
    swapClips: () => {
      const s = useCutEditorStore.getState();
      const ids = [...useSelectionStore.getState().selectedClipIds];
      if (ids.length !== 2) return;
      // Find both clips — must be on the same lane
      for (const lane of s.lanes) {
        const clipA = lane.clips.find((c) => c.clip_id === ids[0]);
        const clipB = lane.clips.find((c) => c.clip_id === ids[1]);
        if (clipA && clipB) {
          // Sort by position
          const [first, second] = clipA.start_sec < clipB.start_sec ? [clipA, clipB] : [clipB, clipA];
          // Swap positions: second takes first's start, first shifts right
          const newLanes = s.lanes.map((l) => {
            if (l.lane_id !== lane.lane_id) return l;
            return {
              ...l,
              clips: l.clips.map((c) => {
                if (c.clip_id === first.clip_id) return { ...c, start_sec: first.start_sec + second.duration_sec };
                if (c.clip_id === second.clip_id) return { ...c, start_sec: first.start_sec };
                return c;
              }).sort((a, b) => a.start_sec - b.start_sec),
            };
          });
          s.setLanes(newLanes);
          return;
        }
      }
    },
    // Cmd+` — delete marker at or nearest to playhead
    deleteMarker: () => {
      const s = useCutEditorStore.getState();
      if (s.markers.length === 0) return;
      // Find marker closest to playhead (within 2 seconds)
      let nearest: typeof s.markers[0] | null = null;
      let nearestDist = Infinity;
      for (const m of s.markers) {
        const dist = Math.abs(m.start_sec - s.currentTime);
        if (dist < nearestDist) { nearest = m; nearestDist = dist; }
      }
      if (nearest && nearestDist < 2.0) {
        s.setMarkers(s.markers.filter((m) => m.marker_id !== nearest!.marker_id));
      }
    },
    // Alt+V — paste attributes (effects) from clipboard clip to selected clip
    pasteAttributes: () => {
      const s = useCutEditorStore.getState();
      const sel = useSelectionStore.getState();
      const clipboard = (s as any).clipboard as Array<{ clip_id: string; effects?: any; keyframes?: any }> | undefined;
      if (!clipboard || clipboard.length === 0) return;
      const sourceClip = clipboard[0];
      if (!sourceClip.effects && !sourceClip.keyframes) return;
      const targetIds = sel.selectedClipIds.size > 0 ? [...sel.selectedClipIds] : sel.selectedClipId ? [sel.selectedClipId] : [];
      if (targetIds.length === 0) return;
      const newLanes = s.lanes.map((lane) => ({
        ...lane,
        clips: lane.clips.map((c) => {
          if (!targetIds.includes(c.clip_id)) return c;
          return {
            ...c,
            effects: sourceClip.effects ? { ...sourceClip.effects } : c.effects,
            keyframes: sourceClip.keyframes ? { ...sourceClip.keyframes } : c.keyframes,
          };
        }),
      }));
      s.setLanes(newLanes);
    },
    // F9 → insert edit alias — delegates to performInsert (same logic as comma key, with audio lane support)
    insertEditF9: performInsert,
    // F10 → overwrite edit alias — delegates to performOverwrite (same logic as period key, with audio lane support)
    overwriteEditF10: performOverwrite,

    // MARKER_SEL6: 6 missing selection actions (FCP7 recon P1)
    // F6 — select clip at playhead position
    selectClipAtPlayhead: () => {
      const s = useCutEditorStore.getState();
      const sel = useSelectionStore.getState();
      for (const lane of s.lanes) {
        if (s.lockedLanes.has(lane.lane_id) || s.hiddenLanes.has(lane.lane_id)) continue;
        for (const clip of lane.clips) {
          if (s.currentTime >= clip.start_sec && s.currentTime < clip.start_sec + clip.duration_sec) {
            sel.setSelectedClip(clip.clip_id);
            return;
          }
        }
      }
    },
    // Alt+A — select all clips on the same track as the currently selected clip
    selectAllOnTrack: () => {
      const s = useCutEditorStore.getState();
      const sel = useSelectionStore.getState();
      const selId = sel.selectedClipId;
      if (!selId) return;
      for (const lane of s.lanes) {
        if (lane.clips.some((c) => c.clip_id === selId)) {
          const ids = new Set(lane.clips.map((c) => c.clip_id));
          useSelectionStore.setState({ selectedClipIds: ids });
          return;
        }
      }
    },
    // Cmd+Shift+A — deselect all
    deselectAll: () => {
      useSelectionStore.getState().clearSelection();
    },
    // Alt+Shift+Right — select all clips forward from playhead
    selectForward: () => {
      const s = useCutEditorStore.getState();
      const ids = new Set<string>();
      for (const lane of s.lanes) {
        if (s.lockedLanes.has(lane.lane_id) || s.hiddenLanes.has(lane.lane_id)) continue;
        for (const clip of lane.clips) {
          if (clip.start_sec >= s.currentTime - 0.001) ids.add(clip.clip_id);
        }
      }
      if (ids.size > 0) useSelectionStore.setState({ selectedClipIds: ids });
    },
    // T — toggle A/V selection targeting (cycle: all → video-only → audio-only → all)
    toggleAVSelection: () => {
      const s = useCutEditorStore.getState();
      const videoLanes = s.lanes.filter((l) => l.lane_type.startsWith('video')).map((l) => l.lane_id);
      const audioLanes = s.lanes.filter((l) => l.lane_type.startsWith('audio')).map((l) => l.lane_id);
      const targeted = s.targetedLanes;
      const allTargeted = [...videoLanes, ...audioLanes].every((id) => targeted.has(id));
      const onlyVideo = videoLanes.every((id) => targeted.has(id)) && audioLanes.every((id) => !targeted.has(id));
      let next: Set<string>;
      if (allTargeted || targeted.size === 0) {
        next = new Set(videoLanes);
      } else if (onlyVideo) {
        next = new Set(audioLanes);
      } else {
        next = new Set([...videoLanes, ...audioLanes]);
      }
      useCutEditorStore.setState({ targetedLanes: next });
    },
    // Cmd+L — link/unlink clips
    linkUnlinkClips: () => {
      useSelectionStore.getState().toggleLinkedSelection();
    },

    // MARKER_SOURCE_ACQUIRE: Cmd+8 — open Source Acquire panel
    focusSourceAcquire: () => {
      window.dispatchEvent(new CustomEvent('cut:focus-panel', { detail: { panelId: 'acquire' } }));
    },

    // MARKER_FCP7FIX: revealMasterClip, collapse/expand, rename — use selectionStore
    revealMasterClip: () => {
      const s = useCutEditorStore.getState();
      const clipId = useSelectionStore.getState().selectedClipId;
      if (!clipId) return;
      for (const lane of s.lanes) {
        const clip = lane.clips.find((c) => c.clip_id === clipId);
        if (clip?.source_path) {
          window.dispatchEvent(new CustomEvent('cut:reveal-master-clip', { detail: { sourcePath: clip.source_path } }));
          return;
        }
      }
    },
    collapseExpandTrack: () => {
      const s = useCutEditorStore.getState();
      const clipId = useSelectionStore.getState().selectedClipId;
      if (!clipId) return;
      for (const lane of s.lanes) {
        if (lane.clips.some((c) => c.clip_id === clipId)) { s.toggleTrackCollapse(lane.lane_id); return; }
      }
    },
    expandTrack: () => {
      const s = useCutEditorStore.getState();
      const clipId = useSelectionStore.getState().selectedClipId;
      if (!clipId) return;
      for (const lane of s.lanes) {
        if (lane.clips.some((c) => c.clip_id === clipId)) { s.expandTrackMax(lane.lane_id); return; }
      }
    },
    renameClipInline: () => {
      const clipId = useSelectionStore.getState().selectedClipId;
      if (clipId) useCutEditorStore.getState().setRenamingClip(clipId);
    },

    // MARKER_LAYOUT-3: Panel focus shortcuts (⌘1-5)
    // Updates store state AND physically activates the dockview panel tab.
    focusSource: () => {
      useCutEditorStore.getState().setFocusedPanel('source');
      try { useDockviewStore.getState().apiRef?.getPanel('source')?.api.setActive(); } catch { /* panel not mounted */ }
    },
    focusProgram: () => {
      useCutEditorStore.getState().setFocusedPanel('program');
      try { useDockviewStore.getState().apiRef?.getPanel('program')?.api.setActive(); } catch { /* panel not mounted */ }
    },
    focusTimeline: () => {
      useCutEditorStore.getState().setFocusedPanel('timeline');
      try { useDockviewStore.getState().apiRef?.getPanel('timeline')?.api.setActive(); } catch { /* panel not mounted */ }
    },
    focusProject: () => {
      useCutEditorStore.getState().setFocusedPanel('project');
      try { useDockviewStore.getState().apiRef?.getPanel('project')?.api.setActive(); } catch { /* panel not mounted */ }
    },
    focusEffects: () => {
      useCutEditorStore.getState().setFocusedPanel('effects');
      try { useDockviewStore.getState().apiRef?.getPanel('effects')?.api.setActive(); } catch { /* panel not mounted */ }
    },

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
    // MARKER_FCP7-CH15: Insert Gap (FCP7 Sequence > Insert Gap)
    insertGap: () => useCutEditorStore.getState().insertGap(),
    // MARKER_SPLIT-EDIT: L-cut / J-cut (FCP7 Ch.41)
    splitEditLCut: () => useCutEditorStore.getState().splitEditLCut(),
    splitEditJCut: () => useCutEditorStore.getState().splitEditJCut(),
    addDefaultTransition: () => useCutEditorStore.getState().addDefaultTransition(),
    // MARKER_FCP7.SPEED: Cmd+J opens speed control dialog (FCP7 Ch.69)
    openSpeedControl: () => useCutEditorStore.getState().setShowSpeedControl(true),

    // MARKER_GAMMA-P1: 6 new FCP7 UI actions
    editMarkerDialog: () => {
      const s = useCutEditorStore.getState();
      // Find marker nearest to playhead (within 0.1s tolerance)
      const marker = s.markers.find((m) =>
        Math.abs(m.start_sec - s.currentTime) < 0.1
      );
      if (marker) {
        s.setShowEditMarkerDialog(true, marker.marker_id);
      }
    },
    timecodeEntry: () => {
      useCutEditorStore.getState().setShowTimecodeEntry(true);
    },
    toggleTimelineDisplayMode: () => {
      useCutEditorStore.getState().cycleTimelineDisplayMode();
    },
    cycleClipLabelMode: () => {
      useCutEditorStore.getState().cycleClipLabelMode();
    },
    findDialog: () => {
      const s = useCutEditorStore.getState();
      s.setShowFindDialog(!s.showFindDialog);
    },
    publishDialog: () => {
      useCutEditorStore.getState().setShowPublishDialog(true);
    },

  }), [saveProject, performInsert, performOverwrite]);

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

      // MARKER_DUAL-VIDEO: Drive source or timeline based on focused panel
      const s = useCutEditorStore.getState();
      const isSourceFocused = s.focusedPanel === 'source';
      const curTime = isSourceFocused ? s.sourceCurrentTime : s.currentTime;
      let maxDur = isSourceFocused ? s.sourceDuration : s.duration;
      // MARKER_JKL_DUR_FIX: If duration is 0 (not set), compute from lanes
      if (maxDur <= 0 && !isSourceFocused) {
        for (const lane of s.lanes) {
          for (const clip of lane.clips) {
            maxDur = Math.max(maxDur, clip.start_sec + clip.duration_sec);
          }
        }
      }
      const doSeek = isSourceFocused ? s.seekSource : s.seek;
      const newTime = curTime + dt * shuttleSpeed;
      // MARKER_GAMMA-LOOP: If loop playback is on and we've reached the end, wrap back
      if (!isSourceFocused && s.loopPlayback && maxDur > 0 && newTime >= maxDur) {
        const loopStart = s.sequenceMarkIn ?? 0;
        doSeek(loopStart);
      } else {
        doSeek(Math.max(0, maxDur > 0 ? Math.min(newTime, maxDur) : newTime));
      }

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

  // ─── MARKER_B5.2: Audio playback wiring ───
  // Hook provides playAt / stopAll synced to Web Audio API.
  const { playAt, stopAll, prefetch } = useAudioPlayback();

  // Subscribe to audio-relevant store slices
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  const laneVolumes = useCutEditorStore((s) => s.laneVolumes);
  const mutedLanes = useCutEditorStore((s) => s.mutedLanes);
  const soloLanes = useCutEditorStore((s) => s.soloLanes);

  // Track current time via ref to avoid re-triggering play on every frame tick.
  // The effect that starts playback reads this ref at play-start time.
  const audioCurrentTimeRef = useRef<number>(currentTime);
  useEffect(() => {
    audioCurrentTimeRef.current = currentTime;
  });

  // Build AudioClipInfo[] from all audio lanes — memoised on lane/volume/mute/solo changes.
  const audioClips = useMemo<AudioClipInfo[]>(() => {
    const hasSolo = soloLanes.size > 0;
    const result: AudioClipInfo[] = [];
    for (const lane of lanes) {
      // Only audio lanes contribute to audio playback
      if (!lane.lane_type.startsWith('audio')) continue;
      const laneId = lane.lane_id;
      const isMuted = mutedLanes.has(laneId) || (hasSolo && !soloLanes.has(laneId));
      const volume = laneVolumes[laneId] ?? 1.0;
      for (const clip of lane.clips) {
        result.push({
          clip_id: clip.clip_id,
          source_path: clip.source_path,
          start_sec: clip.start_sec,
          duration_sec: clip.duration_sec,
          source_in: (clip as any).source_in ?? 0,
          volume,
          pan: 0,
          muted: isMuted,
        });
      }
    }
    return result;
  }, [lanes, laneVolumes, mutedLanes, soloLanes]);

  // Start / stop audio when isPlaying changes.
  useEffect(() => {
    if (isPlaying) {
      playAt(audioClips, audioCurrentTimeRef.current);
    } else {
      stopAll();
    }
    // Intentionally NOT listing audioClips in deps — rebuilding clips list should not
    // restart audio mid-play. Clips are read at play-start via audioCurrentTimeRef pattern.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, playAt, stopAll]);

  // Re-sync audio when user seeks while playback is active.
  // Stable refs let us read latest values without adding them to the seek-effect deps.
  const isPlayingRef = useRef(isPlaying);
  useEffect(() => { isPlayingRef.current = isPlaying; });

  const audioClipsRef = useRef(audioClips);
  useEffect(() => { audioClipsRef.current = audioClips; });

  const lastSyncedTimeRef = useRef(0);

  useEffect(() => {
    if (!isPlayingRef.current) return;
    const delta = Math.abs(currentTime - lastSyncedTimeRef.current);
    if (delta < 0.1) return; // Skip rAF ticks (~0.016s), only re-sync on real seeks
    lastSyncedTimeRef.current = currentTime;
    // currentTime changed while playing → re-sync audio to new position
    stopAll();
    playAt(audioClipsRef.current, currentTime);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTime, playAt, stopAll]);

  // MARKER_AUDIO_PREFETCH: Prefetch next clip's audio when playhead approaches clip boundary (2s lookahead)
  const lastPrefetchRef = useRef('');
  useEffect(() => {
    if (!isPlayingRef.current) return;
    const s = useCutEditorStore.getState();
    const audioLane = s.lanes.find((l) => l.lane_type.startsWith('audio'));
    if (!audioLane) return;
    for (const clip of audioLane.clips) {
      // If playhead is within 2s before clip start and we haven't prefetched this clip yet
      if (currentTime >= clip.start_sec - 2 && currentTime < clip.start_sec && lastPrefetchRef.current !== clip.clip_id) {
        lastPrefetchRef.current = clip.clip_id;
        prefetch([{ source_path: clip.source_path, source_in: clip.source_in ?? 0, duration_sec: clip.duration_sec, start_sec: clip.start_sec, clip_id: clip.clip_id, volume: 1, pan: 0, muted: false }]);
        break;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTime, prefetch]);

  // MARKER_VIDEO_PREFETCH: Prefetch next clip's video when playhead approaches clip boundary (2s lookahead).
  // Mirror of MARKER_AUDIO_PREFETCH. Uses a hidden <video preload="auto"> to warm the browser HTTP cache
  // so VideoPreview's <video> finds data cached → no blank-frame flash at edit points.
  // No WebCodecs, no store changes, no VideoPreview changes needed — browser cache does the work.
  const videoPrefetchElRef = useRef<HTMLVideoElement | null>(null);
  const lastVideoPrefetchRef = useRef('');
  useEffect(() => {
    if (!isPlayingRef.current) return;
    const s = useCutEditorStore.getState();
    const videoLane = s.lanes.find((l) => l.lane_type.startsWith('video'));
    if (!videoLane) return;
    for (const clip of videoLane.clips) {
      if (
        currentTime >= clip.start_sec - 2 &&
        currentTime < clip.start_sec &&
        lastVideoPrefetchRef.current !== clip.clip_id
      ) {
        lastVideoPrefetchRef.current = clip.clip_id;
        // Lazy-create hidden video element (reused across prefetch calls)
        if (!videoPrefetchElRef.current) {
          const vid = document.createElement('video');
          vid.preload = 'auto';
          vid.muted = true;
          vid.style.cssText = 'position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;';
          document.body.appendChild(vid);
          videoPrefetchElRef.current = vid;
        }
        const url = `${API_BASE}/files/raw?path=${encodeURIComponent(clip.source_path)}`;
        videoPrefetchElRef.current.src = url;
        // Seek to source_in so browser fetches the right segment
        videoPrefetchElRef.current.currentTime = clip.source_in ?? 0;
        break;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTime]);

  // MARKER_GEN-HOTKEYS-GLOBAL: Cmd+J/K/L/R generation transport hotkeys.
  // Scoped to focusedPanel==='generation'. Uses capture phase to override conflicting
  // global bindings (Cmd+J=openSpeedControl, Cmd+K=splitClip, Cmd+L=toggleLinkedSelection).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel !== 'generation') return;
      if (!e.metaKey && !e.ctrlKey) return;
      const store = useGenerationControlStore.getState();
      const { machineState } = store;
      if (e.key === 'r') {
        if (['IDLE', 'CONFIGURING', 'REJECTED'].includes(machineState)) {
          e.preventDefault();
          e.stopImmediatePropagation();
          store.submitJob();
        }
      } else if (e.key === 'j') {
        if (machineState === 'PREVIEWING') {
          e.preventDefault();
          e.stopImmediatePropagation();
          store.acceptPreview();
        }
      } else if (e.key === 'k') {
        if (machineState === 'PREVIEWING') {
          e.preventDefault();
          e.stopImmediatePropagation();
          store.rejectPreview();
        }
      } else if (e.key === 'l') {
        if (machineState === 'QUEUED' || machineState === 'GENERATING') {
          e.preventDefault();
          e.stopImmediatePropagation();
          store.cancelJob();
        }
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, []);

  // MARKER_SCRUB_SYNC: REMOVED — Source Monitor is fully independent from timeline.
  // It only changes via explicit user action: double-click, Match Frame, "Open in Source Monitor".
  // Timeline scrub/playback does NOT affect Source Monitor playhead or content.

  const viewMode = useCutEditorStore((s) => s.viewMode);

  return (
    <div style={ROOT} data-testid="cut-editor-layout">
      <MenuBar />
      {viewMode === 'debug' ? <DebugShellPanel /> : <DockviewLayout scriptText={scriptText} />}
      <ProjectSettings />
      <ExportDialog />
      {/* MARKER_B11: Speed/Duration dialog (⌘R) */}
      <SpeedControlModal />
      {/* MARKER_FCP7-FIND: Find dialog (⌘F) */}
      <FindDialog />
      {/* MARKER_TRIM_WINDOW: Floating trim edit overlay (FCP7 Ch.45-46) */}
      <TrimEditWindow />
      {/* MARKER_GAMMA-P1: Edit Marker dialog + Timecode entry */}
      <EditMarkerDialog />
      <TimecodeEntryOverlay />
      {/* MARKER_GAMMA-P2: Cross-platform publish dialog */}
      <PublishDialog />
      {/* MARKER_PASTE_ATTR: Paste Attributes dialog (⌥V) */}
      <PasteAttributesModal />
      <SaveIndicator />
    </div>
  );
}
