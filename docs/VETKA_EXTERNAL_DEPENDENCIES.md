# VETKA External Dependencies

**Installation guide for all VETKA public repositories.**

> **Note:** This document maps each GitHub repo → its dependencies. Use as reference for any human or AI agent setting up VETKA modules.

---

## Quick Summary

| Repo | Language | Core Dependencies | Optional |
|------|----------|-------------------|----------|
| **vetka-mcp-full** | Python | Docker, Python 3.10+ | Ollama |
| **vetka-mcp-core** | Python | Docker, Python 3.10+ | — |
| **vetka-memory-stack** | Python | Qdrant (Docker), Python 3.10+ | Ollama |
| **vetka-search-retrieval** | Python | Qdrant (Docker), Python 3.10+ | Weaviate |
| **vetka-orchestration-core** | Python | Python 3.10+ | — |
| **vetka-elisya-runtime** | Python | Python 3.10+ | Ollama |
| **vetka-ingest-engine** | Python | Python 3.10+ | Qdrant |
| **vetka-bridge-core** | Python | Python 3.10+ | — |
| **vetka-agents** | Python | Python 3.10+ | — |
| **vetka-taskboard** | Python | Python 3.10+ | — |
| **vetka-parallax** | Python | Python 3.10+ | — |
| **reflex-tool-engine** | Python | Python 3.10+ | — |
| **mycelium** | TypeScript | Node.js 18+, npm | — |
| **vetka-chat-ui** | TypeScript | Node.js 18+, npm | — |
| **vetka-cut** | TypeScript | Node.js 18+, npm | — |
| **pulse** | TypeScript | Node.js 18+, npm, Tauri | MediaPipe |
| **back_to_ussr** | Swift | Xcode 13+ | — |

---

## 1. Common Infrastructure

### Docker (Required for most modules)

```bash
# macOS
brew install --cask docker

# Linux
curl -fsSL https://get.docker.com | sh
```

### Qdrant (Vector DB)

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

### Ollama (Local LLM)

```bash
# macOS
brew install ollama

# Pull models
ollama pull nomic-embed-text  # embeddings
ollama pull llama3.2          # chat
```

---

## 2. Python Modules

### Core Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pydantic>=2.0 httpx>=0.25.0 python-dotenv>=1.0.0
```

### Per-Repo Dependencies

#### vetka-mcp-full
```bash
# Complete MCP server - all modules bundled
pip install qdrant-client>=1.10.0 networkx>=3.0 langchain-core>=0.1.0
# Or from repo:
git clone https://github.com/danilagoleen/vetka-mcp-full
cd vetka-mcp-full && pip install -r requirements.txt
```

#### vetka-mcp-core
```bash
git clone https://github.com/danilagoleen/vetka-mcp-core
cd vetka-mcp-core
pip install -r requirements.txt
```

#### vetka-memory-stack
```bash
git clone https://github.com/danilagoleen/vetka-memory-stack
cd vetka-memory-stack
pip install qdrant-client>=1.10.0 numpy>=2.0.0 scikit-learn>=1.4.0
# Requires: Qdrant running on localhost:6333
```

#### vetka-search-retrieval
```bash
git clone https://github.com/danilagoleen/vetka-search-retrieval
cd vetka-search-retrieval
pip install qdrant-client>=1.10.0 weaviate-client>=4.0.0
```

#### vetka-orchestration-core
```bash
git clone https://github.com/danilagoleen/vetka-orchestration-core
cd vetka-orchestration-core
pip install networkx>=3.0 langchain-core>=0.1.0
```

#### vetka-elisya-runtime
```bash
git clone https://github.com/danilagoleen/vetka-elisya-runtime
cd vetka-elisya-runtime
pip install httpx>=0.25.0 pydantic>=2.0
# Optional: Ollama for local fallback
```

#### vetka-ingest-engine
```bash
git clone https://github.com/danilagoleen/vetka-ingest-engine
cd vetka-ingest-engine
pip install -r requirements.txt
```

#### vetka-bridge-core
```bash
git clone https://github.com/danilagoleen/vetka-bridge-core
cd vetka-bridge-core
pip install -r requirements.txt
```

#### vetka-agents
```bash
git clone https://github.com/danilagoleen/vetka-agents
cd vetka-agents
pip install -r requirements.txt
```

#### vetka-taskboard
```bash
git clone https://github.com/danilagoleen/vetka-taskboard
cd vetka-taskboard
pip install -r requirements.txt
```

#### vetka-parallax
```bash
git clone https://github.com/danilagoleen/vetka-parallax
cd vetka-parallax
pip install -r requirements.txt
```

#### reflex-tool-engine
```bash
git clone https://github.com/danilagoleen/reflex-tool-engine
cd reflex-tool-engine
pip install -r requirements.txt
```

---

## 3. TypeScript/Node.js Modules

### Core Setup

```bash
# Install Node.js 18+
brew install node

# Verify
node --version  # Should be 18+
npm --version
```

### Per-Repo Setup

#### mycelium
```bash
git clone https://github.com/danilagoleen/mycelium
cd mycelium
npm install
npm run dev
```

#### vetka-chat-ui
```bash
git clone https://github.com/danilagoleen/vetka-chat-ui
cd vetka-chat-ui
npm install
npm run dev
```

#### vetka-cut
```bash
git clone https://github.com/danilagoleen/vetka-cut
cd vetka-cut
npm install
npm run dev
```

#### pulse
```bash
git clone https://github.com/danilagoleen/pulse
cd pulse
npm install
# Requires: Tauri CLI
npm run tauri dev
# Optional: MediaPipe for gesture recognition
```

---

## 4. Native Apps

### back_to_ussr (macOS menu-bar VPN)
```bash
# Requires: Xcode 13+ (Intel Mac, macOS 11+)
git clone https://github.com/danilagoleen/back_to_ussr
cd back_to_ussr
# Open in Xcode and build
# Or: xcodebuild -scheme back_to_ussr -configuration Debug
```

---

## 5. Environment Variables

```bash
# Core
export VETKA_QDRANT_URL=http://localhost:6333
export VETKA_WEAVIATE_URL=http://localhost:8080
export OLLAMA_BASE_URL=http://localhost:11434

# Optional: API keys for cloud LLMs
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## 6. Quick Start Commands

### Full MCP Stack
```bash
# 1. Start infrastructure
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant

# 2. Clone and install
git clone https://github.com/danilagoleen/vetka-mcp-full
cd vetka-mcp-full
pip install -r requirements.txt

# 3. Run
python -m src.server
```

### UI Only (React)
```bash
git clone https://github.com/danilagoleen/mycelium
cd mycelium && npm install && npm run dev
```

---

## 7. Troubleshooting

### Qdrant not responding
```bash
docker logs qdrant
docker restart qdrant
```

### Python import errors
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Node.js module errors
```bash
rm -rf node_modules package-lock.json
npm install
```

---

## Related Docs

- [vetka-mcp-full](https://github.com/danilagoleen/vetka-mcp-full)
- [mycelium](https://github.com/danilagoleen/mycelium)
- [Qdrant Docs](https://qdrant.tech/documentation/)
- [Ollama Docs](https://github.com/ollama/ollama)

---

*Last updated: 2026-04-09*
*Source: github.com/danilagoleen*