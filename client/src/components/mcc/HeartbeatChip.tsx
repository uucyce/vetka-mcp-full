import { useState, useEffect, useCallback } from 'react';
import { useMCCStore } from '../../store/useMCCStore';

// Format interval seconds to human-readable
function fmtInterval(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

const INTERVAL_OPTIONS = [
  { value: 60, label: '1m' },
  { value: 300, label: '5m' },
  { value: 900, label: '15m' },
  { value: 3600, label: '1h' },
  { value: 86400, label: '1d' },
];

export const HeartbeatChip: React.FC = () => {
  const { heartbeat, fetchHeartbeat, updateHeartbeat } = useMCCStore();
  const [nextTickIn, setNextTickIn] = useState<number | null>(null);
  const [showMenu, setShowMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });

  // Fetch initial state
  useEffect(() => {
    fetchHeartbeat();
  }, [fetchHeartbeat]);

  // Countdown timer
  useEffect(() => {
    if (!heartbeat?.enabled || !heartbeat.last_tick) {
      setNextTickIn(null);
      return;
    }
    const update = () => {
      const remaining = Math.max(0, Math.round(heartbeat.last_tick + heartbeat.interval_seconds - Date.now() / 1000));
      setNextTickIn(remaining);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [heartbeat?.enabled, heartbeat?.last_tick, heartbeat?.interval_seconds]);

  // Listen for live updates
  useEffect(() => {
    const handleBoardUpdate = () => fetchHeartbeat();
    window.addEventListener('task-board-updated', handleBoardUpdate);
    return () => window.removeEventListener('task-board-updated', handleBoardUpdate);
  }, [fetchHeartbeat]);

  const handleClick = useCallback(async () => {
    if (!heartbeat) return;
    try {
      await updateHeartbeat({ enabled: !heartbeat.enabled });
    } catch (err) {
      console.error('Failed to toggle heartbeat:', err);
    }
  }, [heartbeat, updateHeartbeat]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setMenuPosition({ x: e.clientX, y: e.clientY });
    setShowMenu(true);
  }, []);

  const handleIntervalSelect = useCallback(async (interval: number) => {
    if (!heartbeat) return;
    try {
      await updateHeartbeat({ interval_seconds: interval });
      setShowMenu(false);
    } catch (err) {
      console.error('Failed to set interval:', err);
    }
  }, [heartbeat, updateHeartbeat]);

  const displayText = heartbeat?.enabled
    ? `ON ${nextTickIn !== null ? `${nextTickIn}s` : '...'}` 
    : 'OFF';

  return (
    <>
      <div
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        style={{
          height: 24,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '0 8px',
          background: '#111',
          border: '1px solid #333',
          borderRadius: 4,
          color: '#e0e0e0',
          fontSize: 9,
          fontFamily: 'monospace',
          cursor: 'pointer',
          userSelect: 'none',
          position: 'relative',
        }}
      >
        {heartbeat?.enabled && (
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#4ecdc4',
              boxShadow: '0 0 4px #4ecdc4',
              animation: 'pulse 1.5s infinite',
            }}
          />
        )}
        <span style={{ color: heartbeat?.enabled ? '#e0e0e0' : '#666' }}>
          {displayText}
        </span>
      </div>

      {/* Interval selector popup */}
      {showMenu && (
        <div
          style={{
            position: 'fixed',
            left: menuPosition.x,
            top: menuPosition.y,
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: 4,
            zIndex: 1000,
            padding: 4,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          {INTERVAL_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => handleIntervalSelect(opt.value)}
              style={{
                background: 'none',
                border: 'none',
                color: '#ccc',
                fontSize: 9,
                fontFamily: 'monospace',
                padding: '4px 8px',
                textAlign: 'left',
                cursor: 'pointer',
                borderRadius: 2,
              }}
              onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.08)'}
              onMouseLeave={e => e.target.style.background = 'none'}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.4; }
          100% { opacity: 1; }
        }
      `}</style>
    </>
  );
};