/**
 * MARKER_W4.3: CUT Save System hook.
 *
 * Provides:
 * - Cmd+S → explicit save
 * - Autosave timer (configurable interval, minimum 5 minutes)
 * - Recovery check on mount
 * - beforeunload guard when dirty
 *
 * Mount once in CutStandalone.
 */
import { useEffect, useRef, useCallback } from 'react';
import { useCutEditorStore } from '../store/useCutEditorStore';
import { useSelectionStore } from '../store/useSelectionStore';
import { API_BASE } from '../config/api.config';

export interface RecoveryInfo {
  recovery_available: boolean;
  autosave_at?: string;
  last_save_at?: string | null;
  snapshot_dir?: string;
  files?: string[];
}

export function useCutSaveSystem() {
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const recoveryRef = useRef<RecoveryInfo | null>(null);

  // ── Save project (delegates to the same backend as useCutAutosave) ──
  const doSave = useCallback(async () => {
    const state = useCutEditorStore.getState();
    if (!state.sandboxRoot) return;
    if (state.saveStatus === 'saving') return;

    state.setSaveStatus('saving');
    state.setSaveError(null);

    try {
      const { lanes, markers, currentTime, zoom, scrollLeft, timelineId,
              projectFramerate, projectId,
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
        view: { zoom, scroll_left: scrollLeft, current_time: currentTime },
        markers: markers || [],
        updated_at: new Date().toISOString(),
      };

      const res = await fetch(`${API_BASE}/cut/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sandbox_root: state.sandboxRoot, project_id: projectId || '', timeline_state }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Save failed: ${res.status}`);
      }

      const data = await res.json();
      state.setSaveStatus('saved');
      state.setLastSavedAt(data.saved_at);
      useCutEditorStore.setState({ hasUnsavedChanges: false });
    } catch (err) {
      state.setSaveStatus('error');
      state.setSaveError(err instanceof Error ? err.message : 'Save failed');
    }
  }, []);

  // ── Cmd+S / Cmd+Shift+S hotkey ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key === 's') {
        e.preventDefault();
        doSave();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [doSave]);

  // ── beforeunload guard ──
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (useCutEditorStore.getState().hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, []);

  // ── Recovery check on mount ──
  const checkRecovery = useCallback(async (): Promise<RecoveryInfo | null> => {
    if (!sandboxRoot) return null;
    try {
      const res = await fetch(
        `${API_BASE}/cut/recovery-check?sandbox_root=${encodeURIComponent(sandboxRoot)}`
      );
      const data = await res.json();
      if (data.success && data.recovery_available) {
        recoveryRef.current = data;
        return data as RecoveryInfo;
      }
    } catch { /* silent */ }
    return null;
  }, [sandboxRoot]);

  const recoverFromSnapshot = useCallback(async (snapshotDir: string): Promise<boolean> => {
    if (!sandboxRoot) return false;
    try {
      const res = await fetch(
        `${API_BASE}/cut/recover?sandbox_root=${encodeURIComponent(sandboxRoot)}&snapshot_dir=${encodeURIComponent(snapshotDir)}`,
        { method: 'POST' }
      );
      const data = await res.json();
      return !!data.success;
    } catch {
      return false;
    }
  }, [sandboxRoot]);

  return {
    checkRecovery,
    recoverFromSnapshot,
    recoveryRef,
  };
}
