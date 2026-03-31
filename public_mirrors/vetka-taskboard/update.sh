#!/usr/bin/env bash
# update.sh — Auto-update VETKA TaskBoard from GitHub
#
# Pulls latest changes, installs new dependencies, and restarts the server.
#
# Usage:
#   ./update.sh              # Pull, install deps, restart
#   ./update.sh --no-restart # Pull and install only

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  VETKA TaskBoard — Update                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Check we're in the right directory
if [ ! -f "src/app.py" ]; then
    echo -e "${RED}✗ Not in vetka-taskboard directory${NC}"
    exit 1
fi

# Pull latest from GitHub
echo -e "${YELLOW}→ Pulling latest from GitHub...${NC}"
git pull origin main
echo -e "${GREEN}✓${NC} Updated"

# Activate virtual env and update deps
VENV_DIR="${VETKA_TASKBOARD_VENV:-.venv}"
if [ -d "${VENV_DIR}" ]; then
    source "${VENV_DIR}/bin/activate"
    echo -e "${YELLOW}→ Updating dependencies...${NC}"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies updated"
else
    echo -e "${YELLOW}!${NC} No virtual env found. Run ./setup.sh first."
fi

echo ""

# Restart if --no-restart not passed
if [[ "${1:-}" != "--no-restart" ]]; then
    PORT="${TASKBOARD_PORT:-5001}"
    echo -e "${YELLOW}→ Killing existing TaskBoard processes...${NC}"
    pkill -f "uvicorn src.app:app" 2>/dev/null || true
    sleep 1

    echo -e "${CYAN}→ Starting TaskBoard on port ${PORT}...${NC}"
    echo -e "${GREEN}✓${NC} API docs: http://localhost:${PORT}/docs"
    echo -e "${GREEN}✓${NC} Health check: http://localhost:${PORT}/api/gateway/health"
    echo ""
    uvicorn src.app:app --host 0.0.0.0 --port "${PORT}"
else
    echo -e "${GREEN}✓${NC} Update complete. Restart with:"
    echo "    uvicorn src.app:app --host 0.0.0.0 --port 5001"
fi
