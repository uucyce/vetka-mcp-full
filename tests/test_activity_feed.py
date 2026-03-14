#!/usr/bin/env python3
"""
Test Activity Feed API - Phase 108.4 Step 5

Quick test script to verify the activity feed endpoint works correctly.

Usage:
    python test_activity_feed.py
"""

import requests
import json
from datetime import datetime


def test_activity_feed():
    """Test the activity feed endpoint."""
    base_url = "http://localhost:5001"

    print("=" * 60)
    print("Testing Activity Feed API - Phase 108.4 Step 5")
    print("=" * 60)

    # Test 1: Get activity feed (all types)
    print("\n[Test 1] GET /api/activity/feed (all types)")
    try:
        response = requests.get(f"{base_url}/api/activity/feed?limit=10")
        response.raise_for_status()
        data = response.json()

        print(f"✅ Status: {response.status_code}")
        print(f"✅ Total activities: {data.get('total', 0)}")
        print(f"✅ Activities returned: {len(data.get('activities', []))}")
        print(f"✅ Has more: {data.get('has_more', False)}")

        # Show first 3 activities
        activities = data.get('activities', [])
        for i, activity in enumerate(activities[:3], 1):
            print(f"\n  Activity {i}:")
            print(f"    Type: {activity.get('type')}")
            print(f"    Title: {activity.get('title')}")
            print(f"    Description: {activity.get('description')[:50]}...")
            print(f"    Timestamp: {activity.get('timestamp')}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Get activity feed (filtered by type)
    print("\n" + "-" * 60)
    print("\n[Test 2] GET /api/activity/feed (filtered: chat,mcp)")
    try:
        response = requests.get(f"{base_url}/api/activity/feed?limit=5&types=chat,mcp")
        response.raise_for_status()
        data = response.json()

        print(f"✅ Status: {response.status_code}")
        print(f"✅ Total activities: {data.get('total', 0)}")
        print(f"✅ Activities returned: {len(data.get('activities', []))}")

        # Verify types
        activities = data.get('activities', [])
        types_found = set(activity.get('type') for activity in activities)
        print(f"✅ Types found: {types_found}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Get activity stats
    print("\n" + "-" * 60)
    print("\n[Test 3] GET /api/activity/stats")
    try:
        response = requests.get(f"{base_url}/api/activity/stats")
        response.raise_for_status()
        data = response.json()

        print(f"✅ Status: {response.status_code}")
        print(f"✅ Total activities: {data.get('total', 0)}")
        print(f"✅ By type:")
        for activity_type, count in data.get('by_type', {}).items():
            print(f"    {activity_type}: {count}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: Pagination
    print("\n" + "-" * 60)
    print("\n[Test 4] GET /api/activity/feed (pagination: offset=5, limit=5)")
    try:
        response = requests.get(f"{base_url}/api/activity/feed?limit=5&offset=5")
        response.raise_for_status()
        data = response.json()

        print(f"✅ Status: {response.status_code}")
        print(f"✅ Total activities: {data.get('total', 0)}")
        print(f"✅ Activities returned: {len(data.get('activities', []))}")
        print(f"✅ Has more: {data.get('has_more', False)}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Activity Feed API Tests Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_activity_feed()
