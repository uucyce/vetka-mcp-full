/**
 * MARKER_GEN-HOTKEYS: Generation transport hotkeys.
 *
 * Scoped to focusedPanel === 'generation'.
 * J/K/L: FCP7-style transport mapped to generation lifecycle.
 * Space: toggle generate/cancel.
 * Escape: cancel or reject.
 * Enter: accept preview.
 * Cmd+R: generate.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */
import { useEffect } from 'react';
import { useGenerationControlStore } from '../store/useGenerationControlStore';
import { useCutEditorStore } from '../store/useCutEditorStore';

export function useGenerationHotkeys() {
  const focusedPanel = useCutEditorStore((s) => s.focusedPanel);

  useEffect(() => {
    if (focusedPanel !== 'generation') return;

    const handler = (e: KeyboardEvent) => {
      // Skip if typing in input/textarea/select
      const target = e.target as HTMLElement;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;

      const store = useGenerationControlStore.getState();
      const { machineState } = store;

      // K — cancel (FCP7 "stop deck")
      if (e.key === 'k' && !e.metaKey && !e.ctrlKey) {
        if (machineState === 'QUEUED' || machineState === 'GENERATING') {
          e.preventDefault();
          store.cancelJob();
        }
        return;
      }

      // L — play preview (FCP7 "play forward")
      if (e.key === 'l' && !e.metaKey && !e.ctrlKey) {
        if (machineState === 'PREVIEWING') {
          e.preventDefault();
          const video = document.querySelector<HTMLVideoElement>('[data-testid="preview-video"]');
          video?.play().catch(() => {});
        }
        return;
      }

      // J — rewind preview (FCP7 "play reverse")
      if (e.key === 'j' && !e.metaKey && !e.ctrlKey) {
        if (machineState === 'PREVIEWING') {
          e.preventDefault();
          const video = document.querySelector<HTMLVideoElement>('[data-testid="preview-video"]');
          if (video) video.currentTime = 0;
        }
        return;
      }

      // Cmd+R — generate
      if (e.key === 'r' && (e.metaKey || e.ctrlKey)) {
        if (['IDLE', 'CONFIGURING', 'REJECTED'].includes(machineState)) {
          e.preventDefault();
          // Trigger generate via transport bar's button
          const btn = document.querySelector<HTMLButtonElement>('[data-testid="btn-generate"]');
          btn?.click();
        }
        return;
      }

      // Space — toggle generate/pause-preview
      if (e.key === ' ' && !e.metaKey) {
        e.preventDefault();
        if (['IDLE', 'CONFIGURING', 'REJECTED'].includes(machineState)) {
          const btn = document.querySelector<HTMLButtonElement>('[data-testid="btn-generate"]');
          btn?.click();
        } else if (machineState === 'GENERATING' || machineState === 'QUEUED') {
          store.cancelJob();
        } else if (machineState === 'PREVIEWING') {
          const video = document.querySelector<HTMLVideoElement>('[data-testid="preview-video"]');
          if (video) {
            if (video.paused) video.play().catch(() => {});
            else video.pause();
          }
        }
        return;
      }

      // Enter — accept preview
      if (e.key === 'Enter' && !e.metaKey) {
        if (machineState === 'PREVIEWING') {
          e.preventDefault();
          store.acceptPreview();
        }
        return;
      }

      // Escape — cancel or reject
      if (e.key === 'Escape') {
        if (machineState === 'GENERATING' || machineState === 'QUEUED') {
          e.preventDefault();
          store.cancelJob();
        } else if (machineState === 'PREVIEWING') {
          e.preventDefault();
          store.rejectPreview();
        }
        return;
      }

      // Cmd+F — capture reference frame
      if (e.key === 'f' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        const btn = document.querySelector<HTMLButtonElement>('[data-testid="btn-capture-ref"]');
        btn?.click();
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [focusedPanel]);
}
