# 🚀 PHASE 7-8 QUICK DEPLOYMENT GUIDE

**Время:** ~5 минут  
**Риск:** Низкий (только замена main.py)  
**Результат:** Сервер стабилен, без утечек ресурсов

---

## ⚡ SUPER QUICK (Copy-Paste Commands)

### 1️⃣ Резервная копия
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
cp main.py main_backup_7_7.py
echo "✅ Backup created: main_backup_7_7.py"
```

### 2️⃣ Развернуть исправленную версию
```bash
cp main_fixed_phase_7_8.py main.py
echo "✅ Fixed version deployed"
```

### 3️⃣ Проверить зависимости (выполнить в отдельных окнах терминала)

**Окно 1: Ollama**
```bash
# Проверить, запущен ли Ollama
lsof -i :11434

# Если НЕ запущен:
ollama serve

# В другом окне терминала:
ollama pull gemma:2b-embed-q4_0
```

**Окно 2: Docker (Weaviate + Qdrant)**
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
docker-compose up -d

# Проверить статус
docker-compose ps

# Ожидаемый вывод:
# weaviate     RUNNING
# qdrant       RUNNING
```

### 4️⃣ Запустить Flask сервер
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 main.py

# Ожидаемый вывод:
# ✅ Global MemoryManager singleton created
# ✅ Weaviate is connected
# 🌳 VETKA PHASE 7.8 - RESOURCE LEAK FIXED
```

### 5️⃣ Проверить на утечки (в новом терминале)

**Вариант A: Простая проверка (30 сек)**
```bash
# Запросить статус 15 раз (каждые 2 сек)
for i in {1..15}; do
  echo "Request $i:"
  curl -s http://localhost:5001/api/system/summary | jq .timestamp
  sleep 2
done

# Ожидаемый результат: NO ERROR → Сервер стабилен ✅
```

**Вариант B: Мониторинг файловых дескрипторов (5 минут)**
```bash
# В отдельном терминале мониторить количество открытых файлов
watch -n 1 'echo "Open FDs:" && lsof -p $(pgrep -f "python3 main.py") | wc -l'

# В другом терминале постоянно генерировать запросы
while true; do
  curl -s http://localhost:5001/api/system/summary > /dev/null
  sleep 1
done

# Ожидаемый результат: 
# Open FDs: 45-50 (STABLE, не растёт!)
```

---

## ✅ VERIFICATION STEPS

### Шаг 1: Проверить запуск
```bash
curl http://localhost:5001/health
# Expected response: {"status": "ok", "service": "vetka-phase-7-8", ...}
```

### Шаг 2: Проверить систему
```bash
curl http://localhost:5001/api/system/summary | jq .
# Expected response:
# {
#   "timestamp": 1729036800.0,
#   "modules": {"metrics_engine": true, ...},
#   "services": {"weaviate": true, "qdrant": "connected", ...}
# }
```

### Шаг 3: Проверить Weaviate
```bash
curl http://localhost:8080/v1/meta
# Expected: {"version": "1.x.x", ...}
```

### Шаг 4: Проверить Qdrant
```bash
curl http://127.0.0.1:6333/health
# Expected: {"status": "ok"}
```

### Шаг 5: Проверить Ollama
```bash
curl http://localhost:11434/api/tags
# Expected: {"models": [{"name": "gemma:2b-embed-q4_0", ...}, ...]}
```

---

## 🐛 TROUBLESHOOTING

### Проблема: "Cannot connect to Weaviate"
```bash
# Решение 1: Перезапустить контейнер
docker-compose restart weaviate

# Решение 2: Проверить логи
docker-compose logs weaviate

# Решение 3: Пересоздать контейнер
docker-compose down
docker-compose up -d
```

### Проблема: "Ollama not found"
```bash
# Решение: Запустить Ollama
ollama serve

# Убедитесь, что слушает на порту 11434
lsof -i :11434
```

### Проблема: "Too many open files" (всё ещё случается)
```bash
# Проверить лимит ОС
ulimit -n

# Увеличить лимит временно
ulimit -n 2048

# Запустить сервер
python3 main.py
```

### Проблема: Python3 не найден
```bash
# Проверить версию Python
which python3
python3 --version

# Если не работает, использовать полный путь
/usr/bin/python3 main.py
```

---

## 📊 EXPECTED BEHAVIOR

### ✅ Правильно (After Fix)
```
Time 0s  → [FLASK STARTUP] → Checking dependencies
Time 0.5s → ✅ Global MemoryManager singleton created
Time 1s  → ✅ Metrics Engine initialized
Time 1.5s → ✅ Qdrant Auto-Retry started
Time 2s  → ✅ Weaviate is connected
Time 2.5s → 🌳 VETKA PHASE 7.8 - Starting server

→ Server STAYS RUNNING
→ File descriptor count STABLE (~50)
→ All requests work normally
→ Zero crashes for hours ✅
```

### ❌ Неправильно (Before Fix)
```
Time 0s   → [FLASK STARTUP]
Time 1s   → First /api/system/summary request (+10 FDs)
Time 3s   → Second request (+10 FDs) = 20 total
Time 5s   → Third request (+10 FDs) = 30 total
...
Time 25s  → FDs = 240/256 (CRITICAL)
Time 30s  → 💥 OSError: [Errno 24] Too many open files
```

---

## 📈 METRICS

### File Descriptor Monitoring
```bash
# Команда для мониторинга в реальном времени
lsof -p $(pgrep -f "python3 main.py") | tail -20

# Ожидаемый максимум: ~60 файловых дескрипторов
# Рост должен быть: 0 (абсолютно стабилен)
```

### Request Response Time
```bash
# Измерить время ответа
time curl http://localhost:5001/api/system/summary > /dev/null

# Ожидаемо: 50-100ms (не растёт со временем)
```

---

## 🎯 SUCCESS CHECKLIST

- [ ] ✅ Backup создан
- [ ] ✅ main_fixed_phase_7_8.py скопирован в main.py
- [ ] ✅ Ollama запущен и gemma установлен
- [ ] ✅ Docker контейнеры запущены (Weaviate + Qdrant)
- [ ] ✅ Flask сервер запущен без ошибок
- [ ] ✅ /health работает
- [ ] ✅ /api/system/summary работает
- [ ] ✅ Нет ошибок за 5 минут работы
- [ ] ✅ File descriptors стабильны
- [ ] ✅ Можно идти дальше (Phase 7-9)

---

## 📞 QUICK REFERENCE

| Операция | Команда |
|----------|---------|
| Backup | `cp main.py main_backup_7_7.py` |
| Deploy Fix | `cp main_fixed_phase_7_8.py main.py` |
| Start Server | `python3 main.py` |
| Check Health | `curl http://localhost:5001/health` |
| Monitor FDs | `watch -n 1 'lsof -p $(pgrep -f "python3 main.py") \| wc -l'` |
| Start Ollama | `ollama serve` |
| Pull Gemma | `ollama pull gemma:2b-embed-q4_0` |
| Start Docker | `docker-compose up -d` |
| Stop Docker | `docker-compose down` |
| Check Docker | `docker-compose ps` |

---

**🟢 READY TO DEPLOY**

Все проблемы идентифицированы и решены. Можно запускать!
