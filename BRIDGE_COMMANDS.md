# VETKA Bridge Quick Reference
# Данила, это твой чеклист для быстрых стартов!

## 🚀 ЗАПУСК
```bash
# Основная команда (из папки vetka_live_03)
export OPENCODE_BRIDGE_ENABLED=true && python main.py

# Фоновый запуск
export OPENCODE_BRIDGE_ENABLED=true && nohup python main.py > vetka.log 2>&1 &
```

## 🔍 ПРОВЕРКА
```bash
# Health check
curl http://localhost:5001/api/bridge/openrouter/health

# Ключи (10 штук)
curl http://localhost:5001/api/bridge/openrouter/keys

# Статистика
curl http://localhost:5001/api/bridge/openrouter/stats
```

## 🛠 УПРАВЛЕНИЕ
```bash
# Статус процесса
ps aux | grep "python main.py"

# Остановка
pkill -f "python main.py"

# Логи (если в фоне)
tail -f vetka.log
```

## 📋 МОДЕЛИ
Доступные через bridge:
- deepseek/deepseek-chat (дешёвый)
- deepseek/deepseek-coder (код) 
- meta-llama/llama-3.1-8b-instruct (быстрый)
- anthropic/claude-3.5-sonnet (качественный)
- google/gemini-flash-1.5 (универсальный)

## 🌐 OPENCODE ИНТЕГРАЦИЯ
Base URL: http://localhost:5001/api/bridge/openrouter
Endpoint: /invoke
Method: POST

## 📁 ПОЛЕЗНЫЕ ФАЙЛЫ
- data/config.json - ключи
- src/opencode_bridge/ - код моста
- src/api/routes/__init__.py - регистрация моста

## 🎯 БЕЗОПАСНОСТЬ
- Только localhost (127.0.0.1)
- Ключи masked в UI
- 24h cooldown при 403
- Автоматическая ротация

---
Created: $(date) - Big Pickle 👨‍💻🌳