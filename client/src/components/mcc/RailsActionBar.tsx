/**
 * MARKER_153.6A: RailsActionBar — max 3 context-aware actions per level.
 *
 * Floating bottom bar in the center DAG column.
 * Shows different actions depending on current navLevel.
 * Replaces WorkflowToolbar for non-edit scenarios.
 *
 * Design: ComfyUI/n8n action-bar UX (Grok R6 recommendation).
 * Extra actions accessible via ⚙ gear icon popup.
 *
 * @phase 153
 * @wave 6
 * @status active
 */

import { useCallback, useMemo } from 'react';
import { useMCCStore, type NavLevel } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

interface ActionDef {
  label: string;
  icon: string;
  action: string;
  shortcut?: string;  // keyboard hint
  primary?: boolean;  // highlighted button
}

// ── Level-specific actions (max 3 per level) ──
const LEVEL_ACTIONS: Record<NavLevel, ActionDef[]> = {
  roadmap: [
    { label: 'Drill', icon: '▶', action: 'drillNode', shortcut: 'Enter', primary: true },
    { label: 'Regenerate', icon: '↻', action: 'regenerate' },
    { label: 'Settings', icon: '⚙', action: 'openSettings' },
  ],
  tasks: [
    { label: 'Open', icon: '▶', action: 'drillTask', shortcut: 'Enter', primary: true },
    { label: 'Add Task', icon: '+', action: 'addTask' },
    { label: 'Back', icon: '←', action: 'goBack', shortcut: 'Esc' },
  ],
  workflow: [
    { label: 'Execute', icon: '▶', action: 'execute', shortcut: 'Enter', primary: true },
    { label: 'Edit', icon: '✏', action: 'toggleEdit' },
    { label: 'Back', icon: '←', action: 'goBack', shortcut: 'Esc' },
  ],
  running: [
    { label: 'Stop', icon: '⏹', action: 'stop', primary: true },
    { label: 'Stream', icon: '📺', action: 'expandStream' },
    { label: 'Back', icon: '←', action: 'goBack', shortcut: 'Esc' },
  ],
  results: [
    { label: 'Apply', icon: '✓', action: 'apply', primary: true },
    { label: 'Reject', icon: '✕', action: 'reject' },
    { label: 'Back', icon: '←', action: 'goBack', shortcut: 'Esc' },
  ],
};

interface RailsActionBarProps {
  selectedNode?: string | null;
  onExecute?: () => void;
  onRegenerate?: () => void;
  onToggleEdit?: () => void;
  onAddTask?: () => void;
  onStop?: () => void;
  onApply?: () => void;
  onReject?: () => void;
  onExpandStream?: () => void;
  onOpenSettings?: () => void;
}

export function RailsActionBar({
  selectedNode,
  onExecute,
  onRegenerate,
  onToggleEdit,
  onAddTask,
  onStop,
  onApply,
  onReject,
  onExpandStream,
  onOpenSettings,
}: RailsActionBarProps) {
  const navLevel = useMCCStore(s => s.navLevel);
  const drillDown = useMCCStore(s => s.drillDown);
  const goBack = useMCCStore(s => s.goBack);

  const actions = useMemo(() => LEVEL_ACTIONS[navLevel] || [], [navLevel]);

  const handleAction = useCallback(
    (action: string) => {
      switch (action) {
        case 'drillNode':
          if (selectedNode) drillDown('tasks', { roadmapNodeId: selectedNode });
          break;
        case 'drillTask':
          drillDown('workflow');
          break;
        case 'goBack':
          goBack();
          break;
        case 'execute':
          onExecute?.();
          break;
        case 'regenerate':
          onRegenerate?.();
          break;
        case 'toggleEdit':
          onToggleEdit?.();
          break;
        case 'addTask':
          onAddTask?.();
          break;
        case 'stop':
          onStop?.();
          break;
        case 'apply':
          onApply?.();
          break;
        case 'reject':
          onReject?.();
          break;
        case 'expandStream':
          onExpandStream?.();
          break;
        case 'openSettings':
          onOpenSettings?.();
          break;
      }
    },
    [selectedNode, drillDown, goBack, onExecute, onRegenerate, onToggleEdit, onAddTask, onStop, onApply, onReject, onExpandStream, onOpenSettings],
  );

  // Don't show if at roadmap with no selected node (drill is disabled)
  const drillDisabled = navLevel === 'roadmap' && !selectedNode;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        padding: '6px 12px',
        background: 'rgba(0,0,0,0.6)',
        backdropFilter: 'blur(8px)',
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
        flexShrink: 0,
      }}
    >
      {actions.map((act) => {
        const isDisabled = act.action === 'drillNode' && drillDisabled;
        return (
          <button
            key={act.action}
            onClick={() => !isDisabled && handleAction(act.action)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              background: act.primary
                ? isDisabled
                  ? 'rgba(255,255,255,0.03)'
                  : 'rgba(78,205,196,0.12)'
                : 'rgba(255,255,255,0.04)',
              border: act.primary && !isDisabled
                ? '1px solid rgba(78,205,196,0.4)'
                : `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 3,
              padding: '4px 14px',
              color: isDisabled
                ? '#444'
                : act.primary
                  ? '#c6ffff'
                  : NOLAN_PALETTE.textNormal,
              fontSize: 10,
              fontFamily: 'monospace',
              fontWeight: act.primary ? 600 : 400,
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              opacity: isDisabled ? 0.5 : 1,
              transition: 'all 0.15s',
            }}
            title={act.shortcut ? `${act.label} (${act.shortcut})` : act.label}
          >
            <span>{act.icon}</span>
            <span>{act.label}</span>
            {act.shortcut && (
              <span
                style={{
                  fontSize: 8,
                  color: '#555',
                  padding: '0 3px',
                  background: 'rgba(255,255,255,0.05)',
                  borderRadius: 2,
                }}
              >
                {act.shortcut}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Get available actions for a given level (for testing/external use).
 */
export function getActionsForLevel(level: NavLevel): ActionDef[] {
  return LEVEL_ACTIONS[level] || [];
}
