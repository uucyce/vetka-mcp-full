# 🌳 VETKA Live 0.3

**Advanced Complete Prompt for Cursor - Production-Ready System**

VETKA Live 0.3 is a sophisticated knowledge tree system with LangGraph orchestration, Weaviate memory, Elisya context management, and 3D visualization.

## 🎯 Core Architecture

### Technology Stack
- **Orchestration**: LangGraph 1.0 (state graphs, conditional edges, checkpoints)
- **Agents**: CrewAI 0.201.1 (as executor nodes in graphs)
- **Memory**: Weaviate (localhost:8080) with hybrid search
- **Context**: Elisya AI (decision tree for token management)
- **LLM Router**: Custom OpenRouter rotation + Ollama fallback
- **Backend**: Flask + SocketIO (port 5000)
- **Frontend**: Three.js + D3.js + 3d-force-graph (3D tree visualization)
- **Embeddings**: Ollama embeddinggemma:300m (768d vectors)

### Design Principles
- **Modular**: <500 lines per file
- **Resilient**: Try-except on all external calls, graceful fallbacks
- **Stateful**: LangGraph checkpoints in Weaviate
- **Context-aware**: Elisya limits tokens based on visible UI branches
- **Visual**: Real-time 3D tree updates via SocketIO
- **Testable**: pytest for each component

## 🚀 Профессиональная установка - Рекомендуется!

### 🎯 Изолированная среда без конфликтов:

```bash
# Профессиональная установка (любая ОС)
python install_vetka.py
```

**Или через скрипты:**
```bash
./setup.sh          # macOS/Linux
setup.bat           # Windows
```

### 🔧 Что дает профессиональная установка:

✅ **Изолированная среда** - отдельный .venv без конфликтов  
✅ **Выбор пути** - устанавливается куда хотите  
✅ **Полная конфигурация** - все зависимости правильно  
✅ **Портативность** - можно перемещать установку  
✅ **Легкое управление** - простое обновление/удаление  

### 🚀 Быстрый запуск (альтернатива):

**macOS/Linux:**
```bash
./quick_start.sh
```

**Windows:**
```cmd
run_vetka.bat
```

**Универсальный:**
```bash
python launch_vetka.py
```

### 🎮 Что происходит автоматически:

1. ✅ **Проверка Python** - убеждается что Python 3.8+ установлен
2. 📦 **Виртуальное окружение** - создает `.venv` если не существует  
3. 📥 **Зависимости** - устанавливает все Python пакеты
4. 🎨 **Frontend** - устанавливает Node.js зависимости
5. ⚙️ **Конфигурация** - создает `.env` файл с настройками
6. 🐳 **Weaviate** - запускает в Docker
7. 🤖 **Ollama** - запускает и загружает модели
8. 🌳 **VETKA** - запускает основное приложение

### 🌐 После запуска:

- **Главная страница**: http://localhost:5000
- **Проверка здоровья**: http://localhost:5000/api/health
- **3D визуализация**: автоматически загружается

### 🎮 Команды для тестирования:

```
/bot/create API          # Создать API через LangGraph workflow
/bot/analyze code        # Анализ кода  
/visual/tree            # Обновить 3D визуализацию
/search/query           # Поиск в памяти
```

### ⌨️ Горячие клавиши:

- `/` - фокус на ввод команды
- `1-5` - смена режимов визуализации (ABC, 🕒, 🔥, 🔗, 🌿)
- `g` - глобальный вид
- `t` - вид дерева
- `l` - вид листьев
- `Esc` - закрыть панель артефактов

## 🧪 Testing

Run the test suite:
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python tests/test_weaviate.py
python tests/test_agents.py
python tests/test_langgraph.py
python tests/test_api.py
```

## 🎮 Usage

### Commands
- `/bot/create API` - Create new feature using LangGraph workflow
- `/bot/analyze code` - Analyze existing code
- `/visual/tree` - Update 3D visualization
- `/search/query` - Search memory
- `/code/complete` - Code completion

### 3D Visualization Modes
- **ABC** - Sort by name (alphabetical)
- **🕒** - Sort by date (chronological)
- **🔥** - Heat map by activity
- **🔗** - Show only connected nodes (like Obsidian graph)
- **🌿** - Linear branch view (Gantt-like)

### Navigation
- **Mouse wheel** - Zoom in/out
- **Click nodes** - Open artifact panel
- **Keyboard shortcuts**:
  - `/` - Focus command input
  - `1-5` - Switch visualization modes
  - `g` - Global view
  - `t` - Tree view
  - `l` - Leaf view
  - `Esc` - Close artifact panel

## 🏗️ Project Structure

```
vetka_live_03/
├── .env                          # API keys, config
├── requirements.txt              # Python dependencies
├── constitution.md               # System rules
├── main.py                       # Flask app entry point
│
├── config/
│   ├── config.py                 # All constants, model pools, icons
│
├── src/
│   ├── agents/                   # All VETKA agents
│   │   ├── base_agent.py        # BaseAgent with LLM rotation
│   │   ├── vetka_pm.py          # Product Manager
│   │   ├── vetka_architect.py   # System Architect
│   │   ├── vetka_dev.py         # Developer
│   │   ├── vetka_qa.py          # QA Engineer
│   │   ├── vetka_ops.py         # DevOps
│   │   └── vetka_visual.py      # 3D Visualization
│   │
│   ├── memory/
│   │   └── weaviate_helper.py   # Weaviate CRUD, hybrid search
│   │
│   ├── workflows/
│   │   ├── router.py            # Smart command router
│   │   └── langgraph_builder.py # Graph construction utils
│   │
├── elisya_integration/
│   └── context_manager.py       # Elisya decision tree for context
│
├── langgraph_flows/
│   ├── feature_development.py   # Sequential: PM→Arch→Dev→QA→Ops
│   └── self_improvement.py      # Hierarchical: monitor→fix loop
│
├── frontend/
│   ├── templates/
│   │   └── index.html           # Main UI layout
│   └── static/
│       ├── css/style.css        # Dark theme, minimal
│       ├── js/
│       │   ├── tree_view.js     # Three.js 3D tree
│       │   ├── zoom_manager.js  # LOD + context calculation
│       │   ├── artifact_panel.js # File preview
│       │   └── socket_handler.js # SocketIO client
│       └── package.json         # Frontend dependencies
│
└── tests/
    ├── test_weaviate.py         # Connection, CRUD tests
    ├── test_agents.py           # Agent rotation, fallbacks
    ├── test_langgraph.py        # Graph execution
    └── test_api.py              # Flask endpoints
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=

# Ollama
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=embeddinggemma:300m
VECTOR_SIZE=768

# OpenRouter Keys (rotation pool)
OPENROUTER_KEY_1=your_key_1
OPENROUTER_KEY_2=your_key_2
# ... up to OPENROUTER_KEY_9

# Gemini (backup)
GEMINI_API_KEY=your_gemini_key

# Flask
FLASK_PORT=5000
FLASK_DEBUG=True
```

### Model Configuration
The system uses a tiered model routing approach:
- **Premium**: Claude-3.5-Sonnet, GPT-4-Turbo (architecture, complex debugging)
- **Mid**: DeepSeek, Llama-3.1-70B (feature implementation, refactoring)
- **Local**: DeepSeek-Coder, Llama-3.1-8B, Qwen2 (code completion, simple fixes)

## 🤖 Agents

### VETKA-PM (Product Manager)
- **Role**: Planning and prioritization
- **Context**: 1024 tokens
- **Models**: Llama-3.1-8B

### VETKA-Architect (System Architect)
- **Role**: Design architecture
- **Context**: 1024 tokens
- **Models**: Qwen2-7B, Llama-3.1-8B

### VETKA-Dev (Developer)
- **Role**: Implement features
- **Context**: 2048 tokens
- **Models**: DeepSeek-Coder-6.7B, Qwen2-7B

### VETKA-QA (QA Engineer)
- **Role**: Testing and validation
- **Context**: 1024 tokens
- **Models**: Llama-3.1-8B

### VETKA-Ops (DevOps)
- **Role**: Deployment and monitoring
- **Context**: 1024 tokens
- **Models**: Llama-3.1-8B

### VETKA-Visual (3D Visualization)
- **Role**: Visual representation
- **Context**: 1024 tokens
- **Models**: Llama-3.1-8B

## 🌐 API Endpoints

- `GET /` - Main UI
- `GET /api/health` - Health check
- `GET /api/init` - Initialize tree structure
- `GET /api/tree/<zoom_level>` - Get tree data for zoom level

### SocketIO Events
- `command` - Send command to system
- `zoom_changed` - Zoom level change
- `node_clicked` - Node interaction
- `artifact_message` - Chat on artifacts

## 🐛 Troubleshooting

### Common Issues

1. **Weaviate Connection Failed**
   ```bash
   # Check if Weaviate is running
   curl http://localhost:8080/v1/meta
   
   # Start with Docker
   docker run -p 8080:8080 semitechnologies/weaviate:latest
   ```

2. **Ollama Connection Failed**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # Start Ollama
   ollama serve
   ```

3. **Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

4. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Performance Optimization

For M4 Pro Mac:
```bash
# Force CPU usage for Ollama if MPS hangs
export OLLAMA_DEVICE=cpu
```

## 📚 Documentation

- [Constitution](constitution.md) - System rules and principles
- [Configuration](config/config.py) - All settings and constants
- [Tests](tests/) - Test suite for all components

## 🤝 Contributing

1. Follow the modular design (<500 lines per file)
2. Add tests for new functionality
3. Update documentation
4. Follow the constitution principles

## 📄 License

MIT License - see LICENSE file for details.

## 🎉 Getting Started

1. **Start the system:**
   ```bash
   python main.py
   ```

2. **Open browser:**
   ```
   http://localhost:5000
   ```

3. **Try commands:**
   - Type `/bot/create API` to see the LangGraph workflow
   - Click nodes to explore artifacts
   - Use the mode buttons (ABC, 🕒, 🔥, 🔗, 🌿) to change visualization

4. **Watch the 3D tree grow!** 🌳

---

**VETKA Live 0.3** - Where knowledge grows like a living tree! 🌱
