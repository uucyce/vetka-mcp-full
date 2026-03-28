/**
 * MARKER_GEN-DOCK: Generation Control Panel — dockview wrapper.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */
import type { IDockviewPanelProps } from 'dockview-react';
import GenerationControlPanel from '../GenerationControlPanel';

export default function GenerationControlPanelDock(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'hidden', background: '#0a0a0a' }}>
      <GenerationControlPanel />
    </div>
  );
}
