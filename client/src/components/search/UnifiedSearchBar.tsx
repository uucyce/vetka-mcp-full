// @ts-nocheck
/**
 * UnifiedSearchBar - Real-time search bar with hybrid search (Qdrant + Weaviate + RRF).
 * Supports multi-select, hover preview, sorting, and multiple search contexts.
 * Nolan-style dark minimal design with SVG icons.
 *
 * @status active
 * @phase 96
 * @depends react, useSearch, useStore
 * @used_by ChatSidebar
 */

// MARKER_137.S1_3: Added unified backend support for web/file contexts
// MARKER_139.S1_2_UNIFIED_ARTIFACT_FIX: unified result mapping + artifact path normalization
import React, { useCallback, useRef, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useSearch } from '../../hooks/useSearch';
import { useStore } from '../../store/useStore';
import { buildViewportContext } from '../../utils/viewport';
import type { SearchResult } from '../../types/chat';
import type { MycoModeAHint } from '../myco/mycoModeATypes';
import { getLaneIdlePlaceholderText, resolveSearchLaneState, type VoiceAgentRole } from './searchLaneMode';
import mycoIdleQuestion from '../../assets/myco/myco_idle_question.png';
import mycoReadySmile from '../../assets/myco/myco_ready_smile.png';
import mycoSpeakingLoop from '../../assets/myco/myco_speaking_loop.apng';
import mycoThinkingLoop from '../../assets/myco/myco_thinking_loop.apng';

const API_BASE = 'http://localhost:5001/api';
const LANE_PREVIEW_WIDTH = 400;
const LANE_PREVIEW_HEIGHT = 320;

interface Props {
  /** Called when user clicks on a result */
  onSelectResult?: (result: SearchResult) => void;
  /** Called when user pins a result to context */
  onPinResult?: (result: SearchResult) => void;
  /** Called to open artifact view */
  onOpenArtifact?: (result: SearchResult) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Default context prefix (e.g., "vetka/") */
  contextPrefix?: string;
  /** Compact mode for tight spaces */
  compact?: boolean;
  /** Optional voice trigger shown as mic icon before first text input */
  onVoiceTrigger?: (role?: VoiceAgentRole) => void;
  /** Optional direct deterministic speech trigger for current lane text */
  onSpeakText?: (text: string, role?: VoiceAgentRole, options?: { autoListenAfter?: boolean }) => void;
  /** External voice state for inline activity indicator */
  voiceState?: 'idle' | 'listening' | 'thinking' | 'speaking';
  /** Normalized voice level (0..1) */
  voiceLevel?: number;
  /** Optional scope tag for deterministic MYCO main-surface events */
  mycoSurfaceScope?: 'main';
  /** Explicit lane ownership for mode-driven rendering */
  laneSurface?: 'main' | 'chat';
  /** Current chat panel side for preview placement */
  chatPosition?: 'left' | 'right';
  /** Optional outer chat panel ref for mirrored preview placement */
  previewAnchorRef?: React.RefObject<HTMLDivElement | null>;
  /** Deterministic MYCO hint payload for empty VETKA search lane */
  mycoHint?: MycoModeAHint | null;
  /** Stable key for resetting typed hint rendering */
  mycoStateKey?: string;
  /** Optional preferred context supplied by parent surface (for scanner/chat bridges) */
  preferredSearchContext?: SearchContext;
  /** Called when user explicitly changes search context from the lane */
  onSearchContextChange?: (context: SearchContext) => void;
}

// Inline SVG icons (no external dependencies - Nolan style)
const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.35-4.35" />
  </svg>
);

const CloseIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
);

const PinIcon = ({ filled }: { filled?: boolean }) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
    <path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" />
  </svg>
);

// Chest icon for artifact view
const ChestIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 10 L4 7 Q4 4 12 4 Q20 4 20 7 L20 10" />
    <rect x="3" y="10" width="18" height="8" rx="1" />
    <circle cx="12" cy="14" r="1.5" fill="currentColor" />
  </svg>
);

const FileIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
  </svg>
);

const CodeIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="16 18 22 12 16 6" />
    <polyline points="8 6 2 12 8 18" />
  </svg>
);

const DocIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <line x1="10" y1="9" x2="8" y2="9" />
  </svg>
);

const LoadingSpinner = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="search-spinner">
    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
  </svg>
);

function InlineMycoTokenIcon({ token }: { token: string }) {
  const common = {
    width: 12,
    height: 12,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    style: {
      display: 'inline-block',
      verticalAlign: '-2px',
      marginRight: 4,
      color: '#f2f5f7',
      flex: '0 0 auto',
    },
  };

  switch (token) {
    case 'pin':
      return (
        <svg {...common}>
          <path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" />
        </svg>
      );
    case 'history':
      return (
        <svg {...common}>
          <path d="M3 3v5h5" />
          <path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
          <path d="M12 7v5l4 2" />
        </svg>
      );
    case 'phone':
      return (
        <svg {...common}>
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
        </svg>
      );
    case 'scanner':
      return (
        <svg {...common}>
          <path d="M3 7h18" />
          <path d="M7 12h10" />
          <path d="M10 17h4" />
        </svg>
      );
    case 'folder':
      return (
        <svg {...common}>
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      );
    case 'chat':
      return (
        <svg {...common}>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      );
    case 'web':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12h20" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      );
    case 'file':
      return (
        <svg {...common}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    case 'star':
      return (
        <svg {...common}>
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      );
    case 'key':
      return (
        <svg {...common}>
          <path d="M21 2l-2 2m-7.61 7.61a4 4 0 1 1-5.66-5.66 4 4 0 0 1 5.66 5.66z" />
          <path d="M15.5 7.5L22 14l-4 4-1.5-1.5-2 2-1.5-1.5-2 2-2.5-2.5" />
        </svg>
      );
    default:
      return null;
  }
}

function renderMycoTokenizedText(text: string) {
  const parts = text.split(/(\[\[[a-z]+\]\])/g).filter(Boolean);
  return parts.map((part, index) => {
    const match = part.match(/^\[\[([a-z]+)\]\]$/);
    if (match) {
      return <InlineMycoTokenIcon key={`${part}-${index}`} token={match[1]} />;
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

// Sort icon
const SortIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 6h18M6 12h12M9 18h6" />
  </svg>
);

// Phase 68.3: SVG icons for search contexts
// VETKA symbol: Y-shaped tree branch in circle - curved branches for organic look
const VetkaIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 512 512" fill="none" stroke="currentColor" strokeLinecap="round">
    {/* Outer circle */}
    <circle cx="256" cy="256" r="180" strokeWidth="20" strokeOpacity="0.6" />
    {/* Central vertical stem */}
    <line x1="256" y1="120" x2="256" y2="380" strokeWidth="22" />
    {/* Left branch (curved, V-like) */}
    <path d="M256 260 C230 200, 190 160, 160 120" strokeWidth="20" fill="none" />
    {/* Right branch (curved, V-like) */}
    <path d="M256 260 C282 200, 322 160, 352 120" strokeWidth="20" fill="none" />
  </svg>
);

const MycoIcon = () => (
  <img
    src={mycoIdleQuestion}
    alt="MYCO"
    style={{
      width: 19,
      height: 19,
      objectFit: 'contain',
      objectPosition: 'center',
      display: 'block',
      filter: 'grayscale(1) brightness(0.82) contrast(0.9)',
      opacity: 0.52,
    }}
  />
);

const WebIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="12" cy="12" r="10" />
    <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
);

const FolderIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
);

const CloudIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
  </svg>
);

const UsersIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

const LocationIcon = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
  </svg>
);

function getTypeIcon(type: string) {
  switch (type) {
    case 'code':
      return <CodeIcon />;
    case 'doc':
      return <DocIcon />;
    default:
      return <FileIcon />;
  }
}

type SortMode = 'relevance' | 'name' | 'type' | 'date' | 'size';
type SearchModeType = 'hybrid' | 'semantic' | 'keyword' | 'filename';
type LaneRoleVisual = 'myco' | 'vetka' | 'context';
type MycoAvatarVisualState = 'idle' | 'speaking' | 'ready' | 'thinking';
type ProviderHealth = Record<string, {
  key_present?: boolean;
  sdk_installed?: boolean;
  available?: boolean;
  error?: string | null;
}>;

// Phase 69.4: Format bytes helper (Finder-style)
function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

// Phase 69.4: Format date helper (compact Finder-style)
function formatDate(timestamp: number): string {
  if (!timestamp || timestamp === 0) return '';
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return date.toLocaleDateString('en-US', { weekday: 'short' });
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Phase 68.2: Search mode labels
const SEARCH_MODE_LABELS: Record<SearchModeType, string> = {
  hybrid: 'Hybrid',
  semantic: 'Semantic',
  keyword: 'Keyword',
  filename: 'Filename',
};

const SEARCH_MODE_DESCRIPTIONS: Record<SearchModeType, string> = {
  hybrid: 'Combined semantic + keyword (RRF)',
  semantic: 'Vector similarity (Qdrant)',
  keyword: 'BM25 text match (Weaviate)',
  filename: 'Search by file name',
};

// Phase 68.3: Search context paths
export type SearchContext = 'vetka' | 'myco' | 'web' | 'file' | 'cloud' | 'social';

const CONTEXT_MODE_FALLBACK: Record<SearchContext, SearchModeType[]> = {
  vetka: ['hybrid', 'semantic', 'keyword', 'filename'],
  myco: ['hybrid', 'semantic', 'keyword', 'filename'],
  web: ['hybrid', 'keyword'],
  file: ['keyword', 'filename'],
  cloud: ['keyword'],
  social: ['keyword'],
};

// SVG icon components for each context
const CONTEXT_ICONS: Record<SearchContext, () => React.ReactElement> = {
  vetka: VetkaIcon,
  myco: MycoIcon,
  web: WebIcon,
  file: FolderIcon,
  cloud: CloudIcon,
  social: UsersIcon,
};

// MARKER_137.S1_3: Enabled web + file contexts (backend ready)
const SEARCH_CONTEXTS: Array<{
  id: SearchContext;
  prefix: string;
  label: string;
  description: string;
  available: boolean;
}> = [
  { id: 'vetka', prefix: 'vetka/', label: 'VETKA', description: 'Search in indexed codebase', available: true },
  { id: 'myco', prefix: 'myco/', label: 'MYCO', description: 'Fast help and UI guidance', available: true },
  { id: 'web', prefix: 'web/', label: 'Web', description: 'Search the internet via Tavily', available: true },
  { id: 'file', prefix: 'file/', label: 'Filesystem', description: 'Search local files', available: true },
  { id: 'cloud', prefix: 'cloud/', label: 'Cloud', description: 'Search cloud storage', available: false },
  { id: 'social', prefix: 'social/', label: 'Social', description: 'Search social networks', available: false },
];

export function UnifiedSearchBar({
  onSelectResult,
  onPinResult,
  onOpenArtifact,
  placeholder = 'Search...',
  contextPrefix = 'vetka/',
  compact = false,
  onVoiceTrigger,
  onSpeakText,
  voiceState = 'idle',
  voiceLevel = 0,
  mycoSurfaceScope,
  laneSurface = 'main',
  chatPosition = 'left',
  previewAnchorRef,
  mycoHint = null,
  mycoStateKey = '',
  preferredSearchContext,
  onSearchContextChange,
}: Props) {
  // Phase 68.3: Search context state
  const [searchContext, setSearchContext] = useState<SearchContext>(preferredSearchContext ?? 'myco');
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextSupportedModes, setContextSupportedModes] = useState<SearchModeType[]>(CONTEXT_MODE_FALLBACK.vetka);
  const [providerHealth, setProviderHealth] = useState<ProviderHealth>({});
  const effectiveSearchContext: Exclude<SearchContext, 'myco'> = searchContext === 'myco' ? 'vetka' : searchContext;

  const {
    query,
    setQuery,
    results,
    isSearching,
    error,
    totalResults,
    searchTime,
    searchMode,
    setSearchMode,
    clearResults,
    isConnected,
    displayLimit,
    loadMore,
    hasMore
  } = useSearch({
    debounceMs: 300,
    defaultLimit: 100,
    autoSearch: searchContext === 'vetka' || searchContext === 'myco',
  }); // Fetch up to 100, paginate in UI

  const inputRef = useRef<HTMLInputElement>(null);
  const laneRootRef = useRef<HTMLDivElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const resultPreviewRef = useRef<HTMLDivElement>(null);
  const mycoPreviewRef = useRef<HTMLDivElement>(null);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mycoPreviewTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingInputFocusRef = useRef(false);

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null);

  // Hover preview state
  const [hoveredResult, setHoveredResult] = useState<SearchResult | null>(null);
  const [previewPosition, setPreviewPosition] = useState<{ x: number; y: number } | null>(null);
  const [showMycoPreview, setShowMycoPreview] = useState(false);
  const [mycoPreviewPosition, setMycoPreviewPosition] = useState<{ x: number; y: number } | null>(null);
  const [mycoAvatarState, setMycoAvatarState] = useState<MycoAvatarVisualState>('idle');
  const mycoAvatarTimersRef = useRef<number[]>([]);
  const [mycoTickerPlaybackDone, setMycoTickerPlaybackDone] = useState(false);

  // Sort state
  const [sortMode, setSortMode] = useState<SortMode>('relevance');
  const [sortAscending, setSortAscending] = useState(false); // false = descending (default)
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [mycoVisibleWordCount, setMycoVisibleWordCount] = useState(0);

  // MARKER_137.S1_3: Unified backend results for web/file contexts
  const [unifiedResults, setUnifiedResults] = useState<SearchResult[]>([]);
  const [unifiedLoading, setUnifiedLoading] = useState(false);
  const [unifiedError, setUnifiedError] = useState<string | null>(null);
  const [unifiedTotal, setUnifiedTotal] = useState(0);
  const [unifiedSearchTime, setUnifiedSearchTime] = useState(0);
  const unifiedDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Phase 68.3: Selected file path display
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);

  // Get pinned files from store to show visual state
  const pinnedFileIds = useStore((s) => s.pinnedFileIds);
  const nodes = useStore((s) => s.nodes);
  const cameraRef = useStore((s) => s.cameraRef);

  // Check if a result is pinned
  const isPinned = useCallback((result: SearchResult) => {
    const nodeId = Object.keys(nodes).find(id => nodes[id]?.path === result.path);
    return nodeId ? pinnedFileIds.includes(nodeId) : false;
  }, [nodes, pinnedFileIds]);

  // MARKER_142.BUG_FALLBACK_LEAK: Never fallback to VETKA socket results outside vetka context
  const activeResults = React.useMemo(() => {
    if (effectiveSearchContext !== 'vetka') {
      return unifiedResults;
    }
    return results;
  }, [effectiveSearchContext, unifiedResults, results]);

  const activeIsSearching = effectiveSearchContext === 'vetka' ? isSearching : unifiedLoading;
  const activeError = effectiveSearchContext === 'vetka' ? error : unifiedError;
  const activeTotalResults = effectiveSearchContext === 'vetka' ? totalResults : unifiedTotal;
  const activeSearchTime = effectiveSearchContext === 'vetka' ? searchTime : unifiedSearchTime;
  const hasMoreActive = effectiveSearchContext === 'vetka'
    ? hasMore
    : activeResults.length > displayLimit;
  const webHasAnyProvider = Object.values(providerHealth).some((p) => p?.available);

  const getPreviewPlacement = useCallback((
    rect: DOMRect,
    previewWidth: number,
    previewHeight: number,
    options?: { belowAnchor?: boolean; extraYOffset?: number; horizontalAnchorRect?: DOMRect | null },
  ) => {
    const gap = 6;
    const preferOutsideLeft = laneSurface === 'chat' && chatPosition === 'right';
    const baseTop = options?.belowAnchor ? rect.bottom + (options?.extraYOffset ?? 6) : rect.top;
    const chatPanelRect = previewAnchorRef?.current?.getBoundingClientRect() || null;
    const laneRect = laneSurface === 'chat'
      ? (chatPanelRect || options?.horizontalAnchorRect || laneRootRef.current?.getBoundingClientRect() || rect)
      : (options?.horizontalAnchorRect || laneRootRef.current?.getBoundingClientRect() || rect);
    const x = preferOutsideLeft
      ? Math.max(8, laneRect.left - previewWidth - gap)
      : Math.min(laneRect.right + gap, Math.max(8, window.innerWidth - previewWidth - 8));
    const y = Math.min(Math.max(8, baseTop), Math.max(8, window.innerHeight - previewHeight - 8));
    return { x, y };
  }, [chatPosition, laneSurface, previewAnchorRef]);

  useEffect(() => {
    if (!preferredSearchContext) return;
    setSearchContext((prev) => {
      // In scanner surfaces, explicit agent choice in the top lane owns the lower scanner source.
      // Lower source changes must not kick the lane out of myco/vetka modes.
      if ((prev === 'myco' || prev === 'vetka') && preferredSearchContext !== prev) {
        // MARKER_163A_PLUS.LANE_OWNERSHIP_AUDIT.V1:
        // Emit a debug event whenever a lower scanner/chat preference tries to displace the owned top-lane mode.
        window.dispatchEvent(new CustomEvent('vetka-myco-lane-ownership-audit', {
          detail: {
            laneSurface,
            retainedContext: prev,
            attemptedContext: preferredSearchContext,
          },
        }));
        return prev;
      }
      return prev === preferredSearchContext ? prev : preferredSearchContext;
    });
  }, [laneSurface, preferredSearchContext]);

  useEffect(() => {
    if (!mycoSurfaceScope) return;
    window.dispatchEvent(new CustomEvent('vetka-myco-search-state', {
      detail: {
        scope: mycoSurfaceScope,
        context: effectiveSearchContext,
        mode: searchMode,
        queryEmpty: query.trim().length === 0,
        providerHealth,
        error: activeError,
      },
    }));
  }, [activeError, effectiveSearchContext, mycoSurfaceScope, providerHealth, query, searchMode]);

  useEffect(() => {
    if (!mycoSurfaceScope) return;
    return () => {
      window.dispatchEvent(new CustomEvent('vetka-myco-search-state', {
        detail: {
          scope: mycoSurfaceScope,
          context: 'vetka',
          mode: 'hybrid',
          queryEmpty: true,
          providerHealth: {},
          error: null,
        },
      }));
    };
  }, [mycoSurfaceScope]);

  // Sort results and apply display limit (pagination)
  const sortedResults = React.useMemo(() => {
    const sorted = [...activeResults];
    // Direction multiplier: 1 for ascending, -1 for descending
    const dir = sortAscending ? 1 : -1;

    switch (sortMode) {
      case 'name':
        sorted.sort((a, b) => dir * a.name.localeCompare(b.name));
        break;
      case 'type':
        sorted.sort((a, b) => dir * a.type.localeCompare(b.type));
        break;
      case 'date':
        // Sort by modification time
        sorted.sort((a, b) => {
          const timeA = (a as any).modified_time || (a as any).created_time || 0;
          const timeB = (b as any).modified_time || (b as any).created_time || 0;
          return dir * (timeB - timeA);
        });
        break;
      case 'size':
        // Sort by size
        sorted.sort((a, b) => {
          const sizeA = (a as any).size || 0;
          const sizeB = (b as any).size || 0;
          return dir * (sizeB - sizeA);
        });
        break;
      case 'relevance':
      default:
        sorted.sort((a, b) => dir * (b.relevance - a.relevance));
        break;
    }
    // Apply display limit for pagination
    return sorted.slice(0, displayLimit);
  }, [activeResults, sortMode, sortAscending, displayLimit]);

  // Handle result click with multi-select
  const handleSelect = useCallback((result: SearchResult, index: number, e: React.MouseEvent) => {
    if (e.shiftKey && lastSelectedIndex !== null) {
      // Range select
      const start = Math.min(lastSelectedIndex, index);
      const end = Math.max(lastSelectedIndex, index);
      const newSelected = new Set(selectedIds);
      for (let i = start; i <= end; i++) {
        newSelected.add(sortedResults[i].id);
      }
      setSelectedIds(newSelected);
    } else if (e.ctrlKey || e.metaKey) {
      // Toggle single selection
      const newSelected = new Set(selectedIds);
      if (newSelected.has(result.id)) {
        newSelected.delete(result.id);
      } else {
        newSelected.add(result.id);
      }
      setSelectedIds(newSelected);
      setLastSelectedIndex(index);
    } else {
      // Normal click - select only this one and trigger navigation
      setSelectedIds(new Set([result.id]));
      setLastSelectedIndex(index);
      // Phase 68.3: Show selected file path
      setSelectedFilePath(result.path);
      onSelectResult?.(result);
    }
  }, [lastSelectedIndex, selectedIds, sortedResults, onSelectResult]);

  // Handle pin click
  const handlePin = useCallback((e: React.MouseEvent, result: SearchResult) => {
    e.stopPropagation();
    onPinResult?.(result);
  }, [onPinResult]);

  // Handle artifact click
  const handleArtifact = useCallback((e: React.MouseEvent, result: SearchResult) => {
    e.stopPropagation();
    onOpenArtifact?.(result);
  }, [onOpenArtifact]);

  // Handle Enter key - pin selected or all results
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && sortedResults.length > 0 && onPinResult) {
      e.preventDefault();
      // Pin selected items, or all if none selected
      const toPinIds = selectedIds.size > 0 ? selectedIds : new Set(sortedResults.map(r => r.id));
      sortedResults
        .filter(r => toPinIds.has(r.id))
        .forEach(result => onPinResult(result));
      // Clear after pinning
      clearResults();
      setSelectedIds(new Set());
    }
    if (e.key === 'Escape') {
      clearResults();
      setSelectedIds(new Set());
      inputRef.current?.blur();
    }
  }, [sortedResults, onPinResult, clearResults, selectedIds]);

  // Hover preview handlers
  const clearResultPreview = useCallback(() => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
    setHoveredResult(null);
    setPreviewPosition(null);
  }, []);

  const clearMycoPreview = useCallback(() => {
    if (mycoPreviewTimerRef.current) {
      window.clearTimeout(mycoPreviewTimerRef.current);
      mycoPreviewTimerRef.current = null;
    }
    setShowMycoPreview(false);
    setMycoPreviewPosition(null);
  }, []);

  const handleMouseEnter = useCallback((result: SearchResult, e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const horizontalAnchorRect = resultsRef.current?.getBoundingClientRect() || null;
    hoverTimerRef.current = setTimeout(() => {
      setHoveredResult(result);
      setPreviewPosition(
        getPreviewPlacement(rect, LANE_PREVIEW_WIDTH, LANE_PREVIEW_HEIGHT, { horizontalAnchorRect }),
      );
    }, 300);
  }, [getPreviewPlacement]);

  const handleMouseLeave = useCallback(() => {
    clearResultPreview();
  }, [clearResultPreview]);

  useEffect(() => {
    const dismissPreviews = () => {
      clearResultPreview();
      clearMycoPreview();
    };

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (laneRootRef.current?.contains(target)) return;
      if (resultPreviewRef.current?.contains(target)) return;
      if (mycoPreviewRef.current?.contains(target)) return;
      dismissPreviews();
    };

    const handleFocusIn = (event: FocusEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (laneRootRef.current?.contains(target)) return;
      if (resultPreviewRef.current?.contains(target)) return;
      if (mycoPreviewRef.current?.contains(target)) return;
      dismissPreviews();
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState !== 'visible') {
        dismissPreviews();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        dismissPreviews();
      }
    };

    window.addEventListener('scroll', dismissPreviews, true);
    window.addEventListener('resize', dismissPreviews);
    window.addEventListener('blur', dismissPreviews);
    window.addEventListener('pointerdown', handlePointerDown, true);
    window.addEventListener('focusin', handleFocusIn, true);
    window.addEventListener('keydown', handleKeyDown, true);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('scroll', dismissPreviews, true);
      window.removeEventListener('resize', dismissPreviews);
      window.removeEventListener('blur', dismissPreviews);
      window.removeEventListener('pointerdown', handlePointerDown, true);
      window.removeEventListener('focusin', handleFocusIn, true);
      window.removeEventListener('keydown', handleKeyDown, true);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [clearMycoPreview, clearResultPreview]);

  // MARKER_142.IMPL_STEP_2_CAPABILITIES: Load context capabilities from backend
  useEffect(() => {
    let cancelled = false;
    const fallbackModes = CONTEXT_MODE_FALLBACK[searchContext] || CONTEXT_MODE_FALLBACK.myco;

    const loadCapabilities = async () => {
      try {
        const endpoint = effectiveSearchContext === 'file'
          ? `${API_BASE}/search/file/capabilities`
          : `${API_BASE}/search/capabilities?context=${encodeURIComponent(effectiveSearchContext)}`;
        const res = await fetch(endpoint);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const backendModes = Array.isArray(data?.supported_modes) ? data.supported_modes : [];
        const validModes = backendModes.filter((m: string): m is SearchModeType =>
          ['hybrid', 'semantic', 'keyword', 'filename'].includes(m)
        );
        if (!cancelled) {
          setContextSupportedModes(validModes.length > 0 ? validModes : fallbackModes);
          const health = (data?.provider_health && typeof data.provider_health === 'object')
            ? data.provider_health as ProviderHealth
            : {};
          setProviderHealth(health);
        }
      } catch {
        if (!cancelled) {
          setContextSupportedModes(fallbackModes);
          setProviderHealth({});
        }
      }
    };

    loadCapabilities();
    return () => { cancelled = true; };
  }, [effectiveSearchContext, searchContext]);

  // Keep active mode valid for current context
  useEffect(() => {
    if (contextSupportedModes.length === 0) return;
    if (!contextSupportedModes.includes(searchMode)) {
      setSearchMode(contextSupportedModes[0]);
    }
  }, [contextSupportedModes, searchMode, setSearchMode]);

  // MARKER_137.S1_3: Call unified backend for web/file contexts
  useEffect(() => {
    if (effectiveSearchContext === 'vetka' || !query.trim()) {
      setUnifiedResults([]);
      setUnifiedError(null);
      setUnifiedTotal(0);
      setUnifiedSearchTime(0);
      return;
    }

    // Clear previous debounce
    if (unifiedDebounceRef.current) {
      clearTimeout(unifiedDebounceRef.current);
    }

    setUnifiedLoading(true);
    setUnifiedError(null);

    unifiedDebounceRef.current = setTimeout(async () => {
      try {
        const mode = contextSupportedModes.includes(searchMode)
          ? searchMode
          : (contextSupportedModes[0] || 'keyword');
        let data: any;
        if (effectiveSearchContext === 'file') {
          // MARKER_150.FILE_API_SURFACE: file/ context uses dedicated file search endpoint.
          const fileMode = 'filename';
          const fileRes = await fetch(`${API_BASE}/search/file`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              query: query.trim(),
              limit: 20,
              mode: fileMode,
            }),
          });
          data = await fileRes.json();
          if (!fileRes.ok || data?.success === false) {
            throw new Error(data?.error || `HTTP ${fileRes.status}`);
          }
          data = {
            ...data,
            mode: fileMode,
            count: typeof data?.count === 'number' ? data.count : (Array.isArray(data?.results) ? data.results.length : 0),
          };
        } else {
          const viewportContext = cameraRef ? buildViewportContext(nodes, pinnedFileIds, cameraRef) : undefined;
          // Map context to unified sources
          const sourcesMap: Record<Exclude<SearchContext, 'myco'>, string[]> = {
            vetka: ['semantic', 'file'],
            web: ['web'],
            file: ['file'],
            cloud: [], // not implemented
            social: ['social'],
          };
          const sources = sourcesMap[effectiveSearchContext] || ['file', 'semantic'];
          const res = await fetch(`${API_BASE}/search/unified`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              query: query.trim(),
              limit: 20,
              sources,
              mode,
              // MARKER_146.STEP1_CONTEXTUAL_RETRIEVAL_REST: Pass always-on viewport context for web/file contextual rerank.
              viewport_context: viewportContext,
            }),
          });
          data = await res.json();
          if (!res.ok || data?.success === false) {
            throw new Error(data?.error || `HTTP ${res.status}`);
          }
        }

        const items = data.results || [];
        // Convert to SearchResult format
        const converted: SearchResult[] = items.map((item: any, idx: number) => {
          const source = String(item.source || '');
          const rawPath = String(item.path || item.url || item.title || '');
          // MARKER_139.S1_2_UNIFIED_ARTIFACT_FIX: /api/files/read expects project-relative path, not file:// URL
          const normalizedPath = source === 'file' && rawPath.startsWith('file://')
            ? rawPath.replace(/^file:\/\//, '')
            : rawPath;

          return {
            id: `unified-${source}-${idx}-${rawPath || item.title || 'result'}`,
            name: item.title?.split('/').pop() || item.title || 'Result',
            path: normalizedPath,
            type: source === 'web' ? 'doc' : 'code',
            relevance: item.score || 0.5,
            preview: item.snippet,
            source,
          };
        });
        setUnifiedResults(converted);
        setUnifiedTotal(typeof data.count === 'number' ? data.count : converted.length);
        setUnifiedSearchTime(typeof data.took_ms === 'number' ? data.took_ms : 0);

        const sourceErrors = data?.source_errors || {};
        if (Object.keys(sourceErrors).length > 0 && converted.length === 0) {
          const combined = Object.entries(sourceErrors)
            .map(([src, msg]) => `${src}: ${msg}`)
            .join(' | ');
          setUnifiedError(combined);
        }
      } catch (err) {
        console.error('[UnifiedSearchBar] Unified search error:', err);
        setUnifiedResults([]);
        setUnifiedTotal(0);
        setUnifiedSearchTime(0);
        setUnifiedError((err as Error).message || 'Unified search failed');
      } finally {
        setUnifiedLoading(false);
      }
    }, 300);

    return () => {
      if (unifiedDebounceRef.current) {
        clearTimeout(unifiedDebounceRef.current);
      }
    };
  }, [cameraRef, contextSupportedModes, effectiveSearchContext, nodes, pinnedFileIds, query, searchContext, searchMode]);

  // Focus input on mount if not compact
  useEffect(() => {
    if (!compact) {
      inputRef.current?.focus();
    }
  }, [compact]);

  // Clear selection when results change
  useEffect(() => {
    setSelectedIds(new Set());
    setLastSelectedIndex(null);
  }, [activeResults]);

  const [isFocused, setIsFocused] = useState(false);
  const [thinkingDots, setThinkingDots] = useState('.');
  const laneState = React.useMemo(() => resolveSearchLaneState({
    laneSurface,
    query,
    activeIsSearching,
    showContextMenu,
    isFocused,
    voiceState,
    onVoiceTrigger,
    searchContext: effectiveSearchContext,
    mycoHint,
    mycoStateKey,
    explicitAgentMode: searchContext === 'vetka' ? 'vetka' : searchContext === 'myco' ? 'myco' : undefined,
  }), [activeIsSearching, effectiveSearchContext, isFocused, laneSurface, mycoHint, mycoStateKey, onVoiceTrigger, query, searchContext, showContextMenu, voiceState]);
  const showVoiceTrigger = laneState.showVoiceTrigger;
  const showVoiceActivity = laneState.showVoiceActivity;
  const showThinkingIndicator = laneState.showThinkingIndicator;
  const showMycoTicker = laneState.showMycoTicker;
  const mycoTickerText = laneState.payload.body;
  const laneRoleVisual: LaneRoleVisual = searchContext === 'vetka' ? 'vetka' : searchContext === 'myco' ? 'myco' : 'context';
  const showLaneAvatar = !activeIsSearching;
  const mycoTickerWords = React.useMemo(
    () => mycoTickerText.split(/\s+/).filter(Boolean),
    [mycoTickerText],
  );
  const shouldAnimateMycoTicker = showMycoTicker && mycoTickerText.length > (compact ? 42 : 58);
  const mycoTickerAnimationSeconds = React.useMemo(
    () => (shouldAnimateMycoTicker ? Math.max(10, Number((mycoTickerWords.length * 0.7).toFixed(2))) : 0),
    [mycoTickerWords.length, shouldAnimateMycoTicker],
  );
  const mycoTickerPlaybackActive = showMycoTicker && !mycoTickerPlaybackDone;

  const mycoAvatarSrc = React.useMemo(() => {
    if (mycoAvatarState === 'speaking') return mycoSpeakingLoop;
    if (mycoAvatarState === 'thinking') return mycoThinkingLoop;
    if (mycoAvatarState === 'ready') return mycoReadySmile;
    return mycoIdleQuestion;
  }, [mycoAvatarState]);

  useEffect(() => {
    clearResultPreview();
  }, [activeIsSearching, clearResultPreview, laneState.mode, query, searchContext, showContextMenu]);

  useEffect(() => {
    clearMycoPreview();
  }, [clearMycoPreview, laneState.mode, mycoStateKey, query, searchContext, showContextMenu, showMycoTicker]);

  useEffect(() => {
    if (!pendingInputFocusRef.current) return;
    if (laneState.mode !== 'input') return;
    pendingInputFocusRef.current = false;
    window.requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
  }, [laneState.mode]);

  useEffect(() => {
    const clearTimers = () => {
      mycoAvatarTimersRef.current.forEach((timerId) => window.clearTimeout(timerId));
      mycoAvatarTimersRef.current = [];
    };

    if (!showLaneAvatar || laneRoleVisual === 'context') {
      clearTimers();
      setMycoAvatarState('idle');
      return;
    }

    if (laneState.mode === 'voice_thinking') {
      clearTimers();
      setMycoAvatarState('thinking');
      return;
    }

    if (laneState.mode === 'voice_listening' || laneState.mode === 'voice_speaking') {
      clearTimers();
      setMycoAvatarState('speaking');
      return;
    }

    if (laneState.mode === 'myco_guidance') {
      clearTimers();
      setMycoAvatarState(mycoTickerPlaybackActive ? 'speaking' : 'idle');
      return;
    }

    clearTimers();
    setMycoAvatarState('idle');

    return () => {
      clearTimers();
    };
  }, [laneRoleVisual, laneState.mode, mycoTickerPlaybackActive, showLaneAvatar]);

  useEffect(() => {
    if (!showThinkingIndicator) {
      setThinkingDots('.');
      return;
    }
    const t = window.setInterval(() => {
      setThinkingDots((prev) => (prev.length >= 3 ? '.' : `${prev}.`));
    }, 320);
    return () => window.clearInterval(t);
  }, [showThinkingIndicator]);

  useEffect(() => {
    setMycoTickerPlaybackDone(false);
    if (!showMycoTicker || mycoTickerWords.length === 0 || shouldAnimateMycoTicker) {
      setMycoVisibleWordCount(0);
      return;
    }
    setMycoVisibleWordCount(0);
    const timer = window.setInterval(() => {
      setMycoVisibleWordCount((prev) => {
        if (prev >= mycoTickerWords.length) return prev;
        return prev + 1;
      });
    }, 420);
    return () => window.clearInterval(timer);
  }, [showMycoTicker, mycoStateKey, mycoTickerWords, shouldAnimateMycoTicker]);

  useEffect(() => {
    if (!showMycoTicker || !shouldAnimateMycoTicker) return;
    setMycoTickerPlaybackDone(false);
    const timer = window.setTimeout(() => {
      setMycoTickerPlaybackDone(true);
    }, Math.round(mycoTickerAnimationSeconds * 1000));
    return () => window.clearTimeout(timer);
  }, [mycoStateKey, mycoTickerAnimationSeconds, showMycoTicker, shouldAnimateMycoTicker]);

  useEffect(() => {
    if (!showMycoTicker || shouldAnimateMycoTicker) return;
    if (mycoTickerWords.length === 0) {
      setMycoTickerPlaybackDone(true);
      return;
    }
    setMycoTickerPlaybackDone(mycoVisibleWordCount >= mycoTickerWords.length);
  }, [mycoTickerWords.length, mycoVisibleWordCount, showMycoTicker, shouldAnimateMycoTicker]);

  // Styles (Nolan dark minimal - grayscale only)
  const styles = {
    container: {
      padding: compact ? '6px 8px' : '8px 12px',
      borderBottom: '1px solid #222',
      background: '#0f0f0f',
      position: 'relative' as const,
      // Phase 69.4: Wider container - removed maxWidth constraint
      width: '100%',
      minWidth: '380px',
    },
    inputWrapper: {
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'stretch',
      gap: '4px',
      background: '#1a1a1a',
      borderRadius: '6px',
      padding: compact ? '6px 10px' : '8px 12px',
      borderWidth: '1px',
      borderStyle: 'solid',
      borderColor: '#333',
      transition: 'border-color 0.15s',
    },
    inputWrapperWithMyco: {
      minHeight: compact ? '42px' : '48px',
    },
    inputWrapperFocused: {
      borderColor: '#555',
    },
    inputRow: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      minWidth: 0,
      position: 'relative' as const,
      zIndex: 1,
    },
    contextPrefix: {
      color: '#555',
      fontSize: compact ? '12px' : '13px',
      fontFamily: 'monospace',
      userSelect: 'none' as const,
    },
    input: {
      flex: 1,
      background: 'transparent',
      border: 'none',
      outline: 'none',
      color: '#fff',
      fontSize: compact ? '12px' : '13px',
      fontFamily: 'inherit',
      minWidth: 0,
    },
    iconButton: {
      background: 'none',
      border: 'none',
      color: '#555',
      cursor: 'pointer',
      padding: '4px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '4px',
      transition: 'color 0.15s, background 0.15s',
    },
    mycoAvatarButton: {
      ...{
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        padding: 0,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '999px',
        position: 'relative' as const,
      },
      width: compact ? '22px' : '30px',
      height: compact ? '22px' : '30px',
      color: '#8a8a8a',
    },
    mycoAvatarImage: {
      width: compact ? '22px' : '26px',
      height: compact ? '22px' : '26px',
      objectFit: 'contain' as const,
      objectPosition: 'center' as const,
      display: 'block',
      filter: 'grayscale(0.12)',
    },
    vetkaAvatarIcon: {
      width: compact ? '22px' : '30px',
      height: compact ? '22px' : '30px',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#d7d7d7',
      opacity: mycoAvatarState === 'speaking' ? 1 : 0.9,
    },
    contextMenuIconSlot: {
      width: '26px',
      height: '26px',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    },
    contextMenuLogoImage: {
      width: '20px',
      height: '20px',
      objectFit: 'contain' as const,
      objectPosition: 'center' as const,
      display: 'block',
      filter: 'grayscale(0.12) brightness(0.9) contrast(0.92)',
      opacity: 0.72,
    },
    resultsContainer: {
      marginTop: '8px',
      maxHeight: compact ? '200px' : '350px',
      overflowY: 'auto' as const,
      background: '#1a1a1a',
      borderRadius: '6px',
      border: '1px solid #333',
    },
    resultItem: {
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      padding: compact ? '5px 9px' : '6px 10px',
      cursor: 'pointer',
      borderBottom: '1px solid #222',
      transition: 'background 0.15s',
    },
    resultItemSelected: {
      background: '#252525',
    },
    resultLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      flex: 1,
      minWidth: 0,
    },
    resultTypeIcon: {
      color: '#555',
      flexShrink: 0,
    },
    resultInfo: {
      flex: 1,
      minWidth: 0,
    },
    resultName: {
      color: '#fff',
      fontSize: compact ? '12px' : '12px',
      fontWeight: 500,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap' as const,
    },
    resultPath: {
      color: '#555',
      fontSize: compact ? '10px' : '10px',
      marginTop: '2px',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap' as const,
    },
    resultRight: {
      display: 'flex',
      alignItems: 'center',
      gap: '2px',
      flexShrink: 0,
    },
    resultRelevance: {
      color: '#666',
      fontSize: '10px',
      minWidth: '26px',
      textAlign: 'right' as const,
    },
    sortButton: {
      background: 'none',
      border: '1px solid #333',
      borderRadius: '3px',
      padding: '2px 6px',
      color: '#666',
      fontSize: '10px',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
    },
    sortMenu: {
      position: 'absolute' as const,
      bottom: '100%',
      right: '12px',
      background: '#1a1a1a',
      border: '1px solid #333',
      borderRadius: '4px',
      padding: '4px 0',
      zIndex: 1000,
    },
    sortMenuItem: {
      padding: '6px 12px',
      fontSize: '11px',
      color: '#888',
      cursor: 'pointer',
      transition: 'background 0.15s',
    },
    error: {
      color: '#888',
      fontSize: '12px',
      padding: '8px 12px',
      fontStyle: 'italic' as const,
    },
    disconnected: {
      color: '#666',
      fontSize: '11px',
      textAlign: 'center' as const,
      padding: '8px',
    },
    preview: {
      position: 'fixed' as const,
      background: '#1a1a1a',
      border: '1px solid #333',
      borderRadius: '6px',
      padding: '12px',
      maxWidth: '400px',
      maxHeight: '300px',
      overflow: 'auto',
      zIndex: 2000,
      boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
    },
    previewTitle: {
      color: '#fff',
      fontSize: '13px',
      fontWeight: 500,
      marginBottom: '8px',
      borderBottom: '1px solid #333',
      paddingBottom: '8px',
    },
    previewContent: {
      color: '#888',
      fontSize: '12px',
      fontFamily: 'monospace',
      whiteSpace: 'pre-wrap' as const,
      wordBreak: 'break-all' as const,
    },
    selectedCount: {
      color: '#888',
      fontSize: '10px',
      padding: '2px 6px',
      background: '#252525',
      borderRadius: '3px',
    },
    lanePrimaryText: {
      display: 'flex',
      alignItems: 'center',
      minWidth: 0,
      flex: 1,
      overflow: 'hidden',
    },
    mycoTickerText: {
      color: '#727272',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap' as const,
      flex: 1,
      fontFamily: 'monospace',
      fontSize: compact ? '12px' : '13px',
      lineHeight: 1.2,
      cursor: 'text',
    },
    mycoTickerMarquee: {
      display: 'inline-flex',
      alignItems: 'center',
      whiteSpace: 'nowrap' as const,
      minWidth: 'max-content',
      gap: '24px',
      animation: shouldAnimateMycoTicker ? `myco-marquee ${mycoTickerAnimationSeconds}s linear 1 both` : undefined,
      willChange: 'transform',
    },
    laneModeVoiceText: {
      color: '#8a8a8a',
      fontSize: compact ? '11px' : '12px',
      whiteSpace: 'nowrap' as const,
      userSelect: 'none' as const,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    },
  };

  // Phase 68.3: Get current context config
  const currentContext = SEARCH_CONTEXTS.find(c => c.id === searchContext) || SEARCH_CONTEXTS[0];
  const mycoTickerPreviewBody = laneState.payload.previewBody;
  const displayedMycoTickerText = showMycoTicker
    ? shouldAnimateMycoTicker
      ? mycoTickerText
      : mycoTickerWords.slice(0, mycoVisibleWordCount || 1).join(' ')
    : '';
  const laneIdlePlaceholderText = searchContext === 'vetka'
    ? getLaneIdlePlaceholderText('vetka', 'vetka')
    : searchContext === 'myco'
      ? getLaneIdlePlaceholderText('myco', 'myco')
      : 'tap text to search';
  const laneDisplayText = mycoTickerPlaybackDone
    ? laneIdlePlaceholderText
    : (displayedMycoTickerText || mycoTickerText);
  const deterministicSpeechText = mycoHint
    ? [mycoHint.body, ...mycoHint.nextActions.slice(0, 3)].filter(Boolean).join('. ').trim()
    : '';

  return (
    <div ref={laneRootRef} style={styles.container}>
      {/* Search Input */}
      <div
        style={{
          ...styles.inputWrapper,
          ...(showMycoTicker ? styles.inputWrapperWithMyco : {}),
          ...(isFocused ? styles.inputWrapperFocused : {}),
          position: 'relative',
        }}
      >
        <div style={styles.inputRow}>
          {/* MARKER_137.S1_3: Show loading for either WebSocket or unified search */}
          <span style={{ color: activeIsSearching ? '#888' : '#555' }}>
            {activeIsSearching ? (
              <LoadingSpinner />
            ) : showLaneAvatar ? (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (
                    laneRoleVisual === 'myco'
                    && deterministicSpeechText
                    && onSpeakText
                    && voiceState === 'idle'
                    && !activeIsSearching
                    && !showContextMenu
                    && !query.trim()
                  ) {
                    onSpeakText(deterministicSpeechText, 'myco', { autoListenAfter: true });
                    return;
                  }
                  if (laneRoleVisual !== 'context') {
                    onVoiceTrigger?.(laneRoleVisual === 'vetka' ? 'vetka' : 'myco');
                  }
                }}
                style={styles.mycoAvatarButton}
                onMouseEnter={(e) => {
                  e.currentTarget.style.opacity = '1';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.opacity = '0.92';
                }}
                title={
                  laneState.mode === 'myco_guidance'
                    ? (laneRoleVisual === 'vetka' ? 'vetka guidance' : 'myco guidance')
                    : laneState.mode === 'voice_thinking'
                      ? (laneRoleVisual === 'vetka' ? 'vetka is thinking' : 'myco is thinking')
                      : laneState.mode === 'voice_speaking'
                        ? (laneRoleVisual === 'vetka' ? 'vetka is speaking' : 'myco is speaking')
                        : laneState.mode === 'voice_listening'
                          ? (laneRoleVisual === 'vetka' ? 'vetka is listening' : 'myco is listening')
                          : laneRoleVisual === 'vetka'
                            ? 'vetka voice input'
                            : laneRoleVisual === 'myco'
                              ? 'myco voice input'
                              : `${searchContext} search`
                }
              >
                  {laneRoleVisual === 'vetka' ? (
                    <span aria-label="vetka" style={styles.vetkaAvatarIcon}>
                    <VetkaIcon size={compact ? 20 : 23} />
                  </span>
                ) : laneRoleVisual === 'myco' ? (
                  <img src={mycoAvatarSrc} alt="MYCO" style={styles.mycoAvatarImage} />
                ) : (
                  <span aria-label={searchContext} style={styles.vetkaAvatarIcon}>
                    {searchContext === 'vetka'
                      ? <VetkaIcon size={compact ? 20 : 23} />
                      : React.createElement(CONTEXT_ICONS[searchContext])}
                  </span>
                )}
              </button>
            ) : showVoiceActivity ? (
              <span
                title={voiceState === 'speaking' ? 'VETKA speaking' : 'VETKA listening'}
                style={{ display: 'inline-flex', alignItems: 'flex-end', gap: 2, height: 14 }}
              >
                {[0.5, 0.8, 0.6].map((k, i) => {
                  const h = Math.max(3, Math.min(12, Math.round(3 + (voiceLevel * 14 * k))));
                  return (
                    <span
                      key={`voice-bar-${i}`}
                      style={{
                        width: 2,
                        height: `${h}px`,
                        background: '#bcbcbc',
                        borderRadius: 2,
                        opacity: voiceState === 'speaking' ? 1 : 0.8,
                        transition: 'height 80ms linear',
                      }}
                    />
                  );
                })}
              </span>
            ) : (
              <SearchIcon />
            )}
          </span>

          {/* Phase 68.3: Clickable context prefix */}
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setShowContextMenu(!showContextMenu);
            }}
            style={{
              ...styles.contextPrefix,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '2px 4px',
              borderRadius: 3,
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#252525';
              e.currentTarget.style.color = '#888';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = '#555';
            }}
            title="Change search context"
          >
            {currentContext.prefix}
          </button>

          {laneState.mode === 'input' ? (
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (e.target.value === '') {
                  setShowContextMenu(true);
                } else {
                  setShowContextMenu(false);
                }
              }}
              onKeyDown={handleKeyDown}
              onFocus={() => {
                setIsFocused(true);
                if (!query) {
                  setShowContextMenu(true);
                }
              }}
              onBlur={() => {
                setIsFocused(false);
                setTimeout(() => setShowContextMenu(false), 200);
              }}
              placeholder={
                showVoiceTrigger
                  ? laneState.payload.previewBody || 'Tap mic to talk...'
                  : placeholder
              }
              style={styles.input}
            />
          ) : laneState.mode === 'myco_guidance' ? (
            <div
              data-testid="myco-search-lane"
              style={styles.lanePrimaryText}
              onClick={() => {
                pendingInputFocusRef.current = true;
                setIsFocused(true);
              }}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                mycoPreviewTimerRef.current = window.setTimeout(() => {
                  setMycoPreviewPosition(
                    getPreviewPlacement(rect, LANE_PREVIEW_WIDTH, LANE_PREVIEW_HEIGHT, { belowAnchor: true, extraYOffset: 6 }),
                  );
                  setShowMycoPreview(true);
                }, 300);
              }}
              onMouseLeave={() => {
                clearMycoPreview();
              }}
              title={mycoHint?.title || 'Current guidance'}
            >
              {shouldAnimateMycoTicker ? (
                <span style={styles.mycoTickerText}>
                  {mycoTickerPlaybackDone ? (
                    laneIdlePlaceholderText
                  ) : (
                    <span style={styles.mycoTickerMarquee}>
                      <span>{renderMycoTokenizedText(mycoTickerText)}</span>
                      <span>{renderMycoTokenizedText(mycoTickerText)}</span>
                    </span>
                  )}
                </span>
              ) : (
                <span style={styles.mycoTickerText}>
                  {renderMycoTokenizedText(laneDisplayText)}
                </span>
              )}
            </div>
          ) : (
            <div style={styles.lanePrimaryText}>
              <span style={styles.laneModeVoiceText}>
                {laneState.mode === 'voice_listening'
                  ? 'VETKA is listening'
                  : laneState.mode === 'voice_speaking'
                    ? 'VETKA is speaking'
                    : `VETKA is thinking${thinkingDots}`}
              </span>
            </div>
          )}

          {query && (
            <button
              onClick={clearResults}
              style={{ ...styles.iconButton, color: '#888' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
              title="Clear search"
            >
              <CloseIcon />
            </button>
          )}

        </div>

        {/* Phase 68.3: Context selector dropdown - vetka/ active, others need backend */}
        {showContextMenu && !query && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: 4,
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: 6,
            padding: '4px 0',
            zIndex: 1000,
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
          }}>
            {SEARCH_CONTEXTS.map(ctx => {
              const IconComponent = CONTEXT_ICONS[ctx.id];
              return (
                <div
                  key={ctx.id}
                  onClick={() => {
                    if (ctx.available) {
                      setSearchContext(ctx.id);
                      onSearchContextChange?.(ctx.id);
                      setShowContextMenu(false);
                      inputRef.current?.focus();
                    } else if (mycoSurfaceScope) {
                      // MARKER_163A.MODE_A.SEARCH.DISABLED_CONTEXT_REDIRECT.V1:
                      // Surface guide listens to disabled context attempts and redirects users to runnable modes.
                      window.dispatchEvent(new CustomEvent('vetka-myco-search-context-attempt', {
                        detail: {
                          scope: mycoSurfaceScope,
                          context: ctx.id,
                          available: false,
                        },
                      }));
                    }
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    cursor: ctx.available ? 'pointer' : 'not-allowed',
                    opacity: ctx.available ? 1 : 0.5,
                    background: searchContext === ctx.id ? '#252525' : 'transparent',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={(e) => {
                    if (ctx.available) e.currentTarget.style.background = '#252525';
                  }}
                  onMouseLeave={(e) => {
                    if (ctx.available && searchContext !== ctx.id) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <span
                    style={{
                      ...styles.contextMenuIconSlot,
                      color: ctx.available ? '#888' : '#555',
                    }}
                  >
                    {ctx.id === 'vetka' ? (
                      <VetkaIcon size={20} />
                    ) : ctx.id === 'myco' ? (
                      <img src={mycoIdleQuestion} alt="MYCO" style={styles.contextMenuLogoImage} />
                    ) : (
                      <IconComponent />
                    )}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div style={{ color: ctx.available ? '#fff' : '#666', fontSize: 12, fontWeight: 500 }}>
                      {ctx.prefix}
                    </div>
                    <div style={{ color: '#555', fontSize: 10 }}>
                      {ctx.description}
                      {!ctx.available && ' (coming soon)'}
                    </div>
                  </div>
                  {searchContext === ctx.id && (
                    <span style={{ color: '#888', fontSize: 12 }}>✓</span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Phase 68.3: Selected file path breadcrumb */}
      {selectedFilePath && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginTop: 4,
          padding: '4px 8px',
          background: '#1a1a1a',
          borderRadius: 4,
          fontSize: 10,
          color: '#666',
          overflow: 'hidden',
        }}>
          <span style={{ color: '#555', display: 'flex', alignItems: 'center' }}><LocationIcon /></span>
          <span style={{
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontFamily: 'monospace',
          }} title={selectedFilePath}>
            {currentContext.prefix}{selectedFilePath}
          </span>
          <button
            onClick={() => setSelectedFilePath(null)}
            style={{
              background: 'none',
              border: 'none',
              color: '#555',
              cursor: 'pointer',
              padding: 2,
              fontSize: 10,
              lineHeight: 1,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#555')}
          >
            ✕
          </button>
        </div>
      )}

      {/* Connection status */}
      {!isConnected && effectiveSearchContext === 'vetka' && (
        <div style={styles.disconnected}>Connecting to server...</div>
      )}

      {searchContext === 'web' && Object.keys(providerHealth).length > 0 && !webHasAnyProvider && (
        <div style={styles.error}>
          Web provider unavailable: configure Tavily or Serper key
        </div>
      )}

      {/* Error */}
      {activeError && <div style={styles.error}>{activeError}</div>}

      {/* Phase 68.3: Search mode + sort controls - single row, no wrap */}
      {query && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          marginTop: '6px',
          position: 'relative',
        }}>
          {/* Phase 95: Active mode indicator + mode buttons (hidden in /file context) */}
          {searchContext !== 'file' && (
            <span style={{
              fontSize: '9px',
              color: '#fff',
              background: '#444',
              padding: '3px 6px',
              borderRadius: '3px',
              fontWeight: 600,
              letterSpacing: '0.5px',
              flexShrink: 0,
            }} title={`Active mode: ${SEARCH_MODE_LABELS[searchMode]}`}>
              {searchMode === 'hybrid' && 'HYB'}
              {searchMode === 'semantic' && 'SEM'}
              {searchMode === 'keyword' && 'KEY'}
              {searchMode === 'filename' && 'FILE'}
            </span>
          )}
          {searchContext !== 'file' && contextSupportedModes.map((mode) => {
            // Short labels for compact display
            const shortLabels: Record<SearchModeType, string> = {
              hybrid: 'HYB',
              semantic: 'SEM',
              keyword: 'KEY',
              filename: 'FILE',
            };
            return (
              <button
                key={mode}
                onClick={() => setSearchMode(mode)}
                title={`${SEARCH_MODE_LABELS[mode]}: ${SEARCH_MODE_DESCRIPTIONS[mode]}`}
                style={{
                  padding: '2px 5px',
                  fontSize: '9px',
                  fontWeight: searchMode === mode ? 600 : 400,
                  color: searchMode === mode ? '#fff' : '#555',
                  background: searchMode === mode ? '#333' : 'transparent',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  borderColor: searchMode === mode ? '#444' : '#2a2a2a',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  letterSpacing: '0.5px',
                }}
                onMouseEnter={(e) => {
                  if (searchMode !== mode) {
                    e.currentTarget.style.background = '#222';
                    e.currentTarget.style.borderColor = '#333';
                    e.currentTarget.style.color = '#888';
                  }
                }}
                onMouseLeave={(e) => {
                  if (searchMode !== mode) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.borderColor = '#2a2a2a';
                    e.currentTarget.style.color = '#555';
                  }
                }}
              >
                {shortLabels[mode]}
              </button>
            );
          })}

          {/* Separator */}
          {searchContext !== 'file' && <span style={{ color: '#333', margin: '0 2px' }}>|</span>}

          {/* Stats - compact */}
          <span style={{ fontSize: '10px', color: '#555', whiteSpace: 'nowrap', flexShrink: 0 }}>
            {activeIsSearching ? '...' : `${activeTotalResults}`}
          </span>

          {activeSearchTime > 0 && (
            <span style={{ fontSize: '9px', color: '#444', whiteSpace: 'nowrap', flexShrink: 0 }}>{activeSearchTime}ms</span>
          )}

          {selectedIds.size > 0 && (
            <span style={{ ...styles.selectedCount, flexShrink: 0 }}>{selectedIds.size}sel</span>
          )}

          {/* Phase 95: Sort direction toggle - Finder style (before sort dropdown) */}
          <button
            onClick={() => setSortAscending(!sortAscending)}
            title={sortAscending ? 'Ascending (smallest/oldest first)' : 'Descending (largest/newest first)'}
            style={{
              background: 'transparent',
              border: '1px solid #333',
              borderRadius: '4px',
              padding: '4px 6px',
              color: '#666',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s',
              minWidth: '24px',
              minHeight: '22px',
              fontSize: '12px',
              flexShrink: 0,
              marginLeft: 'auto',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#333';
              e.currentTarget.style.color = '#fff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = '#666';
            }}
          >
            {sortAscending ? '↑' : '↓'}
          </button>

          {/* Phase 95: Sort dropdown - icon only (at edge) - handlers implemented */}
          <div style={{ position: 'relative', flexShrink: 0 }}>
            <button
              style={{
                background: showSortMenu ? '#333' : 'transparent',
                border: '1px solid #333',
                borderRadius: '4px',
                padding: '4px 6px',
                color: showSortMenu ? '#fff' : '#666',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s',
                minWidth: '28px',
                minHeight: '22px',
              }}
              onClick={() => setShowSortMenu(!showSortMenu)}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#333';
                e.currentTarget.style.color = '#fff';
              }}
              onMouseLeave={(e) => {
                if (!showSortMenu) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = '#666';
                }
              }}
              title={`Sort by: ${sortMode}`}
            >
              <SortIcon />
            </button>

            {showSortMenu && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '4px',
                background: '#1a1a1a',
                border: '1px solid #444',
                borderRadius: '4px',
                padding: '4px 0',
                zIndex: 9999,
                minWidth: '110px',
                boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
              }}>
                {(['relevance', 'name', 'type', 'date', 'size'] as SortMode[]).map(mode => (
                  <div
                    key={mode}
                    style={{
                      padding: '6px 12px',
                      fontSize: '11px',
                      color: sortMode === mode ? '#fff' : '#888',
                      background: sortMode === mode ? '#252525' : 'transparent',
                      cursor: 'pointer',
                      transition: 'background 0.15s',
                    }}
                    onClick={() => {
                      setSortMode(mode);
                      setShowSortMenu(false);
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#252525')}
                    onMouseLeave={(e) => {
                      if (sortMode !== mode) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    {mode.charAt(0).toUpperCase() + mode.slice(1)}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TODO_CAM_UI: Add CAM suggestions panel here (backend: /api/cam/suggestions)
          Display contextually relevant files based on CAM activation levels.
          Should show hot/warm/cold memory nodes alongside search results.
          Integration: GET /api/cam/suggestions?context={searchContext}&limit=5
          Display as separate section above results with "From Context Memory" header. */}

      {/* Results */}
      {sortedResults.length > 0 && (
        <div ref={resultsRef} style={styles.resultsContainer}>
          {sortedResults.map((result, index) => {
            const isSelected = selectedIds.has(result.id);
            const pinned = isPinned(result);
            const isWebRow = String(result.source || '').startsWith('web') || /^https?:\/\//i.test(result.path);
            const isFileRow = searchContext === 'file';
            const isVetkaRow = effectiveSearchContext === 'vetka';
            const useExpandedText = isWebRow || isFileRow || isVetkaRow;
            const showMetaColumns = !isWebRow && isFileRow;

            return (
              <div
                key={result.id}
                style={{
                  ...styles.resultItem,
                  ...(isSelected ? styles.resultItemSelected : {}),
                  background: isSelected ? '#252525' : 'transparent',
                }}
                onClick={(e) => handleSelect(result, index, e)}
                onMouseEnter={(e) => {
                  if (!isSelected) e.currentTarget.style.background = '#1f1f1f';
                  handleMouseEnter(result, e);
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) e.currentTarget.style.background = 'transparent';
                  handleMouseLeave();
                }}
              >
                <div style={styles.resultLeft}>
                  <span style={styles.resultTypeIcon}>{getTypeIcon(result.type)}</span>
                  <div style={styles.resultInfo}>
                    <div
                      style={{
                        ...styles.resultName,
                        ...(useExpandedText ? {
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical' as const,
                          whiteSpace: 'normal' as const,
                          lineHeight: 1.18,
                          overflow: 'hidden',
                        } : {}),
                      }}
                    >
                      {result.name}
                    </div>
                    <div
                      style={{
                        ...styles.resultPath,
                        ...(useExpandedText ? {
                          display: '-webkit-box',
                          WebkitLineClamp: isFileRow ? 2 : 1,
                          WebkitBoxOrient: 'vertical' as const,
                          whiteSpace: 'normal' as const,
                          overflowWrap: 'anywhere' as const,
                          lineHeight: 1.18,
                          marginTop: '2px',
                        } : {}),
                      }}
                    >
                      {result.path}
                    </div>
                  </div>
                </div>

                <div style={styles.resultRight}>
                  {/* Phase 95: Source badge display */}
                  {result.source && !isWebRow && !isFileRow && (
                    <span style={{
                      fontSize: '8px',
                      color: '#888',
                      background: '#252525',
                      padding: '2px 4px',
                      borderRadius: '2px',
                      fontWeight: 600,
                      letterSpacing: '0.5px',
                      marginRight: '4px',
                    }}>
                      {result.source === 'qdrant' && 'QD'}
                      {result.source === 'qdrant_filename' && 'QDF'}
                      {result.source === 'weaviate' && 'WV'}
                      {result.source === 'hybrid' && 'HYB'}
                      {!['qdrant', 'qdrant_filename', 'weaviate', 'hybrid'].includes(result.source) && result.source?.toUpperCase().slice(0, 3)}
                    </span>
                  )}

                  {/* MARKER_161.P2_DENSITY: keep size/date only in file/ mode to free width in vetka/web lists */}
                  {showMetaColumns && (
                    <span style={{ color: '#666', fontSize: '10px', minWidth: '42px', textAlign: 'right' as const }}>
                      {formatBytes(result.size || 0)}
                    </span>
                  )}
                  {showMetaColumns && (
                    <span style={{ color: '#666', fontSize: '10px', minWidth: '48px', textAlign: 'right' as const }}>
                      {formatDate(result.modified_time || 0)}
                    </span>
                  )}

                  {/* Show relevance % or type based on sort mode */}
                  {(sortMode === 'relevance' || sortMode === 'name') && !isWebRow && (
                    <span style={styles.resultRelevance}>
                      {Math.round(result.relevance * 100)}%
                    </span>
                  )}
                  {sortMode === 'type' && !isWebRow && (
                    <span style={{ ...styles.resultRelevance, fontFamily: 'monospace', minWidth: '40px' }}>
                      .{result.name.split('.').pop() || '?'}
                    </span>
                  )}

                  {/* Artifact button */}
                  {onOpenArtifact && (
                    <button
                      onClick={(e) => handleArtifact(e, result)}
                      style={{ ...styles.iconButton, color: '#444' }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#888')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = '#444')}
                      title="View content"
                    >
                      <ChestIcon />
                    </button>
                  )}

                  {/* Pin button with filled state */}
                  <button
                    onClick={(e) => handlePin(e, result)}
                    style={{
                      ...styles.iconButton,
                      color: pinned ? '#fff' : '#555',
                      background: pinned ? '#333' : 'transparent',
                    }}
                    onMouseEnter={(e) => {
                      if (!pinned) e.currentTarget.style.color = '#fff';
                    }}
                    onMouseLeave={(e) => {
                      if (!pinned) e.currentTarget.style.color = '#555';
                    }}
                    title={pinned ? 'Unpin from context' : 'Pin to context'}
                  >
                    <PinIcon filled={pinned} />
                  </button>
                </div>
              </div>
            );
          })}

        </div>
      )}

      {/* Load more button */}
      {hasMoreActive && sortedResults.length > 0 && (
        <button
          onClick={loadMore}
          style={{
            width: '100%',
            padding: '8px 12px',
            marginTop: '4px',
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: '4px',
            color: '#888',
            fontSize: '12px',
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#252525';
            e.currentTarget.style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#1a1a1a';
            e.currentTarget.style.color = '#888';
          }}
        >
          Load more ({Math.max(activeResults.length - displayLimit, 0)} remaining)
        </button>
      )}

      {/* No results message */}
      {query && !activeIsSearching && sortedResults.length === 0 && !activeError && (
        <div style={styles.error}>No results found</div>
      )}

      {/* Phase 68.3: Enhanced hover preview with metadata */}
      {typeof document !== 'undefined' && hoveredResult && previewPosition && createPortal(
        <div
          ref={resultPreviewRef}
          style={{
            ...styles.preview,
            left: previewPosition.x,
            top: previewPosition.y,
            zIndex: 10000,
          }}
        >
          <div style={styles.previewTitle}>{hoveredResult.name}</div>

          <div style={{
            display: 'flex',
            gap: 12,
            fontSize: 10,
            color: '#666',
            marginBottom: 8,
            paddingBottom: 8,
            borderBottom: '1px solid #333',
          }}>
            <span>Type: <b style={{ color: '#888' }}>{hoveredResult.type}</b></span>
            <span>Ext: <b style={{ color: '#888' }}>.{hoveredResult.name.split('.').pop() || '?'}</b></span>
            <span>Score: <b style={{ color: '#888' }}>{Math.round(hoveredResult.relevance * 100)}%</b></span>
            {hoveredResult.modified_time ? (
              <span>Modified: <b style={{ color: '#888' }}>{new Date(hoveredResult.modified_time * 1000).toLocaleDateString('ru-RU')}</b></span>
            ) : null}
          </div>

          <div style={{ fontSize: 10, color: '#555', marginBottom: 8, wordBreak: 'break-all' }}>
            {hoveredResult.path}
          </div>

          <div style={styles.previewContent}>
            {hoveredResult.preview || 'No preview available'}
          </div>
        </div>,
        document.body,
      )}

      {typeof document !== 'undefined' && showMycoPreview && mycoPreviewPosition && mycoHint && createPortal(
        <div
          ref={mycoPreviewRef}
          style={{
            ...styles.preview,
            left: mycoPreviewPosition.x,
            top: mycoPreviewPosition.y,
            maxWidth: '440px',
            zIndex: 10000,
          }}
        >
          <div style={styles.previewTitle}>{mycoHint.title}</div>
          <div style={styles.previewContent}>
            {renderMycoTokenizedText(mycoTickerPreviewBody || mycoTickerText)}
          </div>
        </div>,
        document.body,
      )}

      {/* CSS for spinner animation */}
      <style>{`
        .search-spinner {
          animation: search-spin 1s linear infinite;
        }
        @keyframes search-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes myco-marquee {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
}

export default UnifiedSearchBar;
