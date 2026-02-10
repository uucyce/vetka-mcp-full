/**
 * MARKER_129.1A: WatcherStats — File watcher health monitoring.
 * Shows indexed files, skip patterns, event rate, recent events.
 * Nolan monochrome style — numbers + list, no charts.
 *
 * @status active
 * @phase 129.1
 * @depends react
 * @used_by DevPanel
 */

import { useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

interface WatcherEvent {
  path: string;
  type: string;
  time?: string;
  timestamp?: number;
}

interface WatcherStatsData {
  indexed_today: number;
  skip_patterns_count: number;
  skip_patterns: string[];
  events_last_5min: number;
  watched_dirs_count: number;
  recent_events: WatcherEvent[];
}

const API_BASE = 'http://localhost:5001/api/debug';

export function WatcherStats() {
  const [stats, setStats] = useState<WatcherStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPatterns, setShowPatterns] = useState(false);
  // MARKER_134.C34I: Activity history for sparkline
  const [activityHistory, setActivityHistory] = useState<{time: number; events: number}[]>([]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/watcher-stats`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setStats(data);
          setError(null);
          // MARKER_134.C34I: Track activity for sparkline
          setActivityHistory(prev => {
            const next = [...prev, { time: Date.now(), events: data.events_last_5min || 0 }];
            return next.slice(-20); // Keep last 20 samples
          });
        } else {
          setError(data.error || 'Failed to load stats');
        }
      } else {
        setError(`HTTP ${res.status}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on mount and every 10s
  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  if (loading && !stats) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: '#555',
        fontSize: 12,
        fontFamily: 'monospace',
      }}>
        Loading watcher stats...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: '#a66',
        fontSize: 12,
        fontFamily: 'monospace',
      }}>
        Error: {error}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      gap: 12,
    }}>
      {/* Stats Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: 8,
      }}>
        {/* Indexed Today */}
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          borderRadius: 4,
          padding: '12px 16px',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#e0e0e0', fontFamily: 'monospace' }}>
            {stats.indexed_today}
          </div>
          <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1 }}>
            indexed today
          </div>
        </div>

        {/* Events/5min */}
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          borderRadius: 4,
          padding: '12px 16px',
          textAlign: 'center',
        }}>
          <div style={{
            fontSize: 24,
            fontWeight: 700,
            color: stats.events_last_5min > 10 ? '#a88' : '#e0e0e0',
            fontFamily: 'monospace',
          }}>
            {stats.events_last_5min}
          </div>
          <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1 }}>
            events / 5min
          </div>
        </div>

        {/* Watched Dirs */}
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          borderRadius: 4,
          padding: '12px 16px',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#e0e0e0', fontFamily: 'monospace' }}>
            {stats.watched_dirs_count}
          </div>
          <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1 }}>
            watched dirs
          </div>
        </div>

        {/* Skip Patterns */}
        <div
          onClick={() => setShowPatterns(!showPatterns)}
          style={{
            background: 'rgba(255,255,255,0.03)',
            borderRadius: 4,
            padding: '12px 16px',
            textAlign: 'center',
            cursor: 'pointer',
          }}
        >
          <div style={{ fontSize: 24, fontWeight: 700, color: '#e0e0e0', fontFamily: 'monospace' }}>
            {stats.skip_patterns_count}
          </div>
          <div style={{ fontSize: 9, color: '#555', textTransform: 'uppercase', letterSpacing: 1 }}>
            skip patterns {showPatterns ? '▾' : '▸'}
          </div>
        </div>
      </div>

      {/* MARKER_134.C34I: Activity Sparkline */}
      {activityHistory.length > 1 && (
        <div style={{
          height: 40,
          background: 'rgba(255,255,255,0.02)',
          borderRadius: 3,
          padding: '4px 0',
        }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={activityHistory} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
              <Area
                type="monotone"
                dataKey="events"
                stroke="#555"
                fill="rgba(224,224,224,0.1)"
                strokeWidth={1}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Skip Patterns List (collapsible) */}
      {showPatterns && (
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          borderRadius: 3,
          padding: 8,
          fontSize: 10,
          fontFamily: 'monospace',
          color: '#666',
          maxHeight: 100,
          overflowY: 'auto',
        }}>
          {stats.skip_patterns.map((pattern, idx) => (
            <span key={idx} style={{ marginRight: 8 }}>{pattern}</span>
          ))}
        </div>
      )}

      {/* Recent Events */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{
          fontSize: 9,
          color: '#555',
          textTransform: 'uppercase',
          letterSpacing: 1,
          marginBottom: 6,
        }}>
          recent events
        </div>

        <div style={{
          flex: 1,
          overflowY: 'auto',
          background: '#111',
          borderRadius: 3,
          padding: 6,
        }}>
          {stats.recent_events.length === 0 ? (
            <div style={{ color: '#444', fontSize: 11, textAlign: 'center', padding: 12 }}>
              No recent events
            </div>
          ) : (
            stats.recent_events.map((evt, idx) => (
              <div
                key={idx}
                onClick={() => {
                  // MARKER_134.C34I: Click to focus camera on file
                  fetch('http://localhost:5001/api/debug/camera-focus', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: evt.path, zoom: 'medium', highlight: true }),
                  }).catch(() => {});
                }}
                style={{
                  display: 'flex',
                  gap: 8,
                  padding: '4px 0',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                  fontSize: 10,
                  fontFamily: 'monospace',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <span style={{
                  color: evt.type === 'modified' ? '#888'
                    : evt.type === 'created' ? '#8a8'
                    : evt.type === 'deleted' ? '#a88'
                    : '#666',
                  width: 50,
                  flexShrink: 0,
                }}>
                  {evt.type}
                </span>
                <span style={{
                  color: '#aaa',
                  flex: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {evt.path.split('/').pop()}
                </span>
                {evt.time && (
                  <span style={{ color: '#444', flexShrink: 0 }}>
                    {evt.time}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
