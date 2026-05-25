from __future__ import annotations

from django.db import models

from core.models import TenantScopedModel


class TenantMembership(TenantScopedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="tenant_memberships")
    role_name = models.CharField(max_length=64)
    primary_branch = models.ForeignKey(
        "restaurants.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "user"], name="uniq_membership_per_tenant_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} @ {self.tenant.slug}"
