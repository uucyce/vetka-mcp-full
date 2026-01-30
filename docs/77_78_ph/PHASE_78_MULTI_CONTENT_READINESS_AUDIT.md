# Phase 78 Preview: Multi-Content Architecture Readiness
**📊 Audit for Knowledge Mode Universality**

---

## 🎯 Executive Summary

Phase 77 Memory Sync Protocol **успешно реализирована для CODE**, но NOT готова для multi-content (video, audio, documents, images).

**Multi-Content Readiness: 35%** ⚠️

**Gap:** NodeState (память) и ContentType (intake) — **разделены архитектурой**.

- ✅ Intake layer (web/API) — полностью multi-content ready
- ⚠️ Memory layer (sync) — code-centric design
- ❌ Bridge между ними — отсутствует

---

## 📊 Current Architecture Gap

```
┌─────────────────────────────────────────────┐
│         INTAKE LAYER (Multi-Content)        │
│  ✅ ContentType enum (VIDEO, AUDIO, DOC)    │
│  ✅ IntakeResult dataclass with metadata    │
│  ✅ Language, duration, tags, source        │
└────────────┬────────────────────────────────┘
             │ IntakeResult
             │ (with content_type)
             │
         ❌ MISSING BRIDGE
             │
             ↓
┌─────────────────────────────────────────────┐
│         MEMORY LAYER (Code-Centric)         │
│  ❌ NodeState - NO content_type field       │
│  ❌ EdgeState - Code-specific DEP score     │
│  ⚠️ metadata Dict workaround only           │
└─────────────────────────────────────────────┘
```

---

## 1️⃣ NodeState Class — Code-Centric Design

**Файл:** `src/memory/snapshot.py` (Lines 26-98)

### Current Fields:
```python
@dataclass
class NodeState:
    path: str                           # ✅ Universal
    embedding: List[float]              # ✅ Universal (768D)
    content_hash: str                   # ✅ Universal

    import_depth: int                   # ❌ CODE-SPECIFIC
    confidence: float                   # ✅ Universal
    timestamp: datetime                 # ✅ Universal
    memory_layer: Literal[...]          # ✅ Universal
    metadata: Dict[str, Any]            # ⚠️ Workaround only

    name: str                           # ✅ Universal
    extension: str                      # ✅ Universal
    size_bytes: int                     # ✅ Universal
    modified_time: float                # ✅ Universal
    created_time: float                 # ✅ Universal
```

### Missing Fields for Multi-Content:
```python
# ❌ MISSING:
content_type: str                   # "file", "video", "audio", "document", "image", "article"
relationships: Dict[str, List]      # {"imports": [...], "chapters": [...], "citations": [...]}
source_type: str                    # "filesystem", "youtube", "web", "api"
duration_seconds: int               # For video/audio
language: str                       # For documents/transcripts
tags: List[str]                     # For semantic grouping
```

### Assessment:
- **Universal?** NO — `import_depth` is code-specific
- **Extensible?** PARTIAL — `metadata` workaround, but no first-class support

---

## 2️⃣ Relationships Handling — Separate from Content Type

**Файл:** `src/memory/snapshot.py` (Lines 101-126)

### EdgeState:
```python
@dataclass
class EdgeState:
    source: str                     # Node path
    target: str                     # Node path
    dep_score: float               # ❌ CODE-SPECIFIC (0-1)
    edge_type: str                 # "import_dependency", "semantic"
    metadata: Dict[str, Any]       # Generic metadata
```

### Problem:
- **DEP score** assumes code dependencies
- Works for files, but what about video chapters?
- What about document citations?

### What Multi-Content Needs:
```python
# Video relationships:
edge_type = "chapter_follows"
dep_score = 1.0  # Always follows in sequence

# Document relationships:
edge_type = "citations"
dep_score = 0.85  # Relevance of citation

# Audio episode relationships:
edge_type = "episode_series"
dep_score = 0.9  # Continuity score
```

### Assessment:
- **Storage (edges)?** YES ✅ — EdgeState works for all types
- **Scoring (DEP)?** NO ❌ — Code-specific formula

---

## 3️⃣ MemoryDiff Algorithm — Partial Multi-Content Support

**Файл:** `src/memory/diff.py` (Lines 101-290)

### What Works for All Content Types:
```python
# Node added/deleted/modified detection
- Hash comparison (Line 214) ✅
- Timestamp comparison (Line 222) ✅
- Size comparison (Line 227) ✅
```

### What's Code-Specific:
```python
# Edge comparison
- DEP score change > 0.01 (Line 281) ❌

# Example: For videos, edge_type should matter more
# But current impl compares dep_score universally
```

### Assessment:
- **Node diff?** YES ✅ — Works for files/video/audio/docs
- **Edge diff?** PARTIAL ⚠️ — Storage works, comparison is code-centric

---

## 4️⃣ Scanner Architecture — Ready for Extension

**Файл:** `src/scanners/base_scanner.py` (Lines 1-162)

### BaseScanner Interface:
```python
class BaseScanner(ABC):
    @property
    @abstractmethod
    def supported_extensions(self) -> Set[str]: pass

    @abstractmethod
    def extract_dependencies(
        self,
        file_path: str,
        content: str
    ) -> List[Dependency]: pass
```

### Planned Scanners (Comments in code, Lines 10-15):
```
# - CodeScanner (Python, JS, TS) → Phase 72.3 ✅
# - DocumentScanner (MD, TXT, RST) → Future ❌
# - VideoScanner (MP4, chapters) → Future ❌
# - AudioScanner (podcasts, segments) → Future ❌
# - BookScanner (chapters, citations) → Future ❌
```

### Status:
| Scanner | Status | Implementation |
|---------|--------|-----------------|
| BaseScanner | ✅ | Abstract base class (161 lines) |
| PythonScanner | ✅ | Full implementation (461 lines) |
| VideoScanner | ❌ | Placeholder only |
| AudioScanner | ❌ | Placeholder only |
| DocumentScanner | ❌ | Placeholder only |
| ImageScanner | ❌ | Not mentioned |
| BookScanner | ❌ | Mentioned but not started |

### Assessment:
- **Extensible interface?** YES ✅
- **Concrete implementations?** ONLY Python ❌

---

## 5️⃣ IntakeResult → NodeState Bridge — MISSING

**Файл:** `src/intake/base.py` (Lines 18-55)

### IntakeResult (Web Intake Layer):
```python
@dataclass
class IntakeResult:
    content_type: ContentType      # ✅ ENUM with VIDEO, AUDIO, ARTICLE, etc.
    source_type: str               # youtube, telegram, web, api
    source_url: str
    title: str
    text: str
    author: Optional[str]
    published_at: Optional[datetime]
    duration_seconds: Optional[int]  # For video/audio
    language: Optional[str]
    tags: List[str]
```

### NodeState (Memory Layer):
```python
@dataclass
class NodeState:
    path: str
    embedding: List[float]
    # ❌ NO: content_type
    # ❌ NO: source_type
    # ❌ NO: duration_seconds
    # ❌ NO: language
    # ❌ NO: tags (except in metadata)
    metadata: Dict               # ⚠️ Workaround
```

### The Gap:
```python
# Current workaround (UNSAFE):
node = NodeState(
    path="/path/to/video.mp4",
    metadata={
        'content_type': 'video',       # STRING, NOT TYPE-SAFE
        'duration_seconds': 3600,      # UNVALIDATED
        'source_type': 'youtube',      # UNTRACKED
        'language': 'en',              # NOT STANDARD
    }
)

# What's needed:
def intake_to_nodestate(intake_result: IntakeResult) -> NodeState:
    return NodeState(
        path=intake_result.source_url,
        content_type=intake_result.content_type.value,  # ✅ TYPE-SAFE
        source_type=intake_result.source_type,          # ✅ TRACKED
        duration_seconds=intake_result.duration_seconds,# ✅ FIRST-CLASS
        language=intake_result.language,                # ✅ STANDARD
        tags=intake_result.tags,                        # ✅ VALIDATED
        ...
    )
```

### Assessment:
- **Bridge exists?** NO ❌
- **Needed for Phase 78?** YES ✅ CRITICAL

---

## 6️⃣ Multi-Content Readiness Matrix

| Component | Current | Needed | Gap |
|-----------|---------|--------|-----|
| **NodeState.content_type** | ❌ NO | ✅ YES | Add field |
| **NodeState.relationships** | ❌ NO | ✅ YES | Add field |
| **NodeState.source_type** | ❌ NO | ✅ YES | Add field |
| **MemoryDiff for nodes** | ✅ 100% | ✅ 100% | None |
| **MemoryDiff for edges** | ⚠️ 60% | ✅ 100% | Code-specific DEP |
| **VideoScanner** | ❌ 0% | ✅ 100% | Implement |
| **AudioScanner** | ❌ 0% | ✅ 100% | Implement |
| **DocumentScanner** | ❌ 0% | ✅ 100% | Implement |
| **ImageScanner** | ❌ 0% | ✅ 100% | Implement |
| **IntakeResult→NodeState** | ❌ 0% | ✅ 100% | Bridge needed |

**Overall Readiness: 35%** ⚠️

---

## 7️⃣ Exact File Locations

### Key Files to Modify:

| File | What | Lines | Priority |
|------|------|-------|----------|
| `src/memory/snapshot.py` | Add fields to NodeState | 26-98 | 🔴 HIGH |
| `src/memory/diff.py` | Extend for non-code content | 101-290 | 🔴 HIGH |
| `src/scanners/base_scanner.py` | Implement concrete scanners | 1-162 | 🟡 MEDIUM |
| `src/intake/base.py` | Create bridge function | 18-55 | 🔴 HIGH |
| (new file) | `src/scanners/video_scanner.py` | — | 🟡 MEDIUM |
| (new file) | `src/scanners/audio_scanner.py` | — | 🟡 MEDIUM |
| (new file) | `src/scanners/document_scanner.py` | — | 🟡 MEDIUM |

---

## 8️⃣ Phase 78 Implementation Plan

### Step 1: Extend NodeState (🔴 CRITICAL)
```python
# In snapshot.py, line 26-98

@dataclass
class NodeState:
    # ... existing fields ...

    # ❌ ADD THESE:
    content_type: str = "file"
    # Values: "file", "video", "audio", "document", "image", "article", "post"

    relationships: Dict[str, List[str]] = field(default_factory=dict)
    # Keys: "imports", "references", "chapters", "citations", "episodes", "mentions"

    source_type: str = "filesystem"
    # Values: "filesystem", "youtube", "web", "api", "telegram", etc.

    duration_seconds: Optional[int] = None
    # For video/audio

    language: Optional[str] = None
    # For documents/articles

    tags: List[str] = field(default_factory=list)
    # For semantic grouping
```

**Backward Compatible?** YES — all new fields have defaults

---

### Step 2: Create Bridge Function (🔴 CRITICAL)
```python
# In src/intake/bridge.py (new file)

def intake_to_nodestate(
    intake_result: IntakeResult
) -> NodeState:
    """Convert IntakeResult (web) → NodeState (memory)"""

    return NodeState(
        path=intake_result.source_url,
        embedding=[0.0] * 768,  # Will be computed by embedding pipeline
        content_type=intake_result.content_type.value,
        source_type=intake_result.source_type,
        duration_seconds=intake_result.duration_seconds,
        language=intake_result.language,
        tags=intake_result.tags,
        metadata={
            "title": intake_result.title,
            "author": intake_result.author,
            "published_at": intake_result.published_at,
        },
        ...
    )
```

---

### Step 3: Extend MemoryDiff (🟡 HIGH)
```python
# In diff.py, add method after line 290

def _should_compare_dep_score(
    self,
    old_node: NodeState,
    new_node: NodeState
) -> bool:
    """
    DEP score comparison only for code files.
    For other types, compare by edge_type instead.
    """
    return (
        old_node.content_type == "file" and
        new_node.content_type == "file"
    )
```

---

### Step 4: Implement Concrete Scanners (🟡 MEDIUM)

#### VideoScanner:
```python
# src/scanners/video_scanner.py

class VideoScanner(BaseScanner):
    supported_extensions = {".mp4", ".webm", ".mov", ".mkv"}

    def extract_dependencies(
        self,
        file_path: str,
        content: str  # JSON metadata or srt captions
    ) -> List[Dependency]:
        """Extract chapters, referenced videos, speakers"""
        # Returns List[Dependency] with:
        # - type: DependencyType.CHAPTER_REFERENCE
        # - target: next_video_id or timestamp
```

#### DocumentScanner:
```python
# src/scanners/document_scanner.py

class DocumentScanner(BaseScanner):
    supported_extensions = {".md", ".txt", ".rst", ".pdf"}

    def extract_dependencies(
        self,
        file_path: str,
        content: str
    ) -> List[Dependency]:
        """Extract citations, cross-references, headings"""
        # Returns List[Dependency] with:
        # - type: DependencyType.CITATION
        # - target: cited_paper_id
```

#### AudioScanner:
```python
# src/scanners/audio_scanner.py

class AudioScanner(BaseScanner):
    supported_extensions = {".mp3", ".wav", ".m4a", ".ogg"}

    def extract_dependencies(
        self,
        file_path: str,
        content: str  # JSON episode metadata
    ) -> List[Dependency]:
        """Extract episode series, guest mentions"""
        # Returns List[Dependency] with:
        # - type: DependencyType.EPISODE_SERIES
        # - target: next_episode_id
```

---

## 9️⃣ What Works Now (Phase 77 Ready)

✅ **Code file scanning** (PythonScanner complete)
✅ **Generic file metadata** (path, hash, size, timestamp)
✅ **Memory diff for files** (added/modified/deleted)
✅ **Generic relationship storage** (EdgeState)
✅ **Metadata dict** (workaround for content_type)
✅ **IntakeResult** has full multi-content support (web layer)

---

## 🔟 What Needs Phase 78

❌ **NodeState.content_type field** — Add to snapshot.py
❌ **NodeState.relationships field** — Add to snapshot.py
❌ **IntakeResult → NodeState bridge** — Create bridge.py
❌ **VideoScanner implementation** — Create video_scanner.py
❌ **AudioScanner implementation** — Create audio_scanner.py
❌ **DocumentScanner implementation** — Create document_scanner.py
❌ **MemoryDiff content-type awareness** — Extend diff.py

---

## 1️⃣1️⃣ Migration Complexity

| Task | Complexity | Time | Breaking Changes |
|------|-----------|------|------------------|
| Add NodeState fields | LOW | 1 hour | NO (defaults) |
| Create bridge function | LOW | 1 hour | NO (new code) |
| Extend MemoryDiff | LOW | 2 hours | NO (new logic) |
| VideoScanner | MEDIUM | 4 hours | NO (new scanner) |
| AudioScanner | MEDIUM | 4 hours | NO (new scanner) |
| DocumentScanner | MEDIUM | 3 hours | NO (new scanner) |
| Full integration test | MEDIUM | 2 hours | — |
| **TOTAL** | **MEDIUM** | **~17 hours** | **NONE** |

---

## 1️⃣2️⃣ Recommendation

### For Phase 77 (Current):
✅ **NO CHANGES NEEDED** — Phase 77 works perfectly for code

### For Phase 78 (Next):
🔴 **CRITICAL PRIORITY:**
1. Add fields to NodeState (backward compatible)
2. Create IntakeResult → NodeState bridge
3. Implement VideoScanner, AudioScanner, DocumentScanner

### Timeline:
- Phase 77: COMPLETE ✅
- Phase 78: Multi-content support (1-2 weeks)
- Phase 79: Knowledge Mode with universal content

---

## 1️⃣3️⃣ Knowledge Mode Vision

Once Phase 78 complete, VETKA can:

```
YouTube Video (intake) ✅ ContentType.VIDEO
  ↓
VideoScanner extracts chapters
  ↓
Converts to NodeState with content_type='video' ✅
  ↓
Creates edges: chapter→chapter relationships
  ↓
MemoryDiff works universally ✅
  ↓
Knowledge Mode: Video chapters appear in tree like files ✅
```

**Same for documents, audio, images, articles...**

---

## ✅ Summary

| Status | Component |
|--------|-----------|
| ✅ READY | Phase 77 Memory Sync (code-centric) |
| ⚠️ PARTIAL | Phase 77.2 MemoryDiff (node-ready, edge-limited) |
| ❌ BLOCKED | Phase 78 Multi-Content (needs bridge + scanners) |
| 📊 READINESS | 35% — Solid foundation, missing concrete implementations |

**Next Phase:** Build the bridge and scanners for universal Knowledge Mode.

---

**Report Date:** 2026-01-20
**Prepared For:** Phase 78 Planning
**Status:** Ready for implementation planning
