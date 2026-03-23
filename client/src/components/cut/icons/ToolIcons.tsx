/**
 * MARKER_GAMMA-ICON1: SVG tool icons for TimelineToolbar + ToolsPalette.
 * All monochrome, 14x14 viewBox, fill={color} pattern.
 * Replaces Unicode chars that render as color emoji on macOS.
 */

interface IconProps {
  color?: string;
  size?: number;
}

/** Arrow cursor pointing up-left (Premiere V tool / FCP7 Arrow) */
export function SelectionIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill={color}>
      <path d="M3 1l8 5.5-3.5.5 2 4-1.5.7-2-4L3 10V1z" />
    </svg>
  );
}

/** Blade/razor splitting a line (Premiere C tool / FCP7 Blade) */
export function RazorIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke={color} strokeWidth="1.2">
      <path d="M4 2l3 5-3 5" />
      <path d="M7 7h5" />
      <circle cx="7" cy="7" r="1" fill={color} stroke="none" />
    </svg>
  );
}

/** Ripple edit — two arrows pointing apart at edit point */
export function RippleIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke={color} strokeWidth="1.2">
      <path d="M7 2v10" />
      <path d="M3 5L1 7l2 2" />
      <path d="M11 5l2 2-2 2" />
      <line x1="1" y1="7" x2="6" y2="7" />
      <line x1="8" y1="7" x2="13" y2="7" />
    </svg>
  );
}

/** Roll edit — two arrows pointing together at edit point */
export function RollIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke={color} strokeWidth="1.2">
      <path d="M7 2v10" />
      <path d="M3 5l2 2-2 2" />
      <path d="M11 5l-2 2 2 2" />
      <line x1="1" y1="7" x2="5" y2="7" />
      <line x1="9" y1="7" x2="13" y2="7" />
    </svg>
  );
}

/** Slip tool — horizontal arrows with filmstrip frame */
export function SlipIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke={color} strokeWidth="1.2">
      <rect x="3" y="4" width="8" height="6" rx="1" />
      <path d="M1 7h2M11 7h2" />
      <path d="M1.5 5.5L0 7l1.5 1.5M12.5 5.5L14 7l-1.5 1.5" />
    </svg>
  );
}

/** Slide tool — clip moving between neighbors */
export function SlideIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke={color} strokeWidth="1.2">
      <rect x="4" y="4" width="6" height="6" rx="1" />
      <path d="M2 5v4M12 5v4" />
      <path d="M2 7H0M14 7h-2" />
      <path d="M3 6L1.5 7 3 8M11 6l1.5 1L11 8" />
    </svg>
  );
}

/** Hand / pan tool — open palm outline (NOT emoji) */
export function HandIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke={color} strokeWidth="1.1">
      <path d="M4.5 7V3.5a1 1 0 012 0V7M6.5 6V2.5a1 1 0 012 0V6M8.5 6.5V3.5a1 1 0 012 0v3M3 7.5V5.5a1 1 0 012 0" />
      <path d="M3 7.5v2a3.5 3.5 0 007 0V6.5" />
    </svg>
  );
}

/** Zoom / magnifying glass */
export function ZoomIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke={color} strokeWidth="1.3">
      <circle cx="6" cy="6" r="4" />
      <line x1="9" y1="9" x2="13" y2="13" />
    </svg>
  );
}

/** Snap magnet icon */
export function SnapIcon({ color = 'currentColor', size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill={color}>
      <path d="M4 2v2h2V2H4zm6 0v2h2V2h-2zM4 4v4a4 4 0 008 0V4h-2v4a2 2 0 01-4 0V4H4z" />
    </svg>
  );
}
