#!/bin/bash
# VETKA Code Audit Script v2.0
# Run: ./scripts/audit.sh
# Phase 96: Updated with @status markers check and dependency analysis

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              VETKA CODE AUDIT v2.0                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo "Date: $(date)"
echo ""

cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# ═══════════════════════════════════════════════════════════════
# 1. FILE COUNTS
# ═══════════════════════════════════════════════════════════════
echo "📊 FILE COUNTS:"
echo "  Python files:     $(find src -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null | wc -l | tr -d ' ')"
echo "  TypeScript/TSX:   $(find client -name '*.ts' -o -name '*.tsx' 2>/dev/null | grep -v node_modules | wc -l | tr -d ' ')"
echo "  JavaScript:       $(find frontend -name '*.js' 2>/dev/null | wc -l | tr -d ' ')"
echo "  Documentation:    $(find docs -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
echo ""

# ═══════════════════════════════════════════════════════════════
# 2. @STATUS MARKERS CHECK
# ═══════════════════════════════════════════════════════════════
echo "📁 FILES WITHOUT @status MARKER:"
echo "  Python (src/):"
missing_py=0
for f in $(find src -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null); do
  if ! grep -q "@status\|# Status:\|# @status" "$f" 2>/dev/null; then
    echo "    ⚠️  $f"
    missing_py=$((missing_py + 1))
    if [ $missing_py -ge 10 ]; then
      echo "    ... (showing first 10)"
      break
    fi
  fi
done
if [ $missing_py -eq 0 ]; then
  echo "    ✅ All files have @status marker"
fi
echo ""

echo "  Frontend (client/src/):"
missing_ts=0
for f in $(find client/src -name '*.ts' -o -name '*.tsx' 2>/dev/null | grep -v node_modules); do
  if ! grep -q "@status\|// Status:\|// @status" "$f" 2>/dev/null; then
    echo "    ⚠️  $f"
    missing_ts=$((missing_ts + 1))
    if [ $missing_ts -ge 10 ]; then
      echo "    ... (showing first 10)"
      break
    fi
  fi
done
if [ $missing_ts -eq 0 ]; then
  echo "    ✅ All files have @status marker"
fi
echo ""

# ═══════════════════════════════════════════════════════════════
# 3. ZOMBIE/ORPHAN FILES
# ═══════════════════════════════════════════════════════════════
echo "🧟 POTENTIAL ZOMBIE FILES (no imports):"
echo "  src/agents/:"
for f in src/agents/*.py; do
  name=$(basename "$f" .py)
  if [ "$name" != "__init__" ] && [ "$name" != "__pycache__" ]; then
    count=$(grep -rn "from src.agents.$name\|from src.agents import.*$name\|import $name" src/ main.py --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l | tr -d ' ')
    if [ "$count" -lt 1 ]; then
      echo "    ⚠️  $f (0 imports)"
    fi
  fi
done

echo "  src/mcp/tools/:"
for f in src/mcp/tools/*.py; do
  name=$(basename "$f" .py)
  if [ "$name" != "__init__" ]; then
    count=$(grep -rn "$name" src/ --include="*.py" 2>/dev/null | grep -v "__pycache__\|$f" | wc -l | tr -d ' ')
    if [ "$count" -lt 1 ]; then
      echo "    ⚠️  $f (0 references)"
    fi
  fi
done
echo ""

# ═══════════════════════════════════════════════════════════════
# 4. DUPLICATE FUNCTION NAMES
# ═══════════════════════════════════════════════════════════════
echo "🔀 DUPLICATE FUNCTION NAMES:"
echo "  Python (cross-file duplicates in src/):"
dups=$(grep -rh "^def \|^async def " src/ --include="*.py" 2>/dev/null | sed 's/(.*//' | sed 's/async //' | sort | uniq -d | head -10)
if [ -z "$dups" ]; then
  echo "    ✅ No duplicates found"
else
  echo "$dups" | while read line; do echo "    ⚠️  $line"; done
fi

echo "  TypeScript (client/src/):"
dups_ts=$(grep -rh "^export function \|^function \|^const .* = (" client/src --include="*.ts" --include="*.tsx" 2>/dev/null | sed 's/(.*//' | sort | uniq -d | head -5)
if [ -z "$dups_ts" ]; then
  echo "    ✅ No duplicates found"
else
  echo "$dups_ts" | while read line; do echo "    ⚠️  $line"; done
fi
echo ""

# ═══════════════════════════════════════════════════════════════
# 5. CRITICAL INTEGRATIONS CHECK
# ═══════════════════════════════════════════════════════════════
echo "🔗 CRITICAL INTEGRATIONS:"

# TripleWrite
tw_calls=$(grep -rn "TripleWriteManager\|triple_write" src/ --include="*.py" 2>/dev/null | grep -v "import\|#\|__pycache__" | wc -l | tr -d ' ')
echo "  TripleWrite references: $tw_calls"

# CAM Engine
cam_calls=$(grep -rn "CAMEngine\|cam_engine" src/ --include="*.py" 2>/dev/null | grep -v "import\|#\|__pycache__" | wc -l | tr -d ' ')
echo "  CAM Engine references: $cam_calls"

# Weaviate
weav_calls=$(grep -rn "weaviate\|Weaviate\|VetkaLeaf" src/ --include="*.py" 2>/dev/null | grep -v "import\|#\|__pycache__" | wc -l | tr -d ' ')
echo "  Weaviate references: $weav_calls"

# Qdrant
qdrant_calls=$(grep -rn "qdrant\|Qdrant\|vetka_elisya" src/ --include="*.py" 2>/dev/null | grep -v "import\|#\|__pycache__" | wc -l | tr -d ' ')
echo "  Qdrant references: $qdrant_calls"
echo ""

# ═══════════════════════════════════════════════════════════════
# 6. TOP LARGEST FILES
# ═══════════════════════════════════════════════════════════════
echo "📏 TOP 10 LARGEST PYTHON FILES:"
find src -name "*.py" -not -path '*/__pycache__/*' 2>/dev/null | xargs wc -l 2>/dev/null | sort -rn | head -11 | tail -10 | while read line; do
  echo "  $line"
done
echo ""

echo "📏 TOP 10 LARGEST FRONTEND FILES:"
find client/src -name "*.tsx" -o -name "*.ts" 2>/dev/null | grep -v node_modules | xargs wc -l 2>/dev/null | sort -rn | head -11 | tail -10 | while read line; do
  echo "  $line"
done
echo ""

# ═══════════════════════════════════════════════════════════════
# 7. PHASE MARKERS COUNT
# ═══════════════════════════════════════════════════════════════
echo "🏷️  PHASE MARKERS:"
for phase in 90 91 92 93 94 95 96; do
  count=$(grep -rn "Phase $phase\|PHASE_$phase\|FIX_$phase" src/ client/src --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l | tr -d ' ')
  echo "  Phase $phase: $count markers"
done
echo ""

# ═══════════════════════════════════════════════════════════════
# 8. TODO/FIXME COUNT
# ═══════════════════════════════════════════════════════════════
echo "📝 TODO/FIXME COUNT:"
todo_count=$(grep -rn "TODO\|FIXME\|HACK\|XXX" src/ client/src --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l | tr -d ' ')
echo "  Total TODO/FIXME: $todo_count"
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              AUDIT COMPLETE                               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
