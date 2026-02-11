# Grok Research: Diff/Patch Format for Pipeline Results

## Date: 2026-02-09
## Source: Grok via VETKA chat (user relay)

## Recommendation: `difflib.unified_diff` (stdlib, zero deps)

Pipeline already has:
- Original file content (Scout reads via `_read_file_snippets`)
- New code (Coder `subtask.result` with ``` blocks)

## Library Comparison

| Library | Pros | Cons | Fit |
|---|---|---|---|
| `difflib` (stdlib) | No deps, unified diffs, simple | Basic parsing | HIGH |
| `unidiff` (pip) | Git-compatible, hunk metadata | Extra dependency | MEDIUM |
| LSP WorkspaceEdit | IDE-native (Cursor/VSCode) | Manual JSON, complex | HIGH (future) |

## Implementation Plan

1. Scout caches originals in `scout_report.files[path] = content`
2. Coder outputs full new_content via code blocks
3. Pipeline generates diff: `difflib.unified_diff(original, new)`
4. Save as `subtask.diff_patch` in pipeline_tasks.json
5. Apply endpoint reads diff → applies patch (or full write fallback)

## Code Example

```python
import difflib

def generate_unified_diff(file_path: str, original: str, new_content: str) -> str:
    original_lines = original.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines, new_lines,
        fromfile=file_path, tofile=file_path,
        lineterm=''
    )
    return ''.join(diff)
```

## Edge Cases
- New file (no original): empty original → full add hunk
- Binary files: skip diff, flag as full-replace
- Multi-file subtasks: per-file diffs
- Diff >80% changed: use `SequenceMatcher.ratio()` → full replace

## Files to Update
- `agent_pipeline.py:1460-1540` — `_extract_and_write_files` → add diff gen
- `debug_routes.py` — apply endpoint supports both diff and full
- `pipeline_tasks.json` — new `diff_patch` field in subtask

## Phase: 128.4 (after E2E validation)
