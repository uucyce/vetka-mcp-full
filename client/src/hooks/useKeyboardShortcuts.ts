/**
 * MARKER_153.6B: useKeyboardShortcuts — context-aware hotkeys per navigation level.
 *
 * Uses navLevel from useMCCStore to determine which actions are available.
 * Global shortcuts: Escape=back, ?=show help overlay (future).
 *
 * @phase 153
 * @wave 6
 * @status active
 */

import { useEffect, useCallback } from 'react';
import { useMCCStore, type NavLevel } from '../store/useMCCStore';

interface ShortcutHandlers {
  onDrillNode?: () => void;
  onDrillTask?: () => void;
  onExecute?: () => void;
  onStop?: () => void;
  onApply?: () => void;
  onReject?: () => void;
  onToggleEdit?: () => void;
  onExpandStream?: () => void;
  onAddTask?: () => void;
}

/**
 * Level-specific shortcut mapping.
 * Each key maps to a handler name from ShortcutHandlers.
 */
const SHORTCUTS: Record<NavLevel, Record<string, keyof ShortcutHandlers>> = {
  // MARKER_154.1B: first_run level — no keyboard shortcuts (FooterActionBar handles 1/2/3)
  first_run: {},
  roadmap: {
    Enter: 'onDrillNode',
  },
  tasks: {
    Enter: 'onDrillTask',
    a: 'onAddTask',
  },
  workflow: {
    Enter: 'onExecute',
    e: 'onToggleEdit',
  },
  running: {
    ' ': 'onStop',           // Space = stop
    v: 'onExpandStream',
  },
  results: {
    Enter: 'onApply',
    r: 'onReject',
  },
};

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  const navLevel = useMCCStore(s => s.navLevel);
  const goBack = useMCCStore(s => s.goBack);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Skip when typing in form elements
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      // Skip when modifier keys are held (except for Space)
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      // Global: Escape = go back
      if (e.key === 'Escape') {
        e.preventDefault();
        goBack();
        return;
      }

      // Level-specific shortcuts
      const levelShortcuts = SHORTCUTS[navLevel];
      if (!levelShortcuts) return;

      const handlerName = levelShortcuts[e.key];
      if (handlerName && handlers[handlerName]) {
        e.preventDefault();
        handlers[handlerName]!();
      }
    },
    [navLevel, goBack, handlers],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

/**
 * Get available shortcuts for a given level (for testing/documentation).
 */
export function getShortcutsForLevel(level: NavLevel): Record<string, string> {
  const levelShortcuts = SHORTCUTS[level] || {};
  const result: Record<string, string> = { Escape: 'goBack' };
  for (const [key, handler] of Object.entries(levelShortcuts)) {
    result[key === ' ' ? 'Space' : key] = handler.replace('on', '').replace(/([A-Z])/g, ' $1').trim();
  }
  return result;
}
