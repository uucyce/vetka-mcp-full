# CAM UI Implementation Roadmap

**Strategic guide for implementing all 8 CAM UI markers**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│           Frontend UI Components (8)                 │
├─────────────────────────────────────────────────────┤
│  UnifiedSearchBar  │  FileCard  │  MessageBubble    │
│  ChatSidebar       │ MessageInput │  ModelDirectory │
│  MentionPopup                                        │
├─────────────────────────────────────────────────────┤
│           useCAS Hook (Centralized API)             │
├─────────────────────────────────────────────────────┤
│              CAM API Routes (cam_routes.py)         │
├─────────────────────────────────────────────────────┤
│  CAM Engine │ CAM Integration │ CAM Metrics         │
└─────────────────────────────────────────────────────┘
```

---

## Phase-by-Phase Implementation

### PHASE 0: Backend Foundation (3 days)

#### Task 0.1: Create CAM Routes File
**File:** `src/api/routes/cam_routes.py`
**Time:** 1 day

```python
# Routes to implement:
from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/cam", tags=["cam"])

class CAMSuggestionResponse(BaseModel):
    suggestions: List[Dict[str, Any]]
    total_count: int
    cache_hit: bool

@router.get("/suggestions")
async def get_cam_suggestions(
    context: str = Query("vetka"),
    limit: int = Query(5),
    offset: int = Query(0)
) -> CAMSuggestionResponse:
    """GET /api/cam/suggestions - Fetch context-aware file suggestions"""
    # Implementation here
    pass

@router.post("/pin")
async def pin_to_cam(
    file_path: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """POST /api/cam/pin - Pin file to CAM"""
    pass

@router.get("/activation")
async def get_activation(
    node_id: str = Query(None),
    chat_id: str = Query(None)
) -> Dict[str, Any]:
    """GET /api/cam/activation - Check CAM activation state"""
    pass

@router.post("/reaction")
async def add_reaction(
    message_id: str,
    emoji: str,
    weight: float
) -> Dict[str, Any]:
    """POST /api/cam/reaction - Link emoji to CAM weight"""
    pass

@router.get("/model-rank")
async def get_model_rank(
    model_id: str = Query(None)
) -> Dict[str, Any]:
    """GET /api/cam/model-rank - Get CAM relevance for model"""
    pass
```

**Acceptance Criteria:**
- [ ] All 5 routes created with stub implementations
- [ ] FastAPI app can start without errors
- [ ] Routes appear in `/api/docs` (Swagger)
- [ ] Return valid JSON responses

---

#### Task 0.2: Hook Up CAM Engine
**Time:** 1 day

```python
# In cam_routes.py, implement actual logic:

async def get_cam_suggestions(context: str, limit: int):
    """Use CAMIntegration service"""
    try:
        cam_service = request.app.state.cam_integration
        suggestions = await cam_service.get_suggestions(
            context=context,
            limit=limit
        )
        return {
            "suggestions": suggestions,
            "total_count": len(suggestions),
            "cache_hit": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Acceptance Criteria:**
- [ ] CAM engine called correctly
- [ ] Results returned with proper structure
- [ ] Error handling in place
- [ ] Tested with actual CAM data

---

#### Task 0.3: Caching & Optimization
**Time:** 1 day

```python
# Add caching layer
from functools import lru_cache
import asyncio

class CAMCache:
    def __init__(self, ttl=300):  # 5 minute TTL
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl

    async def get_cached(self, key: str, fetch_fn):
        """Get from cache or fetch fresh"""
        now = time.time()
        if key in self.cache:
            value, timestamp = self.cache[key]
            if now - timestamp < self.ttl:
                return value

        value = await fetch_fn()
        self.cache[key] = (value, now)
        return value

# Usage in routes
_cam_cache = CAMCache(ttl=300)

@router.get("/suggestions")
async def get_cam_suggestions(context: str, limit: int):
    key = f"suggestions:{context}:{limit}"
    return await _cam_cache.get_cached(
        key,
        lambda: cam_service.get_suggestions(context, limit)
    )
```

**Acceptance Criteria:**
- [ ] Caching logic implemented
- [ ] TTL working correctly
- [ ] Performance improved (measure with timing)
- [ ] Cache invalidation on updates

---

### PHASE 1: High Priority (6 days)

#### Task 1.1: CAM Suggestions Panel Component
**Component:** CAMSuggestionsPanel
**File:** `client/src/components/search/CAMSuggestionsPanel.tsx`
**Time:** 2 days

```typescript
import React, { useEffect, useState } from 'react';
import { useSearch } from '../../hooks/useSearch';

interface CAMSuggestion {
  id: string;
  name: string;
  path: string;
  level: 'hot' | 'warm' | 'cold';
  cam_score: number;
  preview?: string;
}

interface Props {
  context: string;
  onSelectSuggestion?: (suggestion: CAMSuggestion) => void;
  onPinSuggestion?: (suggestion: CAMSuggestion) => void;
  limit?: number;
}

export function CAMSuggestionsPanel({
  context,
  onSelectSuggestion,
  onPinSuggestion,
  limit = 5
}: Props) {
  const [suggestions, setSuggestions] = useState<CAMSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSuggestions();
  }, [context]);

  const fetchSuggestions = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/cam/suggestions?context=${context}&limit=${limit}`
      );
      if (!response.ok) throw new Error('Failed to fetch suggestions');
      const data = await response.json();
      setSuggestions(data.suggestions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getColorForLevel = (level: string): string => {
    switch (level) {
      case 'hot': return '#ff6b6b';
      case 'warm': return '#ffd93d';
      case 'cold': return '#95a3a3';
      default: return '#555555';
    }
  };

  if (loading) return <div style={{ padding: '8px' }}>Loading suggestions...</div>;
  if (error) return null; // Fail silently
  if (suggestions.length === 0) return null;

  return (
    <div style={{
      marginBottom: '8px',
      background: '#1a1a1a',
      border: '1px solid #333',
      borderRadius: '6px',
      padding: '8px 0',
    }}>
      <div style={{
        padding: '6px 12px',
        fontSize: '10px',
        color: '#888',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}>
        From Context Memory
      </div>

      {suggestions.map((suggestion) => (
        <div
          key={suggestion.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            cursor: 'pointer',
            transition: 'background 0.15s',
            borderBottom: '1px solid #222',
          }}
          onClick={() => onSelectSuggestion?.(suggestion)}
          onMouseEnter={(e) => (e.currentTarget.style.background = '#1f1f1f')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        >
          {/* Level badge */}
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: getColorForLevel(suggestion.level),
            flexShrink: 0,
          }} />

          {/* File info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: '12px',
              color: '#fff',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {suggestion.name}
            </div>
            <div style={{
              fontSize: '10px',
              color: '#666',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {suggestion.path}
            </div>
          </div>

          {/* CAM score */}
          <div style={{
            fontSize: '9px',
            color: '#888',
            flexShrink: 0,
            marginRight: '4px',
          }}>
            {(suggestion.cam_score * 100).toFixed(0)}%
          </div>

          {/* Pin button */}
          {onPinSuggestion && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onPinSuggestion(suggestion);
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#555',
                cursor: 'pointer',
                fontSize: '12px',
                padding: '2px 4px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#555')}
            >
              📌
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Component renders without errors
- [ ] Fetches suggestions from API
- [ ] Displays hot/warm/cold badges
- [ ] Click handler works
- [ ] Pin button functional
- [ ] Styling matches Nolan theme

---

#### Task 1.2: useCAS Hook
**File:** `client/src/hooks/useCAS.ts`
**Time:** 1 day

```typescript
import { useState, useCallback } from 'react';

interface CAMSuggestion {
  id: string;
  name: string;
  path: string;
  level: 'hot' | 'warm' | 'cold';
  cam_score: number;
}

interface CAMActivation {
  node_id: string;
  level: 'hot' | 'warm' | 'cold';
  weight: number;
}

interface UseCASReturn {
  // Suggestions
  getSuggestions: (context: string, limit?: number) => Promise<CAMSuggestion[]>;

  // Pinning
  pinFile: (path: string, metadata?: any) => Promise<{ success: boolean }>;
  unpinFile: (path: string) => Promise<{ success: boolean }>;

  // Activation
  getActivation: (nodeId: string) => Promise<CAMActivation>;

  // Reactions
  addReaction: (messageId: string, emoji: string) => Promise<{ success: boolean }>;

  // Model ranking
  getModelRank: (modelId: string) => Promise<{ score: number; rank: number }>;

  // Loading & Error states
  loading: boolean;
  error: Error | null;
}

export function useCAS(): UseCASReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const apiCall = useCallback(async (endpoint: string, options?: RequestInit) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/cam${endpoint}`, options);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    getSuggestions: (context, limit = 5) =>
      apiCall(`/suggestions?context=${context}&limit=${limit}`),

    pinFile: (path, metadata = {}) =>
      apiCall(`/pin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: path, metadata }),
      }),

    unpinFile: (path) =>
      apiCall(`/pin/${encodeURIComponent(path)}`, { method: 'DELETE' }),

    getActivation: (nodeId) =>
      apiCall(`/activation?node_id=${nodeId}`),

    addReaction: (messageId, emoji) =>
      apiCall(`/reaction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, emoji, weight: 0.1 }),
      }),

    getModelRank: (modelId) =>
      apiCall(`/model-rank?model_id=${modelId}`),

    loading,
    error,
  };
}
```

**Acceptance Criteria:**
- [ ] Hook exports all needed functions
- [ ] API calls correct
- [ ] Error handling works
- [ ] Loading states managed
- [ ] Can be used in components

---

#### Task 1.3: Integrate Marker 1 (Search Suggestions)
**Component:** UnifiedSearchBar
**Time:** 2 days

```typescript
// In UnifiedSearchBar.tsx, add CAMSuggestionsPanel before results

import { CAMSuggestionsPanel } from './CAMSuggestionsPanel';
import { useCAS } from '../../hooks/useCAS';

// Add to component
const camService = useCAS();

// Render in JSX
<>
  {query && !isSearching && (
    <CAMSuggestionsPanel
      context={searchContext}
      onSelectSuggestion={(sugg) => {
        setQuery('');
        onSelectResult?.(sugg);
      }}
      onPinSuggestion={async (sugg) => {
        await camService.pinFile(sugg.path, { source: 'cam_suggestions' });
        // Show toast
      }}
      limit={5}
    />
  )}
</>
```

**Acceptance Criteria:**
- [ ] CAMSuggestionsPanel appears above search results
- [ ] Suggestions load correctly
- [ ] Click to select works
- [ ] Pin functionality works
- [ ] No layout shifts

---

#### Task 1.4: Integrate Marker 2 (File Card Pin)
**Component:** FileCard
**Time:** 2 days

In FileCard, add pin-to-CAM button in the hover preview:

```typescript
// Add to FileCard hover preview section
const [camPinned, setCAMPinned] = useState(false);

const handleCAMPin = async (e: React.MouseEvent) => {
  e.stopPropagation();
  try {
    await camService.pinFile(path, {
      type: 'file',
      depth: depth,
      category: cardCategory,
    });
    setCAMPinned(true);
    // Show toast: "Added to context memory"
  } catch (err) {
    console.error('Failed to pin to CAM:', err);
  }
};

// In preview section:
<button
  onClick={handleCAMPin}
  style={{
    background: camPinned ? '#333' : 'transparent',
    border: '1px solid #333',
    color: camPinned ? '#4aff9e' : '#555',
    padding: '4px 8px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '11px',
  }}
>
  📌 {camPinned ? 'In Memory' : 'Add to Memory'}
</button>
```

**Acceptance Criteria:**
- [ ] Pin button appears on hover
- [ ] Button sends API call
- [ ] Visual feedback on success
- [ ] Error handling works

---

### PHASE 2: Medium Priority (5 days)

#### Task 2.1: Activate Folder Badges (MARKER 3)
**Component:** FileCard (folder labels)
**Time:** 2 days

```typescript
// In FileCard useEffect, add CAM activation check
useEffect(() => {
  if (type === 'folder' && id) {
    camService.getActivation(id)
      .then(activation => {
        setCAMActivation(activation);
      })
      .catch(err => console.warn('CAM activation error:', err));
  }
}, [id, type]);

// In folder label rendering:
<div style={{
  position: 'absolute',
  top: '-12px',
  right: '-12px',
  width: '10px',
  height: '10px',
  borderRadius: '50%',
  background: {
    'hot': '#ff6b6b',
    'warm': '#ffd93d',
    'cold': '#95a3a3',
  }[camActivation?.level] || '#555555',
  opacity: camActivation ? 1 : 0.3,
}}>
  <title>{camActivation?.level || 'unknown'} ({(camActivation?.weight * 100).toFixed(0)}%)</title>
</div>
```

**Acceptance Criteria:**
- [ ] Badges appear on folders
- [ ] Colors correct for levels
- [ ] Tooltips show level and weight
- [ ] Updates when CAM changes

---

#### Task 2.2: Chat Sidebar CAM Status (MARKER 5)
**Component:** ChatSidebar
**Time:** 1.5 days

```typescript
// In loadChats, fetch CAM status for each
const loadChats = async () => {
  const chats = await fetchChats();

  // Fetch CAM status for each chat
  const chatsWithCAM = await Promise.all(
    chats.map(async (chat) => {
      try {
        const activation = await camService.getActivation(undefined, chat.id);
        return { ...chat, cam_activation: activation.level };
      } catch {
        return chat;
      }
    })
  );

  setChats(chatsWithCAM);
};

// In render, display badge:
{chat.cam_activation && (
  <span style={{
    display: 'inline-block',
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: {
      'hot': '#ff6b6b',
      'warm': '#ffd93d',
      'cold': '#95a3a3',
    }[chat.cam_activation],
    marginRight: '6px',
  }} />
)}
```

**Acceptance Criteria:**
- [ ] Badges appear in sidebar
- [ ] Colors correct
- [ ] Updates on load
- [ ] Doesn't slow down sidebar

---

#### Task 2.3: Model Ranking (MARKER 7)
**Component:** ModelDirectory
**Time:** 2 days

```typescript
// In ModelDirectory, fetch CAM scores on load
useEffect(() => {
  const enrichModelsWithCAM = async () => {
    const modelsWithScores = await Promise.all(
      models.map(async (model) => {
        try {
          const ranking = await camService.getModelRank(model.id);
          return { ...model, cam_score: ranking.score };
        } catch {
          return model;
        }
      })
    );

    // Sort by CAM score
    modelsWithScores.sort((a, b) => (b.cam_score || 0) - (a.cam_score || 0));
    setModels(modelsWithScores);
  };

  enrichModelsWithCAM();
}, []);

// In model card, display score:
{model.cam_score && (
  <div style={{
    fontSize: '10px',
    color: '#ffd93d',
    marginTop: '4px',
  }}>
    Context match: {(model.cam_score * 100).toFixed(0)}%
  </div>
)}
```

**Acceptance Criteria:**
- [ ] Models sorted by CAM score
- [ ] Score displayed on card
- [ ] Updates on model load
- [ ] Label clear ("Context match")

---

### PHASE 3: Low Priority (4 days)

#### Task 3.1: Emoji to CAM Weight (MARKER 4)
**Component:** MessageBubble
**Time:** 1.5 days

```typescript
// In MessageBubble, enhance reaction handler
const EMOJI_WEIGHTS = {
  '👍': 0.2,
  '👎': -0.2,
  '❤️': 0.3,
  '🔥': 0.25,
  '💡': 0.15,
  '🤔': 0.1,
};

const handleReaction = async (emoji: string) => {
  // Existing code...

  // Send to CAM
  try {
    await camService.addReaction(
      message.id,
      emoji,
      EMOJI_WEIGHTS[emoji] || 0.1
    );
  } catch (err) {
    console.warn('CAM reaction error:', err);
  }
};
```

**Acceptance Criteria:**
- [ ] Weight mapping correct
- [ ] API call successful
- [ ] No UI blocking
- [ ] Error doesn't prevent reaction display

---

#### Task 3.2: Input Context Hints (MARKER 6)
**Component:** MessageInput
**Time:** 1 day

```typescript
// In MessageInput, use CAM suggestions for hints
const [camHints, setCAMHints] = useState<string[]>([]);

useEffect(() => {
  if (cam_suggestions && cam_suggestions.length > 0) {
    setCAMHints(cam_suggestions.slice(0, 2));
  }
}, [cam_suggestions]);

// Update placeholder
<input
  placeholder={
    camHints.length > 0
      ? `Type... (Hot: ${camHints[0].split('/').pop()})`
      : 'Type your message...'
  }
/>
```

**Acceptance Criteria:**
- [ ] Placeholder updates
- [ ] Shows hot file name
- [ ] Doesn't break existing input
- [ ] Graceful fallback

---

#### Task 3.3: Mention Popup CAM (MARKER 8)
**Component:** MentionPopup
**Time:** 1 day

```typescript
// In MentionPopup, sort by CAM ranking
const sortedModels = useMemo(() => {
  const models = [...(groupParticipants || [])];

  // Sort by CAM score if available
  if (cam_ranked_models?.length > 0) {
    return [
      ...models.filter(m => cam_ranked_models.find(r => r.id === m.agent_id)),
      ...models.filter(m => !cam_ranked_models.find(r => r.id === m.agent_id)),
    ];
  }
  return models;
}, [groupParticipants, cam_ranked_models]);

// Display with indicators:
{cam_ranked_models?.find(m => m.id === model.agent_id) && (
  <span style={{
    fontSize: '9px',
    color: '#ffd93d',
    marginLeft: '4px',
  }}>
    ⭐
  </span>
)}
```

**Acceptance Criteria:**
- [ ] Top models appear first
- [ ] Star indicator shows
- [ ] Maintains user typing
- [ ] No performance impact

---

## Integration Testing Plan

### Test Suite Structure

```
tests/
├── unit/
│   ├── useCAS.test.ts
│   ├── CAMSuggestionsPanel.test.tsx
│   └── emoji_weights.test.ts
├── integration/
│   ├── marker_1_search.test.ts
│   ├── marker_2_filecard.test.ts
│   ├── marker_3_folders.test.ts
│   ├── marker_4_emoji.test.ts
│   ├── marker_5_sidebar.test.ts
│   ├── marker_7_models.test.ts
│   └── marker_8_mention.test.ts
└── e2e/
    ├── cam_workflow.test.ts
    └── performance.test.ts
```

### Critical Workflows to Test

1. **Pin to CAM Workflow**
   - [ ] User clicks file card pin button
   - [ ] API called with correct payload
   - [ ] Toast shows success
   - [ ] Suggestion appears in search
   - [ ] Activation updates in folder label

2. **Emoji Reaction Workflow**
   - [ ] User adds emoji reaction
   - [ ] Weight calculated correctly
   - [ ] CAM API called
   - [ ] No UI blocking
   - [ ] CAM state updates

3. **Model Selection Workflow**
   - [ ] Open ModelDirectory
   - [ ] Models sorted by CAM score
   - [ ] Click model in mention popup
   - [ ] Message input updated
   - [ ] Chat sends with selected model

---

## Performance Benchmarks

### Target Performance

| Operation | Target | Acceptable | Bad |
|-----------|--------|-----------|-----|
| Load suggestions | <100ms | <200ms | >500ms |
| Pin file | <50ms | <100ms | >300ms |
| Get activation | <50ms | <100ms | >300ms |
| Sort models | <100ms | <200ms | >500ms |
| Render 100 suggestions | <200ms | <400ms | >1000ms |

### Optimization Strategies

1. **Caching:**
   - Suggestions cache: 5 minutes TTL
   - Activation cache: 1 minute TTL
   - Model scores cache: 10 minutes TTL

2. **Batching:**
   - Get multiple activations in one request
   - Load model scores on directory open (batch)

3. **Lazy Loading:**
   - Don't fetch suggestions until search active
   - Load CAM sidebar status on demand

4. **UI Optimization:**
   - Virtual scroll for large lists
   - Memoize components
   - Debounce API calls

---

## Rollout Strategy

### Phase 1: Beta (Week 1)
- Deploy to staging environment
- Test with internal team
- Gather feedback
- Fix critical bugs

### Phase 2: Limited Release (Week 2)
- Deploy to 10% of users
- Monitor errors and performance
- Gather user feedback
- Fix issues

### Phase 3: Full Release (Week 3)
- Deploy to all users
- Monitor closely
- Be ready to rollback
- Document in release notes

---

## Rollback Plan

**If critical issues discovered:**
1. Revert CAM route deployments
2. Remove CAM UI components (graceful fallback)
3. Keep markers in code for future work
4. Post-mortem analysis

**Graceful degradation:**
- If CAM API down: Hide suggestions, continue with search
- If CAM activation fails: Don't show badges, continue
- If emoji reaction fails: Show local state, don't crash

---

## Success Metrics

### Engagement Metrics
- [ ] 20% of users pin files to CAM
- [ ] 30% of users use emoji reactions
- [ ] 15% of users interact with CAM suggestions
- [ ] Average session time increases by 5%

### Performance Metrics
- [ ] 99% of API calls <200ms
- [ ] 0 UI blocks >16ms
- [ ] Cache hit rate >80% for suggestions
- [ ] Memory usage < 50MB for CAM data

### Quality Metrics
- [ ] 0 critical bugs in week 1
- [ ] 95% test coverage for CAM components
- [ ] 99.9% API uptime
- [ ] 0 data loss incidents

---

## Team Assignments (Suggested)

| Phase | Task | Lead | Support |
|-------|------|------|---------|
| 0 | Backend routes | Backend | QA |
| 1.1 | CAMSuggestionsPanel | Frontend | Backend |
| 1.2 | useCAS hook | Frontend | Backend |
| 1.3 | Search integration | Frontend | QA |
| 1.4 | FileCard pin | Frontend | QA |
| 2.1 | Folder badges | Frontend | QA |
| 2.2 | Sidebar status | Frontend | QA |
| 2.3 | Model ranking | Frontend | QA |
| 3.1-3.3 | Polish | Frontend | QA |

---

## Documentation Needed

- [ ] Component API docs (Storybook)
- [ ] useCAS hook usage guide
- [ ] CAM route specifications
- [ ] User guide for CAM features
- [ ] Admin guide for CAM configuration
- [ ] Developer guide for extending CAM
- [ ] Migration guide (from old pinning to CAM)

---

## Open Questions

1. Should CAM suggestions replace or supplement search results?
2. Do we need real-time CAM updates (WebSocket)?
3. Should CAM state persist across browser sessions?
4. Can users delete/modify CAM state through UI?
5. Should there be admin controls for CAM configuration?

---

**Roadmap Created:** 2026-01-26
**Estimated Total Duration:** 2-3 weeks
**Status:** Ready for team review
