/**
 * MARKER_W4.3: Save + Autosave hook for CUT NLE.
 *
 * Provides:
 *   saveProject()    — manual save (Cmd+S), flushes state to backend (main file)
 *   saveProjectAs()  — save as new project name (Cmd+Shift+S), prompts for name
 *   Autosave         — every 2 minutes if hasUnsavedChanges, writes to .autosave/
 *   checkRecovery()  — called on mount, offers recovery when autosave is newer
 *   Save status      — 'idle' | 'saving' | 'saved' | 'error'
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
 * Pass overrideProjectId to save under a different project name (Save As).
 */
async function saveProjectToBackend(overrideProjectId?: string): Promise<string | null> {
  const state = useCutEditorStore.getState();
  const { sandboxRoot, projectId } = state;

  if (!sandboxRoot) return null;

  const effectiveProjectId = overrideProjectId ?? projectId ?? '';

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
      project_id: effectiveProjectId,
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
        project_id: effectiveProjectId,
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
    return data.project_id ?? effectiveProjectId;
  } catch (err) {
    state.setSaveStatus('error');
    state.setSaveError(err instanceof Error ? err.message : 'Save failed');
    return null;
  }
}

/**
 * MARKER_AUTOSAVE: Write current timeline state to .autosave/ (periodic background save).
 * Does NOT update save status or clear hasUnsavedChanges — autosave is silent.
 */
async function autosaveToBackend(): Promise<void> {
  const state = useCutEditorStore.getState();
  const { sandboxRoot, projectId, lanes, markers, currentTime, zoom, scrollLeft,
          timelineId, projectFramerate,
          sourceMarkIn, sourceMarkOut, sequenceMarkIn, sequenceMarkOut } = state;
  const selectedClipId = useSelectionStore.getState().selectedClipId;

  if (!sandboxRoot) return;

  try {
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
      view: { zoom, scroll_left: scrollLeft, current_time: currentTime },
      markers: markers || [],
      updated_at: new Date().toISOString(),
    };
    await fetch(`${API_BASE}/cut/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sandbox_root: sandboxRoot,
        project_id: projectId || '',
        timeline_state,
        autosave: true,
      }),
    });
    // Intentionally silent — no status update on autosave
  } catch {
    // Autosave failures are intentionally silent
  }
}

/**
 * MARKER_AUTOSAVE: Check if a newer autosave exists and offer recovery via window.confirm.
 * Called once when sandboxRoot is first established.
 */
async function checkAndOfferRecovery(sandboxRoot: string): Promise<void> {
  try {
    const res = await fetch(
      `${API_BASE}/cut/autosave/check?sandbox_root=${encodeURIComponent(sandboxRoot)}`
    );
    if (!res.ok) return;

    const data: { has_recovery: boolean; autosave_at: string | null; saved_at: string | null } =
      await res.json();
    if (!data.has_recovery) return;

    const autosaveDate = data.autosave_at ? new Date(data.autosave_at).toLocaleString() : 'unknown';
    const savedDate = data.saved_at ? new Date(data.saved_at).toLocaleString() : 'none';

    const confirmed = window.confirm(
      `An autosave from ${autosaveDate} is newer than the last manual save (${savedDate}).\n\nRestore from autosave?`
    );
    if (!confirmed) return;

    const recoverRes = await fetch(`${API_BASE}/cut/autosave/recover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sandbox_root: sandboxRoot }),
    });
    if (!recoverRes.ok) {
      console.error('[CUT] Autosave recovery failed:', recoverRes.status);
      return;
    }

    // Reload project state from backend after recovery
    await useCutEditorStore.getState().refreshProjectState?.();
  } catch (err) {
    console.error('[CUT] Autosave check error:', err);
  }
}

export function useCutAutosave() {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recoveryCheckedRef = useRef(false);

  // Expose saveProject for hotkey use
  const saveProject = useCallback(() => {
    saveProjectToBackend();
  }, []);

  // Save As — prompts for a new project name, saves under that name, updates store
  const saveProjectAs = useCallback(() => {
    const currentId = useCutEditorStore.getState().projectId ?? 'project';
    const newName = window.prompt('Save project as:', currentId);
    if (!newName || !newName.trim()) return;
    const trimmed = newName.trim();
    saveProjectToBackend(trimmed).then((savedId) => {
      if (savedId) {
        useCutEditorStore.setState({ projectId: savedId });
      }
    });
  }, []);

  // MARKER_AUTOSAVE: Check for recovery once when sandboxRoot is first established
  const sandboxRoot = useCutEditorStore(state => state.sandboxRoot);
  useEffect(() => {
    if (!sandboxRoot || recoveryCheckedRef.current) return;
    recoveryCheckedRef.current = true;
    void checkAndOfferRecovery(sandboxRoot);
  }, [sandboxRoot]);

  // Autosave timer — writes to .autosave/ path (silent, does not affect save status)
  useEffect(() => {
    timerRef.current = setInterval(() => {
      const { hasUnsavedChanges, sandboxRoot: root, saveStatus } = useCutEditorStore.getState();
      if (hasUnsavedChanges && root && saveStatus !== 'saving') {
        void autosaveToBackend();
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

  // Beforeunload guard — warn user if there are unsaved changes
  const hasUnsavedChanges = useCutEditorStore(state => state.hasUnsavedChanges);
  useEffect(() => {
    if (!hasUnsavedChanges) return;

    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };

    window.addEventListener('beforeunload', handler);
    return () => {
      window.removeEventListener('beforeunload', handler);
    };
  }, [hasUnsavedChanges]);

  return { saveProject, saveProjectAs };
}
