from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from audit.services import AuditService
from inventory.models import Ingredient, LowStockAlert, Recipe, StockEntry


class StockService:
    @staticmethod
    @transaction.atomic
    def record_entry(
        *,
        tenant,
        branch,
        ingredient: Ingredient,
        movement_type: str,
        quantity: Decimal,
        actor=None,
        note: str = "",
        reference: str = "",
    ) -> StockEntry:
        entry = StockEntry.objects.create(
            tenant=tenant,
            branch=branch,
            ingredient=ingredient,
            movement_type=movement_type,
            quantity=quantity,
            created_by=actor,
            note=note,
            reference=reference,
        )

        if movement_type == StockEntry.MOVEMENT_IN:
            ingredient.current_stock += quantity
        elif movement_type == StockEntry.MOVEMENT_OUT:
            ingredient.current_stock -= quantity
        else:
            ingredient.current_stock = quantity
        ingredient.save(update_fields=["current_stock", "updated_at"])

        StockService.ensure_low_stock_alert(ingredient=ingredient, tenant=tenant, branch=branch)
        return entry

    @staticmethod
    @transaction.atomic
    def apply_recipe_consumption(*, order, actor=None) -> None:
        recipe_map = {}
        recipe_rows = Recipe.objects.filter(tenant=order.tenant, product_id__in=order.items.values_list("product_id", flat=True))
        for recipe in recipe_rows:
            recipe_map.setdefault(recipe.product_id, []).append(recipe)

        for item in order.items.all().select_related("product"):
            recipes = recipe_map.get(item.product_id, [])
            for recipe in recipes:
                deduction = (Decimal(recipe.quantity_per_unit) * Decimal(item.quantity)).quantize(Decimal("0.001"))
                StockService.record_entry(
                    tenant=order.tenant,
                    branch=order.branch,
                    ingredient=recipe.ingredient,
                    movement_type=StockEntry.MOVEMENT_OUT,
                    quantity=deduction,
                    actor=actor,
                    note=f"Auto deduction for order {order.order_number}",
                    reference=order.order_number,
                )

        AuditService.log_action(
            tenant=order.tenant,
            branch=order.branch,
            user=actor,
            action="stock_updated",
            model="inventory.StockEntry",
            object_id=str(order.id),
            metadata={"order_number": order.order_number},
        )

    @staticmethod
    def ensure_low_stock_alert(*, ingredient, tenant, branch) -> None:
        if ingredient.current_stock > ingredient.reorder_level:
            return
        LowStockAlert.objects.get_or_create(
            tenant=tenant,
            branch=branch,
            ingredient=ingredient,
            status=LowStockAlert.STATUS_OPEN,
            defaults={
                "current_stock": ingredient.current_stock,
                "reorder_level": ingredient.reorder_level,
            },
        )

    @staticmethod
    @transaction.atomic
    def resolve_alert(*, alert: LowStockAlert, actor=None):
        alert.status = LowStockAlert.STATUS_RESOLVED
        alert.resolved_at = timezone.now()
        alert.resolved_by = actor
        alert.save(update_fields=["status", "resolved_at", "resolved_by", "updated_at"])
