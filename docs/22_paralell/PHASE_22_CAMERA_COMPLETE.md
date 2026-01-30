# Phase 22: Camera Control - AI Agents Navigate 3D Space

**Date:** 2025-12-30
**Status:** COMPLETE

## Summary

AI agents can now control the 3D camera in VETKA visualization. This creates a shared spatial experience where agents guide users through the codebase visually.

## What We Built

### 4 Access Channels for Camera Control

| Channel | Tool Name | Use Case |
|---------|-----------|----------|
| **Claude Desktop** | `vetka_camera_focus` | MCP protocol, Claude Desktop app |
| **@mention agents** | `camera_focus` | `@qwen`, `@pm`, `@dev`, etc. in chat |
| **Hostess (default)** | `camera_focus` | Natural language: "подлети к main.py" |
| **REST API** | `vetka_camera_focus` | External agents, curl, automation |

### Commands Recognized

```
English:
- "focus on X"
- "show me X"
- "look at X"
- "zoom to X"
- "navigate to X"

Russian:
- "подлети к X"
- "покажи X"
- "перейди к X"
```

## Technical Implementation

### 1. MCP Tool (`src/mcp/tools/camera_tool.py`)
```python
class CameraControlTool(BaseMCPTool):
    name = "vetka_camera_focus"
    # For Claude Desktop and REST API
```

### 2. Agent Tool (`src/agents/tools.py`)
```python
class CameraFocusTool(BaseTool):
    name = "camera_focus"
    # For internal Ollama agents (@qwen, @pm, etc.)
```

### 3. Hostess Integration (`src/agents/hostess_agent.py`)
- Added `camera_focus` to tools list
- Updated system prompt with examples
- Added parser for camera_focus responses

### 4. Main.py Handler
```python
elif hostess_decision['action'] == 'camera_focus':
    emit('camera_control', {
        'action': 'focus',
        'target': target,
        'zoom': zoom,
        'highlight': highlight,
        'animate': True
    })
```

### 5. Frontend (`src/visualizer/tree_renderer.py`)
- `focusOnNodeByPath()` - finds node by name/path
- GSAP animation for smooth camera movement
- Supports partial path matching

## API Examples

### REST API
```bash
curl -X POST http://localhost:5001/api/mcp/call \
  -H "Content-Type: application/json" \
  -d '{"name": "vetka_camera_focus", "arguments": {"target": "main.py", "zoom": "close"}}'
```

### Chat Commands
```
подлети к main.py
покажи src/agents
focus on tools.py
```

### @mention
```
@qwen покажи мне файл hostess_agent.py
```

## Files Modified

1. `src/mcp/tools/camera_tool.py` - MCP tool (created earlier)
2. `src/agents/tools.py` - Agent tool + permissions
3. `src/agents/hostess_agent.py` - Hostess camera support
4. `main.py` - Camera focus handler in routing
5. `src/visualizer/tree_renderer.py` - Frontend camera animation

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target` | string | required | File/folder path or "overview" |
| `zoom` | enum | "medium" | "close", "medium", "far" |
| `highlight` | bool | true | Highlight target node |
| `animate` | bool | true | Smooth camera animation |

## The Vision

> "Мы создали пространство и для агентов и для людей"

This is spatial AI - agents don't just analyze code, they navigate it alongside humans. When an agent says "look at this file", the camera flies there. The 3D space becomes a shared cognitive environment.

## Next Steps

1. **Claude Desktop MCP** - Test with Claude Desktop app
2. **Create Tree Tool** - Agents create new folders/branches
3. **Highlight Connections** - Show relationships between files
4. **Waypoints** - Save camera positions for tours

## Commits

- `645b2b4` - feat: Add camera_focus tool for VETKA agents
- `3094ce4` - feat: Add vetka_camera_focus MCP tool
- Previous Phase 22 commits for MCP finalization

---

*Phase 22 Camera Control - Where AI meets spatial navigation*
