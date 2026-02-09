/**
 * MARKER_127.2A: ActivityLog — Real-time pipeline activity monitor.
 * MARKER_128.6A: Activity message parser (tool calls, verifier, etc.)
 * MARKER_128.6B: Rich formatting (icons, badges, progress bars)
 * MARKER_128.6C: Per-task grouping with collapsible sections
 *
 * @status active
 * @phase 128.6
 * @depends react
 * @used_by DevPanel
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

interface LogEntry {
  id: string;
  timestamp: number;
  role: string;
  model: string;
  message: string;
  subtask_idx: number;
  total: number;
  task_id?: string;
  preset?: string;
}

// MARKER_128.6A: Parsed message structure
interface ParsedMessage {
  type: 'tool_call' | 'verifier' | 'file_create' | 'retry' | 'progress' | 'error' | 'text';
  icon: string;
  content: string;
  filePath?: string;
  confidence?: number;
  passed?: boolean;
}

// MARKER_128.6B: Role definitions with icons
const ROLE_ICONS: Record<string, { icon: string; color: string }> = {
  '@scout': { icon: '🔍', color: '#8888cc' },
  '@researcher': { icon: '🔍', color: '#8888cc' },
  '@coder': { icon: '💻', color: '#88cc88' },
  '@verifier': { icon: '✓', color: '#cccc88' },
  '@architect': { icon: '📐', color: '#cc88cc' },
  '@system': { icon: '▸', color: '#888888' },
  '@unknown': { icon: '·', color: '#666666' },
};

const MAX_ENTRIES = 100;

// MARKER_128.6A: Parse message for known patterns
function parseMessage(message: string): ParsedMessage {
  if (!message) return { type: 'text', icon: '', content: '' };

  // Tool call: 📖 vetka_read_file: path/to/file
  if (message.includes('📖')) {
    const match = message.match(/📖\s*(?:vetka_read_file:\s*)?(.+)/);
    return {
      type: 'tool_call',
      icon: '📖',
      content: 'read',
      filePath: match?.[1]?.trim() || message,
    };
  }

  // File search: 🔍 vetka_search_files
  if (message.includes('🔍')) {
    return { type: 'tool_call', icon: '🔍', content: message.replace('🔍', '').trim() };
  }

  // File created: 📁
  if (message.includes('📁')) {
    const match = message.match(/📁\s*(?:Created:?\s*)?(.+)/);
    return {
      type: 'file_create',
      icon: '📁',
      content: 'created',
      filePath: match?.[1]?.trim(),
    };
  }

  // Verifier passed: ✅
  if (message.includes('✅')) {
    const confMatch = message.match(/(\d+(?:\.\d+)?)\s*%?/);
    return {
      type: 'verifier',
      icon: '✅',
      content: message.replace('✅', '').trim(),
      passed: true,
      confidence: confMatch ? parseFloat(confMatch[1]) / (confMatch[1].includes('.') ? 1 : 100) : undefined,
    };
  }

  // Verifier failed: ❌
  if (message.includes('❌')) {
    const confMatch = message.match(/(\d+(?:\.\d+)?)\s*%?/);
    return {
      type: 'verifier',
      icon: '❌',
      content: message.replace('❌', '').trim(),
      passed: false,
      confidence: confMatch ? parseFloat(confMatch[1]) / (confMatch[1].includes('.') ? 1 : 100) : undefined,
    };
  }

  // Retry/recovery: 🔄
  if (message.includes('🔄')) {
    return { type: 'retry', icon: '🔄', content: message.replace('🔄', '').trim() };
  }

  // Error
  if (message.toLowerCase().includes('error') || message.toLowerCase().includes('failed')) {
    return { type: 'error', icon: '⚠', content: message };
  }

  // Default text
  return { type: 'text', icon: '', content: message };
}

// Format timestamp as HH:MM:SS
function formatTime(ts: number): string {
  const date = new Date(ts * 1000);
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

// MARKER_128.6C: Group entries by task_id
interface TaskGroup {
  task_id: string;
  preset?: string;
  entries: LogEntry[];
  isRunning: boolean;
  latestTimestamp: number;
}

function groupByTask(entries: LogEntry[]): TaskGroup[] {
  const groups: Map<string, TaskGroup> = new Map();
  const ungrouped: LogEntry[] = [];

  for (const entry of entries) {
    const taskId = entry.task_id || 'ungrouped';
    if (taskId === 'ungrouped') {
      ungrouped.push(entry);
      continue;
    }

    if (!groups.has(taskId)) {
      groups.set(taskId, {
        task_id: taskId,
        preset: entry.preset,
        entries: [],
        isRunning: false,
        latestTimestamp: entry.timestamp,
      });
    }
    const group = groups.get(taskId)!;
    group.entries.push(entry);
    if (entry.timestamp > group.latestTimestamp) {
      group.latestTimestamp = entry.timestamp;
    }
    // Check if still running (has progress events in last 30s)
    if (Date.now() / 1000 - entry.timestamp < 30) {
      group.isRunning = true;
    }
  }

  // Sort groups by latest timestamp (newest first)
  const sortedGroups = Array.from(groups.values()).sort((a, b) => b.latestTimestamp - a.latestTimestamp);

  // Add ungrouped if any
  if (ungrouped.length > 0) {
    sortedGroups.push({
      task_id: 'ungrouped',
      entries: ungrouped,
      isRunning: false,
      latestTimestamp: ungrouped[0]?.timestamp || 0,
    });
  }

  return sortedGroups;
}

// MARKER_128.6B: Mini progress bar component
function MiniProgressBar({ current, total }: { current: number; total: number }) {
  const pct = total > 0 ? (current / total) * 100 : 0;
  return (
    <div style={{
      width: 40,
      height: 3,
      background: 'rgba(255,255,255,0.1)',
      borderRadius: 2,
      overflow: 'hidden',
      flexShrink: 0,
    }}>
      <div style={{
        width: `${pct}%`,
        height: '100%',
        background: '#e0e0e0',
        transition: 'width 0.2s',
      }} />
    </div>
  );
}

// MARKER_128.6B: Confidence bar for verifier
function ConfidenceBar({ confidence, passed }: { confidence: number; passed: boolean }) {
  const color = passed ? '#4a8a4a' : '#8a4a4a';
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 4,
    }}>
      <div style={{
        width: 30,
        height: 4,
        background: 'rgba(255,255,255,0.1)',
        borderRadius: 2,
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${confidence * 100}%`,
          height: '100%',
          background: color,
        }} />
      </div>
      <span style={{ color: '#666', fontSize: 9 }}>{Math.round(confidence * 100)}%</span>
    </div>
  );
}

export function ActivityLog() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [followTail, setFollowTail] = useState(true);
  const [groupByTaskEnabled, setGroupByTaskEnabled] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  // MARKER_127.2A: Listen for pipeline-activity CustomEvent
  useEffect(() => {
    const handleActivity = (e: CustomEvent) => {
      const detail = e.detail;
      if (!detail) return;

      const entry: LogEntry = {
        id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        timestamp: detail.timestamp || Date.now() / 1000,
        role: detail.role || '@unknown',
        model: detail.model || '',
        message: detail.message || '',
        subtask_idx: detail.subtask_idx || 0,
        total: detail.total || 0,
        task_id: detail.task_id,
        preset: detail.preset,
      };

      setEntries(prev => {
        const next = [entry, ...prev];  // Newest on top
        return next.slice(0, MAX_ENTRIES);  // Ring buffer
      });
    };

    window.addEventListener('pipeline-activity', handleActivity as EventListener);
    return () => {
      window.removeEventListener('pipeline-activity', handleActivity as EventListener);
    };
  }, []);

  // Auto-scroll to top (newest) when followTail is enabled
  useEffect(() => {
    if (followTail && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [entries, followTail]);

  const handleClear = useCallback(() => {
    setEntries([]);
  }, []);

  const toggleGroupCollapse = useCallback((taskId: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  }, []);

  // MARKER_128.6C: Group entries if enabled
  const taskGroups = useMemo(() => {
    if (!groupByTaskEnabled) return null;
    return groupByTask(entries);
  }, [entries, groupByTaskEnabled]);

  // Render a single log entry with rich formatting
  const renderEntry = (entry: LogEntry) => {
    const roleInfo = ROLE_ICONS[entry.role] || ROLE_ICONS['@unknown'];
    const parsed = parseMessage(entry.message);

    return (
      <div
        key={entry.id}
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 6,
          padding: '4px 6px',
          borderBottom: '1px solid rgba(255,255,255,0.03)',
          fontSize: 10,
          fontFamily: 'monospace',
          lineHeight: 1.4,
          // MARKER_128.6B: Type-based background
          background: parsed.type === 'tool_call' ? '#1a1a1a'
            : parsed.type === 'error' ? 'rgba(100,40,40,0.2)'
            : parsed.type === 'verifier' ? (parsed.passed ? 'rgba(40,80,40,0.15)' : 'rgba(80,40,40,0.15)')
            : 'transparent',
        }}
      >
        {/* Timestamp */}
        <span style={{ color: '#444', flexShrink: 0, fontSize: 9 }}>
          {formatTime(entry.timestamp)}
        </span>

        {/* MARKER_128.6B: Role icon */}
        <span style={{ color: roleInfo.color, flexShrink: 0, width: 14, textAlign: 'center' }}>
          {roleInfo.icon}
        </span>

        {/* Progress bar */}
        {entry.total > 0 && (
          <MiniProgressBar current={entry.subtask_idx} total={entry.total} />
        )}

        {/* MARKER_128.6B: Rich message content */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {parsed.type === 'tool_call' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ color: '#666' }}>{parsed.icon}</span>
              <span style={{ color: '#888' }}>{parsed.content}</span>
              {parsed.filePath && (
                <span style={{
                  color: '#666',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: 200,
                }}>
                  {parsed.filePath}
                </span>
              )}
            </div>
          )}

          {parsed.type === 'file_create' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ color: '#8a8' }}>{parsed.icon}</span>
              <span style={{ color: '#8a8' }}>{parsed.content}</span>
              {parsed.filePath && (
                <span style={{ color: '#6a6' }}>{parsed.filePath}</span>
              )}
            </div>
          )}

          {parsed.type === 'verifier' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: parsed.passed ? '#8a8' : '#a88' }}>
                {parsed.passed ? '✓' : '✕'}
              </span>
              <span style={{ color: parsed.passed ? '#8a8' : '#a88' }}>
                {parsed.passed ? 'passed' : 'failed'}
              </span>
              {parsed.confidence !== undefined && (
                <ConfidenceBar confidence={parsed.confidence} passed={parsed.passed!} />
              )}
            </div>
          )}

          {parsed.type === 'retry' && (
            <span style={{ color: '#aa8' }}>
              ↺ {parsed.content}
            </span>
          )}

          {parsed.type === 'error' && (
            <span style={{ color: '#a66' }}>
              {parsed.content}
            </span>
          )}

          {parsed.type === 'text' && (
            <span style={{
              color: '#bbb',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              display: 'block',
            }}>
              {parsed.content}
            </span>
          )}
        </div>

        {/* Model (compact) */}
        {entry.model && entry.model !== 'system' && (
          <span style={{ color: '#444', flexShrink: 0, fontSize: 9 }}>
            {entry.model.split('/').pop()?.slice(0, 8)}
          </span>
        )}
      </div>
    );
  };

  if (entries.length === 0) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}>
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#555',
          fontSize: 12,
          fontFamily: 'monospace',
        }}>
          No pipeline activity yet.
        </div>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
        paddingBottom: 8,
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{
          color: '#666',
          fontSize: 9,
          fontFamily: 'monospace',
          letterSpacing: 0.5,
          textTransform: 'uppercase',
        }}>
          {entries.length} events
        </div>

        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          {/* MARKER_128.6C: Group toggle */}
          <button
            onClick={() => setGroupByTaskEnabled(!groupByTaskEnabled)}
            style={{
              background: groupByTaskEnabled ? 'rgba(255,255,255,0.08)' : 'transparent',
              color: groupByTaskEnabled ? '#e0e0e0' : '#444',
              border: `1px solid ${groupByTaskEnabled ? '#333' : '#222'}`,
              borderRadius: 2,
              padding: '3px 8px',
              fontSize: 9,
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            group
          </button>

          {/* Follow toggle */}
          <button
            onClick={() => setFollowTail(!followTail)}
            style={{
              background: followTail ? 'rgba(255,255,255,0.08)' : 'transparent',
              color: followTail ? '#e0e0e0' : '#444',
              border: `1px solid ${followTail ? '#333' : '#222'}`,
              borderRadius: 2,
              padding: '3px 8px',
              fontSize: 9,
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {followTail ? 'tail' : 'paused'}
          </button>

          {/* Clear button */}
          <button
            onClick={handleClear}
            style={{
              background: 'transparent',
              color: '#444',
              border: '1px solid #222',
              borderRadius: 2,
              padding: '3px 8px',
              fontSize: 9,
              fontFamily: 'monospace',
              cursor: 'pointer',
              transition: 'color 0.15s',
            }}
          >
            clear
          </button>
        </div>
      </div>

      {/* Log entries */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          minHeight: 0,
          background: '#111',
          borderRadius: 3,
        }}
      >
        {/* MARKER_128.6C: Grouped view */}
        {groupByTaskEnabled && taskGroups ? (
          taskGroups.map(group => (
            <div key={group.task_id} style={{ marginBottom: 2 }}>
              {/* Group header */}
              <div
                onClick={() => toggleGroupCollapse(group.task_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '6px 8px',
                  background: group.isRunning ? 'rgba(224,224,224,0.05)' : 'rgba(255,255,255,0.02)',
                  cursor: 'pointer',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                }}
              >
                <span style={{ color: '#666', fontSize: 10 }}>
                  {collapsedGroups.has(group.task_id) ? '▸' : '▾'}
                </span>
                {group.isRunning && (
                  <span style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: '#e0e0e0',
                    animation: 'taskPulse 1.5s ease-in-out infinite',
                  }} />
                )}
                <span style={{ color: '#888', fontSize: 10, fontFamily: 'monospace', flex: 1 }}>
                  {group.task_id === 'ungrouped' ? 'Other events' : group.task_id.slice(0, 20)}
                </span>
                {group.preset && (
                  <span style={{ color: '#555', fontSize: 9 }}>{group.preset}</span>
                )}
                <span style={{ color: '#444', fontSize: 9 }}>
                  {group.entries.length}
                </span>
              </div>
              {/* Group entries */}
              {!collapsedGroups.has(group.task_id) && (
                <div>
                  {group.entries.map(renderEntry)}
                </div>
              )}
            </div>
          ))
        ) : (
          // Flat view
          entries.map(renderEntry)
        )}
      </div>

      {/* Footer: current preset if active */}
      {entries[0]?.preset && (
        <div style={{
          marginTop: 6,
          padding: '4px 8px',
          background: 'rgba(255,255,255,0.02)',
          borderRadius: 2,
          fontSize: 9,
          fontFamily: 'monospace',
          color: '#555',
        }}>
          preset: {entries[0].preset}
        </div>
      )}
    </div>
  );
}
