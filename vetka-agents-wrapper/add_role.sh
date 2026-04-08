#!/usr/bin/env bash
set -euo pipefail

# VETKA Role Creator — one command to add a new agent role.
# MARKER_ETA.ADD_ROLE_V2: Fixed smart insertion into roles: section.
#
# Usage:
#   scripts/release/add_role.sh --callsign Xi --domain qa --worktree cut-qa-6 \
#     --tool-type opencode --model-tier sonnet --role-title "QA Agent 6 / Qwen"
#
# This script:
# 1. Validates callsign is unique in agent_registry.yaml
# 2. Inserts role into roles: section (BEFORE shared_zones:) — not append to end
# 3. Creates git branch + worktree
# 4. Creates registry symlink → main (always fresh)
# 5. Generates CLAUDE.md + AGENTS.md (with exit-code check)
# 6. Updates USER_GUIDE_MULTI_AGENT.md
# 7. Prints launch command

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

VENV_PYTHON="${ROOT_DIR}/.venv/bin/python3"
if [[ ! -x "$VENV_PYTHON" ]]; then
  VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
fi
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "ERROR: .venv/bin/python3 not found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

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
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --callsign)      CALLSIGN="$2"; shift 2 ;;
    --domain)        DOMAIN="$2"; shift 2 ;;
    --worktree)      WORKTREE="$2"; shift 2 ;;
    --branch)        BRANCH="$2"; shift 2 ;;
    --tool-type)     TOOL_TYPE="$2"; shift 2 ;;
    --model-tier)    MODEL_TIER="$2"; shift 2 ;;
    --pipeline-stage) PIPELINE_STAGE="$2"; shift 2 ;;
    --role-title)    ROLE_TITLE="$2"; shift 2 ;;
    --owned-paths)   OWNED_PATHS="$2"; shift 2 ;;
    --blocked-paths) BLOCKED_PATHS="$2"; shift 2 ;;
    --dry-run)       DRY_RUN=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$CALLSIGN" || -z "$DOMAIN" || -z "$WORKTREE" ]]; then
  echo "Usage: $0 --callsign NAME --domain DOMAIN --worktree NAME [options]"
  echo ""
  echo "Options:"
  echo "  --tool-type     opencode|claude_code|vibe (default: opencode)"
  echo "  --model-tier    sonnet|opus|haiku (default: sonnet)"
  echo "  --pipeline-stage coder|verifier|architect (default: coder)"
  echo "  --role-title    Human-readable title"
  echo "  --owned-paths   JSON array of paths"
  echo "  --blocked-paths JSON array of paths"
  echo "  --dry-run       Print what would happen, don't write"
  exit 1
fi

BRANCH="${BRANCH:-agent/$(echo "$CALLSIGN" | tr '[:upper:]' '[:lower:]')-${DOMAIN}}"
DOMAIN_CAP="$(echo "$DOMAIN" | python3 -c "import sys; print(sys.stdin.read().strip().capitalize())")"
ROLE_TITLE="${ROLE_TITLE:-${CALLSIGN} ${DOMAIN_CAP} Agent}"
REGISTRY="data/templates/agent_registry.yaml"

# ── Default owned/blocked paths ───────────────────────────────
if [[ -z "$OWNED_PATHS" ]]; then
  case "$DOMAIN" in
    qa)        OWNED_PATHS='["e2e/*.spec.cjs","e2e/playwright.config.ts","client/e2e/","tests/test_*.py"]' ;;
    weather)   OWNED_PATHS='["src/services/","config/browser_agents.yaml"]' ;;
    architect) OWNED_PATHS='["data/templates/agent_registry.yaml","docs/","src/orchestration/task_board.py"]' ;;
    engine)    OWNED_PATHS='["client/src/store/","client/src/hooks/","client/src/components/cut/"]' ;;
    harness)   OWNED_PATHS='["src/mcp/tools/","src/orchestration/task_board.py","src/services/agent_registry.py"]' ;;
    *)         OWNED_PATHS='["src/"]' ;;
  esac
fi

if [[ -z "$BLOCKED_PATHS" ]]; then
  case "$DOMAIN" in
    qa)        BLOCKED_PATHS='["client/src/components/","client/src/store/","client/src/hooks/","src/services/"]' ;;
    weather)   BLOCKED_PATHS='["client/src/components/","e2e/"]' ;;
    *)         BLOCKED_PATHS='["client/src/components/","client/src/store/","client/src/hooks/","e2e/"]' ;;
  esac
fi

echo "Adding role: $CALLSIGN ($DOMAIN) → worktree: $WORKTREE"
echo "  Branch: $BRANCH | Tool: $TOOL_TYPE | Model: $MODEL_TIER | Stage: $PIPELINE_STAGE"
echo ""

# ── Step 1: Validate uniqueness ───────────────────────────────
if grep -q "callsign: \"${CALLSIGN}\"" "$REGISTRY" 2>/dev/null; then
  echo "ERROR: Callsign '${CALLSIGN}' already exists in $REGISTRY"
  echo "  Use a different name or remove the existing entry first."
  exit 1
fi

# ── Step 2: Insert into roles: section (before shared_zones:) ─
FIRST_FILE=$("$VENV_PYTHON" -c "import json,sys; d=json.loads('$OWNED_PATHS'); print(d[0])" 2>/dev/null || echo "src/")

ROLE_YAML="
  # ── ${CALLSIGN}: ${DOMAIN} Domain (${TOOL_TYPE}/${MODEL_TIER}) ──────────────────
  - callsign: \"${CALLSIGN}\"
    domain: \"${DOMAIN}\"
    pipeline_stage: \"${PIPELINE_STAGE}\"
    tool_type: \"${TOOL_TYPE}\"
    role_title: \"${ROLE_TITLE}\"
    worktree: \"${WORKTREE}\"
    branch: \"${BRANCH}\"
    model_tier: \"${MODEL_TIER}\"
    file: \"${FIRST_FILE}\"
    owned_paths:
$("$VENV_PYTHON" -c "import json,sys; [print(f'      - \"{p}\"') for p in json.loads('$OWNED_PATHS')]")
    blocked_paths:
$("$VENV_PYTHON" -c "import json,sys; [print(f'      - \"{p}\"') for p in json.loads('$BLOCKED_PATHS')]")
    roadmap: \"\""

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY-RUN: Would insert into $REGISTRY before shared_zones: section:"
  echo "$ROLE_YAML"
else
  # Insert BEFORE the "# ── Shared Zones" or "shared_zones:" line
  # Python does safe in-place insertion (not cat >>)
  "$VENV_PYTHON" << PYEOF
import re, sys

registry_path = "${REGISTRY}"
with open(registry_path, "r") as f:
    content = f.read()

# Find insertion point: before shared_zones: section
# Match either "# ── Shared Zones" comment or "shared_zones:" key
insert_marker = re.search(r"^(# ── Shared Zones|shared_zones:)", content, re.MULTILINE)
if not insert_marker:
    # Fallback: append to end of roles: section (before external_agents: if present)
    insert_marker = re.search(r"^(# ── External Agents|external_agents:)", content, re.MULTILINE)
if not insert_marker:
    # Last resort: append to file
    with open(registry_path, "a") as f:
        f.write("""${ROLE_YAML}""")
    print("  Appended to end of file (no shared_zones marker found)")
    sys.exit(0)

pos = insert_marker.start()
new_content = content[:pos] + """${ROLE_YAML}\n\n""" + content[pos:]
with open(registry_path, "w") as f:
    f.write(new_content)
print("  Inserted into roles: section (before shared_zones:)")
PYEOF

  echo "Added to $REGISTRY (roles: section)"
fi

# ── Step 3: Create branch + worktree ─────────────────────────
if [[ "$DRY_RUN" != "true" ]]; then
  git branch "$BRANCH" 2>/dev/null || echo "  Branch $BRANCH already exists"
  git worktree add ".claude/worktrees/${WORKTREE}" "$BRANCH" 2>/dev/null || echo "  Worktree already exists"
  echo "Branch + worktree ready"
fi

# ── Step 4: Create registry symlink ──────────────────────────
if [[ "$DRY_RUN" != "true" ]]; then
  WT_REGISTRY=".claude/worktrees/${WORKTREE}/data/templates/agent_registry.yaml"
  mkdir -p ".claude/worktrees/${WORKTREE}/data/templates"
  rm -f "$WT_REGISTRY"
  ln -sf "$(pwd)/$REGISTRY" "$WT_REGISTRY"
  echo "Registry symlink: .claude/worktrees/${WORKTREE}/data/templates/ → main"
fi

# ── Step 5: Generate CLAUDE.md + AGENTS.md ───────────────────
if [[ "$DRY_RUN" != "true" ]]; then
  if "$VENV_PYTHON" -m src.generate_claude_md --role "$CALLSIGN"; then
    echo "CLAUDE.md generated"
  else
    echo "ERROR: CLAUDE.md generation failed for $CALLSIGN"
    exit 1
  fi

  if "$VENV_PYTHON" -m src.generate_agents_md --role "$CALLSIGN"; then
    echo "AGENTS.md generated"
  else
    echo "ERROR: AGENTS.md generation failed for $CALLSIGN"
    exit 1
  fi
fi

# ── Step 6: Update USER_GUIDE ─────────────────────────────────
GUIDE="docs/USER_GUIDE_MULTI_AGENT.md"
if [[ "$DRY_RUN" != "true" ]]; then
  if grep -q "\"${CALLSIGN}\"" "$GUIDE" 2>/dev/null || grep -q "| ${CALLSIGN} " "$GUIDE" 2>/dev/null; then
    echo "  $CALLSIGN already in USER_GUIDE_MULTI_AGENT.md"
  else
    printf "\n| **%s** | \`%s\` | %s | %s | %s | %s |\n" \
      "$CALLSIGN" "$WORKTREE" "$DOMAIN" "$TOOL_TYPE" "$MODEL_TIER" "$ROLE_TITLE" >> "$GUIDE"
    echo "Added to USER_GUIDE_MULTI_AGENT.md"
  fi
fi

echo ""
echo "Role $CALLSIGN created successfully!"
echo ""
echo "Launch command:"
if [[ "$TOOL_TYPE" == "opencode" ]]; then
  echo "  cd .claude/worktrees/${WORKTREE} && opencode -m opencode/qwen3.6-plus-free"
elif [[ "$TOOL_TYPE" == "claude_code" ]]; then
  echo "  cd .claude/worktrees/${WORKTREE} && claude --dangerously-skip-permissions"
elif [[ "$TOOL_TYPE" == "vibe" ]]; then
  echo "  cd .claude/worktrees/${WORKTREE} && vibe"
  echo ""
  echo "  NOTE: Vibe requires vetka MCP in ~/.vibe/config.toml:"
  echo "    mcp_servers = [{name=\"vetka\", transport=\"stdio\", command=\"python\","
  echo "      args=[\"$(pwd)/src/mcp/vetka_mcp_bridge.py\"],"
  echo "      env={VETKA_API_URL=\"http://localhost:5001\", PYTHONPATH=\"$(pwd)\"}}]"
else
  echo "  cd .claude/worktrees/${WORKTREE} && <your-tool>"
fi
echo "  First message: vetka_session_init role=${CALLSIGN}"
