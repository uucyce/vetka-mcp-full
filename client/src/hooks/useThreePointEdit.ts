/**
 * MARKER_W5.3PT: Three-Point Editing system — the heart of any NLE.
 *
 * FCP7 Ch.36: Set 3 of 4 edit points (sourceIn, sourceOut, sequenceIn, sequenceOut).
 * System auto-calculates the 4th point. Then perform Insert (,) or Overwrite (.).
 *
 * Rules (from FCP7):
 *   - Sequence IN/OUT always take precedence over source IN/OUT for duration
 *   - Missing sequence IN → use playhead position
 *   - Missing sequence OUT → auto-calculate from source duration
 *   - Missing source IN → use media start (0)
 *   - Missing source OUT → calculate from sequence duration
 *   - Insert: ripples (pushes clips right)
 *   - Overwrite: replaces (no shift)
 *
 * Backend ops used: insert_at, overwrite_at
 */
import { useCallback } from 'react';
import { useCutEditorStore } from '../store/useCutEditorStore';
import { API_BASE } from '../config/api.config';

// ─── Types ────────────────────────────────────────────────────

export interface ThreePointEditResult {
  sourceIn: number;
  sourceOut: number;
  sequenceIn: number;
  duration: number;
  sourcePath: string;
  videoLaneId: string | null;
  audioLaneId: string | null;
}

// ─── Pure resolution logic (exported for testing) ─────────────

/**
 * Resolve 4 edit points from up to 3 user-set points.
 * Returns null if insufficient information (no source media).
 */
export function resolveThreePointEdit(params: {
  sourceMarkIn: number | null;
  sourceMarkOut: number | null;
  sequenceMarkIn: number | null;
  sequenceMarkOut: number | null;
  currentTime: number;
  sourceDuration: number;
  sourceMediaPath: string | null;
  videoLaneId: string | null;
  audioLaneId: string | null;
}): ThreePointEditResult | null {
  const {
    sourceMarkIn, sourceMarkOut,
    sequenceMarkIn, sequenceMarkOut,
    currentTime, sourceDuration,
    sourceMediaPath,
    videoLaneId, audioLaneId,
  } = params;

  // Must have source media loaded
  if (!sourceMediaPath) return null;

  // Resolve source IN/OUT
  let srcIn = sourceMarkIn ?? 0;
  let srcOut = sourceMarkOut;

  // Resolve sequence IN/OUT
  let seqIn = sequenceMarkIn ?? currentTime;
  let seqOut = sequenceMarkOut;

  const hasSourceIn = sourceMarkIn !== null;
  const hasSourceOut = sourceMarkOut !== null;
  const hasSeqIn = sequenceMarkIn !== null;
  const hasSeqOut = sequenceMarkOut !== null;

  // FCP7 rule: Sequence IN/OUT takes precedence for duration
  if (hasSeqIn && hasSeqOut && seqOut !== null) {
    // Duration defined by sequence
    const seqDuration = seqOut - seqIn;
    if (seqDuration <= 0) return null;

    if (!hasSourceOut) {
      // Calculate source OUT from sequence duration
      srcOut = srcIn + seqDuration;
    }
    // Use sequence duration regardless
    return {
      sourceIn: srcIn,
      sourceOut: srcOut ?? srcIn + seqDuration,
      sequenceIn: seqIn,
      duration: seqDuration,
      sourcePath: sourceMediaPath,
      videoLaneId,
      audioLaneId,
    };
  }

  // Source IN + OUT define duration, sequence IN is position
  if (hasSourceIn && hasSourceOut && srcOut !== null) {
    const srcDuration = srcOut - srcIn;
    if (srcDuration <= 0) return null;

    if (hasSeqOut && seqOut !== null) {
      // Backtracking: sequence OUT is set, calculate sequence IN
      seqIn = seqOut - srcDuration;
      if (seqIn < 0) seqIn = 0;
    }

    return {
      sourceIn: srcIn,
      sourceOut: srcOut,
      sequenceIn: seqIn,
      duration: srcDuration,
      sourcePath: sourceMediaPath,
      videoLaneId,
      audioLaneId,
    };
  }

  // Only source IN set (no OUT) — use rest of source or a default duration
  if (hasSourceIn && !hasSourceOut) {
    const dur = sourceDuration > 0 ? sourceDuration - srcIn : 5.0;
    return {
      sourceIn: srcIn,
      sourceOut: srcIn + dur,
      sequenceIn: seqIn,
      duration: dur,
      sourcePath: sourceMediaPath,
      videoLaneId,
      audioLaneId,
    };
  }

  // No source marks at all — use entire source
  if (!hasSourceIn && !hasSourceOut) {
    const dur = sourceDuration > 0 ? sourceDuration : 5.0;
    return {
      sourceIn: 0,
      sourceOut: dur,
      sequenceIn: seqIn,
      duration: dur,
      sourcePath: sourceMediaPath,
      videoLaneId,
      audioLaneId,
    };
  }

  // Only source OUT set — from start to OUT
  if (!hasSourceIn && hasSourceOut && srcOut !== null) {
    return {
      sourceIn: 0,
      sourceOut: srcOut,
      sequenceIn: seqIn,
      duration: srcOut,
      sourcePath: sourceMediaPath,
      videoLaneId,
      audioLaneId,
    };
  }

  return null;
}

// ─── Hook ─────────────────────────────────────────────────────

export function useThreePointEdit() {
  const performEdit = useCallback(
    async (editType: 'insert' | 'overwrite') => {
      const state = useCutEditorStore.getState();

      const { videoLaneId, audioLaneId } = state.getInsertTargets();
      if (!videoLaneId) {
        console.warn('[3PT] No target video lane');
        return false;
      }

      // MARKER_3PT1-FIX: If no source media loaded, fall back to clip under playhead.
      // FCP7 behavior: if Source Monitor is empty, use the clip at playhead as source.
      let effectiveSourcePath = state.sourceMediaPath;
      let effectiveSourceDuration = state.duration;
      if (!effectiveSourcePath) {
        for (const lane of state.lanes) {
          for (const clip of lane.clips) {
            if (state.currentTime >= clip.start_sec && state.currentTime < clip.start_sec + clip.duration_sec) {
              effectiveSourcePath = clip.source_path;
              effectiveSourceDuration = clip.duration_sec;
              break;
            }
          }
          if (effectiveSourcePath) break;
        }
      }

      const resolved = resolveThreePointEdit({
        sourceMarkIn: state.sourceMarkIn,
        sourceMarkOut: state.sourceMarkOut,
        sequenceMarkIn: state.sequenceMarkIn,
        sequenceMarkOut: state.sequenceMarkOut,
        currentTime: state.currentTime,
        sourceDuration: effectiveSourceDuration,
        sourceMediaPath: effectiveSourcePath,
        videoLaneId,
        audioLaneId,
      });

      if (!resolved) {
        console.warn('[3PT] Cannot resolve edit points — no source media loaded');
        return false;
      }

      const op = editType === 'insert' ? 'insert_at' : 'overwrite_at';

      const ops: Array<Record<string, unknown>> = [{
        op,
        lane_id: resolved.videoLaneId,
        start_sec: resolved.sequenceIn,
        duration_sec: resolved.duration,
        source_path: resolved.sourcePath,
      }];

      // Execute via backend
      if (!state.sandboxRoot || !state.projectId) {
        console.warn('[3PT] No active project session');
        return false;
      }

      try {
        const response = await fetch(`${API_BASE}/cut/timeline/apply`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sandbox_root: state.sandboxRoot,
            project_id: state.projectId,
            timeline_id: state.timelineId || 'main',
            author: 'cut_3pt_edit',
            ops,
          }),
        });

        if (!response.ok) {
          console.error(`[3PT] HTTP ${response.status}`);
          return false;
        }

        const payload = await response.json() as { success?: boolean };
        if (!payload.success) {
          console.error('[3PT] Backend returned failure');
          return false;
        }

        // Refresh timeline data
        await state.refreshProjectState?.();

        // Move playhead to end of inserted clip
        state.seek(resolved.sequenceIn + resolved.duration);

        // Clear sequence marks after edit (FCP7 behavior)
        state.setSequenceMarkIn(null);
        state.setSequenceMarkOut(null);

        return true;
      } catch (err) {
        console.error('[3PT] Edit failed:', err);
        return false;
      }
    },
    [],
  );

  const insertEdit = useCallback(() => performEdit('insert'), [performEdit]);
  const overwriteEdit = useCallback(() => performEdit('overwrite'), [performEdit]);

  return { insertEdit, overwriteEdit, performEdit };
}
