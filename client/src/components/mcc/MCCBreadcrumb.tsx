/**
 * MARKER_154.1A: Breadcrumb Bar — shows Matryoshka navigation path.
 * Rewritten for Phase 154: reads LEVEL_CONFIG from useMCCStore (single source of truth).
 *
 * Displays the current navigation level and allows clicking to jump back.
 * Format: 🚀 Welcome > 🗺 Roadmap > 📋 Tasks: auth-module > ⚙ Workflow
 *
 * @phase 154
 * @wave 1
 * @status active
 * @replaces MARKER_153.5A (hard-coded LEVEL_LABELS/LEVEL_ICONS removed)
 */

import { useCallback, useMemo } from 'react';
import { useMCCStore, LEVEL_CONFIG, type NavLevel } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

// MARKER_154.1A: BreadcrumbSegment uses LEVEL_CONFIG from store
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
  const selectedTaskId = useMCCStore(s => s.selectedTaskId);
  const goToLevel = useMCCStore(s => s.goToLevel);
  const goBack = useMCCStore(s => s.goBack);

  // Build breadcrumb segments from history + current level
  const segments: BreadcrumbSegment[] = useMemo(() => {
    const result: BreadcrumbSegment[] = [];

    // History segments (clickable) — read labels/icons from LEVEL_CONFIG
    for (const histLevel of navHistory) {
      const config = LEVEL_CONFIG[histLevel];
      const seg: BreadcrumbSegment = {
        level: histLevel,
        label: config.label,
        icon: config.icon,
        clickable: true,
      };

      // Context labels for intermediate levels
      if (histLevel === 'roadmap' && navRoadmapNodeId) {
        seg.contextLabel = navRoadmapNodeId;
      } else if (histLevel === 'tasks' && navTaskId) {
        seg.contextLabel = navTaskId.slice(0, 16);
      }

      result.push(seg);
    }

    // Current level (not clickable — it's where we are)
    const currentConfig = LEVEL_CONFIG[navLevel];
    const currentSeg: BreadcrumbSegment = {
      level: navLevel,
      label: currentConfig.label,
      icon: currentConfig.icon,
      clickable: false,
    };

    // Context for current level
    if (navLevel === 'tasks' && navRoadmapNodeId) {
      currentSeg.contextLabel = navRoadmapNodeId;
    } else if (navLevel === 'roadmap' && selectedTaskId) {
      // MARKER_155A.G24.BREADCRUMB_ROADMAP_CONTEXT:
      // Keep task context visible in roadmap inline drill mode (single-canvas).
      currentSeg.contextLabel = `task:${selectedTaskId.slice(0, 16)}`;
    } else if (navLevel === 'roadmap' && navRoadmapNodeId) {
      currentSeg.contextLabel = navRoadmapNodeId;
    } else if ((navLevel === 'workflow' || navLevel === 'running' || navLevel === 'results') && navTaskId) {
      currentSeg.contextLabel = navTaskId.slice(0, 16);
    }

    result.push(currentSeg);

    return result;
  }, [navLevel, navHistory, navRoadmapNodeId, navTaskId]);

  // Click handler — jump directly to clicked segment's level
  // MARKER_154.1A: Uses goToLevel instead of multiple goBack() calls
  const handleSegmentClick = useCallback(
    (targetLevel: NavLevel) => {
      goToLevel(targetLevel);
    },
    [goToLevel],
  );

  // Don't show breadcrumb at first_run or plain roadmap root with no context.
  if (navLevel === 'first_run') {
    return null;
  }
  if (navLevel === 'roadmap' && navHistory.length === 0 && !navRoadmapNodeId && !selectedTaskId) {
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
        fontSize: 11,
        fontFamily: 'monospace',
        flexShrink: 0,
        minHeight: 24,
      }}
    >
      {segments.map((seg, i) => (
        <span key={`${seg.level}-${i}`} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          {/* Separator */}
          {i > 0 && (
            <span style={{ color: '#444', fontSize: 9, marginRight: 2 }}>›</span>
          )}

          {/* Segment */}
          <span
            onClick={seg.clickable ? () => handleSegmentClick(seg.level) : undefined}
            style={{
              color: seg.clickable ? '#888' : NOLAN_PALETTE.textAccent,
              cursor: seg.clickable ? 'pointer' : 'default',
              fontWeight: seg.clickable ? 400 : 600,
              padding: '1px 4px',
              borderRadius: 2,
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => {
              if (seg.clickable) {
                (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)';
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
            title={seg.clickable ? `Jump to ${seg.label}` : `Current: ${seg.label}`}
          >
            <span style={{ marginRight: 3 }}>{seg.icon}</span>
            {seg.label}
          </span>

          {/* Context label (module/task name) */}
          {seg.contextLabel && (
            <span style={{ color: '#666', fontSize: 9 }}>
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
            color: '#555',
            fontSize: 9,
            cursor: 'pointer',
            padding: '1px 6px',
            borderRadius: 2,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            transition: 'all 0.15s',
          }}
          onClick={goBack}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.08)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)';
          }}
          title="Go back (Esc)"
        >
          ← Esc
        </span>
      )}
    </div>
  );
}
