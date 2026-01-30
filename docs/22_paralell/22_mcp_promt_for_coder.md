# VETKA MCP Server - Phase 22 Completion

## 🎯 ЗАДАЧА
Завершить интеграцию MCP (Model Context Protocol) сервера для VETKA.
Haiku начал работу, нужно проверить что есть и дописать недостающее.

## 📋 ШАГ 1: АНАЛИЗ (обязательно перед кодом!)

Выполни команды и сообщи результат:
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Что есть в MCP модуле
echo "=== MCP Structure ===" && find src/mcp -type f -name "*.py" | head -20
echo "=== Tools ===" && ls -la src/mcp/tools/
echo "=== Schemas ===" && ls -la src/mcp/schemas/

# Содержимое существующих файлов
for f in src/mcp/*.py src/mcp/tools/*.py; do 
  echo -e "\n=== $f ===" && wc -l "$f" && head -30 "$f"
done

# Проверка main.py на наличие /mcp namespace
grep -n "namespace='/mcp'" main.py || echo "❌ /mcp namespace NOT registered"
grep -n "from src.mcp" main.py || echo "❌ MCP not imported"
```

## 📋 ШАГ 2: ДОПИСАТЬ НЕДОСТАЮЩЕЕ

### 2.1 Если src/mcp/tools/ пустая - создать tools:

**src/mcp/tools/__init__.py:**
```python
"""VETKA MCP Tools"""
from .base_tool import BaseMCPTool
from .search_tool import SearchTool
from .tree_tool import GetTreeTool, GetNodeTool
from .branch_tool import CreateBranchTool
from .list_files_tool import ListFilesTool
from .read_file_tool import ReadFileTool

__all__ = [
    'BaseMCPTool',
    'SearchTool', 
    'GetTreeTool', 
    'GetNodeTool',
    'CreateBranchTool',
    'ListFilesTool',
    'ReadFileTool',
]
```

**src/mcp/tools/base_tool.py:**
```python
"""Base class for MCP tools"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseMCPTool(ABC):
    """Abstract base for all MCP tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (e.g. vetka_search)"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description"""
        pass
    
    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """OpenAI-compatible parameter schema"""
        pass
    
    def validate_arguments(self, args: Dict[str, Any]) -> Optional[str]:
        """Validate args. Return error message or None if valid."""
        return None
    
    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool. Return {success: bool, result: ...} or {success: false, error: ...}"""
        pass
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema
            }
        }
```

**src/mcp/tools/search_tool.py:**
```python
"""Semantic search tool"""
from typing import Any, Dict, Optional
from .base_tool import BaseMCPTool

class SearchTool(BaseMCPTool):
    def __init__(self):
        self._memory = None
    
    def _get_memory(self):
        if self._memory is None:
            try:
                from src.orchestration.memory_manager import get_memory_manager
                self._memory = get_memory_manager()
            except:
                self._memory = None
        return self._memory
    
    @property
    def name(self) -> str:
        return "vetka_search"
    
    @property
    def description(self) -> str:
        return "Search VETKA knowledge base using semantic search"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10, "description": "Max results"}
            },
            "required": ["query"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "")
        limit = min(arguments.get("limit", 10), 20)
        
        memory = self._get_memory()
        if memory:
            try:
                results = memory.search_similar(query, limit=limit)
                return {"success": True, "result": {"query": query, "results": results}}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Fallback: простой поиск по файлам
        import os
        from pathlib import Path
        
        matches = []
        root = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
        for f in root.rglob("*.py"):
            if query.lower() in f.name.lower():
                matches.append({"path": str(f.relative_to(root)), "type": "file"})
        for f in root.rglob("*.md"):
            if query.lower() in f.name.lower():
                matches.append({"path": str(f.relative_to(root)), "type": "file"})
        
        return {"success": True, "result": {"query": query, "results": matches[:limit]}}
```

**src/mcp/tools/tree_tool.py:**
```python
"""Tree structure tools"""
import os
from pathlib import Path
from typing import Any, Dict, List
from .base_tool import BaseMCPTool

PROJECT_ROOT = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"

class GetTreeTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "vetka_get_tree"
    
    @property
    def description(self) -> str:
        return "Get VETKA folder/file tree structure"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "", "description": "Relative path"},
                "depth": {"type": "integer", "default": 3, "description": "Max depth (1-5)"}
            }
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rel_path = arguments.get("path", "").strip("/")
        depth = min(max(arguments.get("depth", 3), 1), 5)
        full_path = Path(PROJECT_ROOT) / rel_path
        
        if not full_path.exists():
            return {"success": False, "error": f"Path not found: {rel_path}"}
        
        def walk(p: Path, d: int) -> List[Dict]:
            if d <= 0 or not p.is_dir():
                return []
            items = []
            try:
                for item in sorted(p.iterdir()):
                    if item.name.startswith('.') or item.name == '__pycache__':
                        continue
                    entry = {
                        "name": item.name,
                        "path": str(item.relative_to(PROJECT_ROOT)),
                        "type": "directory" if item.is_dir() else "file"
                    }
                    if item.is_dir():
                        entry["children"] = walk(item, d - 1)
                    items.append(entry)
            except PermissionError:
                pass
            return items
        
        tree = walk(full_path, depth)
        return {"success": True, "result": {"path": rel_path or "/", "tree": tree}}


class GetNodeTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "vetka_get_node"
    
    @property
    def description(self) -> str:
        return "Get details about a specific file or folder"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to node"}
            },
            "required": ["path"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rel_path = arguments.get("path", "").strip("/")
        full_path = Path(PROJECT_ROOT) / rel_path
        
        if not full_path.exists():
            return {"success": False, "error": f"Not found: {rel_path}"}
        
        stat = full_path.stat()
        result = {
            "name": full_path.name,
            "path": rel_path,
            "type": "directory" if full_path.is_dir() else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime
        }
        
        if full_path.is_file() and stat.st_size < 50000:
            try:
                result["preview"] = full_path.read_text()[:500]
            except:
                result["preview"] = None
        
        return {"success": True, "result": result}
```

**src/mcp/tools/branch_tool.py:**
```python
"""Branch creation tool"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from .base_tool import BaseMCPTool

PROJECT_ROOT = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"

class CreateBranchTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "vetka_create_branch"
    
    @property
    def description(self) -> str:
        return "Create a new folder (branch) in VETKA tree"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Folder name"},
                "parent_path": {"type": "string", "default": "", "description": "Parent path"},
                "description": {"type": "string", "default": "", "description": "Description"},
                "dry_run": {"type": "boolean", "default": True, "description": "Preview only"}
            },
            "required": ["name"]
        }
    
    def validate_arguments(self, args: Dict[str, Any]) -> str:
        name = args.get("name", "")
        if not name or "/" in name or ".." in name:
            return "Invalid folder name"
        return None
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        name = arguments["name"]
        parent = arguments.get("parent_path", "").strip("/")
        description = arguments.get("description", "")
        dry_run = arguments.get("dry_run", True)
        
        full_path = Path(PROJECT_ROOT) / parent / name
        
        if dry_run:
            return {
                "success": True,
                "result": {
                    "action": "dry_run",
                    "would_create": str(full_path.relative_to(PROJECT_ROOT)),
                    "exists": full_path.exists()
                }
            }
        
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Metadata file
            meta_path = full_path / ".vetka_branch.json"
            meta_path.write_text(json.dumps({
                "name": name,
                "created": datetime.utcnow().isoformat(),
                "description": description
            }, indent=2))
            
            return {
                "success": True,
                "result": {"path": str(full_path.relative_to(PROJECT_ROOT))}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

**src/mcp/tools/list_files_tool.py:**
```python
"""List files tool"""
from pathlib import Path
from typing import Any, Dict, List
from .base_tool import BaseMCPTool

PROJECT_ROOT = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"

class ListFilesTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "vetka_list_files"
    
    @property
    def description(self) -> str:
        return "List files in a directory with optional recursion"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "", "description": "Directory path"},
                "depth": {"type": "integer", "default": 1, "description": "Recursion depth (1-5)"},
                "pattern": {"type": "string", "default": "*", "description": "Glob pattern"}
            }
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rel_path = arguments.get("path", "").strip("/")
        depth = min(max(arguments.get("depth", 1), 1), 5)
        pattern = arguments.get("pattern", "*")
        
        root = Path(PROJECT_ROOT) / rel_path
        if not root.is_dir():
            return {"success": False, "error": f"Not a directory: {rel_path}"}
        
        items: List[Dict] = []
        
        def collect(p: Path, d: int):
            if d <= 0:
                return
            try:
                for item in p.glob(pattern):
                    if item.name.startswith('.') or '__pycache__' in str(item):
                        continue
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(item.relative_to(PROJECT_ROOT)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None
                    })
                    if item.is_dir() and d > 1:
                        collect(item, d - 1)
            except:
                pass
        
        collect(root, depth)
        return {"success": True, "result": {"path": rel_path or "/", "items": items[:100]}}
```

**src/mcp/tools/read_file_tool.py:**
```python
"""Read file tool"""
import base64
from pathlib import Path
from mimetypes import guess_type
from typing import Any, Dict
from .base_tool import BaseMCPTool

PROJECT_ROOT = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
MAX_SIZE = 500_000  # 500KB

class ReadFileTool(BaseMCPTool):
    @property
    def name(self) -> str:
        return "vetka_read_file"
    
    @property
    def description(self) -> str:
        return "Read file content (text or base64 for binary)"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "max_lines": {"type": "integer", "default": 500, "description": "Max lines for text"}
            },
            "required": ["path"]
        }
    
    def validate_arguments(self, args: Dict[str, Any]) -> str:
        path = args.get("path", "")
        if ".." in path:
            return "Invalid path"
        return None
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rel_path = arguments["path"].strip("/")
        max_lines = arguments.get("max_lines", 500)
        full_path = Path(PROJECT_ROOT) / rel_path
        
        if not full_path.is_file():
            return {"success": False, "error": f"File not found: {rel_path}"}
        
        if full_path.stat().st_size > MAX_SIZE:
            return {"success": False, "error": f"File too large (>{MAX_SIZE} bytes)"}
        
        mime, _ = guess_type(str(full_path))
        is_text = mime is None or mime.startswith('text/') or mime in [
            'application/json', 'application/javascript', 'application/xml'
        ]
        
        try:
            if is_text:
                lines = full_path.read_text(errors='replace').splitlines()
                content = "\n".join(lines[:max_lines])
                truncated = len(lines) > max_lines
                return {
                    "success": True,
                    "result": {
                        "path": rel_path,
                        "content": content,
                        "encoding": "utf-8",
                        "truncated": truncated,
                        "total_lines": len(lines)
                    }
                }
            else:
                content = base64.b64encode(full_path.read_bytes()).decode()
                return {
                    "success": True,
                    "result": {
                        "path": rel_path,
                        "content": content,
                        "encoding": "base64",
                        "mime_type": mime
                    }
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### 2.2 Обновить src/mcp/mcp_server.py (добавить регистрацию tools):

В конец `__init__` метода MCPServer добавить:
```python
# Register all tools
from .tools import SearchTool, GetTreeTool, GetNodeTool, CreateBranchTool, ListFilesTool, ReadFileTool

self.register_tool(SearchTool())
self.register_tool(GetTreeTool())
self.register_tool(GetNodeTool())
self.register_tool(CreateBranchTool())
self.register_tool(ListFilesTool())
self.register_tool(ReadFileTool())
```

### 2.3 Добавить в main.py регистрацию /mcp namespace:

Найди место после `socketio = SocketIO(app, ...)` и добавь:
```python
# ============== MCP INTEGRATION ==============
from src.mcp import MCPServer

mcp_server = MCPServer(socketio)

@socketio.on('connect', namespace='/mcp')
def mcp_connect():
    from flask import request
    print(f"[MCP] Agent connected: {request.sid}")
    socketio.emit('welcome', {
        'message': 'VETKA MCP Server ready',
        'tools': [t.name for t in mcp_server.tools.values()]
    }, namespace='/mcp', to=request.sid)

@socketio.on('disconnect', namespace='/mcp')
def mcp_disconnect():
    from flask import request
    print(f"[MCP] Agent disconnected: {request.sid}")

@socketio.on('list_tools', namespace='/mcp')
def mcp_list_tools():
    """Return available tools in OpenAI format"""
    from flask import request
    tools = [t.to_openai_schema() for t in mcp_server.tools.values()]
    socketio.emit('tools_list', {'tools': tools}, namespace='/mcp', to=request.sid)

@socketio.on('tool_call', namespace='/mcp')
def mcp_tool_call(data):
    """Execute a tool call (JSON-RPC style)"""
    from flask import request
    import uuid
    
    request_id = data.get('id', str(uuid.uuid4()))
    tool_name = data.get('name')
    arguments = data.get('arguments', {})
    
    print(f"[MCP] Tool call: {tool_name} with {arguments}")
    
    tool = mcp_server.tools.get(tool_name)
    if not tool:
        socketio.emit('tool_result', {
            'id': request_id,
            'error': f'Tool not found: {tool_name}'
        }, namespace='/mcp', to=request.sid)
        return
    
    # Validate
    validation_error = tool.validate_arguments(arguments)
    if validation_error:
        socketio.emit('tool_result', {
            'id': request_id,
            'error': validation_error
        }, namespace='/mcp', to=request.sid)
        return
    
    # Execute
    try:
        result = tool.execute(arguments)
        socketio.emit('tool_result', {
            'id': request_id,
            'result': result
        }, namespace='/mcp', to=request.sid)
    except Exception as e:
        socketio.emit('tool_result', {
            'id': request_id,
            'error': str(e)
        }, namespace='/mcp', to=request.sid)

# REST endpoint для статуса MCP
@app.route('/api/mcp/status', methods=['GET'])
def mcp_status():
    return jsonify({
        'status': 'active',
        'tools': list(mcp_server.tools.keys()),
        'namespace': '/mcp'
    })

print("[MCP] ✅ MCP Server initialized with", len(mcp_server.tools), "tools")
# ============== END MCP ==============
```

### 2.4 Создать тест tests/test_mcp_server.py:
```python
"""MCP Server Tests"""
import pytest
import socketio
import time

MCP_URL = "http://localhost:5001"

@pytest.fixture
def sio():
    client = socketio.Client()
    client.connect(MCP_URL, namespaces=['/mcp'])
    yield client
    client.disconnect()

def test_connect(sio):
    """Test connection to /mcp namespace"""
    assert sio.connected
    print("✅ Connected to /mcp")

def test_list_tools(sio):
    """Test list_tools returns tools"""
    received = []
    
    @sio.on('tools_list', namespace='/mcp')
    def on_tools(data):
        received.append(data)
    
    sio.emit('list_tools', namespace='/mcp')
    time.sleep(0.5)
    
    assert len(received) > 0
    tools = received[0]['tools']
    assert len(tools) >= 4
    print(f"✅ Got {len(tools)} tools")

def test_vetka_search(sio):
    """Test vetka_search tool"""
    received = []
    
    @sio.on('tool_result', namespace='/mcp')
    def on_result(data):
        received.append(data)
    
    sio.emit('tool_call', {
        'id': 'test-1',
        'name': 'vetka_search',
        'arguments': {'query': 'main', 'limit': 5}
    }, namespace='/mcp')
    time.sleep(1)
    
    assert len(received) > 0
    result = received[0]
    assert 'result' in result or 'error' in result
    print(f"✅ vetka_search: {result}")

def test_vetka_get_tree(sio):
    """Test vetka_get_tree tool"""
    received = []
    
    @sio.on('tool_result', namespace='/mcp')
    def on_result(data):
        received.append(data)
    
    sio.emit('tool_call', {
        'id': 'test-2',
        'name': 'vetka_get_tree',
        'arguments': {'path': 'src', 'depth': 2}
    }, namespace='/mcp')
    time.sleep(0.5)
    
    assert len(received) > 0
    result = received[0]
    assert result.get('result', {}).get('success', False)
    print(f"✅ vetka_get_tree works")

def test_vetka_read_file(sio):
    """Test vetka_read_file tool"""
    received = []
    
    @sio.on('tool_result', namespace='/mcp')
    def on_result(data):
        received.append(data)
    
    sio.emit('tool_call', {
        'id': 'test-3',
        'name': 'vetka_read_file',
        'arguments': {'path': 'main.py', 'max_lines': 50}
    }, namespace='/mcp')
    time.sleep(0.5)
    
    assert len(received) > 0
    result = received[0]['result']
    assert result.get('success')
    assert 'content' in result.get('result', {})
    print(f"✅ vetka_read_file works")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

## 📋 ШАГ 3: ПРОВЕРКА

После всех изменений:
```bash
# Запусти сервер
python main.py

# В другом терминале - тест API
curl http://localhost:5001/api/mcp/status

# Тесты (если установлен python-socketio[client])
pip install python-socketio[client] pytest
pytest tests/test_mcp_server.py -v
```

## 📋 ШАГ 4: ОТЧЁТ

Создай docs/22_paralell/MCP_IMPLEMENTATION_REPORT.md:
```markdown
# MCP Implementation Report

## Files Created/Modified
- src/mcp/tools/*.py - 6 tool files
- src/mcp/mcp_server.py - updated
- main.py - added /mcp namespace
- tests/test_mcp_server.py - created

## Tools Implemented
1. vetka_search - semantic search
2. vetka_get_tree - tree structure
3. vetka_get_node - node details
4. vetka_create_branch - folder creation
5. vetka_list_files - file listing
6. vetka_read_file - file reading

## Test Results
[paste test output]

## Git Commit
git add src/mcp/ tests/test_mcp_server.py main.py
git commit -m "feat: MCP Server integration Phase 22

- Add 6 MCP tools (search, tree, node, branch, list, read)
- Register /mcp Socket.IO namespace
- Add REST endpoint /api/mcp/status
- Add pytest tests for MCP"
```

## ⚠️ ВАЖНО

1. **НЕ ломай существующий код** - MCP это НОВЫЙ namespace
2. **Используй существующие сервисы** - MemoryManager, file routes
3. **PROJECT_ROOT** - проверь путь `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03`
4. **Тестируй каждый tool** отдельно перед коммитом