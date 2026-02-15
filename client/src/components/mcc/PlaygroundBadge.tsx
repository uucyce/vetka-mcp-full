import { useState, useEffect, useCallback } from 'react';

interface PlaygroundInfo {
  playground_id: string;
  branch: string;
  status: string;
  pipeline_runs: number;
  files_created: number;
  age_minutes: number;
  task?: string;
}

function fmtAge(minutes: number): string {
  if (minutes < 1) return '<1m';
  if (minutes < 60) return `${Math.round(minutes)}m`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h`;
  return `${Math.floor(minutes / 1440)}d`;
}

const API_DEBUG = 'http://localhost:5001/api/debug';

export function PlaygroundBadge() {
  const [playgrounds, setPlaygrounds] = useState<PlaygroundInfo[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchPlaygrounds = useCallback(async () => {
    try {
      const res = await fetch(`${API_DEBUG}/playground`);
      if (!res.ok) return;
      const data = await res.json();
      setPlaygrounds(data.playgrounds || []);
    } catch {
      // silently fail
    }
  }, []);

  // Initial fetch + periodic refresh
  useEffect(() => {
    fetchPlaygrounds();
    const timer = setInterval(fetchPlaygrounds, 15000);
    return () => clearInterval(timer);
  }, [fetchPlaygrounds]);

  const handleDestroy = useCallback(async (pgId: string) => {
    setLoading(true);
    try {
      await fetch(`${API_DEBUG}/playground/${pgId}`, { method: 'DELETE' });
      await fetchPlaygrounds();
    } catch {
      // silently fail
    }
    setLoading(false);
  }, [fetchPlaygrounds]);

  const activeCount = playgrounds.filter(p => p.status === 'active').length;
  const hasActive = activeCount > 0;

  return (
    <div style={{ position: 'relative' }}>
      <div
        onClick={() => setShowDropdown(!showDropdown)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: '#111',
          border: `1px solid ${hasActive ? '#4ecdc4' : 'rgba(255,255,255,0.1)'}`,
          borderRadius: 12,
          padding: '4px 8px',
          fontSize: 10,
          fontFamily: 'monospace',
          color: '#ccc',
          cursor: 'pointer',
        }}
      >
        {/* Status dot */}
        <div
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: hasActive ? '#4ecdc4' : '#444',
          }}
        />
        <span>PG {activeCount}</span>
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: 4,
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: 4,
            padding: 6,
            zIndex: 1000,
            minWidth: 220,
            maxHeight: 300,
            overflowY: 'auto',
          }}
          onClick={e => e.stopPropagation()}
        >
          {playgrounds.length === 0 ? (
            <div style={{ color: '#666', fontSize: 10, fontFamily: 'monospace', padding: 4 }}>
              No playgrounds
            </div>
          ) : (
            playgrounds.map(pg => (
              <div
                key={pg.playground_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '4px 6px',
                  borderRadius: 3,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  color: '#ccc',
                }}
              >
                {/* Status dot */}
                <div
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: pg.status === 'active' ? '#4ecdc4' : '#666',
                    flexShrink: 0,
                  }}
                />

                {/* Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <span style={{ color: '#e0e0e0' }}>{pg.playground_id.slice(0, 12)}</span>
                    <span style={{ color: '#666' }}>{fmtAge(pg.age_minutes)} ago</span>
                  </div>
                  {pg.task && (
                    <div style={{
                      color: '#888',
                      fontSize: 9,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: 160,
                    }}>
                      {pg.task}
                    </div>
                  )}
                </div>

                {/* Destroy button */}
                <button
                  onClick={() => handleDestroy(pg.playground_id)}
                  disabled={loading}
                  style={{
                    background: 'transparent',
                    border: '1px solid #333',
                    borderRadius: 2,
                    color: '#a66',
                    fontSize: 9,
                    fontFamily: 'monospace',
                    padding: '2px 6px',
                    cursor: loading ? 'wait' : 'pointer',
                    flexShrink: 0,
                  }}
                >
                  {loading ? '...' : '✕'}
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
