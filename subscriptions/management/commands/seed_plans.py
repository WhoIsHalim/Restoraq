from __future__ import annotations

from django.core.management.base import BaseCommand

from core.constants import PLAN_BASIC, PLAN_MULTIBRANCH, PLAN_PRO, PLAN_STANDARD
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Seed default subscription plans"

    def handle(self, *args, **options):
        plans = [
            (PLAN_BASIC, "Basic", 500),
            (PLAN_STANDARD, "Standard", 950),
            (PLAN_MULTIBRANCH, "MultiBranch", 1300),
            (PLAN_PRO, "Pro", 2500),
        ]
        for code, name, price in plans:
            plan, _ = SubscriptionPlan.objects.update_or_create(
                code=code,
                defaults={"name": name, "price_egp": price},
            )
            self.stdout.write(self.style.SUCCESS(f"Plan ready: {plan.code}"))
