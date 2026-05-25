from __future__ import annotations

from celery import shared_task

from audit.services import AuditRetentionService


@shared_task
def cleanup_old_audit_logs() -> int:
    return AuditRetentionService.cleanup()
