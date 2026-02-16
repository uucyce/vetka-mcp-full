/**
 * MARKER_153.5A: Breadcrumb Bar — shows Matryoshka navigation path.
 *
 * Displays the current navigation level and allows clicking to jump back.
 * Format: Roadmap > Module Name > Task > Workflow
 *
 * @phase 153
 * @wave 5
 * @status active
 */

import { useCallback, useMemo } from 'react';
import { useMCCStore, type NavLevel } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

// Level display config
const LEVEL_LABELS: Record<NavLevel, string> = {
  roadmap: 'Roadmap',
  tasks: 'Tasks',
  workflow: 'Workflow',
  running: 'Running',
  results: 'Results',
};

const LEVEL_ICONS: Record<NavLevel, string> = {
  roadmap: '🗺',
  tasks: '📋',
  workflow: '⚙',
  running: '▶',
  results: '📊',
};

interface BreadcrumbSegment {
  level: NavLevel;
  label: string;
  icon: string;
  contextLabel?: string; // e.g. module name or task title
  clickable: boolean;
}

export function MCCBreadcrumb() {
  const navLevel = useMCCStore(s => s.navLevel);
  const navHistory = useMCCStore(s => s.navHistory);
  const navRoadmapNodeId = useMCCStore(s => s.navRoadmapNodeId);
  const navTaskId = useMCCStore(s => s.navTaskId);
  const goBack = useMCCStore(s => s.goBack);
  const drillDown = useMCCStore(s => s.drillDown);

  // Build breadcrumb segments from history + current level
  const segments: BreadcrumbSegment[] = useMemo(() => {
    const result: BreadcrumbSegment[] = [];

    // History segments (clickable)
    for (const histLevel of navHistory) {
      const seg: BreadcrumbSegment = {
        level: histLevel,
        label: LEVEL_LABELS[histLevel],
        icon: LEVEL_ICONS[histLevel],
        clickable: true,
      };

      // Add context labels for intermediate levels
      if (histLevel === 'roadmap' && navRoadmapNodeId) {
        // Will be resolved when roadmap data is available
      }

      result.push(seg);
    }

    // Current level (not clickable — it's where we are)
    const currentSeg: BreadcrumbSegment = {
      level: navLevel,
      label: LEVEL_LABELS[navLevel],
      icon: LEVEL_ICONS[navLevel],
      clickable: false,
    };

    // Add context for current level
    if (navLevel === 'tasks' && navRoadmapNodeId) {
      currentSeg.contextLabel = navRoadmapNodeId;
    } else if ((navLevel === 'workflow' || navLevel === 'running' || navLevel === 'results') && navTaskId) {
      currentSeg.contextLabel = navTaskId.slice(0, 12);
    }

    result.push(currentSeg);

    return result;
  }, [navLevel, navHistory, navRoadmapNodeId, navTaskId]);

  // Click handler — go back to the clicked segment's level
  const handleSegmentClick = useCallback(
    (segIndex: number) => {
      // Calculate how many levels to go back
      const stepsBack = segments.length - 1 - segIndex;
      for (let i = 0; i < stepsBack; i++) {
        goBack();
      }
    },
    [segments, goBack],
  );

  // Don't show breadcrumb at root level with no history
  if (navLevel === 'roadmap' && navHistory.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '4px 10px',
        background: 'rgba(255,255,255,0.02)',
        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
        fontSize: 9,
        fontFamily: 'monospace',
        flexShrink: 0,
        minHeight: 22,
      }}
    >
      {segments.map((seg, i) => (
        <span key={`${seg.level}-${i}`} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          {/* Separator */}
          {i > 0 && (
            <span style={{ color: '#444', fontSize: 8, marginRight: 2 }}>›</span>
          )}

          {/* Segment */}
          <span
            onClick={seg.clickable ? () => handleSegmentClick(i) : undefined}
            style={{
              color: seg.clickable ? '#888' : NOLAN_PALETTE.textAccent,
              cursor: seg.clickable ? 'pointer' : 'default',
              fontWeight: seg.clickable ? 400 : 600,
              padding: '1px 4px',
              borderRadius: 2,
              transition: 'background 0.15s',
              ...(seg.clickable && {
                ':hover': { background: 'rgba(255,255,255,0.05)' },
              }),
            }}
            onMouseEnter={(e) => {
              if (seg.clickable) {
                (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)';
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
            title={seg.clickable ? `Go back to ${seg.label}` : `Current: ${seg.label}`}
          >
            <span style={{ marginRight: 3 }}>{seg.icon}</span>
            {seg.label}
          </span>

          {/* Context label (module/task name) */}
          {seg.contextLabel && (
            <span style={{ color: '#666', fontSize: 8 }}>
              ({seg.contextLabel})
            </span>
          )}
        </span>
      ))}

      {/* Back button shortcut hint */}
      {navHistory.length > 0 && (
        <span
          style={{
            marginLeft: 'auto',
            color: '#444',
            fontSize: 8,
            cursor: 'pointer',
          }}
          onClick={goBack}
          title="Go back (Esc)"
        >
          ← Esc
        </span>
      )}
    </div>
  );
}
