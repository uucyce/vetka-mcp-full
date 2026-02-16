import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useMCCStore } from '../../store/useMCCStore';
import { create } from 'zustand';

// Heartbeat state interface
interface HeartbeatState {
  enabled: boolean;
  interval: number; // in seconds
  last_tick: number | null; // timestamp in seconds
  tasks_dispatched: number;
  tasks_failed: number;
}

// Heartbeat store interface
interface HeartbeatStore {
  heartbeat: HeartbeatState | null;
  updateHeartbeat: (updates: Partial<HeartbeatState>) => void;
  resetHeartbeat: () => void;
}

// Create the heartbeat store
const useHeartbeatStore = create<HeartbeatStore>((set) => ({
  heartbeat: null,
  
  updateHeartbeat: (updates) => set((state) => {
    if (!state.heartbeat) return state;
    return {
      heartbeat: {
        ...state.heartbeat,
        ...updates
      }
    };
  }),
  
  resetHeartbeat: () => set({
    heartbeat: {
      enabled: false,
      interval: 300, // 5 minutes default
      last_tick: null,
      tasks_dispatched: 0,
      tasks_failed: 0
    }
  })
}));

// Format interval helper
function fmtInterval(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

export function HeartbeatChip() {
  const { heartbeat, updateHeartbeat } = useMCCStore();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [nextTickIn, setNextTickIn] = useState<number | null>(null);
  const [customMinutes, setCustomMinutes] = useState('');

  const PRESETS = useMemo(() => ([
    { label: '10 min', value: 600 },
    { label: '30 min', value: 1800 },
    { label: '1 hour', value: 3600 },
    { label: '4 hours', value: 14400 },
    { label: '12 hours', value: 43200 },
    { label: '1 day', value: 86400 },
    { label: '1 week', value: 604800 },
  ]), []);

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

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const toggleHeartbeat = useCallback(async () => {
    if (!heartbeat) return;
    await updateHeartbeat({ enabled: !heartbeat.enabled });
  }, [heartbeat, updateHeartbeat]);

  const selectPreset = useCallback(async (seconds: number) => {
    await updateHeartbeat({ interval: seconds });
  }, [updateHeartbeat]);

  const applyCustom = useCallback(async () => {
    const mins = parseInt(customMinutes, 10);
    if (!Number.isFinite(mins) || mins <= 0) return;
    await updateHeartbeat({ interval: mins * 60 });
    setCustomMinutes('');
  }, [customMinutes, updateHeartbeat]);

  if (!heartbeat) return null;

  const isActive = heartbeat.enabled;
  const displayTime = isActive ? (nextTickIn !== null ? fmtInterval(nextTickIn) : '--') : 'Heartbeat off';
  const selectedPreset = PRESETS.find(p => p.value === heartbeat.interval) || null;
  const nextTickTs = heartbeat.last_tick ? (heartbeat.last_tick + heartbeat.interval) * 1000 : null;
  const nextTickLabel = nextTickTs ? new Date(nextTickTs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--';
  const remainingLabel = nextTickIn !== null ? `${Math.max(0, Math.round(nextTickIn / 60))}m remaining` : '--';

  return (
    <div
      ref={dropdownRef}
      style={{
        display: 'inline-flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        position: 'relative',
      }}
    >
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: '#111',
          border: `1px solid ${open ? '#4ecdc4' : (isActive ? '#4ecdc460' : 'rgba(255,255,255,0.1)')}`,
          borderRadius: 12,
          padding: '4px 8px',
          fontSize: 10,
          fontFamily: 'monospace',
          color: '#ccc',
          cursor: 'pointer',
          animation: isActive ? 'hb-pulse 1.5s infinite' : 'none',
        }}
        title="Heartbeat settings"
      >
        <span style={{ width: 10, textAlign: 'center' }}>&#x23f1;</span>
        <span>{isActive ? displayTime : 'Heartbeat off'}</span>
        <span style={{ color: '#777' }}>&#x25be;</span>
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: 6,
            zIndex: 1000,
            width: 220,
            fontFamily: 'monospace',
            fontSize: 10,
            color: '#ccc',
            overflow: 'hidden',
          }}
        >
          <button
            onClick={toggleHeartbeat}
            style={{
              width: '100%',
              textAlign: 'left',
              background: 'transparent',
              border: 'none',
              borderBottom: '1px solid #2a2a2a',
              color: '#ddd',
              padding: '8px 10px',
              fontFamily: 'monospace',
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            {isActive ? '\u25cf Pause' : '\u25cf Start'}
          </button>

          <div style={{ padding: '6px 8px' }}>
            {PRESETS.map((preset) => {
              const selected = heartbeat.interval === preset.value;
              return (
                <button
                  key={preset.value}
                  onClick={() => selectPreset(preset.value)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    background: 'transparent',
                    border: 'none',
                    color: selected ? '#e8f8f6' : '#bbb',
                    padding: '4px 2px',
                    fontFamily: 'monospace',
                    fontSize: 10,
                    cursor: 'pointer',
                  }}
                >
                  <span style={{ color: selected ? '#4ecdc4' : '#666' }}>{selected ? '\u25cf' : '\u25cb'}</span>
                  <span>{preset.label}</span>
                </button>
              );
            })}
          </div>

          <div
            style={{
              borderTop: '1px solid #2a2a2a',
              padding: '8px 10px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span style={{ color: '#888' }}>Custom:</span>
            <input
              type="number"
              min={1}
              value={customMinutes}
              onChange={(e) => setCustomMinutes(e.target.value)}
              style={{
                width: 56,
                background: '#111',
                border: '1px solid #333',
                borderRadius: 3,
                color: '#ddd',
                padding: '3px 5px',
                fontSize: 10,
                fontFamily: 'monospace',
              }}
            />
            <span style={{ color: '#888' }}>min</span>
            <button
              onClick={applyCustom}
              style={{
                marginLeft: 'auto',
                background: '#222',
                border: '1px solid #3a3a3a',
                color: '#ddd',
                borderRadius: 3,
                padding: '3px 8px',
                fontSize: 10,
                fontFamily: 'monospace',
                cursor: 'pointer',
              }}
            >
              Set
            </button>
          </div>

          <div
            style={{
              borderTop: '1px solid #2a2a2a',
              padding: '8px 10px',
              color: '#8d8d8d',
              fontSize: 9,
              lineHeight: 1.5,
            }}
          >
            <div>Next: {nextTickLabel} ({remainingLabel})</div>
            <div>
              Dispatched: {heartbeat.tasks_dispatched ?? 0}
              {' | '}
              Last: {heartbeat.last_tick ? 'OK' : '--'}
              {selectedPreset ? ` | ${selectedPreset.label}` : ''}
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes hb-pulse {
          0% { opacity: 0.6; }
          50% { opacity: 1; }
          100% { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
}