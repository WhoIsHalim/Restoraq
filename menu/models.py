from __future__ import annotations

from django.db import models

from core.models import TenantBranchScopedModel


class Category(TenantBranchScopedModel):
    name = models.CharField(max_length=120)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "branch", "name"], name="uniq_category_name_per_branch"),
        ]

    def __str__(self) -> str:
        return self.name


class Product(TenantBranchScopedModel):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=64)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=14)
    is_tax_inclusive = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to="menu/products/", null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "sku"], name="uniq_product_sku_per_tenant"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"


class ModifierGroup(TenantBranchScopedModel):
    name = models.CharField(max_length=120)
    is_required = models.BooleanField(default=False)
    max_select = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "branch", "name"], name="uniq_modifier_group_name_per_branch"),
        ]

    def __str__(self) -> str:
        return self.name


class ModifierOption(TenantBranchScopedModel):
    group = models.ForeignKey(ModifierGroup, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=120)
    price_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "group", "name"], name="uniq_modifier_option_per_group"),
        ]

    def __str__(self) -> str:
        return f"{self.group.name} - {self.name}"


class ProductModifier(TenantBranchScopedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_modifiers")
    modifier_group = models.ForeignKey(ModifierGroup, on_delete=models.CASCADE, related_name="product_links")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "product", "modifier_group"],
                name="uniq_product_modifier_group_link",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product.name} -> {self.modifier_group.name}"
