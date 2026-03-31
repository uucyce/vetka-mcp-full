#!/usr/bin/env bash
# sync_public_mirror.sh — Extract subtree from VETKA monorepo and push to public GitHub mirror
#
# Usage: ./scripts/release/sync_public_mirror.sh <mirror-name>
# Example: ./scripts/release/sync_public_mirror.sh vetka-taskboard
#
# MARKER_196.MIRROR-SYNC: Auto-sync public mirrors
#
# First-time setup for a new mirror:
#   gh repo create danilagoleen/<mirror-name> --public --description "<desc>"
#   ./scripts/release/sync_public_mirror.sh <mirror-name>

set -euo pipefail

MIRROR_NAME="${1:?Usage: $0 <mirror-name>}"
MIRROR_DIR="public_mirrors/${MIRROR_NAME}"
GITHUB_USER="danilagoleen"
REMOTE_URL="git@github.com:${GITHUB_USER}/${MIRROR_NAME}.git"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== VETKA Public Mirror Sync ===${NC}"
echo "Mirror: ${MIRROR_NAME}"
echo "Source: ${MIRROR_DIR}/"
echo "Remote: ${REMOTE_URL}"
echo ""

# Check source directory exists
if [ ! -d "${MIRROR_DIR}" ]; then
    echo -e "${RED}Error: ${MIRROR_DIR} does not exist${NC}"
    exit 1
fi

# Check we're in the monorepo root
if [ ! -f "scripts/release/sync_public_mirror.sh" ]; then
    echo -e "${RED}Error: Run from VETKA monorepo root${NC}"
    exit 1
fi

# Create temp dir with mirror contents
TMPDIR=$(mktemp -d)
trap "rm -rf ${TMPDIR}" EXIT

cp -r "${MIRROR_DIR}/." "${TMPDIR}/"

cd "${TMPDIR}"
git init -q
git add -A
git commit -q -m "phase196: Sync ${MIRROR_NAME} from VETKA monorepo ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
git branch -M main

# Add or update remote
if git remote get-url origin &>/dev/null; then
    git remote set-url origin "${REMOTE_URL}"
else
    git remote add origin "${REMOTE_URL}"
fi

# Push
echo -e "${YELLOW}Pushing to ${REMOTE_URL}...${NC}"
git push -u origin main --force

echo ""
echo -e "${GREEN}=== Mirror sync complete! ===${NC}"
echo "Public repo: https://github.com/${GITHUB_USER}/${MIRROR_NAME}"
