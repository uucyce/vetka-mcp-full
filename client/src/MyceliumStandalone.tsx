/**
 * MyceliumStandalone — Standalone wrapper for MCC window
 * MARKER_134.C34C: Separate Tauri window for autonomous monitoring
 * MARKER_135.4C: Simplified — DAG is now first tab in DevPanel
 *
 * @status active
 * @phase 135.4
 */
import { DevPanel } from './components/panels/DevPanel';

export default function MyceliumStandalone() {
  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#111',
      overflow: 'hidden',
    }}>
      <DevPanel standalone={true} />
    </div>
  );
}
