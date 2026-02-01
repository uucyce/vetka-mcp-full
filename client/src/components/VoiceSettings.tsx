/**
 * VoiceSettings - Voice model configuration panel.
 * Allows users to configure TTS model, fallback, speed, pitch, and language.
 *
 * @status active
 * @phase 105
 * @depends react, socket.io-client, lucide-react
 * @used_by App, ChatPanel
 *
 * MARKER_105_VOICE_UI
 */

import { useState, useEffect, useCallback } from 'react';
import { Volume2, RefreshCw } from 'lucide-react';

// MARKER_105_VOICE_UI
export interface VoiceSettings {
  primaryModel: 'qwen3' | 'edge' | 'piper';
  fallbackModel: 'edge' | 'piper' | 'none';
  speed: number;      // 0.5 - 2.0
  pitch: number;      // -20 to +20
  language: 'ru' | 'en' | 'auto';
}

export interface VoiceSettingsProps {
  settings: VoiceSettings;
  onChange: (settings: VoiceSettings) => void;
  onTest?: () => void;  // Play test audio
}

// MARKER_105_VOICE_UI - Default settings
export const DEFAULT_VOICE_SETTINGS: VoiceSettings = {
  primaryModel: 'qwen3',
  fallbackModel: 'edge',
  speed: 1.0,
  pitch: 0,
  language: 'auto',
};

// Model display names
const MODEL_NAMES: Record<string, string> = {
  qwen3: 'Qwen 3 TTS',
  edge: 'Edge TTS',
  piper: 'Piper',
  none: 'None',
};

// Language display names
const LANGUAGE_NAMES: Record<string, string> = {
  ru: 'Russian',
  en: 'English',
  auto: 'Auto-detect',
};

// MARKER_105_VOICE_UI - Subtle gray styling matching ArtifactPanel
const styles = {
  container: {
    background: '#1a1a1a',
    border: '1px solid #333',
    borderRadius: 4,
    padding: 16,
    color: '#ccc',
    fontFamily: 'inherit',
  } as React.CSSProperties,
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
    paddingBottom: 12,
    borderBottom: '1px solid #333',
  } as React.CSSProperties,
  headerTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#e0e0e0',
  } as React.CSSProperties,
  headerIcon: {
    color: '#666',
  } as React.CSSProperties,
  section: {
    marginBottom: 16,
  } as React.CSSProperties,
  label: {
    display: 'block',
    fontSize: 12,
    color: '#888',
    marginBottom: 6,
  } as React.CSSProperties,
  select: {
    width: '100%',
    padding: '8px 12px',
    background: '#0a0a0a',
    border: '1px solid #333',
    borderRadius: 4,
    color: '#e0e0e0',
    fontSize: 13,
    cursor: 'pointer',
    outline: 'none',
    appearance: 'none' as const,
    WebkitAppearance: 'none' as const,
    backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'12\' height=\'12\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'%23666\' stroke-width=\'2\'%3E%3Cpath d=\'M6 9l6 6 6-6\'/%3E%3C/svg%3E")',
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 12px center',
    paddingRight: 36,
  } as React.CSSProperties,
  sliderContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  } as React.CSSProperties,
  slider: {
    flex: 1,
    height: 4,
    background: '#333',
    borderRadius: 2,
    cursor: 'pointer',
    WebkitAppearance: 'none' as const,
    appearance: 'none' as const,
  } as React.CSSProperties,
  sliderValue: {
    minWidth: 48,
    textAlign: 'right' as const,
    fontSize: 12,
    color: '#888',
    fontFamily: 'monospace',
  } as React.CSSProperties,
  testButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    width: '100%',
    padding: '10px 16px',
    background: '#0a0a0a',
    border: '1px solid #333',
    borderRadius: 4,
    color: '#888',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    marginTop: 8,
  } as React.CSSProperties,
  testButtonHover: {
    background: '#222',
    borderColor: '#444',
    color: '#ccc',
  } as React.CSSProperties,
  row: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
  } as React.CSSProperties,
};

// Custom slider thumb styles (injected via style tag)
const sliderStyles = `
  .voice-settings-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    background: #666;
    border-radius: 50%;
    cursor: pointer;
    transition: background 0.15s ease;
  }
  .voice-settings-slider::-webkit-slider-thumb:hover {
    background: #888;
  }
  .voice-settings-slider::-moz-range-thumb {
    width: 14px;
    height: 14px;
    background: #666;
    border: none;
    border-radius: 50%;
    cursor: pointer;
  }
  .voice-settings-slider:focus {
    outline: none;
  }
`;

export function VoiceSettings({ settings, onChange, onTest }: VoiceSettingsProps) {
  const [isTestHovered, setIsTestHovered] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  // MARKER_105_VOICE_UI - Listen for voice-settings-update socket event
  useEffect(() => {
    const handleVoiceSettingsUpdate = (event: CustomEvent<VoiceSettings>) => {
      if (event.detail) {
        onChange(event.detail);
      }
    };

    window.addEventListener('voice-settings-update', handleVoiceSettingsUpdate as EventListener);
    return () => {
      window.removeEventListener('voice-settings-update', handleVoiceSettingsUpdate as EventListener);
    };
  }, [onChange]);

  // MARKER_105_VOICE_UI - Emit voice-settings-change on save
  const emitSettingsChange = useCallback((newSettings: VoiceSettings) => {
    window.dispatchEvent(
      new CustomEvent('voice-settings-change', { detail: newSettings })
    );
  }, []);

  const handleChange = useCallback((key: keyof VoiceSettings, value: string | number) => {
    const newSettings = { ...settings, [key]: value };
    onChange(newSettings);
    emitSettingsChange(newSettings);
  }, [settings, onChange, emitSettingsChange]);

  const handleTest = useCallback(async () => {
    if (isTesting) return;

    setIsTesting(true);
    try {
      if (onTest) {
        await onTest();
      }
    } finally {
      setIsTesting(false);
    }
  }, [onTest, isTesting]);

  // Format speed display
  const formatSpeed = (speed: number) => `${speed.toFixed(1)}x`;

  // Format pitch display
  const formatPitch = (pitch: number) => {
    if (pitch === 0) return '0';
    return pitch > 0 ? `+${pitch}` : `${pitch}`;
  };

  return (
    <div style={styles.container}>
      {/* Inject slider styles */}
      <style>{sliderStyles}</style>

      {/* Header */}
      <div style={styles.header}>
        <Volume2 size={16} style={styles.headerIcon} />
        <span style={styles.headerTitle}>Voice Settings</span>
      </div>

      {/* Primary Model */}
      <div style={styles.section}>
        <label style={styles.label}>Primary Model</label>
        <select
          value={settings.primaryModel}
          onChange={(e) => handleChange('primaryModel', e.target.value as VoiceSettings['primaryModel'])}
          style={styles.select}
        >
          <option value="qwen3">{MODEL_NAMES.qwen3}</option>
          <option value="edge">{MODEL_NAMES.edge}</option>
          <option value="piper">{MODEL_NAMES.piper}</option>
        </select>
      </div>

      {/* Fallback Model */}
      <div style={styles.section}>
        <label style={styles.label}>Fallback Model</label>
        <select
          value={settings.fallbackModel}
          onChange={(e) => handleChange('fallbackModel', e.target.value as VoiceSettings['fallbackModel'])}
          style={styles.select}
        >
          <option value="edge">{MODEL_NAMES.edge}</option>
          <option value="piper">{MODEL_NAMES.piper}</option>
          <option value="none">{MODEL_NAMES.none}</option>
        </select>
      </div>

      {/* Speed and Pitch Row */}
      <div style={styles.row}>
        {/* Speed Slider */}
        <div style={styles.section}>
          <label style={styles.label}>Speed</label>
          <div style={styles.sliderContainer}>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={settings.speed}
              onChange={(e) => handleChange('speed', parseFloat(e.target.value))}
              style={styles.slider}
              className="voice-settings-slider"
            />
            <span style={styles.sliderValue}>{formatSpeed(settings.speed)}</span>
          </div>
        </div>

        {/* Pitch Slider */}
        <div style={styles.section}>
          <label style={styles.label}>Pitch</label>
          <div style={styles.sliderContainer}>
            <input
              type="range"
              min="-20"
              max="20"
              step="1"
              value={settings.pitch}
              onChange={(e) => handleChange('pitch', parseInt(e.target.value))}
              style={styles.slider}
              className="voice-settings-slider"
            />
            <span style={styles.sliderValue}>{formatPitch(settings.pitch)}</span>
          </div>
        </div>
      </div>

      {/* Language Selector */}
      <div style={styles.section}>
        <label style={styles.label}>Language</label>
        <select
          value={settings.language}
          onChange={(e) => handleChange('language', e.target.value as VoiceSettings['language'])}
          style={styles.select}
        >
          <option value="auto">{LANGUAGE_NAMES.auto}</option>
          <option value="ru">{LANGUAGE_NAMES.ru}</option>
          <option value="en">{LANGUAGE_NAMES.en}</option>
        </select>
      </div>

      {/* Test Button */}
      {onTest && (
        <button
          onClick={handleTest}
          disabled={isTesting}
          onMouseEnter={() => setIsTestHovered(true)}
          onMouseLeave={() => setIsTestHovered(false)}
          style={{
            ...styles.testButton,
            ...(isTestHovered && !isTesting ? styles.testButtonHover : {}),
            opacity: isTesting ? 0.6 : 1,
            cursor: isTesting ? 'wait' : 'pointer',
          }}
        >
          {isTesting ? (
            <>
              <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />
              Testing...
            </>
          ) : (
            <>
              <Volume2 size={14} />
              Test Voice
            </>
          )}
        </button>
      )}

      {/* Spin animation for loading state */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default VoiceSettings;
