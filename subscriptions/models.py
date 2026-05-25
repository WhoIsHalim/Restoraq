from __future__ import annotations

from datetime import timedelta

from django.db import models

from core.models import TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    price_egp = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["price_egp"]

    def __str__(self) -> str:
        return f"{self.name} ({self.price_egp} EGP)"


class Subscription(TimeStampedModel):
    STATUS_ACTIVE = "active"
    STATUS_GRACE = "grace"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_GRACE, "Grace"),
        (STATUS_EXPIRED, "Expired"),
    ]

    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    start_date = models.DateField()
    end_date = models.DateField()
    grace_period_end = models.DateField(blank=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["-end_date"]

    def save(self, *args, **kwargs):
        if not self.grace_period_end:
            self.grace_period_end = self.end_date + timedelta(days=5)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.tenant.slug} - {self.plan.code}"
