#!/usr/bin/env bash
# add_role.sh — Create a new agent role in one command
#
# Based on Captain Polaris's team creation log.
# Creates: registry entry → branch → worktree → CLAUDE.md → AGENTS.md
#
# Usage:
#   ./add_role.sh <Callsign> <domain> <worktree-name> <client>
#
# Examples:
#   ./add_role.sh Lambda qa cut-qa-3 opencode
#   ./add_role.sh Polaris architect captain opencode
#   ./add_role.sh Nu engine cut-nu claude_code
#
# MARKER_201.ADD_ROLE: Automated team creation

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  VETKA — Add Agent Role                     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Parse arguments ──
CALLSIGN="${1:?Usage: $0 <Callsign> <domain> <worktree-name> <client>}"
DOMAIN="${2:?Domain (engine|media|ux|qa|harness|weather|architect)}"
WORKTREE="${3:?Worktree name (e.g. cut-qa-3)}"
CLIENT="${4:-opencode}"  # Default to opencode

ROLE_LOWER=$(echo "$CALLSIGN" | tr '[:upper:]' '[:lower:]')
BRANCH="agent/${ROLE_LOWER}"

# ── Determine defaults ──
case "$DOMAIN" in
  qa)       PIPELINE_STAGE="verifier";   MODEL_TIER="sonnet" ;;
  engine)   PIPELINE_STAGE="coder";      MODEL_TIER="sonnet" ;;
  media)    PIPELINE_STAGE="coder";      MODEL_TIER="sonnet" ;;
  ux)       PIPELINE_STAGE="coder";      MODEL_TIER="sonnet" ;;
  harness)  PIPELINE_STAGE="null";       MODEL_TIER="opus" ;;
  weather)  PIPELINE_STAGE="coder";      MODEL_TIER="sonnet" ;;
  architect) PIPELINE_STAGE="null";      MODEL_TIER="opus" ;;
  *)        PIPELINE_STAGE="null";       MODEL_TIER="sonnet" ;;
esac

case "$CLIENT" in
  opencode)   TOOL_TYPE="opencode" ;;
  claude_code) TOOL_TYPE="claude_code" ;;
  *)          TOOL_TYPE="$CLIENT" ;;
esac

echo -e "Role:      ${GREEN}${CALLSIGN}${NC}"
echo -e "Domain:    ${GREEN}${DOMAIN}${NC}"
echo -e "Worktree:  ${GREEN}${WORKTREE}${NC}"
echo -e "Branch:    ${GREEN}${BRANCH}${NC}"
echo -e "Client:    ${GREEN}${CLIENT}${NC}"
echo -e "Model:     ${GREEN}${MODEL_TIER}${NC}"
echo -e "Pipeline:  ${GREEN}${PIPELINE_STAGE}${NC}"
echo ""

# ── Find project root ──
PROJECT_ROOT="$(pwd)"
REGISTRY="${PROJECT_ROOT}/data/templates/agent_registry.yaml"
WORKTREES_DIR="${PROJECT_ROOT}/.claude/worktrees"

if [ ! -f "$REGISTRY" ]; then
    echo -e "${RED}✗ agent_registry.yaml not found at ${REGISTRY}${NC}"
    echo "  Run from VETKA project root or set VETKA_ROOT"
    exit 1
fi

# ── Step 1: Check if role already exists ──
if grep -q "callsign: \"${CALLSIGN}\"" "$REGISTRY" 2>/dev/null; then
    echo -e "${YELLOW}!${NC} Role ${CALLSIGN} already exists in registry"
else
    echo -e "${YELLOW}→ Step 1: Adding role to registry...${NC}"
    cat >> "$REGISTRY" <<EOF

# ── ${CALLSIGN}: ${DOMAIN} Domain (${CLIENT}) ──────────
- callsign: "${CALLSIGN}"
  domain: "${DOMAIN}"
  pipeline_stage: ${PIPELINE_STAGE}
  tool_type: "${TOOL_TYPE}"
  role_title: "${CALLSIGN} — ${DOMAIN} (${CLIENT})"
  worktree: "${WORKTREE}"
  branch: "${BRANCH}"
  model_tier: "${MODEL_TIER}"
  file: "src/"
  owned_paths:
    - "src/${DOMAIN}/"
  blocked_paths: []
  predecessor_docs: ""
  key_docs: []
  roadmap: ""
EOF
    echo -e "${GREEN}✓${NC} Registry updated"
fi

# ── Step 2: Create branch ──
echo -e "${YELLOW}→ Step 2: Creating branch ${BRANCH}...${NC}"
if git rev-parse --verify "$BRANCH" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Branch already exists"
else
    git branch "$BRANCH"
    echo -e "${GREEN}✓${NC} Branch created"
fi

# ── Step 3: Create worktree ──
echo -e "${YELLOW}→ Step 3: Creating worktree ${WORKTREE}...${NC}"
if [ -d "${WORKTREES_DIR}/${WORKTREE}" ]; then
    echo -e "${GREEN}✓${NC} Worktree already exists"
else
    mkdir -p "$WORKTREES_DIR"
    git worktree add "${WORKTREES_DIR}/${WORKTREE}" "$BRANCH"
    echo -e "${GREEN}✓${NC} Worktree created"
fi

# ── Step 4: Generate CLAUDE.md ──
echo -e "${YELLOW}→ Step 4: Generating CLAUDE.md...${NC}"
if command -v python3 &>/dev/null && [ -f "${PROJECT_ROOT}/src/tools/generate_claude_md.py" ]; then
    cd "$PROJECT_ROOT"
    python3 -m src.tools.generate_claude_md --role "$CALLSIGN" 2>&1 | tail -3
    echo -e "${GREEN}✓${NC} CLAUDE.md generated"
else
    echo -e "${YELLOW}!${NC} Generator not found — run from VETKA monorepo"
fi

# ── Step 5: Generate AGENTS.md ──
echo -e "${YELLOW}→ Step 5: Generating AGENTS.md...${NC}"
if command -v python3 &>/dev/null && [ -f "${PROJECT_ROOT}/src/tools/generate_agents_md.py" ]; then
    cd "$PROJECT_ROOT"
    python3 -m src.tools.generate_agents_md --role "$CALLSIGN" 2>&1 | tail -3
    echo -e "${GREEN}✓${NC} AGENTS.md generated"
else
    echo -e "${YELLOW}!${NC} Generator not found — run from VETKA monorepo"
fi

# ── Step 6: Commit registry change ──
echo -e "${YELLOW}→ Step 6: Committing registry change...${NC}"
cd "$PROJECT_ROOT"
git add "$REGISTRY"
git commit -m "Add ${CALLSIGN} role (${DOMAIN}, ${CLIENT})" 2>/dev/null || echo "  (no changes to commit)"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Role ${CALLSIGN} ready!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "Launch the agent:"
echo "  cd ${WORKTREES_DIR}/${WORKTREE}"
if [ "$CLIENT" = "opencode" ]; then
    echo "  opencode -m opencode/qwen3.6-plus-free"
else
    echo "  claude --model ${MODEL_TIER}"
fi
echo ""
echo "First message inside:"
echo "  vetka_session_init role=${CALLSIGN}"
