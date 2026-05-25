from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.conf import settings
from django.utils import timezone

from audit.services import AuditService
from audit.models import AuditLog
from backup.models import BackupRecord
from core.constants import (
    FEATURE_ACCOUNTING_MODULE,
    FEATURE_ADVANCED_DASHBOARD,
    FEATURE_ADVANCED_INVENTORY,
    FEATURE_BRANCH_COMPARISON,
    FEATURE_BRANCHES_LIMIT,
    FEATURE_EXPORT_REPORTS,
    FEATURE_HR_MODULE,
    FEATURE_KDS_SCREEN,
    FEATURE_RECIPES,
    PLAN_PRO,
)
from crm.models import Customer
from featureflags.services import FeatureService
from hr.models import Employee, PayrollRecord
from inventory.models import Ingredient, LowStockAlert, Recipe, StockEntry, Supplier
from inventory.services import StockService
from menu.models import Category, ModifierGroup, ModifierOption, Product, ProductModifier
from orders.models import Order, PaymentReview
from orders.services import OrderService
from printing.models import BranchPrinterConfig, PrintJob, PrintTemplate, Printer
from printing.services import PrintService
from reports.models import ReportSnapshot
from reports.services import ReportService
from restaurants.models import Branch, RestaurantSetting
from subscriptions.models import Subscription, SubscriptionPlan
from tenants.models import Tenant, TenantDomain
from users.models import TenantMembership


class Command(BaseCommand):
    help = "Seed a complete Pro demo tenant with realistic data and ready-to-use credentials"

    PRODUCT_TEMPLATES = [
        ("Burgers", "Classic Burger", Decimal("145.00"), {"Burger Bun": Decimal("1.0"), "Beef Patty": Decimal("1.0"), "Cheese Slice": Decimal("1.0"), "Lettuce": Decimal("0.04")}),
        ("Burgers", "Mushroom Burger", Decimal("165.00"), {"Burger Bun": Decimal("1.0"), "Beef Patty": Decimal("1.0"), "Mushroom Mix": Decimal("0.06"), "Cheese Slice": Decimal("1.0")}),
        ("Pizza", "Margherita Pizza", Decimal("220.00"), {"Pizza Dough": Decimal("1.0"), "Tomato Sauce": Decimal("0.12"), "Mozzarella": Decimal("0.18")}),
        ("Pizza", "Chicken Pizza", Decimal("245.00"), {"Pizza Dough": Decimal("1.0"), "Tomato Sauce": Decimal("0.12"), "Mozzarella": Decimal("0.17"), "Chicken Cubes": Decimal("0.16")}),
        ("Pasta", "Pasta Alfredo", Decimal("175.00"), {"Pasta": Decimal("0.22"), "Cream": Decimal("0.14"), "Chicken Cubes": Decimal("0.09")}),
        ("Drinks", "Cola", Decimal("40.00"), {"Soft Drink Syrup": Decimal("0.02")}),
    ]

    INGREDIENT_TEMPLATES = [
        ("Burger Bun", "piece", Decimal("40.000"), Decimal("400.000")),
        ("Beef Patty", "piece", Decimal("40.000"), Decimal("350.000")),
        ("Cheese Slice", "piece", Decimal("60.000"), Decimal("500.000")),
        ("Lettuce", "kg", Decimal("8.000"), Decimal("65.000")),
        ("Mushroom Mix", "kg", Decimal("8.000"), Decimal("70.000")),
        ("Pizza Dough", "piece", Decimal("30.000"), Decimal("300.000")),
        ("Tomato Sauce", "kg", Decimal("10.000"), Decimal("85.000")),
        ("Mozzarella", "kg", Decimal("12.000"), Decimal("95.000")),
        ("Chicken Cubes", "kg", Decimal("12.000"), Decimal("90.000")),
        ("Pasta", "kg", Decimal("12.000"), Decimal("120.000")),
        ("Cream", "liter", Decimal("10.000"), Decimal("95.000")),
        ("Soft Drink Syrup", "liter", Decimal("8.000"), Decimal("70.000")),
    ]

    FEATURE_EXPECTED = {
        FEATURE_BRANCHES_LIMIT: -1,
        FEATURE_ADVANCED_INVENTORY: True,
        FEATURE_RECIPES: True,
        FEATURE_BRANCH_COMPARISON: True,
        FEATURE_HR_MODULE: True,
        FEATURE_ACCOUNTING_MODULE: True,
        FEATURE_EXPORT_REPORTS: True,
        FEATURE_ADVANCED_DASHBOARD: True,
        FEATURE_KDS_SCREEN: True,
    }

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--tenant-slug", default="demo-pro")
        parser.add_argument("--tenant-name", default="Restoraq Demo Restaurant")
        parser.add_argument("--domain", default="127.0.0.1")
        parser.add_argument("--system-username", default="system_owner_demo")
        parser.add_argument("--system-password", default="SystemOwner@123")
        parser.add_argument("--user-password", default="DemoUser@123")
        parser.add_argument("--orders-per-branch", type=int, default=6)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--reseed-orders", action="store_true")
        parser.add_argument("--skip-localhost-mapping", action="store_true")
        parser.add_argument("--export-file", default="helping-data/demo_credentials.txt")

    def handle(self, *args, **options):
        tenant_slug = options["tenant_slug"].strip().lower()
        tenant_name = options["tenant_name"].strip()
        domain = options["domain"].strip().lower()
        system_username = options["system_username"].strip()
        system_password = options["system_password"]
        user_password = options["user_password"]
        orders_per_branch = max(1, int(options["orders_per_branch"]))
        reset = bool(options["reset"])
        reseed_orders = bool(options["reseed_orders"])
        skip_localhost_mapping = bool(options["skip_localhost_mapping"])
        export_file = Path(options["export_file"])

        self.stdout.write(self.style.NOTICE("Preparing prerequisites..."))
        for cmd in ("seed_roles", "seed_plans", "seed_features"):
            call_command(cmd, verbosity=0)

        if reset:
            self._reset_demo(tenant_slug=tenant_slug, system_username=system_username)

        with transaction.atomic():
            tenant = self._ensure_tenant(tenant_slug=tenant_slug, tenant_name=tenant_name)
            plan = SubscriptionPlan.objects.get(code=PLAN_PRO)
            self._ensure_subscription(tenant=tenant, plan=plan)
            mapped_domains = self._ensure_domains(
                tenant=tenant,
                preferred_domain=domain,
                include_localhost=(not skip_localhost_mapping),
            )
            branches = self._ensure_branches(tenant=tenant)
            RestaurantSetting.objects.update_or_create(
                tenant=tenant,
                defaults={"currency": "EGP", "receipt_footer": "Thank you for visiting Restoraq demo."},
            )

            system_owner = self._ensure_system_owner(username=system_username, password=system_password)
            tenant_users = self._ensure_tenant_users(tenant=tenant, branches=branches, password=user_password)

            products_by_branch = self._seed_menu(tenant=tenant, branches=branches)
            ingredients_by_branch = self._seed_inventory(
                tenant=tenant,
                branches=branches,
                inventory_user=tenant_users["inventory_main"],
                reset_levels=reseed_orders,
            )
            self._seed_recipes(
                tenant=tenant,
                branches=branches,
                products_by_branch=products_by_branch,
                ingredients_by_branch=ingredients_by_branch,
            )
            self._seed_customers(tenant=tenant, branches=branches)
            self._seed_hr(tenant=tenant, branches=branches)
            self._seed_printing(tenant=tenant, branches=branches)
            created_orders = self._seed_orders(
                tenant=tenant,
                branches=branches,
                products_by_branch=products_by_branch,
                tenant_users=tenant_users,
                orders_per_branch=orders_per_branch,
                reseed_orders=reseed_orders,
            )
            self._seed_reports(tenant=tenant, branches=branches)
            self._seed_backups(tenant=tenant)
            self._seed_audit_examples(tenant=tenant, branch=branches["MAIN"], system_owner=system_owner)

        warnings = self._validate_features(tenant=tenant)
        lines = self._build_summary(
            tenant=tenant,
            mapped_domains=mapped_domains,
            system_username=system_username,
            system_password=system_password,
            user_password=user_password,
            new_orders_count=created_orders,
        )
        export_file.parent.mkdir(parents=True, exist_ok=True)
        export_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        for line in lines:
            self.stdout.write(line)
        if warnings:
            self.stdout.write(self.style.WARNING("Feature mismatches:"))
            for row in warnings:
                self.stdout.write(self.style.WARNING(f"- {row}"))
        else:
            self.stdout.write(self.style.SUCCESS("Feature matrix verified for Pro."))
        self.stdout.write(self.style.SUCCESS("Demo tenant is ready."))

    @staticmethod
    def _reset_demo(*, tenant_slug: str, system_username: str) -> None:
        user_model = get_user_model()
        tenant = Tenant.objects.filter(slug=tenant_slug).first()
        if tenant:
            PaymentReview.objects.filter(tenant=tenant).delete()
            PrintJob.objects.filter(tenant=tenant).delete()
            Order.objects.filter(tenant=tenant).delete()

            Recipe.objects.filter(tenant=tenant).delete()
            StockEntry.objects.filter(tenant=tenant).delete()
            LowStockAlert.objects.filter(tenant=tenant).delete()
            Ingredient.objects.filter(tenant=tenant).delete()
            Supplier.objects.filter(tenant=tenant).delete()

            ProductModifier.objects.filter(tenant=tenant).delete()
            ModifierOption.objects.filter(tenant=tenant).delete()
            ModifierGroup.objects.filter(tenant=tenant).delete()
            Product.objects.filter(tenant=tenant).delete()
            Category.objects.filter(tenant=tenant).delete()

            PayrollRecord.objects.filter(tenant=tenant).delete()
            Employee.objects.filter(tenant=tenant).delete()
            Customer.objects.filter(tenant=tenant).delete()
            ReportSnapshot.objects.filter(tenant=tenant).delete()
            AuditLog.objects.filter(tenant=tenant).delete()

            BranchPrinterConfig.objects.filter(tenant=tenant).delete()
            Printer.objects.filter(tenant=tenant).delete()
            PrintTemplate.objects.filter(tenant=tenant).delete()

            TenantMembership.objects.filter(tenant=tenant).delete()
            RestaurantSetting.objects.filter(tenant=tenant).delete()
            Branch.objects.filter(tenant=tenant).delete()
            Subscription.objects.filter(tenant=tenant).delete()
            TenantDomain.objects.filter(tenant=tenant).delete()

        user_model.objects.filter(username__startswith=f"{tenant_slug}_").delete()
        user_model.objects.filter(username=system_username).delete()

    @staticmethod
    def _ensure_tenant(*, tenant_slug: str, tenant_name: str) -> Tenant:
        tenant, _ = Tenant.objects.update_or_create(
            slug=tenant_slug,
            defaults={
                "name": tenant_name,
                "is_active": True,
                "default_language": "ar",
                "vat_rate": Decimal("14.00"),
                "tax_inclusive_pricing": True,
            },
        )
        return tenant

    @staticmethod
    def _ensure_subscription(*, tenant: Tenant, plan: SubscriptionPlan) -> None:
        today = timezone.localdate()
        Subscription.objects.update_or_create(
            tenant=tenant,
            defaults={
                "plan": plan,
                "start_date": today - timedelta(days=10),
                "end_date": today + timedelta(days=365),
                "grace_period_end": today + timedelta(days=370),
                "is_active": True,
                "status": Subscription.STATUS_ACTIVE,
            },
        )

    def _ensure_domains(self, *, tenant: Tenant, preferred_domain: str, include_localhost: bool) -> list[str]:
        hosts: list[str] = []
        if preferred_domain:
            hosts.append(preferred_domain)
        if include_localhost:
            hosts.extend(["127.0.0.1", "localhost"])

        TenantDomain.objects.filter(tenant=tenant).update(is_primary=False)
        mapped: list[str] = []
        for host in dict.fromkeys(hosts):
            existing = TenantDomain.objects.filter(domain=host).first()
            if existing and existing.tenant_id != tenant.id:
                self.stdout.write(
                    self.style.WARNING(
                        f"Domain '{host}' belongs to tenant '{existing.tenant.slug}', skipped."
                    )
                )
                continue
            TenantDomain.objects.update_or_create(
                domain=host,
                defaults={"tenant": tenant, "is_primary": len(mapped) == 0, "is_active": True},
            )
            mapped.append(host)

        if not mapped:
            fallback = f"{tenant.slug}.local"
            TenantDomain.objects.update_or_create(
                domain=fallback,
                defaults={"tenant": tenant, "is_primary": True, "is_active": True},
            )
            mapped.append(fallback)
        return mapped

    @staticmethod
    def _ensure_branches(*, tenant: Tenant) -> dict[str, Branch]:
        rows = [
            ("MAIN", "Main Branch", "Nasr City, Cairo", "+20-100-000-0001"),
            ("NORTH", "North Branch", "6th of October, Giza", "+20-100-000-0002"),
            ("SEA", "Seaside Branch", "Stanley, Alexandria", "+20-100-000-0003"),
        ]
        branches: dict[str, Branch] = {}
        for code, name, address, phone in rows:
            branch, _ = Branch.objects.update_or_create(
                tenant=tenant,
                code=code,
                defaults={"name": name, "address": address, "phone": phone, "is_active": True},
            )
            branches[code] = branch
        return branches

    @staticmethod
    def _ensure_system_owner(*, username: str, password: str):
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": "system.owner@restoraq.local",
                "is_staff": True,
                "is_superuser": True,
                "is_system_owner": True,
                "preferred_language": "ar",
            },
        )
        user.email = "system.owner@restoraq.local"
        user.is_staff = True
        user.is_superuser = True
        user.is_system_owner = True
        user.preferred_language = "ar"
        user.set_password(password)
        user.save()
        group, _ = Group.objects.get_or_create(name="SystemOwner")
        user.groups.add(group)
        return user

    @staticmethod
    def _tenant_specs() -> list[tuple[str, str, str, str]]:
        return [
            ("owner", "RestaurantOwner", "MAIN", "owner@demo.local"),
            ("branch_manager_main", "BranchManager", "MAIN", "manager.main@demo.local"),
            ("branch_manager_north", "BranchManager", "NORTH", "manager.north@demo.local"),
            ("accountant", "Accountant", "MAIN", "accounting@demo.local"),
            ("inventory_main", "InventoryManager", "MAIN", "inventory.main@demo.local"),
            ("cashier_main", "Cashier", "MAIN", "cashier.main@demo.local"),
            ("cashier_north", "Cashier", "NORTH", "cashier.north@demo.local"),
            ("cashier_sea", "Cashier", "SEA", "cashier.sea@demo.local"),
            ("kitchen_main", "KitchenStaff", "MAIN", "kitchen.main@demo.local"),
            ("kitchen_north", "KitchenStaff", "NORTH", "kitchen.north@demo.local"),
        ]

    def _ensure_tenant_users(self, *, tenant: Tenant, branches: dict[str, Branch], password: str) -> dict[str, object]:
        user_model = get_user_model()
        users: dict[str, object] = {}
        for suffix, role, branch_code, email in self._tenant_specs():
            username = f"{tenant.slug}_{suffix}"
            user, _ = user_model.objects.get_or_create(
                username=username,
                defaults={"email": email, "preferred_language": "ar"},
            )
            user.email = email
            user.preferred_language = "ar"
            user.is_staff = False
            user.is_superuser = False
            user.is_system_owner = False
            user.set_password(password)
            user.save()

            user.groups.set([Group.objects.get(name=role)])
            TenantMembership.objects.update_or_create(
                tenant=tenant,
                user=user,
                defaults={"role_name": role, "primary_branch": branches[branch_code], "is_active": True},
            )
            users[suffix] = user
        return users

    def _seed_menu(self, *, tenant: Tenant, branches: dict[str, Branch]) -> dict[str, list[Product]]:
        products_by_branch: dict[str, list[Product]] = {}
        for branch_code, branch in branches.items():
            categories: dict[str, Category] = {}
            for order, name in enumerate(("Burgers", "Pizza", "Pasta", "Drinks"), start=1):
                category, _ = Category.objects.update_or_create(
                    tenant=tenant,
                    branch=branch,
                    name=name,
                    defaults={"display_order": order, "is_active": True},
                )
                categories[name] = category

            branch_products: list[Product] = []
            for idx, (category_name, product_name, price, _recipe) in enumerate(self.PRODUCT_TEMPLATES, start=1):
                product, _ = Product.objects.update_or_create(
                    tenant=tenant,
                    sku=f"{branch_code}-P{idx:03d}",
                    defaults={
                        "branch": branch,
                        "category": categories[category_name],
                        "name": product_name,
                        "price": price,
                        "tax_rate": tenant.vat_rate,
                        "is_tax_inclusive": tenant.tax_inclusive_pricing,
                        "is_active": True,
                    },
                )
                branch_products.append(product)

            group, _ = ModifierGroup.objects.update_or_create(
                tenant=tenant,
                branch=branch,
                name="Size",
                defaults={"is_required": False, "max_select": 1},
            )
            for option_name, delta in (("Regular", Decimal("0.00")), ("Double", Decimal("35.00")), ("Combo", Decimal("55.00"))):
                ModifierOption.objects.update_or_create(
                    tenant=tenant,
                    branch=branch,
                    group=group,
                    name=option_name,
                    defaults={"price_delta": delta, "is_active": True},
                )
            for product in branch_products[:2]:
                ProductModifier.objects.update_or_create(
                    tenant=tenant,
                    branch=branch,
                    product=product,
                    modifier_group=group,
                )

            products_by_branch[branch_code] = branch_products
        return products_by_branch

    def _seed_inventory(
        self,
        *,
        tenant: Tenant,
        branches: dict[str, Branch],
        inventory_user,
        reset_levels: bool,
    ) -> dict[str, dict[str, Ingredient]]:
        ingredients_by_branch: dict[str, dict[str, Ingredient]] = {}

        for branch_code, branch in branches.items():
            Supplier.objects.update_or_create(
                tenant=tenant,
                branch=branch,
                name=f"{branch.name} Primary Supplier",
                defaults={
                    "phone": "+20-100-200-3000",
                    "email": f"supplier.{branch_code.lower()}@demo.local",
                    "address": branch.address,
                    "is_active": True,
                },
            )

            rows: dict[str, Ingredient] = {}
            for name, unit, reorder, initial in self.INGREDIENT_TEMPLATES:
                ingredient, _ = Ingredient.objects.update_or_create(
                    tenant=tenant,
                    branch=branch,
                    name=name,
                    defaults={"unit": unit, "reorder_level": reorder, "is_active": True},
                )
                rows[name] = ingredient

                has_initial = StockEntry.objects.filter(
                    tenant=tenant,
                    branch=branch,
                    ingredient=ingredient,
                    reference="DEMO-INITIAL",
                ).exists()
                if not has_initial:
                    StockService.record_entry(
                        tenant=tenant,
                        branch=branch,
                        ingredient=ingredient,
                        movement_type=StockEntry.MOVEMENT_IN,
                        quantity=initial,
                        actor=inventory_user,
                        note="Initial stock for demo",
                        reference="DEMO-INITIAL",
                    )
                elif reset_levels:
                    StockService.record_entry(
                        tenant=tenant,
                        branch=branch,
                        ingredient=ingredient,
                        movement_type=StockEntry.MOVEMENT_ADJUSTMENT,
                        quantity=initial,
                        actor=inventory_user,
                        note="Stock reset for order reseed",
                        reference="DEMO-RESET",
                    )

            ingredients_by_branch[branch_code] = rows

        return ingredients_by_branch

    def _seed_recipes(
        self,
        *,
        tenant: Tenant,
        branches: dict[str, Branch],
        products_by_branch: dict[str, list[Product]],
        ingredients_by_branch: dict[str, dict[str, Ingredient]],
    ) -> None:
        recipe_map = {name: recipe for _cat, name, _price, recipe in self.PRODUCT_TEMPLATES}
        for branch_code, products in products_by_branch.items():
            branch = branches[branch_code]
            ingredient_map = ingredients_by_branch[branch_code]
            for product in products:
                for ingredient_name, qty in recipe_map.get(product.name, {}).items():
                    Recipe.objects.update_or_create(
                        tenant=tenant,
                        branch=branch,
                        product=product,
                        ingredient=ingredient_map[ingredient_name],
                        defaults={"quantity_per_unit": qty},
                    )

    @staticmethod
    def _seed_customers(*, tenant: Tenant, branches: dict[str, Branch]) -> None:
        names = [
            "Ahmed Samir", "Mina Nabil", "Sara Adel", "Nour Hassan", "Youssef Kamal", "Mariam Fathy",
            "Aly Farouk", "Hoda Magdy", "Karim Saeed", "Hana Mostafa", "Tarek Hamdy", "Rana Mohsen",
        ]
        branch_list = list(branches.values())
        for idx, name in enumerate(names, start=1):
            Customer.objects.update_or_create(
                tenant=tenant,
                phone=f"010{tenant.id:03d}{idx:05d}",
                defaults={
                    "branch": branch_list[idx % len(branch_list)],
                    "name": name,
                    "email": f"customer{idx}@demo.local",
                    "notes": "Demo customer profile",
                    "loyalty_points": idx * 5,
                    "is_active": True,
                },
            )

    @staticmethod
    def _seed_hr(*, tenant: Tenant, branches: dict[str, Branch]) -> None:
        today = timezone.localdate()
        period_start = today.replace(day=1)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        employees = [
            ("MAIN", "Mohamed Ali", "Branch Manager", Decimal("14000.00")),
            ("MAIN", "Ramy Emad", "Cashier", Decimal("7000.00")),
            ("NORTH", "Salma Tarek", "Kitchen Lead", Decimal("9000.00")),
            ("SEA", "Mahmoud Saad", "Branch Supervisor", Decimal("11000.00")),
        ]
        for branch_code, full_name, position, salary in employees:
            branch = branches[branch_code]
            employee, _ = Employee.objects.update_or_create(
                tenant=tenant,
                branch=branch,
                full_name=full_name,
                defaults={
                    "phone": "+20-100-900-0000",
                    "email": f"{full_name.lower().replace(' ', '.')}@demo.local",
                    "position": position,
                    "salary": salary,
                    "hired_on": today - timedelta(days=180),
                    "is_active": True,
                },
            )
            allowances = Decimal("450.00")
            bonuses = Decimal("300.00")
            deductions = Decimal("200.00")
            PayrollRecord.objects.update_or_create(
                tenant=tenant,
                branch=branch,
                employee=employee,
                period_start=period_start,
                period_end=period_end,
                defaults={
                    "basic_salary": salary,
                    "allowances": allowances,
                    "bonuses": bonuses,
                    "deductions": deductions,
                    "net_amount": salary + allowances + bonuses - deductions,
                    "status": PayrollRecord.STATUS_PAID,
                },
            )

    @staticmethod
    def _seed_printing(*, tenant: Tenant, branches: dict[str, Branch]) -> None:
        PrintTemplate.objects.update_or_create(
            tenant=tenant,
            code=PrintTemplate.TYPE_CUSTOMER,
            defaults={"title": "Customer Receipt", "content": "{{ order_number }}\\n{{ items }}\\nTotal: {{ total }}"},
        )
        PrintTemplate.objects.update_or_create(
            tenant=tenant,
            code=PrintTemplate.TYPE_KITCHEN,
            defaults={"title": "Kitchen Ticket", "content": "{{ order_number }}\\n{{ items }}"},
        )
        for branch in branches.values():
            customer_printer, _ = Printer.objects.update_or_create(
                tenant=tenant,
                branch=branch,
                name=f"{branch.code} Customer Printer",
                defaults={"connection_type": Printer.CONNECTION_USB, "device_identifier": f"USB:{branch.code}:CUSTOMER", "is_active": True},
            )
            kitchen_printer, _ = Printer.objects.update_or_create(
                tenant=tenant,
                branch=branch,
                name=f"{branch.code} Kitchen Printer",
                defaults={"connection_type": Printer.CONNECTION_USB, "device_identifier": f"USB:{branch.code}:KITCHEN", "is_active": True},
            )
            BranchPrinterConfig.objects.update_or_create(
                tenant=tenant,
                branch=branch,
                defaults={"customer_printer": customer_printer, "kitchen_printer": kitchen_printer, "auto_print": True},
            )

    def _seed_orders(
        self,
        *,
        tenant: Tenant,
        branches: dict[str, Branch],
        products_by_branch: dict[str, list[Product]],
        tenant_users: dict[str, object],
        orders_per_branch: int,
        reseed_orders: bool,
    ) -> int:
        existing = Order.objects.filter(tenant=tenant).count()
        if existing and not reseed_orders:
            return 0
        if existing and reseed_orders:
            Order.objects.filter(tenant=tenant).delete()

        cashier_by_branch = {
            "MAIN": tenant_users["cashier_main"],
            "NORTH": tenant_users["cashier_north"],
            "SEA": tenant_users["cashier_sea"],
        }

        now = timezone.now()
        created = 0
        methods = ["cash", "card", "wallet"]
        for branch_code, branch in branches.items():
            products = products_by_branch[branch_code]
            cashier = cashier_by_branch[branch_code]
            for idx in range(orders_per_branch):
                item_a = products[idx % len(products)]
                item_b = products[(idx + 2) % len(products)]
                items = [
                    {"product_id": item_a.id, "quantity": 1 + (idx % 2)},
                    {"product_id": item_b.id, "quantity": 1},
                ]
                totals = OrderService.preview_order(tenant=tenant, branch=branch, items=items)
                payload = {
                    "items": items,
                    "notes": f"Demo order for {branch.code}",
                    "payments": [{"method": methods[idx % len(methods)], "amount": str(totals.total)}],
                }
                source = "online"
                if idx == orders_per_branch - 1:
                    source = "offline"
                    payload["client_order_uuid"] = str(uuid5(NAMESPACE_DNS, f"{tenant.slug}-{branch.code}-offline-{idx + 1}"))
                    payload["payments"] = [{"method": "card", "amount": str(totals.total), "reference": f"OFF-{branch.code}-{idx + 1:03d}"}]

                order = OrderService.create_order(
                    tenant=tenant,
                    branch=branch,
                    user=cashier,
                    payload=payload,
                    source=source,
                )
                Order.objects.filter(id=order.id).update(created_at=now - timedelta(days=idx % 10, hours=idx % 5))
                created += 1

        jobs = list(PrintJob.objects.filter(tenant=tenant).order_by("id")[:3])
        if jobs:
            PrintService.mark_sent(jobs[0])
            PrintService.acknowledge(jobs[0])
        if len(jobs) > 1:
            PrintService.mark_failed(jobs[1], "QZ Tray not connected during demo scenario")

        return created

    @staticmethod
    def _seed_reports(*, tenant: Tenant, branches: dict[str, Branch]) -> None:
        today = timezone.localdate()
        start = today - timedelta(days=30)
        branch_sales = {code: str(ReportService.monthly_sales(tenant=tenant, branch=branch)) for code, branch in branches.items()}
        best_least = ReportService.best_and_least_selling(tenant=tenant)
        best = best_least["best"] or (None, None)
        least = best_least["least"] or (None, None)

        payloads = {
            "daily_sales": {"daily_sales": str(ReportService.daily_sales(tenant=tenant))},
            "monthly_sales": {"monthly_sales": str(ReportService.monthly_sales(tenant=tenant))},
            "branch_comparison": {"branch_sales": branch_sales},
            "advanced_dashboard": {
                "daily_sales": str(ReportService.daily_sales(tenant=tenant)),
                "monthly_sales": str(ReportService.monthly_sales(tenant=tenant)),
                "best_selling": {"name": best[0], "quantity": best[1]},
                "least_selling": {"name": least[0], "quantity": least[1]},
            },
        }
        for key, payload in payloads.items():
            ReportSnapshot.objects.update_or_create(
                tenant=tenant,
                branch=branches["MAIN"],
                report_key=key,
                period_start=start,
                period_end=today,
                defaults={"payload_json": payload},
            )

    @staticmethod
    def _seed_backups(*, tenant: Tenant) -> None:
        now = timezone.now()
        stamp = now.strftime("%Y%m%d")
        BackupRecord.objects.update_or_create(
            file_path=f"demo/{tenant.slug}/{stamp}.sql.gz",
            defaults={
                "backup_type": BackupRecord.TYPE_MANUAL,
                "storage_backend": "local",
                "checksum": "demo-checksum-success",
                "file_size": 1024 * 1024,
                "status": BackupRecord.STATUS_SUCCESS,
                "started_at": now - timedelta(minutes=4),
                "completed_at": now - timedelta(minutes=2),
            },
        )
        BackupRecord.objects.update_or_create(
            file_path=f"demo/{tenant.slug}/{stamp}-failed.sql.gz",
            defaults={
                "backup_type": BackupRecord.TYPE_AUTO,
                "storage_backend": "s3",
                "checksum": "",
                "file_size": 0,
                "status": BackupRecord.STATUS_FAILED,
                "started_at": now - timedelta(minutes=1),
                "completed_at": now,
                "error_message": "Network timeout while uploading to S3",
            },
        )

    @staticmethod
    def _seed_audit_examples(*, tenant: Tenant, branch: Branch, system_owner) -> None:
        AuditService.log_action(tenant=tenant, branch=branch, user=system_owner, action="login", model="accounts.User", object_id=str(system_owner.id), metadata={"source": "demo_seed"})
        AuditService.log_action(tenant=tenant, branch=branch, user=None, action="failed_login", model="accounts.User", object_id="", metadata={"source": "demo_seed", "username": "unknown_demo"})
        AuditService.log_action(tenant=tenant, branch=branch, user=system_owner, action="role_changed", model="users.TenantMembership", object_id="demo", metadata={"source": "demo_seed"})
        AuditService.log_action(tenant=tenant, branch=branch, user=system_owner, action="price_changed", model="menu.Product", object_id="demo", metadata={"source": "demo_seed"})

    def _validate_features(self, *, tenant: Tenant) -> list[str]:
        warnings: list[str] = []
        for feature_name, expected in self.FEATURE_EXPECTED.items():
            actual = FeatureService.resolve(tenant, feature_name)
            if actual != expected:
                warnings.append(f"{feature_name}: expected {expected}, got {actual}")
        return warnings

    def _build_summary(
        self,
        *,
        tenant: Tenant,
        mapped_domains: list[str],
        system_username: str,
        system_password: str,
        user_password: str,
        new_orders_count: int,
    ) -> list[str]:
        branch_count = Branch.objects.filter(tenant=tenant).count()
        user_count = TenantMembership.objects.filter(tenant=tenant, is_active=True).count()
        product_count = Product.objects.filter(tenant=tenant, is_active=True).count()
        ingredient_count = Ingredient.objects.filter(tenant=tenant, is_active=True).count()
        customer_count = Customer.objects.filter(tenant=tenant, is_active=True).count()
        employee_count = Employee.objects.filter(tenant=tenant, is_active=True).count()
        order_count = Order.objects.filter(tenant=tenant).count()
        pending_reviews = PaymentReview.objects.filter(tenant=tenant, status=PaymentReview.STATUS_PENDING).count()
        print_jobs = PrintJob.objects.filter(tenant=tenant).count()

        lines = [
            "",
            "==================== DEMO READY ====================",
            f"Tenant: {tenant.name} ({tenant.slug})",
            f"Domains mapped: {', '.join(mapped_domains)}",
            "",
            "System owner credentials:",
            f"  username: {system_username}",
            f"  password: {system_password}",
            "",
            "Restaurant demo credentials (same password for all):",
            f"  password: {user_password}",
        ]
        for suffix, role, branch_code, _email in self._tenant_specs():
            lines.append(f"  - {tenant.slug}_{suffix:<20} role={role:<16} branch={branch_code}")

        lines.extend(
            [
                "",
                "Quick links:",
                "  - Website: http://127.0.0.1:8000/",
                "  - App dashboard: http://127.0.0.1:8000/dashboard/",
                "  - POS terminal: http://127.0.0.1:8000/pos/",
                f"  - System dashboard: http://127.0.0.1:8000/{getattr(settings, 'SYSTEM_PATH', 'system/').lstrip('/')}",
                f"  - Django admin: http://127.0.0.1:8000/{getattr(settings, 'ADMIN_PATH', 'admin/').lstrip('/')}",
                "",
                "Seeded data summary:",
                f"  branches: {branch_count}",
                f"  tenant users: {user_count}",
                f"  products: {product_count}",
                f"  ingredients: {ingredient_count}",
                f"  customers: {customer_count}",
                f"  employees: {employee_count}",
                f"  orders total: {order_count} (new this run: {new_orders_count})",
                f"  pending payment reviews: {pending_reviews}",
                f"  print jobs: {print_jobs}",
                "====================================================",
            ]
        )
        return lines
