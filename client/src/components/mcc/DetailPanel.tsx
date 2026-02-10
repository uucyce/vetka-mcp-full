/**
 * MARKER_135.3A: Detail Panel — right sidebar with node info.
 * Shows selected node details, stats, and action buttons.
 *
 * @phase 135.1
 * @status active
 */

import { NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGNode, DAGStats } from '../../types/dag';

interface DetailPanelProps {
  node: DAGNode | null;
  stats: DAGStats | null;
  onAction: (action: string) => void;
}

export function DetailPanel({ node, stats, onAction }: DetailPanelProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        padding: 12,
        background: NOLAN_PALETTE.bgPanel,
        overflow: 'auto',
      }}
    >
      {/* Selected Node Info */}
      {node ? (
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: 9,
              color: NOLAN_PALETTE.textDim,
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            selected
          </div>

          {/* Node type badge */}
          <div
            style={{
              display: 'inline-block',
              padding: '2px 6px',
              background: NOLAN_PALETTE.bgNode,
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 3,
              fontSize: 9,
              color: NOLAN_PALETTE.textNormal,
              textTransform: 'uppercase',
              marginBottom: 8,
            }}
          >
            {node.type}
          </div>

          {/* Node label */}
          <div
            style={{
              fontSize: 12,
              color: NOLAN_PALETTE.textAccent,
              fontWeight: 500,
              marginBottom: 12,
              lineHeight: 1.4,
            }}
          >
            {node.label}
          </div>

          {/* Metadata grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
              marginBottom: 12,
            }}
          >
            <MetaItem label="Status" value={node.status} />
            <MetaItem label="Layer" value={node.layer} />
            {node.durationS && <MetaItem label="Duration" value={`${node.durationS}s`} />}
            {node.tokens && <MetaItem label="Tokens" value={node.tokens} />}
            {node.model && <MetaItem label="Model" value={node.model} />}
            {node.role && <MetaItem label="Role" value={node.role} />}
            {node.confidence !== undefined && (
              <MetaItem label="Confidence" value={`${Math.round(node.confidence * 100)}%`} />
            )}
          </div>

          {/* Actions */}
          {node.type === 'proposal' && (
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <ActionButton label="Approve" onClick={() => onAction('approve')} />
              <ActionButton label="Reject" onClick={() => onAction('reject')} variant="danger" />
            </div>
          )}

          {node.type === 'task' && node.status === 'failed' && (
            <ActionButton label="Retry" onClick={() => onAction('retry')} />
          )}
        </div>
      ) : (
        <div
          style={{
            color: NOLAN_PALETTE.textDim,
            fontSize: 11,
            textAlign: 'center',
            padding: 20,
          }}
        >
          Click a node to see details
        </div>
      )}

      {/* Stats Summary */}
      {stats && (
        <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: `1px solid ${NOLAN_PALETTE.borderDim}` }}>
          <div
            style={{
              fontSize: 9,
              color: NOLAN_PALETTE.textDim,
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 8,
            }}
          >
            overview
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <StatRow label="Total Tasks" value={stats.totalTasks} />
            <StatRow label="Running" value={stats.runningTasks} color={NOLAN_PALETTE.statusRunning} />
            <StatRow label="Completed" value={stats.completedTasks} color={NOLAN_PALETTE.statusDone} />
            <StatRow label="Failed" value={stats.failedTasks} color={NOLAN_PALETTE.statusFailed} />
            <StatRow label="Success Rate" value={`${stats.successRate}%`} />
          </div>
        </div>
      )}
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ fontSize: 11, color: NOLAN_PALETTE.textBright }}>
        {value}
      </div>
    </div>
  );
}

function StatRow({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10 }}>
      <span style={{ color: NOLAN_PALETTE.textNormal }}>{label}</span>
      <span style={{ color: color || NOLAN_PALETTE.textBright }}>{value}</span>
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  variant = 'default',
}: {
  label: string;
  onClick: () => void;
  variant?: 'default' | 'danger';
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: '6px 10px',
        background: variant === 'danger' ? 'rgba(138,106,106,0.2)' : 'rgba(255,255,255,0.05)',
        border: `1px solid ${variant === 'danger' ? NOLAN_PALETTE.statusFailed : NOLAN_PALETTE.borderDim}`,
        borderRadius: 3,
        color: variant === 'danger' ? NOLAN_PALETTE.statusFailed : NOLAN_PALETTE.textNormal,
        fontSize: 10,
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  );
}
