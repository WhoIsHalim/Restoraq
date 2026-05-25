from __future__ import annotations

import hmac
import hashlib

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.db import connection
from django.db import transaction
from django.utils.text import slugify

from audit.services import AuditService
from core.tenant_context import clear_current_tenant_id, set_current_tenant_id
from restaurants.models import Branch, RestaurantSetting
from subscriptions.models import Subscription
from tenants.models import Tenant, TenantDomain
from users.models import TenantMembership


class TenantResolver:
    @staticmethod
    def resolve_by_host(host: str):
        domain = host.split(":", 1)[0].lower()
        mapping = (
            TenantDomain.objects.select_related("tenant")
            .filter(domain=domain, is_active=True, tenant__is_active=True)
            .first()
        )
        if mapping:
            return mapping.tenant
        return None

    @staticmethod
    def resolve_by_header(header_value: str, signature: str):
        expected = hmac.new(
            key=settings.TENANT_HEADER_SIGNATURE_SECRET.encode("utf-8"),
            msg=header_value.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature or ""):
            return None
        return Tenant.objects.filter(slug=header_value, is_active=True).first()


class TenantDBContextService:
    @staticmethod
    def set_tenant(tenant):
        tenant_id = getattr(tenant, "id", None)
        set_current_tenant_id(tenant_id)
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                if tenant_id is None:
                    cursor.execute("SELECT set_config('app.current_tenant', '', false)")
                else:
                    cursor.execute("SELECT set_config('app.current_tenant', %s, false)", [str(tenant_id)])

    @staticmethod
    def clear() -> None:
        clear_current_tenant_id()
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('app.current_tenant', '', false)")


class TenantProvisioningService:
    @staticmethod
    def _build_unique_slug(name: str, preferred_slug: str | None = None) -> str:
        base = preferred_slug or slugify(name)
        if not base:
            base = "tenant"
        candidate = base
        counter = 2
        while Tenant.objects.filter(slug=candidate).exists():
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    @classmethod
    @transaction.atomic
    def create_tenant_with_owner(cls, *, data: dict, actor=None) -> Tenant:
        tenant = Tenant.objects.create(
            name=data["tenant_name"],
            slug=cls._build_unique_slug(data["tenant_name"], data.get("tenant_slug")),
            default_language=data.get("default_language", "ar"),
            vat_rate=data.get("vat_rate", 14),
            tax_inclusive_pricing=bool(data.get("tax_inclusive_pricing", True)),
            is_active=True,
        )

        domain = (data.get("tenant_domain") or "").strip().lower()
        if domain:
            TenantDomain.objects.create(
                tenant=tenant,
                domain=domain,
                is_primary=True,
                is_active=True,
            )

        branch = Branch.objects.create(
            tenant=tenant,
            name=data.get("branch_name", "Main Branch"),
            code=data.get("branch_code", "MAIN"),
            address=data.get("branch_address", ""),
            phone=data.get("branch_phone", ""),
            is_active=True,
        )
        RestaurantSetting.objects.create(tenant=tenant)

        subscription = Subscription.objects.create(
            tenant=tenant,
            plan=data["plan"],
            start_date=data["subscription_start_date"],
            end_date=data["subscription_end_date"],
            is_active=bool(data.get("is_subscription_active", True)),
        )

        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username=data["owner_username"],
            email=data.get("owner_email", ""),
            password=data["owner_password"],
            phone=data.get("owner_phone", ""),
        )
        owner_group, _ = Group.objects.get_or_create(name="RestaurantOwner")
        owner.groups.add(owner_group)

        TenantMembership.objects.create(
            tenant=tenant,
            user=owner,
            role_name="RestaurantOwner",
            primary_branch=branch,
            is_active=True,
        )

        if actor and getattr(actor, "is_authenticated", False):
            AuditService.log_action(
                tenant=tenant,
                branch=branch,
                user=actor,
                action="tenant_created",
                model="tenants.Tenant",
                object_id=str(tenant.id),
                metadata={
                    "tenant_slug": tenant.slug,
                    "plan": subscription.plan.code,
                    "owner_username": owner.username,
                    "domain": domain,
                },
            )

        return tenant
