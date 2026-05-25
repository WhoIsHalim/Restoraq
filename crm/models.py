from __future__ import annotations

from django.db import models

from core.models import TenantBranchScopedModel


class Customer(TenantBranchScopedModel):
    name = models.CharField(max_length=180)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    loyalty_points = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "phone"], name="uniq_customer_phone_per_tenant"),
        ]

    def __str__(self) -> str:
        return self.name
