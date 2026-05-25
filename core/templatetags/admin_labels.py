from __future__ import annotations

from django import template

register = template.Library()

APP_LABELS = {
    "core": {"ar": "المحتوى العام", "en": "Core Content"},
    "accounts": {"ar": "الحسابات", "en": "Accounts"},
    "tenants": {"ar": "المطاعم والعملاء", "en": "Tenants"},
    "subscriptions": {"ar": "الاشتراكات", "en": "Subscriptions"},
    "restaurants": {"ar": "المطاعم والفروع", "en": "Restaurants"},
    "users": {"ar": "مستخدمو المطاعم", "en": "Restaurant Users"},
    "orders": {"ar": "الطلبات والمدفوعات", "en": "Orders & Payments"},
    "menu": {"ar": "المنيو", "en": "Menu"},
    "inventory": {"ar": "المخزون", "en": "Inventory"},
    "reports": {"ar": "التقارير", "en": "Reports"},
    "crm": {"ar": "العملاء", "en": "CRM"},
    "hr": {"ar": "الموارد البشرية", "en": "HR"},
    "printing": {"ar": "الطباعة", "en": "Printing"},
    "audit": {"ar": "سجل التدقيق", "en": "Audit"},
    "backup": {"ar": "النسخ الاحتياطي", "en": "Backup"},
    "featureflags": {"ar": "مزايا الباقات", "en": "Feature Flags"},
    "support": {"ar": "الدعم والتذاكر", "en": "Support"},
    "auth": {"ar": "صلاحيات النظام", "en": "Auth"},
    "admin": {"ar": "سجل المدير", "en": "Admin Log"},
}

MODEL_LABELS = {
    "core.cmspage": {"ar": "صفحات الموقع", "en": "CMS Pages"},
    "core.homepagecontent": {"ar": "محتوى الصفحة الرئيسية", "en": "Home Page Content"},
    "core.featurespagecontent": {"ar": "محتوى صفحة الحلول", "en": "Features Page Content"},
    "core.pricingpagecontent": {"ar": "محتوى صفحة الأسعار", "en": "Pricing Page Content"},
    "core.marketingslide": {"ar": "شرائح السلايدر", "en": "Marketing Slides"},
    "core.leadrequest": {"ar": "طلبات العملاء", "en": "Lead Requests"},
    "accounts.user": {"ar": "المستخدمون", "en": "Users"},
    "tenants.tenant": {"ar": "المطاعم", "en": "Tenants"},
    "tenants.tenantdomain": {"ar": "دومينات المطاعم", "en": "Tenant Domains"},
    "subscriptions.subscriptionplan": {"ar": "باقات الاشتراك", "en": "Subscription Plans"},
    "subscriptions.subscription": {"ar": "اشتراكات المطاعم", "en": "Subscriptions"},
    "restaurants.branch": {"ar": "الفروع", "en": "Branches"},
    "restaurants.restaurantsetting": {"ar": "إعدادات المطعم", "en": "Restaurant Settings"},
    "restaurants.floorarea": {"ar": "مناطق الجلوس", "en": "Floor Areas"},
    "restaurants.diningtable": {"ar": "الطاولات", "en": "Dining Tables"},
    "restaurants.reservation": {"ar": "الحجوزات", "en": "Reservations"},
    "users.tenantmembership": {"ar": "عضوية المستخدم", "en": "Tenant Membership"},
    "orders.order": {"ar": "الطلبات", "en": "Orders"},
    "orders.orderitem": {"ar": "عناصر الطلب", "en": "Order Items"},
    "orders.payment": {"ar": "المدفوعات", "en": "Payments"},
    "orders.paymentreview": {"ar": "مراجعات المدفوعات", "en": "Payment Reviews"},
    "menu.category": {"ar": "الأقسام", "en": "Categories"},
    "menu.product": {"ar": "المنتجات", "en": "Products"},
    "menu.modifiergroup": {"ar": "مجموعات الإضافات", "en": "Modifier Groups"},
    "menu.modifieroption": {"ar": "خيارات الإضافات", "en": "Modifier Options"},
    "menu.productmodifier": {"ar": "إضافات المنتجات", "en": "Product Modifiers"},
    "inventory.ingredient": {"ar": "المكونات", "en": "Ingredients"},
    "inventory.supplier": {"ar": "الموردون", "en": "Suppliers"},
    "inventory.stockentry": {"ar": "حركات المخزون", "en": "Stock Entries"},
    "inventory.recipe": {"ar": "الوصفات", "en": "Recipes"},
    "inventory.lowstockalert": {"ar": "تنبيهات المخزون", "en": "Low Stock Alerts"},
    "reports.reportsnapshot": {"ar": "لقطات التقارير", "en": "Report Snapshots"},
    "crm.customer": {"ar": "العملاء", "en": "Customers"},
    "hr.employee": {"ar": "الموظفون", "en": "Employees"},
    "hr.payrollrecord": {"ar": "سجلات الرواتب", "en": "Payroll Records"},
    "printing.printer": {"ar": "الطابعات", "en": "Printers"},
    "printing.branchprinterconfig": {"ar": "إعدادات طابعات الفروع", "en": "Branch Printer Config"},
    "printing.printtemplate": {"ar": "قوالب الطباعة", "en": "Print Templates"},
    "printing.printjob": {"ar": "مهام الطباعة", "en": "Print Jobs"},
    "audit.auditlog": {"ar": "سجلات التدقيق", "en": "Audit Logs"},
    "backup.backuprecord": {"ar": "سجلات النسخ الاحتياطي", "en": "Backup Records"},
    "featureflags.featurecatalog": {"ar": "كتالوج المزايا", "en": "Feature Catalog"},
    "featureflags.planfeature": {"ar": "مزايا الباقات", "en": "Plan Features"},
    "featureflags.tenantfeatureoverride": {"ar": "تخصيص مزايا المطعم", "en": "Tenant Feature Override"},
    "support.supportticket": {"ar": "تذاكر الدعم", "en": "Support Tickets"},
    "auth.group": {"ar": "المجموعات", "en": "Groups"},
    "auth.permission": {"ar": "الصلاحيات", "en": "Permissions"},
    "admin.logentry": {"ar": "سجل مدير النظام", "en": "Admin Logs"},
}


def _lang(language_code: str) -> str:
    return "ar" if str(language_code).startswith("ar") else "en"


@register.simple_tag
def admin_app_name(app_label: str, default_name: str, language_code: str = "en") -> str:
    names = APP_LABELS.get(str(app_label).lower())
    if names:
        return names[_lang(language_code)]
    return default_name


@register.simple_tag
def admin_model_name(
    app_label: str,
    object_name: str,
    default_name: str,
    language_code: str = "en",
) -> str:
    key = f"{str(app_label).lower()}.{str(object_name).lower()}"
    names = MODEL_LABELS.get(key)
    if names:
        return names[_lang(language_code)]
    return default_name
