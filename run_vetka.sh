#!/bin/bash
# 🌳 VETKA Live 0.3 - One-Click Launch Script
# Автоматический запуск системы VETKA

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

# Проверка Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_status "Python $PYTHON_VERSION найден"
        return 0
    else
        print_error "Python3 не найден. Установите Python 3.8+"
        exit 1
    fi
}

# Проверка и создание виртуального окружения
setup_venv() {
    if [ ! -d ".venv" ]; then
        print_info "Создание виртуального окружения..."
        python3 -m venv .venv
        print_status "Виртуальное окружение создано"
    else
        print_status "Виртуальное окружение уже существует"
    fi
    
    # Активация виртуального окружения
    source .venv/bin/activate
    print_status "Виртуальное окружение активировано"
}

# Установка Python зависимостей
install_python_deps() {
    print_info "Установка Python зависимостей..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_status "Python зависимости установлены"
}

# Проверка Node.js и установка frontend зависимостей
setup_frontend() {
    if command -v node &> /dev/null && command -v npm &> /dev/null; then
        print_status "Node.js и npm найдены"
        
        if [ -d "frontend" ]; then
            print_info "Установка frontend зависимостей..."
            cd frontend
            npm install --silent
            cd ..
            print_status "Frontend зависимости установлены"
        else
            print_warning "Папка frontend не найдена"
        fi
    else
        print_warning "Node.js или npm не найдены. Frontend может не работать"
    fi
}

# Создание .env файла если не существует
create_env() {
    if [ ! -f ".env" ]; then
        print_info "Создание .env файла..."
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

# Flask
FLASK_PORT=5000
FLASK_DEBUG=True
EOF
        print_status ".env файл создан"
        print_warning "Добавьте свои API ключи в .env файл"
    else
        print_status ".env файл уже существует"
    fi
}

# Проверка Docker
check_docker() {
    if command -v docker &> /dev/null; then
        print_status "Docker найден"
        return 0
    else
        print_warning "Docker не найден. Weaviate не будет запущен автоматически"
        return 1
    fi
}

# Запуск Weaviate в Docker
start_weaviate() {
    if check_docker; then
        print_info "Проверка Weaviate..."
        if curl -s http://localhost:8080/v1/meta > /dev/null 2>&1; then
            print_status "Weaviate уже запущен"
        else
            print_info "Запуск Weaviate в Docker..."
            docker run -d --name vetka-weaviate -p 8080:8080 -p 50051:50051 semitechnologies/weaviate:latest
            sleep 5
            print_status "Weaviate запущен"
        fi
    else
        print_warning "Запустите Weaviate вручную: docker run -p 8080:8080 semitechnologies/weaviate:latest"
    fi
}

# Проверка Ollama
check_ollama() {
    if command -v ollama &> /dev/null; then
        print_status "Ollama найден"
        return 0
    else
        print_warning "Ollama не найден. Установите Ollama для работы с локальными моделями"
        return 1
    fi
}

# Запуск Ollama
start_ollama() {
    if check_ollama; then
        print_info "Проверка Ollama..."
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            print_status "Ollama уже запущен"
        else
            print_info "Запуск Ollama..."
            ollama serve &
            sleep 3
            print_status "Ollama запущен"
        fi
        
        # Загрузка необходимых моделей
        print_info "Загрузка моделей Ollama..."
        ollama pull embeddinggemma:300m > /dev/null 2>&1 || print_warning "Не удалось загрузить embeddinggemma:300m"
        ollama pull llama3.1:8b > /dev/null 2>&1 || print_warning "Не удалось загрузить llama3.1:8b"
        ollama pull deepseek-coder:6.7b > /dev/null 2>&1 || print_warning "Не удалось загрузить deepseek-coder:6.7b"
        ollama pull qwen2:7b > /dev/null 2>&1 || print_warning "Не удалось загрузить qwen2:7b"
        print_status "Модели Ollama загружены"
    else
        print_warning "Запустите Ollama вручную: ollama serve"
    fi
}

# Запуск VETKA
start_vetka() {
    print_info "Запуск VETKA Live 0.3..."
    echo ""
    echo "🌐 Откройте в браузере: http://localhost:5000"
    echo "📊 Проверка здоровья: http://localhost:5000/api/health"
    echo ""
    echo "🎮 Команды для тестирования:"
    echo "  /bot/create API"
    echo "  /bot/analyze code"
    echo "  /visual/tree"
    echo "  /search/query"
    echo ""
    echo "⌨️ Горячие клавиши:"
    echo "  / - фокус на ввод команды"
    echo "  1-5 - смена режимов визуализации"
    echo "  g - глобальный вид"
    echo "  t - вид дерева"
    echo "  l - вид листьев"
    echo ""
    echo "🛑 Для остановки нажмите Ctrl+C"
    echo ""
    
    # Запуск основного приложения
    python main.py
}

# Очистка при выходе
cleanup() {
    echo ""
    print_info "Остановка VETKA..."
    # Остановка фоновых процессов
    jobs -p | xargs -r kill
    print_status "VETKA остановлен"
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
