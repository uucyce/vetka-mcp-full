"""
Tests for Phase 146.5 SpamDetector — auto-mute noisy directories.

Tests:
1. Normal events pass through
2. Spam threshold triggers mute
3. Muted directory blocks events
4. Cooldown expires and unmutes
5. Suggest skip pattern works
6. Extract dir key groups correctly
7. Alert callback fires on spam
8. Multiple directories tracked independently
9. get_muted_dirs returns active mutes only
10. SKIP_PATTERNS contains playground entries
11. Runtime skip pattern addition
"""

import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.scanners.file_watcher import (
    SpamDetector, SKIP_PATTERNS, get_spam_detector,
    SPAM_THRESHOLD, SPAM_WINDOW_SECONDS
)


class TestSpamDetectorBasic(unittest.TestCase):
    """Basic SpamDetector functionality."""

    def setUp(self):
        self.detector = SpamDetector(threshold=10, window=5.0, cooldown=2.0)

    def test_normal_events_pass(self):
        """Events below threshold should pass through."""
        for i in range(8):
            result = self.detector.record_event(f"/project/src/file_{i}.py")
            self.assertTrue(result)
        # 8 events < 10 threshold — next event should also pass
        self.assertTrue(self.detector.record_event("/project/src/another.py"))

    def test_spam_triggers_mute(self):
        """Exceeding threshold mutes the directory."""
        path_prefix = "/project/.playgrounds/pg_test/"
        # Send exactly threshold events from same dir
        for i in range(10):
            self.detector.record_event(f"{path_prefix}file_{i}.py")

        # Next event should be blocked (directory muted)
        result = self.detector.record_event(f"{path_prefix}one_more.py")
        self.assertFalse(result)

    def test_muted_directory_blocks(self):
        """After muting, all events from that dir are blocked."""
        path_prefix = "/project/.playgrounds/pg_xxx/"
        # Trigger spam
        for i in range(10):
            self.detector.record_event(f"{path_prefix}file_{i}.py")

        # 10 more events — all should be blocked
        blocked_count = 0
        for i in range(10):
            if not self.detector.record_event(f"{path_prefix}blocked_{i}.py"):
                blocked_count += 1
        self.assertEqual(blocked_count, 10)

    def test_cooldown_unmutes(self):
        """After cooldown expires, directory is unmuted."""
        # Use very short cooldown
        detector = SpamDetector(threshold=5, window=5.0, cooldown=0.1)
        path = "/project/.claude/worktrees/test-branch/src/main.py"

        # Trigger spam
        for i in range(5):
            detector.record_event(f"/project/.claude/worktrees/test-branch/file_{i}.py")

        # Should be muted
        self.assertFalse(detector.record_event(path))

        # Wait for cooldown
        time.sleep(0.15)

        # Should be unmuted now
        self.assertTrue(detector.record_event(path))

    def test_is_muted(self):
        """is_muted() correctly reports directory status."""
        path_prefix = "/project/.playgrounds/pg_mute_test/"
        # Before spam — not muted
        self.assertFalse(self.detector.is_muted(f"{path_prefix}file.py"))

        # Trigger spam
        for i in range(10):
            self.detector.record_event(f"{path_prefix}file_{i}.py")

        # After spam — muted
        self.assertTrue(self.detector.is_muted(f"{path_prefix}any_file.py"))

    def test_get_muted_dirs(self):
        """get_muted_dirs returns only actively muted directories."""
        path1 = "/project/.playgrounds/pg_a/"
        path2 = "/project/.playgrounds/pg_b/"

        # Mute dir A
        for i in range(10):
            self.detector.record_event(f"{path1}file_{i}.py")

        muted = self.detector.get_muted_dirs()
        self.assertGreaterEqual(len(muted), 1)

        # At least one muted dir should contain '.playgrounds'
        has_playground = any('.playgrounds' in d for d in muted)
        self.assertTrue(has_playground)


class TestSpamDetectorDirKey(unittest.TestCase):
    """Tests for directory key extraction logic."""

    def setUp(self):
        self.detector = SpamDetector()

    def test_playground_dir_key(self):
        """Playground paths group by .playgrounds/pg_xxx."""
        key = self.detector._extract_dir_key(
            "/project/.playgrounds/pg_abc123/src/components/Button.tsx"
        )
        self.assertIn(".playgrounds", key)

    def test_claude_worktree_dir_key(self):
        """Claude worktree paths group by .claude/worktrees."""
        key = self.detector._extract_dir_key(
            "/project/.claude/worktrees/vibrant-wright/src/main.py"
        )
        self.assertIn(".claude", key)

    def test_regular_path_returns_none(self):
        """Regular (non-dot) paths return None — never spam-checked."""
        key = self.detector._extract_dir_key("/project/src/utils/helper.py")
        self.assertIsNone(key)

    def test_regular_path_client(self):
        """Client directory paths return None."""
        key = self.detector._extract_dir_key("/project/client/src/App.tsx")
        self.assertIsNone(key)

    def test_independent_directory_tracking(self):
        """Different directories tracked independently."""
        detector = SpamDetector(threshold=5, window=5.0, cooldown=2.0)

        # Spam dir A
        for i in range(5):
            detector.record_event(f"/project/.playgrounds/pg_a/file_{i}.py")

        # Dir A muted, dir B still free
        self.assertFalse(detector.record_event("/project/.playgrounds/pg_a/extra.py"))
        self.assertTrue(detector.record_event("/project/src/normal_file.py"))


class TestSpamDetectorSuggestPattern(unittest.TestCase):
    """Tests for skip pattern suggestion."""

    def setUp(self):
        self.detector = SpamDetector()

    def test_suggest_playground_pattern(self):
        """Suggests .playgrounds for playground paths."""
        pattern = self.detector._suggest_skip_pattern("/project/.playgrounds/pg_xxx")
        self.assertEqual(pattern, ".playgrounds")

    def test_suggest_claude_pattern(self):
        """Suggests .claude for claude worktree paths."""
        pattern = self.detector._suggest_skip_pattern("/project/.claude/worktrees")
        self.assertEqual(pattern, ".claude")

    def test_suggest_custom_dotdir(self):
        """Suggests dotdir for any hidden directory."""
        pattern = self.detector._suggest_skip_pattern("/project/.cache/build_temp")
        self.assertEqual(pattern, ".cache")


class TestSpamDetectorAlertCallback(unittest.TestCase):
    """Tests for alert callback on spam detection."""

    def test_alert_callback_fires(self):
        """Alert callback is called when spam detected."""
        detector = SpamDetector(threshold=5, window=5.0, cooldown=2.0)
        callback = MagicMock()
        detector.set_alert_callback(callback)

        # Trigger spam
        for i in range(5):
            detector.record_event(f"/project/.playgrounds/pg_alert/file_{i}.py")

        # Callback should have been called once
        callback.assert_called_once()
        args = callback.call_args[0]
        self.assertIn('.playgrounds', args[0])  # dir_path
        self.assertEqual(args[1], 5)  # event_count
        self.assertEqual(args[2], '.playgrounds')  # suggested_skip

    def test_no_callback_when_not_set(self):
        """No error when callback is not set."""
        detector = SpamDetector(threshold=5, window=5.0, cooldown=2.0)
        # Should not crash without callback
        for i in range(5):
            detector.record_event(f"/project/.playgrounds/pg_no_cb/file_{i}.py")


class TestBulkScanProtection(unittest.TestCase):
    """
    CRITICAL: Regular directories must NEVER be muted, even under heavy load.
    This protects legitimate bulk scans (adding a folder with 100+ files).
    """

    def test_bulk_scan_100_files_not_muted(self):
        """Adding a folder with 100 files should NOT trigger spam detection."""
        detector = SpamDetector(threshold=10, window=5.0, cooldown=2.0)

        # Simulate adding a large project folder — 100 files all at once
        all_passed = True
        for i in range(100):
            result = detector.record_event(f"/project/src/components/Component_{i}.tsx")
            if not result:
                all_passed = False
                break

        self.assertTrue(all_passed, "Regular directory was muted during bulk scan!")

    def test_bulk_scan_nested_dirs_not_muted(self):
        """Files across nested regular dirs should not be muted."""
        detector = SpamDetector(threshold=10, window=5.0, cooldown=2.0)

        dirs = ['src/utils', 'src/hooks', 'src/api', 'client/components', 'tests']
        all_passed = True
        for d in dirs:
            for i in range(30):
                result = detector.record_event(f"/project/{d}/file_{i}.py")
                if not result:
                    all_passed = False
                    break
        # 150 events total across regular dirs — none should be muted
        self.assertTrue(all_passed, "Regular nested directories were muted!")

    def test_dotdir_still_muted(self):
        """Hidden directories ARE still muted (the original behavior)."""
        detector = SpamDetector(threshold=10, window=5.0, cooldown=2.0)

        # Spam a hidden dir — should trigger mute
        for i in range(10):
            detector.record_event(f"/project/.cache/build/file_{i}.py")

        result = detector.record_event("/project/.cache/build/extra.py")
        self.assertFalse(result, "Hidden directory should be muted!")

    def test_regular_dir_never_appears_in_muted(self):
        """Regular directories should never appear in get_muted_dirs()."""
        detector = SpamDetector(threshold=5, window=5.0, cooldown=2.0)

        # Send 100 events from regular dir
        for i in range(100):
            detector.record_event(f"/project/src/file_{i}.py")

        muted = detector.get_muted_dirs()
        # No regular dirs in muted list
        for path in muted:
            has_dotdir = any(part.startswith('.') and part not in ('.', '..')
                           for part in Path(path).parts)
            self.assertTrue(has_dotdir,
                           f"Regular directory '{path}' found in muted list!")

    def test_is_muted_false_for_regular_dir(self):
        """is_muted() always returns False for regular directories."""
        detector = SpamDetector(threshold=5, window=5.0, cooldown=2.0)

        # Even after many events, regular dir is not muted
        for i in range(50):
            detector.record_event(f"/project/src/file_{i}.py")

        self.assertFalse(detector.is_muted("/project/src/file_0.py"))


class TestSkipPatternsPlayground(unittest.TestCase):
    """Verify SKIP_PATTERNS includes playground entries."""

    def test_playgrounds_in_skip(self):
        """SKIP_PATTERNS contains .playgrounds."""
        self.assertIn('.playgrounds', SKIP_PATTERNS)

    def test_claude_worktrees_in_skip(self):
        """SKIP_PATTERNS contains .claude/worktrees."""
        self.assertIn('.claude/worktrees', SKIP_PATTERNS)

    def test_playground_settings_in_skip(self):
        """SKIP_PATTERNS contains playground_settings.json."""
        has_settings = any('playground_settings' in p for p in SKIP_PATTERNS)
        self.assertTrue(has_settings)

    def test_global_detector_exists(self):
        """get_spam_detector() returns a SpamDetector instance."""
        detector = get_spam_detector()
        self.assertIsInstance(detector, SpamDetector)


if __name__ == '__main__':
    unittest.main()
