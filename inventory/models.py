from __future__ import annotations

from django.db import models

from core.models import TenantBranchScopedModel


class Ingredient(TenantBranchScopedModel):
    name = models.CharField(max_length=160)
    unit = models.CharField(max_length=30, default="unit")
    current_stock = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "branch", "name"], name="uniq_ingredient_name_per_branch"),
        ]

    def __str__(self) -> str:
        return self.name


class Supplier(TenantBranchScopedModel):
    name = models.CharField(max_length=160)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "branch", "name"], name="uniq_supplier_name_per_branch"),
        ]

    def __str__(self) -> str:
        return self.name


class StockEntry(TenantBranchScopedModel):
    MOVEMENT_IN = "in"
    MOVEMENT_OUT = "out"
    MOVEMENT_ADJUSTMENT = "adjustment"

    MOVEMENT_CHOICES = [
        (MOVEMENT_IN, "IN"),
        (MOVEMENT_OUT, "OUT"),
        (MOVEMENT_ADJUSTMENT, "ADJUSTMENT"),
    ]

    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="stock_entries")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_entries")
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_CHOICES)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    reference = models.CharField(max_length=128, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.ingredient.name} {self.movement_type} {self.quantity}"


class Recipe(TenantBranchScopedModel):
    product = models.ForeignKey("menu.Product", on_delete=models.CASCADE, related_name="recipes")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="recipes")
    quantity_per_unit = models.DecimalField(max_digits=14, decimal_places=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "product", "ingredient"], name="uniq_recipe_line"),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} -> {self.ingredient.name}"


class LowStockAlert(TenantBranchScopedModel):
    STATUS_OPEN = "open"
    STATUS_RESOLVED = "resolved"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="alerts")
    current_stock = models.DecimalField(max_digits=14, decimal_places=3)
    reorder_level = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.ingredient.name} ({self.status})"
