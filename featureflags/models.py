from __future__ import annotations

from django.db import models

from core.models import TimeStampedModel


class FeatureCatalog(TimeStampedModel):
    TYPE_BOOL = "bool"
    TYPE_INT = "int"
    TYPE_JSON = "json"

    VALUE_TYPE_CHOICES = [
        (TYPE_BOOL, "Boolean"),
        (TYPE_INT, "Integer"),
        (TYPE_JSON, "JSON"),
    ]

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    value_type = models.CharField(max_length=16, choices=VALUE_TYPE_CHOICES, default=TYPE_BOOL)

    def __str__(self) -> str:
        return self.name


class PlanFeature(TimeStampedModel):
    plan = models.ForeignKey("subscriptions.SubscriptionPlan", on_delete=models.CASCADE, related_name="feature_mappings")
    feature = models.ForeignKey(FeatureCatalog, on_delete=models.CASCADE, related_name="plan_mappings")
    enabled = models.BooleanField(default=False)
    value_json = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["plan", "feature"], name="uniq_plan_feature_mapping"),
        ]

    def __str__(self) -> str:
        return f"{self.plan.code}:{self.feature.name}"


class TenantFeatureOverride(TimeStampedModel):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="feature_overrides")
    feature = models.ForeignKey(FeatureCatalog, on_delete=models.CASCADE, related_name="tenant_overrides")
    enabled = models.BooleanField(default=False)
    value_json = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "feature"], name="uniq_tenant_feature_override"),
        ]

    def __str__(self) -> str:
        return f"{self.tenant.slug}:{self.feature.name}"
