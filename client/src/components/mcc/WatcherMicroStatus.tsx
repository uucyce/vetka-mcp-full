/**
 * MARKER_143.P5: WatcherMicroStatus — tiny inline watcher health indicator.
 * Replaces the full Watcher tab with a compact status in MCC header.
 * Shows: dot + indexed count + events/5min. Click to expand popover.
 *
 * @phase 143
 * @status active
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = 'http://localhost:5001/api/debug';

interface WatcherData {
  indexed_today: number;
  events_last_5min: number;
  watched_dirs_count: number;
}

export function WatcherMicroStatus() {
  const [data, setData] = useState<WatcherData | null>(null);
  const [expanded, setExpanded] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/watcher-stats`);
      if (res.ok) {
        const json = await res.json();
        if (json.success) {
          setData({
            indexed_today: json.indexed_today || 0,
            events_last_5min: json.events_last_5min || 0,
            watched_dirs_count: json.watched_dirs_count || 0,
          });
        }
      }
    } catch { /* silent */ }
  }, []);

  // MARKER_145.CLEANUP: Fetch on mount only — no polling.
  // Was 30s. This is a tiny status indicator, no real-time need.
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Close popover on click outside
  useEffect(() => {
    if (!expanded) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setExpanded(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [expanded]);

  if (!data) return null;

  const healthy = data.events_last_5min < 50;

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          cursor: 'pointer',
          fontSize: 9,
          fontFamily: 'monospace',
          color: '#666',
          padding: '2px 4px',
          borderRadius: 2,
          background: expanded ? 'rgba(255,255,255,0.04)' : 'transparent',
        }}
        title={`Watcher: ${data.indexed_today} indexed, ${data.events_last_5min} events/5min, ${data.watched_dirs_count} dirs`}
      >
        <span style={{
          width: 5, height: 5, borderRadius: '50%',
          background: healthy ? '#6a6' : '#a66',
        }} />
        <span>{data.indexed_today > 999 ? `${(data.indexed_today / 1000).toFixed(1)}k` : data.indexed_today}</span>
        <span style={{ color: '#444' }}>·</span>
        <span style={{ color: data.events_last_5min > 10 ? '#a88' : '#666' }}>
          {data.events_last_5min}ev
        </span>
      </div>

      {/* Popover */}
      {expanded && (
        <div style={{
          position: 'absolute',
          top: '100%',
          right: 0,
          marginTop: 4,
          width: 180,
          background: '#111',
          border: '1px solid #333',
          borderRadius: 4,
          padding: 10,
          zIndex: 1000,
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          fontFamily: 'monospace',
          fontSize: 10,
        }}>
          <div style={{ color: '#888', fontSize: 8, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
            watcher health
          </div>
          {[
            { label: 'Indexed today', value: data.indexed_today },
            { label: 'Events / 5min', value: data.events_last_5min },
            { label: 'Watched dirs', value: data.watched_dirs_count },
          ].map(({ label, value }) => (
            <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
              <span style={{ color: '#888' }}>{label}</span>
              <span style={{ color: '#ccc' }}>{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
