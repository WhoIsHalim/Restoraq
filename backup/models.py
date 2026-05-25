from __future__ import annotations

from django.db import models

from core.models import TimeStampedModel


class BackupRecord(TimeStampedModel):
    TYPE_AUTO = "auto"
    TYPE_MANUAL = "manual"

    TYPE_CHOICES = [
        (TYPE_AUTO, "Automated"),
        (TYPE_MANUAL, "Manual"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    backup_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_AUTO)
    storage_backend = models.CharField(max_length=16, default="local")
    file_path = models.CharField(max_length=500, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    file_size = models.BigIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.backup_type} - {self.status}"
