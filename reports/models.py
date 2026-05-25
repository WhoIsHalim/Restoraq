from __future__ import annotations

from django.db import models

from core.models import TenantBranchScopedModel


class ReportSnapshot(TenantBranchScopedModel):
    report_key = models.CharField(max_length=64)
    period_start = models.DateField()
    period_end = models.DateField()
    payload_json = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "report_key", "period_start", "period_end"],
                name="uniq_report_snapshot_scope",
            )
        ]

    def __str__(self) -> str:
        return f"{self.report_key} [{self.period_start}:{self.period_end}]"
