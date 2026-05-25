from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

from audit.models import AuditLog


class AuditService:
    @staticmethod
    def log_action(
        *,
        request=None,
        tenant=None,
        branch=None,
        user=None,
        action: str,
        model: str,
        object_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        if request is not None:
            tenant = tenant or getattr(request, "tenant", None)
            branch = branch or getattr(getattr(request, "membership", None), "primary_branch", None)
            user = user or (request.user if getattr(request, "user", None) and request.user.is_authenticated else None)
            ip = getattr(request, "client_ip", None)
            device = getattr(request, "client_device", "")
        else:
            ip = None
            device = ""

        if tenant is None:
            return None

        return AuditLog.objects.create(
            tenant=tenant,
            branch=branch,
            user=user,
            action=action,
            model=model,
            object_id=object_id,
            ip=ip,
            device=device,
            metadata_json=metadata or {},
        )


class AuditRetentionService:
    @staticmethod
    def cleanup() -> int:
        retention_days = int(getattr(settings, "AUDIT_RETENTION_DAYS", 730))
        cutoff = timezone.now() - timedelta(days=retention_days)
        deleted, _ = AuditLog.objects.filter(timestamp__lt=cutoff).delete()
        return deleted
