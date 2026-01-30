# VETKA Context Intelligence Research

**Phase:** 65.5
**Status:** Research Required
**Priority:** CRITICAL
**Date:** 2025-01-18

---

## Problem Statement

When users pin files/folders in VETKA, the context sent to AI agents is **naively truncated**, losing critical information.

### Evidence from ChatGPT Testing

User pinned a folder with 2 Python files. ChatGPT reported:

```
- classify_images.py: обрезан на сцене 6 [truncated]
- analyze_images.py: обрезан на сцене 8 [truncated]
- Total context: ~800-1200 токенов (очень мало)
- Директория /Users/.../work: "Status: File not found"
```

### Current Elysium Behavior

1. **Naive truncation**: Simply takes first N characters/lines
2. **No semantic understanding**: Cuts mid-function, mid-class
3. **No smart summarization**: No AST parsing, no importance scoring
4. **Lost relationships**: File dependencies, imports not preserved
5. **No user feedback**: User doesn't know what was actually sent

---

## Research Prompt for Grok

```markdown
# Research Task: VETKA Context Intelligence

## Background
We're building VETKA - a 3D knowledge graph IDE where users can pin files/folders
to provide context to AI agents. Current implementation (Elysium) uses naive
truncation which loses critical information.

## Current Problem
When user pins a folder with files, the context sent to AI:
- Simply takes first N characters of each file
- No semantic understanding
- No smart summarization
- Large files get cut mid-function
- Structure/relationships lost

## Research Questions

### 1. Context Compression Strategies
- What are SOTA approaches for fitting large codebases into LLM context?
- Compare: truncation vs chunking vs summarization vs embeddings+retrieval
- What do Cursor, Windsurf, Aider use?
- Token budget allocation strategies

### 2. Semantic Code Summarization
- How to summarize code while preserving:
  - Function signatures and docstrings
  - Class hierarchies
  - Import dependencies
  - Key logic flow
- AST-based vs LLM-based summarization tradeoffs
- Language-specific considerations (Python, TypeScript, etc.)

### 3. Multi-file Context Assembly
- How to prioritize which files/parts to include?
- Relevance scoring based on user query
- Dynamic context window management
- "Zoom levels" for code:
  - Level 0: File name only
  - Level 1: Exports/signatures
  - Level 2: + Docstrings
  - Level 3: + Implementation summaries
  - Level 4: Full code

### 4. Existing Solutions Analysis
- How does GitHub Copilot handle workspace context?
- Claude's "Projects" feature - how does it work?
- Sourcegraph Cody's context fetching
- Continue.dev's context providers
- Cursor's @codebase feature
- Aider's repo-map

### 5. VETKA-specific Considerations
- User manually pins files = explicit intent signal
- 3D spatial layout = implicit importance (closer = more related?)
- Chat history = what user asked before
- Selected node = current focus
- Optimal strategy for our use case

### 6. Implementation Approaches
- Tree-sitter for AST parsing (multi-language)
- LLM-based summarization (expensive but smart)
- Hybrid: AST structure + LLM for complex parts
- Caching strategies for summaries
- Incremental updates on file changes

## Expected Output
1. Comparison table of approaches (pros/cons/complexity)
2. Recommended architecture for VETKA
3. Implementation priorities (MVP → Full)
4. Token budget allocation strategy
5. Code snippets or pseudocode for key algorithms
6. Metrics to measure context quality
```

---

## Current VETKA Context Flow

```
User pins files → Elysium reads files → [TRUNCATION HERE] → Send to AI

What happens now:
1. pinnedFileIds[] in useStore
2. ChatPanel reads files via /api/files/read
3. Files concatenated with headers
4. If too long → first N chars taken
5. Sent to provider (OpenAI, Anthropic, etc.)
```

### Files Involved

| File | Role |
|------|------|
| `client/src/store/useStore.ts` | pinnedFileIds state |
| `client/src/components/chat/ChatPanel.tsx` | Context assembly |
| `server/src/api/files.py` | File reading |
| `server/src/chat/elysium.py` | Context processing |

---

## Proposed Solutions (Hypothesis)

### MVP (Quick Win)
1. **Show user what's sent**: Display token count, truncation warnings
2. **Smart truncation**: Preserve function signatures, cut bodies
3. **Priority ordering**: Selected file first, then by relevance

### Short-term
1. **AST-based summarization** for Python/TypeScript
2. **Signature extraction**: Functions, classes, exports
3. **Configurable zoom levels** per file

### Medium-term
1. **LLM-assisted summarization** for complex files
2. **Dependency graph**: Show related files
3. **Query-aware context**: Adjust based on user's question

### Long-term
1. **RAG with embeddings**: Vector search for relevant chunks
2. **Semantic caching**: Reuse summaries across sessions
3. **Learning from usage**: Which context led to good answers?

---

## Metrics to Track

| Metric | Description |
|--------|-------------|
| Context utilization | % of token budget used effectively |
| Information density | Useful info per token |
| User satisfaction | Did AI understand the code? |
| Truncation rate | How often files get cut |
| Response relevance | AI answers match user intent |

---

## Questions for Team Discussion

1. **Token budget**: How much context per provider? (GPT-4: 128k, Claude: 200k)
2. **User control**: Should users see/edit what's sent?
3. **Caching**: Store summaries in Qdrant alongside embeddings?
4. **Real-time vs batch**: Summarize on pin or on send?
5. **Language support**: Start with Python/TS or all languages?

---

## Next Steps

1. [ ] Grok research with prompt above
2. [ ] Audit current Elysium implementation
3. [ ] Prototype AST-based signature extraction
4. [ ] Add context preview in ChatPanel
5. [ ] User testing with different strategies

---

## References

- [Aider's Repo Map](https://aider.chat/docs/repomap.html)
- [Cursor's Context](https://cursor.sh/docs)
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)

---

## Appendix: ChatGPT's Full Report

```
## 1. Какие файлы я **реально вижу сейчас**

Из всего, что ты указал, **фактически загружены в мой контекст только 2 файла**,
и оба — **закреплённые (pinned)**:

### ✅ `classify_images.py`
- шапку файла и назначение
- функцию `get_detailed_scene_mapping()`
- **подробную структуру сцен** (номер, title, description, shots)
- **НО**: файл **обрезан** — начиная примерно с сцены 6 текст заканчивается (`[truncated]`)

### ✅ `analyze_images.py`
- назначение файла
- `analyze_image_with_description()` (заглушка под FastVLM)
- `get_scene_mapping()`
- сцены 1–8
- **тоже обрезан** на сцене 8 (`[truncated]`)

### ❌ `/Users/danilagulin/work`
- **не существует для меня**
- я не вижу дерево файлов
- Сообщение `Status: File not found`

## 2. Контекст **не перегружен**
- каждый файл: ~300–600 токенов видимого текста
- итого: **≈ 800–1200 токенов**
- Для меня это очень мало, комфортно, почти «пусто»

## 3. Я НЕ могу:
- сам открыть директорию
- сам прочитать файл по пути
- сам «подгрузить ещё»
```

---

*Document created: Phase 65.5 Context Research*
*Last updated: 2025-01-18*
