from __future__ import annotations

from datetime import datetime

from django.contrib import auth
from django.utils import timezone

from accounts.services import get_user_session_timeout


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            self._set_membership(request)
            self._enforce_timeout(request)
        return self.get_response(request)

    @staticmethod
    def _set_membership(request) -> None:
        tenant = getattr(request, "tenant", None)
        request.membership = None
        if not tenant:
            return
        membership_model = auth.get_user_model()._meta.apps.get_model("users", "TenantMembership")
        membership = (
            membership_model.objects.select_related("primary_branch")
            .filter(tenant=tenant, user=request.user, is_active=True)
            .first()
        )
        if membership:
            request.membership = membership
            return

        is_system_user = request.user.is_superuser or request.user.groups.filter(
            name__in={"SystemOwner", "SystemAdmin"}
        ).exists()
        is_forced_tenant_context = request.session.get("system_active_tenant_id") == tenant.id
        if not (is_system_user and is_forced_tenant_context):
            return

        branch_model = auth.get_user_model()._meta.apps.get_model("restaurants", "Branch")
        primary_branch = branch_model.objects.filter(tenant=tenant, is_active=True).order_by("id").first()
        request.membership = membership_model(
            tenant=tenant,
            user=request.user,
            role_name="RestaurantOwner",
            primary_branch=primary_branch,
            is_active=True,
        )

    def _enforce_timeout(self, request) -> None:
        session_key = "last_seen_at"
        now = timezone.now()
        last_seen_raw = request.session.get(session_key)
        if last_seen_raw:
            try:
                last_seen = datetime.fromisoformat(last_seen_raw)
            except ValueError:
                last_seen = now
            if timezone.is_naive(last_seen):
                last_seen = timezone.make_aware(last_seen)

            timeout = get_user_session_timeout(request.user)
            if now - last_seen > timeout:
                auth.logout(request)
                return
        request.session[session_key] = now.isoformat()
