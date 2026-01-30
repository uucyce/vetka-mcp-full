#!/bin/bash
# VETKA Phase 8.0 - Load Ollama Models
# Run: bash setup/load_models.sh

echo "========================================"
echo "  VETKA PHASE 8.0 - MODEL LOADER"
echo "========================================"
echo ""
echo "Make sure 'ollama serve' is running!"
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[X] Ollama is NOT running!"
    echo "    Start it with: ollama serve"
    exit 1
fi

echo "[+] Ollama is running"
echo ""

# Function to pull model if not exists
pull_if_needed() {
    local model=$1
    local description=$2

    # Check if model exists (base name match)
    base_name=$(echo $model | cut -d: -f1)
    if ollama list 2>/dev/null | grep -q "$base_name"; then
        echo "[+] $model - Already installed"
    else
        echo "[ ] $model - $description"
        echo "    Downloading..."
        ollama pull $model
        if [ $? -eq 0 ]; then
            echo "[+] $model - Downloaded!"
        else
            echo "[X] $model - FAILED (try manually: ollama pull $model)"
        fi
    fi
}

echo "REQUIRED MODELS:"
echo "----------------------------------------"

# 1. DeepSeek LLM (main reasoning)
pull_if_needed "deepseek-llm:7b" "Main reasoning model (4GB)"

# 2. Qwen2 (fast fallback)
pull_if_needed "qwen2:7b" "Fast fallback model (4GB)"

# 3. Embedding Gemma
pull_if_needed "embeddinggemma:300m" "Embedding model (600MB)"

# 4. Llama 3.1 (HOPE pattern / vision fallback)
pull_if_needed "llama3.1:8b" "HOPE pattern / vision fallback (5GB)"

echo ""
echo "OPTIONAL MODELS (enhanced capabilities):"
echo "----------------------------------------"

# Check for optional models availability and suggest
echo "To install optional models:"
echo "  ollama pull deepseek-coder:6.7b  # Code specialist (4GB)"
echo "  ollama pull mistral:7b           # General assistant (4GB)"
echo "  ollama pull nomic-embed-text     # Alternative embeddings (300MB)"
echo ""

# Note about Pixtral
echo "NOTE: Advanced vision model:"
echo "  - pixtral-12b: HuggingFace model at ~/pixtral-12b/"
echo "    Download: huggingface-cli download mistral-ai/Pixtral-12B-2409"
echo ""

echo "========================================"
echo "  DOWNLOAD COMPLETE"
echo "========================================"

# Show current models
echo ""
echo "Installed models:"
ollama list

echo ""
echo "To run VETKA:"
echo "  source .venv/bin/activate"
echo "  python main.py"
