#!/usr/bin/env python3
"""
🌳 VETKA Live 0.3 - Universal One-Click Launch Script
Универсальный скрипт для запуска VETKA на любой платформе
"""

import os
import sys
import subprocess
import time
import platform
import requests
from pathlib import Path

class Colors:
    """Цвета для консольного вывода"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color

def print_banner():
    """Печать баннера VETKA"""
    banner = f"""
{Colors.CYAN}🌳 VETKA Live 0.3 - Universal Launch Script{Colors.NC}
{Colors.CYAN}{'=' * 50}{Colors.NC}
{Colors.WHITE}Платформа: {platform.system()} {platform.release()}{Colors.NC}
{Colors.WHITE}Python: {sys.version.split()[0]}{Colors.NC}
{Colors.WHITE}Рабочая директория: {os.getcwd()}{Colors.NC}
"""
    print(banner)

def print_status(message):
    """Печать статуса с зеленым цветом"""
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")

def print_warning(message):
    """Печать предупреждения с желтым цветом"""
    print(f"{Colors.YELLOW}⚠️ {message}{Colors.NC}")

def print_error(message):
    """Печать ошибки с красным цветом"""
    print(f"{Colors.RED}❌ {message}{Colors.NC}")

def print_info(message):
    """Печать информации с синим цветом"""
    print(f"{Colors.BLUE}ℹ️ {message}{Colors.NC}")

def print_step(message):
    """Печать шага с фиолетовым цветом"""
    print(f"{Colors.PURPLE}🚀 {message}{Colors.NC}")

def check_command(command, name):
    """Проверка наличия команды в системе"""
    try:
        result = subprocess.run([command, '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print_status(f"{name} найден: {version}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        pass
    
    print_warning(f"{name} не найден")
    return False

def run_command(command, cwd=None, shell=False, check=True):
    """Выполнение команды с обработкой ошибок"""
    try:
        if isinstance(command, str) and shell:
            result = subprocess.run(command, shell=True, cwd=cwd, 
                                  capture_output=True, text=True, timeout=300)
        else:
            result = subprocess.run(command, cwd=cwd, 
                                  capture_output=True, text=True, timeout=300)
        
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, command)
        
        return result
    except subprocess.TimeoutExpired:
        print_error(f"Команда превысила время ожидания: {' '.join(command) if isinstance(command, list) else command}")
        return None
    except Exception as e:
        print_error(f"Ошибка выполнения команды: {e}")
        return None

def setup_python_environment():
    """Настройка Python окружения"""
    print_step("Настройка Python окружения...")
    
    # Проверка Python версии
    if sys.version_info < (3, 8):
        print_error("Требуется Python 3.8+. Текущая версия: " + sys.version)
        return False
    
    # Создание виртуального окружения
    venv_path = Path(".venv")
    if not venv_path.exists():
        print_info("Создание виртуального окружения...")
        result = run_command([sys.executable, "-m", "venv", ".venv"])
        if result is None:
            return False
        print_status("Виртуальное окружение создано")
    else:
        print_status("Виртуальное окружение уже существует")
    
    # Определение пути к pip в зависимости от ОС
    if platform.system() == "Windows":
        pip_path = venv_path / "Scripts" / "pip"
        python_path = venv_path / "Scripts" / "python"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # Обновление pip
    print_info("Обновление pip...")
    run_command([str(pip_path), "install", "--upgrade", "pip"], check=False)
    
    # Установка зависимостей
    print_info("Установка Python зависимостей...")
    result = run_command([str(pip_path), "install", "-r", "requirements.txt"])
    if result is None:
        return False
    
    print_status("Python зависимости установлены")
    return True

def setup_frontend():
    """Настройка frontend"""
    print_step("Настройка frontend...")
    
    if not check_command("node", "Node.js"):
        print_warning("Node.js не найден. Frontend может не работать")
        return True
    
    if not check_command("npm", "npm"):
        print_warning("npm не найден. Frontend может не работать")
        return True
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print_warning("Папка frontend не найдена")
        return True
    
    print_info("Установка frontend зависимостей...")
    result = run_command(["npm", "install", "--silent"], cwd=frontend_dir)
    if result is None:
        print_warning("Не удалось установить frontend зависимости")
        return True
    
    print_status("Frontend зависимости установлены")
    return True

def create_env_file():
    """Создание .env файла"""
    print_step("Создание конфигурации...")
    
    env_file = Path(".env")
    if env_file.exists():
        print_status(".env файл уже существует")
        return True
    
    env_content = """# Weaviate Configuration
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=embeddinggemma:300m
VECTOR_SIZE=768

# OpenRouter Keys (добавьте свои ключи)
OPENROUTER_KEY_1=
OPENROUTER_KEY_2=
OPENROUTER_KEY_3=
OPENROUTER_KEY_4=
OPENROUTER_KEY_5=

# Gemini API Key (backup)
GEMINI_API_KEY=

# Flask Configuration
FLASK_PORT=5000
FLASK_DEBUG=True
"""
    
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print_status(".env файл создан")
        print_warning("Добавьте свои API ключи в .env файл")
        return True
    except Exception as e:
        print_error(f"Не удалось создать .env файл: {e}")
        return False

def check_service(url, name, timeout=5):
    """Проверка доступности сервиса"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def setup_weaviate():
    """Настройка Weaviate"""
    print_step("Настройка Weaviate...")
    
    if check_service("http://localhost:8080/v1/meta", "Weaviate"):
        print_status("Weaviate уже запущен")
        return True
    
    if not check_command("docker", "Docker"):
        print_warning("Docker не найден. Запустите Weaviate вручную:")
        print_warning("docker run -p 8080:8080 semitechnologies/weaviate:latest")
        return False
    
    print_info("Запуск Weaviate в Docker...")
    result = run_command([
        "docker", "run", "-d", "--name", "vetka-weaviate",
        "-p", "8080:8080", "-p", "50051:50051",
        "semitechnologies/weaviate:latest"
    ])
    
    if result is None:
        print_error("Не удалось запустить Weaviate")
        return False
    
    print_info("Ожидание запуска Weaviate...")
    for i in range(30):  # Ждем до 30 секунд
        time.sleep(1)
        if check_service("http://localhost:8080/v1/meta", "Weaviate"):
            print_status("Weaviate запущен")
            return True
        print(f"Ожидание... ({i+1}/30)")
    
    print_error("Weaviate не запустился в течение 30 секунд")
    return False

def setup_ollama():
    """Настройка Ollama"""
    print_step("Настройка Ollama...")
    
    if not check_command("ollama", "Ollama"):
        print_warning("Ollama не найден. Установите Ollama для работы с локальными моделями")
        return True
    
    if check_service("http://localhost:11434/api/tags", "Ollama"):
        print_status("Ollama уже запущен")
    else:
        print_info("Запуск Ollama...")
        if platform.system() == "Windows":
            subprocess.Popen(["ollama", "serve"], shell=True)
        else:
            subprocess.Popen(["ollama", "serve"])
        
        print_info("Ожидание запуска Ollama...")
        for i in range(10):  # Ждем до 10 секунд
            time.sleep(1)
            if check_service("http://localhost:11434/api/tags", "Ollama"):
                print_status("Ollama запущен")
                break
        else:
            print_warning("Ollama не запустился автоматически")
    
    # Загрузка моделей
    print_info("Загрузка моделей Ollama...")
    models = [
        "embeddinggemma:300m",
        "llama3.1:8b", 
        "deepseek-coder:6.7b",
        "qwen2:7b"
    ]
    
    for model in models:
        print_info(f"Загрузка {model}...")
        result = run_command(["ollama", "pull", model], check=False)
        if result and result.returncode == 0:
            print_status(f"{model} загружен")
        else:
            print_warning(f"Не удалось загрузить {model}")
    
    return True

def run_vetka():
    """Запуск VETKA"""
    print_step("Запуск VETKA Live 0.3...")
    
    print(f"""
{Colors.CYAN}🌐 Откройте в браузере: http://localhost:5000{Colors.NC}
{Colors.CYAN}📊 Проверка здоровья: http://localhost:5000/api/health{Colors.NC}

{Colors.WHITE}🎮 Команды для тестирования:{Colors.NC}
  /bot/create API
  /bot/analyze code
  /visual/tree
  /search/query

{Colors.WHITE}⌨️ Горячие клавиши:{Colors.NC}
  / - фокус на ввод команды
  1-5 - смена режимов визуализации
  g - глобальный вид
  t - вид дерева
  l - вид листьев

{Colors.WHITE}🛑 Для остановки нажмите Ctrl+C{Colors.NC}
""")
    
    # Определение пути к Python в виртуальном окружении
    if platform.system() == "Windows":
        python_path = Path(".venv") / "Scripts" / "python"
    else:
        python_path = Path(".venv") / "bin" / "python"
    
    try:
        # Запуск основного приложения
        subprocess.run([str(python_path), "main.py"])
    except KeyboardInterrupt:
        print_info("VETKA остановлен пользователем")
    except Exception as e:
        print_error(f"Ошибка запуска VETKA: {e}")

def main():
    """Основная функция"""
    print_banner()
    
    try:
        # Настройка окружения
        if not setup_python_environment():
            return False
        
        if not setup_frontend():
            print_warning("Frontend настройка завершена с предупреждениями")
        
        if not create_env_file():
            return False
        
        # Настройка сервисов
        if not setup_weaviate():
            print_warning("Weaviate настройка завершена с предупреждениями")
        
        if not setup_ollama():
            print_warning("Ollama настройка завершена с предупреждениями")
        
        print_status("Все готово! Запускаем VETKA...")
        print()
        
        # Запуск VETKA
        run_vetka()
        
    except KeyboardInterrupt:
        print_info("Запуск прерван пользователем")
    except Exception as e:
        print_error(f"Критическая ошибка: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
