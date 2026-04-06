#!/bin/bash
# MARKER_175.7: Build MYCELIUM.app standalone
# Usage: ./scripts/build_mycelium.sh [dev|build]
#
# Prerequisites:
#   - Node.js + npm installed
#   - Rust + cargo installed
#   - Tauri CLI: cargo install tauri-cli
#   - Backend running: python main.py (port 5001)
#
# Phase 175 — MYCELIUM.app

set -e

MODE="${1:-build}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLIENT_DIR="$PROJECT_ROOT/client"
TAURI_MCC_DIR="$CLIENT_DIR/src-tauri-mcc"

echo "🍄 MYCELIUM Build System"
echo "   Mode: $MODE"
echo "   Project: $PROJECT_ROOT"
echo ""

# Step 0: Ensure we're in the right place
if [ ! -f "$TAURI_MCC_DIR/tauri.conf.json" ]; then
    echo "❌ src-tauri-mcc/tauri.conf.json not found"
    exit 1
fi

# Step 1: Install frontend dependencies if needed
if [ ! -d "$CLIENT_DIR/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd "$CLIENT_DIR" && npm install
fi

if [ "$MODE" = "dev" ]; then
    # Development mode — Tauri dev with hot reload
    echo "🔧 Starting MYCELIUM in dev mode..."
    echo "   Frontend: http://localhost:3002 (Vite HMR)"
    echo "   Backend:  http://localhost:5001 (must be running)"
    echo ""
    cd "$CLIENT_DIR" && cargo tauri dev --config src-tauri-mcc/tauri.conf.json

elif [ "$MODE" = "build" ]; then
    # Production build — create .app + .dmg
    echo "🏗️  Building MYCELIUM.app..."

    # Build frontend (MCC-only, no Three.js)
    echo "  [1/2] Building frontend (MCC bundle)..."
    cd "$CLIENT_DIR" && VITE_MODE=mcc npm run build:mcc

    # Build Tauri app
    echo "  [2/2] Building Tauri binary..."
    cd "$CLIENT_DIR" && cargo tauri build --config src-tauri-mcc/tauri.conf.json

    echo ""
    echo "✅ MYCELIUM.app ready!"
    echo "   App: $TAURI_MCC_DIR/target/release/bundle/macos/MYCELIUM.app"
    echo "   DMG: $TAURI_MCC_DIR/target/release/bundle/dmg/"

elif [ "$MODE" = "frontend" ]; then
    # Frontend-only dev (browser mode, no Tauri)
    echo "🌐 Starting MCC in browser mode..."
    echo "   URL: http://localhost:3002"
    echo "   Backend: http://localhost:5001 (must be running)"
    echo ""
    cd "$CLIENT_DIR" && VITE_MODE=mcc npx vite --port 3002

else
    echo "Usage: $0 [dev|build|frontend]"
    echo "  dev      — Tauri dev mode with HMR"
    echo "  build    — Production .app + .dmg"
    echo "  frontend — Browser-only (no Tauri)"
    exit 1
fi
