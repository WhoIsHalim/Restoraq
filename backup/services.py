from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from backup.models import BackupRecord


class BackupService:
    @classmethod
    def run_backup(cls, *, backup_type: str = BackupRecord.TYPE_AUTO) -> BackupRecord:
        record = BackupRecord.objects.create(
            backup_type=backup_type,
            storage_backend="local",
            status=BackupRecord.STATUS_PENDING,
            started_at=timezone.now(),
        )
        backup_dir = Path(settings.BACKUP_LOCAL_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{stamp}.sql"
        file_path = backup_dir / filename

        env = os.environ.copy()
        env["PGPASSWORD"] = settings.DATABASES["default"].get("PASSWORD", "")
        cmd = [
            "pg_dump",
            "-h",
            settings.DATABASES["default"].get("HOST", "127.0.0.1"),
            "-p",
            str(settings.DATABASES["default"].get("PORT", "5432")),
            "-U",
            settings.DATABASES["default"].get("USER", "postgres"),
            "-d",
            settings.DATABASES["default"].get("NAME", "restaurant_saas"),
            "-f",
            str(file_path),
        ]

        try:
            subprocess.run(cmd, check=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            checksum = hashlib.sha256(file_path.read_bytes()).hexdigest()
            file_size = file_path.stat().st_size
            record.file_path = str(file_path)
            record.file_size = file_size
            record.checksum = checksum
            record.status = BackupRecord.STATUS_SUCCESS
            record.completed_at = timezone.now()
            record.storage_backend = "local"
            record.save(
                update_fields=[
                    "file_path",
                    "file_size",
                    "checksum",
                    "status",
                    "completed_at",
                    "storage_backend",
                    "updated_at",
                ]
            )

            cls._prune_local_backups(keep_days=30)

            if settings.AWS_S3_ENABLED and settings.AWS_STORAGE_BUCKET_NAME:
                cls._upload_to_s3(file_path)
                cls._prune_s3_backups(keep_days=90)
            return record
        except Exception as exc:  # pragma: no cover
            record.status = BackupRecord.STATUS_FAILED
            record.completed_at = timezone.now()
            record.error_message = str(exc)
            record.save(update_fields=["status", "completed_at", "error_message", "updated_at"])
            return record

    @staticmethod
    def _prune_local_backups(*, keep_days: int) -> None:
        backup_dir = Path(settings.BACKUP_LOCAL_DIR)
        if not backup_dir.exists():
            return
        cutoff = timezone.now() - timezone.timedelta(days=keep_days)
        for item in backup_dir.glob("backup_*.sql"):
            mtime = timezone.make_aware(timezone.datetime.fromtimestamp(item.stat().st_mtime))
            if mtime < cutoff:
                item.unlink(missing_ok=True)

    @staticmethod
    def _upload_to_s3(file_path: Path) -> None:
        import boto3

        s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
        key = f"{settings.BACKUP_S3_PREFIX}/{file_path.name}"
        s3.upload_file(str(file_path), settings.AWS_STORAGE_BUCKET_NAME, key)

    @staticmethod
    def _prune_s3_backups(*, keep_days: int) -> None:
        import boto3

        s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
        cutoff = timezone.now() - timezone.timedelta(days=keep_days)
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Prefix=f"{settings.BACKUP_S3_PREFIX}/",
        )
        for page in pages:
            for obj in page.get("Contents", []):
                last_modified = obj["LastModified"]
                if last_modified < cutoff:
                    s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=obj["Key"])
