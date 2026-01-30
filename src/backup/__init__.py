"""
VETKA Phase 77: Backup System.

Safe point creation before memory sync operations.
Exports VetkaBackup for complete state backup and restore.

@status: active
@phase: 96
@depends: vetka_backup
@used_by: memory, orchestration
"""

from .vetka_backup import VetkaBackup, BackupMetadata, get_vetka_backup

__all__ = ['VetkaBackup', 'BackupMetadata', 'get_vetka_backup']
