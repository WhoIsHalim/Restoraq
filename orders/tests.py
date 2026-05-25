from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from crm.models import Customer
from menu.models import Category, Product
from featureflags.models import FeatureCatalog, PlanFeature
from orders.models import Payment, PaymentReview
from orders.services import OrderService
from restaurants.models import Branch
from subscriptions.models import Subscription, SubscriptionPlan
from tenants.models import Tenant
from users.models import TenantMembership


class OrderServiceOfflinePaymentTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme", slug="acme")
        self.plan = SubscriptionPlan.objects.create(code="pro", name="Pro", price_egp=2500)
        Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=30),
        )
        self.branch = Branch.objects.create(tenant=self.tenant, name="Main", code="M01")
        self.user = get_user_model().objects.create_user(username="cashier", password="secret123")
        category = Category.objects.create(tenant=self.tenant, branch=self.branch, name="Burgers")
        self.product = Product.objects.create(
            tenant=self.tenant,
            branch=self.branch,
            category=category,
            name="Classic",
            sku="CL-1",
            price=Decimal("100.00"),
            tax_rate=Decimal("14"),
            is_tax_inclusive=True,
        )

    def test_offline_non_cash_creates_review(self):
        payload = {
            "client_order_uuid": "03e1d79f-fdb9-4747-87d2-a273e2f8d2aa",
            "items": [{"product_id": self.product.id, "quantity": 1}],
            "payments": [{"method": "card", "amount": "100.00"}],
        }
        order = OrderService.create_order(
            tenant=self.tenant,
            branch=self.branch,
            user=self.user,
            payload=payload,
            source="offline",
        )
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.status, Payment.STATUS_CAPTURED_UNVERIFIED)
        self.assertTrue(payment.requires_manual_review)
        self.assertTrue(PaymentReview.objects.filter(payment=payment).exists())


class CashierAndKitchenPermissionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Demo Tenant", slug="demo-tenant")
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
        self.branch_two = Branch.objects.create(tenant=self.tenant, name="Second", code="SECOND")
        category = Category.objects.create(tenant=self.tenant, branch=self.branch, name="Fast Food")
        category_two = Category.objects.create(tenant=self.tenant, branch=self.branch_two, name="Desserts")
        self.product = Product.objects.create(
            tenant=self.tenant,
            branch=self.branch,
            category=category,
            name="Burger",
            sku="BURGER-1",
            price=Decimal("120.00"),
            tax_rate=Decimal("14"),
            is_tax_inclusive=True,
        )
        self.product_two = Product.objects.create(
            tenant=self.tenant,
            branch=self.branch_two,
            category=category_two,
            name="Cake",
            sku="CAKE-1",
            price=Decimal("95.00"),
            tax_rate=Decimal("14"),
            is_tax_inclusive=True,
        )

        user_model = get_user_model()
        self.cashier = user_model.objects.create_user(username="cashier_test", password="secret123")
        self.branch_manager = user_model.objects.create_user(username="branch_manager_test", password="secret123")
        self.kitchen = user_model.objects.create_user(username="kitchen_test", password="secret123")
        self.owner = user_model.objects.create_user(username="owner_test", password="secret123")
        self.owner_no_branch = user_model.objects.create_user(username="owner_nobranch", password="secret123")

        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.cashier,
            role_name="Cashier",
            primary_branch=self.branch,
            is_active=True,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.branch_manager,
            role_name="BranchManager",
            primary_branch=self.branch,
            is_active=True,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.kitchen,
            role_name="KitchenStaff",
            primary_branch=self.branch,
            is_active=True,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.owner,
            role_name="RestaurantOwner",
            primary_branch=self.branch,
            is_active=True,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.owner_no_branch,
            role_name="RestaurantOwner",
            primary_branch=None,
            is_active=True,
        )

    def test_cashier_can_open_pos_and_create_order(self):
        self.client.login(username=self.cashier.username, password="secret123")
        pos_response = self.client.get("/pos/")
        self.assertEqual(pos_response.status_code, 200)

        payload = {
            "client_order_uuid": "11111111-1111-4111-8111-111111111111",
            "items": [{"product_id": self.product.id, "quantity": 1}],
            "payments": [{"method": "cash", "amount": "120.00"}],
            "source": "online",
        }
        create_response = self.client.post(
            "/orders/api/create/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 200)

    def test_pos_menu_branch_options_respect_role_scope(self):
        self.client.login(username=self.cashier.username, password="secret123")
        cashier_payload = self.client.get("/pos/api/menu/").json()
        self.assertTrue(cashier_payload["branch_locked"])
        self.assertEqual(len(cashier_payload["branches"]), 1)
        self.assertEqual(cashier_payload["branches"][0]["id"], self.branch.id)
        self.client.logout()

        self.client.login(username=self.branch_manager.username, password="secret123")
        manager_payload = self.client.get("/pos/api/menu/").json()
        self.assertTrue(manager_payload["branch_locked"])
        self.assertEqual(len(manager_payload["branches"]), 1)
        self.assertEqual(manager_payload["branches"][0]["id"], self.branch.id)
        self.client.logout()

        self.client.login(username=self.owner.username, password="secret123")
        owner_payload = self.client.get("/pos/api/menu/").json()
        self.assertFalse(owner_payload["branch_locked"])
        owner_branch_ids = {row["id"] for row in owner_payload["branches"]}
        self.assertEqual(owner_branch_ids, {self.branch.id, self.branch_two.id})

    def test_kitchen_cannot_open_pos_or_create_order(self):
        self.client.login(username=self.kitchen.username, password="secret123")
        pos_response = self.client.get("/pos/")
        self.assertEqual(pos_response.status_code, 403)

        payload = {
            "client_order_uuid": "22222222-2222-4222-8222-222222222222",
            "items": [{"product_id": self.product.id, "quantity": 1}],
            "payments": [{"method": "cash", "amount": "120.00"}],
            "source": "online",
        }
        create_response = self.client.post(
            "/orders/api/create/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 403)

    def test_kitchen_screen_and_status_transitions(self):
        order = OrderService.create_order(
            tenant=self.tenant,
            branch=self.branch,
            user=self.owner,
            payload={
                "client_order_uuid": "33333333-3333-4333-8333-333333333333",
                "items": [{"product_id": self.product.id, "quantity": 1}],
                "payments": [{"method": "cash", "amount": "120.00"}],
            },
            source="online",
        )

        self.client.login(username=self.kitchen.username, password="secret123")
        board_response = self.client.get("/orders/kitchen/")
        self.assertEqual(board_response.status_code, 200)

        preparing_response = self.client.post(
            f"/orders/kitchen/{order.id}/status/",
            data={"kitchen_status": "preparing"},
        )
        self.assertEqual(preparing_response.status_code, 200)

        ready_response = self.client.post(
            f"/orders/kitchen/{order.id}/status/",
            data={"kitchen_status": "ready"},
        )
        self.assertEqual(ready_response.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.kitchen_status, "ready")

    def test_owner_without_primary_branch_can_operate_pos_with_fallback_branch(self):
        self.client.login(username=self.owner_no_branch.username, password="secret123")

        menu_response = self.client.get("/pos/api/menu/")
        self.assertEqual(menu_response.status_code, 200)
        menu_payload = menu_response.json()
        self.assertEqual(menu_payload["active_branch_id"], self.branch.id)
        self.assertTrue(len(menu_payload["products"]) >= 1)

        payload = {
            "client_order_uuid": "44444444-4444-4444-8444-444444444444",
            "items": [{"product_id": self.product.id, "quantity": 1}],
            "payments": [{"method": "cash", "amount": "120.00"}],
            "source": "online",
        }
        create_response = self.client.post(
            "/orders/api/create/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 200)

    def test_branch_manager_cannot_create_order_for_other_branch(self):
        self.client.login(username=self.branch_manager.username, password="secret123")
        payload = {
            "client_order_uuid": "66666666-6666-4666-8666-666666666666",
            "branch_id": self.branch_two.id,
            "items": [{"product_id": self.product_two.id, "quantity": 1}],
            "payments": [{"method": "cash", "amount": "95.00"}],
            "source": "online",
        }
        create_response = self.client.post(
            "/orders/api/create/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 403)

    def test_delivery_order_creates_or_links_customer(self):
        self.client.login(username=self.cashier.username, password="secret123")
        payload = {
            "client_order_uuid": "77777777-7777-4777-8777-777777777777",
            "order_type": "delivery",
            "customer": {
                "name": "Ali",
                "phone": "01000000000",
                "address": "Nasr City",
            },
            "items": [{"product_id": self.product.id, "quantity": 1}],
            "payments": [{"method": "cash", "amount": "120.00"}],
            "source": "online",
        }
        create_response = self.client.post(
            "/orders/api/create/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 200)
        order_id = create_response.json()["id"]
        from orders.models import Order

        order = Order.objects.get(id=order_id)
        self.assertEqual(order.order_type, "delivery")
        self.assertEqual(order.customer_phone_snapshot, "01000000000")
        self.assertEqual(order.customer_name_snapshot, "Ali")
        self.assertTrue(Customer.objects.filter(tenant=self.tenant, phone="01000000000").exists())

    def test_pos_customer_lookup_by_phone(self):
        Customer.objects.create(
            tenant=self.tenant,
            branch=self.branch,
            name="Delivery Client",
            phone="01111111111",
            notes="Dokki",
            is_active=True,
        )
        self.client.login(username=self.cashier.username, password="secret123")
        response = self.client.get("/pos/api/customers/?phone=0111")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["results"]), 1)
