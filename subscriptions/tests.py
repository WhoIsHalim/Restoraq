from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from subscriptions.models import Subscription, SubscriptionPlan
from subscriptions.services import SubscriptionService
from tenants.models import Tenant


class SubscriptionServiceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme", slug="acme")
        self.plan = SubscriptionPlan.objects.create(code="basic", name="Basic", price_egp=500)

    def test_active_subscription_allows_write(self):
        today = timezone.localdate()
        Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=5),
        )
        decision = SubscriptionService.evaluate_access(self.tenant, "/orders/api/create/", "POST")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.read_only)

    def test_grace_allows_read_only(self):
        today = timezone.localdate()
        Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            start_date=today - timedelta(days=15),
            end_date=today - timedelta(days=1),
            grace_period_end=today + timedelta(days=3),
        )
        post_decision = SubscriptionService.evaluate_access(self.tenant, "/orders/api/create/", "POST")
        get_decision = SubscriptionService.evaluate_access(self.tenant, "/orders/", "GET")
        self.assertFalse(post_decision.allowed)
        self.assertTrue(post_decision.read_only)
        self.assertTrue(get_decision.allowed)

    def test_expired_blocks_access(self):
        today = timezone.localdate()
        Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=10),
            grace_period_end=today - timedelta(days=5),
        )
        decision = SubscriptionService.evaluate_access(self.tenant, "/orders/", "GET")
        self.assertFalse(decision.allowed)
