from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db.models import Q

from core.constants import ALL_GROUP_ROLES


class Command(BaseCommand):
    help = "Create default role groups and assign model permissions"

    def handle(self, *args, **options):
        permissions = Permission.objects.exclude(codename__startswith="view_logentry")
        read_write_permissions = permissions.filter(
            Q(codename__startswith="view_")
            | Q(codename__startswith="add_")
            | Q(codename__startswith="change_")
        )

        for role in ALL_GROUP_ROLES:
            group, created = Group.objects.get_or_create(name=role)
            if role in {"SystemOwner", "SystemAdmin"}:
                group.permissions.set(permissions)
            elif role in {"RestaurantOwner", "BranchManager"}:
                group.permissions.set(read_write_permissions)
            elif role == "Cashier":
                group.permissions.set(permissions.filter(content_type__app_label__in=["orders", "menu", "pos"]))
            elif role == "KitchenStaff":
                group.permissions.set(permissions.filter(content_type__app_label__in=["orders", "menu"]))
            elif role == "InventoryManager":
                group.permissions.set(permissions.filter(content_type__app_label__in=["inventory", "menu"]))
            elif role == "Accountant":
                group.permissions.set(permissions.filter(content_type__app_label__in=["orders", "reports", "subscriptions"]))
            elif role == "ContentManager":
                group.permissions.set(permissions.filter(content_type__app_label__in=["core", "tenants"]))
            self.stdout.write(self.style.SUCCESS(f"Role ready: {role} (created={created})"))
