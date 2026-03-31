# Agent Gateway — Roadmap

**Task:** tb_1774956292_51219_1 (RECON)
**Date:** 2026-03-31
**Goal:** External agents (Gemini, Claude, GPT) work with VETKA TaskBoard via REST API

---

## Phase 1: MVP — Auth + Gateway Core [Qwen]

**Owner: Qwen (codex)**

- [ ] GW-1.1: Fix duplicate claim/complete routes in taskboard_routes.py
- [ ] GW-1.2: Agent registry table (SQLite + migration)
- [ ] GW-1.3: API key auth middleware
- [ ] GW-1.4: Gateway routes — register, tasks list, claim, complete, status
- [ ] GW-1.5: Register gateway_router in routes/__init__.py

## Phase 2: Models + SSE [Opus]

**Owner: Opus (claude-code)**

- [ ] GW-2.1: Pydantic models for gateway API (request/response schemas)
- [ ] GW-2.2: SSE stream endpoint for real-time task updates
- [ ] GW-2.3: Audit log table + middleware logging

## Phase 3: Admin + Security [Opus]

**Owner: Opus (claude-code)**

- [ ] GW-3.1: Admin endpoints (list agents, suspend, rotate key)
- [ ] GW-3.2: Rate limiting middleware (per API key)
- [ ] GW-3.3: Gateway tests (test_agent_gateway.py)

## Phase 4: Polish + Docs [Opus]

**Owner: Opus (claude-code)**

- [ ] GW-4.1: API documentation (AGENT_GATEWAY_API.md)
- [ ] GW-4.2: CORS restrictions for /api/gateway/*

## Phase 5: Integration [Both]

**Owner: Both**

- [ ] GW-5.1: Merge branches via TaskBoard merge_request
- [ ] GW-5.2: End-to-end test (register → claim → complete)
- [ ] GW-5.3: Gemini demo walkthrough

---

## File Ownership

| File | Owner |
|------|-------|
| src/api/routes/gateway_routes.py | Qwen |
| src/api/middleware/auth.py | Qwen |
| src/api/routes/taskboard_routes.py | Qwen (fix) |
| data/migrations/003_agents.sql | Qwen |
| routes/__init__.py | Qwen |
| src/api/models/gateway.py | Opus |
| src/services/gateway_sse.py | Opus |
| src/api/middleware/audit.py | Opus |
| src/api/routes/gateway_admin_routes.py | Opus |
| tests/test_agent_gateway.py | Opus |
| docs/.../AGENT_GATEWAY_API.md | Opus |
