/**
 * MARKER_GAMMA-B3: Loading skeleton for media import and panel loading states.
 *
 * Monochrome pulsing skeleton matching NLE dark theme.
 * CSS animation defined in dockview-cut-theme.css (cut-skeleton-pulse).
 *
 * Usage:
 *   <CutLoadingSkeleton variant="timeline" />
 *   <CutLoadingSkeleton variant="project" />
 *   <CutLoadingSkeleton variant="monitor" label="Importing media..." />
 */
import type { CSSProperties } from 'react';

type SkeletonVariant = 'timeline' | 'project' | 'monitor' | 'generic';

interface CutLoadingSkeletonProps {
  variant?: SkeletonVariant;
  label?: string;
}

const CONTAINER: CSSProperties = {
  width: '100%',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  padding: 8,
  background: '#0a0a0a',
};

const LABEL_STYLE: CSSProperties = {
  color: '#555',
  fontSize: 11,
  fontFamily: 'system-ui',
  textAlign: 'center',
  padding: '8px 0',
};

function SkeletonBlock({ w, h }: { w: string; h: number }) {
  return (
    <div
      data-testid="cut-loading-skeleton-block"
      style={{ width: w, height: h, flexShrink: 0 }}
    />
  );
}

function TimelineSkeleton() {
  return (
    <div style={CONTAINER} data-testid="cut-loading-skeleton">
      {/* Ruler */}
      <SkeletonBlock w="100%" h={28} />
      {/* Track rows */}
      {[1, 2, 3, 4].map((i) => (
        <div key={i} data-testid="cut-loading-skeleton-row">
          <SkeletonBlock w="60px" h={40} />
          <SkeletonBlock w="100%" h={40} />
        </div>
      ))}
    </div>
  );
}

function ProjectSkeleton() {
  return (
    <div style={CONTAINER} data-testid="cut-loading-skeleton">
      {/* Search bar */}
      <SkeletonBlock w="100%" h={24} />
      {/* File list rows */}
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} data-testid="cut-loading-skeleton-row">
          <SkeletonBlock w="32px" h={20} />
          <SkeletonBlock w="60%" h={20} />
          <SkeletonBlock w="20%" h={20} />
        </div>
      ))}
    </div>
  );
}

function MonitorSkeleton() {
  return (
    <div style={{ ...CONTAINER, alignItems: 'center', justifyContent: 'center' }}
         data-testid="cut-loading-skeleton">
      <SkeletonBlock w="80%" h={120} />
      <SkeletonBlock w="60%" h={16} />
    </div>
  );
}

function GenericSkeleton() {
  return (
    <div style={CONTAINER} data-testid="cut-loading-skeleton">
      {[1, 2, 3].map((i) => (
        <SkeletonBlock key={i} w="100%" h={24} />
      ))}
    </div>
  );
}

export default function CutLoadingSkeleton({ variant = 'generic', label }: CutLoadingSkeletonProps) {
  const skeletons: Record<SkeletonVariant, () => JSX.Element> = {
    timeline: TimelineSkeleton,
    project: ProjectSkeleton,
    monitor: MonitorSkeleton,
    generic: GenericSkeleton,
  };

  const Skeleton = skeletons[variant];

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Skeleton />
      {label && <div style={LABEL_STYLE}>{label}</div>}
    </div>
  );
}
