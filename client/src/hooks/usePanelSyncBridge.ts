/**
 * MARKER_W1.1: PanelSyncStore → EditorStore bridge.
 *
 * Problem: ScriptPanel, DAGProjectPanel, StorySpace3D write to usePanelSyncStore.
 * But VideoPreview, TimelineTrackView, MonitorTransport only read useCutEditorStore.
 * These two stores are islands — no connection between them.
 *
 * Solution: This hook subscribes to PanelSyncStore changes and forwards them
 * to EditorStore actions. Mount once in CutStandalone.
 *
 * Bridge routes:
 *   PanelSyncStore.selectedAssetPath  → EditorStore.setSourceMedia()
 *   PanelSyncStore.playheadSec        → EditorStore.seek()  (from script/storyspace/dag clicks)
 *   PanelSyncStore.activeSceneId      → EditorStore (stored for DAG highlight / Inspector)
 */
import { useEffect } from 'react';
import { usePanelSyncStore } from '../store/usePanelSyncStore';
import { useCutEditorStore } from '../store/useCutEditorStore';

export function usePanelSyncBridge() {
  useEffect(() => {
    // Subscribe to PanelSyncStore changes
    const unsub = usePanelSyncStore.subscribe((state, prevState) => {
      const editorStore = useCutEditorStore.getState();

      // 1. Asset selection → Source Monitor
      //    When user clicks a node in DAG or a scene in Script → show that asset in Source Monitor
      if (state.selectedAssetPath !== prevState.selectedAssetPath && state.selectedAssetPath) {
        editorStore.setSourceMedia(state.selectedAssetPath);
      }

      // 2. Playhead sync → seek timeline
      //    When user clicks a script line or StorySpace dot → move timeline playhead
      //    Only sync from script/storyspace/dag sources (not from timeline itself, to avoid loops)
      if (
        state.playheadSec !== prevState.playheadSec &&
        state.lastSyncSource &&
        state.lastSyncSource !== 'timeline' &&
        state.lastSyncSource !== 'transport'
      ) {
        editorStore.seek(state.playheadSec);
      }
    });

    return unsub;
  }, []);
}
