/**
 * MARKER_170.13.SVG_ICON_SET
 * Monochrome SVG icon set for CUT NLE editor.
 * All icons use currentColor — tint via CSS color property.
 * Adobe Premiere Pro design language: clean, geometric, 16×16 base grid.
 */
import { memo, type CSSProperties } from 'react';

type IconProps = {
  size?: number;
  color?: string;
  style?: CSSProperties;
  className?: string;
};

const defaults = (props: IconProps) => ({
  width: props.size ?? 16,
  height: props.size ?? 16,
  color: props.color ?? 'currentColor',
  style: props.style,
  className: props.className,
});

// ─── Lane Icons ───

/** Film strip — video main track */
export const IconFilmStrip = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="1" y="2" width="14" height="12" rx="1" stroke={d.color} strokeWidth="1.3" />
      <rect x="3" y="2" width="2" height="3" fill={d.color} opacity="0.5" />
      <rect x="7" y="2" width="2" height="3" fill={d.color} opacity="0.5" />
      <rect x="11" y="2" width="2" height="3" fill={d.color} opacity="0.5" />
      <rect x="3" y="11" width="2" height="3" fill={d.color} opacity="0.5" />
      <rect x="7" y="11" width="2" height="3" fill={d.color} opacity="0.5" />
      <rect x="11" y="11" width="2" height="3" fill={d.color} opacity="0.5" />
    </svg>
  );
});
IconFilmStrip.displayName = 'IconFilmStrip';

/** Speaker / waveform — audio sync track */
export const IconSpeaker = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M3 6h2l3-3v10L5 10H3a1 1 0 01-1-1V7a1 1 0 011-1z" fill={d.color} />
      <path d="M10.5 4.5a5 5 0 010 7" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
      <path d="M12.5 2.5a8 8 0 010 11" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
});
IconSpeaker.displayName = 'IconSpeaker';

/** Camera — alternate take track */
export const IconCamera = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="1" y="4" width="10" height="8" rx="1" stroke={d.color} strokeWidth="1.3" />
      <path d="M11 6.5l3.5-2v7l-3.5-2" stroke={d.color} strokeWidth="1.3" strokeLinejoin="round" />
    </svg>
  );
});
IconCamera.displayName = 'IconCamera';

/** Link/chain — aux track */
export const IconLink = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M6.5 9.5l3-3" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
      <path d="M4.5 8.5l-1 1a2.12 2.12 0 003 3l1-1" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
      <path d="M11.5 7.5l1-1a2.12 2.12 0 00-3-3l-1 1" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
});
IconLink.displayName = 'IconLink';

// ─── Transport Icons ───

/** Skip to start |◀ */
export const IconSkipStart = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="3" y="3" width="1.5" height="10" rx="0.5" fill={d.color} />
      <path d="M13 3L6.5 8l6.5 5V3z" fill={d.color} />
    </svg>
  );
});
IconSkipStart.displayName = 'IconSkipStart';

/** Play ▶ */
export const IconPlay = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M4 2.5v11l9.5-5.5L4 2.5z" fill={d.color} />
    </svg>
  );
});
IconPlay.displayName = 'IconPlay';

/** Pause ⏸ */
export const IconPause = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="3.5" y="2.5" width="3" height="11" rx="0.75" fill={d.color} />
      <rect x="9.5" y="2.5" width="3" height="11" rx="0.75" fill={d.color} />
    </svg>
  );
});
IconPause.displayName = 'IconPause';

/** Skip to end ▶| */
export const IconSkipEnd = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M3 3l6.5 5L3 13V3z" fill={d.color} />
      <rect x="11.5" y="3" width="1.5" height="10" rx="0.5" fill={d.color} />
    </svg>
  );
});
IconSkipEnd.displayName = 'IconSkipEnd';

/** Step back 1 frame |◂ */
export const IconPrevFrame = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="2" y="3" width="1.5" height="10" rx="0.5" fill={d.color} />
      <path d="M11 3.5L5.5 8L11 12.5V3.5z" fill={d.color} />
    </svg>
  );
});
IconPrevFrame.displayName = 'IconPrevFrame';

/** Step forward 1 frame ▸| */
export const IconNextFrame = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M5 3.5L10.5 8L5 12.5V3.5z" fill={d.color} />
      <rect x="12.5" y="3" width="1.5" height="10" rx="0.5" fill={d.color} />
    </svg>
  );
});
IconNextFrame.displayName = 'IconNextFrame';

/** Previous edit point |◂◂ */
export const IconPrevEdit = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="1.5" y="3" width="1.5" height="10" rx="0.5" fill={d.color} />
      <path d="M8.5 3.5L4.5 8L8.5 12.5V3.5z" fill={d.color} />
      <path d="M13.5 3.5L9.5 8L13.5 12.5V3.5z" fill={d.color} />
    </svg>
  );
});
IconPrevEdit.displayName = 'IconPrevEdit';

/** Next edit point ▸▸| */
export const IconNextEdit = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M2.5 3.5L6.5 8L2.5 12.5V3.5z" fill={d.color} />
      <path d="M7.5 3.5L11.5 8L7.5 12.5V3.5z" fill={d.color} />
      <rect x="13" y="3" width="1.5" height="10" rx="0.5" fill={d.color} />
    </svg>
  );
});
IconNextEdit.displayName = 'IconNextEdit';

/** Export / arrow up from box */
export const IconExport = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M8 2v8" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
      <path d="M5 4.5L8 1.5l3 3" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 10v3a1 1 0 001 1h8a1 1 0 001-1v-3" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
});
IconExport.displayName = 'IconExport';

/** Spinner / loading */
export const IconSpinner = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <circle cx="8" cy="8" r="5.5" stroke={d.color} strokeWidth="1.3" opacity="0.25" />
      <path d="M8 2.5a5.5 5.5 0 014.9 3" stroke={d.color} strokeWidth="1.3" strokeLinecap="round">
        <animateTransform attributeName="transform" type="rotate" from="0 8 8" to="360 8 8" dur="0.8s" repeatCount="indefinite" />
      </path>
    </svg>
  );
});
IconSpinner.displayName = 'IconSpinner';

/** Checkmark ✓ */
export const IconCheck = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M3 8.5l3.5 3.5L13 4" stroke={d.color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
});
IconCheck.displayName = 'IconCheck';

// ─── View Mode Icons ───

/** Grid/layout — NLE mode */
export const IconLayoutNLE = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="1.5" y="1.5" width="5" height="5" rx="0.75" stroke={d.color} strokeWidth="1.2" />
      <rect x="9.5" y="1.5" width="5" height="5" rx="0.75" stroke={d.color} strokeWidth="1.2" />
      <rect x="1.5" y="9.5" width="13" height="5" rx="0.75" stroke={d.color} strokeWidth="1.2" />
    </svg>
  );
});
IconLayoutNLE.displayName = 'IconLayoutNLE';

/** Wrench — debug mode */
export const IconWrench = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M10.5 2a3.5 3.5 0 00-3.12 5.1L3 11.5 4.5 13l4.4-4.38A3.5 3.5 0 1010.5 2z" stroke={d.color} strokeWidth="1.3" strokeLinejoin="round" />
    </svg>
  );
});
IconWrench.displayName = 'IconWrench';

// ─── Music / Audio ───

/** Music note — markers badge */
export const IconMusicNote = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M6 3v9" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="4.5" cy="12" r="2" fill={d.color} />
      <path d="M6 3l6-1.5v2L6 5" fill={d.color} />
    </svg>
  );
});
IconMusicNote.displayName = 'IconMusicNote';

/** Audio bars — meter fallback */
export const IconAudioBars = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="2" y="8" width="2" height="6" rx="0.5" fill={d.color} />
      <rect x="5.5" y="5" width="2" height="9" rx="0.5" fill={d.color} />
      <rect x="9" y="3" width="2" height="11" rx="0.5" fill={d.color} />
      <rect x="12.5" y="6" width="2" height="8" rx="0.5" fill={d.color} />
    </svg>
  );
});
IconAudioBars.displayName = 'IconAudioBars';

/** Scissors — scene detection / cut point */
export const IconScissors = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <circle cx="4" cy="4" r="2" stroke={d.color} strokeWidth="1.3" />
      <circle cx="4" cy="12" r="2" stroke={d.color} strokeWidth="1.3" />
      <line x1="5.5" y1="5.5" x2="14" y2="12" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
      <line x1="5.5" y1="10.5" x2="14" y2="4" stroke={d.color} strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
});
IconScissors.displayName = 'IconScissors';

// ─── MARKER_W2.1: Track Header Icons ───

/** Lock — padlock closed */
export const IconLock = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="3" y="7" width="10" height="7" rx="1.5" stroke={d.color} strokeWidth="1.5" />
      <path d="M5 7V5a3 3 0 016 0v2" stroke={d.color} strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="8" cy="10.5" r="1" fill={d.color} />
    </svg>
  );
});
IconLock.displayName = 'IconLock';

/** Unlock — padlock open */
export const IconUnlock = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <rect x="3" y="7" width="10" height="7" rx="1.5" stroke={d.color} strokeWidth="1.5" />
      <path d="M5 7V5a3 3 0 016 0" stroke={d.color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
});
IconUnlock.displayName = 'IconUnlock';

/** Mute — speaker with X */
export const IconMute = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M2 6h2l3-3v10L4 10H2a1 1 0 01-1-1V7a1 1 0 011-1z" fill={d.color} />
      <line x1="11" y1="5.5" x2="14.5" y2="10.5" stroke={d.color} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="14.5" y1="5.5" x2="11" y2="10.5" stroke={d.color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
});
IconMute.displayName = 'IconMute';

/** Solo — headphones */
export const IconSolo = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M3 9V7a5 5 0 0110 0v2" stroke={d.color} strokeWidth="1.5" strokeLinecap="round" />
      <rect x="1" y="9" width="3" height="4" rx="1" stroke={d.color} strokeWidth="1.3" />
      <rect x="12" y="9" width="3" height="4" rx="1" stroke={d.color} strokeWidth="1.3" />
    </svg>
  );
});
IconSolo.displayName = 'IconSolo';

/** Target — filled circle (patch/enable) */
export const IconTarget = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <circle cx="8" cy="8" r="5" stroke={d.color} strokeWidth="1.5" />
      <circle cx="8" cy="8" r="2" fill={d.color} />
    </svg>
  );
});

/** MARKER_FIX-TIMELINE-2: Eye — track visible */
export const IconEye = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M8 4C4.5 4 2 8 2 8s2.5 4 6 4 6-4 6-4-2.5-4-6-4z" stroke={d.color} strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx="8" cy="8" r="2" fill={d.color} />
    </svg>
  );
});

/** MARKER_FIX-TIMELINE-2: Eye off — track hidden */
export const IconEyeOff = memo((props: IconProps) => {
  const d = defaults(props);
  return (
    <svg width={d.width} height={d.height} viewBox="0 0 16 16" fill="none" style={d.style} className={d.className}>
      <path d="M8 4C4.5 4 2 8 2 8s2.5 4 6 4 6-4 6-4-2.5-4-6-4z" stroke={d.color} strokeWidth="1.5" strokeLinejoin="round" opacity="0.3" />
      <line x1="3" y1="3" x2="13" y2="13" stroke={d.color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
});
