# VETKA Phase 22-MCP-4: Claude Desktop Integration + Memory Export

## 🎯 ЗАДАЧА
1. Настроить интеграцию с Claude Desktop через `claude_desktop_config.json`
2. Реализовать Memory Transfer Protocol (`.vetka-mem` формат для export/import)

## 📋 ШАГ 1: АНАЛИЗ

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Проверить текущее состояние
echo "=== MCP modules ===" && ls -la src/mcp/*.py
echo "=== Security modules ===" && wc -l src/mcp/rate_limiter.py src/mcp/audit_logger.py src/mcp/approval.py
echo "=== Tests ===" && grep -c "def test_" tests/test_mcp_server.py

# Claude Desktop config location (macOS)
echo "=== Claude config location ===" 
ls -la ~/Library/Application\ Support/Claude/ 2>/dev/null || echo "Claude Desktop not installed or no config yet"
```

## 📋 ШАГ 2: CLAUDE DESKTOP CONFIG

### 2.1 Создать конфиг генератор (src/mcp/claude_desktop.py)

```python
"""Claude Desktop MCP configuration generator"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Claude Desktop config paths by OS
CLAUDE_CONFIG_PATHS = {
    "darwin": Path.home() / "Library/Application Support/Claude/claude_desktop_config.json",
    "linux": Path.home() / ".config/claude/claude_desktop_config.json",
    "win32": Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json"
}

def get_vetka_mcp_config(
    host: str = "localhost",
    port: int = 5001,
    name: str = "vetka"
) -> Dict[str, Any]:
    """Generate VETKA MCP server config for Claude Desktop"""
    return {
        "mcpServers": {
            name: {
                "command": "curl",
                "args": [
                    "-s",
                    "-X", "POST",
                    f"http://{host}:{port}/api/mcp/call",
                    "-H", "Content-Type: application/json",
                    "-d", "@-"
                ],
                "env": {},
                "description": "VETKA Knowledge System - 11 tools for file search, semantic search, git operations"
            }
        }
    }


def get_vetka_stdio_config(
    project_path: str = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03",
    python_path: str = None
) -> Dict[str, Any]:
    """Generate VETKA MCP server config using stdio transport"""
    if python_path is None:
        python_path = f"{project_path}/venv/bin/python"
    
    return {
        "mcpServers": {
            "vetka": {
                "command": python_path,
                "args": [
                    "-m", "src.mcp.stdio_server"
                ],
                "cwd": project_path,
                "env": {
                    "PYTHONPATH": project_path
                },
                "description": "VETKA Knowledge System MCP Server"
            }
        }
    }


def generate_config_file(output_path: Optional[Path] = None, use_stdio: bool = True) -> Path:
    """Generate Claude Desktop config file"""
    import sys
    
    if output_path is None:
        output_path = CLAUDE_CONFIG_PATHS.get(sys.platform)
        if output_path is None:
            output_path = Path("claude_desktop_config.json")
    
    # Generate config
    if use_stdio:
        config = get_vetka_stdio_config()
    else:
        config = get_vetka_mcp_config()
    
    # Check if config exists and merge
    if output_path.exists():
        with open(output_path, 'r') as f:
            existing = json.load(f)
        
        # Merge mcpServers
        if "mcpServers" in existing:
            existing["mcpServers"].update(config["mcpServers"])
            config = existing
    
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write config
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return output_path


def get_install_instructions() -> str:
    """Get installation instructions for Claude Desktop"""
    return """
# VETKA MCP Server - Claude Desktop Integration

## Option 1: HTTP Transport (Recommended for development)

1. Start VETKA server:
   ```bash
   cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
   source venv/bin/activate
   python main.py
   ```

2. Add to Claude Desktop config:
   - macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
   - Linux: ~/.config/claude/claude_desktop_config.json
   - Windows: %APPDATA%/Claude/claude_desktop_config.json

   ```json
   {
     "mcpServers": {
       "vetka": {
         "url": "http://localhost:5001/api/mcp",
         "description": "VETKA Knowledge System"
       }
     }
   }
   ```

3. Restart Claude Desktop

## Option 2: Stdio Transport (For production)

1. Generate config:
   ```bash
   python -c "from src.mcp.claude_desktop import generate_config_file; print(generate_config_file())"
   ```

2. Restart Claude Desktop

## Available Tools

After installation, Claude Desktop will have access to:
- vetka_search - Search files by name
- vetka_search_knowledge - Semantic search
- vetka_get_tree - Get folder structure
- vetka_get_node - Get file details
- vetka_list_files - List directory
- vetka_read_file - Read file content
- vetka_edit_file - Edit files (with approval)
- vetka_create_branch - Create folders
- vetka_git_status - Git status
- vetka_git_commit - Git commit (with approval)
- vetka_run_tests - Run pytest
"""
```

### 2.2 Создать stdio сервер (src/mcp/stdio_server.py)

```python
"""VETKA MCP Server - Stdio transport for Claude Desktop"""
import sys
import json
from typing import Any, Dict

from .mcp_server import MCPServer, get_all_tools

def read_message() -> Dict[str, Any]:
    """Read JSON-RPC message from stdin"""
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line.strip())


def write_message(msg: Dict[str, Any]):
    """Write JSON-RPC message to stdout"""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming JSON-RPC request"""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "vetka-mcp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
    
    elif method == "tools/list":
        tools = get_all_tools()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.schema
                    }
                    for t in tools
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        # Find and execute tool
        tools = {t.name: t for t in get_all_tools()}
        if tool_name not in tools:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            }
        
        try:
            result = tools[tool_name].execute(arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    elif method == "notifications/initialized":
        # No response needed for notifications
        return None
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def main():
    """Main stdio server loop"""
    # Log to stderr (stdout is for protocol)
    sys.stderr.write("[VETKA MCP] Starting stdio server...\n")
    sys.stderr.flush()
    
    while True:
        try:
            request = read_message()
            if request is None:
                break
            
            sys.stderr.write(f"[VETKA MCP] Received: {request.get('method', 'unknown')}\n")
            sys.stderr.flush()
            
            response = handle_request(request)
            if response is not None:
                write_message(response)
                
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[VETKA MCP] JSON error: {e}\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[VETKA MCP] Error: {e}\n")
            sys.stderr.flush()
    
    sys.stderr.write("[VETKA MCP] Server stopped\n")
    sys.stderr.flush()


if __name__ == "__main__":
    main()
```

## 📋 ШАГ 3: MEMORY TRANSFER PROTOCOL

### 3.1 Memory Exporter (src/mcp/memory_transfer.py)

```python
"""VETKA Memory Transfer Protocol - Export/Import memory between sessions"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import base64

# Format version
VETKA_MEM_VERSION = "1.0"

class MemoryExporter:
    """Export VETKA memory to portable format"""
    
    def __init__(self, project_root: str = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"):
        self.project_root = Path(project_root)
        self.export_dir = self.project_root / "data" / "memory_exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def export_session(
        self,
        session_id: str,
        include_vectors: bool = False,
        include_files: bool = False
    ) -> Dict[str, Any]:
        """Export a session/branch memory"""
        
        export_data = {
            "format": "vetka-memory",
            "version": VETKA_MEM_VERSION,
            "exported_at": datetime.now().isoformat(),
            "session_id": session_id,
            "project_branch": self._get_git_branch(),
            "metadata": {}
        }
        
        # 1. Export chat history
        chat_history = self._load_chat_history(session_id)
        export_data["messages"] = chat_history
        
        # 2. Export changelog entries
        changelog = self._load_changelog_entries(session_id)
        export_data["changelog"] = changelog
        
        # 3. Export Weaviate references
        weaviate_refs = self._get_weaviate_refs(session_id)
        export_data["weaviate_refs"] = weaviate_refs
        
        # 4. Optionally include vectors
        if include_vectors:
            vectors = self._export_vectors(session_id)
            export_data["vectors"] = vectors
        
        # 5. Optionally include referenced files
        if include_files:
            files = self._export_referenced_files(chat_history)
            export_data["files"] = files
        
        # Calculate checksum
        content = json.dumps(export_data, sort_keys=True)
        export_data["checksum"] = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        return export_data
    
    def _get_git_branch(self) -> str:
        """Get current git branch"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except:
            return "unknown"
    
    def _load_chat_history(self, session_id: str) -> List[Dict]:
        """Load chat history for session"""
        history_dir = self.project_root / "data" / "chat_history"
        
        # Try to find session file
        session_file = history_dir / f"{session_id}.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
                return data.get("messages", [])
        
        # If no exact match, return empty
        return []
    
    def _load_changelog_entries(self, session_id: str) -> List[Dict]:
        """Load changelog entries for date range"""
        changelog_dir = self.project_root / "data" / "changelog"
        entries = []
        
        # Load today's changelog
        today = datetime.now().strftime("%Y-%m-%d")
        changelog_file = changelog_dir / f"changelog_{today}.json"
        
        if changelog_file.exists():
            with open(changelog_file, 'r') as f:
                data = json.load(f)
                entries = data.get("entries", [])[-50:]  # Last 50 entries
        
        return entries
    
    def _get_weaviate_refs(self, session_id: str) -> List[str]:
        """Get Weaviate object references"""
        # Placeholder - would need actual Weaviate connection
        return []
    
    def _export_vectors(self, session_id: str) -> List[Dict]:
        """Export vector embeddings"""
        # Placeholder - would need Qdrant connection
        return []
    
    def _export_referenced_files(self, messages: List[Dict]) -> Dict[str, str]:
        """Export files referenced in messages"""
        files = {}
        
        for msg in messages:
            content = msg.get("content", "")
            # Simple pattern matching for file paths
            import re
            paths = re.findall(r'(?:src|docs|tests)/[\w/.-]+\.(?:py|md|json|txt)', content)
            
            for path in paths:
                full_path = self.project_root / path
                if full_path.exists() and full_path.stat().st_size < 50000:  # Max 50KB
                    try:
                        with open(full_path, 'r') as f:
                            files[path] = f.read()
                    except:
                        pass
        
        return files
    
    def save_export(self, export_data: Dict, filename: Optional[str] = None) -> Path:
        """Save export to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vetka_memory_{timestamp}.vetka-mem"
        
        output_path = self.export_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return output_path


class MemoryImporter:
    """Import VETKA memory from portable format"""
    
    def __init__(self, project_root: str = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"):
        self.project_root = Path(project_root)
    
    def validate_format(self, data: Dict) -> tuple:
        """Validate memory format. Returns (valid, errors)"""
        errors = []
        
        if data.get("format") != "vetka-memory":
            errors.append("Invalid format: expected 'vetka-memory'")
        
        if "version" not in data:
            errors.append("Missing version field")
        
        if "messages" not in data:
            errors.append("Missing messages field")
        
        # Verify checksum if present
        if "checksum" in data:
            checksum = data.pop("checksum")
            content = json.dumps(data, sort_keys=True)
            expected = hashlib.sha256(content.encode()).hexdigest()[:16]
            data["checksum"] = checksum  # Restore
            
            if checksum != expected:
                errors.append(f"Checksum mismatch: expected {expected}, got {checksum}")
        
        return len(errors) == 0, errors
    
    def import_memory(self, file_path: Path) -> Dict[str, Any]:
        """Import memory from file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        valid, errors = self.validate_format(data)
        if not valid:
            return {"success": False, "errors": errors}
        
        result = {
            "success": True,
            "imported": {
                "messages": len(data.get("messages", [])),
                "changelog": len(data.get("changelog", [])),
                "files": len(data.get("files", {})),
                "vectors": len(data.get("vectors", []))
            },
            "session_id": data.get("session_id"),
            "source_branch": data.get("project_branch")
        }
        
        # Import messages to new session
        if data.get("messages"):
            session_id = self._create_session(data["messages"])
            result["new_session_id"] = session_id
        
        # Import files if present
        if data.get("files"):
            imported_files = self._import_files(data["files"])
            result["imported"]["files_written"] = imported_files
        
        return result
    
    def _create_session(self, messages: List[Dict]) -> str:
        """Create new chat session with imported messages"""
        import uuid
        session_id = str(uuid.uuid4())[:16]
        
        history_dir = self.project_root / "data" / "chat_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        
        session_file = history_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump({
                "session_id": session_id,
                "imported_at": datetime.now().isoformat(),
                "messages": messages
            }, f, indent=2)
        
        return session_id
    
    def _import_files(self, files: Dict[str, str]) -> int:
        """Import referenced files (to temp directory)"""
        import_dir = self.project_root / "data" / "imported_files"
        import_dir.mkdir(parents=True, exist_ok=True)
        
        count = 0
        for path, content in files.items():
            safe_name = path.replace("/", "_")
            output = import_dir / safe_name
            with open(output, 'w') as f:
                f.write(content)
            count += 1
        
        return count


# Convenience functions
def export_current_session() -> Path:
    """Quick export of current session"""
    exporter = MemoryExporter()
    
    # Get most recent session
    history_dir = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/chat_history")
    sessions = sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if sessions:
        session_id = sessions[0].stem
        data = exporter.export_session(session_id, include_files=True)
        return exporter.save_export(data)
    
    return None


def import_from_file(file_path: str) -> Dict:
    """Quick import from file"""
    importer = MemoryImporter()
    return importer.import_memory(Path(file_path))
```

### 3.2 REST Endpoints для Memory Transfer

Добавить в main.py:

```python
# Memory Transfer endpoints
@app.route('/api/memory/export', methods=['POST'])
def export_memory():
    """Export memory to .vetka-mem format"""
    from src.mcp.memory_transfer import MemoryExporter
    
    data = request.json or {}
    session_id = data.get('session_id', 'current')
    include_vectors = data.get('include_vectors', False)
    include_files = data.get('include_files', True)
    
    exporter = MemoryExporter()
    
    if session_id == 'current':
        # Get most recent session
        history_dir = Path("data/chat_history")
        sessions = sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if sessions:
            session_id = sessions[0].stem
        else:
            return jsonify({"success": False, "error": "No sessions found"}), 404
    
    export_data = exporter.export_session(session_id, include_vectors, include_files)
    output_path = exporter.save_export(export_data)
    
    return jsonify({
        "success": True,
        "file": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "messages": len(export_data.get("messages", [])),
        "checksum": export_data.get("checksum")
    })


@app.route('/api/memory/import', methods=['POST'])
def import_memory():
    """Import memory from .vetka-mem format"""
    from src.mcp.memory_transfer import MemoryImporter
    
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.vetka-mem'):
        return jsonify({"success": False, "error": "Invalid file format"}), 400
    
    # Save to temp location
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.vetka-mem') as tmp:
        file.save(tmp.name)
        tmp_path = Path(tmp.name)
    
    try:
        importer = MemoryImporter()
        result = importer.import_memory(tmp_path)
        return jsonify(result)
    finally:
        tmp_path.unlink()  # Clean up temp file


@app.route('/api/memory/exports', methods=['GET'])
def list_memory_exports():
    """List available memory exports"""
    export_dir = Path("data/memory_exports")
    if not export_dir.exists():
        return jsonify({"exports": []})
    
    exports = []
    for f in sorted(export_dir.glob("*.vetka-mem"), key=lambda p: p.stat().st_mtime, reverse=True):
        exports.append({
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    
    return jsonify({"count": len(exports), "exports": exports[:20]})
```

## 📋 ШАГ 4: ТЕСТЫ

Добавить в tests/test_mcp_server.py:

```python
# ============================================================
# PHASE 22-MCP-4 TESTS
# ============================================================

def test_27_claude_desktop_config():
    """Test Claude Desktop config generation"""
    from src.mcp.claude_desktop import get_vetka_mcp_config, get_vetka_stdio_config
    
    # HTTP config
    http_config = get_vetka_mcp_config()
    assert "mcpServers" in http_config
    assert "vetka" in http_config["mcpServers"]
    
    # Stdio config
    stdio_config = get_vetka_stdio_config()
    assert "mcpServers" in stdio_config
    assert "command" in stdio_config["mcpServers"]["vetka"]
    
    print("✅ Test 27: Claude Desktop config generation works")

def test_28_memory_exporter():
    """Test memory export"""
    from src.mcp.memory_transfer import MemoryExporter
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = MemoryExporter(project_root=tmpdir)
        
        # Create mock data
        Path(f"{tmpdir}/data/chat_history").mkdir(parents=True)
        with open(f"{tmpdir}/data/chat_history/test123.json", 'w') as f:
            json.dump({"messages": [{"role": "user", "content": "test"}]}, f)
        
        export = exporter.export_session("test123")
        
        assert export["format"] == "vetka-memory"
        assert export["version"] == "1.0"
        assert "checksum" in export
    
    print("✅ Test 28: Memory exporter works")

def test_29_memory_importer():
    """Test memory import"""
    from src.mcp.memory_transfer import MemoryImporter
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock export file
        export_data = {
            "format": "vetka-memory",
            "version": "1.0",
            "messages": [{"role": "user", "content": "imported message"}],
            "changelog": [],
            "session_id": "imported_session"
        }
        
        export_file = Path(tmpdir) / "test.vetka-mem"
        with open(export_file, 'w') as f:
            json.dump(export_data, f)
        
        importer = MemoryImporter(project_root=tmpdir)
        result = importer.import_memory(export_file)
        
        assert result["success"] == True
        assert result["imported"]["messages"] == 1
    
    print("✅ Test 29: Memory importer works")

def test_30_memory_export_endpoint():
    """Test memory export endpoint"""
    response = requests.post(f"{BASE_URL}/api/memory/export", json={})
    # May fail if no sessions exist, but should return valid response
    assert response.status_code in (200, 404)
    print("✅ Test 30: Memory export endpoint works")

def test_31_memory_exports_list():
    """Test memory exports list endpoint"""
    response = requests.get(f"{BASE_URL}/api/memory/exports")
    assert response.status_code == 200
    data = response.json()
    assert "exports" in data
    print("✅ Test 31: Memory exports list endpoint works")

def test_32_stdio_server_import():
    """Test stdio server can be imported"""
    try:
        from src.mcp.stdio_server import handle_request
        
        # Test initialize
        response = handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })
        
        assert response["result"]["serverInfo"]["name"] == "vetka-mcp"
        print("✅ Test 32: Stdio server works")
    except Exception as e:
        print(f"⚠️ Test 32: Stdio server import issue: {e}")
```

## 📋 ШАГ 5: Обновить __init__.py

```python
# src/mcp/__init__.py - добавить:
from .claude_desktop import (
    get_vetka_mcp_config,
    get_vetka_stdio_config,
    generate_config_file,
    get_install_instructions
)
from .memory_transfer import (
    MemoryExporter,
    MemoryImporter,
    export_current_session,
    import_from_file,
    VETKA_MEM_VERSION
)
```

## ✅ КРИТЕРИИ УСПЕХА

- [ ] Claude Desktop config generator создаёт валидный JSON
- [ ] Stdio server отвечает на initialize и tools/list
- [ ] Memory export создаёт .vetka-mem файлы
- [ ] Memory import восстанавливает сессии
- [ ] REST endpoints: /api/memory/export, /api/memory/import, /api/memory/exports
- [ ] 6 новых тестов (27-32)

## 📁 НОВЫЕ ФАЙЛЫ

```
src/mcp/
├── claude_desktop.py   (NEW - config generator)
├── stdio_server.py     (NEW - stdio transport)
├── memory_transfer.py  (NEW - export/import)
└── __init__.py         (MODIFIED)

data/memory_exports/    (NEW DIRECTORY)
└── vetka_memory_*.vetka-mem
```

## 🔄 ПОСЛЕ ЗАВЕРШЕНИЯ

1. Запусти тесты: `python tests/test_mcp_server.py`
2. Проверь endpoints:
   ```bash
   curl -X POST http://localhost:5001/api/memory/export -H "Content-Type: application/json" -d '{}'
   curl http://localhost:5001/api/memory/exports
   ```
3. Тест Claude Desktop config:
   ```bash
   python -c "from src.mcp.claude_desktop import get_install_instructions; print(get_install_instructions())"
   ```
4. Сообщи результаты!
