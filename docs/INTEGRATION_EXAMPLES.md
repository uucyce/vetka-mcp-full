# 🔧 VETKA Phase 8.0 - Integration Examples

## Quick Integration Guide

Примеры интеграции всех компонентов Phase 8.0 в существующий код VETKA.

---

## 1️⃣ main.py - REST API Endpoints

### Добавить imports

```python
# main.py - в начало файла

from src.agents.learner_initializer import (
    LearnerInitializer,
    TaskComplexity,
    OpenRouterAPIKeyRotator
)
from src.elisya.api_aggregator_v3 import APIAggregator, ProviderType
from src.agents.arc_solver_agent import create_arc_solver
```

### Initialize Components

```python
# main.py - после инициализации memory_manager и eval_agent

# 1. Load OpenRouter keys
OpenRouterAPIKeyRotator.load_keys()
logger.info("✅ OpenRouter keys loaded")

# 2. Initialize API Aggregator
api_aggregator = APIAggregator(memory_manager=memory_manager)

# Add keys from environment
if os.getenv('GROK_API_KEY'):
    api_aggregator.add_key(
        ProviderType.GROK,
        os.getenv('GROK_API_KEY'),
        metadata={'purpose': 'multimodal_analysis'}
    )

if os.getenv('ANTHROPIC_API_KEY'):
    api_aggregator.add_key(
        ProviderType.CLAUDE,
        os.getenv('ANTHROPIC_API_KEY'),
        metadata={'purpose': 'code_generation'}
    )

# OpenRouter keys are auto-loaded
logger.info("✅ API Aggregator initialized")

# 3. Initialize ARC Solver
arc_solver = create_arc_solver(
    memory_manager=memory_manager,
    eval_agent=eval_agent,
    prefer_api=True  # Use API (Grok/Claude) for better quality
)
logger.info("✅ ARC Solver initialized")
```

### Add Endpoints

```python
# main.py - добавить endpoints

# ============================================================================
# PHASE 8.0 ENDPOINTS
# ============================================================================

@app.post("/api/learner/create")
async def create_learner_endpoint(request: Request):
    """
    Create learner with intelligent routing

    Body:
    {
        "task_description": "Analyze complex workflow graph",
        "complexity": "complex",  # optional: simple, medium, complex, expert
        "prefer_api": false
    }
    """
    try:
        data = await request.json()
        task_desc = data.get('task_description', '')
        complexity_str = data.get('complexity')
        prefer_api = data.get('prefer_api', False)

        # Auto-detect complexity if not provided
        if complexity_str:
            complexity = TaskComplexity(complexity_str)
        else:
            complexity = LearnerInitializer.get_routing_recommendation(task_desc)

        # Create learner
        learner = LearnerInitializer.create_with_intelligent_routing(
            complexity=complexity,
            memory_manager=memory_manager,
            eval_agent=eval_agent,
            prefer_api=prefer_api
        )

        if learner:
            return {
                'success': True,
                'complexity': complexity.value,
                'learner_type': 'api' if prefer_api else 'local'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to create learner'
            }

    except Exception as e:
        logger.error(f"❌ Learner creation failed: {e}")
        return {'success': False, 'error': str(e)}


@app.post("/api/aggregator/generate")
async def aggregator_generate(request: Request):
    """
    Universal AI generation via API Aggregator

    Body:
    {
        "prompt": "Explain this code",
        "task_type": "code",  # general, code, creative, analysis
        "multimodal": false,
        "cheap": true,
        "max_tokens": 2000
    }
    """
    try:
        data = await request.json()
        prompt = data.get('prompt', '')
        task_type = data.get('task_type', 'general')
        multimodal = data.get('multimodal', False)
        cheap = data.get('cheap', True)
        max_tokens = data.get('max_tokens', 2000)

        result = api_aggregator.generate_with_fallback(
            prompt=prompt,
            task_type=task_type,
            multimodal=multimodal,
            cheap=cheap,
            max_tokens=max_tokens
        )

        if result:
            return {
                'success': True,
                'response': result['response'],
                'model': result['model'],
                'provider': result['provider'],
                'tokens': result.get('tokens', 0),
                'cost': result.get('cost', 0.0)
            }
        else:
            return {
                'success': False,
                'error': 'All providers failed'
            }

    except Exception as e:
        logger.error(f"❌ Aggregator generation failed: {e}")
        return {'success': False, 'error': str(e)}


@app.post("/api/aggregator/add-key")
async def aggregator_add_key(request: Request):
    """
    Dynamically add API key

    Body:
    {
        "provider": "grok",  # grok, claude, openai, gemini, etc.
        "api_key": "sk-...",
        "base_url": "https://...",  # optional
        "metadata": {"purpose": "..."}  # optional
    }
    """
    try:
        data = await request.json()
        provider_str = data.get('provider', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url')
        metadata = data.get('metadata', {})

        provider_type = ProviderType(provider_str)

        success = api_aggregator.add_key(
            provider_type=provider_type,
            api_key=api_key,
            base_url=base_url,
            metadata=metadata
        )

        return {
            'success': success,
            'provider': provider_str
        }

    except Exception as e:
        logger.error(f"❌ Add key failed: {e}")
        return {'success': False, 'error': str(e)}


@app.get("/api/aggregator/providers")
async def aggregator_list_providers():
    """List available providers"""
    try:
        providers = api_aggregator.list_providers()
        return {
            'success': True,
            'providers': providers
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.post("/api/arc/suggest")
async def arc_suggest_endpoint(request: Request):
    """
    Generate ARC graph transformation suggestions

    Body:
    {
        "workflow_id": "workflow_123",
        "graph_data": {
            "nodes": [...],
            "edges": [...]
        },
        "task_context": "E-commerce checkout flow",
        "num_candidates": 10,
        "min_score": 0.5
    }
    """
    try:
        data = await request.json()
        workflow_id = data.get('workflow_id', 'unknown')
        graph_data = data.get('graph_data', {})
        task_context = data.get('task_context', '')
        num_candidates = data.get('num_candidates', 10)
        min_score = data.get('min_score', 0.5)

        result = arc_solver.suggest_connections(
            workflow_id=workflow_id,
            graph_data=graph_data,
            task_context=task_context,
            num_candidates=num_candidates,
            min_score=min_score
        )

        return {
            'success': True,
            **result
        }

    except Exception as e:
        logger.error(f"❌ ARC suggestion failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'suggestions': [],
            'top_suggestions': []
        }


@app.get("/api/arc/status")
async def arc_status_endpoint():
    """Get ARC Solver statistics"""
    try:
        stats = arc_solver.get_stats()
        return {
            'success': True,
            'stats': stats
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.post("/api/arc/load-examples")
async def arc_load_examples(request: Request):
    """
    Load few-shot examples from memory

    Body:
    {
        "limit": 20
    }
    """
    try:
        data = await request.json()
        limit = data.get('limit', 20)

        count = arc_solver.load_few_shot_examples(limit=limit)

        return {
            'success': True,
            'loaded': count
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

---

## 2️⃣ orchestrator_with_elisya.py - Orchestrator Integration

### Add imports

```python
# orchestrator_with_elisya.py - в начало файла

from src.agents.learner_initializer import LearnerInitializer, TaskComplexity
from src.agents.arc_solver_agent import create_arc_solver
```

### Update __init__

```python
# orchestrator_with_elisya.py - в __init__ метод

class ElysiaOrchestrator:
    def __init__(
        self,
        memory_manager,
        eval_agent,
        socketio=None,
        use_api=True
    ):
        self.memory_manager = memory_manager
        self.eval_agent = eval_agent
        self.socketio = socketio

        # Initialize ARC Solver
        self.arc_solver = create_arc_solver(
            memory_manager=memory_manager,
            eval_agent=eval_agent,
            prefer_api=use_api
        )
        logger.info("✅ ARC Solver initialized in orchestrator")

        # ... rest of init
```

### Add workflow completion handler

```python
# orchestrator_with_elisya.py - новый метод

async def handle_workflow_complete(self, workflow_id: str):
    """
    Called when workflow completes - generate ARC suggestions

    Args:
        workflow_id: ID of completed workflow
    """
    try:
        logger.info(f"🎯 Workflow {workflow_id} completed, generating ARC suggestions...")

        # Get workflow graph from memory
        graph_data = await self.get_workflow_graph(workflow_id)

        if not graph_data:
            logger.warning(f"⚠️  No graph data found for workflow {workflow_id}")
            return

        # Get task context
        task_context = await self.get_workflow_context(workflow_id)

        # Generate ARC suggestions
        result = self.arc_solver.suggest_connections(
            workflow_id=workflow_id,
            graph_data=graph_data,
            task_context=task_context or "Workflow completed, suggest improvements",
            num_candidates=5,  # Top-5 suggestions
            min_score=0.6      # Only high-quality suggestions
        )

        # Send to UI via Socket.IO
        if self.socketio and result['top_suggestions']:
            await self.socketio.emit('arc_suggestions', {
                'workflow_id': workflow_id,
                'suggestions': result['top_suggestions'],
                'stats': result['stats']
            })

            logger.info(f"✅ Sent {len(result['top_suggestions'])} ARC suggestions to UI")

        return result

    except Exception as e:
        logger.error(f"❌ Workflow completion handler failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def get_workflow_graph(self, workflow_id: str) -> Optional[Dict]:
    """Get workflow graph data from memory"""
    try:
        # Try to load from memory manager
        if hasattr(self.memory_manager, 'load_workflow_graph'):
            return self.memory_manager.load_workflow_graph(workflow_id)

        # Fallback: construct from stored data
        nodes = []
        edges = []

        # Query nodes
        if hasattr(self.memory_manager, 'search'):
            node_results = self.memory_manager.search(
                query=f"workflow:{workflow_id}",
                filter={'type': 'node'}
            )
            nodes = [r.get('data', {}) for r in node_results]

            edge_results = self.memory_manager.search(
                query=f"workflow:{workflow_id}",
                filter={'type': 'edge'}
            )
            edges = [r.get('data', {}) for r in edge_results]

        return {
            'nodes': nodes,
            'edges': edges
        }

    except Exception as e:
        logger.error(f"❌ Failed to get workflow graph: {e}")
        return None


async def get_workflow_context(self, workflow_id: str) -> Optional[str]:
    """Get workflow task context"""
    try:
        if hasattr(self.memory_manager, 'get_workflow_metadata'):
            metadata = self.memory_manager.get_workflow_metadata(workflow_id)
            return metadata.get('description') or metadata.get('task')

        return None

    except Exception as e:
        logger.error(f"❌ Failed to get workflow context: {e}")
        return None
```

### Call on workflow completion

```python
# orchestrator_with_elisya.py - в существующем методе обработки workflow

async def process_workflow(self, workflow_id: str, workflow_data: Dict):
    """Process workflow (existing method)"""

    # ... existing workflow processing logic ...

    # ДОБАВИТЬ В КОНЕЦ:
    # When workflow completes successfully
    if workflow_status == 'completed':
        # Generate ARC suggestions asynchronously
        asyncio.create_task(
            self.handle_workflow_complete(workflow_id)
        )
```

---

## 3️⃣ Socket.IO Events

### Add Socket.IO handlers

```python
# main.py или отдельный файл socketio_handlers.py

from src.agents.arc_solver_agent import ARCSolverAgent

# Предполагается, что arc_solver уже инициализирован

@socketio.on('request_arc_suggestions')
async def handle_arc_request(data):
    """
    Client requests ARC suggestions for workflow

    Client sends:
    {
        "workflow_id": "workflow_123",
        "graph_data": {
            "nodes": [...],
            "edges": [...]
        },
        "num_candidates": 5
    }
    """
    try:
        workflow_id = data.get('workflow_id', 'unknown')
        graph_data = data.get('graph_data', {})
        num_candidates = data.get('num_candidates', 5)

        logger.info(f"🔍 Client requested ARC suggestions for {workflow_id}")

        # Generate suggestions
        result = arc_solver.suggest_connections(
            workflow_id=workflow_id,
            graph_data=graph_data,
            task_context="User-requested suggestions",
            num_candidates=num_candidates,
            min_score=0.5
        )

        # Send back to client
        await emit('arc_suggestions_ready', {
            'workflow_id': workflow_id,
            'suggestions': result['top_suggestions'],
            'stats': result['stats'],
            'timestamp': result.get('timestamp')
        })

        logger.info(f"✅ Sent {len(result['top_suggestions'])} suggestions to client")

    except Exception as e:
        logger.error(f"❌ ARC request handler failed: {e}")
        await emit('arc_error', {
            'workflow_id': data.get('workflow_id'),
            'error': str(e)
        })


@socketio.on('apply_arc_suggestion')
async def handle_apply_suggestion(data):
    """
    Client wants to apply ARC suggestion to graph

    Client sends:
    {
        "workflow_id": "workflow_123",
        "suggestion": {
            "code": "def ...",
            "type": "connection",
            ...
        },
        "graph_data": {...}
    }
    """
    try:
        workflow_id = data.get('workflow_id')
        suggestion = data.get('suggestion', {})
        graph_data = data.get('graph_data', {})

        code = suggestion.get('code', '')

        # Apply transformation
        # (В реальности вы можете захотеть более сложную логику)
        success, result = arc_solver._safe_execute(code, graph_data)

        if success and result:
            # Send updated graph to client
            await emit('graph_updated', {
                'workflow_id': workflow_id,
                'graph_data': result
            })

            logger.info(f"✅ Applied ARC suggestion to {workflow_id}")
        else:
            await emit('arc_error', {
                'workflow_id': workflow_id,
                'error': 'Failed to apply suggestion'
            })

    except Exception as e:
        logger.error(f"❌ Apply suggestion failed: {e}")
        await emit('arc_error', {
            'workflow_id': data.get('workflow_id'),
            'error': str(e)
        })


@socketio.on('get_arc_stats')
async def handle_get_stats(data):
    """Get ARC Solver statistics"""
    try:
        stats = arc_solver.get_stats()
        await emit('arc_stats', stats)
    except Exception as e:
        await emit('arc_error', {'error': str(e)})
```

---

## 4️⃣ Frontend Integration (JavaScript/TypeScript)

### Request ARC Suggestions

```javascript
// frontend/src/services/arcService.js

export class ARCService {
  constructor(socket) {
    this.socket = socket;
    this.setupListeners();
  }

  setupListeners() {
    // Listen for suggestions
    this.socket.on('arc_suggestions', (data) => {
      console.log('📥 ARC Suggestions received:', data);
      this.handleSuggestions(data);
    });

    // Listen for errors
    this.socket.on('arc_error', (error) => {
      console.error('❌ ARC Error:', error);
    });

    // Listen for graph updates
    this.socket.on('graph_updated', (data) => {
      console.log('🔄 Graph updated:', data);
      this.handleGraphUpdate(data);
    });
  }

  requestSuggestions(workflowId, graphData, numCandidates = 5) {
    console.log('🚀 Requesting ARC suggestions...');
    this.socket.emit('request_arc_suggestions', {
      workflow_id: workflowId,
      graph_data: graphData,
      num_candidates: numCandidates
    });
  }

  applySuggestion(workflowId, suggestion, graphData) {
    console.log('✅ Applying suggestion:', suggestion.type);
    this.socket.emit('apply_arc_suggestion', {
      workflow_id: workflowId,
      suggestion: suggestion,
      graph_data: graphData
    });
  }

  handleSuggestions(data) {
    // Display suggestions in UI
    const { suggestions, stats } = data;

    suggestions.forEach((suggestion, i) => {
      console.log(`💡 Suggestion ${i + 1}:`);
      console.log(`   Type: ${suggestion.type}`);
      console.log(`   Score: ${suggestion.score}`);
      console.log(`   ${suggestion.explanation}`);
    });

    // Update UI with suggestions
    this.displaySuggestionsInUI(suggestions);
  }

  displaySuggestionsInUI(suggestions) {
    // Your UI rendering logic
    // Example: Show modal with suggestions
    const modal = document.getElementById('arc-suggestions-modal');
    const container = modal.querySelector('.suggestions-container');

    container.innerHTML = suggestions.map((s, i) => `
      <div class="suggestion-card">
        <div class="suggestion-header">
          <span class="suggestion-type">${s.type}</span>
          <span class="suggestion-score">${(s.score * 100).toFixed(0)}%</span>
        </div>
        <p class="suggestion-explanation">${s.explanation}</p>
        <button onclick="arcService.applySuggestion('${workflowId}', ${JSON.stringify(s)}, graphData)">
          Apply
        </button>
      </div>
    `).join('');

    modal.style.display = 'block';
  }
}

// Initialize
const socket = io('http://localhost:3000');
const arcService = new ARCService(socket);

// Export
export default arcService;
```

### Usage in React Component

```typescript
// frontend/src/components/WorkflowGraph.tsx

import React, { useState, useEffect } from 'react';
import arcService from '../services/arcService';

export const WorkflowGraph: React.FC = () => {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    // Listen for suggestions
    arcService.socket.on('arc_suggestions', (data) => {
      setSuggestions(data.suggestions);
      setShowSuggestions(true);
    });

    return () => {
      arcService.socket.off('arc_suggestions');
    };
  }, []);

  const handleRequestSuggestions = () => {
    arcService.requestSuggestions('workflow_123', graphData, 5);
  };

  const handleApplySuggestion = (suggestion) => {
    arcService.applySuggestion('workflow_123', suggestion, graphData);
  };

  return (
    <div className="workflow-graph">
      <button onClick={handleRequestSuggestions}>
        💡 Get AI Suggestions
      </button>

      {showSuggestions && (
        <SuggestionsModal
          suggestions={suggestions}
          onApply={handleApplySuggestion}
          onClose={() => setShowSuggestions(false)}
        />
      )}

      {/* Graph visualization */}
    </div>
  );
};
```

---

## 5️⃣ Environment Configuration

### .env Setup

```bash
# .env

# ============================================================================
# PHASE 8.0 CONFIGURATION
# ============================================================================

# OpenRouter Keys (9 keys for rotation)
OPENROUTER_KEY_1=sk-or-v1-...
OPENROUTER_KEY_2=sk-or-v1-...
OPENROUTER_KEY_3=sk-or-v1-...
OPENROUTER_KEY_4=sk-or-v1-...
OPENROUTER_KEY_5=sk-or-v1-...
OPENROUTER_KEY_6=sk-or-v1-...
OPENROUTER_KEY_7=sk-or-v1-...
OPENROUTER_KEY_8=sk-or-v1-...
OPENROUTER_KEY_9=sk-or-v1-...

# Direct API Keys (optional - fallback если OpenRouter не работает)
GROK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Encryption (optional - для API Aggregator)
ENCRYPTION_KEY=<generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

# Local Models (Ollama)
DEEPSEEK_MODEL=deepseek-v3.2:7b
HOPE_MODEL=hope-vl:7b-instruct-q4_k_m
QWEN_MODEL=qwen2:7b
```

### Generate Encryption Key

```bash
# Генерация Fernet ключа для шифрования
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Добавить в .env
ENCRYPTION_KEY=<output>
```

---

## 6️⃣ Testing Integration

### Test REST API

```bash
# Test learner creation
curl -X POST http://localhost:3000/api/learner/create \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Analyze complex workflow with 500 nodes",
    "prefer_api": false
  }'

# Test API aggregator
curl -X POST http://localhost:3000/api/aggregator/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain how neural networks work",
    "task_type": "analysis",
    "multimodal": false,
    "cheap": true
  }'

# Test ARC suggestions
curl -X POST http://localhost:3000/api/arc/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "test_workflow",
    "graph_data": {
      "nodes": [
        {"id": "auth", "type": "feature"},
        {"id": "user_db", "type": "data"}
      ],
      "edges": []
    },
    "task_context": "Authentication system",
    "num_candidates": 5
  }'

# Get ARC stats
curl http://localhost:3000/api/arc/status
```

### Test Socket.IO

```javascript
// Browser console or Node.js script
const socket = io('http://localhost:3000');

socket.emit('request_arc_suggestions', {
  workflow_id: 'test_workflow',
  graph_data: {
    nodes: [
      { id: 'auth', type: 'feature' },
      { id: 'user_db', type: 'data' }
    ],
    edges: []
  },
  num_candidates: 3
});

socket.on('arc_suggestions_ready', (data) => {
  console.log('Suggestions:', data);
});
```

---

## 🎯 Summary

### Integration Checklist

- [ ] **main.py**: Add imports, initialize components, add endpoints
- [ ] **orchestrator_with_elisya.py**: Add ARC Solver, handle workflow completion
- [ ] **Socket.IO**: Add event handlers for real-time suggestions
- [ ] **Frontend**: Integrate ARCService, display suggestions
- [ ] **.env**: Configure OpenRouter keys, encryption key
- [ ] **Testing**: Test all endpoints and Socket.IO events

### Quick Start (5 minutes)

1. **Copy integration code** from this file
2. **Configure .env** with OpenRouter keys
3. **Restart server**: `python3 main.py`
4. **Test endpoint**: `curl http://localhost:3000/api/arc/status`
5. **Use in UI**: Request suggestions via Socket.IO

---

**VETKA Phase 8.0** - Integration Complete! 🚀
