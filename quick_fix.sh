#!/bin/bash
# 🚀 VETKA Live 0.3 - Quick Fix Script
# Быстрое исправление и запуск

echo "🚀 VETKA Live 0.3 - Quick Fix"
echo "============================"

# Удаляем проблемное виртуальное окружение
echo "🗑️ Очистка..."
rm -rf .venv

# Создаем новое
echo "📦 Создание виртуального окружения..."
python3 -m venv .venv

# Активируем
echo "🔧 Активация..."
source .venv/bin/activate

# Устанавливаем минимальные зависимости
echo "📥 Установка минимальных зависимостей..."
pip install --upgrade pip
pip install -r requirements_minimal.txt

# Создаем .env
echo "⚙️ Создание конфигурации..."
cat > .env << 'EOF'
# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=

# Ollama
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=embeddinggemma:300m
VECTOR_SIZE=768

# OpenRouter Keys
OPENROUTER_KEY_1=
OPENROUTER_KEY_2=
OPENROUTER_KEY_3=

# Gemini
GEMINI_API_KEY=

# Flask
FLASK_PORT=5000
FLASK_DEBUG=True
EOF

echo "✅ Готово! Запускаем VETKA..."
echo "🌐 Откройте: http://localhost:5000"
echo ""

# Запускаем
python main.py
