# PHASE I-J-K: Economic Model Routing + Agentic Tools

**Date:** 2025-12-27
**Status:** COMPLETED

---

## Overview

This phase implements three major improvements to VETKA's chat system:

1. **Phase I** - Economic model routing (use cheap models by default)
2. **Phase J** - Agentic tools (read/write files, execute commands)
3. **Phase K** - Smart routing with @mentions and scenarios

---

## PHASE I: Economic Model Routing

### Problem
- System was using expensive models like `gpt-4o-mini` and `gemini-2.0-flash-exp` ($0.01/1K tokens)
- $3+ spent on a single prompt
- No fallback chain for API failures

### Solution

#### 1. Model Configuration (`main.py:118-195`)

```python
MODEL_CONFIG = {
    'cheap': {
        'default': 'deepseek/deepseek-chat',      # $0.0001/1K - PRIMARY!
        'code': 'deepseek/deepseek-coder',        # $0.0001/1K
        'fast': 'meta-llama/llama-3.1-8b-instruct',  # $0.0001/1K
    },
    'medium': {
        'default': 'anthropic/claude-3-haiku',    # $0.00025/1K
        'fast': 'google/gemini-flash-1.5',        # $0.00015/1K
    },
    'premium': {
        'default': 'anthropic/claude-3.5-sonnet', # $0.003/1K
    },
    'banned': [
        'google/gemini-2.0-flash-exp',   # $0.01/1K - ate $3!
        'anthropic/claude-3-opus',       # $0.015/1K
        'openai/gpt-4',                  # $0.03/1K
    ],
    'ollama': {
        'default': 'qwen2:7b',
        'code': 'deepseek-coder:6.7b',
    }
}
```

#### 2. API Key Rotation (`main.py:121-148`)

```python
OPENROUTER_KEYS = [
    os.getenv('OPENROUTER_KEY_1', 'sk-or-v1-...'),
    # ... 9 keys total
]

_current_key_index = 0
_key_lock = threading.Lock()

def get_openrouter_key() -> str:
    """Get current OpenRouter API key"""
    return OPENROUTER_KEYS[_current_key_index % len(OPENROUTER_KEYS)]

def rotate_openrouter_key() -> str:
    """Rotate to next API key on error"""
    global _current_key_index
    with _key_lock:
        _current_key_index = (_current_key_index + 1) % len(OPENROUTER_KEYS)
        return OPENROUTER_KEYS[_current_key_index]
```

#### 3. Banned Model Check (`main.py:4099-4116`)

```python
# Check if model is banned (too expensive)
if is_model_banned(selected_model):
    print(f"⚠️  Model {selected_model} is BANNED! Using deepseek instead.")
    selected_model = get_model_for_tier('default', 'cheap')
```

### Cost Savings

| Before | After |
|--------|-------|
| gemini-2.0-flash: $0.01/1K | deepseek-chat: $0.0001/1K |
| ~$3 per complex prompt | ~$0.03 per complex prompt |
| **100x cheaper!** | |

---

## PHASE J: Agentic Tools

### New File: `src/agents/agentic_tools.py`

Complete module for agent tools with:

#### Tool Definitions

```python
TOOL_DEFINITIONS = {
    "read_file": {
        "name": "read_file",
        "description": "Read content of a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "lines": {"type": "string", "description": "Line range like '1-50'"}
            },
            "required": ["path"]
        }
    },
    "write_file": {...},
    "edit_file": {...},
    "search_code": {...},
    "run_bash": {...},
    "list_files": {...}
}
```

#### ToolExecutor Class

```python
class ToolExecutor:
    """Safe executor for agent tools"""

    def __init__(self, project_root=None):
        self.root = Path(project_root) if project_root else PROJECT_ROOT
        self.allowed_extensions = ['.py', '.js', '.json', '.md', ...]
        self.blocked_commands = ['rm -rf', 'sudo', 'chmod 777', ...]

    def execute(self, tool_name: str, params: dict) -> dict:
        method = getattr(self, f"_exec_{tool_name}", None)
        if not method:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            result = method(params)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_read_file(self, params): ...
    def _exec_write_file(self, params): ...
    def _exec_edit_file(self, params): ...
    def _exec_search_code(self, params): ...
    def _exec_run_bash(self, params): ...
    def _exec_list_files(self, params): ...
```

#### Safety Features

- Path escape prevention (files must be within project root)
- Blocked dangerous commands (rm -rf, sudo, etc.)
- File extension whitelist
- Max file size limits
- Output truncation

---

## PHASE K: Smart Routing

### @Mention Syntax

Users can now use @mentions to specify models/agents:

```
@deepseek fix the bug in main.py      # Use deepseek directly
@coder implement function X            # Use deepseek-coder
@pm @dev review this code              # Two agents in parallel
what is this file?                     # Hostess decides (auto)
```

### Configuration: `data/config.json`

```json
{
  "version": "1.0",
  "models": {
    "aliases": {
      "@deepseek": "deepseek/deepseek-chat",
      "@coder": "deepseek/deepseek-coder",
      "@claude": "anthropic/claude-3.5-sonnet",
      "@haiku": "anthropic/claude-3-haiku",
      "@qwen": "ollama:qwen2:7b",
      "@pm": "agent:PM",
      "@dev": "agent:Dev",
      "@qa": "agent:QA"
    },
    "defaults": {
      "cheap": "deepseek/deepseek-chat",
      "code": "deepseek/deepseek-coder",
      "complex": "anthropic/claude-3.5-sonnet"
    }
  },
  "scenarios": {
    "simple_question": {
      "patterns": ["what", "how", "explain"],
      "agents": "single",
      "model_tier": "cheap",
      "tools": []
    },
    "code_fix": {
      "patterns": ["fix", "bug", "error"],
      "agents": "single",
      "model_tier": "code",
      "tools": ["read_file", "edit_file", "run_bash"]
    },
    "code_review": {
      "patterns": ["review", "analyze"],
      "agents": "parallel",
      "team": ["PM", "Dev", "QA"],
      "tools": ["read_file", "search_code"]
    }
  }
}
```

### Mention Parser

```python
def parse_mentions(message: str) -> dict:
    """
    Parse @mentions in user message

    Returns:
        {
            'mentions': [{'alias': '@deepseek', 'target': 'deepseek/deepseek-chat', 'type': 'model'}],
            'clean_message': 'fix main.py',
            'mode': 'single',  # auto | single | team | agents
            'models': ['deepseek/deepseek-chat'],
            'agents': []
        }
    """
```

### Hostess Decision Logic

```python
def hostess_decide(message: str, parsed_mentions: dict) -> dict:
    """
    Hostess decides how to handle the message.

    Returns:
        {
            'mode': 'single' | 'parallel' | 'sequential',
            'models': ['model1', ...],
            'agents': ['PM', 'Dev', ...],
            'tools': ['read_file', ...],
            'scenario': 'code_fix',
            'max_iterations': 3
        }
    """
```

---

## API Endpoints

### Config Management

```bash
# Get config (without API keys)
GET /api/config

# Update config (partial update)
POST /api/config
Content-Type: application/json
{"routing": {"default_strategy": "quality_first"}}
```

### Mentions

```bash
# Get available @mentions for autocomplete
GET /api/mentions

# Response:
{
  "success": true,
  "mentions": [
    {"alias": "@deepseek", "target": "deepseek/deepseek-chat", "description": "Fast & cheap"},
    {"alias": "@pm", "target": "agent:PM", "description": "Project Manager agent"}
  ]
}
```

### Models

```bash
# Get available models
GET /api/models/available

# Response:
{
  "success": true,
  "available": {"ollama": [...], "openrouter": [...]},
  "defaults": {"cheap": "deepseek/deepseek-chat", ...},
  "aliases": {"@deepseek": "deepseek/deepseek-chat", ...}
}
```

### Tools

```bash
# Get available tools
GET /api/tools/available

# Execute tool (for debugging)
POST /api/tools/execute
Content-Type: application/json
{"tool": "read_file", "params": {"path": "main.py", "lines": "1-50"}}
```

---

## Files Changed

### New Files

| File | Description |
|------|-------------|
| `data/config.json` | Central configuration for models, routing, scenarios |
| `src/agents/agentic_tools.py` | Agentic tools module (550+ lines) |
| `data/skills/hostess_scenarios.md` | Documentation for scenarios |

### Modified Files

| File | Changes |
|------|---------|
| `main.py` | +200 lines: imports, API endpoints, @mention handling |
| `src/visualizer/tree_renderer.py` | CSS resize fix |

---

## UI Changes

### Summary Labels (English)

Before:
```
✅ Принять | ✏️ Доработать | ❌ Отклонить
```

After:
```
✅ Accept | ✏️ Refine | ❌ Reject
```

### Single Agent Buttons (English)

Before:
```
🔍 Подробнее | ✏️ Улучшить | 🪧 Тесты | 👥 Вся команда
```

After:
```
🔍 Details | ✏️ Improve | 🧪 Tests | 👥 Full Team
```

### CSS Fix

Removed `resize: none` from `#chat-panel` to allow JS resize handlers to work properly.

---

## Testing

### Syntax Check

```bash
python3 -m py_compile main.py && \
python3 -m py_compile src/agents/agentic_tools.py && \
echo "✅ All syntax OK"
```

### API Tests

```bash
# Test mentions endpoint
curl http://localhost:5001/api/mentions

# Test tools endpoint
curl http://localhost:5001/api/tools/available

# Test tool execution
curl -X POST http://localhost:5001/api/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "read_file", "params": {"path": "main.py", "lines": "1-10"}}'
```

### Chat Tests

```
# Test @mention parsing
User: "@deepseek what is this file?"
Expected: Single deepseek model responds

User: "@PM @Dev analyze main.py"
Expected: PM and Dev respond in parallel

User: "fix the bug in main.py"
Expected: Hostess routes to Dev with code_fix scenario
```

---

## Summary

| Phase | Status | Key Changes |
|-------|--------|-------------|
| Phase I | ✅ Complete | Economic models, API rotation, banned list |
| Phase J | ✅ Complete | ToolExecutor, 6 tools, safety features |
| Phase K | ✅ Complete | @mentions, scenarios, config API |

**Total changes:** ~800 lines of new code

**Expected savings:** 100x reduction in API costs

---

## Next Steps

1. **UI Autocomplete** - Add @mention dropdown in chat input
2. **Tool Streaming** - Show tool execution steps in real-time
3. **Cost Tracking** - Log and display API costs per session
4. **Agentic Loop Integration** - Full tool-use iteration in chat
