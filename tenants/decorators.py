from __future__ import annotations

from functools import wraps

from django.core.exceptions import PermissionDenied


def system_role_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required")
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        allowed = request.user.groups.filter(name__in={"SystemOwner", "SystemAdmin", "ContentManager"}).exists()
        if not allowed:
            raise PermissionDenied("System dashboard access denied")
        return view_func(request, *args, **kwargs)

    return _wrapped
