from django.contrib import admin

from tenants.models import Tenant, TenantDomain


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "vat_rate", "tax_inclusive_pricing")
    search_fields = ("name", "slug")


@admin.register(TenantDomain)
class TenantDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary", "is_active")
    search_fields = ("domain", "tenant__name")
    list_filter = ("is_primary", "is_active")
