/**
 * MARKER_154.2A: FooterActionBar — max 3 context-aware actions per level.
 *
 * Floating bottom bar, replaces CaptainBar + WorkflowToolbar + RailsActionBar.
 * Reads actions from LEVEL_CONFIG (useMCCStore) — single source of truth.
 * Keyboard shortcuts: 1/2/3 for actions, Esc for Back.
 *
 * Design: ComfyUI/n8n bottom bar, Nolan dark monochrome, glass-morphism.
 *
 * @phase 154
 * @wave 1
 * @status active
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useMCCStore, LEVEL_CONFIG, type NavLevel, type ActionDef } from '../../store/useMCCStore';
import { NOLAN_PALETTE } from '../../utils/dagLayout';

// ── MARKER_154.2B: Extra actions per level (gear popup) ──
const GEAR_ACTIONS: Partial<Record<NavLevel, ActionDef[]>> = {
  roadmap: [
    { label: 'Playground', icon: '📁', action: 'openPlayground' },
    { label: 'Regenerate', icon: '↻', action: 'regenerate' },
    { label: 'Settings', icon: '⚙', action: 'openSettings' },
  ],
  tasks: [
    // MARKER_176.1F: Edit remains available in gear now that primary slot 2 is roadmap task creation.
    { label: 'Edit', icon: '✏', action: 'editTask' },
    { label: 'Add Task', icon: '+', action: 'addTask' },
    { label: 'Filter', icon: '🔍', action: 'openFilter' },
  ],
  workflow: [
    { label: 'Save', icon: '💾', action: 'saveWorkflow' },
  ],
  running: [
    { label: 'Stream', icon: '📺', action: 'expandStream' },
    { label: 'Details', icon: '📋', action: 'showDetails' },
  ],
  results: [
    { label: 'Diff', icon: '📄', action: 'showDiff' },
    { label: 'Details', icon: '📋', action: 'showDetails' },
  ],
};

interface FooterActionBarProps {
  /** Handlers for action dispatching — parent wires these */
  onAction?: (action: string) => void;
  /** Disable specific actions by name */
  disabledActions?: string[];
}

export function FooterActionBar({ onAction, disabledActions = [] }: FooterActionBarProps) {
  const navLevel = useMCCStore(s => s.navLevel);
  const goBack = useMCCStore(s => s.goBack);
  const [gearOpen, setGearOpen] = useState(false);

  // Primary actions from LEVEL_CONFIG (max 3)
  const actions = useMemo(() => LEVEL_CONFIG[navLevel]?.actions || [], [navLevel]);
  // Extra actions for gear popup
  const gearActions = useMemo(() => GEAR_ACTIONS[navLevel] || [], [navLevel]);

  // Close gear on level change
  useEffect(() => { setGearOpen(false); }, [navLevel]);

  // Action dispatcher
  const handleAction = useCallback(
    (action: string) => {
      if (action === 'goBack') {
        goBack();
        return;
      }
      onAction?.(action);
    },
    [goBack, onAction],
  );

  // MARKER_154.2A: Keyboard shortcuts — 1/2/3 for primary actions, Esc for back
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Skip if typing in an input/textarea
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'Escape') {
        if (gearOpen) {
          setGearOpen(false);
        } else {
          goBack();
        }
        return;
      }

      const idx = parseInt(e.key, 10) - 1;
      if (idx >= 0 && idx < actions.length) {
        const act = actions[idx];
        if (!disabledActions.includes(act.action)) {
          handleAction(act.action);
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [actions, goBack, handleAction, disabledActions, gearOpen]);

  // Close gear on outside click
  useEffect(() => {
    if (!gearOpen) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-footer-gear]')) {
        setGearOpen(false);
      }
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [gearOpen]);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        padding: '6px 16px',
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(10px)',
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
        flexShrink: 0,
        position: 'relative',
      }}
    >
      {/* Primary actions (max 3) */}
      {actions.map((act, idx) => {
        const isDisabled = disabledActions.includes(act.action);
        return (
          <button
            key={act.action}
            onClick={() => !isDisabled && handleAction(act.action)}
            disabled={isDisabled}
            data-onboarding={idx === 0 ? 'footer-primary-1' : undefined}
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
              borderRadius: 4,
              padding: '5px 16px',
              color: isDisabled
                ? '#444'
                : act.primary
                  ? '#c6ffff'
                  : NOLAN_PALETTE.textNormal,
              fontSize: 11,
              fontFamily: 'monospace',
              fontWeight: act.primary ? 600 : 400,
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              opacity: isDisabled ? 0.5 : 1,
              transition: 'all 0.15s',
              outline: 'none',
            }}
            onMouseEnter={(e) => {
              if (!isDisabled) {
                (e.currentTarget as HTMLElement).style.background = act.primary
                  ? 'rgba(78,205,196,0.2)'
                  : 'rgba(255,255,255,0.08)';
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = act.primary
                ? isDisabled ? 'rgba(255,255,255,0.03)' : 'rgba(78,205,196,0.12)'
                : 'rgba(255,255,255,0.04)';
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
                  background: 'rgba(255,255,255,0.06)',
                  borderRadius: 2,
                  marginLeft: 2,
                }}
              >
                {act.shortcut}
              </span>
            )}
          </button>
        );
      })}

      {/* Gear icon — extra actions popup */}
      {gearActions.length > 0 && (
        <div data-footer-gear style={{ position: 'relative' }}>
          <button
            onClick={() => setGearOpen(!gearOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 28,
              height: 28,
              background: gearOpen ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 4,
              color: '#888',
              fontSize: 13,
              cursor: 'pointer',
              transition: 'all 0.15s',
              outline: 'none',
            }}
            title="More actions"
          >
            ⚙
          </button>

          {/* Popup */}
          {gearOpen && (
            <div
              style={{
                position: 'absolute',
                bottom: 36,
                right: 0,
                background: 'rgba(17,17,17,0.95)',
                backdropFilter: 'blur(10px)',
                border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 4,
                padding: 4,
                minWidth: 140,
                zIndex: 100,
              }}
            >
              {gearActions.map((act) => (
                <button
                  key={act.action}
                  onClick={() => {
                    handleAction(act.action);
                    setGearOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    width: '100%',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: 3,
                    padding: '5px 10px',
                    color: NOLAN_PALETTE.textNormal,
                    fontSize: 10,
                    fontFamily: 'monospace',
                    cursor: 'pointer',
                    transition: 'background 0.1s',
                    textAlign: 'left',
                    outline: 'none',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.06)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = 'transparent';
                  }}
                >
                  <span>{act.icon}</span>
                  <span>{act.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
