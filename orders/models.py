from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q

from core.models import TenantBranchScopedModel


class Order(TenantBranchScopedModel):
    STATUS_DRAFT = "draft"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    KITCHEN_PENDING = "pending"
    KITCHEN_PREPARING = "preparing"
    KITCHEN_READY = "ready"
    KITCHEN_STATUS_CHOICES = [
        (KITCHEN_PENDING, "Pending"),
        (KITCHEN_PREPARING, "Preparing"),
        (KITCHEN_READY, "Ready"),
    ]

    TYPE_DINE_IN = "dine_in"
    TYPE_TAKEAWAY = "takeaway"
    TYPE_DELIVERY = "delivery"
    ORDER_TYPE_CHOICES = [
        (TYPE_DINE_IN, "Dine In"),
        (TYPE_TAKEAWAY, "Takeaway"),
        (TYPE_DELIVERY, "Delivery"),
    ]

    order_number = models.CharField(max_length=40)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    pending_sync = models.BooleanField(default=False)
    client_order_uuid = models.UUIDField(null=True, blank=True, default=None)
    source = models.CharField(max_length=32, default="online")
    order_type = models.CharField(max_length=16, choices=ORDER_TYPE_CHOICES, default=TYPE_DINE_IN)
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    customer_name_snapshot = models.CharField(max_length=180, blank=True)
    customer_phone_snapshot = models.CharField(max_length=32, blank=True)
    customer_address_snapshot = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    kitchen_status = models.CharField(max_length=16, choices=KITCHEN_STATUS_CHOICES, default=KITCHEN_PENDING)
    kitchen_started_at = models.DateTimeField(null=True, blank=True)
    kitchen_completed_at = models.DateTimeField(null=True, blank=True)
    cooking_duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "order_number"], name="uniq_order_number_per_tenant"),
            models.UniqueConstraint(
                fields=["tenant", "client_order_uuid"],
                condition=Q(client_order_uuid__isnull=False),
                name="uniq_client_uuid_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order_number}"


class OrderItem(TenantBranchScopedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("menu.Product", on_delete=models.PROTECT, related_name="order_items")
    name_snapshot = models.CharField(max_length=160)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return f"{self.order.order_number} - {self.name_snapshot}"


class Payment(TenantBranchScopedModel):
    METHOD_CASH = "cash"
    METHOD_CARD = "card"
    METHOD_WALLET = "wallet"
    METHOD_OTHER = "other"

    METHOD_CHOICES = [
        (METHOD_CASH, "Cash"),
        (METHOD_CARD, "Card"),
        (METHOD_WALLET, "Wallet"),
        (METHOD_OTHER, "Other"),
    ]

    STATUS_CAPTURED = "captured"
    STATUS_CAPTURED_UNVERIFIED = "captured_unverified"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_CAPTURED, "Captured"),
        (STATUS_CAPTURED_UNVERIFIED, "Captured - Unverified"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=16, choices=METHOD_CHOICES, default=METHOD_CASH)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_CAPTURED)
    reference = models.CharField(max_length=128, blank=True)
    requires_manual_review = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.order.order_number} - {self.method}"


class PaymentReview(TenantBranchScopedModel):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="review")
    reviewer = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Review {self.payment_id} - {self.status}"
