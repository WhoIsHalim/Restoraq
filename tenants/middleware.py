from __future__ import annotations

from django.conf import settings
from django.apps import apps

from tenants.services import TenantDBContextService, TenantResolver


class TenantResolutionMiddleware:
    SKIP_PREFIXES = ("/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None

        if request.path.startswith(self.SKIP_PREFIXES):
            return self.get_response(request)

        host = request.get_host()
        tenant = TenantResolver.resolve_by_host(host)
        if not tenant:
            header_name = settings.TENANT_HEADER_NAME
            header_value = request.META.get(header_name, "")
            signature = request.META.get("HTTP_X_TENANT_SIGNATURE", "")
            if header_value:
                tenant = TenantResolver.resolve_by_header(header_value, signature)

        if not tenant:
            tenant = self._resolve_from_user_membership(request)

        request.tenant = tenant
        return self.get_response(request)

    @staticmethod
    def _is_system_user(request) -> bool:
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name__in={"SystemOwner", "SystemAdmin", "ContentManager"}).exists()

    def _resolve_from_user_membership(self, request):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return None

        if self._is_system_user(request):
            forced_tenant_id = request.session.get("system_active_tenant_id")
            if not forced_tenant_id:
                return None
            tenant_model = apps.get_model("tenants", "Tenant")
            return tenant_model.objects.filter(id=forced_tenant_id, is_active=True).first()

        membership_model = apps.get_model("users", "TenantMembership")
        memberships = membership_model.objects.select_related("tenant").filter(
            user=request.user,
            is_active=True,
            tenant__is_active=True,
        )

        active_tenant_id = request.session.get("active_tenant_id")
        if active_tenant_id:
            membership = memberships.filter(tenant_id=active_tenant_id).first()
            if membership:
                return membership.tenant

        membership = memberships.order_by("created_at").first()
        if membership:
            request.session["active_tenant_id"] = membership.tenant_id
            return membership.tenant
        return None


class TenantDBContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        TenantDBContextService.set_tenant(getattr(request, "tenant", None))
        try:
            response = self.get_response(request)
        finally:
            TenantDBContextService.clear()
        return response
