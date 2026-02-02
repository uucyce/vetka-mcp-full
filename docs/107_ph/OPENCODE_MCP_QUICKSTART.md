# OpenCode MCP Quick Start

## Quick Fix Checklist

### ✅ Fixes Applied
- [x] Added missing `logger` to `vetka_mcp_bridge.py`
- [x] Changed command from `-m module` to absolute path
- [x] Increased timeout from 10s to 30s
- [x] Set PYTHONPATH environment variable

### 🚀 How to Use

#### 1. Start VETKA Server
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python main.py
```

**Check it's running:**
```bash
curl http://localhost:5001/api/health
```

#### 2. Test MCP Bridge (Optional)
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python src/mcp/vetka_mcp_bridge.py
```
- Should wait on stdin (stdio mode)
- No errors = good
- Press `Ctrl+C` to exit

#### 3. Restart OpenCode
OpenCode needs to reload the config to pick up changes.

#### 4. Test MCP Tools in OpenCode

**Basic test:**
```
@vetka vetka_health
```

**Expected:** Health status with components

**Session init:**
```
@vetka vetka_session_init
```

**Expected:** Session ID + project digest + user preferences

**Semantic search:**
```
@vetka vetka_search_semantic query="MCP integration"
```

**Expected:** Search results from codebase

**Spawn pipeline:**
```
@vetka vetka_spawn_pipeline task="Research MCP stdio protocol" phase_type="research"
```

**Expected:** Task ID + background execution confirmation

### 🔧 Troubleshooting

#### Problem: "vetka connected" but tools don't work

**Check 1: Logger error?**
```bash
grep "logger =" /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py
```
Should show: `logger = logging.getLogger(__name__)`

**Check 2: VETKA server running?**
```bash
curl http://localhost:5001/api/health
```
Should return JSON with "status": "ok"

**Check 3: Config correct?**
```bash
cat /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/opencode.json
```
Command should be:
```json
"command": [
  "python",
  "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"
]
```

#### Problem: Timeout errors

Increase timeout in `opencode.json`:
```json
"timeout": 60000  // 60s for long-running tools
```

#### Problem: Import errors

Check PYTHONPATH:
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python -c "import sys; sys.path.insert(0, '.'); from src.mcp import vetka_mcp_bridge; print('OK')"
```

### 📊 MCP Audit Logs

Tool calls are logged to:
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/mcp_audit/mcp_audit_2026-02-02.jsonl
```

Check latest logs:
```bash
tail -f data/mcp_audit/mcp_audit_*.jsonl
```

### 🎯 Available MCP Tools

#### Read-Only Tools (Safe)
- `vetka_health` - Server health status
- `vetka_search_semantic` - Semantic search in knowledge base
- `vetka_read_file` - Read file content
- `vetka_get_tree` - Get 3D tree structure
- `vetka_list_files` - List files in directory
- `vetka_search_files` - Search files by name/content
- `vetka_git_status` - Git status
- `vetka_get_metrics` - System metrics
- `vetka_get_knowledge_graph` - Knowledge graph structure
- `vetka_read_group_messages` - Read group chat messages

#### Session & Memory Tools
- `vetka_session_init` - Initialize session with fat context
- `vetka_session_status` - Get session status
- `vetka_get_conversation_context` - Get ELISION-compressed context
- `vetka_get_user_preferences` - Get user preferences from Engram
- `vetka_get_memory_summary` - CAM + Elisium memory summary

#### Write Tools (Require Confirmation)
- `vetka_edit_file` - Edit/create files (dry_run=true by default)
- `vetka_git_commit` - Create git commits (dry_run=true by default)
- `vetka_run_tests` - Run pytest tests

#### Advanced Tools
- `vetka_call_model` - Call any LLM (Grok, GPT, Claude, Gemini, Ollama)
- `vetka_arc_suggest` - ARC workflow suggestions
- `vetka_spawn_pipeline` - Spawn fractal agent pipeline
- `vetka_execute_workflow` - Execute PM->Arch->Dev->QA workflow
- `vetka_workflow_status` - Check workflow/pipeline status

#### Compound Tools
- `vetka_research` - Research topic (search + read + summarize)
- `vetka_implement` - Plan implementation
- `vetka_review` - Review file and suggest improvements

### 📚 Configuration Reference

**Minimal config:**
```json
{
  "mcp": {
    "vetka": {
      "type": "local",
      "command": ["python", "/absolute/path/to/vetka_mcp_bridge.py"],
      "enabled": true
    }
  }
}
```

**Full config:**
```json
{
  "mcp": {
    "vetka": {
      "type": "local",
      "command": [
        "python",
        "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"
      ],
      "enabled": true,
      "timeout": 30000,
      "environment": {
        "VETKA_API_URL": "http://localhost:5001",
        "PYTHONPATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
      }
    }
  }
}
```

### 🎬 Example Workflow

```
# 1. Initialize session (loads project context)
@vetka vetka_session_init

# 2. Research a topic
@vetka vetka_research topic="MCP stdio protocol" depth="medium"

# 3. Search for specific code
@vetka vetka_search_semantic query="MCP tool registration"

# 4. Read a file
@vetka vetka_read_file file_path="src/mcp/vetka_mcp_bridge.py"

# 5. Spawn a pipeline for complex task
@vetka vetka_spawn_pipeline task="Add HTTP transport mode to MCP bridge" phase_type="build"

# 6. Check pipeline status
@vetka vetka_workflow_status
```

## Next Steps

1. **Test basic tools** - `vetka_health`, `vetka_search_semantic`
2. **Test session init** - Check project digest loading
3. **Test pipeline** - Spawn a research pipeline
4. **Monitor logs** - Watch `data/mcp_audit/` for tool calls
5. **Report issues** - Create GitHub issue or update docs

## Related Documentation

- [Full Fix Report](./opencode_mcp_fix_report.md)
- [Phase 106 MCP Documentation](../phase_106_multi_agent_mcp/)
- [OpenCode MCP Docs](https://opencode.ai/docs/mcp-servers/)
