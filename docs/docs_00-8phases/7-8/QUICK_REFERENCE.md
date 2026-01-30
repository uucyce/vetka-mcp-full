# 🚀 VETKA /api/chat — Quick Reference

## Start Server
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 main.py
```

## Endpoint
```
POST http://localhost:5001/api/chat
```

## Minimal Request
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Your question here"}'
```

## Full Request Template
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "User message",
    "conversation_id": "optional_id",
    "model_override": "gpt-4-turbo",
    "system_prompt": "You are helpful AI",
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

## Response Structure
```json
{
  "conversation_id": "uuid",
  "response": "answer text",
  "model": "gpt-4o-mini",
  "provider": "openai",
  "processing_time_ms": 1250.45,
  "eval_score": 8.5,
  "eval_feedback": {
    "relevance": 9,
    "completeness": 8,
    "clarity": 8.5,
    "accuracy": 8,
    "recommendations": ["...", "..."]
  },
  "metrics": {
    "input_tokens": 10,
    "output_tokens": 150,
    "agent_scores": {"pm": 7.5, "dev": 9.0, "qa": 8.0}
  },
  "timestamp": 1734000000.123
}
```

## Python Quick Test
```python
import requests

r = requests.post(
    'http://localhost:5001/api/chat',
    json={'message': 'What is Python?'}
)
print(r.json()['response'])
print(f"Score: {r.json()['eval_score']}/10")
```

## Features
✅ ModelRouter (auto model selection)  
✅ EvalAgent (quality scoring 0-10)  
✅ Parallel agents (PM, Dev, QA)  
✅ Weaviate + Qdrant storage  
✅ Comprehensive metrics  

## Models Available
- `gpt-4-turbo` (best quality)
- `gpt-4o-mini` (fast, cheap)
- `claude-3-opus` (strong)
- `gemini-2.0-flash` (latest)
- `ollama_llm` (local)

## Common Issues
| Issue | Fix |
|-------|-----|
| Connection refused | `lsof -i :5001` |
| ModuleNotFound | `pip install litellm openai anthropic` |
| No eval_score | Check EvalAgent import in main.py |
| Slow response | Reduce max_tokens or use gpt-4o-mini |

## API Keys Needed
```bash
# Add to ~/.env or environment
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=...
```

## Verify Service
```bash
curl http://localhost:5001/health
curl http://localhost:5001/api/system/summary
```

## Full Docs
- API: `/Users/danilagulin/Documents/VETKA_Project/docs/7-8/API_CHAT_ENDPOINT.md`
- Testing: `/Users/danilagulin/Documents/VETKA_Project/docs/7-8/TESTING_GUIDE.md`
- README: `/Users/danilagulin/Documents/VETKA_Project/docs/7-8/README.md`

---
**Phase 7.8 ✅ Production Ready**
