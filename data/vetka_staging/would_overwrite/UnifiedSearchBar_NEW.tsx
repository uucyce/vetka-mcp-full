// MARKER_102_3_START
const MicIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);
// MARKER_102_3_END

// MARKER_102_3_START
export function UnifiedSearchBar({
  onSelectResult,
  onPinResult,
  onOpenArtifact,
  placeholder = "Search...",
  contextPrefix = "",
  compact = false,
}: Props) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [sortMode, setSortMode] = useState<SortMode>('relevance');
  const [searchMode, setSearchMode] = useState<SearchModeType>('hybrid');
  const [activeContext, setActiveContext] = useState<SearchContext>('vetka');
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [showSortMenu, setShowSortMenu] = useState(false);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const modeMenuRef = useRef<HTMLDivElement>(null);
  const sortMenuRef = useRef<HTMLDivElement>(null);
  
  const { results, isLoading, error, search } = useSearch();
  const { addMessage, currentChatId } = useStore();

  // Handle search input changes
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    
    if (value.trim()) {
      search(value, activeContext, searchMode);
      setShowResults(true);
    } else {
      setShowResults(false);
    }
  }, [search, activeContext, searchMode]);

  // Clear search query
  const handleClear = useCallback(() => {
    setQuery("");
    setShowResults(false);
    inputRef.current?.focus();
  }, []);

  // Handle input focus
  const handleFocus = useCallback(() => {
    setIsFocused(true);
    if (query.trim()) {
      setShowResults(true);
    }
  }, [query]);

  // Handle input blur
  const handleBlur = useCallback(() => {
    setIsFocused(false);
    // Delay hiding results to allow menu interactions
    setTimeout(() => {
      if (!resultsRef.current?.matches(":hover")) {
        setShowResults(false);
      }
    }, 200);
  }, []);

  // MARKER_102_3_START
  // Handle voice input activation
  const handleVoiceInput = useCallback(() => {
    // Voice input implementation would go here
    console.log("Voice input activated");
  }, []);
  // MARKER_102_3_END

  // ... rest of the component implementation
// MARKER_102_3_END