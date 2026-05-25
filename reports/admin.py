from django.contrib import admin

from reports.models import ReportSnapshot


@admin.register(ReportSnapshot)
class ReportSnapshotAdmin(admin.ModelAdmin):
    list_display = ("report_key", "tenant", "branch", "period_start", "period_end", "created_at")
    list_filter = ("tenant", "branch", "report_key")
