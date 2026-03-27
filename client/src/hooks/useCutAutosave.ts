/**
 * MARKER_W4.3: Save + Autosave hook for CUT NLE.
 *
 * Provides:
 *   saveProject()  — manual save (Cmd+S), flushes state to backend
 *   Autosave       — every 2 minutes if hasUnsavedChanges
 *   Save status    — 'idle' | 'saving' | 'saved' | 'error'
 *
 * Mount once in CutStandalone or CutEditorLayoutV2.
 */
import { useCallback, useEffect, useRef } from 'react';
import { API_BASE } from '../config/api.config';
import { useCutEditorStore } from '../store/useCutEditorStore';
import { useSelectionStore } from '../store/useSelectionStore';

const AUTOSAVE_INTERVAL_MS = 2 * 60 * 1000; // 2 minutes

/**
 * Save current project state to backend.
 * Called by Cmd+S hotkey and autosave timer.
 */
async function saveProjectToBackend(): Promise<void> {
  const state = useCutEditorStore.getState();
  const { sandboxRoot, projectId } = state;

  if (!sandboxRoot) return;

  state.setSaveStatus('saving');
  state.setSaveError(null);

  try {
    // MARKER_A15: Serialize timeline state in cut_timeline_state_v1 schema
    // so backend persists actual editing data. Without this, Cmd+S saved nothing useful.
    const { lanes, markers, currentTime, zoom, scrollLeft, timelineId,
            projectFramerate,
            sourceMarkIn, sourceMarkOut, sequenceMarkIn, sequenceMarkOut } = state;
    const selectedClipId = useSelectionStore.getState().selectedClipId;
    const timeline_state = {
      schema_version: 'cut_timeline_state_v1',
      project_id: projectId || '',
      timeline_id: timelineId || 'main',
      revision: 0,
      fps: projectFramerate,
      lanes,
      selection: {
        selected_clip_ids: selectedClipId ? [selectedClipId] : [],
        source_mark_in: sourceMarkIn,
        source_mark_out: sourceMarkOut,
        sequence_mark_in: sequenceMarkIn,
        sequence_mark_out: sequenceMarkOut,
      },
      view: {
        zoom,
        scroll_left: scrollLeft,
        current_time: currentTime,
      },
      markers: markers || [],
      updated_at: new Date().toISOString(),
    };

    const res = await fetch(`${API_BASE}/cut/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sandbox_root: sandboxRoot,
        project_id: projectId || '',
        timeline_state,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Save failed: ${res.status}`);
    }

    const data = await res.json();
    state.setSaveStatus('saved');
    state.setLastSavedAt(data.saved_at);
    // Clear unsaved flag
    useCutEditorStore.setState({ hasUnsavedChanges: false });
  } catch (err) {
    state.setSaveStatus('error');
    state.setSaveError(err instanceof Error ? err.message : 'Save failed');
  }
}

export function useCutAutosave() {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Expose saveProject for hotkey use
  const saveProject = useCallback(() => {
    saveProjectToBackend();
  }, []);

  // Autosave timer
  useEffect(() => {
    timerRef.current = setInterval(() => {
      const { hasUnsavedChanges, sandboxRoot, saveStatus } = useCutEditorStore.getState();
      if (hasUnsavedChanges && sandboxRoot && saveStatus !== 'saving') {
        saveProjectToBackend();
      }
    }, AUTOSAVE_INTERVAL_MS);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Track unsaved changes — subscribe to lane/marker mutations
  useEffect(() => {
    const unsub = useCutEditorStore.subscribe(
      (state, prevState) => {
        // Only mark dirty on actual data changes (not UI state)
        if (
          state.lanes !== prevState.lanes ||
          state.markers !== prevState.markers
        ) {
          if (state.saveStatus !== 'saving') {
            state.markUnsavedChanges();
          }
        }
      },
    );
    return unsub;
  }, []);

  return { saveProject };
}
