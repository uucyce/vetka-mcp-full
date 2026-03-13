/**
 * MARKER_170.12.TIMELINE_TAB_BAR
 * Tab bar for multi-timeline support. Sits above the timeline area.
 * Premiere Pro-style: dark tabs with active indicator, + button to create.
 */
import { type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

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

let tabCounter = 1;

export default function TimelineTabBar() {
  const tabs = useCutEditorStore((s) => s.timelineTabs);
  const activeIndex = useCutEditorStore((s) => s.activeTimelineTabIndex);
  const setActive = useCutEditorStore((s) => s.setActiveTimelineTab);
  const addTab = useCutEditorStore((s) => s.addTimelineTab);
  const removeTab = useCutEditorStore((s) => s.removeTimelineTab);

  const handleAdd = () => {
    tabCounter++;
    const id = `timeline_${tabCounter}`;
    addTab(id, `Timeline ${tabCounter}`);
  };

  return (
    <div style={BAR_STYLE} data-testid="timeline-tab-bar">
      {tabs.map((tab, i) => (
        <div
          key={tab.id}
          style={i === activeIndex ? TAB_ACTIVE : TAB_STYLE}
          onClick={() => setActive(i)}
          title={tab.id}
        >
          <span>{tab.label}</span>
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
      <button style={ADD_BTN} onClick={handleAdd} title="New timeline">
        +
      </button>
    </div>
  );
}
