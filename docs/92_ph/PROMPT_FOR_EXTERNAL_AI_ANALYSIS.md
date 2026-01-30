# 🚀 PROMPT FOR EXTERNAL AI ANALYSIS

**Copy and send this prompt to large unpaid models (GPT-4, Claude Opus, Grok, etc.)**

---

## 📋 PROMPT START

Я эксперт по VETKA AI системе и мне нужен твой глубокий технический анализ. Система VETKA - это сложная multi-agent архитектура с умным роутингом API ключей, MCP интеграцией, и недавними исправлениями токенного усечения.

### 🎯 КОНТЕКТ ПРОБЛЕМЫ:

1. **7000-токенное усечение:** Недавно исправлено, но нужно верифицировать что все харкод лимиты удалены и система использует Elisum+CAM+Engram компрессию вместо примитивных усечений.

2. **Умный роутинг ключей:** Multi-key система с OpenRouter, xAI, OpenAI, Gemini провайдерами. Есть проблемы с fallback и auto-rotation.

3. **MCP интеграция:** Claude Code + OpenCode бриджи для внешних AI агентов. `vetka_call_model` падает на Ollama fallback.

### 📁 ФАЙЛЫ ДЛЯ АНАЛИЗА:

**🔴 КРИТИЧЕСКИЕ (анализировать первым):**
```
src/utils/unified_key_manager.py
src/orchestration/orchestrator_with_elisya.py  
src/mcp/vetka_mcp_bridge.py              # 🔥 MAIN MCP BRIDGE
src/opencode_bridge/open_router_bridge.py
src/api/handlers/user_message_handler.py
src/elisya/api_aggregator_v3.py
src/api/handlers/handler_utils.py
```

**🟡 ВТОРИЧНЫЕ (анализировать после):**
```
src/elisya/provider_registry.py
src/api/routes/config_routes.py
src/mcp/mcp_server.py
src/mcp/vetka_mcp_server.py
src/orchestration/services/api_key_service.py
```

**🌐 MCP КОНФИГУРАЦИЯ:**
```
src/mcp/vetka_mcp_bridge.py                # 🔴 CRITICAL: MAIN VETKA MCP Bridge
/Users/danilagulin/.config/claude-desktop/config.json
src/opencode_bridge/routes.py
```

### 🔍 ЗАДАЧИ АНАЛИЗА:

#### 1. Токенное Усечение (Truncation Analysis):
- Проверить что все hard-coded лимиты удалены из указанных файлов
- Убедиться что используется Elisum+CAM+Engram компрессия 
- Найти любые оставшиеся места с усечением на ~7000 токенов
- Оценить эффективность текущей компрессионной системы

#### 2. Умный Роутинг Ключей (Smart Key Routing):
- Проанализировать UnifiedKeyManager архитектуру
- Проверить mechanisms auto-rotation и fallback
- Найти проблемы с multi-key управлением 
- Оценить надежность провайдер switching логики

#### 3. MCP Интеграция (MCP Integration):
- Проверить Claude Code bridge корректность
- Проанализировать OpenCode integration
- Найти причины `vetka_call_model` ошибок на Ollama
- Оценить общую MCP архитектуру

#### 4. Архитектурная Оптимизация:
- Найти узкие места в производительности
- Предложить улучшения для large token contexts
- Оценить безопасность API key handling
- Рекомендовать scalability улучшения

### 🎯 КОНКРЕТНЫЕ ВОПРОСЫ:

1. **Truncation:** Все ли харкод лимиты (500 chars, 8000 chars, 3000 chars) действительно удалены? Заменены ли они на умную компрессию?

2. **Key Routing:** Почему `vetka_call_model` fallback на Ollama? Правильно ли сконфигурирован `export XAI_API_KEY`?

3. **MCP Bridges:** Корректно ли работают Claude Code и OpenCode мосты? Какие есть проблемы в JSON-RPC коммуникации?

4. **Architecture:** Какие главные слабые места в текущей архитектуре для обработки 100k+ токенов?

5. **Performance:** Как оптимизировать систему для real-time обработки больших артефактов?

### 📊 ОЖИДАЕМЫЙ ВЫВОД:

Создай структурированный отчет:
```
## 🎯 EXECUTIVE SUMMARY
- Основные проблемы и их критичность
- Общая оценка системы (0-100%)

## 🔍 DETECTED ISSUES  
### Truncation Problems
### Key Routing Issues  
### MCP Integration Bugs
### Architecture Weaknesses

## 💡 RECOMMENDATIONS
### Immediate Fixes (Today)
### Short-term Improvements (Week)
### Long-term Architecture (Month)

## 🚀 OPTIMIZATION PLAN
- Specific code changes needed
- Architecture improvements
- Performance optimizations
- Security enhancements
```

### 🔧 ТЕХНИЧЕСКИЕ ДЕТАЛИ:

**Файлы исправлений токенных лимитов (Phase 92):**
- `orchestrator_with_elisya.py:797-798` - удален 500 char limit
- `handler_utils.py:163-165` - удален 8000 char limit  
- `user_message_handler.py:999,466` - увеличено до 999999 tokens
- `api_aggregator_v3.py:465` - timeout увеличен до 300s

**Key Manager Features:**
- OpenRouter multi-key с paid/free приоритетом
- xAI fallback на OpenRouter
- Auto-rotation при rate limits
- 24h cooldown для failed keys

**MCP Components:**
- Claude Code bridge через vetka_claude_bridge_simple.py
- OpenCode integration через open_router_bridge.py
- Internal MCP server в mcp_server.py
- JSON-RPC 2.0 протокол для tool calls

### 🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ:

1. **XAI API Keys:** Возможны проблемы с `export XAI_API_KEY`
2. **Ollama Fallback:** Неправильный формат имени модели
3. **Token Limits:** Некоторые места могли быть пропущены при исправлении
4. **MCP Timeouts:** Требуется оптимизация таймаутов

### 💪 ТВОЯ ЗАДАЧА:

Сделай глубокий code review всех указанных файлов, найди корневые причины проблем, и предложи конкретные решения. Фокусируйся на практических улучшениях которые можно внедрить немедленно.

特别: Обрати внимание на русскоязычные комментарии в коде - они указывают на важные места исправлений.

---

## 📋 PROMPT END

**Instructions:**
1. Read all critical files first, then secondary files
2. Focus on the specific questions asked
3. Provide actionable recommendations with code examples
4. Structure output as requested above
5. Consider Russian comments as important markers

**Expected Analysis Time:** 2-4 hours  
**Output Format:** Structured technical report  
**Language:** Russian (code comments are in Russian)