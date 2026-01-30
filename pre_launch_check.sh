#!/bin/bash
# VETKA Phase 7.3 v2 - Final Pre-Launch Check
# This script verifies all components are ready

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║     🔍 VETKA PHASE 7.3 v2 - PRE-LAUNCH VERIFICATION            ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $2"
        return 0
    else
        echo -e "${RED}❌${NC} $2"
        return 1
    fi
}

check_python_module() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $2 installed"
        return 0
    else
        echo -e "${RED}❌${NC} $2 NOT installed"
        return 1
    fi
}

check_port() {
    if lsof -i :$1 >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} Port $1 is available"
        return 0
    else
        echo -e "${YELLOW}⚠️${NC}  Port $1 (service may be off)"
        return 1
    fi
}

PROJECT_DIR="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"

echo "📋 PROJECT STRUCTURE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_file "$PROJECT_DIR/main.py" "main.py"
check_file "$PROJECT_DIR/.env" ".env configuration"
check_file "$PROJECT_DIR/requirements.txt" "requirements.txt"
check_file "$PROJECT_DIR/src/orchestration/key_management_api.py" "key_management_api.py ← NEW"
check_file "$PROJECT_DIR/src/orchestration/elisya_endpoints.py" "elisya_endpoints.py ← NEW"
check_file "$PROJECT_DIR/src/graph/langgraph_workflow_v2.py" "langgraph_workflow_v2.py"
check_file "$PROJECT_DIR/src/orchestration/orchestrator_with_elisya.py" "orchestrator_with_elisya.py"
echo ""

echo "🔧 PYTHON DEPENDENCIES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_python_module "flask" "Flask"
check_python_module "flask_socketio" "SocketIO"
check_python_module "weaviate" "Weaviate"
check_python_module "ollama" "Ollama"
check_python_module "langgraph" "LangGraph"
check_python_module "dotenv" "Python-dotenv"
echo ""

echo "🌐 NETWORK SERVICES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  Flask Server:"
check_port 5001
echo ""
echo "8️⃣  Weaviate (Docker):"
check_port 8080
echo ""
echo "🔟 Ollama LLM:"
check_port 11434
echo ""
echo "6️⃣  Qdrant (Docker):"
check_port 6333
echo ""

echo "📊 CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if grep -q "WEAVIATE_URL" "$PROJECT_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Weaviate URL configured"
else
    echo -e "${YELLOW}⚠️${NC}  Weaviate URL not found"
fi

if grep -q "OPENROUTER_KEY_1" "$PROJECT_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} OpenRouter keys configured (9)"
else
    echo -e "${YELLOW}⚠️${NC}  OpenRouter keys not configured"
fi

if grep -q "GEMINI_API_KEY" "$PROJECT_DIR/.env" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Gemini API key configured"
else
    echo -e "${YELLOW}⚠️${NC}  Gemini API key not configured"
fi
echo ""

echo "✅ VERIFICATION COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🚀 READY TO LAUNCH?"
echo ""
echo "   cd $PROJECT_DIR"
echo "   source .venv/bin/activate"
echo "   python3 main.py"
echo ""
echo "🌐 Then access:"
echo "   • Web UI: http://localhost:5001"
echo "   • API Base: http://localhost:5001/api"
echo ""
echo "════════════════════════════════════════════════════════════════"
