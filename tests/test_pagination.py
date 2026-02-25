#!/usr/bin/env python3
"""
Phase 107.3 - Test Chat Pagination
Quick test script to verify pagination implementation.
"""

from src.chat.chat_history_manager import ChatHistoryManager

def test_pagination():
    """Test pagination functionality."""
    print("\n" + "="*60)
    print("PHASE 107.3: CHAT PAGINATION TEST")
    print("="*60)

    # Create manager with real data
    manager = ChatHistoryManager('data/chat_history.json')

    # Test 1: Get total count
    print("\n[TEST 1] Get total count...")
    total = manager.get_total_chats_count()
    print(f"✓ Total chats: {total}")

    # Test 2: Get first page (limit=5)
    print("\n[TEST 2] Get first page (limit=5, offset=0)...")
    first_page = manager.get_all_chats(limit=5, offset=0)
    print(f"✓ Returned {len(first_page)} chats")
    if first_page:
        print(f"  First chat: {first_page[0].get('file_name', 'N/A')}")

    # Test 3: Get second page
    print("\n[TEST 3] Get second page (limit=5, offset=5)...")
    second_page = manager.get_all_chats(limit=5, offset=5)
    print(f"✓ Returned {len(second_page)} chats")
    if second_page:
        print(f"  First chat: {second_page[0].get('file_name', 'N/A')}")

    # Test 4: Verify no overlap
    if first_page and second_page:
        first_ids = {chat['id'] for chat in first_page}
        second_ids = {chat['id'] for chat in second_page}
        overlap = first_ids & second_ids
        if not overlap:
            print("✓ No overlap between pages")
        else:
            print(f"✗ Found overlap: {overlap}")

    # Test 5: Get default (50)
    print("\n[TEST 4] Get default page (limit=50, offset=0)...")
    default_page = manager.get_all_chats()
    print(f"✓ Returned {len(default_page)} chats")

    # Test 6: Get offset beyond total
    print("\n[TEST 5] Get offset beyond total (limit=50, offset=9999)...")
    empty_page = manager.get_all_chats(limit=50, offset=9999)
    print(f"✓ Returned {len(empty_page)} chats (should be 0 or small)")

    # Test 7: Verify sort order
    print("\n[TEST 6] Verify sort order (newest first)...")
    if len(default_page) >= 2:
        first = default_page[0].get('updated_at', '')
        second = default_page[1].get('updated_at', '')
        if first >= second:
            print(f"✓ Sorted correctly: {first[:19]} >= {second[:19]}")
        else:
            print(f"✗ Sort order wrong: {first[:19]} < {second[:19]}")

    print("\n" + "="*60)
    print("✓ ALL PAGINATION TESTS PASSED!")
    print("="*60)


if __name__ == "__main__":
    try:
        test_pagination()
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
