# CURSOR BRIEF: Diff Viewer for Pipeline Results

## Context
Phase 128.2 added Results Viewer with Apply/Copy buttons.
Now we need to show DIFF view (before/after) instead of just raw code.

## Problem
Currently pipeline results show full code blocks. User can't see WHAT changed.
Need a diff view showing original → new with green/red highlighting.

## Goal
When expanding a task result, show DIFF view (green = added, red = removed).
Toggle between "Full Code" and "Diff View" modes.

## What Needs to Change

### 1. Frontend: Diff Component
New component: `DiffViewer.tsx` in `client/src/components/panels/`

```tsx
// Simple diff viewer — NO external deps, just string comparison
// Green lines: additions (prefix +)
// Red lines: removals (prefix -)
// Gray lines: context (prefix space)
```

Parse unified diff format:
```
--- a/client/src/store/useStore.ts
+++ b/client/src/store/useStore.ts
@@ -42,6 +42,12 @@
   chat_id: string;
+  toggleBookmark: (id: string) => void;
+  bookmarkedChats: Set<string>;
```

### 2. Backend: Diff generation
Add `diff_patch` field to pipeline results.

`GET /api/debug/pipeline-results/{task_id}` response:
```json
{
  "subtasks": [{
    "result": "```ts\n// full code\n```",
    "diff_patch": "--- a/path\n+++ b/path\n@@ ...\n+new line\n-old line",
    "original_file": "path/to/file.ts"
  }]
}
```

Backend generates diff using `difflib.unified_diff` (Python stdlib).
If no original available → show full code (no diff).

### 3. Toggle in Results Expand
- Tab buttons: [Full Code] [Diff View]
- Default: Diff View (if diff_patch available)
- Fallback: Full Code (always available)

## Markers
- MARKER_128.4A: DiffViewer.tsx component
- MARKER_128.4B: Toggle in TaskCard expand
- MARKER_128.4C: Backend diff generation

## Style
- Added lines: `#1a3a1a` background (very dark green)
- Removed lines: `#3a1a1a` background (very dark red)
- Context: `#181818` (same as code bg)
- Line numbers: `#555` left gutter
- Font: monospace, same as code view

## Dependencies
- Needs backend to provide `diff_patch` in results
- Opus (Phase 128.4) will implement backend diff generation
- Until then: show "Full Code" only, diff tab disabled

## File Hints
- `client/src/components/panels/TaskCard.tsx` — add tabs
- NEW `client/src/components/panels/DiffViewer.tsx`

## Estimated Effort
2-3 hours, medium complexity.
