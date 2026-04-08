#!/bin/bash
# Sync vetka-agents-wrapper from original sources
# Run this before publishing vetka-agents mirror

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WRAPPER="${ROOT}/vetka-agents-wrapper"

echo "Syncing vetka-agents-wrapper..."

# Scripts
cp "${ROOT}/scripts/release/add_role.sh" "${WRAPPER}/"
cp "${ROOT}/AGENTS.md" "${WRAPPER}/"

# src/generators
mkdir -p "${WRAPPER}/src/generators"
cp "${ROOT}/src/generators/"* "${WRAPPER}/src/generators/"

# src/agents
mkdir -p "${WRAPPER}/src/agents"
cp "${ROOT}/src/agents/"* "${WRAPPER}/src/agents/"

echo "✅ vetka-agents-wrapper synced"
