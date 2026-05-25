from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from core.policies import AccessPolicy
from featureflags.services import FeatureService


@dataclass(frozen=True)
class WorkspaceNavItem:
    key: str
    label_ar: str
    label_en: str
    url_name: str
    starts_with: tuple[str, ...]
    icon: str
    section: str
    roles: set[str] | None = None
    enabled: bool = True

    def label(self, language: str) -> str:
        return self.label_ar if language.startswith("ar") else self.label_en


def build_workspace_nav(request, language: str) -> list[dict[str, str | bool]]:
    tenant = getattr(request, "tenant", None)
    has_tenant = tenant is not None
    kds_enabled = FeatureService.is_enabled(tenant, "kds_screen") if tenant else False
    accounting_enabled = FeatureService.is_enabled(tenant, "accounting_module") if tenant else False
    is_system_user = AccessPolicy.is_system_user(getattr(request, "user", None))

    system_prefix = f"/{str(getattr(settings, 'SYSTEM_PATH', 'system/')).strip('/')}/"

    raw_items = [
        WorkspaceNavItem(
            "dashboard",
            "لوحة التشغيل",
            "Dashboard",
            "core:dashboard",
            ("/dashboard/",),
            "fa-chart-line",
            "ops",
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "cashier",
            "الكاشير",
            "Cashier",
            "pos:terminal",
            ("/pos/",),
            "fa-cash-register",
            "ops",
            roles={"RestaurantOwner", "BranchManager", "Cashier"},
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "orders",
            "سجل الطلبات",
            "Order Log",
            "orders:list",
            ("/orders/",),
            "fa-receipt",
            "ops",
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "kitchen",
            "شاشة المطبخ",
            "Kitchen Screen",
            "orders:kitchen-board",
            ("/orders/kitchen/",),
            "fa-utensils",
            "ops",
            roles={"RestaurantOwner", "BranchManager", "KitchenStaff"},
            enabled=has_tenant and kds_enabled,
        ),
        WorkspaceNavItem(
            "customers",
            "العملاء",
            "Customers",
            "crm:customers",
            ("/crm/",),
            "fa-users",
            "customers",
            roles={"RestaurantOwner", "BranchManager", "Cashier"},
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "menu",
            "المنيو",
            "Menu",
            "menu:products",
            ("/menu/",),
            "fa-book-open",
            "resources",
            roles={"RestaurantOwner", "BranchManager", "InventoryManager"},
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "operations",
            "موارد التشغيل",
            "Operations Resources",
            "core:operations-resources",
            ("/operations/", "/inventory/", "/hr/"),
            "fa-industry",
            "resources",
            roles={"RestaurantOwner", "BranchManager", "InventoryManager", "Accountant"},
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "reports",
            "التقارير",
            "Reports",
            "reports:dashboard",
            ("/reports/",),
            "fa-chart-pie",
            "insights",
            roles={"RestaurantOwner", "BranchManager", "Accountant"},
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "accounting",
            "الحسابات",
            "Accounting",
            "reports:accounting",
            ("/reports/accounting/",),
            "fa-file-invoice-dollar",
            "insights",
            roles={"RestaurantOwner", "BranchManager", "Accountant"},
            enabled=has_tenant and accounting_enabled,
        ),
        WorkspaceNavItem(
            "branches",
            "الفروع",
            "Branches",
            "restaurants:branches",
            ("/restaurants/",),
            "fa-code-branch",
            "management",
            roles={"RestaurantOwner"},
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "tables",
            "الطاولات والحجوزات",
            "Tables & Reservations",
            "restaurants:tables",
            ("/restaurants/tables/", "/restaurants/areas/", "/restaurants/reservations/"),
            "fa-chair",
            "management",
            roles={"RestaurantOwner", "BranchManager"},
            enabled=has_tenant,
        ),
        WorkspaceNavItem(
            "system",
            "لوحة مدير النظام",
            "System Admin",
            "system:dashboard",
            (system_prefix,),
            "fa-shield-halved",
            "system",
            enabled=is_system_user,
        ),
    ]

    section_labels = {
        "ops": ("التشغيل", "Operations"),
        "customers": ("العملاء", "Customers"),
        "resources": ("الموارد", "Resources"),
        "insights": ("التحليلات", "Insights"),
        "management": ("الإدارة", "Management"),
        "system": ("النظام", "System"),
    }
    section_order = ["ops", "customers", "resources", "insights", "management", "system"]

    path = request.path or ""
    accounting_path = path.startswith("/reports/accounting/")
    sections: dict[str, dict[str, object]] = {}
    for item in raw_items:
        if not item.enabled:
            continue
        if item.roles and not AccessPolicy.has_any_role(request, item.roles):
            continue
        is_active = any(path.startswith(prefix) for prefix in item.starts_with)
        if item.key == "reports" and accounting_path:
            is_active = False
        section_key = item.section
        section_label = section_labels.get(section_key, ("القائمة", "Menu"))
        section_entry = sections.setdefault(
            section_key,
            {
                "key": section_key,
                "label": section_label[0] if language.startswith("ar") else section_label[1],
                "items": [],
                "expanded": False,
            },
        )
        if is_active:
            section_entry["expanded"] = True
        section_entry["items"].append(
            {
                "label": item.label(language),
                "url_name": item.url_name,
                "active": is_active,
                "icon": item.icon,
            }
        )

    grouped = [sections[key] for key in section_order if key in sections]
    return grouped
