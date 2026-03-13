import { useEffect, useRef } from 'react';

import { API_BASE } from '../config/api.config';
import { useCutEditorStore, type TimelineClip, type TimelineLane } from '../store/useCutEditorStore';

type AudioLaneState = {
  audio: HTMLAudioElement;
  sourceNode: MediaElementAudioSourceNode;
  gainNode: GainNode;
  sourcePath: string;
};

function isAudioLane(lane: TimelineLane): boolean {
  const laneType = String(lane.lane_type || '').toLowerCase();
  return laneType.includes('audio');
}

function buildMediaUrl(sourcePath: string, sandboxRoot: string | null): string {
  if (sandboxRoot) {
    return `${API_BASE}/cut/media-proxy?sandbox_root=${encodeURIComponent(sandboxRoot)}&path=${encodeURIComponent(sourcePath)}`;
  }
  return sourcePath;
}

function resolveActiveClip(lane: TimelineLane, currentTime: number): TimelineClip | null {
  return (
    lane.clips.find((clip) => {
      const startSec = Number(clip.start_sec || 0);
      const endSec = startSec + Number(clip.duration_sec || 0);
      return currentTime >= startSec && currentTime <= endSec;
    }) || null
  );
}

export default function useAudioEngine() {
  const lanes = useCutEditorStore((state) => state.lanes);
  const currentTime = useCutEditorStore((state) => state.currentTime);
  const isPlaying = useCutEditorStore((state) => state.isPlaying);
  const playbackRate = useCutEditorStore((state) => state.playbackRate);
  const sandboxRoot = useCutEditorStore((state) => state.sandboxRoot);
  const mutedLanes = useCutEditorStore((state) => state.mutedLanes);
  const soloLanes = useCutEditorStore((state) => state.soloLanes);
  const laneVolumes = useCutEditorStore((state) => state.laneVolumes);

  const audioContextRef = useRef<AudioContext | null>(null);
  const laneStatesRef = useRef<Map<string, AudioLaneState>>(new Map());

  useEffect(() => {
    return () => {
      for (const state of laneStatesRef.current.values()) {
        state.audio.pause();
        state.audio.src = '';
        state.sourceNode.disconnect();
        state.gainNode.disconnect();
      }
      laneStatesRef.current.clear();
      void audioContextRef.current?.close();
      audioContextRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.AudioContext === 'undefined') {
      return;
    }

    const audioLanes = lanes.filter(isAudioLane);
    if (!audioLanes.length) {
      for (const state of laneStatesRef.current.values()) {
        state.audio.pause();
      }
      return;
    }

    const context = audioContextRef.current ?? new window.AudioContext();
    audioContextRef.current = context;
    if (isPlaying && context.state === 'suspended') {
      void context.resume().catch(() => undefined);
    }

    const soloActive = soloLanes.size > 0;
    const activeLaneIds = new Set<string>();

    for (const lane of audioLanes) {
      const activeClip = resolveActiveClip(lane, currentTime);
      const laneId = String(lane.lane_id || '');
      activeLaneIds.add(laneId);
      const mutedBySolo = soloActive && !soloLanes.has(laneId);
      const isMuted = mutedLanes.has(laneId) || mutedBySolo;
      const laneVolume = Math.max(0, Math.min(1.5, Number(laneVolumes[laneId] ?? 1)));

      if (!activeClip?.source_path) {
        const state = laneStatesRef.current.get(laneId);
        if (state) {
          state.gainNode.gain.value = 0;
          state.audio.pause();
        }
        continue;
      }

      let laneState = laneStatesRef.current.get(laneId);
      if (!laneState || laneState.sourcePath !== activeClip.source_path) {
        if (laneState) {
          laneState.audio.pause();
          laneState.audio.src = '';
          laneState.sourceNode.disconnect();
          laneState.gainNode.disconnect();
        }

        const audio = new Audio(buildMediaUrl(activeClip.source_path, sandboxRoot));
        audio.preload = 'auto';
        audio.crossOrigin = 'anonymous';

        const gainNode = context.createGain();
        const sourceNode = context.createMediaElementSource(audio);
        sourceNode.connect(gainNode);
        gainNode.connect(context.destination);

        laneState = {
          audio,
          sourceNode,
          gainNode,
          sourcePath: activeClip.source_path,
        };
        laneStatesRef.current.set(laneId, laneState);
      }

      const clipLocalTime = Math.max(
        0,
        Number(currentTime) - Number(activeClip.start_sec || 0) + Number(activeClip.sync?.offset_sec || 0)
      );
      if (Number.isFinite(clipLocalTime) && Math.abs(laneState.audio.currentTime - clipLocalTime) > 0.08) {
        try {
          laneState.audio.currentTime = clipLocalTime;
        } catch {
          // Ignore out-of-bounds seeks while metadata is still loading.
        }
      }

      laneState.audio.playbackRate = playbackRate;
      laneState.gainNode.gain.value = isMuted ? 0 : laneVolume;

      if (isPlaying) {
        void laneState.audio.play().catch(() => undefined);
      } else {
        laneState.audio.pause();
      }
    }

    for (const [laneId, state] of laneStatesRef.current.entries()) {
      if (!activeLaneIds.has(laneId)) {
        state.gainNode.gain.value = 0;
        state.audio.pause();
      }
    }
  }, [currentTime, isPlaying, laneVolumes, lanes, mutedLanes, playbackRate, sandboxRoot, soloLanes]);
}
