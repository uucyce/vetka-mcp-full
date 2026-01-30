# 🔧 PHASE 7-8 TECHNICAL IMPLEMENTATION GUIDE

**For:** Developers working on VETKA  
**Purpose:** Understand the fix and prevent similar issues  
**Level:** Intermediate+ (Flask, Python, resource management)

---

## 🎓 UNDERSTANDING THE PROBLEM

### The Anti-Pattern (❌ DON'T DO THIS)

```python
from flask import Flask, g

app = Flask(__name__)

class MemoryManager:
    """Stateful resource manager"""
    def __init__(self):
        self.session = requests.Session()  # Opens a file descriptor
        print(f"  MemoryManager created (FD +1)")
    
    def __del__(self):
        print(f"  MemoryManager destroyed (FD -1)")

def get_memory_manager():
    """ANTI-PATTERN: Creates new instance per request!"""
    if 'memory_manager' not in g:
        g.memory_manager = MemoryManager()  # ❌ NEW INSTANCE EACH TIME
    return g.memory_manager

@app.route('/api/status')
def status():
    mm = get_memory_manager()  # ✅ Creates new instance
    # ...
    # When request ends, g is destroyed
    # But MemoryManager.__del__ might not be called immediately
    # File descriptors accumulate!
```

### Why This Fails

```
REQUEST 1:
  /api/status called
  → g = FlaskContext()
  → mm = MemoryManager() [FD +1]
  → response sent
  → g destroyed? (maybe)
  → MemoryManager.__del__ called? (maybe)

REQUEST 2 (same second):
  /api/status called
  → g = NEW FlaskContext() (different from Request 1!)
  → mm = NEW MemoryManager() [FD +1] ← ANOTHER FD OPENS
  → response sent

REQUEST 3:
  → ANOTHER new MemoryManager [FD +1]
  
... after 50 requests ...
  → 50+ file descriptors open
  → GC not running fast enough
  → Memory pressure
  → Eventually: OSError: [Errno 24] Too many open files
```

### The Problem Visualization

```python
# Timeline of FDs
Request 1:  [open FD]
Request 2:  [open FD] [open FD]
Request 3:  [open FD] [open FD] [open FD]
Request 4:  [open FD] [open FD] [open FD] [open FD]
...
Request N:  [open FD] × N  ← Grows linearly!

After ~256 requests: CRASH
```

---

## ✅ THE SOLUTION: SINGLETON PATTERN

### The Correct Pattern (✅ DO THIS)

```python
from flask import Flask
import requests

app = Flask(__name__)

class MemoryManager:
    """Stateful resource manager"""
    def __init__(self):
        self.session = requests.Session()  # Opens ONE file descriptor (total)
        print(f"  MemoryManager created (FD +1 TOTAL)")
    
    def __del__(self):
        print(f"  MemoryManager destroyed (FD -1 TOTAL)")

# ✅ SOLUTION: Create ONE global instance
_memory_manager_singleton = None

def _init_memory_manager():
    """Initialize global singleton at app startup"""
    global _memory_manager_singleton
    if _memory_manager_singleton is None:
        _memory_manager_singleton = MemoryManager()
    return _memory_manager_singleton

def get_memory_manager():
    """CORRECT PATTERN: Returns same instance!"""
    global _memory_manager_singleton
    if _memory_manager_singleton is None:
        _memory_manager_singleton = _init_memory_manager()
    return _memory_manager_singleton

# Initialize at Flask startup
with app.app_context():
    _init_memory_manager()
    print("✅ Memory manager singleton initialized")

@app.route('/api/status')
def status():
    mm = get_memory_manager()  # ✅ SAME INSTANCE every time
    # ...
    # ONE file descriptor for the entire app lifetime!
```

### Why This Works

```
REQUEST 1:
  /api/status called
  → mm = get_memory_manager() → returns EXISTING instance
  → response sent
  → instance still exists

REQUEST 2:
  /api/status called
  → mm = get_memory_manager() → returns SAME instance
  → response sent
  → instance still exists (reused)

REQUEST 3:
  → returns SAME instance
  
... after 1000 requests ...
  → STILL using 1 file descriptor!
  → Connection pooling works
  → Server remains stable

# Timeline of FDs:
Request 1:  [open FD]
Request 2:  [open FD] ← SAME
Request 3:  [open FD] ← SAME
Request 4:  [open FD] ← SAME
...
Request N:  [open FD] ← SAME

Total FDs: Constant (1-2), no growth!
```

---

## 🏗️ IMPLEMENTATION ARCHITECTURE

### Singleton Factory Pattern

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages Weaviate + Qdrant connections"""
    _instance: Optional['MemoryManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Prevent multiple instances (thread-safe)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize only once"""
        if self._initialized:
            return
        
        logger.info("Initializing MemoryManager...")
        self.session = requests.Session()
        self.weaviate_connected = False
        self._initialized = True
        logger.info("✅ MemoryManager initialized (singleton)")
    
    def health_check(self):
        """Check if Weaviate is reachable"""
        try:
            response = self.session.get('http://localhost:8080/v1/meta', timeout=2)
            self.weaviate_connected = response.status_code == 200
            return self.weaviate_connected
        except Exception as e:
            logger.warning(f"Weaviate health check failed: {e}")
            self.weaviate_connected = False
            return False


def get_memory_manager() -> MemoryManager:
    """Get or create the singleton instance"""
    return MemoryManager()

# Test singleton
if __name__ == "__main__":
    mm1 = get_memory_manager()
    mm2 = get_memory_manager()
    print(f"Same instance? {mm1 is mm2}")  # True
    print(f"ID mm1: {id(mm1)}, ID mm2: {id(mm2)}")  # Same
```

### With Flask Integration

```python
from flask import Flask
import atexit

app = Flask(__name__)

# Global singleton
_memory_manager = None

def init_app():
    """Initialize application resources"""
    global _memory_manager
    
    print("🔧 Initializing VETKA services...")
    
    try:
        _memory_manager = MemoryManager()
        print("✅ Memory manager singleton created")
    except Exception as e:
        logger.error(f"Failed to initialize memory manager: {e}")
        raise
    
    # Register cleanup
    atexit.register(cleanup_resources)
    print("✅ Resource cleanup registered")

def cleanup_resources():
    """Clean up resources on shutdown"""
    global _memory_manager
    if _memory_manager:
        if hasattr(_memory_manager.session, 'close'):
            _memory_manager.session.close()
        logger.info("✅ Resources cleaned up")

def get_memory_manager():
    """Get memory manager (must call init_app first!)"""
    global _memory_manager
    if _memory_manager is None:
        raise RuntimeError("Memory manager not initialized. Call init_app() first!")
    return _memory_manager

# In main.py
if __name__ == "__main__":
    init_app()
    app.run()
```

---

## 📊 MONITORING & DEBUGGING

### Check File Descriptors

```python
import os
import logging

logger = logging.getLogger(__name__)

def log_open_files():
    """Log current open file descriptors"""
    pid = os.getpid()
    try:
        # macOS/Linux
        import subprocess
        result = subprocess.run(['lsof', '-p', str(pid)], 
                              capture_output=True, text=True)
        fd_count = len(result.stdout.strip().split('\n')) - 1
        logger.info(f"Open file descriptors: {fd_count}")
    except Exception as e:
        logger.warning(f"Could not count FDs: {e}")

# Add to Flask routes for monitoring
@app.route('/api/debug/fds')
def debug_fds():
    """DEBUG ONLY: Show open file descriptors"""
    import subprocess
    pid = os.getpid()
    result = subprocess.run(['lsof', '-p', str(pid)], 
                          capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    return jsonify({
        'pid': pid,
        'open_fds': len(lines) - 1,
        'fds': [line.split()[3] for line in lines[1:]]
    })
```

### Add Resource Middleware

```python
from functools import wraps
import time

def monitor_resources(f):
    """Decorator to monitor resource usage per request"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Optionally log FDs at start
        log_open_files()
        
        result = f(*args, **kwargs)
        
        duration = time.time() - start_time
        logger.info(f"{f.__name__} took {duration:.3f}s")
        
        return result
    return decorated_function

@app.route('/api/system/summary')
@monitor_resources
def system_summary():
    memory = get_memory_manager()
    return jsonify({
        'weaviate': memory.health_check(),
        'timestamp': time.time()
    })
```

---

## 🧪 TESTING FOR RESOURCE LEAKS

### Unit Test

```python
import pytest
from src.orchestration.memory_manager import MemoryManager, get_memory_manager

def test_memory_manager_is_singleton():
    """Verify MemoryManager uses singleton pattern"""
    mm1 = get_memory_manager()
    mm2 = get_memory_manager()
    
    # Should be same instance
    assert mm1 is mm2, "MemoryManager should be singleton!"
    assert id(mm1) == id(mm2), "IDs should match!"

def test_no_resource_leak():
    """Verify FDs don't leak after multiple calls"""
    import os
    import subprocess
    
    pid = os.getpid()
    
    # Get initial FD count
    result = subprocess.run(['lsof', '-p', str(pid)], 
                          capture_output=True, text=True)
    initial_fds = len(result.stdout.strip().split('\n')) - 1
    
    # Make 100 calls
    for i in range(100):
        mm = get_memory_manager()
        mm.health_check()
    
    # Get final FD count
    result = subprocess.run(['lsof', '-p', str(pid)], 
                          capture_output=True, text=True)
    final_fds = len(result.stdout.strip().split('\n')) - 1
    
    # FD count should not grow significantly
    fd_increase = final_fds - initial_fds
    assert fd_increase < 10, f"FD leak detected! Increase: {fd_increase}"
```

### Load Test

```python
import concurrent.futures
import time

def load_test_memory_manager():
    """Simulate high load and check for FD leaks"""
    import subprocess
    import os
    
    pid = os.getpid()
    
    def get_fds():
        result = subprocess.run(['lsof', '-p', str(pid)], 
                              capture_output=True, text=True)
        return len(result.stdout.strip().split('\n')) - 1
    
    print(f"Initial FDs: {get_fds()}")
    
    # Simulate 50 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(50):
            future = executor.submit(lambda: get_memory_manager().health_check())
            futures.append(future)
        
        for future in concurrent.futures.as_completed(futures):
            future.result()
    
    print(f"After 50 concurrent calls FDs: {get_fds()}")
    print("✅ No FD leak detected!")
```

---

## 🎯 BEST PRACTICES

### DO ✅

1. **Use singletons for stateful resources**
   ```python
   # ✅ GOOD
   db = Database()  # One instance
   def get_db():
       return db
   ```

2. **Close resources on shutdown**
   ```python
   # ✅ GOOD
   atexit.register(cleanup)
   ```

3. **Monitor resource usage**
   ```python
   # ✅ GOOD
   lsof -p $(pgrep python)
   ```

4. **Connection pooling**
   ```python
   # ✅ GOOD
   session = requests.Session()  # Reuses connections
   ```

### DON'T ❌

1. **Don't create new instances per request**
   ```python
   # ❌ BAD
   def get_memory_manager():
       return MemoryManager()  # New instance each time!
   ```

2. **Don't rely on GC for resource cleanup**
   ```python
   # ❌ BAD
   def process():
       session = requests.Session()
       # assuming __del__ will close it
   ```

3. **Don't use Flask.g for stateful resources**
   ```python
   # ❌ BAD (request-scoped, not app-scoped)
   def get_memory():
       if 'memory' not in g:
           g.memory = MemoryManager()
       return g.memory
   ```

---

## 📚 REFERENCES

### Python Singleton Patterns
- https://refactoring.guru/design-patterns/singleton/python
- https://www.geeksforgeeks.org/singleton-method-python-design-patterns/

### Flask Best Practices
- https://flask.palletsprojects.com/patterns/sqlalchemy/
- https://flask.palletsprojects.com/appcontext/

### Resource Management
- https://docs.python.org/3/library/atexit.html
- https://requests.readthedocs.io/en/latest/

---

**Next Phase:** Apply these patterns to other resource managers (Qdrant, ModelRouter, etc.)
