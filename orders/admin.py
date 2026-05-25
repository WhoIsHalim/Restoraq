from django.contrib import admin

from orders.models import Order, OrderItem, Payment, PaymentReview


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "tenant", "branch", "order_type", "status", "total_amount", "pending_sync", "created_at")
    list_filter = ("tenant", "branch", "order_type", "status", "pending_sync")
    inlines = [OrderItemInline, PaymentInline]


@admin.register(PaymentReview)
class PaymentReviewAdmin(admin.ModelAdmin):
    list_display = ("payment", "status", "reviewer", "reviewed_at")
    list_filter = ("status",)
