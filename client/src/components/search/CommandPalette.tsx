/**
 * MARKER_136.W2C: CommandPalette — Unified search with Cmd+K.
 * Floating modal for quick search across files, tasks, and actions.
 * Style: Nolan monochrome with glassmorphism.
 *
 * @status active
 * @phase 136
 * @depends react, zustand store
 */

import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = 'http://localhost:5001/api';

// Nolan palette
const COLORS = {
  bg: 'rgba(10, 10, 10, 0.95)',
  bgLight: '#1a1a1a',
  border: '#333',
  borderLight: '#444',
  text: '#e0e0e0',
  textMuted: '#888',
  textDim: '#666',
  highlight: 'rgba(255, 255, 255, 0.08)',
};

interface SearchResult {
  type: 'file' | 'task' | 'action' | 'semantic';
  id: string;
  title: string;
  subtitle?: string;
  icon?: string;
  action?: () => void;
}

// Quick actions
const QUICK_ACTIONS: SearchResult[] = [
  { type: 'action', id: 'new-task', title: 'New Task', subtitle: 'Create a new pipeline task', icon: '+' },
  { type: 'action', id: 'toggle-devpanel', title: 'Toggle DevPanel', subtitle: 'Show/hide DevPanel', icon: 'D' },
  { type: 'action', id: 'refresh-tree', title: 'Refresh Tree', subtitle: 'Reload 3D tree', icon: 'R' },
];

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>(QUICK_ACTIONS);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // MARKER_136.W3C: DevPanel toggle via custom event (store doesn't have devPanelOpen)
  const [devPanelOpen, setDevPanelOpen] = useState(false);

  // Handle Cmd+K globally
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(prev => !prev);
        if (!isOpen) {
          setQuery('');
          setResults(QUICK_ACTIONS);
          setSelectedIndex(0);
        }
      }
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // MARKER_137.S1_3: Search function using unified backend
  const performSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults(QUICK_ACTIONS);
      return;
    }

    setLoading(true);

    try {
      // MARKER_137.S1_3: Single unified search + task board
      const [unifiedRes, tasksRes] = await Promise.all([
        fetch(`${API_BASE}/search/unified`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: q,
            limit: 15,
            sources: ['file', 'semantic', 'web'],
          }),
        }).catch(() => null),
        fetch(`${API_BASE}/debug/task-board`).catch(() => null),
      ]);

      const newResults: SearchResult[] = [];

      // Unified search results (file + semantic + web)
      if (unifiedRes?.ok) {
        const unified = await unifiedRes.json();
        const items = unified.results || [];
        for (const item of items.slice(0, 10)) {
          const source = item.source || 'file';
          const isWeb = source === 'web';
          newResults.push({
            type: isWeb ? 'action' : (source === 'semantic' ? 'semantic' : 'file'),
            id: item.url || item.title,
            title: item.title?.split('/').pop() || item.title || 'Result',
            subtitle: isWeb ? item.snippet?.slice(0, 80) : item.title,
            icon: isWeb ? 'W' : (source === 'semantic' ? 'S' : 'F'),
          });
        }
      }

      // Tasks from task board
      if (tasksRes?.ok) {
        const tasksData = await tasksRes.json();
        const tasks = tasksData.tasks || [];
        const matchingTasks = tasks.filter((t: any) =>
          t.title?.toLowerCase().includes(q.toLowerCase())
        ).slice(0, 3);
        for (const task of matchingTasks) {
          newResults.push({
            type: 'task',
            id: task.id,
            title: task.title,
            subtitle: `${task.status} · ${task.preset || 'no preset'}`,
            icon: 'T',
          });
        }
      }

      // Filter actions by query
      const matchingActions = QUICK_ACTIONS.filter(a =>
        a.title.toLowerCase().includes(q.toLowerCase())
      );
      newResults.push(...matchingActions);

      setResults(newResults.length > 0 ? newResults : [{ type: 'action', id: 'no-results', title: 'No results', subtitle: `No matches for "${q}"`, icon: '?' }]);
      setSelectedIndex(0);
    } catch (err) {
      console.error('[CommandPalette] Search error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => performSearch(query), 200);
    return () => clearTimeout(timer);
  }, [query, performSearch]);

  // Handle selection
  const handleSelect = useCallback((result: SearchResult) => {
    switch (result.id) {
      case 'toggle-devpanel':
        // MARKER_136.W3C: Use keyboard shortcut event (Cmd+Shift+D) to toggle
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', metaKey: true, shiftKey: true }));
        setDevPanelOpen(!devPanelOpen);
        break;
      case 'new-task':
        // Open DevPanel first, then focus task input
        if (!devPanelOpen) {
          window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', metaKey: true, shiftKey: true }));
          setDevPanelOpen(true);
        }
        break;
      case 'refresh-tree':
        window.dispatchEvent(new CustomEvent('tree-refresh'));
        break;
      default:
        // For files/tasks, could navigate or show details
        if (result.type === 'file' || result.type === 'semantic') {
          // Dispatch event to focus on file in 3D tree
          window.dispatchEvent(new CustomEvent('file-focus', { detail: { path: result.id } }));
        }
    }
    setIsOpen(false);
  }, [devPanelOpen]);

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, results.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (results[selectedIndex]) {
          handleSelect(results[selectedIndex]);
        }
        break;
    }
  }, [results, selectedIndex, handleSelect]);

  if (!isOpen) return null;

  return (
    <div
      onClick={() => setIsOpen(false)}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.6)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: 100,
        zIndex: 99999,
        backdropFilter: 'blur(4px)',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 500,
          maxWidth: '90vw',
          background: COLORS.bg,
          border: `1px solid ${COLORS.border}`,
          borderRadius: 8,
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          overflow: 'hidden',
          fontFamily: 'monospace',
        }}
      >
        {/* Search input */}
        <div style={{
          padding: '12px 16px',
          borderBottom: `1px solid ${COLORS.border}`,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <span style={{ color: COLORS.textDim, fontSize: 14 }}>⌘</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search files, tasks, actions..."
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              color: COLORS.text,
              fontSize: 14,
              fontFamily: 'monospace',
              outline: 'none',
            }}
          />
          {loading && (
            <span style={{ color: COLORS.textDim, fontSize: 10 }}>...</span>
          )}
          <span style={{
            color: COLORS.textDim,
            fontSize: 9,
            padding: '2px 6px',
            background: 'rgba(255,255,255,0.05)',
            borderRadius: 3,
          }}>
            ESC
          </span>
        </div>

        {/* Results */}
        <div style={{
          maxHeight: 350,
          overflowY: 'auto',
        }}>
          {results.map((result, idx) => (
            <div
              key={result.id}
              onClick={() => handleSelect(result)}
              style={{
                padding: '10px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                background: idx === selectedIndex ? COLORS.highlight : 'transparent',
                cursor: 'pointer',
                borderBottom: `1px solid ${COLORS.border}`,
              }}
            >
              {/* Type icon */}
              <span style={{
                width: 24,
                height: 24,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(255,255,255,0.05)',
                borderRadius: 4,
                fontSize: 10,
                color: COLORS.textMuted,
              }}>
                {result.icon}
              </span>

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  color: COLORS.text,
                  fontSize: 12,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {result.title}
                </div>
                {result.subtitle && (
                  <div style={{
                    color: COLORS.textDim,
                    fontSize: 10,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    marginTop: 2,
                  }}>
                    {result.subtitle}
                  </div>
                )}
              </div>

              {/* Type badge */}
              <span style={{
                fontSize: 8,
                color: COLORS.textDim,
                padding: '2px 6px',
                background: 'rgba(255,255,255,0.04)',
                borderRadius: 2,
                textTransform: 'uppercase',
              }}>
                {result.type}
              </span>
            </div>
          ))}
        </div>

        {/* Footer hint */}
        <div style={{
          padding: '8px 16px',
          borderTop: `1px solid ${COLORS.border}`,
          display: 'flex',
          gap: 16,
          fontSize: 9,
          color: COLORS.textDim,
        }}>
          <span>↑↓ navigate</span>
          <span>↵ select</span>
          <span>esc close</span>
        </div>
      </div>
    </div>
  );
}
