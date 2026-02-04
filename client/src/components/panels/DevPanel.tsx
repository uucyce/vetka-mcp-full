/**
 * MARKER_110_UX
 * DevPanel - Developer configuration panel for VETKA.
 * Provides controls for Y-axis formula weights, position protection,
 * and fallback threshold settings.
 *
 * Phase 110 UX Improvements:
 * - Sliders for MIN_Y_FLOOR and MAX_Y_CEILING
 * - Visual progress bars for all sliders
 * - Helper text for each control
 * - Keyboard shortcut hint in header
 * - Improved button styling
 *
 * @status active
 * @phase 110
 * @depends react, FloatingWindow, devConfig
 * @used_by App
 */

import { useState, useEffect, useCallback } from 'react';
import { FloatingWindow } from '../artifact/FloatingWindow';
import {
  DevPanelConfig,
  DEFAULT_CONFIG,
  getDevPanelConfig,
  saveDevPanelConfig,
  resetDevPanelConfig,
} from '../../utils/devConfig';

interface DevPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// MARKER_110_UX: Button base style for consistent button appearance
const buttonBaseStyle = {
  padding: '8px 16px',
  borderRadius: 4,
  border: 'none',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500 as const,
  transition: 'all 0.15s ease',
};

// MARKER_110_UX: Developer configuration panel component
export function DevPanel({ isOpen, onClose }: DevPanelProps) {
  const [config, setConfig] = useState<DevPanelConfig>(DEFAULT_CONFIG);
  const [isDirty, setIsDirty] = useState(false);

  // Load config on mount
  useEffect(() => {
    setConfig(getDevPanelConfig());
  }, [isOpen]);

  // Update local config state
  const updateConfig = useCallback((updates: Partial<DevPanelConfig>) => {
    setConfig((prev) => {
      const newConfig = { ...prev, ...updates };
      // Auto-calculate knowledge weight as inverse of time weight
      if ('Y_WEIGHT_TIME' in updates) {
        newConfig.Y_WEIGHT_KNOWLEDGE = 1 - newConfig.Y_WEIGHT_TIME;
      }
      return newConfig;
    });
    setIsDirty(true);
  }, []);

  // Apply configuration
  // MARKER_110_BACKEND_CONFIG: Save config and trigger tree refresh
  const handleApply = useCallback(async () => {
    saveDevPanelConfig(config);
    setIsDirty(false);

    // Emit to backend via socket for server-side layout recalculation
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const socket = (window as any).__vetkaSocket;
    if (socket?.connected) {
      socket.emit('update_layout_config', {
        ...config,
        apply_immediately: true
      });
      console.log('[DevPanel] Config emitted to backend via socket');
    }

    // Local event for other components to react to config changes
    window.dispatchEvent(new CustomEvent('vetka-dev-config-changed', { detail: config }));

    // MARKER_110_FIX: Force tree reload to apply new layout config
    // Dispatch custom event that useTreeData can listen to
    window.dispatchEvent(new CustomEvent('vetka-tree-refresh-needed'));
    console.log('[DevPanel] Config applied, tree refresh triggered');
  }, [config]);

  // Reset to defaults
  const handleReset = useCallback(() => {
    resetDevPanelConfig();
    setConfig(DEFAULT_CONFIG);
    setIsDirty(false);
    window.dispatchEvent(new CustomEvent('vetka-dev-config-changed', { detail: DEFAULT_CONFIG }));
    console.log('[DevPanel] Config reset to defaults');
  }, []);

  if (!isOpen) return null;

  return (
    <FloatingWindow
      title="Dev Panel"
      isOpen={isOpen}
      onClose={onClose}
      defaultWidth={360}
      defaultHeight={520}
    >
      {/* MARKER_110_UX: Keyboard shortcut hint in header */}
      <div style={{ padding: '4px 16px 0', color: '#666', fontSize: 11 }}>
        Cmd+Shift+D to toggle
      </div>
      <div style={{
        padding: 16,
        paddingTop: 8,
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        height: 'calc(100% - 24px)',
        overflowY: 'auto',
        color: '#e0e0e0',
        fontSize: 13,
      }}>
        {/* Section: Y-Axis Formula */}
        <section>
          <h3 style={{ margin: '0 0 12px 0', color: '#fff', fontSize: 14, fontWeight: 600 }}>
            Y-Axis Formula
          </h3>

          {/* MARKER_110_UX: Y_WEIGHT_TIME slider with visual progress bar */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Time Weight</label>
              <span style={{ color: '#888' }}>{config.Y_WEIGHT_TIME.toFixed(2)}</span>
            </div>
            {/* Visual indicator bar */}
            <div style={{
              height: 4,
              background: '#333',
              borderRadius: 2,
              overflow: 'hidden',
              marginBottom: 6,
            }}>
              <div style={{
                height: '100%',
                width: `${config.Y_WEIGHT_TIME * 100}%`,
                background: '#6366f1',
                borderRadius: 2,
                transition: 'width 0.15s ease',
              }} />
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={config.Y_WEIGHT_TIME}
              onChange={(e) => updateConfig({ Y_WEIGHT_TIME: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#6366f1' }}
            />
            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
              Higher = older files lower on Y-axis
            </div>
          </div>

          {/* MARKER_110_UX: Y_WEIGHT_KNOWLEDGE (read-only, calculated) with helper text */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Knowledge Weight</label>
              <span style={{ color: '#888' }}>{config.Y_WEIGHT_KNOWLEDGE.toFixed(2)}</span>
            </div>
            {/* Visual indicator bar */}
            <div style={{
              height: 4,
              background: '#333',
              borderRadius: 2,
              overflow: 'hidden',
              marginBottom: 6,
            }}>
              <div style={{
                height: '100%',
                width: `${config.Y_WEIGHT_KNOWLEDGE * 100}%`,
                background: '#22c55e',
                borderRadius: 2,
                transition: 'width 0.15s ease',
              }} />
            </div>
            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
              Higher = semantic clustering affects Y (Auto = 1 - Time Weight)
            </div>
          </div>
        </section>

        {/* Section: Position Protection */}
        <section>
          <h3 style={{ margin: '0 0 12px 0', color: '#fff', fontSize: 14, fontWeight: 600 }}>
            Position Protection
          </h3>

          {/* MARKER_110_UX: MIN_Y_FLOOR slider with visual progress bar */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Min Y Floor</label>
              <span style={{ color: '#888' }}>{config.MIN_Y_FLOOR}</span>
            </div>
            {/* Visual indicator bar */}
            <div style={{
              height: 4,
              background: '#333',
              borderRadius: 2,
              overflow: 'hidden',
              marginBottom: 6,
            }}>
              <div style={{
                height: '100%',
                width: `${(config.MIN_Y_FLOOR / 200) * 100}%`,
                background: '#22c55e',
                borderRadius: 2,
                transition: 'width 0.15s ease',
              }} />
            </div>
            <input
              type="range"
              min="0"
              max="200"
              step="5"
              value={config.MIN_Y_FLOOR}
              onChange={(e) => updateConfig({ MIN_Y_FLOOR: parseInt(e.target.value) })}
              style={{ width: '100%', accentColor: '#22c55e' }}
            />
            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
              Protection against underground nodes (Y={config.MIN_Y_FLOOR})
            </div>
          </div>

          {/* MARKER_110_UX: MAX_Y_CEILING slider with visual progress bar */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Max Y Ceiling</label>
              <span style={{ color: '#888' }}>{config.MAX_Y_CEILING}</span>
            </div>
            {/* Visual indicator bar */}
            <div style={{
              height: 4,
              background: '#333',
              borderRadius: 2,
              overflow: 'hidden',
              marginBottom: 6,
            }}>
              <div style={{
                height: '100%',
                width: `${((config.MAX_Y_CEILING - 1000) / 9000) * 100}%`,
                background: '#f59e0b',
                borderRadius: 2,
                transition: 'width 0.15s ease',
              }} />
            </div>
            <input
              type="range"
              min="1000"
              max="10000"
              step="100"
              value={config.MAX_Y_CEILING}
              onChange={(e) => updateConfig({ MAX_Y_CEILING: parseInt(e.target.value) })}
              style={{ width: '100%', accentColor: '#f59e0b' }}
            />
            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
              Keeps tree within visible bounds (Y={config.MAX_Y_CEILING})
            </div>
          </div>
        </section>

        {/* Section: Fallback Settings */}
        <section>
          <h3 style={{ margin: '0 0 12px 0', color: '#fff', fontSize: 14, fontWeight: 600 }}>
            Fallback Settings
          </h3>

          {/* MARKER_110_UX: FALLBACK_THRESHOLD slider with visual progress bar */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Fallback Threshold</label>
              <span style={{ color: '#888' }}>{(config.FALLBACK_THRESHOLD * 100).toFixed(0)}%</span>
            </div>
            {/* Visual indicator bar */}
            <div style={{
              height: 4,
              background: '#333',
              borderRadius: 2,
              overflow: 'hidden',
              marginBottom: 6,
            }}>
              <div style={{
                height: '100%',
                width: `${config.FALLBACK_THRESHOLD * 100}%`,
                background: '#ef4444',
                borderRadius: 2,
                transition: 'width 0.15s ease',
              }} />
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={config.FALLBACK_THRESHOLD}
              onChange={(e) => updateConfig({ FALLBACK_THRESHOLD: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#ef4444' }}
            />
            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
              % invalid nodes to trigger layout recalc
            </div>
          </div>

          {/* MARKER_110_UX: USE_SEMANTIC_FALLBACK toggle with helper text */}
          <div style={{ marginBottom: 12 }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={config.USE_SEMANTIC_FALLBACK}
                onChange={(e) => updateConfig({ USE_SEMANTIC_FALLBACK: e.target.checked })}
                style={{ accentColor: '#6366f1' }}
              />
              <span>Use Semantic Fallback</span>
            </label>
            <div style={{ fontSize: 11, color: '#666', marginTop: 4, marginLeft: 24 }}>
              Try semantic positions before full recalc
            </div>
          </div>
        </section>

        {/* MARKER_110_UX: Improved button styling */}
        <div style={{
          marginTop: 'auto',
          paddingTop: 16,
          borderTop: '1px solid #333',
          display: 'flex',
          gap: 10,
        }}>
          {/* Reset button (secondary) */}
          <button
            onClick={handleReset}
            style={{
              ...buttonBaseStyle,
              flex: 1,
              background: 'transparent',
              border: '1px solid #444',
              color: '#888',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#666';
              e.currentTarget.style.color = '#aaa';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#444';
              e.currentTarget.style.color = '#888';
            }}
          >
            Reset
          </button>
          {/* Apply button (primary) */}
          <button
            onClick={handleApply}
            disabled={!isDirty}
            style={{
              ...buttonBaseStyle,
              flex: 2,
              background: isDirty ? '#6366f1' : '#333',
              color: isDirty ? '#fff' : '#666',
              opacity: isDirty ? 1 : 0.6,
              cursor: isDirty ? 'pointer' : 'not-allowed',
            }}
            onMouseEnter={(e) => {
              if (isDirty) e.currentTarget.style.background = '#5558dd';
            }}
            onMouseLeave={(e) => {
              if (isDirty) e.currentTarget.style.background = '#6366f1';
            }}
          >
            Apply
          </button>
        </div>
      </div>
    </FloatingWindow>
  );
}
