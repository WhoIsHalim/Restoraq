from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import hidden_entry

urlpatterns = [
    path(settings.ADMIN_PATH, admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("crm/", include("crm.urls")),
    path("pos/", include("pos.urls")),
    path("orders/", include("orders.urls")),
    path("menu/", include("menu.urls")),
    path("inventory/", include("inventory.urls")),
    path("hr/", include("hr.urls")),
    path("reports/", include("reports.urls")),
    path("restaurants/", include("restaurants.urls")),
    path("printing/", include("printing.urls")),
    path(settings.SYSTEM_PATH, include("tenants.system_urls")),
    path("i18n/", include("django.conf.urls.i18n")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Obscure default admin/system paths
if settings.ADMIN_PATH.strip("/").lower() != "admin":
    urlpatterns.append(path("admin/", hidden_entry))
if settings.SYSTEM_PATH.strip("/").lower() != "system":
    urlpatterns.append(path("system/", hidden_entry))

handler404 = "core.views.custom_404"
