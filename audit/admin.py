from django.contrib import admin

from audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "tenant", "branch", "user", "action", "model", "object_id")
    list_filter = ("tenant", "action", "model")
    search_fields = ("object_id", "user__username", "action")
    readonly_fields = ("tenant", "branch", "user", "action", "model", "object_id", "timestamp", "ip", "device", "metadata_json")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
