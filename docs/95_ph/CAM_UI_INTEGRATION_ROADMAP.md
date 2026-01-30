# CAM UI INTEGRATION ROADMAP
**Phase 95: Comprehensive Implementation Plan**
**Date:** 2026-01-26
**Status:** Architecture Review Complete

---

## Executive Summary

This document bridges Grok's UI/UX recommendations with VETKA's existing CAM engine implementation to create a practical implementation roadmap.

### Key Findings
1. **CAM Engine is robust** - Full activation scoring, branching, merging, and pruning logic already implemented
2. **Missing piece:** No API exposure to frontend - backend is ready but no REST endpoints exist
3. **Tool Memory ready:** CAMToolMemory (Phase 75.1) already tracks VETKA tool usage patterns
4. **Next step:** Create API routes and React components per Grok's recommendations

---

## Architecture Overview

### Existing Backend (cam_engine.py)

#### Core Classes
```python
# VETKANode - Represents memory nodes with activation scores
@dataclass
class VETKANode:
    id: str
    path: str
    activation_score: float  # 0.0-1.0
    is_marked_for_deletion: bool
    created_at: datetime
    last_accessed: datetime
    metadata: Dict[str, Any]

# VETKACAMEngine - Main CAM orchestrator
class VETKACAMEngine:
    # Thresholds
    SIMILARITY_THRESHOLD_NOVEL = 0.7
    SIMILARITY_THRESHOLD_MERGE = 0.92
    ACTIVATION_THRESHOLD_PRUNE = 0.2

    # Methods
    calculate_activation_score(branch_id) -> float
    handle_new_artifact(artifact_path, metadata) -> CAMOperation
    prune_low_entropy(threshold=0.2) -> List[str]
    merge_similar_subtrees(threshold=0.92) -> List[Tuple]

# CAMToolMemory - JARVIS-style tool suggestions (Phase 75.1)
class CAMToolMemory:
    record_tool_use(tool_name, context, success)
    suggest_tool(context, top_n=3) -> List[Tuple[str, float]]
    get_jarvis_hint(context) -> Optional[str]
```

#### Activation Score Formula
```python
score = avg_relevance + connectivity_bonus + recency_bonus

# avg_relevance: cosine similarity to recent queries
# connectivity_bonus: min(0.2, len(children) * 0.02)
# recency_bonus: max(0, 0.1 * (1 - time_since_access / 86400))
```

#### Hot/Warm/Cold Classification
Based on `activation_score`:
- **Hot:** score >= 0.7 (frequently accessed, highly relevant)
- **Warm:** 0.4 <= score < 0.7 (moderately relevant)
- **Cold:** score < 0.4 (rarely used, prune candidate)

---

## Grok's Recommendations (Aligned with Backend)

### 1. API Endpoints Design

#### Endpoint: GET /api/cam/suggestions
**Purpose:** Get context-aware memory suggestions

**Implementation:**
```python
# File: src/api/routes/cam_routes.py
@router.get("/api/cam/suggestions")
async def get_cam_suggestions(
    user_id: str,
    context_id: Optional[str] = None,
    limit: int = 10
):
    cam_engine = get_cam_engine()

    # Get nodes sorted by activation score
    nodes = sorted(
        cam_engine.nodes.values(),
        key=lambda n: n.activation_score,
        reverse=True
    )[:limit]

    # Classify as hot/warm/cold
    suggestions = []
    for node in nodes:
        status = classify_activation_level(node.activation_score)
        suggestions.append({
            'id': node.id,
            'title': node.name,
            'path': node.path,
            'activationScore': round(node.activation_score, 3),
            'status': status,  # 'hot', 'warm', 'cold'
            'relevanceReason': get_relevance_reason(node),
            'lastAccessed': node.last_accessed.isoformat()
        })

    return {'suggestions': suggestions}

def classify_activation_level(score: float) -> str:
    if score >= 0.7:
        return 'hot'
    elif score >= 0.4:
        return 'warm'
    else:
        return 'cold'
```

#### Endpoint: GET /api/cam/node/{id}
**Purpose:** Get detailed node information

**Backend mapping:**
```python
@router.get("/api/cam/node/{node_id}")
async def get_node_details(node_id: str):
    cam_engine = get_cam_engine()

    if node_id not in cam_engine.nodes:
        raise HTTPException(status_code=404)

    node = cam_engine.nodes[node_id]

    # Get linked nodes (children + similar nodes)
    linked_nodes = []
    for child_id in node.children:
        if child_id in cam_engine.nodes:
            linked_nodes.append({
                'id': child_id,
                'name': cam_engine.nodes[child_id].name,
                'relationship': 'child'
            })

    # Find similar nodes via embedding similarity
    similar_nodes = find_similar_nodes(node, cam_engine, top_k=5)

    return {
        'id': node.id,
        'path': node.path,
        'name': node.name,
        'activationScore': node.activation_score,
        'status': classify_activation_level(node.activation_score),
        'linkedNodes': linked_nodes,
        'similarNodes': similar_nodes,
        'metadata': node.metadata,
        'activationHistory': get_activation_history(node_id)
    }
```

#### Endpoint: POST /api/cam/feedback
**Purpose:** Record user reactions (emoji boosts)

**Backend mapping:**
```python
@router.post("/api/cam/feedback")
async def record_feedback(
    node_id: str,
    user_id: str,
    reaction_type: str,  # '👍', '❤️', '💡', '❌'
    weight_adjustment: Optional[float] = None
):
    cam_engine = get_cam_engine()

    if node_id not in cam_engine.nodes:
        raise HTTPException(status_code=404)

    node = cam_engine.nodes[node_id]

    # Map emojis to weight adjustments
    emoji_weights = {
        '👍': 0.2,
        '❤️': 0.3,
        '💡': 0.25,
        '❌': -0.1
    }

    adjustment = weight_adjustment or emoji_weights.get(reaction_type, 0.1)

    # Update activation score (capped at 1.0)
    old_score = node.activation_score
    new_score = min(1.0, max(0.0, old_score + adjustment))
    node.activation_score = new_score

    # Update last_accessed timestamp
    node.last_accessed = datetime.now(timezone.utc)

    # Store reaction in metadata
    if 'user_reactions' not in node.metadata:
        node.metadata['user_reactions'] = []

    node.metadata['user_reactions'].append({
        'user_id': user_id,
        'emoji': reaction_type,
        'adjustment': adjustment,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

    logger.info(f"[CAM] Node {node_id} feedback: {old_score:.2f} → {new_score:.2f} ({reaction_type})")

    return {
        'success': True,
        'newActivationScore': new_score,
        'newStatus': classify_activation_level(new_score)
    }
```

#### Endpoint: GET /api/cam/history
**Purpose:** Get recent activation history

**Backend mapping:**
```python
@router.get("/api/cam/history")
async def get_history(user_id: str, limit: int = 20):
    cam_engine = get_cam_engine()

    # Get nodes sorted by last_accessed
    recent_nodes = sorted(
        cam_engine.nodes.values(),
        key=lambda n: n.last_accessed,
        reverse=True
    )[:limit]

    return {
        'history': [
            {
                'id': node.id,
                'name': node.name,
                'path': node.path,
                'activationScore': node.activation_score,
                'status': classify_activation_level(node.activation_score),
                'lastAccessed': node.last_accessed.isoformat()
            }
            for node in recent_nodes
        ]
    }
```

---

### 2. Frontend Components

#### Component: CAMSidebar.tsx
**Location:** `client/src/components/cam/CAMSidebar.tsx`

**Structure:**
```typescript
interface CAMSuggestion {
  id: string;
  title: string;
  path: string;
  activationScore: number;
  status: 'hot' | 'warm' | 'cold';
  relevanceReason: string;
  lastAccessed: string;
}

const CAMSidebar: React.FC = () => {
  const [suggestions, setSuggestions] = useState<CAMSuggestion[]>([]);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    // Fetch suggestions on mount and when context changes
    fetchSuggestions();

    // Setup WebSocket or polling for real-time updates
    const interval = setInterval(fetchSuggestions, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchSuggestions = async () => {
    const response = await fetch('/api/cam/suggestions?user_id=current&limit=10');
    const data = await response.json();
    setSuggestions(data.suggestions);
  };

  const handleReaction = async (nodeId: string, emoji: string) => {
    await fetch('/api/cam/feedback', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        node_id: nodeId,
        user_id: 'current',
        reaction_type: emoji
      })
    });

    // Refresh suggestions
    fetchSuggestions();
  };

  return (
    <div className={`cam-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="cam-header">
        <h3>CAM Suggestions</h3>
        <button onClick={() => setIsCollapsed(!isCollapsed)}>
          {isCollapsed ? '▶' : '◀'}
        </button>
      </div>

      <div className="cam-suggestions-list">
        {suggestions.map(suggestion => (
          <CAMSuggestionCard
            key={suggestion.id}
            suggestion={suggestion}
            onReaction={handleReaction}
          />
        ))}
      </div>
    </div>
  );
};
```

#### Component: CAMSuggestionCard.tsx
**Location:** `client/src/components/cam/CAMSuggestionCard.tsx`

**Structure:**
```typescript
const CAMSuggestionCard: React.FC<{
  suggestion: CAMSuggestion;
  onReaction: (nodeId: string, emoji: string) => void;
}> = ({ suggestion, onReaction }) => {
  const statusColors = {
    hot: '#FF5733',    // Red-orange
    warm: '#FFC300',   // Yellow-amber
    cold: '#4A90E2'    // Cool blue
  };

  const statusIcons = {
    hot: '🔥',
    warm: '☀️',
    cold: '❄️'
  };

  return (
    <div
      className="cam-suggestion-card"
      style={{ borderLeft: `4px solid ${statusColors[suggestion.status]}` }}
    >
      <div className="card-header">
        <span className="status-icon">{statusIcons[suggestion.status]}</span>
        <h4>{suggestion.title}</h4>
        <span className="activation-score">{suggestion.activationScore.toFixed(2)}</span>
      </div>

      <p className="relevance-reason">{suggestion.relevanceReason}</p>

      <div className="reaction-toolbar">
        <button onClick={() => onReaction(suggestion.id, '👍')} title="Helpful">👍</button>
        <button onClick={() => onReaction(suggestion.id, '❤️')} title="Love it">❤️</button>
        <button onClick={() => onReaction(suggestion.id, '💡')} title="Insightful">💡</button>
        <button onClick={() => onReaction(suggestion.id, '❌')} title="Not relevant">❌</button>
      </div>

      <div className="card-meta">
        <small>Last accessed: {formatRelativeTime(suggestion.lastAccessed)}</small>
      </div>
    </div>
  );
};
```

#### CSS: cam_sidebar.css
**Location:** `client/src/components/cam/cam_sidebar.css`

```css
.cam-sidebar {
  position: fixed;
  right: 0;
  top: 60px; /* Below header */
  width: 320px;
  height: calc(100vh - 60px);
  background: rgba(15, 15, 20, 0.95);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  padding: 16px;
  overflow-y: auto;
  transition: transform 0.3s ease;
  z-index: 100;
}

.cam-sidebar.collapsed {
  transform: translateX(300px);
}

.cam-suggestion-card {
  background: rgba(30, 30, 40, 0.8);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.cam-suggestion-card:hover {
  background: rgba(40, 40, 50, 0.9);
  transform: translateX(-4px);
}

/* Hot/Warm/Cold color coding */
.cam-suggestion-card[data-status="hot"] {
  border-left: 4px solid #FF5733;
}

.cam-suggestion-card[data-status="warm"] {
  border-left: 4px solid #FFC300;
}

.cam-suggestion-card[data-status="cold"] {
  border-left: 4px solid #4A90E2;
}

.reaction-toolbar {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.reaction-toolbar button {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 16px;
}

.reaction-toolbar button:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

/* Activation animation when reaction is clicked */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }
  50% { box-shadow: 0 0 20px 4px rgba(255, 255, 255, 0.3); }
}

.cam-suggestion-card.reacting {
  animation: pulse-glow 0.6s ease-out;
}
```

---

### 3. Integration with CAM Tool Memory (JARVIS Hints)

#### Extend CAMSidebar to show tool suggestions
```typescript
const CAMSidebar: React.FC = () => {
  const [toolHint, setToolHint] = useState<string | null>(null);

  useEffect(() => {
    // Get JARVIS hint based on current context
    const fetchToolHint = async () => {
      const context = {
        folder_path: currentFolder,
        file_extension: selectedFile?.extension,
        viewport_zoom: currentZoom
      };

      const response = await fetch('/api/cam/tool-hint', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({context})
      });

      const data = await response.json();
      setToolHint(data.hint);
    };

    fetchToolHint();
  }, [currentFolder, selectedFile, currentZoom]);

  return (
    <div className="cam-sidebar">
      {/* Suggestions section */}

      {toolHint && (
        <div className="jarvis-hint">
          <span className="jarvis-icon">🤖</span>
          <p>{toolHint}</p>
        </div>
      )}
    </div>
  );
};
```

#### Backend endpoint for JARVIS hints
```python
# File: src/api/routes/cam_routes.py
@router.post("/api/cam/tool-hint")
async def get_tool_hint(context: Dict[str, Any]):
    tool_memory = get_cam_tool_memory()
    hint = tool_memory.get_jarvis_hint(context)

    return {'hint': hint}
```

---

## Implementation Phases

### Phase 95.1: Backend API Routes (2-3 hours)
**Files to create:**
- `src/api/routes/cam_routes.py` - CAM API endpoints
- Update `src/api/routes/__init__.py` - Register CAM routes

**Tasks:**
1. ✅ Create 4 core CAM endpoints (suggestions, node details, feedback, history)
2. ✅ Add tool hint endpoint for JARVIS integration
3. ✅ Add helper functions (classify_activation_level, find_similar_nodes)
4. ✅ Register routes in FastAPI app

### Phase 95.2: Frontend Components (3-4 hours)
**Files to create:**
- `client/src/components/cam/CAMSidebar.tsx`
- `client/src/components/cam/CAMSuggestionCard.tsx`
- `client/src/components/cam/cam_sidebar.css`
- `client/src/components/cam/index.ts`

**Tasks:**
1. ✅ Create CAMSidebar with collapse/expand functionality
2. ✅ Create CAMSuggestionCard with emoji reactions
3. ✅ Add hot/warm/cold color theming
4. ✅ Integrate with existing layout (sidebar right side)

### Phase 95.3: Real-time Updates (1-2 hours)
**Tasks:**
1. ⬜ Setup WebSocket connection for CAM updates
2. ⬜ Or implement polling every 5 seconds
3. ⬜ Add optimistic UI updates for reactions
4. ⬜ Handle connection errors gracefully

### Phase 95.4: 3D Inline Badges (2-3 hours)
**Files to modify:**
- `client/src/components/tree/VETKATree.tsx` (or relevant 3D component)

**Tasks:**
1. ⬜ Add activation score badges to 3D nodes
2. ⬜ Implement glowing effect for hot nodes
3. ⬜ Add click handler to open node details
4. ⬜ Performance optimization (only show badges for visible nodes)

### Phase 95.5: Testing & Polish (2-3 hours)
**Tasks:**
1. ⬜ Test CAM suggestions with various queries
2. ⬜ Test emoji reactions update scores correctly
3. ⬜ Test real-time updates across multiple tabs
4. ⬜ Accessibility testing (WCAG 2.1)
5. ⬜ Performance testing with 1000+ nodes

---

## Database Schema Extensions

### User Reactions Table
```sql
CREATE TABLE IF NOT EXISTS cam_user_reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    emoji TEXT NOT NULL,
    weight_adjustment REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES nodes(id)
);

CREATE INDEX idx_user_reactions_node ON cam_user_reactions(node_id);
CREATE INDEX idx_user_reactions_user ON cam_user_reactions(user_id);
```

### CAM Metrics Table
```sql
CREATE TABLE IF NOT EXISTS cam_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    activation_score REAL NOT NULL,
    status TEXT NOT NULL, -- 'hot', 'warm', 'cold'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES nodes(id)
);

CREATE INDEX idx_cam_metrics_node ON cam_metrics(node_id);
CREATE INDEX idx_cam_metrics_timestamp ON cam_metrics(timestamp);
```

---

## Performance Considerations

### 1. Caching Strategy
- Cache CAM suggestions for 5 seconds per user
- Invalidate cache on feedback submission
- Use Redis if available, otherwise in-memory dict

### 2. Query Optimization
- Pre-compute activation scores periodically (every 5 minutes)
- Store scores in database for fast retrieval
- Only recalculate when user submits feedback

### 3. Frontend Optimization
- Virtualize suggestion list if > 50 items
- Debounce real-time updates to avoid UI thrashing
- Use React.memo for suggestion cards

---

## Success Metrics

### Phase 95 Goals
1. **CAM suggestions visible in UI** - Sidebar with 5-10 suggestions
2. **Emoji reactions working** - Users can boost/lower activation scores
3. **Hot/warm/cold visualization** - Color-coded suggestions
4. **Real-time updates** - Suggestions refresh every 5 seconds
5. **Performance** - API responses < 100ms, UI responsive

### User Experience Goals
1. **Discoverability** - Users find relevant nodes 30% faster
2. **Engagement** - 50% of users try emoji reactions in first session
3. **Accuracy** - CAM suggestions are relevant 70%+ of the time

---

## Next Steps

1. **Immediate:** Create `src/api/routes/cam_routes.py` with 4 core endpoints
2. **Next:** Build `CAMSidebar.tsx` and `CAMSuggestionCard.tsx`
3. **Then:** Add CSS styling with hot/warm/cold theming
4. **Finally:** Test end-to-end with real user queries

---

**Status:** Ready for Phase 95.1 implementation
**Blocker:** None - CAM engine is fully operational, just needs API exposure
**Risk:** Low - Backend logic is solid, frontend is straightforward React
