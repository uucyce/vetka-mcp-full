/**
 * MARKER_GAMMA-P2: Platform selector checkbox row.
 * White monochrome SVG icons — no color per CUT design rule.
 */
import type { CSSProperties } from 'react';
import type { Platform } from './types';
import { PLATFORM_LABELS } from './types';

// Monochrome SVG paths for platform logos (simplified glyphs)
const PLATFORM_ICONS: Record<Platform, string> = {
  youtube:   'M21.8 8.001a2.75 2.75 0 0 0-1.94-1.94C18.12 5.5 12 5.5 12 5.5s-6.12 0-7.86.56A2.75 2.75 0 0 0 2.2 8c-.56 1.74-.56 5.37-.56 5.37s0 3.63.56 5.37a2.75 2.75 0 0 0 1.94 1.94c1.74.56 7.86.56 7.86.56s6.12 0 7.86-.56a2.75 2.75 0 0 0 1.94-1.94c.56-1.74.56-5.37.56-5.37s0-3.63-.56-5.37ZM9.75 15.02V8.98L15.5 12l-5.75 3.02Z',
  instagram: 'M12 2.16c2.65 0 2.96.01 4 .06 1.05.05 1.63.22 2.12.47.52.2.9.47 1.3.86.4.4.67.78.86 1.3.25.49.42 1.07.47 2.12.05 1.04.06 1.35.06 4s-.01 2.96-.06 4c-.05 1.05-.22 1.63-.47 2.12-.2.52-.47.9-.86 1.3-.4.4-.78.67-1.3.86-.49.25-1.07.42-2.12.47-1.04.05-1.35.06-4 .06s-2.96-.01-4-.06c-1.05-.05-1.63-.22-2.12-.47a3.5 3.5 0 0 1-1.3-.86 3.5 3.5 0 0 1-.86-1.3c-.25-.49-.42-1.07-.47-2.12-.05-1.04-.06-1.35-.06-4s.01-2.96.06-4c.05-1.05.22-1.63.47-2.12.2-.52.47-.9.86-1.3.4-.4.78-.67 1.3-.86.49-.25 1.07-.42 2.12-.47 1.04-.05 1.35-.06 4-.06Zm0 2.16a7.68 7.68 0 1 0 0 15.36 7.68 7.68 0 0 0 0-15.36Zm0 12.67a5 5 0 1 1 0-9.98 5 5 0 0 1 0 9.98Zm6.4-11.85a1.44 1.44 0 1 1-2.88 0 1.44 1.44 0 0 1 2.88 0Z',
  tiktok:    'M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.88-2.88 2.89 2.89 0 0 1 2.88-2.88c.3 0 .58.04.86.11v-3.5a6.37 6.37 0 0 0-.86-.06A6.35 6.35 0 0 0 3.14 15.3 6.35 6.35 0 0 0 9.49 21a6.35 6.35 0 0 0 6.35-6.35V8.7a8.19 8.19 0 0 0 4.76 1.52v-3.4a4.85 4.85 0 0 1-1.01-.13Z',
  x:         'M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117Z',
  telegram:  'M20.66 3.72 2.68 10.4c-1.22.49-1.21 1.17-.22 1.47l4.62 1.44 10.7-6.75c.5-.31.97-.14.59.2l-8.67 7.83-.33 4.76c.49 0 .7-.22.97-.49l2.33-2.26 4.84 3.58c.89.49 1.53.24 1.76-.83l3.18-15c.33-1.3-.49-1.89-1.35-1.5Z',
  file:      'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Zm4 18H6V4h7v5h5v11Z',
};

const ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  borderRadius: 4,
  transition: 'background 0.1s',
  userSelect: 'none',
};

interface Props {
  platform: Platform;
  checked: boolean;
  onChange: (platform: Platform, checked: boolean) => void;
}

export function PlatformCheckbox({ platform, checked, onChange }: Props) {
  return (
    <label
      style={{
        ...ROW,
        background: checked ? '#222' : 'transparent',
      }}
      data-testid={`publish-platform-${platform}`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(platform, e.target.checked)}
        style={{ accentColor: '#999', width: 14, height: 14 }}
      />
      <svg width="18" height="18" viewBox="0 0 24 24" fill="#ccc" style={{ flexShrink: 0 }}>
        <path d={PLATFORM_ICONS[platform]} />
      </svg>
      <span style={{ color: checked ? '#eee' : '#888', fontSize: 12 }}>
        {PLATFORM_LABELS[platform]}
      </span>
    </label>
  );
}
