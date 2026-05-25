from __future__ import annotations

from django.http import HttpResponseForbidden

from subscriptions.services import SubscriptionService


class SubscriptionAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        decision = SubscriptionService.evaluate_access(
            tenant=getattr(request, "tenant", None),
            path=request.path,
            method=request.method,
        )
        request.subscription_read_only = decision.read_only
        if not decision.allowed:
            return HttpResponseForbidden(
                "Your subscription does not allow this action. Please renew to continue."
            )
        return self.get_response(request)
