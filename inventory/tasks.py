from __future__ import annotations

from celery import shared_task

from inventory.models import Ingredient
from inventory.services import StockService


@shared_task
def detect_low_stock_alerts() -> int:
    count = 0
    for ingredient in Ingredient.objects.filter(is_active=True):
        StockService.ensure_low_stock_alert(
            ingredient=ingredient,
            tenant=ingredient.tenant,
            branch=ingredient.branch,
        )
        count += 1
    return count
