from django.contrib import admin

from backup.models import BackupRecord


@admin.action(description="Generate manual backup")
def run_manual_backup(modeladmin, request, queryset):
    from backup.services import BackupService

    BackupService.run_backup(backup_type=BackupRecord.TYPE_MANUAL)


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = ("created_at", "backup_type", "storage_backend", "status", "file_size")
    list_filter = ("backup_type", "storage_backend", "status")
    actions = [run_manual_backup]
