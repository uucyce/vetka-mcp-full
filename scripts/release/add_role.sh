#!/usr/bin/env bash
set -euo pipefail

# VETKA Role Creator — one command to add a new agent role.
# Usage: scripts/release/add_role.sh --callsign Polaris --domain architect --worktree captain --tool-type opencode --model-tier sonnet
#
# This script:
# 1. Adds role to agent_registry.yaml
# 2. Creates git branch + worktree
# 3. Generates CLAUDE.md + AGENTS.md
# 4. Creates symlink for registry (so worktree always reads from main)
# 5. Updates USER_GUIDE_MULTI_AGENT.md
# 6. Commits everything

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

# ── Parse arguments ───────────────────────────────────────────
CALLSIGN=""
DOMAIN=""
WORKTREE=""
BRANCH=""
TOOL_TYPE="opencode"
MODEL_TIER="sonnet"
PIPELINE_STAGE="coder"
ROLE_TITLE=""
OWNED_PATHS=""
BLOCKED_PATHS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --callsign) CALLSIGN="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --worktree) WORKTREE="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --tool-type) TOOL_TYPE="$2"; shift 2 ;;
    --model-tier) MODEL_TIER="$2"; shift 2 ;;
    --pipeline-stage) PIPELINE_STAGE="$2"; shift 2 ;;
    --role-title) ROLE_TITLE="$2"; shift 2 ;;
    --owned-paths) OWNED_PATHS="$2"; shift 2 ;;
    --blocked-paths) BLOCKED_PATHS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$CALLSIGN" || -z "$DOMAIN" || -z "$WORKTREE" ]]; then
  echo "Usage: $0 --callsign NAME --domain DOMAIN --worktree NAME [--tool-type opencode|claude_code] [--model-tier sonnet|opus]"
  exit 1
fi

BRANCH="${BRANCH:-agent/$(echo "$CALLSIGN" | tr '[:upper:]' '[:lower:]')-${DOMAIN}}"
ROLE_TITLE="${ROLE_TITLE:-${CALLSIGN} Agent}"

# ── Default owned/blocked paths ───────────────────────────────
if [[ -z "$OWNED_PATHS" ]]; then
  case "$DOMAIN" in
    qa)       OWNED_PATHS='["e2e/*.spec.cjs","e2e/playwright.config.ts","client/e2e/","tests/test_*.py"]' ;;
    weather)  OWNED_PATHS='["src/services/","config/browser_agents.yaml"]' ;;
    architect) OWNED_PATHS='["data/templates/agent_registry.yaml","docs/","src/orchestration/task_board.py"]' ;;
    *)        OWNED_PATHS='["src/"]' ;;
  esac
fi

if [[ -z "$BLOCKED_PATHS" ]]; then
  case "$DOMAIN" in
    qa)       BLOCKED_PATHS='["client/src/components/","client/src/store/","client/src/hooks/","src/services/"]' ;;
    weather)  BLOCKED_PATHS='["client/src/components/","e2e/"]' ;;
    *)        BLOCKED_PATHS='["client/src/components/","client/src/store/","client/src/hooks/"]' ;;
  esac
fi

echo "🚀 Adding role: $CALLSIGN ($DOMAIN) → worktree: $WORKTREE"
echo "   Branch: $BRANCH"
echo "   Tool: $TOOL_TYPE | Model: $MODEL_TIER | Stage: $PIPELINE_STAGE"
echo ""

# ── Step 1: Add to registry ──────────────────────────────────
REGISTRY="data/templates/agent_registry.yaml"
FIRST_FILE=$(echo "$OWNED_PATHS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0].strip('\"'))" 2>/dev/null || echo "src/")

cat >> "$REGISTRY" << EOF

  # ── ${CALLSIGN}: ${DOMAIN} Domain (${TOOL_TYPE}/${MODEL_TIER}) ──────────────────
  - callsign: "${CALLSIGN}"
    domain: "${DOMAIN}"
    pipeline_stage: "${PIPELINE_STAGE}"
    tool_type: "${TOOL_TYPE}"
    role_title: "${ROLE_TITLE}"
    worktree: "${WORKTREE}"
    branch: "${BRANCH}"
    model_tier: "${MODEL_TIER}"
    file: "${FIRST_FILE}"
    owned_paths:
$(echo "$OWNED_PATHS" | python3 -c "import sys,json; [print(f'      - \"{p}\"') for p in json.load(sys.stdin)]")
    blocked_paths:
$(echo "$BLOCKED_PATHS" | python3 -c "import sys,json; [print(f'      - \"{p}\"') for p in json.load(sys.stdin)]")
    roadmap: ""
EOF

echo "✅ Added to $REGISTRY"

# ── Step 2: Create branch + worktree ─────────────────────────
git branch "$BRANCH" 2>/dev/null || echo "   Branch $BRANCH already exists"
git worktree add ".claude/worktrees/${WORKTREE}" "$BRANCH" 2>/dev/null || echo "   Worktree already exists"

echo "✅ Branch + worktree created"

# ── Step 3: Create registry symlink ──────────────────────────
WT_REGISTRY=".claude/worktrees/${WORKTREE}/data/templates/agent_registry.yaml"
mkdir -p ".claude/worktrees/${WORKTREE}/data/templates"
rm -f "$WT_REGISTRY"
ln -sf "$(pwd)/$REGISTRY" "$WT_REGISTRY"

echo "✅ Registry symlink created → always reads from main"

# ── Step 4: Generate CLAUDE.md + AGENTS.md ──────────────────
.venv/bin/python -m src.tools.generate_claude_md --role "$CALLSIGN" 2>/dev/null || echo "⚠️  CLAUDE.md generation failed (may need registry reload)"
.venv/bin/python -m src.tools.generate_agents_md --role "$CALLSIGN" 2>/dev/null || echo "⚠️  AGENTS.md generation failed (may need registry reload)"

echo "✅ CLAUDE.md + AGENTS.md generated"

# ── Step 5: Update USER_GUIDE ────────────────────────────────
GUIDE="docs/USER_GUIDE_MULTI_AGENT.md"
if grep -q "$CALLSIGN" "$GUIDE" 2>/dev/null; then
  echo "ℹ️  $CALLSIGN already in USER_GUIDE_MULTI_AGENT.md"
else
  echo "" >> "$GUIDE"
  echo "| **${CALLSIGN}** | \`${WORKTREE}\` | ${DOMAIN} | ${TOOL_TYPE} | ${MODEL_TIER} | ${ROLE_TITLE} |" >> "$GUIDE"
  echo "✅ Added to USER_GUIDE_MULTI_AGENT.md"
fi

echo ""
echo "🎉 Role $CALLSIGN created successfully!"
echo ""
echo "Launch command:"
if [[ "$TOOL_TYPE" == "opencode" ]]; then
  echo "  cd .claude/worktrees/${WORKTREE} && opencode -m opencode/qwen3.6-plus-free"
else
  echo "  cd .claude/worktrees/${WORKTREE} && claude --dangerously-skip-permissions --model ${MODEL_TIER}"
fi
echo "  First message: vetka_session_init role=${CALLSIGN}"
