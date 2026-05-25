from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from featureflags.models import FeatureCatalog, PlanFeature
from menu.models import Category, Product
from orders.services import OrderService
from restaurants.models import Branch
from subscriptions.models import Subscription, SubscriptionPlan
from tenants.models import Tenant
from users.models import TenantMembership


class ReportsAnalyticsAPITests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Analytics Tenant", slug="analytics-tenant")
        self.plan = SubscriptionPlan.objects.create(code="pro", name="Pro", price_egp=2500)
        Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=30),
        )
        kds_feature = FeatureCatalog.objects.create(name="kds_screen", value_type=FeatureCatalog.TYPE_BOOL)
        PlanFeature.objects.create(plan=self.plan, feature=kds_feature, enabled=True, value_json={"value": True})

        self.branch = Branch.objects.create(tenant=self.tenant, name="Main", code="MAIN")
        category = Category.objects.create(tenant=self.tenant, branch=self.branch, name="Meals")
        self.product = Product.objects.create(
            tenant=self.tenant,
            branch=self.branch,
            category=category,
            name="Pasta",
            sku="PASTA-1",
            price=Decimal("150.00"),
            tax_rate=Decimal("14"),
            is_tax_inclusive=True,
        )
        self.user = get_user_model().objects.create_user(username="owner_reports", password="secret123")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role_name="RestaurantOwner",
            primary_branch=self.branch,
            is_active=True,
        )

        OrderService.create_order(
            tenant=self.tenant,
            branch=self.branch,
            user=self.user,
            payload={
                "client_order_uuid": "55555555-5555-4555-8555-555555555555",
                "items": [{"product_id": self.product.id, "quantity": 2}],
                "payments": [{"method": "cash", "amount": "300.00"}],
            },
            source="online",
        )

    def test_reports_analytics_api_returns_multi_chart_payload(self):
        self.client.login(username=self.user.username, password="secret123")
        response = self.client.get("/reports/api/analytics/?period=monthly")
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertIn("trend", payload)
        self.assertIn("status", payload)
        self.assertIn("top_products", payload)
        self.assertIn("branches", payload)
        self.assertTrue(len(payload["trend"]["labels"]) >= 1)
