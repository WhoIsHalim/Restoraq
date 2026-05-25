from django.contrib import admin

from subscriptions.models import Subscription, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "price_egp")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "plan", "start_date", "end_date", "grace_period_end", "status", "is_active")
    list_filter = ("status", "is_active", "plan")
