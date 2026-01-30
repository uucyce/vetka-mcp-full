# VETKA Phase 7.9 - Pluggable Learner Architecture

## 🎯 Overview

Universal, extensible architecture for AI learning agents. **Add any LLM with just 3 lines of code.**

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LearnerFactory                         │
│  Registry-based factory for managing learner instances      │
└────────────┬────────────────────────────────────────────────┘
             │
             │ @register("name")
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐      ┌────▼────┐      ┌──────────┐
│Pixtral │      │  Qwen   │      │ Your LLM │
│12B     │      │  2-7B   │      │  Model   │
└────────┘      └─────────┘      └──────────┘
    │                │                  │
    └────────────────┴──────────────────┘
                     │
              ┌──────▼──────┐
              │BaseLearner  │
              │Interface    │
              └─────────────┘
```

## 📁 File Structure

```
src/agents/
├── base_learner.py         # Abstract interface
├── learner_factory.py      # Registration & creation
├── pixtral_learner.py      # Pixtral-12B (multimodal)
├── qwen_learner.py         # Qwen2-7B (text-only)
└── your_learner.py         # Add your own!
```

## 🚀 Quick Start

### 1. Use Qwen (Default - Fast & Reliable)

```bash
# No configuration needed - works out of the box
python3 main.py

# Or explicitly:
export LEARNER_TYPE=qwen
export QWEN_MODEL=qwen2:7b
python3 main.py
```

### 2. Use Pixtral (Vision-Enabled)

```bash
# Install dependencies
pip install transformers torch accelerate

# Configure
export LEARNER_TYPE=pixtral
export PIXTRAL_PATH=~/pixtral-12b

# Run
python3 main.py
```

### 3. Switch Models at Runtime

```bash
# Switch to Pixtral
curl -X POST http://localhost:5001/api/learner/switch \
  -H "Content-Type: application/json" \
  -d '{"type":"pixtral"}'

# Switch to Qwen
curl -X POST http://localhost:5001/api/learner/switch \
  -H "Content-Type: application/json" \
  -d '{"type":"qwen"}'
```

## 📊 API Endpoints

### GET /api/learner/info
Get current learner and available models

```bash
curl http://localhost:5001/api/learner/info
```

Response:
```json
{
  "current_learner": {
    "name": "qwen2:7b",
    "info": {
      "name": "Qwen2-7B",
      "type": "text-only",
      "vision": "disabled",
      "parameters": "7B",
      "source": "ollama"
    },
    "stats": {
      "total_lessons": 5,
      "avg_score": 8.4
    }
  },
  "available_learners": {
    "pixtral": "Multimodal learner with vision...",
    "qwen": "Fast, reliable fallback..."
  },
  "registered_types": ["pixtral", "qwen"]
}
```

### POST /api/learner/switch
Switch to different learner

```bash
curl -X POST http://localhost:5001/api/learner/switch \
  -H "Content-Type: application/json" \
  -d '{"type":"pixtral"}'
```

### GET /api/learner/stats
Get learning statistics

```bash
curl http://localhost:5001/api/learner/stats
```

## 🔧 Adding New Learners

### Example: Add Claude Learner

**1. Create `src/agents/claude_learner.py`:**

```python
from .base_learner import BaseLearner
from .learner_factory import LearnerFactory
import anthropic

@LearnerFactory.register("claude")
class ClaudeLearner(BaseLearner):
    """Claude Sonnet 4.5 learner via API"""

    def __init__(self, api_key: str, memory_manager=None, eval_agent=None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.memory = memory_manager
        # ... initialization

    @property
    def model_name(self) -> str:
        return "claude-sonnet-4-5"

    def get_model_info(self) -> Dict[str, str]:
        return {
            "name": "Claude Sonnet 4.5",
            "type": "text-only",
            "vision": "enabled",
            "source": "anthropic-api"
        }

    def analyze_workflow(self, workflow_data: Dict) -> Dict:
        # Use Claude API for analysis
        response = self.client.messages.create(
            model="claude-sonnet-4.5-20250929",
            messages=[{"role": "user", "content": prompt}]
        )
        # Parse and return lesson
```

**2. Import in `main.py`:**

```python
from src.agents.claude_learner import ClaudeLearner
```

**3. Add configuration:**

```python
LEARNER_CONFIG = {
    'pixtral': {...},
    'qwen': {...},
    'claude': {  # Add this
        'api_key': os.getenv('CLAUDE_API_KEY')
    }
}
```

**4. Use it:**

```bash
export LEARNER_TYPE=claude
export CLAUDE_API_KEY=sk-ant-...
python3 main.py
```

**That's it!** 🎉 Factory automatically registers and manages it.

## 🎨 Learner Comparison

| Learner  | Type       | Vision | Speed | Resource | Best For              |
|----------|------------|--------|-------|----------|-----------------------|
| Pixtral  | Multimodal | ✅     | Slow  | 25GB RAM | Complex analysis      |
| Qwen     | Text-only  | ❌     | Fast  | <1GB RAM | Quick, reliable       |
| Claude   | Multimodal | ✅     | Medium| API only | Production            |
| GPT-4    | Multimodal | ✅     | Medium| API only | Best quality          |

## 🔐 Environment Variables

```bash
# Primary configuration
LEARNER_TYPE=qwen              # Which learner to use

# Learner-specific configs
PIXTRAL_PATH=~/pixtral-12b     # Path to Pixtral model
QWEN_MODEL=qwen2:7b            # Qwen model name
CLAUDE_API_KEY=sk-ant-...      # Claude API key (if added)
GPT4_API_KEY=sk-...            # GPT-4 API key (if added)

# System
QDRANT_HOST=127.0.0.1          # Qdrant connection
```

## 🧪 Testing

```bash
# 1. Check syntax
python3 -m py_compile src/agents/*.py

# 2. Start server
python3 main.py

# 3. Check available learners
curl http://localhost:5001/api/learner/info

# 4. Get stats
curl http://localhost:5001/api/learner/stats

# 5. Test switching
curl -X POST http://localhost:5001/api/learner/switch -d '{"type":"qwen"}'

# 6. Run workflow (triggers learning)
# ... use normal workflow endpoints ...
```

## 🎓 How Learning Works

1. **Workflow Completes** → Agent analyzes results
2. **Check Threshold** → Only learn from high-quality (>0.75 score)
3. **Extract Lesson** → LLM generates structured JSON
4. **Store Triple** → Weaviate + Qdrant + ChangeLog
5. **Reuse** → Future workflows query similar lessons

## 🔄 Automatic Fallback

System automatically falls back to Qwen if primary learner fails:

```
Pixtral Load Failed → Try Qwen → Success ✅
```

## 💡 Benefits

1. **Zero Lock-in** - Switch models instantly
2. **Easy Extension** - Add new models in minutes
3. **Production Ready** - Graceful degradation
4. **Cost Optimized** - Use cheap models for simple tasks
5. **Future Proof** - New models → just add & register

## 📚 Implementation Details

### BaseLearner Interface

All learners must implement:

```python
class YourLearner(BaseLearner):
    @property
    def model_name(self) -> str:
        """Unique identifier"""

    def get_model_info(self) -> Dict:
        """Model metadata"""

    def analyze_workflow(self, workflow_data: Dict) -> Dict:
        """Extract lesson from workflow"""
```

### Registration

```python
@LearnerFactory.register("your_model")
class YourLearner(BaseLearner):
    pass
```

This automatically:
- Registers in factory
- Makes available via API
- Enables runtime switching

## 🚀 Next Steps

- [ ] Add Claude learner (API-based)
- [ ] Add GPT-4 learner (API-based)
- [ ] Add Llama 3.3 learner (local)
- [ ] Add Mistral learner (via Ollama)
- [ ] Vision analysis for Pixtral
- [ ] Multi-model ensemble (best of 3)

---

**Built for VETKA Phase 7.9** - Universal AI Learning System
