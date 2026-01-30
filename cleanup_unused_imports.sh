#!/bin/bash
# VETKA Unused Imports Cleanup Script
# Generated: 2026-01-07
#
# This script provides commands to clean up unused imports
# Review each section before running!

set -e

echo "VETKA Unused Imports Cleanup Script"
echo "===================================="
echo ""
echo "This script will help you remove unused imports from the VETKA codebase."
echo "Each phase is commented out by default. Uncomment to run."
echo ""

# ============================================================================
# PHASE 1: QUICK WINS (Verified Safe - 18 imports from 3 files)
# ============================================================================
echo "Phase 1: Quick Wins"
echo "-------------------"
echo "Files: src/tools/code_tools.py (3), orchestrator_with_elisya.py (10), agent_orchestrator_parallel.py (5)"
echo ""

# Uncomment to run Phase 1
: <<'PHASE1'

# 1. src/tools/code_tools.py - Remove lines 4, 5, 7
python3 << 'PYTHON_CODE'
import re

file_path = "src/tools/code_tools.py"
with open(file_path, 'r') as f:
    lines = f.readlines()

# Remove specific lines (in reverse to maintain line numbers)
lines_to_remove = [6, 4, 3]  # 0-indexed: line 7, 5, 4
for line_num in lines_to_remove:
    lines.pop(line_num)

with open(file_path, 'w') as f:
    f.writelines(lines)

print(f"✅ Cleaned {file_path}")
PYTHON_CODE

# 2. src/orchestration/orchestrator_with_elisya.py - Remove specific imports
# This is more complex - recommend manual editing or using an IDE refactoring tool

echo "⚠️  orchestrator_with_elisya.py requires manual editing (10 imports)"
echo "    Remove these lines:"
echo "    - Line 31: from src.agents.streaming_agent import StreamingAgent"
echo "    - Line 32: from src.orchestration.progress_tracker import ProgressTracker"
echo "    - Line 34: from src.orchestration.query_dispatcher import RouteStrategy"
echo "    - Line 37: from src.tools import registry, PermissionLevel"
echo "    - Line 38: from src.agents.tools import CreateArtifactTool"
echo "    - Line 42: from src.orchestration.chain_context import ChainContext"
echo "    - Line 45: from src.orchestration.response_formatter import format_response"
echo "    - Line 48: from src.elisya.state import ConversationMessage"
echo "    - Line 51: from src.elisya.key_manager import APIKeyRecord"

# 3. src/orchestration/agent_orchestrator_parallel.py - Remove specific imports
echo "⚠️  agent_orchestrator_parallel.py requires manual editing (5 imports)"
echo "    Remove these lines:"
echo "    - Line 12: from typing import Optional, Dict, Any"
echo "    - Line 20: from src.agents.streaming_agent import StreamingAgent"
echo "    - Line 21: from src.orchestration.progress_tracker import ProgressTracker"

PHASE1


# ============================================================================
# PHASE 2: AUTOMATED CLEANUP (Using autoflake or ruff)
# ============================================================================
echo ""
echo "Phase 2: Automated Cleanup"
echo "--------------------------"
echo "Install and run autoflake or ruff to automatically remove unused imports"
echo ""

# Uncomment to install and run autoflake
: <<'PHASE2_AUTOFLAKE'

# Install autoflake
pip install autoflake

# Dry run first (see what would be removed)
autoflake --remove-all-unused-imports --recursive src/

# Apply changes (uncomment when ready)
# autoflake --remove-all-unused-imports --in-place --recursive src/

echo "✅ Autoflake cleanup complete"

PHASE2_AUTOFLAKE

# Uncomment to install and run ruff
: <<'PHASE2_RUFF'

# Install ruff
pip install ruff

# Check for unused imports
ruff check --select F401 src/

# Apply fixes (uncomment when ready)
# ruff check --select F401 --fix src/

echo "✅ Ruff cleanup complete"

PHASE2_RUFF


# ============================================================================
# PHASE 3: ADD NOQA COMMENTS (For intentional unused imports)
# ============================================================================
echo ""
echo "Phase 3: Document Intentional Unused Imports"
echo "---------------------------------------------"
echo "Add # noqa: F401 comments to intentional unused imports"
echo ""

# Uncomment to add noqa comments
: <<'PHASE3'

# src/initialization/dependency_check.py - Add noqa comments
python3 << 'PYTHON_CODE'
import re

file_path = "src/initialization/dependency_check.py"
with open(file_path, 'r') as f:
    content = f.read()

# Add noqa comments to specific lines
replacements = [
    (r'(\s+import ollama)$', r'\1  # noqa: F401 - checking availability'),
    (r'(\s+import openai)$', r'\1  # noqa: F401 - checking availability'),
    (r'(\s+import anthropic)$', r'\1  # noqa: F401 - checking availability'),
    (r'(\s+import google\.generativeai)$', r'\1  # noqa: F401 - checking availability'),
    (r'(from src\.agents\.pixtral_learner import PixtralLearner)$', r'\1  # noqa: F401 - trigger @register'),
    (r'(from src\.agents\.qwen_learner import QwenLearner)$', r'\1  # noqa: F401 - trigger @register'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

with open(file_path, 'w') as f:
    f.write(content)

print(f"✅ Added noqa comments to {file_path}")
PYTHON_CODE

PHASE3


# ============================================================================
# PHASE 4: SETUP PRE-COMMIT HOOKS
# ============================================================================
echo ""
echo "Phase 4: Setup Pre-Commit Hooks"
echo "--------------------------------"
echo "Add unused import checking to pre-commit hooks"
echo ""

# Uncomment to setup pre-commit with ruff
: <<'PHASE4'

# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml if it doesn't exist
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --select, F401]
      - id: ruff-format
EOF

# Install the git hook
pre-commit install

echo "✅ Pre-commit hooks installed"

PHASE4


# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "============================================================================"
echo "CLEANUP SUMMARY"
echo "============================================================================"
echo ""
echo "To use this script:"
echo "  1. Review each PHASE section"
echo "  2. Uncomment the phase you want to run"
echo "  3. Run: bash cleanup_unused_imports.sh"
echo ""
echo "Recommended order:"
echo "  1. Phase 1: Quick wins (manual verification recommended)"
echo "  2. Phase 2: Automated cleanup with ruff or autoflake"
echo "  3. Phase 3: Add noqa comments for intentional imports"
echo "  4. Phase 4: Setup pre-commit hooks to prevent future issues"
echo ""
echo "For detailed information, see:"
echo "  - UNUSED_IMPORTS_REPORT.md (detailed analysis)"
echo "  - unused_imports_report.json (machine-readable data)"
echo "  - analyze_unused_imports_v2.py (re-run analysis)"
echo ""
echo "============================================================================"
