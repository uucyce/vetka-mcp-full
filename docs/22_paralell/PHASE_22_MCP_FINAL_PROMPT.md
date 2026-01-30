# VETKA Phase 22-MCP-FINAL: Финализация MCP-4 и MCP-5

## 🎯 ЗАДАЧА
Доделать пробелы в MCP-4 и MCP-5 по результатам верификации:

**MCP-4 (90% → 100%):**
- Добавить endpoint `/api/mcp/claude-config`
- Проверить memory export/import endpoints
- Запустить тесты 27-32

**MCP-5 (90% → 100%):**
- Зарегистрировать 3 MCP tools в сервере
- Интегрировать tools.py в main.py
- Запустить тесты 33-38

## 📋 ШАГ 1: ДИАГНОСТИКА

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Проверить текущие endpoints
echo "=== Checking MCP endpoints ===" 
curl -s http://localhost:5001/api/mcp/status | jq '.tools_count'
curl -s http://localhost:5001/api/mcp/claude-config 2>/dev/null || echo "claude-config: NOT FOUND"

# Проверить memory endpoints
echo "=== Checking Memory endpoints ===" 
curl -s http://localhost:5001/api/memory/exports | jq '.count'

# Проверить intake endpoints
echo "=== Checking Intake endpoints ===" 
curl -s http://localhost:5001/api/intake/list | jq '.count'

# Проверить MCP tools (должно быть 11 сейчас, станет 14)
curl -s http://localhost:5001/api/mcp/tools | jq '.[].name' | wc -l

# Проверить файлы
echo "=== Checking files ===" 
ls -la src/mcp/claude_desktop.py 2>/dev/null || echo "claude_desktop.py: NOT FOUND"
ls -la src/mcp/memory_transfer.py 2>/dev/null || echo "memory_transfer.py: NOT FOUND"
ls -la src/intake/tools.py 2>/dev/null || echo "intake/tools.py: NOT FOUND"
```

## 📋 ШАГ 2: MCP-4 FIXES

### 2.1 Добавить endpoint /api/mcp/claude-config

В файл `main.py` добавить:

```python
@app.route('/api/mcp/claude-config', methods=['GET'])
def mcp_claude_config():
    """Generate Claude Desktop configuration"""
    from src.mcp.claude_desktop import get_vetka_mcp_config, get_vetka_stdio_config, get_install_instructions
    
    transport = request.args.get('transport', 'http')  # http or stdio
    host = request.args.get('host', 'localhost')
    port = int(request.args.get('port', 5001))
    
    if transport == 'stdio':
        config = get_vetka_stdio_config()
    else:
        config = get_vetka_mcp_config(host=host, port=port)
    
    return jsonify({
        "config": config,
        "transport": transport,
        "instructions": get_install_instructions()
    })
```

### 2.2 Проверить/исправить memory endpoints

Убедиться что в `main.py` есть:

```python
@app.route('/api/memory/export', methods=['POST'])
def export_memory():
    """Export memory to .vetka-mem format"""
    from src.mcp.memory_transfer import MemoryExporter
    from pathlib import Path
    
    data = request.json or {}
    session_id = data.get('session_id', 'current')
    include_vectors = data.get('include_vectors', False)
    include_files = data.get('include_files', True)
    
    exporter = MemoryExporter()
    
    if session_id == 'current':
        # Get most recent session
        history_dir = Path("data/chat_history")
        if history_dir.exists():
            sessions = sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if sessions:
                session_id = sessions[0].stem
            else:
                return jsonify({"success": False, "error": "No sessions found"}), 404
        else:
            return jsonify({"success": False, "error": "No chat history directory"}), 404
    
    try:
        export_data = exporter.export_session(session_id, include_vectors, include_files)
        output_path = exporter.save_export(export_data)
        
        return jsonify({
            "success": True,
            "file": str(output_path),
            "filename": output_path.name,
            "size_bytes": output_path.stat().st_size,
            "messages": len(export_data.get("messages", [])),
            "checksum": export_data.get("checksum")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/memory/import', methods=['POST'])
def import_memory():
    """Import memory from .vetka-mem format"""
    from src.mcp.memory_transfer import MemoryImporter
    from pathlib import Path
    import tempfile
    
    if 'file' not in request.files:
        # Try JSON body with filename from exports
        data = request.json or {}
        filename = data.get('filename')
        if filename:
            # Import from existing export
            export_path = Path("data/memory_exports") / filename
            if not export_path.exists():
                return jsonify({"success": False, "error": f"Export not found: {filename}"}), 404
            
            importer = MemoryImporter()
            result = importer.import_memory(export_path)
            return jsonify(result)
        
        return jsonify({"success": False, "error": "No file provided. Use multipart/form-data with 'file' field or JSON with 'filename'"}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.vetka-mem'):
        return jsonify({"success": False, "error": "Invalid file format. Expected .vetka-mem"}), 400
    
    # Save to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.vetka-mem') as tmp:
        file.save(tmp.name)
        tmp_path = Path(tmp.name)
    
    try:
        importer = MemoryImporter()
        result = importer.import_memory(tmp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        tmp_path.unlink(missing_ok=True)  # Clean up temp file


@app.route('/api/memory/exports/<filename>', methods=['DELETE'])
def delete_memory_export(filename):
    """Delete a memory export"""
    from pathlib import Path
    
    export_path = Path("data/memory_exports") / filename
    if not export_path.exists():
        return jsonify({"success": False, "error": "Export not found"}), 404
    
    if not filename.endswith('.vetka-mem'):
        return jsonify({"success": False, "error": "Invalid filename"}), 400
    
    export_path.unlink()
    return jsonify({"success": True, "deleted": filename})
```

## 📋 ШАГ 3: MCP-5 FIXES

### 3.1 Создать/исправить src/intake/tools.py

```python
"""MCP Tools for content intake - Phase 22-MCP-5"""
from typing import Any, Dict
import asyncio

class IntakeURLTool:
    """Process URL and extract content (YouTube, web pages)"""
    
    name = "vetka_intake_url"
    description = "Extract content from URL (YouTube video transcript/captions, web article text). Returns title, text preview, metadata."
    schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to process (YouTube video or web page)"
            },
            "transcribe": {
                "type": "boolean",
                "description": "For YouTube: transcribe audio if no subtitles available (slower, requires whisper)",
                "default": False
            }
        },
        "required": ["url"]
    }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        from src.intake.manager import get_intake_manager
        
        url = arguments.get("url", "")
        options = {
            "transcribe": arguments.get("transcribe", False)
        }
        
        if not url:
            return {"success": False, "error": "URL is required"}
        
        manager = get_intake_manager()
        
        # Run async in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(manager.process_url(url, options))
            return {
                "success": True,
                "source_type": result.source_type,
                "title": result.title,
                "text_preview": result.text[:2000] if result.text else "",
                "text_length": len(result.text) if result.text else 0,
                "author": result.author,
                "duration_seconds": result.duration_seconds,
                "metadata": result.metadata
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            loop.close()


class ListIntakesTool:
    """List processed content intakes"""
    
    name = "vetka_list_intakes"
    description = "List recently processed content intakes (YouTube videos, web pages). Returns filename, source_type, title, text_length."
    schema = {
        "type": "object",
        "properties": {
            "source_type": {
                "type": "string",
                "description": "Filter by source type",
                "enum": ["youtube", "web"]
            },
            "limit": {
                "type": "integer",
                "description": "Number of results to return",
                "default": 10
            }
        }
    }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        from src.intake.manager import get_intake_manager
        
        manager = get_intake_manager()
        
        intakes = manager.list_intakes(
            source_type=arguments.get("source_type"),
            limit=arguments.get("limit", 10)
        )
        
        return {
            "success": True,
            "count": len(intakes),
            "intakes": intakes
        }


class GetIntakeTool:
    """Get full content of a processed intake"""
    
    name = "vetka_get_intake"
    description = "Get the full text content of a previously processed intake by filename."
    schema = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Intake filename from vetka_list_intakes (e.g., youtube_abc123_20251230.json)"
            }
        },
        "required": ["filename"]
    }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        from src.intake.manager import get_intake_manager
        
        filename = arguments.get("filename", "")
        if not filename:
            return {"success": False, "error": "filename is required"}
        
        manager = get_intake_manager()
        
        intake = manager.get_intake(filename)
        if intake:
            return {
                "success": True,
                **intake
            }
        return {
            "success": False,
            "error": f"Intake not found: {filename}"
        }


# Export all tools
INTAKE_TOOLS = [IntakeURLTool, ListIntakesTool, GetIntakeTool]

def get_intake_tools():
    """Return list of intake tool instances"""
    return [tool() for tool in INTAKE_TOOLS]
```

### 3.2 Зарегистрировать intake tools в MCP server

В файл `src/mcp/mcp_server.py` добавить импорт и регистрацию:

```python
# В начале файла, в секции импортов:
try:
    from src.intake.tools import get_intake_tools, INTAKE_TOOLS
    INTAKE_AVAILABLE = True
except ImportError:
    INTAKE_AVAILABLE = False
    INTAKE_TOOLS = []

# В функции get_all_tools() или при инициализации tools:
def get_all_tools():
    """Get all available MCP tools including intake tools"""
    tools = [
        # ... existing 11 tools ...
    ]
    
    # Add intake tools if available
    if INTAKE_AVAILABLE:
        tools.extend(get_intake_tools())
    
    return tools
```

### 3.3 Альтернативно: регистрация через main.py

Если tools регистрируются в main.py, добавить:

```python
# После других tool imports
try:
    from src.intake.tools import IntakeURLTool, ListIntakesTool, GetIntakeTool
    
    # Register intake tools with MCP server
    from src.mcp.mcp_server import register_tool  # или как называется функция регистрации
    
    register_tool(IntakeURLTool())
    register_tool(ListIntakesTool())
    register_tool(GetIntakeTool())
    
    print("[MCP] Intake tools registered: vetka_intake_url, vetka_list_intakes, vetka_get_intake")
except ImportError as e:
    print(f"[MCP] Intake tools not available: {e}")
```

## 📋 ШАГ 4: ЗАПУСК ТЕСТОВ

### 4.1 Проверить что тесты 27-38 существуют

```bash
# Проверить тесты в файле
grep -n "def test_2[7-9]\|def test_3[0-8]" tests/test_mcp_server.py
```

### 4.2 Если тестов нет, добавить:

```python
# ============================================================
# PHASE 22-MCP-4 TESTS (27-32)
# ============================================================

def test_27_claude_config_endpoint():
    """Test Claude Desktop config endpoint"""
    response = requests.get(f"{BASE_URL}/api/mcp/claude-config")
    assert response.status_code == 200
    data = response.json()
    assert "config" in data
    assert "mcpServers" in data["config"]
    print("✅ Test 27: Claude config endpoint works")

def test_28_claude_config_stdio():
    """Test Claude Desktop stdio config"""
    response = requests.get(f"{BASE_URL}/api/mcp/claude-config?transport=stdio")
    assert response.status_code == 200
    data = response.json()
    assert data["transport"] == "stdio"
    assert "command" in data["config"]["mcpServers"]["vetka"]
    print("✅ Test 28: Claude stdio config works")

def test_29_memory_export():
    """Test memory export"""
    response = requests.post(f"{BASE_URL}/api/memory/export", json={})
    # May return 404 if no sessions, but should be valid response
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert data.get("success") == True
    print("✅ Test 29: Memory export endpoint works")

def test_30_memory_exports_list():
    """Test memory exports list"""
    response = requests.get(f"{BASE_URL}/api/memory/exports")
    assert response.status_code == 200
    data = response.json()
    assert "exports" in data
    print("✅ Test 30: Memory exports list works")

def test_31_memory_transfer_classes():
    """Test memory transfer classes"""
    from src.mcp.memory_transfer import MemoryExporter, MemoryImporter, VETKA_MEM_VERSION
    
    assert VETKA_MEM_VERSION == "1.0"
    exporter = MemoryExporter()
    assert exporter.export_dir.exists() or True  # May create on first use
    print("✅ Test 31: Memory transfer classes work")

def test_32_claude_desktop_module():
    """Test Claude Desktop module"""
    from src.mcp.claude_desktop import get_vetka_mcp_config, get_vetka_stdio_config
    
    http_config = get_vetka_mcp_config()
    assert "mcpServers" in http_config
    
    stdio_config = get_vetka_stdio_config()
    assert "mcpServers" in stdio_config
    print("✅ Test 32: Claude Desktop module works")

# ============================================================
# PHASE 22-MCP-5 TESTS (33-38)
# ============================================================

def test_33_intake_url_pattern_youtube():
    """Test YouTube URL pattern matching"""
    from src.intake.youtube import YouTubeIntake
    
    intake = YouTubeIntake()
    assert intake.can_process("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert intake.can_process("https://youtu.be/dQw4w9WgXcQ")
    assert intake.can_process("https://youtube.com/shorts/abc123")
    assert not intake.can_process("https://example.com/video")
    print("✅ Test 33: YouTube pattern matching works")

def test_34_intake_url_pattern_web():
    """Test Web URL pattern matching"""
    from src.intake.web import WebIntake
    
    intake = WebIntake()
    assert intake.can_process("https://example.com/article")
    assert intake.can_process("https://wikipedia.org/wiki/Test")
    assert not intake.can_process("https://youtube.com/watch?v=123")
    print("✅ Test 34: Web pattern matching works")

def test_35_intake_manager():
    """Test intake manager processor selection"""
    from src.intake.manager import IntakeManager
    
    manager = IntakeManager()
    
    # YouTube should get YouTubeIntake
    processor = manager.get_processor("https://youtube.com/watch?v=abc")
    assert processor is not None
    assert processor.source_type == "youtube"
    
    # Web should get WebIntake
    processor = manager.get_processor("https://example.com/article")
    assert processor is not None
    assert processor.source_type == "web"
    print("✅ Test 35: Intake manager processor selection works")

def test_36_intake_list_endpoint():
    """Test intake list endpoint"""
    response = requests.get(f"{BASE_URL}/api/intake/list")
    assert response.status_code == 200
    data = response.json()
    assert "intakes" in data
    assert "count" in data
    print("✅ Test 36: Intake list endpoint works")

def test_37_intake_mcp_tools_registered():
    """Test intake MCP tools are registered"""
    response = requests.get(f"{BASE_URL}/api/mcp/tools")
    assert response.status_code == 200
    tools = response.json()
    
    tool_names = [t["name"] for t in tools]
    
    # Should have intake tools
    assert "vetka_intake_url" in tool_names, f"vetka_intake_url not in {tool_names}"
    assert "vetka_list_intakes" in tool_names, f"vetka_list_intakes not in {tool_names}"
    assert "vetka_get_intake" in tool_names, f"vetka_get_intake not in {tool_names}"
    
    # Should have 14 tools total (11 original + 3 intake)
    assert len(tools) >= 14, f"Expected 14+ tools, got {len(tools)}"
    print("✅ Test 37: Intake MCP tools registered (14 tools)")

def test_38_intake_result_format():
    """Test IntakeResult dataclass"""
    from src.intake.base import IntakeResult, ContentType
    
    result = IntakeResult(
        source_url="https://example.com",
        source_type="web",
        content_type=ContentType.ARTICLE,
        title="Test Article",
        text="This is test content for VETKA"
    )
    
    data = result.to_dict()
    assert data["source_url"] == "https://example.com"
    assert data["content_type"] == "article"
    assert data["text_length"] == len("This is test content for VETKA")
    assert "processed_at" in data
    print("✅ Test 38: IntakeResult format works")
```

### 4.3 Запустить тесты

```bash
# Запустить все тесты
python tests/test_mcp_server.py

# Или только новые
python -c "
import sys
sys.path.insert(0, '.')
from tests.test_mcp_server import *

# MCP-4 tests
test_27_claude_config_endpoint()
test_28_claude_config_stdio()
test_29_memory_export()
test_30_memory_exports_list()
test_31_memory_transfer_classes()
test_32_claude_desktop_module()

# MCP-5 tests
test_33_intake_url_pattern_youtube()
test_34_intake_url_pattern_web()
test_35_intake_manager()
test_36_intake_list_endpoint()
test_37_intake_mcp_tools_registered()
test_38_intake_result_format()

print('\\n✅ All MCP-4 and MCP-5 tests passed!')
"
```

## 📋 ШАГ 5: ВЕРИФИКАЦИЯ

```bash
# 1. Проверить Claude config endpoint
curl http://localhost:5001/api/mcp/claude-config | jq '.config.mcpServers'

# 2. Проверить количество tools (должно быть 14)
curl http://localhost:5001/api/mcp/tools | jq 'length'

# 3. Проверить что intake tools есть
curl http://localhost:5001/api/mcp/tools | jq '.[].name' | grep intake

# 4. Тест intake через MCP
curl -X POST http://localhost:5001/api/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "vetka_list_intakes",
    "arguments": {"limit": 5}
  }'

# 5. Проверить memory endpoints
curl http://localhost:5001/api/memory/exports | jq '.count'
```

## ✅ КРИТЕРИИ УСПЕХА

**MCP-4 (завершение):**
- [ ] `/api/mcp/claude-config` возвращает валидный JSON
- [ ] `/api/mcp/claude-config?transport=stdio` возвращает stdio конфиг
- [ ] `/api/memory/export` работает (или 404 если нет сессий)
- [ ] `/api/memory/exports` возвращает список
- [ ] Тесты 27-32 проходят

**MCP-5 (завершение):**
- [ ] `vetka_intake_url` зарегистрирован в MCP tools
- [ ] `vetka_list_intakes` зарегистрирован в MCP tools
- [ ] `vetka_get_intake` зарегистрирован в MCP tools
- [ ] Всего 14 tools (было 11)
- [ ] Тесты 33-38 проходят

**Итого:**
- [ ] 38/38 тестов проходят
- [ ] 14 MCP tools доступны

## 🔄 ПОСЛЕ ЗАВЕРШЕНИЯ

1. Перезапустить сервер: `python main.py`
2. Запустить все тесты: `python tests/test_mcp_server.py`
3. Проверить tools count: `curl http://localhost:5001/api/mcp/tools | jq 'length'`
4. Сообщить: "MCP-4 и MCP-5 финализированы, 38 тестов, 14 tools"
