#!/bin/bash
# MARKER_196.CHECK-DUPE: Detect duplicate keys in CUT handler objects
# Prevents the Babel scope analysis errors from duplicate key definitions
# Focuses on: CutEditorLayoutV2 handlers, useCutEditorStore methods

set -e

echo "🔍 Scanning CUT critical files for duplicate object keys..."

FOUND_DUPLICATES=0

# Files that are known to have caused issues (hotkeyHandlers, store methods)
CRITICAL_FILES=(
  "client/src/components/cut/CutEditorLayoutV2.tsx"
  "client/src/store/useCutEditorStore.ts"
  "client/src/hooks/useCutHotkeys.ts"
  "client/src/components/cut/TimelineTrackView.tsx"
)

for file in "${CRITICAL_FILES[@]}"; do
  if [ ! -f "$file" ]; then
    continue
  fi

  # Use TypeScript compiler for real syntax checking
  # TS1117 = "An object literal cannot have multiple properties with the same name"
  # TS2451 = "Cannot redeclare block-scoped variable"
  if grep -q "^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*:" "$file" && \
     ! grep -q "^\s*//.*@ts-ignore\|^\s*//.*@ts-nocheck" "$file"; then

    # Check via TypeScript compiler if available
    if command -v npx &> /dev/null; then
      # Try to detect duplicates via quick TS check
      if npx tsc --noEmit "$file" 2>&1 | grep -q "TS1117\|TS2451"; then
        echo ""
        echo "❌ Duplicate keys detected in: $file"
        npx tsc --noEmit "$file" 2>&1 | grep "TS1117\|TS2451"
        FOUND_DUPLICATES=1
      fi
    fi
  fi
done

if [ $FOUND_DUPLICATES -eq 0 ]; then
  echo "✅ No critical duplicate keys found!"
  exit 0
else
  echo ""
  echo "❌ Please fix duplicate keys before committing."
  exit 1
fi
