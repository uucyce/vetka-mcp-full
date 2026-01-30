#!/bin/bash
# VETKA - Quick Start Script (FastAPI)
# Phase 39.8 - Production Ready

echo "VETKA - Quick Start (FastAPI)"
echo "=============================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8+"
    exit 1
fi

# Создание и активация виртуального окружения
if [ ! -d ".venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv .venv
fi

echo "🔧 Активация виртуального окружения..."
source .venv/bin/activate

# Установка зависимостей
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# Frontend зависимости
if command -v npm &> /dev/null && [ -d "frontend" ]; then
    echo "🎨 Установка frontend зависимостей..."
    cd frontend && npm install --silent && cd ..
fi

# Создание .env файла
if [ ! -f ".env" ]; then
    echo "⚙️ Создание конфигурации..."
    cat > .env << 'EOF'
# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=

# Ollama
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=embeddinggemma:300m
VECTOR_SIZE=768

# OpenRouter Keys (добавьте свои ключи)
OPENROUTER_KEY_1sk-or-v1-08b39403601eca10edd73e28b336fa900996a56ba6e231057cdd8d5efb39b296=
OPENROUTER_KEY_2sk-or-v1-2335b0236e5e8021368a599a2ddf535bc920b3f8e34d172e0b2cfb0320698dcd=
OPENROUTER_KEY_3=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

# Gemini (backup)
GEMINI_API_KEY=

# VETKA (FastAPI)
VETKA_PORT=5001
VETKA_DEBUG=True
EOF
    echo "✅ .env файл создан - добавьте свои API ключи"
fi

# Запуск сервисов
echo "🚀 Запуск сервисов..."

# Weaviate
if command -v docker &> /dev/null; then
    if ! curl -s http://localhost:8080/v1/meta > /dev/null 2>&1; then
        echo "🐳 Запуск Weaviate..."
        docker run -d --name vetka-weaviate -p 8080:8080 semitechnologies/weaviate:latest
        sleep 5
    fi
fi

# Ollama
if command -v ollama &> /dev/null; then
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "🤖 Запуск Ollama..."
        ollama serve &
        sleep 3
    fi
    
    echo "📥 Загрузка моделей..."
    ollama pull embeddinggemma:300m > /dev/null 2>&1 &
    ollama pull llama3.1:8b > /dev/null 2>&1 &
fi

echo ""
echo "Ready! Starting VETKA FastAPI..."
echo "API: http://localhost:5001"
echo "Docs: http://localhost:5001/docs"
echo "Stop: Ctrl+C"
echo ""

# Run VETKA (FastAPI + Socket.IO)
python3 main.py
