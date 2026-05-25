from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from featureflags.models import FeatureCatalog, PlanFeature, TenantFeatureOverride
from featureflags.services import FeatureService
from subscriptions.models import Subscription, SubscriptionPlan
from tenants.models import Tenant


class FeatureServiceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme", slug="acme")
        self.plan = SubscriptionPlan.objects.create(code="standard", name="Standard", price_egp=950)
        Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=20),
        )
        self.feature = FeatureCatalog.objects.create(name="advanced_inventory", value_type=FeatureCatalog.TYPE_BOOL)
        PlanFeature.objects.create(plan=self.plan, feature=self.feature, enabled=True, value_json={"value": True})

    def test_plan_feature_enabled(self):
        self.assertTrue(FeatureService.is_enabled(self.tenant, "advanced_inventory"))

    def test_tenant_override_takes_precedence(self):
        TenantFeatureOverride.objects.create(
            tenant=self.tenant,
            feature=self.feature,
            enabled=False,
            value_json={"value": False},
        )
        self.assertFalse(FeatureService.is_enabled(self.tenant, "advanced_inventory"))
