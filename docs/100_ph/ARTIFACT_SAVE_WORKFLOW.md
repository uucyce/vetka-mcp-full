# VETKA Phase 100.7: Artifact Save-to-Disk Workflow

> **Source:** Grok Analysis (2026-01-29)
> **Status:** Implementation Ready
> **Priority:** Quick Win (1-2 days)

## Current State Analysis

### What Works (40-50% complete)
- **Extraction:** `artifact_extractor.py` (Phase 17-J) - fully functional
- **UI:** ArtifactPanel (522 lines) with tabs, viewers, toolbar
- **Tauri FS:** Native read/write/remove/list/watch ready (Phase 100.2)
- **Permissions:** Bash for git ops, file ops configured

### Gaps Identified
- `create_artifact` tool is **stub only** (tools.py:895,926)
- No persistence to Qdrant/Weaviate
- Team chat: No QA-approval hooks before save
- Offline: SQLite queue not started

## Implementation Plan

### Step 1: Core Save Function (~200 lines)

**File:** `src/agents/tools.py` (extend around line 895)

```python
def create_artifact(name: str, content: str, type_: str = 'code', language: str = 'python', agent: str = 'Dev') -> Dict:
    """
    Create artifact file and open in Artifact Panel.
    Supports Tauri-native or browser fallback.
    """
    import uuid
    from datetime import datetime
    from src.utils.artifact_extractor import extract_artifacts
    from src.memory.qdrant_client import upsert_artifact_to_qdrant

    artifact_id = str(uuid.uuid4())
    extension_map = {'python': '.py', 'javascript': '.js', 'typescript': '.ts', 'rust': '.rs'}
    ext = extension_map.get(language, f'.{language}')

    # Generate metadata
    metadata = {
        'id': artifact_id,
        'name': name,
        'type': type_,
        'language': language,
        'content': content,
        'created_at': datetime.now().isoformat(),
        'agent': agent,
        'lines': len(content.split('\n'))
    }

    # Save path (relative to project)
    filepath = f"artifacts/{artifact_id}_{name}{ext}"

    # Write to disk
    import os
    os.makedirs('artifacts', exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # Persist to Qdrant for semantic search
    upsert_artifact_to_qdrant(metadata)

    # Emit socket events
    from flask_socketio import emit
    emit('artifact_created', {
        'id': artifact_id,
        'name': name,
        'content': content[:500] + '...' if len(content) > 500 else content,
        'type': type_,
        'filepath': filepath
    }, broadcast=True)

    emit('open_artifact_panel', {
        'content': content,
        'title': name,
        'type': type_
    })

    return {
        'status': 'saved',
        'path': filepath,
        'id': artifact_id,
        'message': f"**Artifact Created:** {name} ({type_}, {len(content)} bytes)"
    }
```

### Step 2: Team Chat Integration (~150 lines)

**File:** `src/services/group_chat_manager.py` (around line 354)

```python
# Add after message routing logic
if message_type == 'artifact_proposed' and agent_role == 'dev':
    from src.utils.artifact_extractor import extract_qa_score

    qa_score = extract_qa_score(response_content)

    if qa_score and qa_score > 0.75:
        # Auto-save approved artifact
        result = create_artifact(
            name=artifact_name,
            content=artifact_content,
            agent='Dev'
        )

        # Notify group
        emit_to_group(group_id, 'artifact_approved', {
            'path': result['path'],
            'score': qa_score,
            'approved_by': 'QA (auto)'
        })

        # Camera fly-to new file
        socketio.emit('camera_focus', {
            'nodeId': get_node_by_path(result['path'])
        })
    else:
        # Request QA review
        emit_to_group(group_id, 'qa_review_needed', {
            'content': artifact_content,
            'score': qa_score,
            'retry_count': retry_count
        })
```

### Step 3: Frontend Socket Handlers

**File:** `client/src/components/artifact/ArtifactPanel.tsx`

```typescript
// Add to useEffect socket listeners
useEffect(() => {
  socket.on('artifact_created', (data) => {
    // Add to local history
    setArtifacts(prev => [...prev.slice(-9), { ...data, createdAt: new Date() }]);

    // Auto-open in viewer
    setCurrentArtifact(data);
    openViewer(data.type, data.content, data.name);
  });

  socket.on('artifact_approved', (data) => {
    // Show success notification
    showToast(`Artifact saved: ${data.path} (QA Score: ${data.score})`);
  });

  return () => {
    socket.off('artifact_created');
    socket.off('artifact_approved');
  };
}, [socket]);
```

### Step 4: Tauri-Specific Save (Phase 100.7)

**File:** `client/src/config/tauri.ts`

```typescript
/**
 * Save artifact via Tauri native FS (bypasses HTTP)
 * Phase 100.7: Direct disk write for desktop app
 */
export async function saveArtifactNative(
  filename: string,
  content: string,
  subfolder: string = 'artifacts'
): Promise<string | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;

  try {
    const path = `${subfolder}/${filename}`;
    return await invoke<string>('write_file_native', { path, content });
  } catch (e) {
    console.warn('Native artifact save failed:', e);
    return null;
  }
}
```

## Approval Flow (Multi-Level)

```
Level 1 (Auto):     Dev creates → auto-save as draft
Level 2 (QA):       QA reviews → extract_qa_score > 0.75 → approve
Level 3 (PM/User):  Final approval for production/commit
```

## Integration Points

| Component | File | Action |
|-----------|------|--------|
| Extraction | `artifact_extractor.py` | Parse agent response for code blocks |
| Formatting | `response_formatter.py:307` | Call create_artifact after extraction |
| Persistence | `qdrant_client.py` | Upsert metadata for search |
| UI | `ArtifactPanel.tsx` | Socket listeners + viewers |
| Tauri | `tauri.ts` | Native FS fallback |
| Team Chat | `group_chat_manager.py` | QA approval hooks |

## Testing Checklist

- [ ] Unit: `create_artifact` returns correct dict
- [ ] Unit: File created on disk
- [ ] Integration: Socket emits received by frontend
- [ ] Integration: Panel opens automatically
- [ ] E2E: Dev agent → artifact → QA review → save
- [ ] Tauri: Native save works offline

## Timeline

| Day | Task |
|-----|------|
| 1 | Core save function + basic socket events |
| 2 | Team chat hooks + Tauri integration |
| 3 | Polish: undo/redo, version history |

---

**Next Action:** Implement `create_artifact` in `tools.py` and test in solo chat mode.
