/**
 * MARKER_135.5A: Filter Bar — status, time, and type filters.
 *
 * @phase 135.1
 * @status active
 */

import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGFilters, NodeStatus, DAGNodeType } from '../../types/dag';

interface FilterBarProps {
  filters: DAGFilters;
  onChange: (filters: DAGFilters) => void;
}

const STATUS_OPTIONS: Array<NodeStatus | 'all'> = ['all', 'pending', 'running', 'done', 'failed'];
const TIME_OPTIONS: Array<DAGFilters['timeRange']> = ['1h', '6h', '24h', 'all'];
const TYPE_OPTIONS: Array<DAGNodeType | 'all'> = ['all', 'task', 'agent', 'subtask', 'proposal'];

export function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '6px 12px',
        borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
        background: NOLAN_PALETTE.bgDim,
      }}
    >
      {/* Status filter */}
      <FilterGroup label="Status">
        {STATUS_OPTIONS.map((status) => (
          <FilterButton
            key={status}
            active={filters.status === status}
            onClick={() => onChange({ ...filters, status })}
          >
            {status}
          </FilterButton>
        ))}
      </FilterGroup>

      {/* Time filter */}
      <FilterGroup label="Time">
        {TIME_OPTIONS.map((time) => (
          <FilterButton
            key={time}
            active={filters.timeRange === time}
            onClick={() => onChange({ ...filters, timeRange: time })}
          >
            {time}
          </FilterButton>
        ))}
      </FilterGroup>

      {/* Type filter */}
      <FilterGroup label="Type">
        {TYPE_OPTIONS.map((type) => (
          <FilterButton
            key={type}
            active={filters.type === type}
            onClick={() => onChange({ ...filters, type })}
          >
            {type}
          </FilterButton>
        ))}
      </FilterGroup>
    </div>
  );
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span
        style={{
          fontSize: 9,
          color: NOLAN_PALETTE.textDim,
          textTransform: 'uppercase',
          letterSpacing: 0.5,
          marginRight: 4,
        }}
      >
        {label}:
      </span>
      {children}
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '3px 8px',
        background: active ? 'rgba(255,255,255,0.1)' : 'transparent',
        border: `1px solid ${active ? NOLAN_PALETTE.borderLight : NOLAN_PALETTE.border}`,
        borderRadius: 3,
        color: active ? NOLAN_PALETTE.text : NOLAN_PALETTE.textMuted,
        fontSize: 9,
        cursor: 'pointer',
        transition: 'all 0.15s',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
      }}
    >
      {children}
    </button>
  );
}
