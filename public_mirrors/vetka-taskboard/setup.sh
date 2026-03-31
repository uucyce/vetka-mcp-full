#!/usr/bin/env bash
# setup.sh — One-command setup for VETKA TaskBoard Agent Gateway
#
# Installs dependencies, creates config, and starts the server.
# Works standalone — no other VETKA components required.
#
# Usage:
#   ./setup.sh              # Install deps and start
#   ./setup.sh --no-start   # Install deps only

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  VETKA TaskBoard Agent Gateway — Setup      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python 3.10+ not found. Install it first.${NC}"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✓${NC} Python ${PY_VERSION}"

# Create virtual environment
VENV_DIR="${VETKA_TASKBOARD_VENV:-.venv}"
if [ ! -d "${VENV_DIR}" ]; then
    echo -e "${YELLOW}→ Creating virtual environment...${NC}"
    python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
echo -e "${GREEN}✓${NC} Virtual env: ${VENV_DIR}"

# Install dependencies
echo -e "${YELLOW}→ Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Install test deps if tests/ exists
if [ -d tests ]; then
    pip install -q pytest httpx
fi

echo -e "${GREEN}✓${NC} Dependencies installed"

# Create data directory
mkdir -p data
echo -e "${GREEN}✓${NC} Data directory: data/"

# Check for optional VETKA ecosystem components
echo ""
echo -e "${CYAN}── VETKA Ecosystem Detection ──${NC}"

VETKA_DIR="${VETKA_DIR:-$HOME/Documents/VETKA_Project/vetka_live_03}"
if [ -d "${VETKA_DIR}" ]; then
    echo -e "${GREEN}✓${NC} VETKA monorepo found: ${VETKA_DIR}"
    echo "  → TaskBoard can integrate with Memory, MCP, REFLEX"
else
    echo -e "${YELLOW}!${NC} VETKA monorepo not found at ${VETKA_DIR}"
    echo "  → Running in standalone mode (fully functional)"
    echo "  → Set VETKA_DIR env var to connect to full platform"
fi

if command -v gh &>/dev/null; then
    echo -e "${GREEN}✓${NC} GitHub CLI available"
fi

if command -v uvicorn &>/dev/null; then
    echo -e "${GREEN}✓${NC} uvicorn available"
fi

echo ""

# Start server if --no-start not passed
if [[ "${1:-}" != "--no-start" ]]; then
    PORT="${TASKBOARD_PORT:-5001}"
    echo -e "${CYAN}→ Starting TaskBoard on port ${PORT}...${NC}"
    echo -e "${GREEN}✓${NC} API docs: http://localhost:${PORT}/docs"
    echo -e "${GREEN}✓${NC} Health check: http://localhost:${PORT}/api/gateway/health"
    echo ""
    uvicorn src.app:app --host 0.0.0.0 --port "${PORT}"
else
    echo -e "${GREEN}✓${NC} Setup complete. Start with:"
    echo "    uvicorn src.app:app --host 0.0.0.0 --port 5001"
fi
