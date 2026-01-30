#!/bin/bash
# VETKA Phase 8.0 - Quick System Check
# Run: ./setup/quick_check.sh

echo "========================================"
echo "  VETKA QUICK CHECK"
echo "========================================"

# Activate venv
source .venv/bin/activate 2>/dev/null || {
    echo "[X] Virtual environment not found!"
    echo "    Run: python3 -m venv .venv && source .venv/bin/activate"
    exit 1
}
echo "[+] Virtual environment active"

# Check Python
python3 --version
echo "[+] Python OK"

# Check Ollama
curl -s http://localhost:11434/api/tags > /dev/null && echo "[+] Ollama running" || echo "[X] Ollama NOT running - start with: ollama serve"

# Check Qdrant
curl -s http://localhost:6333/health > /dev/null && echo "[+] Qdrant running" || echo "[!] Qdrant not running (optional)"

# Check Weaviate
curl -s http://localhost:8080/v1/.well-known/ready > /dev/null && echo "[+] Weaviate running" || echo "[!] Weaviate not running (optional)"

# Test imports
python3 -c "from flask import Flask; from src.orchestration.memory_manager import MemoryManager; print('[+] Core imports OK')" 2>/dev/null || echo "[X] Import errors"

echo ""
echo "To run VETKA:"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""
echo "For full diagnostics:"
echo "  python diagnostics/system_check.py -v"
echo "========================================"
