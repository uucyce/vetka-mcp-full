# VETKA BUGFIX: Artifact Panel File Loading

## 🔴 КРИТИЧЕСКИЙ БАГ
Artifact Panel не загружает файлы от агентов. Панель показывает "Failed to load".

## 📋 ЦЕПОЧКА ОШИБКИ

```
Agent создаёт artifact content
  ↓
Main page создаёт путь: /artifact/QA_1767070876452.md
  ↓
React Panel получает PostMessage с path
  ↓
React Panel вызывает: POST /api/files/read { path: "/artifact/..." }
  ↓
❌ BACKEND: 404 NOT FOUND
  ↓
React Panel: "Failed to load" error
```

## 📋 ШАГ 1: ДИАГНОСТИКА

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Проверить существует ли endpoint
grep -n "api/files/read" main.py src/**/*.py

# Проверить существует ли директория artifacts
ls -la data/artifacts/ 2>/dev/null || echo "Directory NOT FOUND"

# Проверить routes в main.py
grep -n "@app.route.*files" main.py

# Проверить React Panel код
grep -n "api/files/read" app/artifact-panel/src/**/*.tsx app/artifact-panel/src/**/*.ts
```

## 📋 ШАГ 2: СОЗДАТЬ ENDPOINT /api/files/read

Добавить в `main.py`:

```python
@app.route('/api/files/read', methods=['POST'])
def api_files_read():
    """Read file content for artifact panel"""
    from pathlib import Path
    import os
    
    data = request.json or {}
    file_path = data.get('path', '')
    
    if not file_path:
        return jsonify({"success": False, "error": "path is required"}), 400
    
    # Security: sanitize path
    file_path = file_path.replace('..', '').lstrip('/')
    
    # Map artifact paths to actual files
    if file_path.startswith('artifact/'):
        # Artifact files are stored in data/artifacts/
        actual_path = Path('data/artifacts') / file_path.replace('artifact/', '')
    else:
        # Regular project files
        actual_path = Path(file_path)
    
    # Security: ensure path is within project
    try:
        actual_path = actual_path.resolve()
        project_root = Path('.').resolve()
        if not str(actual_path).startswith(str(project_root)):
            return jsonify({"success": False, "error": "Access denied"}), 403
    except Exception:
        return jsonify({"success": False, "error": "Invalid path"}), 400
    
    if not actual_path.exists():
        return jsonify({"success": False, "error": f"File not found: {file_path}"}), 404
    
    try:
        content = actual_path.read_text(encoding='utf-8')
        return jsonify({
            "success": True,
            "content": content,
            "path": file_path,
            "encoding": "utf-8",
            "size": len(content)
        })
    except UnicodeDecodeError:
        # Binary file
        import base64
        content = base64.b64encode(actual_path.read_bytes()).decode('ascii')
        return jsonify({
            "success": True,
            "content": content,
            "path": file_path,
            "encoding": "base64",
            "size": actual_path.stat().st_size
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

## 📋 ШАГ 3: СОЗДАТЬ ENDPOINT ДЛЯ СОХРАНЕНИЯ ARTIFACTS

Добавить в `main.py`:

```python
@app.route('/api/artifact/save', methods=['POST'])
def api_artifact_save():
    """Save artifact content from agent"""
    from pathlib import Path
    import time
    import uuid
    
    data = request.json or {}
    content = data.get('content', '')
    artifact_type = data.get('type', 'artifact')  # QA, Dev, PM, etc.
    filename = data.get('filename')  # Optional custom filename
    
    if not content:
        return jsonify({"success": False, "error": "content is required"}), 400
    
    # Create artifacts directory
    artifacts_dir = Path('data/artifacts')
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        timestamp = int(time.time() * 1000)
        short_id = str(uuid.uuid4())[:8]
        filename = f"{artifact_type}_{timestamp}_{short_id}.md"
    
    # Ensure .md extension
    if not filename.endswith('.md'):
        filename += '.md'
    
    # Save file
    file_path = artifacts_dir / filename
    file_path.write_text(content, encoding='utf-8')
    
    # Return path for artifact panel
    return jsonify({
        "success": True,
        "path": f"/artifact/{filename}",
        "filename": filename,
        "size": len(content)
    })


@app.route('/api/artifact/list', methods=['GET'])
def api_artifact_list():
    """List saved artifacts"""
    from pathlib import Path
    
    artifacts_dir = Path('data/artifacts')
    if not artifacts_dir.exists():
        return jsonify({"success": True, "artifacts": [], "count": 0})
    
    artifacts = []
    for f in sorted(artifacts_dir.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True):
        artifacts.append({
            "filename": f.name,
            "path": f"/artifact/{f.name}",
            "size": f.stat().st_size,
            "modified": f.stat().st_mtime
        })
    
    return jsonify({
        "success": True,
        "artifacts": artifacts[:50],  # Last 50
        "count": len(artifacts)
    })


@app.route('/api/artifact/<filename>', methods=['GET'])
def api_artifact_get(filename):
    """Get specific artifact content"""
    from pathlib import Path
    
    # Security: sanitize filename
    filename = filename.replace('..', '').replace('/', '')
    
    artifacts_dir = Path('data/artifacts')
    file_path = artifacts_dir / filename
    
    if not file_path.exists():
        return jsonify({"success": False, "error": "Artifact not found"}), 404
    
    try:
        content = file_path.read_text(encoding='utf-8')
        return jsonify({
            "success": True,
            "content": content,
            "filename": filename,
            "size": len(content)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/artifact/<filename>', methods=['DELETE'])
def api_artifact_delete(filename):
    """Delete artifact"""
    from pathlib import Path
    
    # Security: sanitize filename
    filename = filename.replace('..', '').replace('/', '')
    
    artifacts_dir = Path('data/artifacts')
    file_path = artifacts_dir / filename
    
    if not file_path.exists():
        return jsonify({"success": False, "error": "Artifact not found"}), 404
    
    file_path.unlink()
    return jsonify({"success": True, "deleted": filename})
```

## 📋 ШАГ 4: СОЗДАТЬ ДИРЕКТОРИЮ ARTIFACTS

```bash
mkdir -p data/artifacts
echo "# Artifacts Directory" > data/artifacts/.gitkeep
```

## 📋 ШАГ 5: ПРОВЕРИТЬ REACT PANEL КОД

В файле `app/artifact-panel/src/App.tsx` или аналогичном, убедиться что:

```typescript
// Функция загрузки файла
const loadFile = async (path: string) => {
  console.log('[ArtifactPanel] Loading file:', path);
  
  try {
    const response = await fetch('http://localhost:5001/api/files/read', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    
    console.log('[ArtifactPanel] Response status:', response.status);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Unknown error');
    }
    
    return data.content;
  } catch (error) {
    console.error('[ArtifactPanel] Load error:', error);
    throw error;
  }
};
```

## 📋 ШАГ 6: ИСПРАВИТЬ RACE CONDITION (iframe ready)

В `templates/3d.html` или где инициализируется iframe:

```javascript
// Добавить ожидание ready состояния
let iframeReady = false;
const pendingMessages = [];

// Обработчик ready от iframe
window.addEventListener('message', (event) => {
  if (event.data?.type === 'READY') {
    console.log('[ARTIFACT] iframe marked ready');
    iframeReady = true;
    
    // Отправить все ожидающие сообщения
    while (pendingMessages.length > 0) {
      const msg = pendingMessages.shift();
      sendToIframeInternal(msg);
    }
  }
});

// Функция отправки с буферизацией
function sendToIframe(message) {
  if (iframeReady) {
    sendToIframeInternal(message);
  } else {
    console.log('[ARTIFACT] Buffering message until iframe ready');
    pendingMessages.push(message);
  }
}

function sendToIframeInternal(message) {
  const iframe = document.getElementById('artifact-iframe');
  if (iframe && iframe.contentWindow) {
    iframe.contentWindow.postMessage(message, '*');
    console.log('[ARTIFACT] Message sent:', message.type);
  }
}
```

## 📋 ШАГ 7: ТЕСТИРОВАНИЕ CURL

```bash
# 1. Перезапустить сервер
python main.py

# 2. Проверить endpoint существует
curl -X POST http://localhost:5001/api/files/read \
  -H "Content-Type: application/json" \
  -d '{"path": "README.md"}'

# 3. Создать тестовый artifact
curl -X POST http://localhost:5001/api/artifact/save \
  -H "Content-Type: application/json" \
  -d '{"content": "# Test Artifact\n\nThis is a test.", "type": "QA"}'

# 4. Проверить список artifacts
curl http://localhost:5001/api/artifact/list

# 5. Прочитать artifact через /api/files/read
curl -X POST http://localhost:5001/api/files/read \
  -H "Content-Type: application/json" \
  -d '{"path": "/artifact/QA_xxx.md"}'  # Use actual filename from step 3
```

## 📋 ШАГ 8: BROWSER DEBUG TESTS (от Haiku)

После перезапуска сервера, выполнить в browser console (F12 → Console):

```javascript
// Test 1: Does the endpoint exist?
fetch('http://localhost:5001/api/files/read', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ path: 'README.md' })
}).then(r => r.json()).then(d => console.log('Test 1 - files/read:', d));

// Test 2: Create test artifact
fetch('http://localhost:5001/api/artifact/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ content: '# Test\nHello from test', type: 'QA' })
}).then(r => r.json()).then(d => console.log('Test 2 - artifact save:', d));

// Test 3: List artifacts
fetch('http://localhost:5001/api/artifact/list')
  .then(r => r.json())
  .then(d => console.log('Test 3 - artifact list:', d));

// Test 4: Read artifact via files/read (use filename from Test 2)
fetch('http://localhost:5001/api/files/read', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ path: '/artifact/QA_test.md' })  // Replace with actual filename
}).then(r => r.json()).then(d => console.log('Test 4 - read artifact:', d));
```

**Expected Results:**
- Test 1: `{ success: true, content: "...", path: "README.md" }`
- Test 2: `{ success: true, path: "/artifact/QA_xxx.md", filename: "..." }`
- Test 3: `{ success: true, artifacts: [...], count: N }`
- Test 4: `{ success: true, content: "# Test\nHello from test" }`

## ✅ КРИТЕРИИ УСПЕХА

- [ ] `POST /api/files/read` возвращает 200 и content
- [ ] `POST /api/artifact/save` создаёт файл в data/artifacts/
- [ ] `GET /api/artifact/list` возвращает список
- [ ] `GET /api/artifact/<filename>` возвращает content
- [ ] Директория data/artifacts/ существует
- [ ] React Panel загружает файлы без ошибок
- [ ] Нет race condition (iframe ready)
- [ ] Browser debug tests все проходят

## 📁 ИЗМЕНЕНИЯ

```
main.py:
  + POST /api/files/read
  + POST /api/artifact/save
  + GET /api/artifact/list
  + GET /api/artifact/<filename>
  + DELETE /api/artifact/<filename>

data/artifacts/  (NEW DIRECTORY)
  + .gitkeep

templates/3d.html (или где iframe):
  + iframe ready buffering logic
```

## 🔄 ПОСЛЕ ЗАВЕРШЕНИЯ

1. Перезапустить сервер
2. Выполнить browser debug tests (Шаг 8)
3. Открыть http://localhost:5001/3d
4. В чате написать @qa или @dev с задачей
5. Убедиться что artifact отображается в панели
6. Сообщить результат!
