#!/bin/bash
# Sync vetka-mcp-full wrapper from original sources
# Run this before publishing vetka-mcp-full mirror

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WRAPPER="${ROOT}/vetka-mcp-full"

echo "Syncing vetka-mcp-full..."

# Copy modules from monorepo
cp -r "${ROOT}/src/mcp" "${WRAPPER}/src/"
cp -r "${ROOT}/src/orchestration" "${WRAPPER}/src/"
cp -r "${ROOT}/src/memory" "${WRAPPER}/src/"
cp -r "${ROOT}/src/search" "${WRAPPER}/src/"
cp -r "${ROOT}/src/bridge" "${WRAPPER}/src/"
cp -r "${ROOT}/src/agents" "${WRAPPER}/src/"

# Copy critical services
mkdir -p "${WRAPPER}/src/services"
for f in agent_registry session_tracker artifact_scanner disk_artifact_service \
         activity_hub activity_emitter balance_tracker experience_report \
         roadmap_task_sync roadmap_generator mcc_jepa_adapter jepa_runtime \
         tool_source_watch reflex_*; do
    cp "${ROOT}/src/services/${f}.py" "${WRAPPER}/src/services/" 2>/dev/null || true
done

# Copy stubs
cp "${ROOT}/vetka-mcp-full/src/initialization/singletons.py" "${WRAPPER}/src/initialization/" 2>/dev/null || true
cp "${ROOT}/vetka-mcp-full/src/utils/unified_key_manager.py" "${WRAPPER}/src/utils/" 2>/dev/null || true
cp "${ROOT}/vetka-mcp-full/src/utils/staging_utils.py" "${WRAPPER}/src/utils/" 2>/dev/null || true

echo "✅ vetka-mcp-full synced"
