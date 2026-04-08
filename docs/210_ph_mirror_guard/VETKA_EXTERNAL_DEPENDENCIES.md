# VETKA External Dependencies

**Required infrastructure components for running VETKA modules.**

> **Note:** This is a living document. Some components are optional depending on your use case.

---

## Quick Summary

| Component | Required For | Type | Install |
|-----------|-------------|------|---------|
| **Qdrant** | Memory stack, Semantic search | Vector DB | Docker |
| **Weaviate** | Alternative vector DB | Vector DB | Docker |
| **Ollama** | Local LLM inference | LLM Runtime | Homebrew/Docker |
| **Docker** | All containerized services | Container Runtime | Required |
| **Python 3.10+** | All Python modules | Runtime | Required |
| **Node.js 18+** | React UI (mycelium, chat-ui) | Runtime | Optional |

---

## 1. Docker (Required)

**Purpose:** Runs Qdrant, Weaviate, and other services.

### macOS
```bash
# Install Docker Desktop
brew install --cask docker

# Or download from https://docker.com
```

### Linux
```bash
curl -fsSL https://get.docker.com | sh
```

---

## 2. Qdrant (Recommended)

**Purpose:** Vector database for memory stack and semantic search.

### With Docker
```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

### Verify
```bash
curl http://localhost:6333/health
# Should return: {"status":"ok"}
```

### Environment Variable
```bash
export VETKA_QDRANT_URL=http://localhost:6333
```

---

## 3. Weaviate (Alternative)

**Purpose:** Alternative vector database for hybrid search.

### With Docker
```bash
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -e QUERY_MAXIMUM_RESULTS=100 \
  semitechnologies/weaviate:latest
```

### Environment Variable
```bash
export VETKA_WEAVIATE_URL=http://localhost:8080
```

---

## 4. Ollama (Optional)

**Purpose:** Local LLM inference for development/testing.

### macOS
```bash
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Pull Models
```bash
# For embeddings
ollama pull nomic-embed-text

# For chat
ollama pull llama3.2
ollama pull qwen2.5
```

### Verify
```bash
ollama list
```

### Environment Variable
```bash
export OLLAMA_BASE_URL=http://localhost:11434
```

---

## 5. Python Dependencies

### Core (all modules)
```bash
pip install pydantic>=2.0 httpx>=0.25.0 python-dotenv>=1.0.0
```

### Memory Stack
```bash
pip install qdrant-client>=1.10.0 weaviate-client>=4.0.0 numpy>=2.0.0 scikit-learn>=1.4.0
```

### Search & Retrieval
```bash
pip install qdrant-client>=1.10.0
```

### Orchestration
```bash
pip install networkx>=3.0 langchain-core>=0.1.0
```

---

## 6. Node.js (for UI modules)

### macOS
```bash
brew install node
```

### Verify
```bash
node --version  # Should be 18+
npm --version
```

### For React UI
```bash
cd client
npm install
```

---

## 7. Complete Setup Script

```bash
#!/bin/bash
# VETKA External Dependencies Setup

echo "Installing VETKA external dependencies..."

# 1. Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    # Add your platform-specific Docker install here
fi

# 2. Qdrant
if ! docker ps | grep -q qdrant; then
    echo "Starting Qdrant..."
    docker run -d \
        --name qdrant \
        -p 6333:6333 \
        -p 6334:6334 \
        -v qdrant_storage:/qdrant/storage \
        qdrant/qdrant
fi

# 3. Ollama (optional)
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found (optional)"
else
    echo "Installing Ollama models..."
    ollama pull nomic-embed-text
fi

echo "✅ Setup complete!"
echo "Qdrant: http://localhost:6333"
echo "Ollama: http://localhost:11434"
```

---

## 8. Module-Specific Requirements

### vetka-mcp-full (Complete MCP)
```
Core:       Python 3.10+, pip
Vector DB:  Qdrant or Weaviate (Docker)
Optional:   Ollama for local inference
```

### vetka-memory-stack
```
Vector DB:  Qdrant (Docker) — REQUIRED
Embedding:  OpenAI, or Ollama (nomic-embed-text)
```

### vetka-search-retrieval
```
Vector DB:  Qdrant (Docker) — REQUIRED
```

### vetka-orchestration-core
```
Python:     3.10+
Graph:      networkx
Pipeline:   langchain-core
```

### mycelium / vetka-chat-ui
```
Node.js:    18+
React:      via npm install
Backend:    Python + FastAPI
```

---

## 9. Troubleshooting

### Qdrant not starting
```bash
# Check logs
docker logs qdrant

# Restart
docker restart qdrant
```

### Ollama not responding
```bash
# Check if running
ollama serve

# Or restart
pkill ollama && ollama serve
```

### Python import errors
```bash
# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install deps
pip install -r requirements.txt
```

---

## Related Docs

- [VETKA MCP Full README](https://github.com/danilagoleen/vetka-mcp-full)
- [Docker Getting Started](https://docs.docker.com/get-started/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Ollama Documentation](https://github.com/ollama/ollama)

---

*Last updated: 2026-04-09*
