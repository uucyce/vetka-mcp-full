# 🚀 VETKA Live 0.3 - Быстрый запуск

## 🎯 Один клик - и VETKA запущена!

### 🖥️ Для macOS/Linux:

```bash
# Сделать скрипт исполняемым и запустить
chmod +x quick_start.sh
./quick_start.sh
```

### 🪟 Для Windows:

```cmd
# Двойной клик на файл или в командной строке
run_vetka.bat
```

### 🐍 Универсальный Python скрипт (любая ОС):

```bash
python launch_vetka.py
```

## 🎮 Что происходит при запуске:

1. **✅ Проверка Python** - убеждается что Python 3.8+ установлен
2. **📦 Виртуальное окружение** - создает `.venv` если не существует
3. **📥 Зависимости** - устанавливает все Python пакеты из `requirements.txt`
4. **🎨 Frontend** - устанавливает Node.js зависимости (если Node.js есть)
5. **⚙️ Конфигурация** - создает `.env` файл с настройками
6. **🐳 Weaviate** - запускает в Docker (если Docker есть)
7. **🤖 Ollama** - запускает и загружает модели
8. **🌳 VETKA** - запускает основное приложение

## 🌐 После запуска:

- **Главная страница**: http://localhost:5000
- **Проверка здоровья**: http://localhost:5000/api/health
- **3D визуализация**: автоматически загружается на главной странице

## 🎮 Команды для тестирования:

```
/bot/create API          # Создать API через LangGraph workflow
/bot/analyze code        # Анализ кода
/visual/tree            # Обновить 3D визуализацию
/search/query           # Поиск в памяти
```

## ⌨️ Горячие клавиши:

- `/` - фокус на ввод команды
- `1-5` - смена режимов визуализации (ABC, 🕒, 🔥, 🔗, 🌿)
- `g` - глобальный вид
- `t` - вид дерева  
- `l` - вид листьев
- `Esc` - закрыть панель артефактов

## 🐛 Если что-то не работает:

### Weaviate не запускается:
```bash
# Запустить вручную
docker run -p 8080:8080 semitechnologies/weaviate:latest
```

### Ollama не запускается:
```bash
# Установить Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
```

### Python зависимости:
```bash
pip install -r requirements.txt
```

### Frontend зависимости:
```bash
cd frontend
npm install
```

## 🔧 Ручная настройка:

Если автоматические скрипты не работают, выполните команды вручную:

```bash
# 1. Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Frontend (если есть Node.js)
cd frontend && npm install && cd ..

# 4. Запустить сервисы
docker run -p 8080:8080 semitechnologies/weaviate:latest &
ollama serve &

# 5. Запустить VETKA
python main.py
```

## 🎉 Готово!

После запуска откройте http://localhost:5000 и наслаждайтесь 3D деревом знаний! 🌳✨
