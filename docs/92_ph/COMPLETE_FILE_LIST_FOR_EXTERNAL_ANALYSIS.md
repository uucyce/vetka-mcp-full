# 📋 COMPLETE FILE LIST FOR EXTERNAL AI ANALYSIS

**Generated:** 2026-01-25  
**Purpose:** Send to large unpaid models for deep analysis of VETKA key routing and MCP integration

---

## 🎯 ANALYSIS OBJECTIVES

1. **Investigate 7000-token truncation** - Verify fixes are complete
2. **Smart key routing analysis** - Deep dive into API key management  
3. **MCP integration audit** - Claude Code + OpenCode bridges
4. **Architecture optimization** - Identify improvements for large models

---

## 🔑 SMART KEY ROUTING FILES

### Core Key Management
```
src/utils/unified_key_manager.py              # 🔴 PRIMARY: Main key management system
src/orchestration/services/api_key_service.py # 🔴 PRIMARY: Service layer for keys
src/elisya/provider_registry.py              # 🔴 PRIMARY: Provider abstraction
src/elisya/api_gateway.py                    # 🟡 SECONDARY: Legacy gateway (deprecated)
```

### Key Routing Implementation
```
src/orchestration/orchestrator_with_elisya.py # 🔴 CRITICAL: _inject_api_key() function
src/api/handlers/user_message_handler.py     # 🔴 CRITICAL: Key selection logic
src/api/handlers/user_message_handler_legacy.py # 🟡 SECONDARY: Legacy handler
src/api/handlers/models/model_client.py      # 🔴 CRITICAL: Model client key usage
```

### Configuration & Endpoints
```
src/api/routes/config_routes.py              # 🔴 CRITICAL: /api/keys endpoints
src/services/model_registry.py               # 🟡 SECONDARY: Model registry
src/api/handlers/handler_utils.py            # 🟡 SECONDARY: Handler utilities
```

---

## 🌐 MCP INTEGRATION FILES

### Claude Code Bridge (Config Files)
```
/Users/danilagulin/.config/mcp/servers/vetka_claude_code/vetka_claude_bridge.py      # 🟡 SECONDARY: Old bridge
/Users/danilagulin/.config/mcp/servers/vetka_claude_code/vetka_claude_bridge_enhanced.py # 🟡 SECONDARY: Enhanced bridge
/Users/danilagulin/.config/claude-desktop/config.json                                  # 🔴 CRITICAL: MCP server config
```

### VETKA MCP Bridge (REAL WORKING BRIDGE)
```
src/mcp/vetka_mcp_bridge.py                # 🔴 CRITICAL: MAIN VETKA MCP Bridge
src/mcp/mcp_server.py                      # 🔴 CRITICAL: Internal MCP server
src/mcp/mcp_console_standalone.py          # 🟡 SECONDARY: Console interface
src/mcp/vetka_mcp_server.py               # 🟡 SECONDARY: MCP server implementation
```

### OpenCode Bridge
```
src/opencode_bridge/open_router_bridge.py   # 🔴 CRITICAL: OpenCode integration
src/opencode_bridge/routes.py               # 🔴 CRITICAL: OpenCode routes
src/opencode_bridge/multi_model_orchestrator.py # 🟡 SECONDARY: Multi-model orchestration
```

### MCP Tools & Handlers
```
src/mcp/tools/                              # 🔴 DIRECTORY: All MCP tools
src/api/routes/mcp_console_routes.py         # 🟡 SECONDARY: MCP console routes
```

---

## 🎭 TRUNCATION FIX FILES

### Core Orchestrator Fixes
```
src/orchestration/orchestrator_with_elisya.py # 🔴 CRITICAL: Lines 797-798, 741, 185 fixed
src/orchestration/response_formatter.py      # 🟡 SECONDARY: Previous Phase 90.2 fixes
```

### Handler Limit Removal
```
src/api/handlers/handler_utils.py            # 🔴 CRITICAL: Line 163-165 8000 char limit removed
src/api/handlers/user_message_handler.py     # 🔴 CRITICAL: Lines 999, 466 token limits increased
src/api/handlers/user_message_handler_legacy.py # 🟡 SECONDARY: Line 466 token limits increased
src/api/handlers/models/model_client.py      # 🔴 CRITICAL: Line 74 token limits increased
src/orchestration/agent_orchestrator.py      # 🟡 SECONDARY: Line 130 token limits increased
```

### System-wide Token Increases
```
src/elisya/api_aggregator_v3.py             # 🔴 CRITICAL: Line 465 timeout to 300s
src/interfaces/__init__.py                   # 🔴 CRITICAL: Line 84 token limits to 999999
src/context/context_fusion.py                # 🔴 CRITICAL: Line 418 token limits to 999999
src/utils/message_utils.py                   # 🔴 CRITICAL: Line 185 pinned files limit removed
```

---

## 🔍 CONFIGURATION & ENVIRONMENT

### Configuration Files
```
data/config.json                            # 🔴 CRITICAL: Main configuration
data/models_cache.json                      # 🟡 SECONDARY: Models cache
src/config/settings.py                      # 🟡 SECONDARY: Settings management
```

### Environment & Deployment
```
main.py                                     # 🔴 CRITICAL: Application entry point
.env.example                               # 🟡 SECONDARY: Environment template
```

---

## 📊 LOGGING & MONITORING

### Audit & Debug Files
```
src/mcp/audit_logger.py                     # 🟡 SECONDARY: MCP audit logging
src/mcp/rate_limiter.py                    # 🟡 SECONDARY: Rate limiting
data/mcp_audit/                             # 🔴 DIRECTORY: MCP audit logs
```

---

## 🎯 PRIORITY ANALYSIS ORDER

### 🔴 CRITICAL (Analyze First)
1. `src/utils/unified_key_manager.py` - Core key management
2. `src/orchestration/orchestrator_with_elisya.py` - Main orchestrator + truncation fixes
3. `src/mcp/mcp_server.py` - Internal MCP server
4. `src/opencode_bridge/open_router_bridge.py` - OpenCode integration
5. `/Users/danilagulin/.config/mcp/servers/vetka_claude_code/vetka_claude_bridge_simple.py` - Claude bridge

### 🟡 SECONDARY (Analyze After Critical)
6. `src/elisya/provider_registry.py` - Provider abstraction
7. `src/api/handlers/user_message_handler.py` - Message handling
8. `src/api/routes/config_routes.py` - Key endpoints
9. `src/elisya/api_aggregator_v3.py` - API aggregator
10. `src/mcp/vetka_mcp_bridge.py` - MCP bridge

---

## 🚨 SPECIFIC ISSUES TO INVESTIGATE

### 1. 7000-Token Truncation
- **Files to check:** All truncation fix files listed above
- **What to verify:** All hard-coded limits removed, using Elisum+CAM+Engram compression
- **Expected result:** Unlimited token processing with intelligent compression

### 2. Smart Key Routing Problems  
- **Files to check:** Key routing files listed above
- **What to verify:** Multi-key rotation, fallback mechanisms, provider selection
- **Expected result:** Robust key management with automatic failover

### 3. MCP Integration Issues
- **Files to check:** MCP bridge and server files
- **What to verify:** Claude Code integration, OpenCode bridge, tool calling
- **Expected result:** Seamless MCP communication with external AIs

---

## 📝 INSTRUCTIONS FOR EXTERNAL AI ANALYSIS

### Analysis Tasks
1. **Code Review:** Examine all 🔴 CRITICAL files first, then 🟡 SECONDARY
2. **Architecture Assessment:** Evaluate overall system design and patterns
3. **Problem Identification:** Find root causes of truncation and routing issues
4. **Optimization Recommendations:** Suggest improvements for each component
5. **Security Analysis:** Check API key handling and security practices

### Key Questions to Answer
- Are all truncation fixes properly implemented?
- Is smart key routing robust and scalable?
- Are MCP bridges correctly configured?
- What are the main architectural weaknesses?
- How can the system handle 100k+ token contexts efficiently?

### Expected Output Format
- Executive summary with key findings
- Detailed analysis per component
- Specific code recommendations
- Architecture improvement suggestions
- Security and performance optimization tips

---

## 🔄 TESTING INSTRUCTIONS

After receiving analysis, test with:
1. **Large artifacts (>10000 tokens)** to verify truncation fixes
2. **Key rotation scenarios** to test smart routing  
3. **MCP calls** to verify bridge functionality
4. **Stress tests** with multiple concurrent requests

---

**Total Files to Analyze:** ~35 files  
**Estimated Analysis Time:** 2-4 hours for large model  
**Expected Impact:** Major system optimization and reliability improvements