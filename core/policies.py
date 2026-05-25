from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet

from core.constants import BRANCH_SCOPED_ROLES
from restaurants.models import Branch


SYSTEM_ROLES = {"SystemOwner", "SystemAdmin", "ContentManager"}
POS_ALLOWED_ROLES = {"RestaurantOwner", "BranchManager", "Cashier"}
KITCHEN_ALLOWED_ROLES = {"RestaurantOwner", "BranchManager", "KitchenStaff"}
ORDER_WRITE_ROLES = POS_ALLOWED_ROLES


@dataclass(frozen=True)
class AccessContext:
    tenant: object | None
    membership: object | None
    role_name: str | None


class AccessPolicy:
    """Central policy helper for tenant and role based access checks."""

    @staticmethod
    def context(request) -> AccessContext:
        membership = getattr(request, "membership", None)
        return AccessContext(
            tenant=getattr(request, "tenant", None),
            membership=membership,
            role_name=getattr(membership, "role_name", None),
        )

    @staticmethod
    def is_system_user(user) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=SYSTEM_ROLES).exists()

    @staticmethod
    def has_any_role(request, roles: Iterable[str]) -> bool:
        ctx = AccessPolicy.context(request)
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return bool(ctx.role_name and ctx.role_name in set(roles))

    @staticmethod
    def require_tenant_context(request) -> AccessContext:
        ctx = AccessPolicy.context(request)
        if not ctx.tenant:
            raise PermissionDenied("Tenant context is required.")
        return ctx

    @staticmethod
    def require_membership(request) -> AccessContext:
        ctx = AccessPolicy.require_tenant_context(request)
        if not ctx.membership and not AccessPolicy.is_system_user(request.user):
            raise PermissionDenied("Membership is required.")
        return ctx

    @staticmethod
    def require_pos_access(request) -> AccessContext:
        ctx = AccessPolicy.require_membership(request)
        if request.user.is_superuser:
            return ctx
        if not ctx.role_name or ctx.role_name not in POS_ALLOWED_ROLES:
            raise PermissionDenied("You are not allowed to access cashier module.")
        return ctx

    @staticmethod
    def require_order_write_access(request) -> AccessContext:
        ctx = AccessPolicy.require_membership(request)
        if request.user.is_superuser:
            return ctx
        if not ctx.role_name or ctx.role_name not in ORDER_WRITE_ROLES:
            raise PermissionDenied("You are not allowed to create orders.")
        return ctx

    @staticmethod
    def require_kitchen_access(request) -> AccessContext:
        ctx = AccessPolicy.require_membership(request)
        if request.user.is_superuser:
            return ctx
        if not ctx.role_name or ctx.role_name not in KITCHEN_ALLOWED_ROLES:
            raise PermissionDenied("You are not allowed to access kitchen screen.")
        return ctx

    @staticmethod
    def apply_branch_scope(request, queryset: QuerySet, branch_field: str = "branch") -> QuerySet:
        """Scope queryset to membership primary branch when role is branch-scoped."""
        ctx = AccessPolicy.context(request)
        membership = ctx.membership
        if membership and ctx.role_name in BRANCH_SCOPED_ROLES and membership.primary_branch_id:
            return queryset.filter(**{f"{branch_field}_id": membership.primary_branch_id})
        return queryset

    @staticmethod
    def permitted_branches(request, *, tenant):
        """Return branches that current user is allowed to operate on for the tenant."""
        if not tenant:
            return Branch.objects.none()
        ctx = AccessPolicy.context(request)
        membership = ctx.membership
        qs = Branch.objects.filter(tenant=tenant, is_active=True).order_by("name")
        if membership and ctx.role_name in BRANCH_SCOPED_ROLES:
            if membership.primary_branch_id:
                return qs.filter(id=membership.primary_branch_id)
            return qs.none()
        return qs

    @staticmethod
    def resolve_operating_branch(request, *, tenant, requested_branch_id: int | str | None = None):
        """
        Resolve the branch to be used for write operations.
        - Branch-scoped roles are locked to their primary branch.
        - Non-branch-scoped roles can choose any active branch in tenant.
        - If no branch is provided, fallback to session branch then first active branch.
        """
        if not tenant:
            return None

        ctx = AccessPolicy.context(request)
        membership = ctx.membership
        role_name = ctx.role_name
        is_branch_scoped = bool(membership and role_name in BRANCH_SCOPED_ROLES)

        if is_branch_scoped:
            if not membership.primary_branch_id:
                return None
            if requested_branch_id and str(requested_branch_id) != str(membership.primary_branch_id):
                raise PermissionDenied("Branch-scoped role cannot operate on another branch.")
            return membership.primary_branch

        candidate_id: str | None = None
        if requested_branch_id:
            candidate_id = str(requested_branch_id)
        else:
            session_branch_id = request.session.get("active_branch_id")
            if session_branch_id:
                candidate_id = str(session_branch_id)

        allowed_branches = AccessPolicy.permitted_branches(request, tenant=tenant)
        branch = None
        if candidate_id:
            branch = allowed_branches.filter(id=candidate_id).first()

        if not branch:
            branch = allowed_branches.first()

        if branch:
            request.session["active_branch_id"] = branch.id
        return branch
