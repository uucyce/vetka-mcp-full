# QUICK START: CAM UI Implementation
**Phase 95 - Step-by-Step Guide**

---

## 1. Create Backend API Routes (30 minutes)

### File: `src/api/routes/cam_routes.py`
```python
"""
CAM API Routes - Phase 95.1
Exposes Context-Aware Memory suggestions to frontend
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

from src.orchestration.cam_engine import get_cam_engine, get_cam_tool_memory

router = APIRouter()
logger = logging.getLogger("VETKA_CAM_API")


def classify_activation_level(score: float) -> str:
    """Classify activation score into hot/warm/cold."""
    if score >= 0.7:
        return 'hot'
    elif score >= 0.4:
        return 'warm'
    else:
        return 'cold'


@router.get("/api/cam/suggestions")
async def get_cam_suggestions(
    user_id: str = "current",
    context_id: Optional[str] = None,
    limit: int = 10
):
    """Get CAM memory suggestions sorted by activation score."""
    try:
        cam_engine = get_cam_engine()
        if not cam_engine:
            return {'suggestions': []}

        # Get nodes sorted by activation score
        nodes = sorted(
            cam_engine.nodes.values(),
            key=lambda n: n.activation_score,
            reverse=True
        )[:limit]

        suggestions = []
        for node in nodes:
            status = classify_activation_level(node.activation_score)
            suggestions.append({
                'id': node.id,
                'title': node.name,
                'path': node.path,
                'activationScore': round(node.activation_score, 3),
                'status': status,
                'relevanceReason': f"Activation score: {node.activation_score:.2f}",
                'lastAccessed': node.last_accessed.isoformat() if node.last_accessed else None
            })

        return {'suggestions': suggestions}

    except Exception as e:
        logger.error(f"[CAM API] get_suggestions failed: {e}")
        return {'suggestions': []}


@router.post("/api/cam/feedback")
async def record_feedback(request: Dict[str, Any]):
    """Record user emoji reaction and update activation score."""
    try:
        node_id = request.get('node_id')
        user_id = request.get('user_id', 'current')
        reaction_type = request.get('reaction_type')

        cam_engine = get_cam_engine()
        if not cam_engine or node_id not in cam_engine.nodes:
            raise HTTPException(status_code=404, detail="Node not found")

        node = cam_engine.nodes[node_id]

        # Emoji weight mapping
        emoji_weights = {
            '👍': 0.2,
            '❤️': 0.3,
            '💡': 0.25,
            '❌': -0.1
        }

        adjustment = emoji_weights.get(reaction_type, 0.1)

        # Update score (capped at 1.0)
        old_score = node.activation_score
        new_score = min(1.0, max(0.0, old_score + adjustment))
        node.activation_score = new_score
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

    except Exception as e:
        logger.error(f"[CAM API] record_feedback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cam/tool-hint")
async def get_tool_hint(request: Dict[str, Any]):
    """Get JARVIS-style tool suggestion based on context."""
    try:
        context = request.get('context', {})
        tool_memory = get_cam_tool_memory()
        hint = tool_memory.get_jarvis_hint(context)

        return {'hint': hint}

    except Exception as e:
        logger.error(f"[CAM API] get_tool_hint failed: {e}")
        return {'hint': None}
```

### Update: `src/api/routes/__init__.py`
```python
from src.api.routes import cam_routes

# In your FastAPI app setup:
app.include_router(cam_routes.router)
```

---

## 2. Create Frontend Component (45 minutes)

### File: `client/src/components/cam/CAMSidebar.tsx`
```typescript
import React, { useState, useEffect } from 'react';
import './cam_sidebar.css';

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
  const [reactingNodeId, setReactingNodeId] = useState<string | null>(null);

  const fetchSuggestions = async () => {
    try {
      const response = await fetch('/api/cam/suggestions?user_id=current&limit=10');
      const data = await response.json();
      setSuggestions(data.suggestions || []);
    } catch (error) {
      console.error('[CAM] Failed to fetch suggestions:', error);
    }
  };

  useEffect(() => {
    fetchSuggestions();

    // Poll every 5 seconds for updates
    const interval = setInterval(fetchSuggestions, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleReaction = async (nodeId: string, emoji: string) => {
    try {
      setReactingNodeId(nodeId);

      await fetch('/api/cam/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: nodeId,
          user_id: 'current',
          reaction_type: emoji
        })
      });

      // Refresh suggestions
      await fetchSuggestions();

      // Clear reacting animation
      setTimeout(() => setReactingNodeId(null), 600);
    } catch (error) {
      console.error('[CAM] Failed to record reaction:', error);
    }
  };

  const statusColors: Record<string, string> = {
    hot: '#FF5733',
    warm: '#FFC300',
    cold: '#4A90E2'
  };

  const statusIcons: Record<string, string> = {
    hot: '🔥',
    warm: '☀️',
    cold: '❄️'
  };

  return (
    <div className={`cam-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="cam-header">
        <h3>CAM Suggestions</h3>
        <button
          className="collapse-btn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? 'Expand' : 'Collapse'}
        >
          {isCollapsed ? '◀' : '▶'}
        </button>
      </div>

      {!isCollapsed && (
        <div className="cam-suggestions-list">
          {suggestions.length === 0 ? (
            <p className="no-suggestions">No suggestions yet. Start exploring!</p>
          ) : (
            suggestions.map(suggestion => (
              <div
                key={suggestion.id}
                className={`cam-suggestion-card ${reactingNodeId === suggestion.id ? 'reacting' : ''}`}
                style={{ borderLeft: `4px solid ${statusColors[suggestion.status]}` }}
              >
                <div className="card-header">
                  <span className="status-icon">{statusIcons[suggestion.status]}</span>
                  <h4 title={suggestion.path}>{suggestion.title}</h4>
                  <span className="activation-score">{suggestion.activationScore.toFixed(2)}</span>
                </div>

                <p className="relevance-reason">{suggestion.relevanceReason}</p>

                <div className="reaction-toolbar">
                  <button onClick={() => handleReaction(suggestion.id, '👍')} title="Helpful">
                    👍
                  </button>
                  <button onClick={() => handleReaction(suggestion.id, '❤️')} title="Love it">
                    ❤️
                  </button>
                  <button onClick={() => handleReaction(suggestion.id, '💡')} title="Insightful">
                    💡
                  </button>
                  <button onClick={() => handleReaction(suggestion.id, '❌')} title="Not relevant">
                    ❌
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default CAMSidebar;
```

### File: `client/src/components/cam/cam_sidebar.css`
```css
.cam-sidebar {
  position: fixed;
  right: 0;
  top: 60px;
  width: 320px;
  height: calc(100vh - 60px);
  background: rgba(15, 15, 20, 0.95);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  padding: 16px;
  overflow-y: auto;
  transition: transform 0.3s ease;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.cam-sidebar.collapsed {
  transform: translateX(280px);
}

.cam-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.cam-header h3 {
  margin: 0;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
}

.collapse-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  padding: 6px 10px;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.collapse-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.cam-suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cam-suggestion-card {
  background: rgba(30, 30, 40, 0.8);
  border-radius: 8px;
  padding: 12px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.cam-suggestion-card:hover {
  background: rgba(40, 40, 50, 0.9);
  transform: translateX(-4px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.status-icon {
  font-size: 20px;
}

.card-header h4 {
  margin: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activation-score {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.relevance-reason {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin: 8px 0;
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

.no-suggestions {
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
  padding: 32px 16px;
  font-size: 14px;
}

/* Pulse animation on reaction */
@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0);
  }
  50% {
    box-shadow: 0 0 20px 4px rgba(255, 255, 255, 0.3);
  }
}

.cam-suggestion-card.reacting {
  animation: pulse-glow 0.6s ease-out;
}

/* Scrollbar styling */
.cam-sidebar::-webkit-scrollbar {
  width: 6px;
}

.cam-sidebar::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}

.cam-sidebar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.cam-sidebar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
```

### File: `client/src/components/cam/index.ts`
```typescript
export { default as CAMSidebar } from './CAMSidebar';
```

---

## 3. Integrate into App (10 minutes)

### Update: `client/src/App.tsx` (or main layout component)
```typescript
import { CAMSidebar } from './components/cam';

function App() {
  return (
    <div className="app">
      {/* Existing components */}
      <Header />
      <MainContent />

      {/* Add CAM sidebar */}
      <CAMSidebar />
    </div>
  );
}
```

---

## 4. Test (15 minutes)

### Backend Test
```bash
# Start server
python main.py

# Test API endpoint
curl http://localhost:5002/api/cam/suggestions?user_id=current&limit=5
```

### Frontend Test
```bash
# Start frontend
cd client && npm run dev

# Open browser and check:
# 1. CAM sidebar appears on right side
# 2. Suggestions load (if CAM engine has nodes)
# 3. Emoji reactions work (pulse animation)
# 4. Collapse/expand button works
```

---

## 5. Populate CAM with Test Data (Optional)

### Script: `test_cam_suggestions.py`
```python
"""
Populate CAM engine with test nodes for UI testing
"""
import asyncio
from src.orchestration.cam_engine import get_cam_engine
import numpy as np

async def populate_test_nodes():
    cam = get_cam_engine()

    test_nodes = [
        {
            'path': 'src/orchestration/cam_engine.py',
            'name': 'CAM Engine',
            'activation_score': 0.85,
            'metadata': {'type': 'core'}
        },
        {
            'path': 'src/api/routes/chat_routes.py',
            'name': 'Chat Routes',
            'activation_score': 0.65,
            'metadata': {'type': 'api'}
        },
        {
            'path': 'client/src/components/chat/ChatPanel.tsx',
            'name': 'Chat Panel',
            'activation_score': 0.45,
            'metadata': {'type': 'ui'}
        },
        {
            'path': 'docs/95_ph/GROK_CAM_UI_RECOMMENDATIONS.md',
            'name': 'Grok Recommendations',
            'activation_score': 0.92,
            'metadata': {'type': 'docs'}
        },
        {
            'path': 'src/memory/engram_user_memory.py',
            'name': 'Engram Memory',
            'activation_score': 0.38,
            'metadata': {'type': 'memory'}
        }
    ]

    for node_data in test_nodes:
        await cam.handle_new_artifact(
            artifact_path=node_data['path'],
            metadata=node_data
        )

    print(f"✅ Added {len(test_nodes)} test nodes to CAM")
    print(f"Total nodes in CAM: {len(cam.nodes)}")

if __name__ == '__main__':
    asyncio.run(populate_test_nodes())
```

---

## Troubleshooting

### Issue: No suggestions appear
**Solution:** Populate CAM with test data using script above

### Issue: Emoji reactions don't work
**Solution:** Check browser console for errors, verify `/api/cam/feedback` endpoint is accessible

### Issue: Sidebar overlaps other content
**Solution:** Adjust `right` position in CSS or add `margin-right: 320px` to main content

### Issue: Performance issues with many nodes
**Solution:** Add virtualization to suggestion list (react-window library)

---

## Success Checklist

- [ ] Backend: CAM routes registered and responding
- [ ] Frontend: CAMSidebar component renders
- [ ] Frontend: Suggestions load and display
- [ ] Frontend: Hot/warm/cold colors show correctly
- [ ] Frontend: Emoji reactions trigger pulse animation
- [ ] Frontend: Collapse/expand button works
- [ ] Integration: Sidebar doesn't overlap main content
- [ ] Integration: Real-time updates work (5s polling)

---

**Total Implementation Time:** ~1.5-2 hours
**Difficulty:** Low-Medium (straightforward React + FastAPI)
**Next Phase:** Add 3D inline badges for hot nodes
