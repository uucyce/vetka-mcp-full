/**
 * MARKER_C4.5 + GAMMA-INS1: Inspector panel — shows ClipInspector when clip selected,
 * PulseInspector otherwise. Reactive to selectedClipId from store.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useSelectionStore } from '../../../store/useSelectionStore';
import PulseInspector from '../PulseInspector';
import ClipInspector from '../ClipInspector';

export default function InspectorPanelDock(_props: IDockviewPanelProps) {
  const selectedClipId = useSelectionStore((s) => s.selectedClipId);

  return (
    <div style={{ height: '100%', overflow: 'auto', background: '#0d0d0d' }}>
      {selectedClipId ? <ClipInspector /> : <PulseInspector />}
    </div>
  );
}
