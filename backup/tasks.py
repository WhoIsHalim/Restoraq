from __future__ import annotations

from celery import shared_task

from backup.models import BackupRecord
from backup.services import BackupService


@shared_task
def daily_backup_task() -> int:
    record = BackupService.run_backup(backup_type=BackupRecord.TYPE_AUTO)
    return record.id
