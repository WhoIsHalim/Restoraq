from __future__ import annotations

from django.db import models

from core.models import TenantBranchScopedModel, TenantScopedModel


class Printer(TenantBranchScopedModel):
    CONNECTION_USB = "usb"
    CONNECTION_NETWORK = "network"

    CONNECTION_CHOICES = [
        (CONNECTION_USB, "USB"),
        (CONNECTION_NETWORK, "Network"),
    ]

    name = models.CharField(max_length=120)
    connection_type = models.CharField(max_length=16, choices=CONNECTION_CHOICES, default=CONNECTION_USB)
    device_identifier = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "branch", "name"], name="uniq_printer_name_per_branch"),
        ]

    def __str__(self) -> str:
        return self.name


class BranchPrinterConfig(TenantScopedModel):
    branch = models.OneToOneField("restaurants.Branch", on_delete=models.CASCADE, related_name="printer_config")
    customer_printer = models.ForeignKey(
        Printer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_configs",
    )
    kitchen_printer = models.ForeignKey(
        Printer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kitchen_configs",
    )
    delivery_printer = models.ForeignKey(
        Printer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_configs",
    )
    auto_print = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Printers: {self.branch.name}"


class PrintTemplate(TenantScopedModel):
    TYPE_CUSTOMER = "customer"
    TYPE_KITCHEN = "kitchen"
    TYPE_DELIVERY = "delivery"

    TYPE_CHOICES = [
        (TYPE_CUSTOMER, "Customer"),
        (TYPE_KITCHEN, "Kitchen"),
        (TYPE_DELIVERY, "Delivery"),
    ]

    code = models.CharField(max_length=32, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120)
    content = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="uniq_print_template_code"),
        ]

    def __str__(self) -> str:
        return f"{self.tenant.slug} - {self.code}"


class PrintJob(TenantBranchScopedModel):
    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_ACKED = "acked"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_SENT, "Sent"),
        (STATUS_ACKED, "Acknowledged"),
        (STATUS_FAILED, "Failed"),
    ]

    TEMPLATE_CUSTOMER = "customer"
    TEMPLATE_KITCHEN = "kitchen"
    TEMPLATE_DELIVERY = "delivery"

    TEMPLATE_CHOICES = [
        (TEMPLATE_CUSTOMER, "Customer Receipt"),
        (TEMPLATE_KITCHEN, "Kitchen Receipt"),
        (TEMPLATE_DELIVERY, "Delivery Receipt"),
    ]

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="print_jobs")
    printer = models.ForeignKey(Printer, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs")
    template_type = models.CharField(max_length=16, choices=TEMPLATE_CHOICES)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    acked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order.order_number}:{self.template_type}:{self.status}"
