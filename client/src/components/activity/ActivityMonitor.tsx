/**
 * ActivityMonitor - Real-time activity feed with filtering and Socket.IO integration
 * MARKER_108_5_ACTIVITY_UI
 *
 * @status active
 * @phase 108.4 Step 5
 * @depends react, socket.io-client
 * @used_by ChatPanel, Dashboard
 */

import { useState, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { getSocketUrl } from '../../config/api.config';
import './ActivityMonitor.css';

// MARKER_108_5_ACTIVITY_UI
interface Activity {
  id: string;
  type: 'chat' | 'mcp' | 'artifact' | 'commit';
  title: string;
  timestamp: string;
  details?: string;
  metadata?: Record<string, any>;
}

type ActivityFilter = 'all' | 'chat' | 'mcp' | 'artifact' | 'commit';

interface ActivityMonitorProps {
  className?: string;
  maxHeight?: string;
  limit?: number;
}

export function ActivityMonitor({
  className = '',
  maxHeight = '500px',
  limit = 50
}: ActivityMonitorProps) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [filter, setFilter] = useState<ActivityFilter>('all');
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const socketRef = useRef<Socket | null>(null);

  // Fetch initial activity feed
  useEffect(() => {
    const fetchActivities = async () => {
      try {
        const response = await fetch(`/api/activity/feed?limit=${limit}`);
        if (response.ok) {
          const data = await response.json();
          setActivities(data.activities || []);
          setHasMore(data.has_more || false);
        }
      } catch (error) {
        console.error('[ActivityMonitor] Failed to fetch activities:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchActivities();
  }, [limit]);

  // Socket.IO real-time updates
  useEffect(() => {
    const socket = io(getSocketUrl(), {
      transports: ['websocket', 'polling'],
      reconnection: true,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('[ActivityMonitor] Socket connected');
    });

    socket.on('activity_update', (newActivity: Activity) => {
      console.log('[ActivityMonitor] New activity:', newActivity.type, newActivity.title);
      setActivities(prev => [newActivity, ...prev].slice(0, limit));
    });

    socket.on('disconnect', () => {
      console.log('[ActivityMonitor] Socket disconnected');
    });

    return () => {
      socket.disconnect();
    };
  }, [limit]);

  // Load more activities
  const loadMore = async () => {
    if (!hasMore) return;

    try {
      const offset = activities.length;
      const response = await fetch(`/api/activity/feed?limit=${limit}&offset=${offset}`);
      if (response.ok) {
        const data = await response.json();
        setActivities(prev => [...prev, ...(data.activities || [])]);
        setHasMore(data.has_more || false);
      }
    } catch (error) {
      console.error('[ActivityMonitor] Failed to load more:', error);
    }
  };

  // Filter activities
  const filteredActivities = filter === 'all'
    ? activities
    : activities.filter(a => a.type === filter);

  // Format relative timestamp
  const formatRelativeTime = (timestamp: string): string => {
    const now = Date.now();
    const activityTime = new Date(timestamp).getTime();
    const diffMs = now - activityTime;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return new Date(timestamp).toLocaleDateString();
  };

  // Get icon based on activity type
  const getActivityIcon = (type: Activity['type']): string => {
    switch (type) {
      case 'chat': return '💬';
      case 'mcp': return '🔧';
      case 'artifact': return '📄';
      case 'commit': return '📝';
      default: return '•';
    }
  };

  // Toggle expanded details
  const toggleExpanded = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  if (loading) {
    return (
      <div className={`activity-monitor ${className}`}>
        <div className="activity-loading">Loading activity feed...</div>
      </div>
    );
  }

  return (
    <div className={`activity-monitor ${className}`}>
      {/* Header with filters */}
      <div className="activity-header">
        <h3 className="activity-title">Activity Feed</h3>
        <div className="activity-filters">
          <button
            className={`activity-filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={`activity-filter-btn ${filter === 'chat' ? 'active' : ''}`}
            onClick={() => setFilter('chat')}
          >
            💬
          </button>
          <button
            className={`activity-filter-btn ${filter === 'mcp' ? 'active' : ''}`}
            onClick={() => setFilter('mcp')}
          >
            🔧
          </button>
          <button
            className={`activity-filter-btn ${filter === 'artifact' ? 'active' : ''}`}
            onClick={() => setFilter('artifact')}
          >
            📄
          </button>
          <button
            className={`activity-filter-btn ${filter === 'commit' ? 'active' : ''}`}
            onClick={() => setFilter('commit')}
          >
            📝
          </button>
        </div>
      </div>

      {/* Activity list */}
      <div className="activity-list" style={{ maxHeight }}>
        {filteredActivities.length === 0 ? (
          <div className="activity-empty">No activities yet</div>
        ) : (
          filteredActivities.map((activity) => (
            <div
              key={activity.id}
              className={`activity-item activity-item-${activity.type}`}
              onClick={() => toggleExpanded(activity.id)}
            >
              <div className="activity-item-header">
                <span className="activity-item-icon">
                  {getActivityIcon(activity.type)}
                </span>
                <div className="activity-item-content">
                  <span className="activity-item-title">{activity.title}</span>
                  <span className="activity-item-time">
                    {formatRelativeTime(activity.timestamp)}
                  </span>
                </div>
              </div>

              {expandedId === activity.id && activity.details && (
                <div className="activity-item-details">
                  {activity.details}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Load more button */}
      {hasMore && filteredActivities.length > 0 && (
        <div className="activity-footer">
          <button className="activity-load-more" onClick={loadMore}>
            Load More
          </button>
        </div>
      )}
    </div>
  );
}
