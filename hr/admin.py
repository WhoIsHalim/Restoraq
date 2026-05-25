from django.contrib import admin

from hr.models import Employee, PayrollRecord


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "tenant", "branch", "position", "salary", "is_active")
    list_filter = ("tenant", "branch", "is_active")


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "period_start", "period_end", "net_amount", "status")
    list_filter = ("status",)
