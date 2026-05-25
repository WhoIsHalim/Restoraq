from django.contrib import admin

from printing.models import BranchPrinterConfig, PrintJob, PrintTemplate, Printer


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch", "connection_type", "is_active")
    list_filter = ("tenant", "branch", "connection_type", "is_active")


@admin.register(BranchPrinterConfig)
class BranchPrinterConfigAdmin(admin.ModelAdmin):
    list_display = ("branch", "tenant", "customer_printer", "kitchen_printer", "delivery_printer", "auto_print")


@admin.register(PrintTemplate)
class PrintTemplateAdmin(admin.ModelAdmin):
    list_display = ("tenant", "code", "title")


@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    list_display = ("order", "template_type", "status", "attempts", "created_at")
    list_filter = ("status", "template_type")
