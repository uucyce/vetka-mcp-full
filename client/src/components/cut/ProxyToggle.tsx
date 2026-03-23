/**
 * MARKER_B7.2: Proxy Toggle — switch between proxy and original media.
 *
 * FCP7 Ch.40: Proxy workflow allows editing with lightweight proxies,
 * switching to originals for final export/grading.
 *
 * States:
 *   - "original": using full-resolution source files
 *   - "proxy": using proxy files (lower res, faster playback)
 *
 * Gamma wires into ProjectPanel toolbar or MenuBar > View.
 * Store integration: Alpha adds `useProxies` boolean to useCutEditorStore.
 *
 * @phase B7.2
 * @task tb_1774235726_20
 */
import { useCallback, type CSSProperties } from 'react';

interface ProxyToggleProps {
  /** Whether proxies are currently active */
  useProxies: boolean;
  /** Toggle callback */
  onToggle: (useProxies: boolean) => void;
  /** Whether proxy files are available */
  proxiesAvailable?: boolean;
  /** Number of clips with proxies / total clips */
  proxyCoverage?: { available: number; total: number };
  /** Compact mode (icon only, no label) */
  compact?: boolean;
}

const BTN_BASE: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: '3px 8px',
  border: '1px solid #333',
  borderRadius: 3,
  background: '#111',
  color: '#888',
  fontSize: 9,
  fontFamily: 'monospace',
  cursor: 'pointer',
  transition: 'all 0.15s',
};

export default function ProxyToggle({
  useProxies,
  onToggle,
  proxiesAvailable = true,
  proxyCoverage,
  compact = false,
}: ProxyToggleProps) {
  const handleClick = useCallback(() => {
    if (!proxiesAvailable && !useProxies) return; // can't enable if no proxies
    onToggle(!useProxies);
  }, [useProxies, proxiesAvailable, onToggle]);

  const style: CSSProperties = {
    ...BTN_BASE,
    background: useProxies ? '#1a2a1a' : '#111',
    borderColor: useProxies ? '#3a5a3a' : '#333',
    color: useProxies ? '#8a8' : '#888',
    opacity: proxiesAvailable ? 1 : 0.4,
    cursor: proxiesAvailable ? 'pointer' : 'not-allowed',
  };

  const label = useProxies ? 'Proxy' : 'Original';
  const title = useProxies
    ? 'Using proxy files — click to switch to originals'
    : proxiesAvailable
      ? 'Using original files — click to switch to proxies'
      : 'No proxy files available — generate proxies first';

  return (
    <button
      style={style}
      onClick={handleClick}
      title={title}
      data-testid="proxy-toggle"
    >
      {/* Proxy icon: two stacked rectangles (small over large) */}
      <svg width={10} height={10} viewBox="0 0 10 10" fill="none">
        <rect x={0} y={3} width={10} height={7} rx={1} stroke={useProxies ? '#8a8' : '#555'} strokeWidth={0.8} />
        <rect x={2} y={0} width={6} height={5} rx={1} fill={useProxies ? '#3a5a3a' : '#222'} stroke={useProxies ? '#8a8' : '#555'} strokeWidth={0.8} />
      </svg>
      {!compact && (
        <>
          <span>{label}</span>
          {proxyCoverage && (
            <span style={{ color: '#555', fontSize: 8 }}>
              {proxyCoverage.available}/{proxyCoverage.total}
            </span>
          )}
        </>
      )}
    </button>
  );
}
