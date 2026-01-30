#!/usr/bin/env python3
"""
Real watchdog test - creates observer and watches for file changes.
Run this, then touch a file in docs/90_ph to see if event is detected.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

class TestHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        print(f"[DETECTED] type={event.event_type}, path={event.src_path}, is_dir={event.is_directory}")

# Watch docs/90_ph
watch_path = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/90_ph"

print(f"=== Real Watchdog Test ===")
print(f"Watching: {watch_path}")
print(f"Observer: {Observer}")
print()

observer = Observer()
handler = TestHandler()
observer.schedule(handler, watch_path, recursive=True)
observer.start()

print("Observer started. Waiting 10 seconds...")
print("Try: touch docs/90_ph/test_real.md")
print()

try:
    for i in range(10):
        time.sleep(1)
        print(f"  {10-i} seconds remaining...")
except KeyboardInterrupt:
    pass

observer.stop()
observer.join()
print("\nObserver stopped.")
