"""
VETKA Phase 77.3 - Hostess Memory Curator Agent
User dialog for memory sync decisions

@file memory_curator_agent.py
@status ACTIVE
@phase Phase 77.3 - Memory Sync Protocol
@calledBy MemorySyncEngine
@lastAudit 2026-01-20

MARKER-77-03: Add memory_sync_dialog tool to hostess
MARKER-77-08: Add 30s timeout with fallback to default decisions

The Hostess asks the user about sync decisions:
- What to keep, what to delete, what to compress
- User decides, VETKA executes
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field

from src.memory.diff import DiffResult

logger = logging.getLogger(__name__)


@dataclass
class SyncDecision:
    """
    User's decision for a single item.
    """
    path: str
    action: Literal["keep", "trash", "delete", "compress", "full"]
    reason: Optional[str] = None


@dataclass
class SyncDecisions:
    """
    Collection of user decisions for sync operation.
    """
    decisions: Dict[str, SyncDecision] = field(default_factory=dict)
    compression_policy: Literal["yes", "no", "partial"] = "partial"
    compression_threshold_days: int = 90
    approved: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def get_decision(self, path: str) -> Optional[SyncDecision]:
        """Get decision for a specific path."""
        return self.decisions.get(path)

    def add_decision(self, path: str, action: str, reason: str = None):
        """Add a decision."""
        self.decisions[path] = SyncDecision(
            path=path,
            action=action,
            reason=reason
        )


class HostessMemoryCuratorAgent:
    """
    Hostess agent specialized for memory sync dialogs.

    Asks user about:
    - Added files: save full or compress?
    - Deleted files: trash or permanent delete?
    - Old files: compress or keep full?

    MARKER-77-08: 30s timeout with auto-approve default decisions.

    Usage:
        curator = HostessMemoryCuratorAgent(hostess_agent)
        decisions = await curator.sync_with_user(diff_result)

        # Apply decisions
        for path, decision in decisions.decisions.items():
            if decision.action == 'trash':
                await trash.move_to_trash(node)
    """

    # MARKER-77-08: Timeout for user response
    DIALOG_TIMEOUT_SECONDS = 30

    # Auto-decisions for system directories
    SYSTEM_DIRS = {
        'node_modules', '__pycache__', '.git', '.venv', 'venv',
        '.cache', '.pytest_cache', 'dist', 'build', '.tox'
    }

    # Optional directories (ask user)
    OPTIONAL_DIRS = {'tests', 'test', 'docs', 'examples', 'samples'}

    def __init__(
        self,
        hostess_agent=None,
        socket_io=None,
        auto_approve_threshold: int = 5
    ):
        """
        Initialize memory curator.

        Args:
            hostess_agent: HostessAgent for tool calling
            socket_io: Socket.IO for real-time communication
            auto_approve_threshold: Auto-approve if changes <= this count
        """
        self.hostess = hostess_agent
        self.sio = socket_io
        self.auto_approve_threshold = auto_approve_threshold

    async def sync_with_user(
        self,
        diff_result: DiffResult,
        user_id: str = "default"
    ) -> SyncDecisions:
        """
        Main dialog: ask user about sync decisions.

        MARKER-77-08: Times out after 30s with default decisions.

        Args:
            diff_result: DiffResult from MemoryDiff
            user_id: User identifier for personalized dialog

        Returns:
            SyncDecisions with user choices (or defaults on timeout)
        """
        decisions = SyncDecisions()

        # Check if changes are below auto-approve threshold
        if diff_result.total_changes <= self.auto_approve_threshold:
            logger.info(f"[MemoryCurator] Auto-approving {diff_result.total_changes} changes")
            decisions = await self._create_default_decisions(diff_result)
            decisions.approved = True
            return decisions

        try:
            # Phase 1: Show summary
            await self._show_summary(diff_result, user_id)

            # Phase 2: Handle added files
            if diff_result.added:
                added_decisions = await asyncio.wait_for(
                    self._handle_added_files(diff_result.added, user_id),
                    timeout=self.DIALOG_TIMEOUT_SECONDS
                )
                decisions.decisions.update(added_decisions)

            # Phase 3: Handle deleted files
            if diff_result.deleted:
                deleted_decisions = await asyncio.wait_for(
                    self._handle_deleted_files(diff_result.deleted, user_id),
                    timeout=self.DIALOG_TIMEOUT_SECONDS
                )
                decisions.decisions.update(deleted_decisions)

            # Phase 4: Compression policy
            compression = await asyncio.wait_for(
                self._handle_compression_policy(user_id),
                timeout=self.DIALOG_TIMEOUT_SECONDS
            )
            decisions.compression_policy = compression

            decisions.approved = True
            logger.info(f"[MemoryCurator] User approved {len(decisions.decisions)} decisions")

        except asyncio.TimeoutError:
            # MARKER-77-08: Timeout fallback
            logger.warning(f"[MemoryCurator] Dialog timeout, using default decisions")
            decisions = await self._create_default_decisions(diff_result)
            decisions.approved = True  # Auto-approve defaults

        return decisions

    async def _show_summary(self, diff: DiffResult, user_id: str):
        """Show sync summary to user."""
        summary = f"""
🔄 Обнаружены расхождения с файловой системой:

✅ Добавлены: {len(diff.added)} файлов
📝 Изменены: {len(diff.modified)} файлов
❌ Удалены: {len(diff.deleted)} файлов
🔗 Изменены связи: {len(diff.edges_added) + len(diff.edges_modified) + len(diff.edges_deleted)}
"""
        await self._send_message(summary, user_id)

    async def _handle_added_files(
        self,
        added: Dict[str, Any],
        user_id: str
    ) -> Dict[str, SyncDecision]:
        """
        Handle decisions for added files.

        - System dirs → auto compress
        - Optional dirs → ask user
        - Code → save full
        """
        decisions = {}

        # Group by type
        system_files = []
        optional_files = []
        code_files = []

        for path in added.keys():
            if self._is_system_path(path):
                system_files.append(path)
            elif self._is_optional_path(path):
                optional_files.append(path)
            else:
                code_files.append(path)

        # Auto-compress system files
        for path in system_files:
            decisions[path] = SyncDecision(
                path=path,
                action="compress",
                reason="system_directory"
            )

        if system_files:
            await self._send_message(
                f"🗜️ Сжимаю {len(system_files)} системных файлов (node_modules, __pycache__, etc.)",
                user_id
            )

        # Ask about optional files
        if optional_files:
            response = await self._ask_user(
                f"📚 {len(optional_files)} файлов из тестов/документации. Сохранить полностью?",
                options=[
                    ("full", "📖 Полностью (768D embeddings)"),
                    ("compress", "🗜️ Сжать (256D)")
                ],
                user_id=user_id
            )

            action = response or "compress"
            for path in optional_files:
                decisions[path] = SyncDecision(
                    path=path,
                    action=action,
                    reason="optional_directory"
                )

        # Code files → full by default
        for path in code_files:
            decisions[path] = SyncDecision(
                path=path,
                action="full",
                reason="code_file"
            )

        if code_files:
            await self._send_message(
                f"💾 Сохраняю {len(code_files)} файлов кода полностью",
                user_id
            )

        return decisions

    async def _handle_deleted_files(
        self,
        deleted: Dict[str, Any],
        user_id: str
    ) -> Dict[str, SyncDecision]:
        """
        Handle decisions for deleted files.

        Key: deleted ≠ delete immediately!
        Default: move to trash (recoverable)
        """
        decisions = {}

        # Show preview of deleted files
        preview_paths = list(deleted.keys())[:5]
        deleted_preview = "\n".join(f"  • {p}" for p in preview_paths)
        if len(deleted) > 5:
            deleted_preview += f"\n  ... и ещё {len(deleted) - 5}"

        response = await self._ask_user(
            f"""⚠️ Эти файлы удалены из файловой системы:
{deleted_preview}

Что сделать?""",
            options=[
                ("trash", "📦 В корзину (можно восстановить)"),
                ("delete", "🗑️ Удалить из VETKA навсегда"),
                ("keep", "📌 Оставить в памяти (они важны!)")
            ],
            user_id=user_id
        )

        action = response or "trash"  # Default: trash (safest)

        for path in deleted.keys():
            decisions[path] = SyncDecision(
                path=path,
                action=action,
                reason="filesystem_deletion"
            )

        return decisions

    async def _handle_compression_policy(self, user_id: str) -> str:
        """Ask about compression policy for old files."""
        response = await self._ask_user(
            "🗜️ Сжимать старые файлы (>30 дней) для экономии памяти?",
            options=[
                ("partial", "🔄 Только >90 дней (рекомендуется)"),
                ("yes", "✅ Да, все >30 дней"),
                ("no", "❌ Нет, оставить полностью")
            ],
            user_id=user_id
        )

        return response or "partial"

    async def _create_default_decisions(self, diff: DiffResult) -> SyncDecisions:
        """
        Create safe default decisions (no user interaction).

        Defaults:
        - Added: full for code, compress for system
        - Deleted: trash (never permanent delete by default!)
        - Compression: partial (>90 days)
        """
        decisions = SyncDecisions()
        decisions.compression_policy = "partial"
        decisions.compression_threshold_days = 90

        # Added files
        for path in diff.added.keys():
            if self._is_system_path(path):
                decisions.add_decision(path, "compress", "auto_system")
            else:
                decisions.add_decision(path, "full", "auto_code")

        # Deleted files → always trash (safe default)
        for path in diff.deleted.keys():
            decisions.add_decision(path, "trash", "auto_safe_default")

        return decisions

    def _is_system_path(self, path: str) -> bool:
        """Check if path is in a system directory."""
        path_lower = path.lower()
        return any(sys_dir in path_lower for sys_dir in self.SYSTEM_DIRS)

    def _is_optional_path(self, path: str) -> bool:
        """Check if path is in an optional directory."""
        path_lower = path.lower()
        return any(opt_dir in path_lower for opt_dir in self.OPTIONAL_DIRS)

    async def _send_message(self, message: str, user_id: str):
        """Send message to user via Socket.IO or log."""
        if self.sio:
            try:
                await self.sio.emit('memory_sync_message', {
                    'type': 'info',
                    'message': message,
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"[MemoryCurator] Socket emit failed: {e}")

        logger.info(f"[MemoryCurator] {message}")

    async def _ask_user(
        self,
        question: str,
        options: List[tuple],
        user_id: str
    ) -> Optional[str]:
        """
        Ask user a question with options.

        In real implementation, this would use Socket.IO
        and wait for user response.

        For now, returns default (first option).
        """
        if self.sio:
            try:
                # Send question
                await self.sio.emit('memory_sync_question', {
                    'type': 'question',
                    'question': question,
                    'options': [{'value': v, 'label': l} for v, l in options],
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat()
                })

                # TODO: Wait for response via callback
                # For now, return default
                await asyncio.sleep(0.1)  # Small delay for logging

            except Exception as e:
                logger.warning(f"[MemoryCurator] Socket question failed: {e}")

        # Default: first option
        logger.info(f"[MemoryCurator] Q: {question[:50]}... → Default: {options[0][0]}")
        return options[0][0]


# ========== FACTORY FUNCTION ==========

_curator_instance: Optional[HostessMemoryCuratorAgent] = None


def get_memory_curator(
    hostess_agent=None,
    socket_io=None
) -> HostessMemoryCuratorAgent:
    """
    Factory function - returns singleton MemoryCurator.

    Args:
        hostess_agent: HostessAgent instance
        socket_io: Socket.IO server

    Returns:
        HostessMemoryCuratorAgent singleton
    """
    global _curator_instance

    if _curator_instance is None:
        _curator_instance = HostessMemoryCuratorAgent(
            hostess_agent=hostess_agent,
            socket_io=socket_io
        )

    return _curator_instance
