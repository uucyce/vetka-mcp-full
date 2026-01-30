# HOSTESS DECISION SCENARIOS

This file documents the logic Hostess uses to route messages.

## Decision Parameters

### 1. Task Size
- **small**: Question, explanation (< 100 tokens response)
- **medium**: Analysis, review (100-500 tokens)
- **large**: Refactoring, creation (500+ tokens)

### 2. Cost Tier
- **free**: Ollama only (qwen2:7b, llama3.1:8b)
- **cheap**: deepseek ($0.0001/1K) - DEFAULT
- **medium**: haiku ($0.00025/1K)
- **expensive**: sonnet ($0.003/1K)

### 3. Task Type
- **question**: Simple Q&A
- **code**: Code work (fix, create, refactor)
- **analysis**: Review, audit
- **creative**: Idea generation
- **planning**: Architecture, design

### 4. Execution Mode
- **single**: One model, one response
- **parallel**: Multiple agents respond independently
- **sequential**: Chain of agents (PM → Dev → QA)

---

## Scenarios

### SIMPLE_QUESTION
```
Triggers: "what", "how", "explain", "describe", "why", "when"
Size: small
Cost: free/cheap
Mode: single
Model: ollama:qwen2:7b → deepseek/deepseek-chat
Tools: NONE
Iterations: 1
```

### CODE_FIX
```
Triggers: "fix", "bug", "error", "broken", "issue", "problem"
Size: medium
Cost: cheap
Mode: single
Agent: Dev
Model: deepseek/deepseek-coder
Tools: read_file, edit_file, run_bash
Iterations: up to 3
```

### CODE_CREATE
```
Triggers: "create", "write", "implement", "add", "build"
Size: medium-large
Cost: cheap
Mode: single
Agent: Dev
Model: deepseek/deepseek-coder
Tools: read_file, write_file, search_code, run_bash
Iterations: up to 5
```

### CODE_REVIEW
```
Triggers: "review", "analyze", "check", "audit"
Size: medium
Cost: cheap
Mode: parallel
Team: PM + Dev + QA
Model: deepseek/deepseek-chat (all)
Tools: read_file, search_code
Iterations: 1 each
```

### TESTING
```
Triggers: "test", "tests", "unittest", "pytest"
Size: medium
Cost: cheap
Mode: single
Agent: QA
Model: deepseek/deepseek-coder
Tools: read_file, write_file, run_bash, search_code
Iterations: up to 3
```

### COMPLEX_TASK
```
Triggers: "refactor", "architect", "design", "plan", "migrate"
Size: large
Cost: medium (lead) + cheap (support)
Mode: sequential
Sequence: PM → Dev → QA
Lead Model: anthropic/claude-3-haiku
Support Model: deepseek/deepseek-chat
Tools: ALL
Iterations: up to 5
```

---

## Decision Logic

```
IF @mention detected:
    USE specified model(s)/agent(s)

ELSE IF task matches scenario pattern:
    USE scenario config

ELSE:
    DEFAULT to single cheap model
    NO tools
```

---

## @Mention Aliases

| Alias | Target | Type |
|-------|--------|------|
| @deepseek | deepseek/deepseek-chat | Model |
| @coder | deepseek/deepseek-coder | Model |
| @claude | anthropic/claude-3.5-sonnet | Model |
| @haiku | anthropic/claude-3-haiku | Model |
| @gemini | google/gemini-flash-1.5 | Model |
| @llama | meta-llama/llama-3.1-8b-instruct | Model |
| @qwen | ollama:qwen2:7b | Local |
| @local | ollama:qwen2:7b | Local |
| @pm | agent:PM | Agent |
| @dev | agent:Dev | Agent |
| @qa | agent:QA | Agent |

---

## Tool Safety

### Allowed Operations
- Read any file in project
- Write to allowed extensions only
- Search code with grep
- Run safe bash commands
- List directory contents

### Blocked Operations
- `rm -rf` - Recursive delete
- `sudo` - Elevated permissions
- `chmod 777` - Dangerous permissions
- `> /dev` - Device writes
- `mkfs` - Filesystem creation
- `dd if=` - Raw disk operations

### Allowed File Extensions
.py, .js, .ts, .json, .md, .txt, .html, .css, .yaml, .yml, .toml

---

## Cost Tracking

All API calls are logged with:
- Model used
- Input/output tokens
- Cost calculation
- Timestamp

Warning at $0.10 cumulative
Block at $1.00 cumulative (per session)
