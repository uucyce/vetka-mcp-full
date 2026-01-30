@echo off
REM 🌳 VETKA Live 0.3 - One-Click Launch Script for Windows
REM Автоматический запуск системы VETKA для Windows

title VETKA Live 0.3 - One-Click Launch

echo.
echo 🌳 VETKA Live 0.3 - One-Click Launch
echo ==================================
echo.

REM Проверка Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не найден. Установите Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python найден

REM Создание виртуального окружения если не существует
if not exist ".venv" (
    echo ℹ️ Создание виртуального окружения...
    python -m venv .venv
    echo ✅ Виртуальное окружение создано
) else (
    echo ✅ Виртуальное окружение уже существует
)

REM Активация виртуального окружения
call .venv\Scripts\activate.bat
echo ✅ Виртуальное окружение активировано

REM Установка Python зависимостей
echo ℹ️ Установка Python зависимостей...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo ✅ Python зависимости установлены

REM Проверка Node.js и установка frontend зависимостей
node --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Node.js найден
    if exist "frontend" (
        echo ℹ️ Установка frontend зависимостей...
        cd frontend
        npm install --silent
        cd ..
        echo ✅ Frontend зависимости установлены
    )
) else (
    echo ⚠️ Node.js не найден. Frontend может не работать
)

REM Создание .env файла если не существует
if not exist ".env" (
    echo ℹ️ Создание .env файла...
    (
        echo # Weaviate
        echo WEAVIATE_URL=http://localhost:8080
        echo WEAVIATE_API_KEY=
        echo.
        echo # Ollama
        echo OLLAMA_URL=http://localhost:11434
        echo EMBEDDING_MODEL=embeddinggemma:300m
        echo VECTOR_SIZE=768
        echo.
        echo # OpenRouter Keys (добавьте свои ключи)
        echo OPENROUTER_KEY_1=
        echo OPENROUTER_KEY_2=
        echo OPENROUTER_KEY_3=
        echo.
        echo # Gemini (backup)
        echo GEMINI_API_KEY=
        echo.
        echo # Flask
        echo FLASK_PORT=5000
        echo FLASK_DEBUG=True
    ) > .env
    echo ✅ .env файл создан
    echo ⚠️ Добавьте свои API ключи в .env файл
) else (
    echo ✅ .env файл уже существует
)

REM Проверка Docker
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker найден
    echo ℹ️ Проверка Weaviate...
    curl -s http://localhost:8080/v1/meta >nul 2>&1
    if %errorlevel% neq 0 (
        echo ℹ️ Запуск Weaviate в Docker...
        docker run -d --name vetka-weaviate -p 8080:8080 -p 50051:50051 semitechnologies/weaviate:latest
        timeout /t 5 /nobreak >nul
        echo ✅ Weaviate запущен
    ) else (
        echo ✅ Weaviate уже запущен
    )
) else (
    echo ⚠️ Docker не найден. Запустите Weaviate вручную
)

REM Проверка Ollama
ollama --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama найден
    echo ℹ️ Проверка Ollama...
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% neq 0 (
        echo ℹ️ Запуск Ollama...
        start /b ollama serve
        timeout /t 3 /nobreak >nul
        echo ✅ Ollama запущен
    ) else (
        echo ✅ Ollama уже запущен
    )
    
    echo ℹ️ Загрузка моделей Ollama...
    ollama pull embeddinggemma:300m >nul 2>&1
    ollama pull llama3.1:8b >nul 2>&1
    ollama pull deepseek-coder:6.7b >nul 2>&1
    ollama pull qwen2:7b >nul 2>&1
    echo ✅ Модели Ollama загружены
) else (
    echo ⚠️ Ollama не найден. Установите Ollama для работы с локальными моделями
)

echo.
echo ✅ Все готово! Запускаем VETKA...
echo.
echo 🌐 Откройте в браузере: http://localhost:5000
echo 📊 Проверка здоровья: http://localhost:5000/api/health
echo.
echo 🎮 Команды для тестирования:
echo   /bot/create API
echo   /bot/analyze code
echo   /visual/tree
echo   /search/query
echo.
echo ⌨️ Горячие клавиши:
echo   / - фокус на ввод команды
echo   1-5 - смена режимов визуализации
echo   g - глобальный вид
echo   t - вид дерева
echo   l - вид листьев
echo.
echo 🛑 Для остановки закройте это окно
echo.

REM Запуск основного приложения
python main.py

pause
