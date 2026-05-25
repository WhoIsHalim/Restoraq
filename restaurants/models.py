from __future__ import annotations

from django.db import models

from core.models import TenantScopedModel, TenantBranchScopedModel


class Branch(TenantScopedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="uniq_branch_code_per_tenant"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant.slug})"


class RestaurantSetting(TenantScopedModel):
    currency = models.CharField(max_length=8, default="EGP")
    receipt_footer = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant"], name="uniq_restaurant_setting_per_tenant"),
        ]

    def __str__(self) -> str:
        return f"Settings: {self.tenant.slug}"


class FloorArea(TenantBranchScopedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "branch", "name"], name="uniq_floor_area_per_branch"),
        ]

    def __str__(self) -> str:
        return self.name


class DiningTable(TenantBranchScopedModel):
    name = models.CharField(max_length=120)
    capacity = models.PositiveIntegerField(default=2)
    is_active = models.BooleanField(default=True)
    area = models.ForeignKey(FloorArea, on_delete=models.SET_NULL, null=True, blank=True, related_name="tables")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "branch", "name"], name="uniq_table_name_per_branch"),
        ]

    def __str__(self) -> str:
        return f"{self.name}"


class Reservation(TenantBranchScopedModel):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
    ]

    SOURCE_PHONE = "phone"
    SOURCE_WALKIN = "walkin"
    SOURCE_ONLINE = "online"
    SOURCE_CHOICES = [
        (SOURCE_PHONE, "Phone"),
        (SOURCE_WALKIN, "Walk-in"),
        (SOURCE_ONLINE, "Online"),
    ]

    customer_name = models.CharField(max_length=180)
    customer_phone = models.CharField(max_length=32, blank=True)
    reservation_time = models.DateTimeField()
    party_size = models.PositiveIntegerField(default=2)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_PHONE)
    table = models.ForeignKey(DiningTable, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservations")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-reservation_time"]

    def __str__(self) -> str:
        return f"{self.customer_name} - {self.reservation_time}"
