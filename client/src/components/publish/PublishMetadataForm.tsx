/**
 * MARKER_GAMMA-P2: Per-platform metadata form — title, description, tags.
 * Monochrome styling.
 */
import { useCallback, type CSSProperties } from 'react';
import type { PlatformMetadata, Platform } from './types';
import { PLATFORM_LABELS } from './types';

const LABEL: CSSProperties = {
  display: 'block',
  marginBottom: 3,
  color: '#888',
  fontSize: 10,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
};

const INPUT: CSSProperties = {
  width: '100%',
  background: '#111',
  border: '1px solid #333',
  borderRadius: 3,
  padding: '5px 8px',
  color: '#eee',
  fontSize: 12,
  fontFamily: 'inherit',
  outline: 'none',
  boxSizing: 'border-box',
  marginBottom: 8,
};

const TEXTAREA: CSSProperties = {
  ...INPUT,
  minHeight: 48,
  resize: 'vertical',
};

interface Props {
  platform: Platform;
  metadata: PlatformMetadata;
  onChange: (platform: Platform, metadata: PlatformMetadata) => void;
}

export function PublishMetadataForm({ platform, metadata, onChange }: Props) {
  const update = useCallback((partial: Partial<PlatformMetadata>) => {
    onChange(platform, { ...metadata, ...partial });
  }, [platform, metadata, onChange]);

  return (
    <div data-testid={`publish-metadata-${platform}`} style={{ marginTop: 8 }}>
      <label style={LABEL}>Title</label>
      <input
        style={INPUT}
        value={metadata.title}
        onChange={(e) => update({ title: e.target.value })}
        placeholder={`Title for ${PLATFORM_LABELS[platform]}`}
      />

      <label style={LABEL}>Description</label>
      <textarea
        style={TEXTAREA}
        value={metadata.description}
        onChange={(e) => update({ description: e.target.value })}
        placeholder="Description..."
      />

      <label style={LABEL}>Tags (comma separated)</label>
      <input
        style={INPUT}
        value={metadata.tags.join(', ')}
        onChange={(e) => update({ tags: e.target.value.split(',').map((t) => t.trim()).filter(Boolean) })}
        placeholder="tag1, tag2, tag3"
      />

      {platform === 'youtube' && (
        <>
          <label style={{ ...LABEL, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={metadata.isShorts ?? false}
              onChange={(e) => update({ isShorts: e.target.checked })}
              style={{ accentColor: '#999' }}
            />
            YouTube Shorts
          </label>
        </>
      )}

      {platform === 'telegram' && (
        <label style={{ ...LABEL, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={metadata.isDocument ?? false}
            onChange={(e) => update({ isDocument: e.target.checked })}
            style={{ accentColor: '#999' }}
          />
          Send as document (no compression)
        </label>
      )}
    </div>
  );
}
