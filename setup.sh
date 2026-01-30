#!/bin/bash
# 🚀 VETKA Live 0.3 - Quick Setup
# Быстрый запуск профессионального установщика

echo "🌳 VETKA Live 0.3 - Professional Setup"
echo "======================================"

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8+"
    exit 1
fi

echo "✅ Python найден: $(python3 --version)"

# Запускаем установщик
echo "🚀 Запуск профессионального установщика..."
python3 install_vetka.py

echo ""
echo "🎉 Установка завершена!"
echo "📁 Проверьте выбранную директорию для запуска VETKA"
