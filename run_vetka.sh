#!/bin/bash
# VETKA Live 0.3 - One-Click Launch Script
# Automatic VETKA startup

set -e  # Остановить при ошибке

echo "🌳 VETKA Live 0.3 - One-Click Launch"
echo "=================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для цветного вывода
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Check Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_status "Python $PYTHON_VERSION найден"
        return 0
    else
        print_error "Python3 not found. Install Python 3.8+"
        exit 1
    fi
}

# Check and create virtual environment
setup_venv() {
    if [ ! -d ".venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv .venv
        print_status "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    print_status "Virtual environment activated"
}

# Install Python dependencies
install_python_deps() {
    print_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_status "Python dependencies installed"
}

# Check Node.js and install frontend dependencies
setup_frontend() {
    if command -v node &> /dev/null && command -v npm &> /dev/null; then
        print_status "Node.js and npm found"
        
        if [ -d "frontend" ]; then
            print_info "Installing frontend dependencies..."
            cd frontend
            npm install --silent
            cd ..
            print_status "Frontend dependencies installed"
        else
            print_warning "frontend directory not found"
        fi
    else
        print_warning "Node.js or npm not found. Frontend may not work"
    fi
}

# Create .env file if missing
create_env() {
    if [ ! -f ".env" ]; then
        print_info "Creating .env file..."
        cat > .env << EOF
# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=

# Ollama
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=embeddinggemma:300m
VECTOR_SIZE=768

# OpenRouter Keys (добавьте свои ключи)
OPENROUTER_KEY_1=
OPENROUTER_KEY_2=
OPENROUTER_KEY_3=

# Gemini (backup)
GEMINI_API_KEY=

# VETKA FastAPI
VETKA_HOST=0.0.0.0
VETKA_PORT=5001
VETKA_RELOAD=false

# Phase 157.1 - Context Packer / JEPA profile
VETKA_CONTEXT_PACKER_ENABLED=true
VETKA_CONTEXT_PACKER_JEPA_ENABLE=true
VETKA_CONTEXT_PACKER_TOKEN_PRESSURE=0.80
VETKA_CONTEXT_PACKER_DOCS_THRESHOLD=18
VETKA_CONTEXT_PACKER_ENTROPY_THRESHOLD=2.50
VETKA_CONTEXT_PACKER_MODALITY_THRESHOLD=2
VETKA_CONTEXT_PACKER_HYSTERESIS_ON=3
VETKA_CONTEXT_PACKER_HYSTERESIS_OFF=2
VETKA_CONTEXT_PACKER_RECENT_MAX=300
EOF
        print_status ".env file created"
        print_warning "Add your API keys to .env"
    else
        print_status ".env file already exists"
    fi
}

# Check Docker
check_docker() {
    if command -v docker &> /dev/null; then
        print_status "Docker found"
        return 0
    else
        print_warning "Docker not found. Weaviate will not start automatically"
        return 1
    fi
}

# Start Weaviate in Docker
start_weaviate() {
    if check_docker; then
        print_info "Checking Weaviate..."
        if curl -s http://localhost:8080/v1/meta > /dev/null 2>&1; then
            print_status "Weaviate already running"
        else
            print_info "Starting Weaviate in Docker..."
            docker run -d --name vetka-weaviate -p 8080:8080 -p 50051:50051 semitechnologies/weaviate:latest
            sleep 5
            print_status "Weaviate started"
        fi
    else
        print_warning "Start Weaviate manually: docker run -p 8080:8080 semitechnologies/weaviate:latest"
    fi
}

# Check Ollama
check_ollama() {
    if command -v ollama &> /dev/null; then
        print_status "Ollama found"
        return 0
    else
        print_warning "Ollama not found. Install it for local models"
        return 1
    fi
}

# Start Ollama
start_ollama() {
    if check_ollama; then
        print_info "Checking Ollama..."
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            print_status "Ollama already running"
        else
            print_info "Starting Ollama..."
            ollama serve &
            sleep 3
            print_status "Ollama started"
        fi
        
        # Pull key models
        print_info "Pulling Ollama models..."
        ollama pull embeddinggemma:300m > /dev/null 2>&1 || print_warning "Failed to pull embeddinggemma:300m"
        ollama pull llama3.1:8b > /dev/null 2>&1 || print_warning "Failed to pull llama3.1:8b"
        ollama pull deepseek-coder:6.7b > /dev/null 2>&1 || print_warning "Failed to pull deepseek-coder:6.7b"
        ollama pull qwen2:7b > /dev/null 2>&1 || print_warning "Failed to pull qwen2:7b"
        print_status "Ollama models pulled"
    else
        print_warning "Start Ollama manually: ollama serve"
    fi
}

# Start VETKA
start_vetka() {
    print_info "Starting VETKA Live 0.3..."
    echo ""
    echo "Open in browser: http://localhost:5001"
    echo "Health check: http://localhost:5001/api/health"
    echo ""
    echo "Test commands:"
    echo "  /bot/create API"
    echo "  /bot/analyze code"
    echo "  /visual/tree"
    echo "  /search/query"
    echo ""
    echo "Hotkeys:"
    echo "  / - фокус на ввод команды"
    echo "  1-5 - смена режимов визуализации"
    echo "  g - глобальный вид"
    echo "  t - вид дерева"
    echo "  l - вид листьев"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Запуск основного приложения через единый entrypoint.
    # Это гарантирует одинаковый JEPA autostart path (run.sh + main.py).
    ./run.sh
}

# Cleanup on exit
cleanup() {
    echo ""
    print_info "Stopping VETKA..."
    # Stop background processes
    jobs -p | xargs -r kill
    print_status "VETKA stopped"
}

# Установка обработчика сигналов
trap cleanup EXIT INT TERM

# Основная функция
main() {
    echo "🚀 Начинаем запуск VETKA..."
    echo ""
    
    # Проверки и настройка
    check_python
    setup_venv
    install_python_deps
    setup_frontend
    create_env
    
    # Запуск сервисов
    start_weaviate
    start_ollama
    
    echo ""
    print_status "Все готово! Запускаем VETKA..."
    echo ""
    
    # Запуск VETKA
    start_vetka
}

# Запуск основной функции
main "$@"
