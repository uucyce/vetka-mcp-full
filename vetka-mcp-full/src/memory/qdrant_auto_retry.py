"""
QDRANT AUTO-RETRY for PHASE 7.4.

Background retry connection with exponential backoff.
Solves: Qdrant warning spam if service unavailable at startup.

@status: active
@phase: 96
@depends: qdrant_client, threading
@used_by: singletons.py, qdrant_client.py
"""

import threading
import time
import logging
from typing import Optional, Callable
from qdrant_client import QdrantClient

# Handle different qdrant-client versions - APIError may not exist in newer versions
try:
    from qdrant_client.http.exceptions import UnexpectedResponse, ApiException as APIError
except ImportError:
    try:
        from qdrant_client.http.exceptions import UnexpectedResponse
        # Create a dummy APIError if not available
        class APIError(Exception):
            pass
    except ImportError:
        # Fallback for very old versions
        class UnexpectedResponse(Exception):
            pass
        class APIError(Exception):
            pass

logger = logging.getLogger(__name__)

# MARKER_ENGRAM_QDRANT_FIX: Error handling for Qdrant 400 Bad Request
# Problem: Some 400 errors from vector format issues are not being caught/logged
# Audit needed: Check if UnexpectedResponse exceptions include 400 errors
# TODO: Add specific 400 Bad Request handler for vector validation


class QdrantAutoRetry:
    """
    Background Qdrant connection manager with exponential backoff
    
    Features:
    - Silent retry if Qdrant unavailable at startup
    - Exponential backoff (2s, 4s, 8s, 16s, 32s)
    - Background thread (daemon, non-blocking)
    - Health status queries
    - Callback on successful connection
    - Thread-safe operations
    """
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 6333,
                 max_retries: int = 5,
                 on_connected: Optional[Callable] = None):
        """
        Initialize Qdrant auto-retry manager
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            max_retries: Maximum retry attempts before giving up
            on_connected: Callback function when connection successful
        """
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.on_connected = on_connected
        
        self.client: Optional[QdrantClient] = None
        self.is_connected = False
        self.is_attempting = False
        self.retry_count = 0
        
        # Thread lock
        self.lock = threading.RLock()
        
        # Start background retry thread immediately
        self._start_background_retry()
    
    def _start_background_retry(self):
        """Start background retry thread"""
        thread = threading.Thread(
            target=self._retry_loop,
            daemon=True,
            name=f"QdrantAutoRetry-{self.host}:{self.port}"
        )
        thread.start()
        logger.debug(f"🔄 Qdrant auto-retry thread started")
    
    def _retry_loop(self):
        """Background retry loop with exponential backoff"""
        gave_up_logged = False
        while True:
            try:
                with self.lock:
                    if self.is_connected:
                        # Already connected, stop retrying
                        break
                
                self._attempt_connection()
                
                if self.is_connected:
                    # Connection successful!
                    logger.debug(
                        f"Qdrant connected (attempt #{self.retry_count + 1} of {self.max_retries})"
                    )
                    
                    # Call callback if provided
                    if self.on_connected:
                        try:
                            self.on_connected()
                        except Exception as e:
                            logger.error(f"⚠️  Callback error: {e}")
                    
                    break
                
            except Exception as e:
                # Silently handle errors in retry loop
                pass
            
            # Retry strategy:
            # - First max_retries attempts: exponential backoff (1,2,4,8,...)
            # - Afterwards: keep retrying in background every 10s (never give up)
            if self.retry_count < self.max_retries:
                backoff_time = 2 ** self.retry_count
                logger.debug(
                    f"⏳ Qdrant reconnect attempt {self.retry_count + 1}/{self.max_retries} "
                    f"failed, retrying in {backoff_time}s..."
                )
            else:
                backoff_time = 10
                if not gave_up_logged:
                    logger.warning(
                        f"⚠️  Qdrant connection failed after {self.max_retries} attempts. "
                        "Switching to continuous background retry (10s interval)."
                    )
                    gave_up_logged = True
                else:
                    logger.debug("⏳ Qdrant still unavailable, background retry in 10s...")

            time.sleep(backoff_time)
            self.retry_count += 1

    def add_conversation_vector(self, *args, **kwargs):
        """
        Phase 27.11: Proxy method for MemoryManager compatibility.
        Attempts to call add_conversation_vector on the underlying client
        or logs warning if functionality is missing.
        """
        with self.lock:
            if self.is_ready() and hasattr(self.client, 'add_conversation_vector'):
                return self.client.add_conversation_vector(*args, **kwargs)
            elif not self.is_ready():
                logger.warning("⚠️ Cannot add vector: Qdrant not connected")
                return None
            else:
                # Stub - log but don't crash
                logger.debug("⚠️ add_conversation_vector called on QdrantAutoRetry (method stub)")
                return None

    def _attempt_connection(self) -> bool:
        """Attempt to connect to Qdrant with fallback to /readyz endpoint"""
        try:
            with self.lock:
                print(f"🔌 Attempting Qdrant connection to {self.host}:{self.port}...")
                
                # Create client - use URL to force HTTP
                import socket
                resolved_ip = socket.gethostbyname(self.host)
                print(f"   🔍 Resolved {self.host} -> {resolved_ip}")
                
                # Use url= to force HTTP protocol (not gRPC)
                test_client = QdrantClient(
                    url=f"http://{self.host}:{self.port}",
                    timeout=3.0,
                )
                
                print(f"   ✓ QdrantClient created")
                
                # Try primary health check: get_collections
                health_ok = False
                try:
                    print(f"   🚀 Calling get_collections()...")
                    test_client.get_collections()
                    print(f"   ✓ get_collections() successful")
                    health_ok = True
                except Exception as e:
                    print(f"   ⚠ get_collections FAILED: {type(e).__name__}: {e}")
                    # Try raw HTTP request to debug
                    print(f"   ↻ Trying /readyz health endpoint...")
                    try:
                        import requests
                        url = f"http://{self.host}:{self.port}/readyz"
                        print(f"   ↻ Trying {url}...")
                        session = requests.Session()
                        session.trust_env = False
                        resp = session.get(url, timeout=2)
                        print(f"   ↻ Response status: {resp.status_code}, body: {resp.text[:50]}")
                        if resp.status_code == 200 or "ready" in resp.text.lower():
                            print(f"   ✓ /readyz health check passed")
                            health_ok = True
                        else:
                            print(f"   ❌ /readyz returned {resp.status_code}")
                    except Exception as req_e:
                        print(f"   ❌ /readyz check failed: {req_e}")
                
                if not health_ok:
                    self.client = None
                    self.is_connected = False
                    self.is_attempting = False
                    print("   ⏳ Qdrant not ready yet, will retry...")
                    return False

                self.client = test_client
                self.is_connected = True
                self.is_attempting = False
                print("✅ Qdrant connection SUCCESSFUL (health check passed)!")
                return True
        
        except (ConnectionError, TimeoutError, APIError, UnexpectedResponse) as e:
            # Expected errors - Qdrant not ready yet
            print(f"   ❌ {type(e).__name__}: {e}")
            self.is_connected = False
            self.is_attempting = False
            return False
        
        except Exception as e:
            # Unexpected error
            print(f"   ❌ Connection error: {e}")
            logger.debug(f"Unexpected error connecting to Qdrant: {e}")
            self.is_connected = False
            self.is_attempting = False
            return False
    
    def get_client(self) -> Optional[QdrantClient]:
        """Get Qdrant client if connected"""
        with self.lock:
            if self.is_connected and self.client:
                return self.client
            return None
    
    def is_ready(self) -> bool:
        """Check if Qdrant is ready to use"""
        with self.lock:
            return self.is_connected and self.client is not None
    
    def get_status(self) -> dict:
        """Get current connection status"""
        with self.lock:
            return {
                'host': self.host,
                'port': self.port,
                'connected': self.is_connected,
                'retry_count': self.retry_count,
                'max_retries': self.max_retries,
                'status': 'connected' if self.is_connected else 'disconnected',
                'message': (
                    f"Connected (attempt #{self.retry_count + 1})" 
                    if self.is_connected 
                    else f"Retrying... (attempt {self.retry_count}/{self.max_retries})"
                )
            }
    
    def manual_connect(self, timeout: float = 5.0) -> bool:
        """Manually attempt connection (blocking)"""
        try:
            test_client = QdrantClient(
                url=f"http://{self.host}:{self.port}",
                timeout=int(timeout),
            )
            test_client.get_collections()
            
            with self.lock:
                self.client = test_client
                self.is_connected = True
            
            logger.debug("Qdrant manually connected")
            return True

        except Exception as e:
            logger.warning(f"Manual Qdrant connection failed: {e}")
            return False

    def disconnect(self):
        """Manually disconnect"""
        with self.lock:
            self.client = None
            self.is_connected = False
        logger.debug("Qdrant disconnected")

    def reset_retries(self):
        """Reset retry counter and attempt connection again"""
        with self.lock:
            self.retry_count = 0
            self.is_connected = False

        self._start_background_retry()
        logger.debug("Qdrant retry counter reset, attempting reconnection")


# Singleton instance
_qdrant_auto_retry = None


def init_qdrant_auto_retry(host: str = 'localhost',
                          port: int = 6333,
                          max_retries: int = 5,
                          on_connected: Optional[Callable] = None) -> QdrantAutoRetry:
    """Initialize global Qdrant auto-retry manager"""
    global _qdrant_auto_retry
    _qdrant_auto_retry = QdrantAutoRetry(
        host=host,
        port=port,
        max_retries=max_retries,
        on_connected=on_connected
    )
    return _qdrant_auto_retry


def get_qdrant_auto_retry() -> Optional[QdrantAutoRetry]:
    """Get global Qdrant auto-retry manager"""
    return _qdrant_auto_retry


# ============ INTEGRATION EXAMPLE ============
"""
# In main.py or initialization:

from src.memory.qdrant_auto_retry import init_qdrant_auto_retry

def on_qdrant_connected():
    print("🎉 Qdrant is now available!")
    # Trigger any deferred operations

# Initialize with callback
qdrant_manager = init_qdrant_auto_retry(
    host='localhost',
    port=6333,
    max_retries=5,
    on_connected=on_qdrant_connected
)

# Later, in code:
qdrant_mgr = get_qdrant_auto_retry()
if qdrant_mgr and qdrant_mgr.is_ready():
    client = qdrant_mgr.get_client()
    # Use client
"""
