from __future__ import annotations

import hashlib
import hmac
import json

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.test import Client

from menu.models import Product
from orders.models import Order, PaymentReview
from printing.models import PrintJob
from tenants.models import Tenant


class Command(BaseCommand):
    help = "Run smoke checks over the demo tenant UI and key APIs"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--tenant-slug", default="demo-pro")
        parser.add_argument("--tenant-user", default="demo-pro_cashier_main")
        parser.add_argument("--tenant-password", default="DemoUser@123")
        parser.add_argument("--system-user", default="system_owner_demo")
        parser.add_argument("--system-password", default="SystemOwner@123")
        parser.add_argument("--tenant-host", default="127.0.0.1")
        parser.add_argument("--skip-seed", action="store_true")

    def handle(self, *args, **options):
        tenant_slug = options["tenant_slug"].strip().lower()
        tenant_user = options["tenant_user"]
        tenant_password = options["tenant_password"]
        system_user = options["system_user"]
        system_password = options["system_password"]
        tenant_host = options["tenant_host"]
        skip_seed = bool(options["skip_seed"])

        if not skip_seed:
            self.stdout.write(self.style.NOTICE("Seeding/updating demo tenant before smoke test..."))
            call_command("seed_demo_pro", tenant_slug=tenant_slug, verbosity=0)

        tenant = Tenant.objects.filter(slug=tenant_slug).first()
        if not tenant:
            raise CommandError(f"Tenant '{tenant_slug}' not found.")

        failures: list[str] = []
        anon_client = Client()

        self._expect_status("Public home", anon_client.get("/"), 200, failures)
        self._expect_status("Public features", anon_client.get("/features/"), 200, failures)
        self._expect_status("Public pricing", anon_client.get("/pricing/"), 200, failures)
        self._expect_status("Health endpoint", anon_client.get("/health/"), 200, failures)
        self._expect_status("Login page", anon_client.get("/accounts/login/"), 200, failures)

        tenant_client = Client()
        logged_in_tenant = tenant_client.login(username=tenant_user, password=tenant_password)
        self._expect_bool("Tenant login", logged_in_tenant, failures, "Invalid tenant credentials")

        headers = self._tenant_headers(tenant_slug=tenant.slug, tenant_host=tenant_host)

        first_product_id: int | None = None
        if logged_in_tenant:
            self._expect_status("App dashboard", tenant_client.get("/dashboard/", **headers), 200, failures)
            self._expect_status("POS page", tenant_client.get("/pos/", **headers), 200, failures)
            self._expect_status("Orders page", tenant_client.get("/orders/", **headers), 200, failures)
            self._expect_status("Inventory page", tenant_client.get("/inventory/ingredients/", **headers), 200, failures)
            self._expect_status("Reports page", tenant_client.get("/reports/", **headers), 200, failures)

            menu_resp = tenant_client.get("/pos/api/menu/", **headers)
            self._expect_status("POS menu API", menu_resp, 200, failures)
            if menu_resp.status_code == 200:
                payload = menu_resp.json()
                self._expect_bool("Menu has products", bool(payload.get("products")), failures, "No products returned from menu API")
                if payload.get("products"):
                    first_product_id = int(payload["products"][0]["id"])

            if first_product_id:
                preview_resp = tenant_client.post(
                    "/pos/api/order/preview/",
                    data=json.dumps({"items": [{"product_id": first_product_id, "quantity": 1}]}),
                    content_type="application/json",
                    **headers,
                )
                self._expect_status("Order preview API", preview_resp, 200, failures)

            reviews_resp = tenant_client.get("/orders/api/payment-reviews/", **headers)
            self._expect_status("Payment review queue API", reviews_resp, 200, failures)
            if reviews_resp.status_code == 200:
                queue = reviews_resp.json().get("results", [])
                self._expect_bool("Payment review queue not empty", len(queue) > 0, failures, "Expected offline non-cash reviews")

            self._expect_status("QZ certificate API", tenant_client.get("/printing/qz/certificate/", **headers), 200, failures)
            self._expect_status("Sales chart API", tenant_client.get("/reports/api/sales-chart/", **headers), 200, failures)

        system_client = Client()
        logged_in_system = system_client.login(username=system_user, password=system_password)
        self._expect_bool("System login", logged_in_system, failures, "Invalid system credentials")
        if logged_in_system:
            system_path = f"/{getattr(settings, 'SYSTEM_PATH', 'system/').strip('/')}/"
            self._expect_status("System dashboard", system_client.get(system_path), 200, failures)
            self._expect_status("System tenants", system_client.get(system_path + "tenants/"), 200, failures)
            admin_path = f"/{getattr(settings, 'ADMIN_PATH', 'admin/').strip('/')}/"
            self._expect_status("Admin index", system_client.get(admin_path), 200, failures)

        self._expect_bool("Orders seeded", Order.objects.filter(tenant=tenant).exists(), failures, "No orders found")
        self._expect_bool("Products seeded", Product.objects.filter(tenant=tenant).exists(), failures, "No products found")
        self._expect_bool("Pending reviews exist", PaymentReview.objects.filter(tenant=tenant, status=PaymentReview.STATUS_PENDING).exists(), failures, "No pending payment reviews")
        self._expect_bool("Print jobs exist", PrintJob.objects.filter(tenant=tenant).exists(), failures, "No print jobs generated")

        if failures:
            joined = "\n".join(f"- {item}" for item in failures)
            raise CommandError(f"Smoke test failed with {len(failures)} issue(s):\n{joined}")

        self.stdout.write(self.style.SUCCESS("All smoke checks passed."))

    def _tenant_headers(self, *, tenant_slug: str, tenant_host: str) -> dict[str, str]:
        header_name = settings.TENANT_HEADER_NAME
        signature = hmac.new(
            key=settings.TENANT_HEADER_SIGNATURE_SECRET.encode("utf-8"),
            msg=tenant_slug.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return {
            header_name: tenant_slug,
            "HTTP_X_TENANT_SIGNATURE": signature,
            "HTTP_HOST": tenant_host,
        }

    def _expect_status(self, label: str, response, expected: int, failures: list[str]) -> None:
        if response.status_code == expected:
            self.stdout.write(self.style.SUCCESS(f"[PASS] {label}: {response.status_code}"))
            return
        message = f"{label} expected {expected}, got {response.status_code}"
        failures.append(message)
        self.stdout.write(self.style.ERROR(f"[FAIL] {message}"))

    def _expect_bool(self, label: str, ok: bool, failures: list[str], fail_message: str) -> None:
        if ok:
            self.stdout.write(self.style.SUCCESS(f"[PASS] {label}"))
            return
        failures.append(fail_message)
        self.stdout.write(self.style.ERROR(f"[FAIL] {label}: {fail_message}"))
