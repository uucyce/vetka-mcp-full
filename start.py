#!/usr/bin/env python3
"""
🌳 VETKA Live 0.3 - Ultimate One-Click Launcher
Универсальный лаунчер для любой платформы
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def main():
    """Главная функция запуска"""
    print("🌳 VETKA Live 0.3 - Ultimate Launcher")
    print("=" * 40)
    
    # Определяем платформу и выбираем подходящий скрипт
    system = platform.system().lower()
    
    if system == "windows":
        print("🪟 Запуск для Windows...")
        if Path("run_vetka.bat").exists():
            subprocess.run(["run_vetka.bat"], shell=True)
        else:
            print("❌ run_vetka.bat не найден")
            sys.exit(1)
    
    elif system in ["darwin", "linux"]:  # macOS или Linux
        print("🐧 Запуск для Unix-систем...")
        if Path("quick_start.sh").exists():
            # Делаем скрипт исполняемым
            os.chmod("quick_start.sh", 0o755)
            subprocess.run(["./quick_start.sh"])
        else:
            print("❌ quick_start.sh не найден")
            sys.exit(1)
    
    else:
        print("🤖 Неизвестная платформа, используем универсальный Python скрипт...")
        if Path("launch_vetka.py").exists():
            subprocess.run([sys.executable, "launch_vetka.py"])
        else:
            print("❌ launch_vetka.py не найден")
            sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Запуск прерван пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)
