from __future__ import annotations

from django.db import models
from django.utils.text import slugify

from core.models import TimeStampedModel


class Tenant(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    default_language = models.CharField(max_length=8, default="ar")
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=14)
    tax_inclusive_pricing = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class TenantDomain(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="domains")
    domain = models.CharField(max_length=255, unique=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_primary", "domain"]

    def __str__(self) -> str:
        return f"{self.domain} ({self.tenant.slug})"
