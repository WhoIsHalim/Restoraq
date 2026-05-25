from django.contrib import admin

from support.models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("subject", "tenant", "status", "priority", "created_at")
    list_filter = ("status", "priority", "tenant")
    search_fields = ("subject", "description", "tenant__name")
