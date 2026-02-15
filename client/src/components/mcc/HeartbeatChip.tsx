import { useState, useEffect, useCallback } from 'react';
import { useMCCStore } from '../../store/useMCCStore';

// Format interval helper
function fmtInterval(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

export function HeartbeatChip() {
  const { heartbeat, updateHeartbeat } = useMCCStore();
  const [nextTickIn, setNextTickIn] = useState<number | null>(null);
  const [showIntervalInput, setShowIntervalInput] = useState(false);
  const [tempInterval, setTempInterval] = useState(heartbeat?.interval || 30);

  // Countdown timer effect
  useEffect(() => {
    if (!heartbeat?.enabled || !heartbeat.last_tick) {
      setNextTickIn(null);
      return;
    }
    const update = () => {
      const remaining = Math.max(0, Math.round(heartbeat.last_tick + heartbeat.interval - Date.now() / 1000));
      setNextTickIn(remaining);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [heartbeat?.enabled, heartbeat?.last_tick, heartbeat?.interval]);

  // Toggle heartbeat
  const handleToggle = useCallback(async () => {
    if (!heartbeat) return;
    await updateHeartbeat({ enabled: !heartbeat.enabled });
  }, [heartbeat, updateHeartbeat]);

  // Handle interval change
  const handleIntervalSubmit = useCallback(async () => {
    if (!heartbeat) return;
    await updateHeartbeat({ interval: tempInterval });
    setShowIntervalInput(false);
  }, [heartbeat, tempInterval, updateHeartbeat]);

  if (!heartbeat) return null;

  const isActive = heartbeat.enabled;
  const displayTime = nextTickIn !== null ? fmtInterval(nextTickIn) : '--';

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        background: '#111',
        border: `1px solid ${isActive ? '#4ecdc4' : 'rgba(255,255,255,0.1)'}`,
        borderRadius: 12,
        padding: '4px 8px',
        fontSize: 10,
        fontFamily: 'monospace',
        color: '#ccc',
        cursor: 'pointer',
        position: 'relative',
        animation: isActive ? 'hb-pulse 1.5s infinite' : 'none',
      }}
      onClick={handleToggle}
      onContextMenu={(e) => {
        e.preventDefault();
        setShowIntervalInput(true);
      }}
    >
      {/* Status dot */}
      <div
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: isActive ? '#4ecdc4' : '#444',
        }}
      />

      {/* Label */}
      <span>{isActive ? `Heartbeat ${displayTime}` : 'Heartbeat off'}</span>

      {/* Interval popup */}
      {showIntervalInput && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: 4,
            padding: 8,
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
            minWidth: 120,
          }}
          onClick={e => e.stopPropagation()}
        >
          <div style={{ fontSize: 10, color: '#888' }}>Interval (seconds)</div>
          <input
            type="number"
            value={tempInterval}
            onChange={e => setTempInterval(Number(e.target.value))}
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid #333',
              borderRadius: 2,
              color: '#ccc',
              padding: '4px 6px',
              fontSize: 11,
              fontFamily: 'monospace',
            }}
          />
          <div style={{ display: 'flex', gap: 4 }}>
            <button
              onClick={handleIntervalSubmit}
              style={{
                flex: 1,
                background: '#2d3d5a',
                color: '#8af',
                border: 'none',
                borderRadius: 2,
                padding: '4px 0',
                fontSize: 10,
                cursor: 'pointer',
              }}
            >
              Set
            </button>
            <button
              onClick={() => setShowIntervalInput(false)}
              style={{
                flex: 1,
                background: 'transparent',
                color: '#888',
                border: '1px solid #333',
                borderRadius: 2,
                padding: '4px 0',
                fontSize: 10,
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes hb-pulse {
          0% { box-shadow: 0 0 0 0 rgba(78, 205, 196, 0.4); }
          70% { box-shadow: 0 0 0 4px rgba(78, 205, 196, 0); }
          100% { box-shadow: 0 0 0 0 rgba(78, 205, 196, 0); }
        }
      `}</style>
    </div>
  );
}
