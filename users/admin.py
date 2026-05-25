from django.contrib import admin

from users.models import TenantMembership


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant", "role_name", "primary_branch", "is_active")
    list_filter = ("tenant", "role_name", "is_active")
    search_fields = ("user__username", "tenant__name")
