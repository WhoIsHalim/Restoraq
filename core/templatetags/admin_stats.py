from __future__ import annotations

from django import template
from datetime import timedelta

from django.utils import timezone

from audit.models import AuditLog
from backup.models import BackupRecord
from core.models import CMSPage
from orders.models import Order
from subscriptions.models import Subscription
from tenants.models import Tenant

register = template.Library()


@register.simple_tag
def admin_metric(key: str):
    try:
        today = timezone.localdate()
        key = str(key or "").lower()

        if key == "tenants_total":
            return Tenant.objects.count()
        if key == "tenants_active":
            return Tenant.objects.filter(is_active=True).count()
        if key == "subscriptions_active":
            return Subscription.objects.filter(is_active=True, end_date__gte=today).count()
        if key == "subscriptions_expiring":
            return Subscription.objects.filter(end_date__lt=today, grace_period_end__gte=today).count()
        if key == "orders_today":
            return Order.objects.filter(status=Order.STATUS_CONFIRMED, created_at__date=today).count()
        if key == "cms_pages":
            return CMSPage.objects.count()
        if key == "audit_logs":
            return AuditLog.objects.count()
        if key == "backups_failed_24h":
            since = timezone.now() - timedelta(hours=24)
            return BackupRecord.objects.filter(status=BackupRecord.STATUS_FAILED, created_at__gte=since).count()
        return 0
    except Exception:
        return 0
