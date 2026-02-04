/**
 * MARKER_109_DEVPANEL
 * DevPanel configuration utility for managing development settings.
 * Handles Y-axis formula weights, position protection, and fallback thresholds.
 *
 * @status active
 * @phase 109
 * @depends localStorage
 * @used_by DevPanel, useTreeData
 */

// MARKER_109_DEVPANEL: Configuration interface for development panel
export interface DevPanelConfig {
  // Y-axis formula weights
  Y_WEIGHT_TIME: number;        // Weight for time-based Y positioning (0-1)
  Y_WEIGHT_KNOWLEDGE: number;   // Auto = 1 - Y_WEIGHT_TIME

  // Position protection (Y-axis bounds)
  MIN_Y_FLOOR: number;          // Minimum Y position (default 20)
  MAX_Y_CEILING: number;        // Maximum Y position (default 5000)

  // Fallback layout settings
  FALLBACK_THRESHOLD: number;   // Ratio of invalid nodes to trigger fallback (0-1)
  USE_SEMANTIC_FALLBACK: boolean; // Try semantic_position before full layout recalc
}

// MARKER_109_DEVPANEL: Default configuration values
export const DEFAULT_CONFIG: DevPanelConfig = {
  Y_WEIGHT_TIME: 0.5,
  Y_WEIGHT_KNOWLEDGE: 0.5,
  MIN_Y_FLOOR: 20,
  MAX_Y_CEILING: 5000,
  FALLBACK_THRESHOLD: 0.5,
  USE_SEMANTIC_FALLBACK: true,
};

const STORAGE_KEY = 'vetka_dev_config';

/**
 * Get the current DevPanel configuration from localStorage.
 * Falls back to defaults if no config is stored or parsing fails.
 */
export function getDevPanelConfig(): DevPanelConfig {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_CONFIG, ...parsed };
    }
  } catch (e) {
    console.warn('[DevConfig] Failed to load config:', e);
  }
  return DEFAULT_CONFIG;
}

/**
 * Save DevPanel configuration to localStorage.
 * Automatically calculates Y_WEIGHT_KNOWLEDGE as inverse of Y_WEIGHT_TIME.
 */
export function saveDevPanelConfig(config: DevPanelConfig): void {
  // Ensure knowledge weight is always inverse of time weight
  const normalizedConfig = {
    ...config,
    Y_WEIGHT_KNOWLEDGE: 1 - config.Y_WEIGHT_TIME,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizedConfig));
}

/**
 * Reset configuration to defaults and clear localStorage.
 */
export function resetDevPanelConfig(): void {
  localStorage.removeItem(STORAGE_KEY);
}
