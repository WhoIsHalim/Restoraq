from __future__ import annotations

from django import template

register = template.Library()


def _is_ar(language: str) -> bool:
    return str(language).startswith("ar")


@register.filter
def localized_bool(value: bool, language: str = "ar") -> str:
    if value is None:
        return "-"
    if _is_ar(language):
        return "نعم" if bool(value) else "لا"
    return "Yes" if bool(value) else "No"


@register.filter
def subscription_status_label(value: str, language: str = "ar") -> str:
    normalized = (value or "").lower()
    if _is_ar(language):
        mapping = {
            "active": "نشط",
            "grace": "فترة سماح",
            "expired": "منتهي",
        }
    else:
        mapping = {
            "active": "Active",
            "grace": "Grace",
            "expired": "Expired",
        }
    return mapping.get(normalized, value or "-")


@register.filter
def localized_plan_name(plan, language: str = "ar") -> str:
    code = (getattr(plan, "code", "") or "").lower()
    if _is_ar(language):
        mapping = {
            "basic": "أساسي",
            "standard": "قياسي",
            "multibranch": "متعدد الفروع",
            "pro": "احترافي",
        }
    else:
        mapping = {
            "basic": "Basic",
            "standard": "Standard",
            "multibranch": "MultiBranch",
            "pro": "Pro",
        }
    default_name = getattr(plan, "name", "") or "-"
    return mapping.get(code, default_name)


@register.filter
def localized_audit_action(action: str, language: str = "ar") -> str:
    action_value = (action or "").lower()
    if _is_ar(language):
        mapping = {
            "login": "تسجيل دخول",
            "failed_login": "محاولة دخول فاشلة",
            "order_created": "إنشاء طلب",
            "price_changed": "تغيير سعر",
            "stock_updated": "تحديث مخزون",
            "user_changed": "تعديل مستخدم",
            "role_changed": "تعديل دور",
            "deleted": "حذف",
            "tenant_created": "إنشاء مطعم",
            "backup_created": "إنشاء نسخة احتياطية",
        }
    else:
        mapping = {
            "login": "Login",
            "failed_login": "Failed Login",
            "order_created": "Order Created",
            "price_changed": "Price Changed",
            "stock_updated": "Stock Updated",
            "user_changed": "User Changed",
            "role_changed": "Role Changed",
            "deleted": "Deleted",
            "tenant_created": "Tenant Created",
            "backup_created": "Backup Created",
        }
    return mapping.get(action_value, action or "-")


@register.filter
def dict_get(data: dict, key: str):
    if not isinstance(data, dict):
        return None
    return data.get(key)
