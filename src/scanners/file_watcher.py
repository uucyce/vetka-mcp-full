"""
VETKA File Watcher - Real-Time File System Monitoring.

@status: active
@phase: 96
@depends: watchdog, threading, src.scanners.qdrant_updater, src.memory.qdrant_client,
          src.initialization.components_init
@used_by: src.api.routes.watcher_routes, src.initialization.components_init

Real-time file watching using watchdog library.
Features:
- Debounced event handling (400ms default)
- Bulk operation detection (git checkout, npm install)
- Smart adaptive scan frequency
- Persistent watch state
- Socket.IO integration for live updates
- Phase 80.17: Lazy Qdrant client fetch (fixes singleton cache bug)
- Phase 80.20: Fix async emit from sync context (AsyncServer.emit is coroutine)
- Phase 90.3: Qdrant retry logic (2s delay, prevents silent skip)
- Phase 96.1: TripleWrite integration for coherent writes
"""

import os
import json
import time
import threading
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Set, Optional, Any

from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver  # FIX_95.9: Fallback for macOS FSEvents issues
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# FIX_95.9: MARKER_WATCHDOG_002 - macOS FSEvents can miss 'created' events
# Set USE_POLLING_OBSERVER=1 to use reliable but slower polling instead
USE_POLLING_OBSERVER = os.environ.get('USE_POLLING_OBSERVER', '0') == '1'
print(f"[Watcher Module] USE_POLLING_OBSERVER = {USE_POLLING_OBSERVER} (env: {os.environ.get('USE_POLLING_OBSERVER', 'NOT SET')})")

# Qdrant integration for real-time indexing
from src.scanners.qdrant_updater import handle_watcher_event


# ============================================================
# CONFIGURATION
# ============================================================

# Directories to skip
SKIP_PATTERNS = [
    '.git', 'node_modules', '__pycache__', '.pyc', '.pyo',
    '.venv', 'venv', 'venv_', 'site-packages',  # FIX_95.11: Added venv_ and site-packages for virtual envs
    '.env', 'dist', 'build', '.idea',
    '.vscode', '.DS_Store', 'Pods', '.gradle', 'target',
    # FIX_95.9.3: Prevent infinite loop - TripleWrite writes to changelog, watchdog sees it, triggers TW again
    'data/changelog', 'changelog_',  # Skip changelog directory and files
    'watcher_state.json',  # Skip watcher's own state file
    'models_cache.json', 'groups.json', 'chat_history.json'  # Skip other data files that change frequently
]

# Supported file extensions for watching
SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml',
    '.md', '.txt', '.html', '.css', '.scss', '.sql', '.sh',
    '.java', '.go', '.rs', '.rb', '.php', '.c', '.cpp', '.h',
    '.swift', '.kt', '.scala', '.vue', '.svelte'
}


# ============================================================
# VETKA FILE HANDLER (Debounced)
# ============================================================

class VetkaFileHandler(FileSystemEventHandler):
    """
    Debounced file system event handler for VETKA.

    Collects events and processes them in batches to handle:
    - Rapid successive edits (editor autosave)
    - Bulk operations (git checkout, npm install)
    """

    def __init__(self, on_change_callback: Callable[[Dict], None], debounce_ms: int = 400):
        """
        Initialize handler.

        Args:
            on_change_callback: Function to call with coalesced event
            debounce_ms: Milliseconds to wait before processing (default: 400)
        """
        super().__init__()
        self.callback = on_change_callback
        self.debounce_ms = debounce_ms
        self.pending: Dict[str, List[Dict]] = defaultdict(list)
        self.timers: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event."""
        # MARKER_90.9_DEBUG_START: Debug logging per Grok/Kimi K2 analysis
        print(f"[DEBUG_WATCHER] Raw event: type={event.event_type}, path={event.src_path}, is_dir={event.is_directory}")
        # MARKER_90.9_DEBUG_END

        # Skip directory events
        if event.is_directory:
            print(f"[DEBUG_WATCHER] SKIP: is_directory=True")
            return

        path = event.src_path

        # Skip ignored patterns
        if self._should_skip(path):
            print(f"[DEBUG_WATCHER] SKIP: matches skip pattern -> {path}")
            return

        # Skip unsupported extensions (if filtering is enabled)
        ext = Path(path).suffix.lower()
        if ext and ext not in SUPPORTED_EXTENSIONS:
            print(f"[DEBUG_WATCHER] SKIP: unsupported extension '{ext}' -> {path}")
            return

        print(f"[DEBUG_WATCHER] PASS: Adding to pending batch -> {path}")

        with self.lock:
            # Add event to pending batch
            self.pending[path].append({
                'type': event.event_type,  # created, modified, deleted, moved
                'path': path,
                'time': time.time()
            })

            # Reset debounce timer for this path
            if path in self.timers:
                self.timers[path].cancel()
                del self.timers[path]  # Fix: Clear reference to prevent memory leak

            self.timers[path] = threading.Timer(
                self.debounce_ms / 1000,
                self._process_batch,
                [path]
            )
            self.timers[path].start()

    def _should_skip(self, path: str) -> bool:
        """Check if path should be skipped."""
        for pattern in SKIP_PATTERNS:
            if pattern in path:
                return True
        return False

    def _process_batch(self, path: str) -> None:
        """Process accumulated events for a path."""
        with self.lock:
            events = self.pending.pop(path, [])
            if path in self.timers:
                del self.timers[path]

        if not events:
            return

        # Coalesce events
        if len(events) > 10:
            # Bulk operation detected (git checkout, npm install, etc.)
            coalesced = {
                'type': 'bulk_update',
                'path': path,
                'count': len(events),
                'events': [e['type'] for e in events]
            }
        else:
            # Single file: use the last event type
            coalesced = events[-1]

        # Call the callback
        self.callback(coalesced)


# ============================================================
# ADAPTIVE SCANNER
# ============================================================

class AdaptiveScanner:
    """
    Adjusts scan frequency based on directory activity.

    Hot directories (frequently modified) get scanned more often.
    Cold directories (rarely touched) get scanned less often.
    """

    def __init__(self):
        self.heat_scores: Dict[str, float] = {}
        self.min_interval = 5      # seconds (hot directories)
        self.max_interval = 300    # seconds (cold directories) = 5 min
        self.decay_factor = 0.95   # hourly decay
        self.last_decay = time.time()

    def get_scan_interval(self, dir_path: str) -> int:
        """
        Get scan interval based on heat score.

        Args:
            dir_path: Directory path

        Returns:
            Scan interval in seconds (5-300)
        """
        score = self.heat_scores.get(dir_path, 0.0)
        # Hot (score=1.0) -> 5s, Cold (score=0.0) -> 300s
        interval = int(self.min_interval + (self.max_interval - self.min_interval) * (1 - score))
        return interval

    def update_heat(self, dir_path: str, event_type: str) -> None:
        """
        Update heat score on activity.

        Args:
            dir_path: Directory path
            event_type: Type of event ('modify', 'create', 'delete', 'access', 'click')
        """
        delta_map = {
            'modified': 0.3,
            'created': 0.2,
            'deleted': 0.2,
            'access': 0.1,
            'click': 0.05,
            'bulk_update': 0.4
        }
        delta = delta_map.get(event_type, 0.05)

        current = self.heat_scores.get(dir_path, 0.0)
        self.heat_scores[dir_path] = min(1.0, current + delta)

    def decay_all(self) -> None:
        """
        Decay heat scores (call hourly via scheduler).
        Removes cold directories from tracking.
        """
        for dir_path in list(self.heat_scores.keys()):
            self.heat_scores[dir_path] *= self.decay_factor
            if self.heat_scores[dir_path] < 0.01:
                del self.heat_scores[dir_path]

        self.last_decay = time.time()

    def maybe_decay(self) -> None:
        """Check if decay should happen (auto-call every hour)."""
        if time.time() - self.last_decay > 3600:  # 1 hour
            self.decay_all()

    def get_all_heat_scores(self) -> Dict[str, float]:
        """Get all current heat scores."""
        return dict(self.heat_scores)


# ============================================================
# VETKA FILE WATCHER (Main Class)
# ============================================================

class VetkaFileWatcher:
    """
    Manages multiple directory watchers with Socket.IO integration.

    Features:
    - Add/remove directories dynamically
    - Persistent state (survives restarts)
    - Socket.IO event emission
    - Adaptive scan frequency
    """

    def __init__(self, socketio: Optional[Any] = None, state_file: str = 'data/watcher_state.json', qdrant_client: Optional[Any] = None, use_emit_queue: bool = False):
        """
        Initialize watcher.

        Args:
            socketio: Socket.IO server instance (optional)
            state_file: Path to persist watched directories
            qdrant_client: Qdrant client for real-time indexing (optional)
            use_emit_queue: Phase 80.15 - Use queue-based emit (fallback if direct fails)
        """
        self.observers: Dict[str, Observer] = {}
        self.watched_dirs: Set[str] = set()
        self.socketio = socketio
        self.qdrant_client = qdrant_client
        self.state_file = state_file
        self.adaptive_scanner = AdaptiveScanner()
        self._lock = threading.Lock()

        # Phase 80.15: Optional queue-based emit for thread safety
        self._use_emit_queue = use_emit_queue
        self._emit_queue: Optional[Any] = None
        self._emit_worker_thread: Optional[threading.Thread] = None

        if use_emit_queue:
            self._start_emit_worker()

        # Ensure data directory exists
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

    def add_directory(self, path: str, recursive: bool = True) -> bool:
        """
        Add directory to watch list.

        Args:
            path: Directory path to watch
            recursive: Watch subdirectories (default: True)

        Returns:
            True if added, False if already watching
        """
        # Normalize path
        path = os.path.abspath(path)

        if not os.path.isdir(path):
            print(f"[Watcher] Path is not a directory: {path}")
            return False

        with self._lock:
            if path in self.watched_dirs:
                print(f"[Watcher] Already watching: {path}")
                return False

            try:
                # FIX_95.9: MARKER_WATCHDOG_002 - Use PollingObserver on macOS if FSEvents unreliable
                # Read env var dynamically to ensure it's picked up even with uvicorn reload
                use_polling = os.environ.get('USE_POLLING_OBSERVER', '0') == '1'
                if use_polling:
                    observer = PollingObserver(timeout=1)  # Check every 1 second
                    print(f"[Watcher] Using PollingObserver (slower but reliable)")
                else:
                    observer = Observer()  # FSEvents on macOS, inotify on Linux

                handler = VetkaFileHandler(self._on_file_change)
                observer.schedule(handler, path, recursive=recursive)
                observer.start()

                self.observers[path] = observer
                self.watched_dirs.add(path)
                self._save_state()

                observer_type = "Polling" if use_polling else "FSEvents"
                print(f"[Watcher] Started watching ({observer_type}): {path}")
                return True

            except Exception as e:
                print(f"[Watcher] Error starting observer for {path}: {e}")
                return False

    def remove_directory(self, path: str) -> bool:
        """
        Stop watching directory.

        Args:
            path: Directory path to stop watching

        Returns:
            True if removed, False if not watching
        """
        path = os.path.abspath(path)

        with self._lock:
            if path not in self.observers:
                print(f"[Watcher] Not watching: {path}")
                return False

            try:
                self.observers[path].stop()
                self.observers[path].join(timeout=5)
                del self.observers[path]
                self.watched_dirs.discard(path)
                self._save_state()

                print(f"[Watcher] Stopped watching: {path}")
                return True

            except Exception as e:
                print(f"[Watcher] Error stopping observer for {path}: {e}")
                return False

    def _on_file_change(self, event: Dict) -> None:
        """
        Handle file change event from handler.

        Args:
            event: Coalesced event dictionary
        """
        event_type = event['type']
        path = event['path']

        print(f"[Watcher] {event_type}: {path}")

        # Update adaptive scanner heat
        dir_path = os.path.dirname(path)
        self.adaptive_scanner.update_heat(dir_path, event_type)
        self.adaptive_scanner.maybe_decay()

        # MARKER_90.11_START: Index FIRST, emit AFTER
        # Phase 90.11: Fix race condition - emit node_added AFTER Qdrant indexing
        # Problem: Frontend receives node_added -> requests tree/data -> file not yet in Qdrant
        # Solution: Index to Qdrant first, then emit to trigger tree refresh

        indexed_successfully = False

        # MARKER_90.3_START: Fix qdrant client retry
        # FIX_95.9: MARKER_WATCHDOG_001 - Removed blocking sleep(2) that froze watchdog thread
        # Original bug: time.sleep(2) in callback blocked ALL file event processing
        # New approach: Non-blocking background retry via threading.Timer
        qdrant_client = self._get_qdrant_client()

        if not qdrant_client:
            # FIX_95.9: Schedule non-blocking retry instead of blocking sleep
            print(f"[Watcher] ⏳ Qdrant unavailable, scheduling background retry for: {path}")
            self._schedule_qdrant_retry(event, retry_count=0)
            # Continue to emit socket event (don't block watchdog thread)
            indexed_successfully = False
        else:
            # Qdrant client available - index immediately
            # FIX_96.1: Explicit enable_triple_write=True for coherent writes to all stores
            try:
                result = handle_watcher_event(event, qdrant_client=qdrant_client, enable_triple_write=True)
                indexed_successfully = result
                print(f"[Watcher] ✅ Indexed via TripleWrite: {path}")
            except Exception as e:
                import traceback
                print(f"[Watcher] ❌ Error updating Qdrant: {e}")
                traceback.print_exc()
        # MARKER_90.3_END

        # MARKER_90.11: Emit to frontend AFTER indexing completes
        # This ensures tree/data will include the new file
        if self.socketio:
            try:
                if event_type == 'created':
                    self._emit('node_added', {'path': path, 'event': event, 'indexed': indexed_successfully})
                elif event_type == 'deleted':
                    self._emit('node_removed', {'path': path, 'event': event})
                elif event_type == 'modified':
                    self._emit('node_updated', {'path': path, 'event': event, 'indexed': indexed_successfully})
                elif event_type == 'moved':
                    self._emit('node_moved', {'path': path, 'event': event})
                elif event_type == 'bulk_update':
                    self._emit('tree_bulk_update', {
                        'path': path,
                        'count': event.get('count', 0),
                        'events': event.get('events', [])
                    })
            except Exception as e:
                print(f"[Watcher] Error emitting socket event: {e}")
        # MARKER_90.11_END

    def _schedule_qdrant_retry(self, event: Dict, retry_count: int = 0, max_retries: int = 3) -> None:
        """
        FIX_95.9: Non-blocking Qdrant retry via background timer.

        Instead of blocking the watchdog thread with time.sleep(2),
        schedule a background timer that will retry indexing without
        blocking file event processing.

        Args:
            event: The file change event to index
            retry_count: Current retry attempt (0-based)
            max_retries: Maximum retry attempts (default: 3)
        """
        if retry_count >= max_retries:
            path = event.get('path', 'unknown')
            print(f"[Watcher] ⚠️ SKIPPED after {max_retries} retries (Qdrant unavailable): {path}")
            return

        # Exponential backoff: 2s, 4s, 8s
        delay = 2 * (2 ** retry_count)
        path = event.get('path', 'unknown')

        def retry_index():
            qdrant_client = self._get_qdrant_client()
            if qdrant_client:
                try:
                    # FIX_96.1: Explicit enable_triple_write=True for coherent writes
                    result = handle_watcher_event(event, qdrant_client=qdrant_client, enable_triple_write=True)
                    if result:
                        print(f"[Watcher] ✅ Retry #{retry_count + 1} via TripleWrite succeeded: {path}")
                        # Emit update to frontend
                        if self.socketio:
                            event_type = event.get('type', 'modified')
                            if event_type == 'created':
                                self._emit('node_added', {'path': path, 'event': event, 'indexed': True})
                            elif event_type == 'modified':
                                self._emit('node_updated', {'path': path, 'event': event, 'indexed': True})
                    else:
                        print(f"[Watcher] ⚠️ Retry #{retry_count + 1} returned False: {path}")
                except Exception as e:
                    print(f"[Watcher] ❌ Retry #{retry_count + 1} error: {e}")
                    # Schedule another retry
                    self._schedule_qdrant_retry(event, retry_count + 1, max_retries)
            else:
                print(f"[Watcher] ⏳ Retry #{retry_count + 1} - still no Qdrant, scheduling next: {path}")
                self._schedule_qdrant_retry(event, retry_count + 1, max_retries)

        # Schedule non-blocking retry
        timer = threading.Timer(delay, retry_index)
        timer.daemon = True  # Don't block app shutdown
        timer.start()
        print(f"[Watcher] 🔄 Scheduled retry #{retry_count + 1} in {delay}s for: {path}")

    def _start_emit_worker(self) -> None:
        """
        Phase 80.15: Start background worker thread for queue-based emit.
        Phase 80.20: Fixed to properly handle AsyncServer.emit() coroutine.
        """
        import queue
        import asyncio
        self._emit_queue = queue.Queue()

        def worker():
            # Phase 80.20: Create dedicated event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            while True:
                try:
                    event_name, data = self._emit_queue.get()
                    if event_name is None:  # Shutdown signal
                        break
                    if self.socketio:
                        # Phase 80.20: Run coroutine in thread's event loop
                        loop.run_until_complete(self.socketio.emit(event_name, data))
                        print(f"[Watcher] Queue emitted {event_name}: {data.get('path', 'unknown')}")
                except Exception as e:
                    print(f"[Watcher] Queue emit error: {e}")
                finally:
                    self._emit_queue.task_done()

            loop.close()

        self._emit_worker_thread = threading.Thread(target=worker, daemon=True, name="WatcherEmitWorker")
        self._emit_worker_thread.start()
        print("[Watcher] Emit worker started (queue mode with async support)")

    def _emit(self, event_name: str, data: Dict) -> None:
        """
        Phase 80.15: Thread-safe socket emit.
        Phase 80.20: Fixed async emit from sync context.

        Emit socket event from watchdog thread to notify frontend.
        Supports two modes:
        1. Direct emit (default) - handles AsyncServer.emit() coroutine properly
        2. Queue-based emit (fallback) - if use_emit_queue=True in __init__

        CRITICAL FIX (Phase 80.20):
        self.socketio is AsyncServer, so emit() returns a coroutine.
        Calling without await just creates a coroutine object that never executes!
        """
        if not self.socketio:
            print(f"[Watcher] No socketio - cannot emit {event_name}")
            return

        try:
            if self._use_emit_queue and self._emit_queue is not None:
                # Phase 80.15: Queue-based emit (fallback mode)
                # Queue worker handles async properly (Phase 80.20)
                self._emit_queue.put((event_name, data))
            else:
                # Phase 80.20: Fix async emit from sync context
                # AsyncServer.emit() is a coroutine - must be awaited or scheduled
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    # Schedule coroutine in running loop (non-blocking)
                    asyncio.ensure_future(self.socketio.emit(event_name, data))
                else:
                    # No running loop - create temporary one
                    asyncio.run(self.socketio.emit(event_name, data))

                print(f"[Watcher] Emitted {event_name}: {data.get('path', 'unknown')}")

        except Exception as e:
            print(f"[Watcher] Emit error for {event_name}: {e}")
            import traceback
            traceback.print_exc()

    def _get_qdrant_client(self) -> Optional[Any]:
        """
        Phase 80.17: Lazy fetch Qdrant client.
        Phase 90.7: Multi-source fallback (same as watcher_routes.py MARKER_90.5.0)

        The watcher singleton may be created BEFORE Qdrant connects.
        This method fetches the client at event time, not at init time.

        Returns:
            Qdrant client if available, None otherwise
        """
        # First check instance variable (may have been set via get_watcher update)
        if self.qdrant_client is not None:
            return self.qdrant_client

        # MARKER_90.7_START: Multi-source Qdrant client (same as watcher_routes.py)
        # Try 1: get_qdrant_manager from components_init
        try:
            from src.initialization.components_init import get_qdrant_manager
            manager = get_qdrant_manager()
            if manager and hasattr(manager, 'client') and manager.client:
                self.qdrant_client = manager.client
                print("[Watcher] ✅ Qdrant client from qdrant_manager")
                return manager.client
        except Exception as e:
            pass  # Try next source

        # Try 2: memory_manager.qdrant_client (VetkaMemory) - THIS WORKS per Kimi K2
        try:
            from src.initialization.components_init import get_memory_manager
            memory_manager = get_memory_manager()
            if memory_manager and hasattr(memory_manager, 'qdrant_client') and memory_manager.qdrant_client:
                self.qdrant_client = memory_manager.qdrant_client
                print("[Watcher] ✅ Qdrant client from memory_manager")
                return memory_manager.qdrant_client
        except Exception as e:
            pass  # Try next source

        # Try 3: Direct from qdrant_client singleton
        try:
            from src.memory.qdrant_client import get_qdrant_client
            client = get_qdrant_client()
            if client:
                self.qdrant_client = client
                print("[Watcher] ✅ Qdrant client from singleton")
                return client
        except Exception as e:
            pass
        # MARKER_90.7_END

        return None

    def _save_state(self) -> None:
        """Persist watched directories to file."""
        try:
            state = {
                'watched_dirs': list(self.watched_dirs),
                'heat_scores': self.adaptive_scanner.get_all_heat_scores(),
                'saved_at': time.time()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[Watcher] Error saving state: {e}")

    def load_state(self) -> None:
        """Restore watched directories on startup."""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Restore watched directories
            for path in state.get('watched_dirs', []):
                if os.path.exists(path):
                    self.add_directory(path)
                else:
                    print(f"[Watcher] Skipping non-existent path: {path}")

            # Restore heat scores
            heat_scores = state.get('heat_scores', {})
            self.adaptive_scanner.heat_scores = heat_scores

            print(f"[Watcher] Restored state: {len(self.watched_dirs)} directories")

        except FileNotFoundError:
            print("[Watcher] No state file found, starting fresh")
        except Exception as e:
            print(f"[Watcher] Error loading state: {e}")

    def stop_all(self) -> None:
        """Stop all watchers and emit worker."""
        with self._lock:
            for path in list(self.observers.keys()):
                try:
                    self.observers[path].stop()
                    self.observers[path].join(timeout=5)
                except Exception as e:
                    print(f"[Watcher] Error stopping observer for {path}: {e}")

            self.observers.clear()
            self.watched_dirs.clear()
            self._save_state()

        # Phase 80.15: Stop emit worker if running
        if self._emit_queue is not None:
            try:
                self._emit_queue.put((None, None))  # Shutdown signal
                if self._emit_worker_thread and self._emit_worker_thread.is_alive():
                    self._emit_worker_thread.join(timeout=2)
                print("[Watcher] Emit worker stopped")
            except Exception as e:
                print(f"[Watcher] Error stopping emit worker: {e}")

        print("[Watcher] All watchers stopped")

    def add_browser_directory(self, root_name: str, files_count: int) -> None:
        """
        Track a browser-scanned directory (virtual, no filesystem watcher).

        Browser FileSystem API doesn't provide real paths, so we track
        by root name only for display purposes.

        Args:
            root_name: Name of the root folder from browser
            files_count: Number of files scanned
        """
        # Track as virtual watched directory (prefixed to distinguish)
        virtual_path = f"[browser] {root_name}"

        with self._lock:
            self.watched_dirs.add(virtual_path)
            # Give it some initial heat
            self.adaptive_scanner.heat_scores[virtual_path] = 0.5

        print(f"[Watcher] Browser directory tracked: {root_name} ({files_count} files)")

    def get_status(self) -> Dict:
        """
        Get current watcher status.

        Returns:
            Dictionary with watching dirs, count, and heat scores
        """
        return {
            'watching': list(self.watched_dirs),
            'count': len(self.watched_dirs),
            'heat_scores': self.adaptive_scanner.get_all_heat_scores(),
            'observers_active': len([o for o in self.observers.values() if o.is_alive()])
        }


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_watcher_instance: Optional[VetkaFileWatcher] = None
_watcher_lock = threading.Lock()


def get_watcher(socketio: Optional[Any] = None, qdrant_client: Optional[Any] = None, use_emit_queue: bool = False) -> VetkaFileWatcher:
    """
    Get singleton watcher instance.

    Args:
        socketio: Socket.IO server (only used on first call)
        qdrant_client: Qdrant client for real-time indexing (only used on first call)
        use_emit_queue: Phase 80.15 - Use queue-based emit (fallback, only on first call)

    Returns:
        VetkaFileWatcher singleton
    """
    global _watcher_instance

    with _watcher_lock:
        if _watcher_instance is None:
            _watcher_instance = VetkaFileWatcher(socketio=socketio, qdrant_client=qdrant_client, use_emit_queue=use_emit_queue)
            _watcher_instance.load_state()
        else:
            if socketio and _watcher_instance.socketio is None:
                _watcher_instance.socketio = socketio
            if qdrant_client and _watcher_instance.qdrant_client is None:
                _watcher_instance.qdrant_client = qdrant_client

        return _watcher_instance


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    import sys

    def test_callback(event):
        print(f"[TEST] Received event: {event}")

    # Create watcher
    watcher = VetkaFileWatcher()

    # Watch current directory
    test_path = sys.argv[1] if len(sys.argv) > 1 else "."
    watcher.add_directory(test_path)

    print(f"\nWatching: {test_path}")
    print("Press Ctrl+C to stop...\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop_all()
        print("\nStopped.")
