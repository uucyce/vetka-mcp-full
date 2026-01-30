# VETKA Phase 8.0 - Universal Learner Initializer

## 🎯 Overview

Phase 8.0 introduces **LearnerInitializer** - a universal initialization system supporting multiple state-of-the-art models with automatic fallback chains and task complexity-based recommendations.

## 🤖 Supported Models

### 1. DeepSeek-V3.2-7B (Primary - Fast)
- **Type**: Text-only with sparse attention (DSA + NSA)
- **Backend**: Ollama
- **Capabilities**:
  - Sparse attention for efficient inference
  - Fast JSON generation
  - Workflow analysis
  - 8K context window
- **Recommended for**: Simple, Medium, Complex tasks
- **Resource**: Low (via Ollama)

### 2. HOPE-VL-7B (Expert - Hierarchical)
- **Type**: Multimodal with hierarchical reasoning
- **Backend**: Transformers (local)
- **Capabilities**:
  - Hierarchical multi-level planning
  - Self-modification capabilities
  - Graph-aware reasoning
  - Vision support
  - Meta-learning
- **Recommended for**: Complex, Expert tasks
- **Resource**: High (~25GB RAM)

### 3. Qwen2-7B (Fallback - Reliable)
- **Type**: Text-only general purpose
- **Backend**: Ollama
- **Capabilities**:
  - Reliable fallback for all tasks
  - Fast inference
  - Low resource usage
  - JSON output
- **Recommended for**: All complexity levels (fallback)
- **Resource**: Low (via Ollama)

## 📊 Task Complexity Levels

```python
from src.agents.learner_initializer import TaskComplexity

TaskComplexity.SIMPLE   # Basic CRUD, simple queries
TaskComplexity.MEDIUM   # Multi-step workflows, moderate reasoning
TaskComplexity.COMPLEX  # Advanced reasoning, hierarchical planning
TaskComplexity.EXPERT   # Self-improvement, meta-learning, graph reasoning
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install base dependencies
pip install ollama transformers torch accelerate

# Pull DeepSeek model (if using DeepSeek)
ollama pull deepseek-r1:7b

# Download HOPE model (if using HOPE)
# Place in ~/hope-vl-7b or set HOPE_PATH environment variable

# Qwen is already available if you have Ollama
ollama pull qwen2:7b
```

### 2. Environment Configuration

Create `.env` file:

```bash
# Primary model selection
LEARNER_TYPE=deepseek  # or "hope" or "qwen"

# Model-specific paths
DEEPSEEK_MODEL=deepseek-r1:7b
HOPE_PATH=~/hope-vl-7b
QWEN_MODEL=qwen2:7b

# Qdrant connection
QDRANT_HOST=127.0.0.1
```

### 3. Basic Usage

```python
from src.agents.learner_initializer import LearnerInitializer, TaskComplexity

# Initialize
initializer = LearnerInitializer(
    memory_manager=memory,
    eval_agent=eval_agent
)

# Create learner with automatic fallback
learner = initializer.create_with_fallback(
    preferred='deepseek',
    fallback_chain=['qwen']
)

# Or create specific learner
learner = initializer.create_learner('deepseek')
```

## 🎯 Task Complexity Recommendations

The initializer provides **recommendations** (not automatic selection) based on task complexity:

```python
# Get recommendations for task complexity
recommendations = initializer.select_by_complexity(TaskComplexity.EXPERT)
# Returns: ['hope', 'deepseek', 'qwen']

# You choose which to use based on recommendations
for model_type in recommendations:
    learner = initializer.create_learner(model_type)
    if learner:
        break  # Use first available
```

### Recommendation Matrix

| Complexity | Primary | Secondary | Fallback |
|-----------|---------|-----------|----------|
| SIMPLE    | qwen | deepseek | - |
| MEDIUM    | qwen | deepseek | - |
| COMPLEX   | deepseek | hope | qwen |
| EXPERT    | hope | deepseek | qwen |

## 🌲 Graph Context Templates

For text-only models working with graph structures, use context templates:

```python
# Prepare graph state
graph_state = {
    'total_nodes': 150,
    'total_edges': 300,
    'depth_levels': 5,
    'recent_changes': [
        'Added node: feature_X',
        'Connected: A -> B',
        'Updated: workflow_Y'
    ],
    'active_patterns': [
        'Sequential dependency chain',
        'Hub-and-spoke architecture',
        'Recursive refinement'
    ],
    'hierarchy': {
        'level_0': 'Root concepts (10 nodes)',
        'level_1': 'Main features (35 nodes)',
        'level_2': 'Sub-components (80 nodes)',
        'level_3': 'Implementation details (25 nodes)'
    },
    'attention_focus': [
        'Recent workflow failures',
        'High-scoring patterns',
        'Dependency bottlenecks'
    ]
}

# Generate context template for DeepSeek
context = initializer.get_context_template('deepseek', graph_state)

# Use in prompt
prompt = f"""
{context}

TASK: Analyze the recent workflow and extract learnings...
"""
```

### Example Context Output

```
CURRENT GRAPH STATE:
- Total nodes: 150
- Total edges: 300
- Depth levels: 5

RECENT CHANGES:
- Added node: feature_X
- Connected: A -> B
- Updated: workflow_Y

ACTIVE PATTERNS:
- Sequential dependency chain
- Hub-and-spoke architecture
- Recursive refinement

ATTENTION FOCUS AREAS:
- Recent workflow failures
- High-scoring patterns
- Dependency bottlenecks
```

## 🔄 Fallback Chains

Automatic fallback ensures system always has a working learner:

```python
# Attempt DeepSeek → fallback to Qwen
learner = initializer.create_with_fallback(
    preferred='deepseek',
    fallback_chain=['qwen']
)

# Attempt HOPE → DeepSeek → Qwen
learner = initializer.create_with_fallback(
    preferred='hope',
    fallback_chain=['deepseek', 'qwen']
)
```

Output:
```
🔄 Creating learner with fallback chain:
   Preferred: hope
   Fallback: deepseek → qwen

🔨 Creating HOPE-VL-7B learner...
   Type: hope
   Backend: transformers
   Capabilities: hierarchical-reasoning, self-modification, graph-aware...
   Checking dependencies for transformers...
   ⚠️  Model path not found: /Users/user/hope-vl-7b
      Set environment variable (e.g., HOPE_PATH)

⚠️  Falling back to: deepseek

🔨 Creating DeepSeek-V3.2-7B learner...
   Checking dependencies for ollama...
   ✅ ollama package available
   ✅ Model 'deepseek-r1:7b' available in Ollama
✅ DeepSeek-V3.2-7B learner created successfully
```

## 📋 Model Information API

```python
# Get info about specific model
info = initializer.get_model_info('deepseek')
# Returns:
{
    'name': 'DeepSeek-V3.2-7B',
    'type': 'deepseek',
    'backend': 'ollama',
    'capabilities': ['sparse-attention', 'fast-inference', ...],
    'recommended_for': ['simple', 'medium', 'complex'],
    'dependencies_ok': True
}

# List all available models
all_models = initializer.list_all_models()
```

Example output:
```
======================================================================
📋 AVAILABLE LEARNER MODELS
======================================================================

DeepSeek-V3.2-7B (deepseek):
   Backend: ollama
   Capabilities: sparse-attention, fast-inference, text-only...
   Recommended for: simple, medium, complex
   Dependencies: ✅

HOPE-VL-7B (hope):
   Backend: transformers
   Capabilities: hierarchical-reasoning, self-modification, graph-aware...
   Recommended for: complex, expert
   Dependencies: ❌

Qwen2-7B (qwen):
   Backend: ollama
   Capabilities: text-only, fast-inference, reliable-fallback...
   Recommended for: simple, medium, complex, expert
   Dependencies: ✅

======================================================================
```

## 🛠️ Advanced Usage

### 1. Custom Configuration Override

```python
# Create DeepSeek with custom temperature
learner = initializer.create_learner(
    'deepseek',
    temperature=0.9,  # Override default 0.7
    max_tokens=1500   # Override default 1000
)
```

### 2. Dependency Checking

```python
# Check if model dependencies are available
deps_ok = initializer._check_dependencies('deepseek')

if deps_ok:
    learner = initializer.create_learner('deepseek')
else:
    print("DeepSeek dependencies not available")
    learner = initializer.create_learner('qwen')
```

### 3. Integration with Existing Factory

The initializer works seamlessly with the existing LearnerFactory:

```python
from src.agents.learner_factory import LearnerFactory
from src.agents.learner_initializer import LearnerInitializer

# Both use the same factory registration
initializer = LearnerInitializer()

# Initializer uses factory internally
learner = initializer.create_learner('qwen')

# Direct factory access still works
learner = LearnerFactory.create('qwen', model='qwen2:7b')
```

## 🔧 Model-Specific Features

### DeepSeek-V3.2 (Sparse Attention)

```python
learner = initializer.create_learner('deepseek')

# DeepSeek benefits from attention focus hints
context = initializer.get_context_template('deepseek', {
    'attention_focus': [
        'Recent workflow failures',
        'High-scoring patterns',
        'Dependency bottlenecks'
    ]
})
```

### HOPE-VL (Hierarchical Reasoning)

```python
learner = initializer.create_learner('hope')

# HOPE benefits from hierarchical structure
context = initializer.get_context_template('hope', {
    'hierarchy': {
        'level_0': 'Root concepts',
        'level_1': 'Main features',
        'level_2': 'Sub-components'
    }
})
```

### Qwen2 (Fast Fallback)

```python
learner = initializer.create_learner('qwen')

# Qwen is optimized for speed and reliability
# Use for simple tasks or when others unavailable
```

## 📊 Performance Comparison

| Model | Speed | Quality | Resource | Vision | Graph-Aware |
|-------|-------|---------|----------|--------|-------------|
| DeepSeek | ⚡⚡⚡ | ⭐⭐⭐ | Low | ❌ | ✅ (via context) |
| HOPE | ⚡ | ⭐⭐⭐⭐⭐ | High | ✅ | ✅ (native) |
| Qwen | ⚡⚡⚡ | ⭐⭐⭐ | Low | ❌ | ✅ (via context) |

## 🎓 Real-World Examples

### Example 1: Simple Task

```python
# For simple CRUD operations
recommendations = initializer.select_by_complexity(TaskComplexity.SIMPLE)
# ['qwen', 'deepseek', 'hope']

learner = initializer.create_with_fallback(
    preferred=recommendations[0],  # qwen
    fallback_chain=recommendations[1:]
)
```

### Example 2: Complex Analysis

```python
# For complex workflow analysis
recommendations = initializer.select_by_complexity(TaskComplexity.COMPLEX)
# ['deepseek', 'hope', 'qwen']

learner = initializer.create_with_fallback(
    preferred=recommendations[0],  # deepseek
    fallback_chain=recommendations[1:]
)
```

### Example 3: Expert Meta-Learning

```python
# For self-improvement and meta-learning
recommendations = initializer.select_by_complexity(TaskComplexity.EXPERT)
# ['hope', 'deepseek', 'qwen']

learner = initializer.create_with_fallback(
    preferred=recommendations[0],  # hope
    fallback_chain=recommendations[1:]
)

# Provide rich graph context
graph_state = {...}
context = initializer.get_context_template('hope', graph_state)
```

## 🔐 Environment Variables Reference

```bash
# ============================================
# LEARNER INITIALIZER CONFIGURATION
# ============================================

# Primary model selection
LEARNER_TYPE=deepseek  # deepseek, hope, or qwen

# DeepSeek configuration
DEEPSEEK_MODEL=deepseek-r1:7b

# HOPE configuration
HOPE_PATH=~/hope-vl-7b

# Qwen configuration (fallback)
QWEN_MODEL=qwen2:7b

# ============================================
# SYSTEM CONFIGURATION
# ============================================

# Qdrant connection
QDRANT_HOST=127.0.0.1
```

## 🚀 Migration from Phase 7.9

Phase 7.9 code:
```python
# Old way
from src.agents.learner_factory import LearnerFactory

learner = LearnerFactory.create('qwen', model='qwen2:7b')
```

Phase 8.0 code (backward compatible):
```python
# New way (with fallback and recommendations)
from src.agents.learner_initializer import LearnerInitializer, TaskComplexity

initializer = LearnerInitializer()
learner = initializer.create_with_fallback('deepseek', ['qwen'])

# Or use complexity-based recommendations
recommendations = initializer.select_by_complexity(TaskComplexity.COMPLEX)
learner = initializer.create_learner(recommendations[0])
```

## 🐛 Troubleshooting

### DeepSeek not available
```bash
# Pull the model
ollama pull deepseek-r1:7b

# Verify
ollama list | grep deepseek
```

### HOPE not found
```bash
# Set environment variable
export HOPE_PATH=/path/to/hope-vl-7b

# Or download to default location
# (Place model files in ~/hope-vl-7b)
```

### All models failing
```bash
# Ensure Qwen is available as fallback
ollama pull qwen2:7b

# Test
python3 -c "from src.agents.learner_initializer import LearnerInitializer; init = LearnerInitializer(); init.list_all_models()"
```

## 🎯 Benefits

1. **Flexibility**: Support for multiple model types (Ollama, transformers, API)
2. **Reliability**: Automatic fallback chains ensure system always works
3. **Intelligence**: Task complexity-based recommendations
4. **Efficiency**: Sparse attention (DeepSeek) and hierarchical reasoning (HOPE)
5. **Context-Aware**: Graph state templates for text-only models
6. **Production-Ready**: Comprehensive dependency checking and error handling

## 📚 Next Steps

- [ ] Add Claude API support (API-based learner)
- [ ] Add GPT-4 support (API-based learner)
- [ ] Implement automatic complexity detection
- [ ] Add multi-model ensemble (best-of-3 voting)
- [ ] Vision analysis integration for HOPE
- [ ] Self-modification loop for HOPE meta-learning

---

**Built for VETKA Phase 8.0** - Universal AI Learning with DeepSeek + HOPE + Qwen
