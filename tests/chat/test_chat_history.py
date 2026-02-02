"""
Phase 74: Chat History Tests

Tests for:
- Folder context support
- Chat rename functionality
- Group chat with items
- Topic-based chats
- Backward compatibility with existing chats
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime

# Import the module under test
from src.chat.chat_history_manager import ChatHistoryManager


@pytest.fixture
def temp_history_file():
    """Create a temporary history file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Write empty but valid history structure
        initial_data = {"chats": {}, "groups": {"default": {"name": "Default", "roles": {}}}}
        json.dump(initial_data, f)
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def manager(temp_history_file):
    """Create a ChatHistoryManager with temp file."""
    return ChatHistoryManager(history_file=temp_history_file)


@pytest.fixture
def temp_folder():
    """Create a temporary folder for folder context tests."""
    temp_dir = tempfile.mkdtemp()
    # Create some test files
    (Path(temp_dir) / "file1.py").write_text("# Python file 1")
    (Path(temp_dir) / "file2.py").write_text("# Python file 2")
    (Path(temp_dir) / "README.md").write_text("# Readme")
    yield temp_dir
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestFolderContextSupport:
    """Test folder context creates chat with context_type='folder'."""

    def test_folder_context_creates_chat(self, manager, temp_folder):
        """Folder path creates chat with context_type='folder'."""
        chat_id = manager.get_or_create_chat(temp_folder)

        chat = manager.get_chat(chat_id)
        assert chat is not None
        assert chat["context_type"] == "folder"
        assert chat["file_path"] == str(Path(temp_folder).resolve())

    def test_folder_name_extracted(self, manager, temp_folder):
        """Folder name is correctly extracted."""
        chat_id = manager.get_or_create_chat(temp_folder)

        chat = manager.get_chat(chat_id)
        expected_name = Path(temp_folder).name
        assert chat["file_name"] == expected_name

    def test_file_context_default(self, manager):
        """Regular file creates chat with context_type='file'."""
        # Use a file that doesn't exist (won't be detected as folder)
        chat_id = manager.get_or_create_chat("/some/path/file.py")

        chat = manager.get_chat(chat_id)
        assert chat is not None
        # Since path doesn't exist, context_type should default to "file"
        assert chat.get("context_type") == "file"


class TestChatRename:
    """Test chat rename functionality."""

    def test_rename_chat_success(self, manager):
        """Rename chat updates display_name."""
        chat_id = manager.get_or_create_chat("/test/file.py")

        result = manager.rename_chat(chat_id, "My Custom Name")
        assert result is True

        chat = manager.get_chat(chat_id)
        assert chat["display_name"] == "My Custom Name"

    def test_rename_chat_updates_timestamp(self, manager):
        """Rename chat updates updated_at timestamp."""
        chat_id = manager.get_or_create_chat("/test/file.py")
        chat_before = manager.get_chat(chat_id)
        original_updated = chat_before["updated_at"]

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        manager.rename_chat(chat_id, "New Name")
        chat_after = manager.get_chat(chat_id)

        assert chat_after["updated_at"] > original_updated

    def test_rename_nonexistent_chat(self, manager):
        """Renaming non-existent chat returns False."""
        result = manager.rename_chat("nonexistent-id", "Name")
        assert result is False

    def test_rename_preserves_other_fields(self, manager):
        """Rename doesn't affect other chat fields."""
        chat_id = manager.get_or_create_chat("/test/file.py")

        # Add a message first
        manager.add_message(chat_id, {"role": "user", "content": "Hello"})

        manager.rename_chat(chat_id, "Renamed Chat")

        chat = manager.get_chat(chat_id)
        assert len(chat["messages"]) == 1
        assert chat["file_path"].endswith("file.py")


class TestGroupChat:
    """Test group chat with items list."""

    def test_group_chat_creation(self, manager):
        """Group chat stores items list."""
        items = ["/path/file1.py", "/path/file2.py", "/path/file3.py"]
        chat_id = manager.get_or_create_chat(
            "/path/file1.py",
            context_type="group",
            items=items
        )

        chat = manager.get_chat(chat_id)
        assert chat["context_type"] == "group"
        assert chat["items"] == items

    def test_update_chat_items(self, manager):
        """update_chat_items updates the items list."""
        chat_id = manager.get_or_create_chat("/path/file1.py")
        original_items = manager.get_chat(chat_id).get("items", [])
        assert original_items == []

        new_items = ["/path/a.py", "/path/b.py"]
        manager.update_chat_items(chat_id, new_items)

        chat = manager.get_chat(chat_id)
        assert chat["items"] == new_items
        assert chat["context_type"] == "group"

    def test_update_items_changes_context_type(self, manager):
        """Adding multiple items changes context_type to 'group'."""
        chat_id = manager.get_or_create_chat("/path/file.py")
        assert manager.get_chat(chat_id).get("context_type") == "file"

        manager.update_chat_items(chat_id, ["/path/a.py", "/path/b.py"])
        assert manager.get_chat(chat_id)["context_type"] == "group"

    def test_update_items_single_keeps_original_type(self, manager):
        """Single item doesn't force context_type to 'group'."""
        chat_id = manager.get_or_create_chat("/path/file.py", context_type="file")

        manager.update_chat_items(chat_id, ["/path/single.py"])
        # Should keep original type since only 1 item
        assert manager.get_chat(chat_id)["context_type"] == "file"


class TestTopicChat:
    """Test topic-based chats without files."""

    def test_topic_chat_creation(self, manager):
        """Topic chat stores topic field."""
        chat_id = manager.get_or_create_chat(
            "unknown",
            context_type="topic",
            topic="General Discussion"
        )

        chat = manager.get_chat(chat_id)
        assert chat["context_type"] == "topic"
        assert chat["topic"] == "General Discussion"

    def test_topic_chat_with_display_name(self, manager):
        """Topic chat can have custom display_name."""
        chat_id = manager.get_or_create_chat(
            "unknown",
            context_type="topic",
            topic="Architecture Planning",
            display_name="Phase 74 Planning"
        )

        chat = manager.get_chat(chat_id)
        assert chat["display_name"] == "Phase 74 Planning"
        assert chat["topic"] == "Architecture Planning"


class TestNullContextGroupChat:
    """Test group chats with null context (Phase 74.7)."""

    def test_group_null_chat_separate_from_regular(self, manager):
        """Group null-chat should not reuse regular null-chat."""
        # Create regular null-context chat
        regular_id = manager.get_or_create_chat("unknown", context_type="file")
        manager.add_message(regular_id, {"role": "user", "content": "Regular chat"})

        # Create group null-context chat
        group_id = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            items=["/path/a.py", "/path/b.py"]
        )
        manager.add_message(group_id, {"role": "user", "content": "Group chat"})

        # Should be different chats
        assert regular_id != group_id

        # Verify types
        assert manager.get_chat(regular_id)["context_type"] == "file"
        assert manager.get_chat(group_id)["context_type"] == "group"

    def test_group_null_chat_reuses_existing_group(self, manager):
        """Second group null-chat should reuse first unnamed one."""
        # Create first group null-context chat
        group_id_1 = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            items=["/path/a.py", "/path/b.py"]
        )

        # Create second group null-context chat (should reuse)
        group_id_2 = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            items=["/path/c.py", "/path/d.py"]
        )

        # Should be same chat
        assert group_id_1 == group_id_2

    def test_renamed_group_chat_not_reused(self, manager):
        """Renamed group null-chat should not be reused."""
        # Create and rename a group chat
        group_id_1 = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            items=["/path/a.py", "/path/b.py"]
        )
        manager.rename_chat(group_id_1, "My Saved Group Chat")

        # Create new group chat - should NOT reuse renamed one
        group_id_2 = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            items=["/path/c.py", "/path/d.py"]
        )

        # Should be different chats
        assert group_id_1 != group_id_2

        # Verify renamed one is preserved
        chat1 = manager.get_chat(group_id_1)
        assert chat1["display_name"] == "My Saved Group Chat"

    def test_named_group_reuses_by_display_name(self, manager):
        """Named group chat should be found by display_name (Phase 74.9)."""
        # Create first group with name
        group_id_1 = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            display_name="Test Group Alpha"
        )
        manager.add_message(group_id_1, {"role": "user", "content": "Message 1"})

        # Create second call with same name - should reuse
        group_id_2 = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            display_name="Test Group Alpha"
        )
        manager.add_message(group_id_2, {"role": "assistant", "content": "Response 1"})

        # Should be SAME chat
        assert group_id_1 == group_id_2

        # Verify both messages in same chat
        chat = manager.get_chat(group_id_1)
        assert len(chat["messages"]) == 2
        assert chat["display_name"] == "Test Group Alpha"

    def test_trailing_space_in_display_name(self, manager):
        """Phase 74.10: Trailing spaces should not create duplicate chats."""
        # Create chat with clean name
        group_id_1 = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            display_name="Test Group Beta"
        )

        # Call with trailing space - should find same chat
        group_id_2 = manager.get_or_create_chat(
            "unknown",
            context_type="group",
            display_name="Test Group Beta "  # Trailing space
        )

        # Should be SAME chat
        assert group_id_1 == group_id_2

        # Stored name should be stripped
        chat = manager.get_chat(group_id_1)
        assert chat["display_name"] == "Test Group Beta"  # No trailing space


class TestBackwardCompatibility:
    """Test that old chats without new fields still work."""

    def test_old_chat_without_context_type(self, temp_history_file):
        """Old chats without context_type field work correctly."""
        # Create a "legacy" chat directly in the file
        old_chat = {
            "chats": {
                "legacy-id": {
                    "id": "legacy-id",
                    "file_path": "/old/file.py",
                    "file_name": "file.py",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00",
                    "messages": [
                        {"role": "user", "content": "Hello", "id": "msg-1"}
                    ]
                }
            },
            "groups": {}
        }

        with open(temp_history_file, 'w') as f:
            json.dump(old_chat, f)

        # Load with new manager
        manager = ChatHistoryManager(history_file=temp_history_file)

        # Should be able to get the chat
        chat = manager.get_chat("legacy-id")
        assert chat is not None
        assert chat["file_name"] == "file.py"
        assert len(chat["messages"]) == 1

        # context_type might be None but that's ok
        # The code should handle missing fields gracefully

    def test_old_chat_add_message_works(self, temp_history_file):
        """Can add messages to old chats without new fields."""
        old_chat = {
            "chats": {
                "legacy-id": {
                    "id": "legacy-id",
                    "file_path": "/old/file.py",
                    "file_name": "file.py",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00",
                    "messages": []
                }
            },
            "groups": {}
        }

        with open(temp_history_file, 'w') as f:
            json.dump(old_chat, f)

        manager = ChatHistoryManager(history_file=temp_history_file)

        # Should be able to add a message
        result = manager.add_message("legacy-id", {"role": "user", "content": "Test"})
        assert result is True

        chat = manager.get_chat("legacy-id")
        assert len(chat["messages"]) == 1

    def test_get_all_chats_includes_old_format(self, temp_history_file):
        """get_all_chats works with mixed old/new format chats."""
        mixed_chats = {
            "chats": {
                "old-chat": {
                    "id": "old-chat",
                    "file_path": "/old/file.py",
                    "file_name": "file.py",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00",
                    "messages": []
                },
                "new-chat": {
                    "id": "new-chat",
                    "file_path": "/new/file.py",
                    "file_name": "file.py",
                    "display_name": "New Style",
                    "context_type": "file",
                    "items": [],
                    "topic": None,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                    "messages": []
                }
            },
            "groups": {}
        }

        with open(temp_history_file, 'w') as f:
            json.dump(mixed_chats, f)

        manager = ChatHistoryManager(history_file=temp_history_file)
        # Phase 107.3: get_all_chats now supports pagination, but defaults load all (limit=50, offset=0)
        all_chats = manager.get_all_chats()

        assert len(all_chats) == 2

        # Both should be accessible
        chat_ids = [c["id"] for c in all_chats]
        assert "old-chat" in chat_ids
        assert "new-chat" in chat_ids


class TestHandlerUtilsFolderSupport:
    """Test handler_utils.py folder context support."""

    def test_sync_get_rich_context_folder(self, temp_folder):
        """sync_get_rich_context works with folders."""
        from src.api.handlers.handler_utils import sync_get_rich_context

        result = sync_get_rich_context(temp_folder)

        assert result["error"] is None
        assert result["file_metadata"]["is_directory"] is True
        assert result["file_metadata"]["file_count"] == 3  # file1.py, file2.py, README.md
        assert "file1.py" in result["file_content"]
        assert "file2.py" in result["file_content"]

    def test_sync_get_rich_context_file(self, temp_folder):
        """sync_get_rich_context still works with regular files."""
        from src.api.handlers.handler_utils import sync_get_rich_context

        file_path = os.path.join(temp_folder, "file1.py")
        result = sync_get_rich_context(file_path)

        assert result["error"] is None
        assert result["file_metadata"]["is_directory"] is False
        assert "Python file 1" in result["file_content"]

    def test_sync_get_rich_context_nonexistent(self):
        """sync_get_rich_context handles non-existent paths."""
        from src.api.handlers.handler_utils import sync_get_rich_context

        result = sync_get_rich_context("/nonexistent/path/file.py")

        assert result["error"] is not None
        assert "not found" in result["error"].lower()
