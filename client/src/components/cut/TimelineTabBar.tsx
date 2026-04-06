/**
 * MARKER_170.12 + MARKER_180.14: Timeline Tab Bar with versioning.
 * Tab bar for multi-timeline support. Sits above the timeline area.
 * Premiere Pro-style: dark tabs with active indicator, + button to create.
 *
 * 180.14 additions:
 * - Version badge on each tab (v01, v02, etc.)
 * - Mode indicator (♩ music, ¶ script, ★ favorites, ✎ manual)
 * - Safety: NEVER overwrites — always creates new versioned timeline.
 */
import { type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
// MARKER_192.1: AutoMontageMenu removed from timeline tab bar.
// PULSE/Auto Cut will live in DAG/Graph panel context menu (separate task).
// Component preserved at ./AutoMontageMenu.tsx for future DAG integration.
// See: RECON_UI_LAYOUT_GROK_2026-03-19.md §1

const BAR_STYLE: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 0,
  height: 28,
  background: '#0a0a0a',
  borderBottom: '1px solid #222',
  paddingLeft: 4,
  flexShrink: 0,
  userSelect: 'none',
};

const TAB_STYLE: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: '0 12px',
  height: 27,
  fontSize: 10,
  color: '#777',
  cursor: 'pointer',
  borderRight: '1px solid #1a1a1a',
  background: 'transparent',
  transition: 'background 0.1s, color 0.1s',
  whiteSpace: 'nowrap',
};

const TAB_ACTIVE: CSSProperties = {
  ...TAB_STYLE,
  color: '#ccc',
  background: '#111',
  borderBottom: '2px solid #555',
};

const CLOSE_BTN: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 14,
  height: 14,
  fontSize: 10,
  color: '#555',
  borderRadius: 2,
  cursor: 'pointer',
  background: 'none',
  border: 'none',
  padding: 0,
  lineHeight: 1,
};

const ADD_BTN: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 24,
  height: 24,
  fontSize: 14,
  color: '#555',
  cursor: 'pointer',
  background: 'none',
  border: 'none',
  borderRadius: 3,
  marginLeft: 4,
};

// MARKER_180.14: Mode icons
const MODE_ICONS: Record<string, string> = {
  favorites: '★',
  script: '¶',
  music: '♩',
  manual: '✎',
};

const VERSION_BADGE: CSSProperties = {
  fontSize: 7,
  color: '#555',
  fontFamily: '"JetBrains Mono", monospace',
  marginLeft: 4,
  padding: '0 3px',
  background: '#1a1a1a',
  borderRadius: 2,
};

export default function TimelineTabBar() {
  const tabs = useCutEditorStore((s) => s.timelineTabs);
  const activeIndex = useCutEditorStore((s) => s.activeTimelineTabIndex);
  const setActive = useCutEditorStore((s) => s.setActiveTimelineTab);
  const removeTab = useCutEditorStore((s) => s.removeTimelineTab);
  const createVersioned = useCutEditorStore((s) => s.createVersionedTimeline);
  const projectId = useCutEditorStore((s) => s.projectId);

  const handleAdd = () => {
    // MARKER_180.14: Always create versioned timeline (§7.1 safety)
    const name = projectId || 'project';
    createVersionedTimeline(name, 'manual');
  };

  // Wrapper for createVersionedTimeline that's accessible from store
  function createVersionedTimeline(projectName: string, mode: string) {
    createVersioned(projectName, mode);
  }

  return (
    <div style={BAR_STYLE} data-testid="timeline-tab-bar">
      {tabs.map((tab, i) => (
        <div
          key={tab.id}
          style={i === activeIndex ? TAB_ACTIVE : TAB_STYLE}
          onClick={() => setActive(i)}
          title={tab.id}
        >
          {/* Mode icon */}
          {tab.mode && MODE_ICONS[tab.mode] && (
            <span style={{ fontSize: 9, color: '#555', marginRight: 3 }}>
              {MODE_ICONS[tab.mode]}
            </span>
          )}
          <span>{tab.label}</span>
          {/* Version badge */}
          {tab.version !== undefined && tab.version > 0 && (
            <span style={VERSION_BADGE}>
              v{tab.version.toString().padStart(2, '0')}
            </span>
          )}
          {tabs.length > 1 && (
            <button
              style={CLOSE_BTN}
              onClick={(e) => {
                e.stopPropagation();
                removeTab(i);
              }}
              title="Close timeline"
            >
              x
            </button>
          )}
        </div>
      ))}
      <button style={ADD_BTN} onClick={handleAdd} title="New versioned timeline">
        +
      </button>
      {/* MARKER_192.1: PULSE dropdown removed — timeline is a result surface, not control surface */}
    </div>
  );
}
