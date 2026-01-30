# 🎯 VETKA API Chat Endpoint — Phase 7.8

## Overview

**Universal Chat API** — полностью интегрированный эндпоинт для обработки пользовательских сообщений через всю архитектуру VETKA v4.2.

### ✅ Возможности

- **ModelRouter v2** — автоматический выбор модели по сложности задачи
- **AgentOrchestrator** — параллельная обработка через PM/Dev/QA агентов
- **EvalAgent** — автоматическое оценивание качества ответов (0-10)
- **MemoryManager** — сохранение в Weaviate + Qdrant (Triple Write)
- **Metrics** — полный tracking latency, tokens, agent scores

---

## 📍 Endpoint

```
POST /api/chat
```

**Base URL:** `http://localhost:5001`

---

## 📤 Request Body

```json
{
  "message": "Как мне создать React компонент с хуками?",
  "conversation_id": "conv_12345",
  "model_override": "gpt-4-turbo",
  "system_prompt": "Ты — опытный React разработчик",
  "temperature": 0.7,
  "max_tokens": 1500
}
```

### Параметры

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `message` | string | ✅ | — | Сообщение от пользователя (макс 10000 символов) |
| `conversation_id` | string | ❌ | UUID | Идентификатор разговора (для сохранения контекста) |
| `model_override` | string | ❌ | auto | Переопределить выбор модели (gpt-4o, gpt-4-turbo, claude-3, gemini-2.0-flash) |
| `system_prompt` | string | ❌ | default | Кастомный system prompt |
| `temperature` | float | ❌ | 0.7 | Температура (0.0 - 2.0) |
| `max_tokens` | int | ❌ | 1000 | Макс токенов в ответе |

---

## 📥 Response

### Success (200 OK)

```json
{
  "conversation_id": "conv_12345",
  "response": "Вот как создать React компонент с хуками...",
  "model": "gpt-4-turbo",
  "provider": "openai",
  "processing_time_ms": 1250.45,
  "eval_score": 8.5,
  "eval_feedback": {
    "relevance": 9,
    "completeness": 8,
    "clarity": 8.5,
    "accuracy": 8,
    "recommendations": ["Добавить больше примеров кода", "Упомянуть useCallback"]
  },
  "metrics": {
    "input_tokens": 15,
    "output_tokens": 142,
    "agent_scores": {
      "pm": 7.5,
      "dev": 9.0,
      "qa": 8.0
    }
  },
  "timestamp": 1734000000.123
}
```

### Error (4xx/5xx)

```json
{
  "error": "Message is required"
}
```

---

## 🧪 Примеры использования

### 1️⃣ cURL — Простой запрос

```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Объясни что такое асинхронность в JavaScript",
    "temperature": 0.8
  }'
```

### 2️⃣ cURL — С переопределением модели

```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Напиши FastAPI приложение для работы с БД",
    "model_override": "gpt-4-turbo",
    "system_prompt": "Ты — expert в Python и FastAPI",
    "max_tokens": 2000,
    "temperature": 0.5
  }'
```

### 3️⃣ Python — requests

```python
import requests
import json

url = "http://localhost:5001/api/chat"
payload = {
    "message": "Как использовать Docker в production?",
    "conversation_id": "user_123_session_1",
    "model_override": "claude-3-opus",
    "temperature": 0.7
}

response = requests.post(url, json=payload)
data = response.json()

print(f"Model: {data['model']}")
print(f"EvalScore: {data['eval_score']}")
print(f"Response: {data['response'][:200]}...")
print(f"Processing time: {data['processing_time_ms']:.1f}ms")
print(f"Agent scores: {data['metrics']['agent_scores']}")
```

### 4️⃣ JavaScript/Node.js — fetch

```javascript
async function chatWithVetka(userMessage) {
  const response = await fetch('http://localhost:5001/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: userMessage,
      conversation_id: `user_${Date.now()}`,
      temperature: 0.7,
      max_tokens: 1500
    })
  });

  const data = await response.json();
  
  console.log(`🔀 Model: ${data.model}`);
  console.log(`⭐ Score: ${data.eval_score}/10`);
  console.log(`📝 Response: ${data.response}`);
  console.log(`⏱️  Time: ${data.processing_time_ms.toFixed(1)}ms`);
  
  return data;
}

// Usage
await chatWithVetka("Как оптимизировать React приложение?");
```

### 5️⃣ Batch запросы — параллельная обработка

```python
import requests
from concurrent.futures import ThreadPoolExecutor
import json

messages = [
    "Как использовать Docker?",
    "Объясни GraphQL",
    "Best practices в Kubernetes",
    "Как оптимизировать БД запросы?"
]

def call_api(message):
    response = requests.post(
        "http://localhost:5001/api/chat",
        json={"message": message, "temperature": 0.7}
    )
    return response.json()

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(call_api, messages))

for result in results:
    print(f"\n📝 Message processed")
    print(f"   Model: {result['model']}")
    print(f"   Score: {result['eval_score']}/10")
    print(f"   Time: {result['processing_time_ms']:.1f}ms")
```

---

## 🔄 Processing Pipeline

```
1️⃣  REQUEST VALIDATION
    ↓
2️⃣  MODEL ROUTING (ModelRouter v2)
    ├─ Анализирует сложность сообщения
    ├─ Выбирает оптимальную модель (GPT-4, Claude, Gemini, Ollama)
    └─ Возвращает provider info
    ↓
3️⃣  AGENT ORCHESTRATION (Elisya + Parallel)
    ├─ PM Agent → анализирует требования
    ├─ Dev Agent → генерирует решение (параллельно)
    ├─ QA Agent → проверяет качество (параллельно)
    └─ Объединяет результаты
    ↓
4️⃣  API FALLBACK (если Elisya не доступна)
    ├─ ModelRouter v2 → прямой вызов провайдера
    └─ Ollama → локальные LLM
    ↓
5️⃣  MEMORY PERSISTENCE (Triple Write)
    ├─ Weaviate → основной граф знаний
    ├─ Qdrant → векторные представления
    └─ ChangeLog → аудит всех изменений
    ↓
6️⃣  EVALUATION (EvalAgent)
    ├─ Relevance score → релевантность ответа
    ├─ Completeness score → полнота
    ├─ Clarity score → ясность
    ├─ Accuracy score → точность
    └─ Feedback → рекомендации для улучшения
    ↓
7️⃣  RESPONSE ASSEMBLY & RETURN
```

---

## 📊 Response Metrics Explained

### `eval_score` (0-10)

**Автоматическая оценка качества ответа:**
- **9-10:** Excellent (полный, точный, релевантный)
- **7-8:** Good (хороший, с малыми недостатками)
- **5-6:** Fair (приемлемый, но неполный)
- **0-4:** Poor (неудовлетворительный)

### `eval_feedback`

```json
{
  "relevance": 9,        // Насколько ответ релевантен вопросу (0-10)
  "completeness": 8,     // Полнота ответа (0-10)
  "clarity": 8.5,        // Ясность изложения (0-10)
  "accuracy": 8,         // Точность информации (0-10)
  "recommendations": [   // Список рекомендаций для улучшения
    "Добавить примеры кода",
    "Упомянуть edge cases"
  ]
}
```

### `agent_scores`

```json
{
  "pm": 7.5,    // Product Manager Agent — анализ требований
  "dev": 9.0,   // Developer Agent — качество решения
  "qa": 8.0     // QA Agent — проверка и тестирование
}
```

### `processing_time_ms`

Полное время обработки от получения запроса до отправки ответа (включает все стадии).

---

## 🔧 Configuration via Environment

Создайте `.env` файл:

```bash
# Model Router configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=...

# Feature flags
ENABLE_PARALLEL_AGENTS=true
ENABLE_EVALAGENT=true
ENABLE_MEMORY_PERSISTENCE=true
ENABLE_QDRANT=true

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Weaviate
WEAVIATE_URL=http://localhost:8080

# Qdrant
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=optional_key
```

---

## ⚠️ Error Handling

### Missing message

```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response (400):**
```json
{
  "error": "Message is required"
}
```

### Message too long

```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "' + 'A' * 11000 + '"}'
```

**Response (400):**
```json
{
  "error": "Message too long (max 10000 chars)"
}
```

### Service unavailable

**Response (503):**
```json
{
  "error": "Model router not available"
}
```

---

## 📈 Monitoring & Debugging

### Логи сервера

При запросе к `/api/chat` вы увидите:

```
======================================================================
💬 CHAT API REQUEST: conv_12345
📝 Message: Как создать React компонент...
======================================================================
🔀 Model Router selected: gpt-4-turbo
✅ Parallel orchestrator processed in 1.25s
💾 Saved to Weaviate
🔵 Saved to Qdrant
⭐ EvalAgent score: 8.50/10

✅ CHAT API RESPONSE: conv_12345
   Model: gpt-4-turbo
   Time: 1250.4ms
   Score: 8.50
======================================================================
```

### Health check

```bash
curl http://localhost:5001/api/system/summary
```

---

## 🚀 Performance Tips

1. **Для быстрых ответов:** используйте `model_override: "gpt-4o-mini"` и `temperature: 0.5`
2. **Для лучшего качества:** используйте `gpt-4-turbo` и позвольте ModelRouter выбирать
3. **Для batch операций:** отправляйте запросы параллельно (макс 10 одновременных)
4. **Для сохранения контекста:** используйте одинаковый `conversation_id`

---

## 📞 Support

**Вопросы?** Проверьте:
1. ✅ Flask запущен на `localhost:5001`
2. ✅ Все зависимости установлены (`pip install qdrant-client requests ollama litellm`)
3. ✅ API ключи установлены в `.env`
4. ✅ Docker контейнеры запущены (`docker-compose ps`)

---

## 📝 Changelog

### Phase 7.8 (Current)
- ✅ Добавлен `/api/chat` endpoint
- ✅ Интеграция с ModelRouter v2
- ✅ EvalAgent scoring
- ✅ Triple Write (Weaviate + Qdrant + ChangeLog)
- ✅ Parallel agent processing (Elisya)
- ✅ Comprehensive metrics & feedback

---

**Created:** 2024-12-11  
**Last Updated:** 2024-12-11  
**Status:** ✅ Production Ready
