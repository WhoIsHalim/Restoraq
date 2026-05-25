from __future__ import annotations

from django import template

register = template.Library()


GROUPS = [
    ("platform", {"ar": "المنصة", "en": "Platform"}, ["tenants", "subscriptions", "featureflags", "backup", "audit", "printing", "support"]),
    ("content", {"ar": "محتوى الموقع", "en": "Marketing Content"}, ["core"]),
    ("operations", {"ar": "التشغيل", "en": "Operations"}, ["orders", "menu", "inventory", "crm", "hr", "restaurants"]),
    ("access", {"ar": "الوصول والصلاحيات", "en": "Access Control"}, ["accounts", "users", "auth", "admin"]),
]


def _lang(language_code: str) -> str:
    return "ar" if str(language_code).startswith("ar") else "en"


@register.simple_tag
def group_admin_apps(app_list, language_code: str = "en"):
    app_map = {app.get("app_label"): app for app in app_list or []}
    used = set()
    grouped = []
    lang = _lang(language_code)

    for key, labels, app_labels in GROUPS:
        apps = []
        for label in app_labels:
            app = app_map.get(label)
            if app:
                apps.append(app)
                used.add(label)
        if apps:
            grouped.append({"key": key, "label": labels[lang], "apps": apps})

    remaining = [app for label, app in app_map.items() if label not in used]
    if remaining:
        grouped.append(
            {
                "key": "other",
                "label": "أخرى" if lang == "ar" else "Other",
                "apps": remaining,
            }
        )
    return grouped
