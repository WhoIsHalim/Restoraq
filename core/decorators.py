from __future__ import annotations

from functools import wraps

from django.core.exceptions import PermissionDenied

from core.constants import BRANCH_SCOPED_ROLES


def role_required(group_name: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise PermissionDenied("Authentication required")
            if not (user.is_superuser or user.groups.filter(name=group_name).exists()):
                raise PermissionDenied(f"Role {group_name} is required")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def branch_scoped_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        membership = getattr(request, "membership", None)
        if membership and membership.role_name in BRANCH_SCOPED_ROLES and not membership.primary_branch_id:
            raise PermissionDenied("Branch-scoped role requires assigned branch")
        return view_func(request, *args, **kwargs)

    return _wrapped
