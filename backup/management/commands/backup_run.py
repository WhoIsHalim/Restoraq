from __future__ import annotations

from django.core.management.base import BaseCommand

from backup.models import BackupRecord
from backup.services import BackupService


class Command(BaseCommand):
    help = "Run manual backup and store metadata"

    def handle(self, *args, **options):
        record = BackupService.run_backup(backup_type=BackupRecord.TYPE_MANUAL)
        if record.status == BackupRecord.STATUS_SUCCESS:
            self.stdout.write(self.style.SUCCESS(f"Backup complete: {record.file_path}"))
        else:
            self.stdout.write(self.style.ERROR(f"Backup failed: {record.error_message}"))
