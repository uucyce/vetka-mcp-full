# VETKA Phase 22-MCP-3: Security & Audit Layer

## 🎯 ЗАДАЧА
Добавить security layer к MCP серверу: аутентификация, rate limiting, audit logging, approval flow.

## 📋 ШАГ 1: АНАЛИЗ (выполни перед кодом)

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Текущее состояние MCP
echo "=== MCP Server ===" && wc -l src/mcp/mcp_server.py
echo "=== Tools count ===" && ls src/mcp/tools/*.py | wc -l
echo "=== Main.py MCP endpoints ===" && grep -n "/api/mcp" main.py | head -20

# Проверить что есть ChangeLog
echo "=== ChangeLog ===" && ls -la data/changelog/ | tail -5
```

## 📋 ШАГ 2: РЕАЛИЗАЦИЯ

### 2.1 Rate Limiter (src/mcp/rate_limiter.py)

```python
"""Rate limiting for MCP API calls"""
import time
from collections import defaultdict
from typing import Dict, Tuple
from functools import wraps

class RateLimiter:
    """Simple in-memory rate limiter per client"""
    
    def __init__(self, max_calls: int = 60, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """Check if client can make a call. Returns (allowed, retry_after_seconds)"""
        now = time.time()
        # Clean old entries
        self.calls[client_id] = [t for t in self.calls[client_id] if now - t < self.window]
        
        if len(self.calls[client_id]) >= self.max_calls:
            oldest = min(self.calls[client_id])
            retry_after = int(self.window - (now - oldest)) + 1
            return False, retry_after
        
        self.calls[client_id].append(now)
        return True, 0
    
    def get_usage(self, client_id: str) -> Dict:
        """Get current usage stats for client"""
        now = time.time()
        self.calls[client_id] = [t for t in self.calls[client_id] if now - t < self.window]
        return {
            "calls_made": len(self.calls[client_id]),
            "calls_remaining": max(0, self.max_calls - len(self.calls[client_id])),
            "window_seconds": self.window
        }


# Global rate limiters
api_limiter = RateLimiter(max_calls=60, window_seconds=60)  # 60/min for API
write_limiter = RateLimiter(max_calls=10, window_seconds=60)  # 10/min for writes
```

### 2.2 Audit Logger (src/mcp/audit_logger.py)

```python
"""Audit logging for MCP tool calls"""
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

class MCPAuditLogger:
    """Log all MCP tool calls to audit file"""
    
    def __init__(self, log_dir: str = "data/mcp_audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_file(self) -> Path:
        """Get today's log file"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"mcp_audit_{date_str}.jsonl"
    
    def log_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_id: str,
        success: bool,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """Log a tool call"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id,
            "tool": tool_name,
            "arguments": self._sanitize_args(arguments),
            "success": success,
            "duration_ms": duration_ms,
        }
        
        if error:
            entry["error"] = error
        
        # Don't log full results (could be huge), just summary
        if result and success:
            entry["result_summary"] = self._summarize_result(result)
        
        log_file = self._get_log_file()
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def _sanitize_args(self, args: Dict) -> Dict:
        """Remove sensitive data from args"""
        sanitized = {}
        for k, v in args.items():
            if k in ("content", "password", "token", "api_key"):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str) and len(v) > 500:
                sanitized[k] = v[:500] + "...[truncated]"
            else:
                sanitized[k] = v
        return sanitized
    
    def _summarize_result(self, result: Any) -> str:
        """Create short summary of result"""
        if isinstance(result, dict):
            if "count" in result:
                return f"count={result['count']}"
            if "success" in result:
                return f"success={result['success']}"
            return f"keys={list(result.keys())[:5]}"
        return str(type(result).__name__)
    
    def get_recent_calls(self, limit: int = 100) -> list:
        """Get recent audit entries"""
        log_file = self._get_log_file()
        if not log_file.exists():
            return []
        
        entries = []
        with open(log_file, "r") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        return entries[-limit:]


# Global audit logger
audit_logger = MCPAuditLogger()
```

### 2.3 Approval Flow (src/mcp/approval.py)

```python
"""Human-in-the-loop approval for dangerous operations"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from enum import Enum

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ApprovalManager:
    """Manage approval requests for dangerous operations"""
    
    # Tools that require approval
    DANGEROUS_TOOLS = {
        "vetka_edit_file": "File modification",
        "vetka_git_commit": "Git commit", 
        "vetka_create_branch": "Create folder",
        "vetka_run_tests": "Execute code"
    }
    
    def __init__(self, expiry_minutes: int = 5):
        self.expiry = timedelta(minutes=expiry_minutes)
        self.pending: Dict[str, Dict] = {}  # request_id -> request data
    
    def needs_approval(self, tool_name: str, dry_run: bool = True) -> bool:
        """Check if tool call needs human approval"""
        if dry_run:
            return False  # Dry run never needs approval
        return tool_name in self.DANGEROUS_TOOLS
    
    def create_request(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_id: str
    ) -> Dict:
        """Create approval request, return request details"""
        request_id = str(uuid.uuid4())[:8]
        
        request = {
            "id": request_id,
            "tool": tool_name,
            "description": self.DANGEROUS_TOOLS.get(tool_name, "Unknown operation"),
            "arguments": arguments,
            "client_id": client_id,
            "status": ApprovalStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + self.expiry).isoformat()
        }
        
        self.pending[request_id] = request
        return request
    
    def approve(self, request_id: str) -> Optional[Dict]:
        """Approve a pending request"""
        if request_id not in self.pending:
            return None
        
        request = self.pending[request_id]
        
        # Check expiry
        expires = datetime.fromisoformat(request["expires_at"])
        if datetime.now() > expires:
            request["status"] = ApprovalStatus.EXPIRED.value
            return request
        
        request["status"] = ApprovalStatus.APPROVED.value
        request["approved_at"] = datetime.now().isoformat()
        return request
    
    def reject(self, request_id: str, reason: str = "") -> Optional[Dict]:
        """Reject a pending request"""
        if request_id not in self.pending:
            return None
        
        request = self.pending[request_id]
        request["status"] = ApprovalStatus.REJECTED.value
        request["rejected_at"] = datetime.now().isoformat()
        request["rejection_reason"] = reason
        return request
    
    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get request by ID"""
        return self.pending.get(request_id)
    
    def get_pending(self) -> list:
        """Get all pending requests"""
        now = datetime.now()
        pending = []
        for req in self.pending.values():
            if req["status"] == ApprovalStatus.PENDING.value:
                expires = datetime.fromisoformat(req["expires_at"])
                if now <= expires:
                    pending.append(req)
                else:
                    req["status"] = ApprovalStatus.EXPIRED.value
        return pending
    
    def cleanup_expired(self):
        """Remove expired requests older than 1 hour"""
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        to_remove = []
        for req_id, req in self.pending.items():
            created = datetime.fromisoformat(req["created_at"])
            if created < cutoff:
                to_remove.append(req_id)
        for req_id in to_remove:
            del self.pending[req_id]


# Global approval manager
approval_manager = ApprovalManager()
```

### 2.4 Обновить mcp_server.py

Добавь в начало файла импорты и интеграцию:

```python
# В начало src/mcp/mcp_server.py добавить:
import time
from .rate_limiter import api_limiter, write_limiter
from .audit_logger import audit_logger
from .approval import approval_manager

# Обернуть handle_tool_call:
def handle_tool_call_with_security(data: dict, client_id: str = "anonymous"):
    """Handle tool call with rate limiting, audit, and approval"""
    tool_name = data.get("name", "")
    arguments = data.get("arguments", {})
    request_id = data.get("id", "")
    
    start_time = time.time()
    
    # 1. Rate limiting
    is_write = tool_name in ("vetka_edit_file", "vetka_git_commit", "vetka_create_branch")
    limiter = write_limiter if is_write else api_limiter
    
    allowed, retry_after = limiter.is_allowed(client_id)
    if not allowed:
        audit_logger.log_call(tool_name, arguments, client_id, False, error="rate_limited")
        return {
            "id": request_id,
            "success": False,
            "error": f"Rate limited. Retry after {retry_after} seconds",
            "retry_after": retry_after
        }
    
    # 2. Approval check (only for non-dry-run writes)
    dry_run = arguments.get("dry_run", True)
    if approval_manager.needs_approval(tool_name, dry_run):
        # Check if we have an approval_id
        approval_id = arguments.pop("_approval_id", None)
        if approval_id:
            approval = approval_manager.get_request(approval_id)
            if not approval or approval["status"] != "approved":
                return {
                    "id": request_id,
                    "success": False,
                    "error": f"Invalid or expired approval: {approval_id}"
                }
        else:
            # Create approval request
            req = approval_manager.create_request(tool_name, arguments, client_id)
            return {
                "id": request_id,
                "success": False,
                "needs_approval": True,
                "approval_request": req,
                "message": f"This operation requires approval. Use approval_id={req['id']} after approval."
            }
    
    # 3. Execute tool
    try:
        result = execute_tool(tool_name, arguments)  # existing function
        duration_ms = (time.time() - start_time) * 1000
        
        audit_logger.log_call(
            tool_name, arguments, client_id, 
            result.get("success", False),
            result.get("result"),
            result.get("error"),
            duration_ms
        )
        
        return {"id": request_id, **result}
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_call(tool_name, arguments, client_id, False, error=str(e), duration_ms=duration_ms)
        return {"id": request_id, "success": False, "error": str(e)}
```

### 2.5 Добавить REST endpoints в main.py

```python
# Добавить после существующих /api/mcp/* endpoints:

@app.route('/api/mcp/rate-limit', methods=['GET'])
def mcp_rate_limit_status():
    """Get rate limit status for client"""
    client_id = request.headers.get('X-Client-ID', request.remote_addr)
    from src.mcp.rate_limiter import api_limiter, write_limiter
    return jsonify({
        "client_id": client_id,
        "api": api_limiter.get_usage(client_id),
        "write": write_limiter.get_usage(client_id)
    })

@app.route('/api/mcp/audit', methods=['GET'])
def mcp_audit_log():
    """Get recent audit entries"""
    limit = request.args.get('limit', 50, type=int)
    from src.mcp.audit_logger import audit_logger
    entries = audit_logger.get_recent_calls(min(limit, 200))
    return jsonify({"count": len(entries), "entries": entries})

@app.route('/api/mcp/approvals', methods=['GET'])
def mcp_pending_approvals():
    """Get pending approval requests"""
    from src.mcp.approval import approval_manager
    pending = approval_manager.get_pending()
    return jsonify({"count": len(pending), "pending": pending})

@app.route('/api/mcp/approvals/<request_id>/approve', methods=['POST'])
def mcp_approve(request_id):
    """Approve a pending request"""
    from src.mcp.approval import approval_manager
    result = approval_manager.approve(request_id)
    if result:
        return jsonify({"success": True, "request": result})
    return jsonify({"success": False, "error": "Request not found"}), 404

@app.route('/api/mcp/approvals/<request_id>/reject', methods=['POST'])
def mcp_reject(request_id):
    """Reject a pending request"""
    from src.mcp.approval import approval_manager
    reason = request.json.get('reason', '') if request.json else ''
    result = approval_manager.reject(request_id, reason)
    if result:
        return jsonify({"success": True, "request": result})
    return jsonify({"success": False, "error": "Request not found"}), 404
```

## 📋 ШАГ 3: ТЕСТЫ

Добавь в `tests/test_mcp_server.py`:

```python
# ============================================================
# PHASE 22-MCP-3 TESTS
# ============================================================

def test_21_rate_limiter():
    """Test rate limiting"""
    from src.mcp.rate_limiter import RateLimiter
    limiter = RateLimiter(max_calls=3, window_seconds=60)
    
    # First 3 calls allowed
    assert limiter.is_allowed("test")[0] == True
    assert limiter.is_allowed("test")[0] == True
    assert limiter.is_allowed("test")[0] == True
    
    # 4th call blocked
    allowed, retry = limiter.is_allowed("test")
    assert allowed == False
    assert retry > 0
    
    print("✅ Test 21: Rate limiter works")

def test_22_audit_logger():
    """Test audit logging"""
    from src.mcp.audit_logger import MCPAuditLogger
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = MCPAuditLogger(log_dir=tmpdir)
        logger.log_call("vetka_search", {"query": "test"}, "client1", True, {"count": 5})
        
        entries = logger.get_recent_calls()
        assert len(entries) == 1
        assert entries[0]["tool"] == "vetka_search"
        assert entries[0]["success"] == True
    
    print("✅ Test 22: Audit logger works")

def test_23_approval_manager():
    """Test approval flow"""
    from src.mcp.approval import ApprovalManager
    
    manager = ApprovalManager(expiry_minutes=5)
    
    # Check dangerous tools
    assert manager.needs_approval("vetka_edit_file", dry_run=False) == True
    assert manager.needs_approval("vetka_edit_file", dry_run=True) == False
    assert manager.needs_approval("vetka_search", dry_run=False) == False
    
    # Create and approve request
    req = manager.create_request("vetka_edit_file", {"path": "test.txt"}, "client1")
    assert req["status"] == "pending"
    
    result = manager.approve(req["id"])
    assert result["status"] == "approved"
    
    print("✅ Test 23: Approval manager works")

def test_24_rate_limit_endpoint():
    """Test rate limit status endpoint"""
    response = requests.get(f"{BASE_URL}/api/mcp/rate-limit")
    assert response.status_code == 200
    data = response.json()
    assert "api" in data
    assert "write" in data
    print("✅ Test 24: Rate limit endpoint works")

def test_25_audit_endpoint():
    """Test audit log endpoint"""
    response = requests.get(f"{BASE_URL}/api/mcp/audit?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    print("✅ Test 25: Audit endpoint works")

def test_26_approvals_endpoint():
    """Test approvals endpoint"""
    response = requests.get(f"{BASE_URL}/api/mcp/approvals")
    assert response.status_code == 200
    data = response.json()
    assert "pending" in data
    print("✅ Test 26: Approvals endpoint works")
```

## 📋 ШАГ 4: ОБНОВИТЬ __init__.py

```python
# src/mcp/__init__.py - добавить:
from .rate_limiter import api_limiter, write_limiter, RateLimiter
from .audit_logger import audit_logger, MCPAuditLogger
from .approval import approval_manager, ApprovalManager, ApprovalStatus
```

## ✅ КРИТЕРИИ УСПЕХА

- [ ] Rate limiter: 60 req/min для API, 10 req/min для writes
- [ ] Audit logger: все вызовы логируются в `data/mcp_audit/`
- [ ] Approval flow: write операции с `dry_run=false` требуют approval
- [ ] REST endpoints: `/api/mcp/rate-limit`, `/api/mcp/audit`, `/api/mcp/approvals`
- [ ] 6 новых тестов проходят (tests 21-26)

## 📁 НОВЫЕ ФАЙЛЫ

```
src/mcp/
├── rate_limiter.py    (NEW)
├── audit_logger.py    (NEW)
├── approval.py        (NEW)
├── mcp_server.py      (MODIFIED)
└── __init__.py        (MODIFIED)

data/mcp_audit/        (NEW DIRECTORY)
└── mcp_audit_YYYY-MM-DD.jsonl
```

## 🔄 ПОСЛЕ ЗАВЕРШЕНИЯ

1. Запусти тесты: `python tests/test_mcp_server.py`
2. Проверь endpoints вручную:
   ```bash
   curl http://localhost:5001/api/mcp/rate-limit
   curl http://localhost:5001/api/mcp/audit?limit=5
   curl http://localhost:5001/api/mcp/approvals
   ```
3. Сообщи результаты!
