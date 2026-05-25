from django.contrib import admin

from crm.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch", "phone", "loyalty_points", "is_active")
    list_filter = ("tenant", "branch", "is_active")
