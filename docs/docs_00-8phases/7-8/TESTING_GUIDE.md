# 🧪 Quick Testing Guide — /api/chat Endpoint

## 🚀 Start Flask Server

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 main.py
```

**Expected output:**
```
🌳 VETKA PHASE 7.8 - FIXED QDRANT INTEGRATION (Qwen Analysis Applied)
======================================================================

📊 Services:
   • Flask API: http://localhost:5001
   • Socket.IO: ws://localhost:5001/socket.io/
   • Weaviate: http://localhost:8080
   • Ollama: http://localhost:11434
   • Qdrant: http://127.0.0.1:6333 (auto-connecting...)

📈 Workflow Endpoints:
   • POST /api/workflow/start - Start standard workflow (Socket.IO)
   • POST /api/workflow/autogen - Start Autogen workflow
   • GET /api/workflow/history - Workflow history
   • GET /api/workflow/stats - Workflow statistics

💬 Chat API:
   • POST /api/chat - Universal chat endpoint (Phase 7.8)
     Features: ModelRouter, EvalAgent, MemoryManager, Triple Write

📊 System Endpoints:
   • GET /api/system/summary - **ENHANCED** DevOps health check
   • GET /api/qdrant/status - Qdrant connection status
```

---

## 📡 Test 1: Basic Chat Request (cURL)

Open **new terminal** and run:

```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is Docker and how does it work?"
  }'
```

**Expected response (200 OK):**
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Docker is a containerization platform that...",
  "model": "gpt-4o-mini",
  "provider": "openai",
  "processing_time_ms": 1250.45,
  "eval_score": 8.5,
  "eval_feedback": {
    "relevance": 9,
    "completeness": 8,
    "clarity": 8.5,
    "accuracy": 8,
    "recommendations": ["Add containerization examples", "Mention image layers"]
  },
  "metrics": {
    "input_tokens": 8,
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

---

## 📡 Test 2: With Model Override

```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain Machine Learning to a beginner",
    "model_override": "gpt-4-turbo",
    "temperature": 0.8,
    "max_tokens": 2000
  }'
```

Server logs will show:
```
💬 CHAT API REQUEST: conv_abc123
📝 Message: Explain Machine Learning to a beginner
======================================================================
🔀 Model Router selected: gpt-4-turbo
🔌 API response via ModelRouter v2
💾 Saved to Weaviate
🔵 Saved to Qdrant
⭐ EvalAgent score: 9.00/10

✅ CHAT API RESPONSE: conv_abc123
   Model: gpt-4-turbo
   Time: 2150.5ms
   Score: 9.00
```

---

## 📡 Test 3: With Conversation ID (Context Preservation)

First request:
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to learn Python",
    "conversation_id": "user_alice_session_1"
  }'
```

Second request (same conversation):
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are decorators in Python?",
    "conversation_id": "user_alice_session_1"
  }'
```

✅ Both messages saved in same conversation in Weaviate + Qdrant

---

## 📡 Test 4: Error Handling

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
# Create 11KB message
MESSAGE=$(python3 -c "print('x' * 11000)")
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"$MESSAGE\"}"
```

**Response (400):**
```json
{
  "error": "Message too long (max 10000 chars)"
}
```

---

## 📡 Test 5: Batch Requests (Python)

Create file `test_batch.py`:

```python
#!/usr/bin/env python3
import requests
import time
from concurrent.futures import ThreadPoolExecutor

API_URL = "http://localhost:5001/api/chat"

messages = [
    "What is Git and why is it used?",
    "Explain REST APIs",
    "How does Docker networking work?",
    "What is a microservice architecture?",
    "Explain OAuth 2.0 authentication"
]

def call_api(msg):
    start = time.time()
    response = requests.post(API_URL, json={"message": msg})
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        return {
            "message": msg[:40] + "...",
            "model": data.get("model"),
            "score": data.get("eval_score"),
            "time_ms": data.get("processing_time_ms")
        }
    else:
        return {
            "message": msg[:40] + "...",
            "error": response.json().get("error")
        }

print("🚀 Starting batch requests...\n")

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(call_api, messages))

print("📊 Results:\n")
for i, result in enumerate(results, 1):
    print(f"{i}. Message: {result['message']}")
    if "error" in result:
        print(f"   ❌ Error: {result['error']}")
    else:
        print(f"   ✅ Model: {result['model']}")
        print(f"   ⭐ Score: {result['score']}/10")
        print(f"   ⏱️  Time: {result['time_ms']:.1f}ms")
    print()
```

Run:
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 test_batch.py
```

---

## 📡 Test 6: Verify Memory Persistence

After making requests, check Weaviate:

```bash
curl http://localhost:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{
      Get {
        Conversation {
          conversation_id
          role
          content
          model
          _additional {
            id
          }
        }
      }
    }"
  }'
```

Check Qdrant:

```bash
curl http://127.0.0.1:6333/collections
```

---

## 🔍 Verify Server Logs

Watch the Flask logs in the original terminal:

```
======================================================================
💬 CHAT API REQUEST: conv_12345
📝 Message: What is Docker and how does it work?
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

---

## ✅ Checklist

- [ ] Flask server started (`python3 main.py`)
- [ ] API responds to health check (`curl http://localhost:5001/health`)
- [ ] Chat API accepts requests (`curl -X POST /api/chat`)
- [ ] Responses include eval_score
- [ ] Messages saved to Weaviate (verify with GraphQL query)
- [ ] Messages saved to Qdrant (verify with collection query)
- [ ] Processing time is reasonable (< 5s)
- [ ] Agent scores are calculated (pm, dev, qa)

---

## 🐛 Troubleshooting

### "Connection refused"
```bash
# Check if Flask is running
lsof -i :5001

# Restart Flask
pkill -f "python3 main.py"
python3 main.py
```

### "Model router not available"
- Install: `pip install litellm openai anthropic google-generativeai`
- Set API keys in `.env` or environment

### "Weaviate save error"
- Check Weaviate: `curl http://localhost:8080`
- Restart: `docker-compose restart weaviate`

### "Qdrant save error"
- Check Qdrant: `curl http://127.0.0.1:6333/health`
- Run: `docker-compose up -d qdrant` (if using compose)

### No EvalAgent score
- Check if `EvalAgent` is imported correctly
- Verify: `curl http://localhost:5001/api/system/summary`

---

## 📊 Performance Benchmarks

| Metric | Expected | Acceptable |
|--------|----------|-----------|
| Response time (simple) | 500-1500ms | < 5000ms |
| Response time (complex) | 2000-5000ms | < 10000ms |
| Eval score calculation | 100-300ms | < 1000ms |
| Weaviate save | 50-200ms | < 1000ms |
| Qdrant save | 100-300ms | < 1000ms |

---

## 📝 Notes

- **First request slower:** Models/services initializing
- **ModelRouter selection:** Based on message complexity (token count)
- **eval_score:** 0-10 scale, auto-calculated by EvalAgent
- **agent_scores:** PM/Dev/QA agents scoring in parallel

---

**Status:** ✅ Ready for testing  
**Created:** 2024-12-11  
**Phase:** 7.8
