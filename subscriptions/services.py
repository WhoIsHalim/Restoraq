from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from subscriptions.models import Subscription


@dataclass
class AccessDecision:
    allowed: bool
    read_only: bool
    reason: str


class SubscriptionService:
    SAFE_PREFIXES = ("/accounts/", "/admin/", "/system/", "/health/", "/static/", "/media/")

    @classmethod
    def evaluate_access(cls, tenant, path: str, method: str) -> AccessDecision:
        if path.startswith(cls.SAFE_PREFIXES):
            return AccessDecision(True, False, "system route")

        if not tenant:
            return AccessDecision(True, False, "no tenant-bound route")

        subscription = getattr(tenant, "subscription", None)
        if not subscription:
            return AccessDecision(False, True, "subscription missing")

        today = timezone.localdate()
        if today <= subscription.end_date and subscription.is_active:
            if subscription.status != Subscription.STATUS_ACTIVE:
                subscription.status = Subscription.STATUS_ACTIVE
                subscription.save(update_fields=["status", "updated_at"])
            return AccessDecision(True, False, "active")

        if subscription.end_date < today <= subscription.grace_period_end:
            if subscription.status != Subscription.STATUS_GRACE:
                subscription.status = Subscription.STATUS_GRACE
                subscription.save(update_fields=["status", "updated_at"])
            if method in {"GET", "HEAD", "OPTIONS"}:
                return AccessDecision(True, True, "grace read-only")
            return AccessDecision(False, True, "grace read-only")

        if subscription.status != Subscription.STATUS_EXPIRED:
            subscription.status = Subscription.STATUS_EXPIRED
            subscription.save(update_fields=["status", "updated_at"])
        return AccessDecision(False, True, "expired")
