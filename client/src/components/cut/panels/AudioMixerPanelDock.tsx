/**
 * MARKER_B13: Audio Mixer panel wrapper for dockview.
 * No focusedPanel mapping (non-scoped panel).
 */
import type { IDockviewPanelProps } from 'dockview-react';
import AudioMixer from '../AudioMixer';

export default function AudioMixerPanelDock(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'hidden', background: '#0a0a0a' }}>
      <AudioMixer />
    </div>
  );
}
