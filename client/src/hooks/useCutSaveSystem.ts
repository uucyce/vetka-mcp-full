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
  const isDirty = useCutEditorStore((s) => s.isDirty);
  const autosaveEnabled = useCutEditorStore((s) => s.autosaveEnabled);
  const autosaveIntervalMinutes = useCutEditorStore((s) => s.autosaveIntervalMinutes);
  const saveProject = useCutEditorStore((s) => s.saveProject);
  const triggerAutosave = useCutEditorStore((s) => s.triggerAutosave);
  const recoveryRef = useRef<RecoveryInfo | null>(null);
  const autosaveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Cmd+S / Cmd+Shift+S hotkey ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key === 's') {
        e.preventDefault();
        if (e.shiftKey) {
          // Cmd+Shift+S = Save As — TODO: open dialog
          // For now, same as save
          saveProject();
        } else {
          saveProject();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [saveProject]);

  // ── Autosave timer ──
  useEffect(() => {
    if (autosaveTimerRef.current) {
      clearInterval(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }
    if (!autosaveEnabled || !sandboxRoot) return;
    const ms = Math.max(5, autosaveIntervalMinutes) * 60 * 1000;
    autosaveTimerRef.current = setInterval(() => {
      triggerAutosave();
    }, ms);
    return () => {
      if (autosaveTimerRef.current) {
        clearInterval(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    };
  }, [autosaveEnabled, autosaveIntervalMinutes, sandboxRoot, triggerAutosave]);

  // ── beforeunload guard ──
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

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
