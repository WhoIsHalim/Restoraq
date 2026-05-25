from __future__ import annotations

from django.core.management.base import BaseCommand

from core.constants import PLAN_FEATURE_PRESET_A
from featureflags.models import FeatureCatalog, PlanFeature
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Seed feature catalog and default plan matrix (Preset A)"

    def handle(self, *args, **options):
        feature_names = set()
        for feature_map in PLAN_FEATURE_PRESET_A.values():
            feature_names.update(feature_map.keys())

        for name in sorted(feature_names):
            catalog, _ = FeatureCatalog.objects.get_or_create(name=name)
            self.stdout.write(self.style.SUCCESS(f"Feature ready: {catalog.name}"))

        for plan_code, feature_map in PLAN_FEATURE_PRESET_A.items():
            plan = SubscriptionPlan.objects.filter(code=plan_code).first()
            if not plan:
                self.stdout.write(self.style.WARNING(f"Plan missing: {plan_code}"))
                continue
            for feature_name, value in feature_map.items():
                feature = FeatureCatalog.objects.get(name=feature_name)
                enabled = bool(value) if not isinstance(value, int) or feature_name != "branches_limit" else True
                value_json = {"value": value}
                PlanFeature.objects.update_or_create(
                    plan=plan,
                    feature=feature,
                    defaults={"enabled": enabled, "value_json": value_json},
                )
            self.stdout.write(self.style.SUCCESS(f"Feature map ready: {plan.code}"))
