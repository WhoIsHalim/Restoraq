from __future__ import annotations

from django.db import models

from core.models import TenantBranchScopedModel


class Employee(TenantBranchScopedModel):
    full_name = models.CharField(max_length=180)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    position = models.CharField(max_length=120)
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    hired_on = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.full_name


class PayrollRecord(TenantBranchScopedModel):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payroll_records")
    period_start = models.DateField()
    period_end = models.DateField()
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        ordering = ["-period_end"]

    def __str__(self) -> str:
        return f"{self.employee.full_name} {self.period_start} - {self.period_end}"
