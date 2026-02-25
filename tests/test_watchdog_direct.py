#!/usr/bin/env python3
"""
Quick test to verify watchdog is working.
Run this in a separate terminal.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scanners.file_watcher import VetkaFileHandler, SUPPORTED_EXTENSIONS, SKIP_PATTERNS
from watchdog.events import FileCreatedEvent, FileModifiedEvent

def test_callback(event):
    print(f"[CALLBACK] Got event: {event}")

# Create handler
handler = VetkaFileHandler(on_change_callback=test_callback, debounce_ms=100)

# Simulate events
test_path = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/90_ph/test.md"

print("=== Testing VetkaFileHandler ===")
print(f"SUPPORTED_EXTENSIONS: {SUPPORTED_EXTENSIONS}")
print(f".md in SUPPORTED_EXTENSIONS: {'.md' in SUPPORTED_EXTENSIONS}")
print()

# Test 1: Create event
print("Test 1: Simulating FileCreatedEvent for .md file...")
event = FileCreatedEvent(test_path)
handler.on_any_event(event)

# Wait for debounce
import time
time.sleep(0.5)

print("\nDone. If callback was called, you should see [CALLBACK] above.")
