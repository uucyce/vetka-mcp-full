@echo off
REM 🚀 VETKA Live 0.3 - Quick Setup for Windows
REM Быстрый запуск профессионального установщика

title VETKA Live 0.3 - Professional Setup

echo.
echo 🌳 VETKA Live 0.3 - Professional Setup
echo ======================================
echo.

REM Проверяем Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не найден. Установите Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python найден
python --version

echo.
echo 🚀 Запуск профессионального установщика...
python install_vetka.py

echo.
echo 🎉 Установка завершена!
echo 📁 Проверьте выбранную директорию для запуска VETKA
pause
