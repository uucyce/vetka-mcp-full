/**
 * MARKER_109_DEVPANEL
 * DevPanel - Developer configuration panel for VETKA.
 * Provides controls for Y-axis formula weights, position protection,
 * and fallback threshold settings.
 *
 * @status active
 * @phase 109
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

// MARKER_109_DEVPANEL: Developer configuration panel component
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
  const handleApply = useCallback(() => {
    saveDevPanelConfig(config);
    setIsDirty(false);

    // Emit event for other components to react to config changes
    window.dispatchEvent(new CustomEvent('vetka-dev-config-changed', { detail: config }));
    console.log('[DevPanel] Config applied:', config);
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
      title="Dev Panel (Cmd+Shift+D)"
      isOpen={isOpen}
      onClose={onClose}
      defaultWidth={360}
      defaultHeight={480}
    >
      <div style={{
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        height: '100%',
        overflowY: 'auto',
        color: '#e0e0e0',
        fontSize: 13,
      }}>
        {/* Section: Y-Axis Formula */}
        <section>
          <h3 style={{ margin: '0 0 12px 0', color: '#fff', fontSize: 14, fontWeight: 600 }}>
            Y-Axis Formula
          </h3>

          {/* Y_WEIGHT_TIME slider */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Time Weight</label>
              <span style={{ color: '#888' }}>{config.Y_WEIGHT_TIME.toFixed(2)}</span>
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
          </div>

          {/* Y_WEIGHT_KNOWLEDGE (read-only, calculated) */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Knowledge Weight</label>
              <span style={{ color: '#888' }}>{config.Y_WEIGHT_KNOWLEDGE.toFixed(2)}</span>
            </div>
            <div style={{
              height: 6,
              background: '#333',
              borderRadius: 3,
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${config.Y_WEIGHT_KNOWLEDGE * 100}%`,
                background: '#22c55e',
                borderRadius: 3,
              }} />
            </div>
            <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
              Auto = 1 - Time Weight
            </div>
          </div>
        </section>

        {/* Section: Position Protection */}
        <section>
          <h3 style={{ margin: '0 0 12px 0', color: '#fff', fontSize: 14, fontWeight: 600 }}>
            Position Protection
          </h3>

          {/* MIN_Y_FLOOR */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Min Y Floor</label>
            </div>
            <input
              type="number"
              min="0"
              max="1000"
              value={config.MIN_Y_FLOOR}
              onChange={(e) => updateConfig({ MIN_Y_FLOOR: parseInt(e.target.value) || 0 })}
              style={{
                width: '100%',
                padding: '6px 10px',
                background: '#1a1a1a',
                border: '1px solid #333',
                borderRadius: 4,
                color: '#fff',
                fontSize: 13,
              }}
            />
          </div>

          {/* MAX_Y_CEILING */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Max Y Ceiling</label>
            </div>
            <input
              type="number"
              min="100"
              max="10000"
              value={config.MAX_Y_CEILING}
              onChange={(e) => updateConfig({ MAX_Y_CEILING: parseInt(e.target.value) || 5000 })}
              style={{
                width: '100%',
                padding: '6px 10px',
                background: '#1a1a1a',
                border: '1px solid #333',
                borderRadius: 4,
                color: '#fff',
                fontSize: 13,
              }}
            />
          </div>
        </section>

        {/* Section: Fallback Settings */}
        <section>
          <h3 style={{ margin: '0 0 12px 0', color: '#fff', fontSize: 14, fontWeight: 600 }}>
            Fallback Settings
          </h3>

          {/* FALLBACK_THRESHOLD slider */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <label>Fallback Threshold</label>
              <span style={{ color: '#888' }}>{(config.FALLBACK_THRESHOLD * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={config.FALLBACK_THRESHOLD}
              onChange={(e) => updateConfig({ FALLBACK_THRESHOLD: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#f59e0b' }}
            />
            <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
              Trigger layout recalc if {`>`}{(config.FALLBACK_THRESHOLD * 100).toFixed(0)}% nodes have zero positions
            </div>
          </div>

          {/* USE_SEMANTIC_FALLBACK toggle */}
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
              Try semantic_position before full layout recalc
            </div>
          </div>
        </section>

        {/* Actions */}
        <div style={{
          marginTop: 'auto',
          paddingTop: 16,
          borderTop: '1px solid #333',
          display: 'flex',
          gap: 10,
        }}>
          <button
            onClick={handleReset}
            style={{
              flex: 1,
              padding: '8px 12px',
              background: '#333',
              border: 'none',
              borderRadius: 6,
              color: '#888',
              cursor: 'pointer',
              fontSize: 13,
              transition: 'background 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#444'}
            onMouseLeave={(e) => e.currentTarget.style.background = '#333'}
          >
            Reset
          </button>
          <button
            onClick={handleApply}
            disabled={!isDirty}
            style={{
              flex: 2,
              padding: '8px 12px',
              background: isDirty ? '#6366f1' : '#333',
              border: 'none',
              borderRadius: 6,
              color: isDirty ? '#fff' : '#666',
              cursor: isDirty ? 'pointer' : 'not-allowed',
              fontSize: 13,
              fontWeight: 500,
              transition: 'background 0.2s',
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
