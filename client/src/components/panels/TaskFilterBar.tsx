/**
 * MARKER_152.8: Task filter/search/sort controls for MCC task board.
 */
import type { TaskSortKey } from '../../store/useDevPanelStore';

export interface TaskFiltersValue {
  source: string;
  statuses: string[];
  preset: string;
  query: string;
  dateFrom: string;
  dateTo: string;
  sortBy: TaskSortKey;
  showCompleted: boolean;
}

interface TaskFilterBarProps {
  value: TaskFiltersValue;
  sources: string[];
  presets: string[];
  onChange: (updates: Partial<TaskFiltersValue>) => void;
}

const STATUSES = ['pending', 'queued', 'running', 'done', 'failed', 'hold'] as const;

export function TaskFilterBar({ value, sources, presets, onChange }: TaskFilterBarProps) {
  return (
    <div
      style={{
        borderBottom: '1px solid #222',
        padding: '6px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: 5,
        background: '#0b0b0b',
      }}
    >
      <div style={{ display: 'flex', gap: 4 }}>
        <input
          value={value.query}
          onChange={(e) => onChange({ query: e.target.value })}
          placeholder="search title/description..."
          style={{
            flex: 1,
            minWidth: 0,
            background: '#111',
            border: '1px solid #333',
            borderRadius: 2,
            color: '#ddd',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '4px 6px',
            outline: 'none',
          }}
        />
        <select
          value={value.sortBy}
          onChange={(e) => onChange({ sortBy: e.target.value as TaskSortKey })}
          style={{
            width: 92,
            background: '#111',
            border: '1px solid #333',
            borderRadius: 2,
            color: '#bbb',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '4px 5px',
          }}
          title="Sort tasks by"
        >
          <option value="priority">priority</option>
          <option value="created_at">date</option>
          <option value="duration_s">duration</option>
          <option value="success_rate">success</option>
        </select>
      </div>

      <div style={{ display: 'flex', gap: 4 }}>
        <select
          value={value.source}
          onChange={(e) => onChange({ source: e.target.value })}
          style={{
            flex: 1,
            minWidth: 0,
            background: '#111',
            border: '1px solid #333',
            borderRadius: 2,
            color: '#bbb',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '3px 5px',
          }}
          title="Filter by task source"
        >
          <option value="all">source: all</option>
          {sources.map((source) => (
            <option key={source} value={source}>
              {source}
            </option>
          ))}
        </select>

        <select
          value={value.preset}
          onChange={(e) => onChange({ preset: e.target.value })}
          style={{
            flex: 1,
            minWidth: 0,
            background: '#111',
            border: '1px solid #333',
            borderRadius: 2,
            color: '#bbb',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '3px 5px',
          }}
          title="Filter by preset/team"
        >
          <option value="all">preset: all</option>
          {presets.map((preset) => (
            <option key={preset} value={preset}>
              {preset}
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        {STATUSES.map((status) => {
          const active = value.statuses.includes(status);
          return (
            <button
              key={status}
              onClick={() => {
                const next = active
                  ? value.statuses.filter((s) => s !== status)
                  : [...value.statuses, status];
                onChange({ statuses: next });
              }}
              style={{
                padding: '2px 5px',
                background: active ? 'rgba(255,255,255,0.08)' : 'transparent',
                border: `1px solid ${active ? '#4ecdc4' : '#333'}`,
                borderRadius: 2,
                color: active ? '#c6ffff' : '#666',
                fontSize: 8,
                fontFamily: 'monospace',
                cursor: 'pointer',
              }}
              title={`Filter status: ${status}`}
            >
              {status}
            </button>
          );
        })}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#888', fontSize: 9, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={value.showCompleted}
            onChange={(e) => onChange({ showCompleted: e.target.checked })}
          />
          show completed
        </label>

        <input
          type="date"
          value={value.dateFrom}
          onChange={(e) => onChange({ dateFrom: e.target.value })}
          style={{
            background: '#111',
            border: '1px solid #333',
            borderRadius: 2,
            color: '#888',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '2px 4px',
          }}
          title="Created from date"
        />
        <input
          type="date"
          value={value.dateTo}
          onChange={(e) => onChange({ dateTo: e.target.value })}
          style={{
            background: '#111',
            border: '1px solid #333',
            borderRadius: 2,
            color: '#888',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '2px 4px',
          }}
          title="Created to date"
        />
      </div>
    </div>
  );
}
