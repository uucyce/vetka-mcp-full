/**
 * MyceliumStandalone — Standalone wrapper for MCC window
 * MARKER_134.C34C: Separate Tauri window for autonomous monitoring
 *
 * @status active
 * @phase 134
 */
import { DevPanel } from './components/panels/DevPanel';

export default function MyceliumStandalone() {
  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#0a0a0a',
      overflow: 'hidden',
    }}>
      <DevPanel standalone={true} />
    </div>
  );
}
