/**
 * Custom hook for debounced search with WebSocket integration.
 * Handles semantic/hybrid/keyword/filename search modes with pagination.
 *
 * @status active
 * @phase 96
 * @depends react, useSocket
 * @used_by UnifiedSearchBar, SearchPanel
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useSocket } from './useSocket';
import type { SearchResult, SearchResponse, SearchError } from '../types/chat';

// Phase 68.2: Constants for pagination
const PAGE_SIZE = 20;

interface UseSearchOptions {
  /** Debounce delay in milliseconds (default: 300) */
  debounceMs?: number;
  /** Maximum results to return (default: 100) - Phase 68.2 increased */
  defaultLimit?: number;
  /** Search mode: hybrid, semantic, keyword, or filename (default: hybrid) */
  defaultMode?: 'hybrid' | 'semantic' | 'keyword' | 'filename';
  /** Auto-search when query changes (default: true) */
  autoSearch?: boolean;
  /** Minimum relevance score filter (default: 0.3) - Phase 68.2 */
  minScore?: number;
}

interface UseSearchReturn {
  /** Current search query */
  query: string;
  /** Set search query */
  setQuery: (q: string) => void;
  /** Search results */
  results: SearchResult[];
  /** Loading state */
  isSearching: boolean;
  /** Error message */
  error: string | null;
  /** Total results count */
  totalResults: number;
  /** Search time in milliseconds */
  searchTime: number;
  /** Search mode actually used */
  searchMode: 'hybrid' | 'semantic' | 'keyword' | 'filename';
  /** Set search mode */
  setSearchMode: (mode: 'hybrid' | 'semantic' | 'keyword' | 'filename') => void;
  /** Clear results and query */
  clearResults: () => void;
  /** Manual search trigger */
  search: (customQuery?: string) => void;
  /** Socket connection state */
  isConnected: boolean;
  /** Current display limit */
  displayLimit: number;
  /** Load more results (increase display limit) */
  loadMore: () => void;
  /** Whether more results can be loaded */
  hasMore: boolean;
}

export function useSearch(options: UseSearchOptions = {}): UseSearchReturn {
  const {
    debounceMs = 300,
    defaultLimit = 100,  // Phase 68.2: Increased from 10 to 100
    defaultMode = 'hybrid',
    autoSearch = true,
    minScore = 0.3  // Phase 68.2: Default score threshold
  } = options;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalResults, setTotalResults] = useState(0);
  const [searchTime, setSearchTime] = useState(0);
  const [searchMode, setSearchMode] = useState<'hybrid' | 'semantic' | 'keyword' | 'filename'>(defaultMode);

  // Phase 68.2: Pagination state - show 20 initially, load 20 more on "Load more"
  const [displayLimit, setDisplayLimit] = useState(PAGE_SIZE);

  // Refs must come after all useState calls
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastQueryRef = useRef<string>('');

  const { searchQuery, isConnected } = useSocket();

  // Listen for search results via custom events from useSocket
  // Note: CAM suggestions available via /api/cam/suggestions - not yet integrated
  useEffect(() => {
    const handleResults = (event: CustomEvent<SearchResponse>) => {
      const data = event.detail;

      // Only process if this matches our last query
      if (data.query !== lastQueryRef.current) {
        return;
      }

      setResults(data.results);
      setTotalResults(data.total);
      setSearchTime(data.took_ms);
      // Phase 95: Track actual search mode used - exposed via searchMode in return value
      const mode = data.mode as 'hybrid' | 'semantic' | 'keyword' | 'filename' | undefined;
      setSearchMode(mode && ['hybrid', 'semantic', 'keyword', 'filename'].includes(mode) ? mode : defaultMode);
      setIsSearching(false);
      setError(null);
    };

    const handleError = (event: CustomEvent<SearchError>) => {
      const data = event.detail;

      // Only process if this matches our last query
      if (data.query !== lastQueryRef.current) {
        return;
      }

      setError(data.error);
      setIsSearching(false);
      setResults([]);
    };

    window.addEventListener('search-results', handleResults as EventListener);
    window.addEventListener('search-error', handleError as EventListener);

    return () => {
      window.removeEventListener('search-results', handleResults as EventListener);
      window.removeEventListener('search-error', handleError as EventListener);
    };
  }, [defaultMode]);

  // Debounced search execution
  const executeSearch = useCallback((searchText: string, mode?: 'hybrid' | 'semantic' | 'keyword' | 'filename') => {
    const trimmed = searchText.trim();

    if (!trimmed) {
      setResults([]);
      setIsSearching(false);
      setTotalResults(0);
      setSearchTime(0);
      return;
    }

    if (!isConnected) {
      setError('Not connected to server');
      setIsSearching(false);
      return;
    }

    lastQueryRef.current = trimmed;
    setIsSearching(true);
    setError(null);

    // Use provided mode, or current searchMode, or defaultMode as fallback
    // Phase 68.2: Pass minScore for server-side filtering
    searchQuery(trimmed, defaultLimit, mode || searchMode, {}, minScore);
  }, [searchQuery, defaultLimit, searchMode, isConnected, minScore]);

  // Auto-search with debounce when query changes
  useEffect(() => {
    if (!autoSearch) return;

    // Clear previous debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Empty query - clear immediately
    if (!query.trim()) {
      setResults([]);
      setIsSearching(false);
      setTotalResults(0);
      return;
    }

    // Set searching state for UI feedback
    setIsSearching(true);

    // Debounce the actual search
    debounceRef.current = setTimeout(() => {
      executeSearch(query);
    }, debounceMs);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, debounceMs, autoSearch, executeSearch]);

  // Manual search function
  const search = useCallback((customQuery?: string, mode?: 'hybrid' | 'semantic' | 'keyword' | 'filename') => {
    const searchText = customQuery ?? query;
    executeSearch(searchText, mode);
  }, [query, executeSearch]);

  // Re-search when mode changes (if there's an active query)
  useEffect(() => {
    if (query.trim() && isConnected) {
      executeSearch(query);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchMode]);

  // Clear everything
  const clearResults = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    setQuery('');
    setResults([]);
    setError(null);
    setTotalResults(0);
    setSearchTime(0);
    setIsSearching(false);
    setDisplayLimit(PAGE_SIZE); // Reset pagination
    lastQueryRef.current = '';
  }, []);

  // Phase 68.2: Load more results (pagination)
  const loadMore = useCallback(() => {
    setDisplayLimit(prev => prev + PAGE_SIZE);
  }, []);

  // Phase 68.2: Check if there are more results to load (using useMemo for consistency)
  const hasMore = useMemo(() => results.length > displayLimit, [results.length, displayLimit]);

  // Reset display limit when query changes
  useEffect(() => {
    setDisplayLimit(PAGE_SIZE);
  }, [query]);

  return {
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
    search,
    isConnected,
    displayLimit,
    loadMore,
    hasMore
  };
}

export default useSearch;
